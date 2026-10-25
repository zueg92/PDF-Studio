"""Compressione, password, watermark."""
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import pikepdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO


def compress_pdf(input_path: str | Path, output_path: str | Path) -> dict:
    """Comprime riscrivendo con pikepdf (stream compress + dedup)."""
    input_path, output_path = Path(input_path), Path(output_path)
    before = input_path.stat().st_size
    with pikepdf.open(str(input_path)) as pdf:
        pdf.save(
            str(output_path),
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
            linearize=True,
        )
    after = output_path.stat().st_size
    return {
        "before": before,
        "after": after,
        "saved_percent": round((1 - after / before) * 100, 1) if before else 0,
    }


def protect_pdf(
    input_path: str | Path,
    output_path: str | Path,
    user_pw: str,
    owner_pw: str | None = None,
) -> str:
    """Aggiunge password (AES-256)."""
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=user_pw, owner_password=owner_pw or user_pw,
                   algorithm="AES-256")
    writer.write(str(output_path))
    return str(output_path)


def remove_password(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> str:
    """Rimuove password (serve quella corretta)."""
    reader = PdfReader(str(input_path))
    if reader.is_encrypted:
        reader.decrypt(password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.write(str(output_path))
    return str(output_path)


def add_watermark(
    input_path: str | Path,
    output_path: str | Path,
    text: str = "BOZZA",
    opacity: float = 0.3,
) -> str:
    """Aggiunge watermark diagonale su ogni pagina."""
    # Crea PDF watermark
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.saveState()
    c.setFont("Helvetica-Bold", 80)
    try:
        c.setFillAlpha(opacity)
    except Exception:
        pass
    c.translate(w / 2, h / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    buf.seek(0)
    wm_page = PdfReader(buf).pages[0]

    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(wm_page)
        writer.add_page(page)
    writer.write(str(output_path))
    return str(output_path)