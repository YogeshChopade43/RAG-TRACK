from typing import List, Dict
import pdfplumber
from app.services.generic.utils.parser_utils import normalize_text


def parse_pdf(file_path: str) -> List[Dict]:
    """
    Safe digital PDF parser.
    Attempts extraction and validates text quality.
    Rejects scanned/image PDFs gracefully.
    """

    pages: List[Dict] = []
    total_characters = 0

    try:
        with pdfplumber.open(file_path) as pdf:

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
                    total_characters += len(text)

    except Exception as e:
        raise ValueError("Failed to read PDF structure.") from e

    # -------- VALIDATION STEP (replaces detection) --------

    if len(pages) == 0:
        raise ValueError(
            "This PDF appears to be image-based (scanned) or contains no extractable text. "
            "Please upload a digital/text PDF."
        )

    return pages
