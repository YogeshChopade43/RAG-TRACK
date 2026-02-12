from typing import List, Dict
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader

from app.services.generic.utils.parser_utils import normalize_text


# -----------------------------------------------------------
#                PDF TYPE DETECTION
# -----------------------------------------------------------

def pdf_has_text(file_path: str) -> bool:
    """
    Detect whether a PDF contains real embedded text.
    We only inspect first 3 pages for speed.
    """
    try:
        reader = PdfReader(file_path)

        for page in reader.pages[:3]:
            text = page.extract_text()
            if text and len(text.strip()) > 30:
                return True

        return False

    except Exception:
        return False


# -----------------------------------------------------------
#                DIGITAL PDF PARSER (LAYOUT AWARE)
# -----------------------------------------------------------

def parse_pdf_textual(path: str) -> List[Dict]:
    """
    For digitally generated PDFs.
    Uses pdfplumber which reconstructs layout.
    """

    pages = []

    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):

            text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2
            ) or ""

            text = normalize_text(text)

            if text.strip():
                pages.append({
                    "page_number": i + 1,
                    "text": text
                })

    return pages


# -----------------------------------------------------------
#                SCANNED PDF PARSER (OCR)
# -----------------------------------------------------------

def parse_pdf_scanned(path: str) -> List[Dict]:
    """
    OCR pipeline for scanned PDFs.
    Converts each page to image -> Tesseract OCR.
    """

    pages = []

    images = convert_from_path(path, dpi=300)

    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img)
        text = normalize_text(text)

        if text.strip():
            pages.append({
                "page_number": i + 1,
                "text": text
            })

    return pages


def parse_pdf(file_path: str) -> List[Dict]:
    """
    Smart PDF router.
    Decides extraction strategy automatically.
    """

    if pdf_has_text(file_path):
        print("PDF detected as DIGITAL → pdfplumber extraction")
        return parse_pdf_textual(file_path)

    print("PDF detected as SCANNED → OCR extraction")
    return parse_pdf_scanned(file_path)
