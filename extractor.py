"""Estrazione contenuti."""
from pathlib import Path
from typing import Iterator
import pdfplumber
import fitz  # PyMuPDF


def extract_text(input_path: str | Path, per_page: bool = True) -> dict:
    """Estrae testo. per_page=True → dict pagina→testo."""
    input_path = Path(input_path)
    if per_page:
        result = {}
        with pdfplumber.open(str(input_path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                result[i] = page.extract_text() or ""
        return result
    with pdfplumber.open(str(input_path)) as pdf:
        return {"text": "\n".join((p.extract_text() or "") for p in pdf.pages)}


def extract_tables(input_path: str | Path) -> list[dict]:
    """Estrae tabelle come lista di {page, table} (table = lista di righe)."""
    tables = []
    with pdfplumber.open(str(input_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            for t in page.extract_tables():
                tables.append({"page": i, "table": t})
    return tables


def extract_images(input_path: str | Path, output_dir: str | Path) -> list[str]:
    """Estrae immagini embedded come PNG."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(input_path))
    paths = []
    for pno in range(len(doc)):
        for img in doc.get_page_images(pno):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:  # CMYK → RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            out = output_dir / f"p{pno + 1}_x{xref}.png"
            pix.save(str(out))
            paths.append(str(out))
    doc.close()
    return paths


def pdf_to_images(input_path: str | Path, output_dir: str | Path, dpi: int = 150) -> list[str]:
    """Rasterizza le pagine in PNG."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(input_path))
    paths = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)
        out = output_dir / f"{input_path.stem}_p{i}.png"
        pix.save(str(out))
        paths.append(str(out))
    doc.close()
    return paths


def images_to_pdf(images: list[str | Path], output_path: str | Path) -> str:
    """Unisce immagini in un PDF."""
    import img2pdf
    with open(output_path, "wb") as f:
        f.write(img2pdf.convert([str(i) for i in images]))
    return str(output_path)


def get_info(input_path: str | Path) -> dict:
    """Metadati + numero pagine."""
    reader_fitz = fitz.open(str(input_path))
    info = {
        "pages": reader_fitz.page_count,
        "metadata": reader_fitz.metadata,
        "size_bytes": Path(input_path).stat().st_size,
    }
    reader_fitz.close()
    return info