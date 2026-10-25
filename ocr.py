"""OCR per PDF scansionati."""
from pathlib import Path
import fitz
from PIL import Image
import pytesseract
from pypdf import PdfReader, PdfWriter
import io


def ocr_pdf(
    input_path: str | Path,
    output_path: str | Path,
    lang: str = "ita+eng",
    dpi: int = 300,
) -> dict:
    """OCR su PDF: genera un PDF con layer testo invisibile sopra le immagini."""
    input_path, output_path = Path(input_path), Path(output_path)
    src = fitz.open(str(input_path))
    out = fitz.open()
    total_chars = 0

    for page in src:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(
            img, extension="pdf", lang=lang
        )
        ocr_page = fitz.open("pdf", pdf_bytes)
        out.insert_pdf(ocr_page)
        text = pytesseract.image_to_string(img, lang=lang)
        total_chars += len(text.strip())

    out.save(str(output_path))
    out.close()
    src.close()
    return {"output": str(output_path), "chars": total_chars}