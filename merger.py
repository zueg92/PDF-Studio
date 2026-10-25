"""Operazioni base sui PDF: merge, split, rotate, delete, reorder."""
from pathlib import Path
from typing import Iterable, Sequence
from pypdf import PdfReader, PdfWriter, PageObject, Transformation


# Dimensioni standard in punti (1 pt = 1/72 di pollice)
STANDARD_SIZES = {
    "a4":               (595.28, 841.89),
    "a4_landscape":     (841.89, 595.28),
    "letter":           (612.0, 792.0),
    "letter_landscape": (792.0, 612.0),
}


def _resolve_target_size(page_size, first_page):
    """Ritorna (w, h) target oppure None se non uniformare."""
    if page_size is None or page_size == "none":
        return None
    if page_size == "auto":
        if first_page is None:
            return None
        return float(first_page.mediabox.width), float(first_page.mediabox.height)
    if isinstance(page_size, tuple) and len(page_size) == 2:
        return float(page_size[0]), float(page_size[1])
    if isinstance(page_size, str) and page_size in STANDARD_SIZES:
        return STANDARD_SIZES[page_size]
    raise ValueError(f"page_size non valido: {page_size!r}")


def merge_pdfs(
    inputs: Sequence[str | Path],
    output: str | Path,
    add_bookmarks: bool = True,
    page_size="auto",
) -> dict:
    """Unisce più PDF.

    Parametri:
        inputs: lista di file
        output: file risultante
        add_bookmarks: aggiunge un segnalibro per ogni file
        page_size: 'auto' | 'a4' | 'a4_landscape' | 'letter' | 'letter_landscape'
                   | 'none' | tuple(w, h)
                   - 'auto': dimensione della prima pagina del primo PDF
                   - 'none': non uniformare (mantieni originali)
                   - tuple: (larghezza_pt, altezza_pt)
    """
    if not inputs:
        raise ValueError("Nessun file da unire.")

    writer = PdfWriter()
    total_pages = 0
    toc = []

    # Determina la dimensione target
    first_page = None
    if page_size == "auto":
        first_reader = PdfReader(str(inputs[0]))
        if len(first_reader.pages) > 0:
            first_page = first_reader.pages[0]
    target = _resolve_target_size(page_size, first_page)

    for path in inputs:
        path = Path(path)
        reader = PdfReader(str(path))
        start = total_pages

        for page in reader.pages:
            if target is not None:
                # Sposta l'eventuale rotazione nel contenuto, così la scalatura è corretta
                if page.rotation != 0:
                    page.transfer_rotation_to_content()

                orig_w = float(page.mediabox.width)
                orig_h = float(page.mediabox.height)

                if orig_w > 0 and orig_h > 0:
                    target_w, target_h = target
                    # Scala mantenendo le proporzioni (contain)
                    scale = min(target_w / orig_w, target_h / orig_h)
                    new_w = orig_w * scale
                    new_h = orig_h * scale
                    # Centra la pagina nel target
                    tx = (target_w - new_w) / 2
                    ty = (target_h - new_h) / 2

                    new_page = PageObject.create_blank_page(
                        width=target_w, height=target_h
                    )
                    op = Transformation().scale(scale, scale).translate(tx, ty)
                    new_page.merge_transformed_page(page, op)
                    writer.add_page(new_page)
                else:
                    writer.add_page(page)
            else:
                writer.add_page(page)

            total_pages += 1

        if add_bookmarks:
            toc.append((path.stem, start))

    for title, page_idx in toc:
        writer.add_outline_item(title, page_idx)

    writer.write(str(output))
    return {
        "output": str(output),
        "pages": total_pages,
        "files": len(inputs),
        "formato": (
            f"{target[0]:.0f} × {target[1]:.0f} pt"
            if target else "originali"
        ),
    }


def split_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    ranges: Sequence[tuple[int, int]] | None = None,
) -> list[str]:
    """Estrae range di pagine (1-based, inclusi). Se ranges=None, una pagina per file."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(input_path))
    n = len(reader.pages)

    if ranges is None:
        ranges = [(i, i) for i in range(1, n + 1)]

    results = []
    for start, end in ranges:
        writer = PdfWriter()
        for p in range(start - 1, min(end, n)):
            writer.add_page(reader.pages[p])
        out = output_dir / f"{input_path.stem}_p{start}-{end}.pdf"
        writer.write(str(out))
        results.append(str(out))
    return results


def rotate_pages(
    input_path: str | Path,
    output_path: str | Path,
    angle: int = 90,
    pages: Sequence[int] | None = None,
) -> str:
    """Ruota pagine (1-based). pages=None → tutte."""
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    targets = set(pages) if pages else None
    for i, page in enumerate(reader.pages, start=1):
        if targets is None or i in targets:
            page.rotate(angle)
        writer.add_page(page)
    writer.write(str(output_path))
    return str(output_path)


def delete_pages(
    input_path: str | Path,
    output_path: str | Path,
    pages: Iterable[int],
) -> str:
    """Elimina pagine (1-based)."""
    reader = PdfReader(str(input_path))
    to_delete = set(pages)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages, start=1):
        if i not in to_delete:
            writer.add_page(page)
    writer.write(str(output_path))
    return str(output_path)


def reorder_pages(
    input_path: str | Path,
    output_path: str | Path,
    order: Sequence[int],
) -> str:
    """Riordina pagine secondo order (lista 1-based)."""
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    for idx in order:
        writer.add_page(reader.pages[idx - 1])
    writer.write(str(output_path))
    return str(output_path)