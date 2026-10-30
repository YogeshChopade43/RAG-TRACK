"""
Docling parser: layout-aware Markdown per page for PDF, DOCX, PPTX and HTML.

OCR (RapidOCR) runs only on bitmap regions; page headers/footers are left out
(Docling puts them in the furniture layer, which the Markdown export skips).
"""
import logging
import threading

import pdfplumber

from app.core.config import settings

logger = logging.getLogger(__name__)

PAGED = {"pdf", "pptx"}
# ponytail: a page cap bounds one upload's time (~3.5 s/page scanned) since uploads run one at a time
MAX_PDF_PAGES = 100
UNREADABLE = "Couldn't read this file. It may be corrupt or password-protected."
_converter = None
_lock = threading.Lock()


def _get_converter():
    """One converter per process: building it loads the layout, table and OCR models."""
    global _converter
    with _lock:
        if _converter is None:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                RapidOcrOptions,
            )
            from docling.document_converter import DocumentConverter, PdfFormatOption

            options = PdfPipelineOptions(
                do_ocr=True,
                do_table_structure=True,
                ocr_options=RapidOcrOptions(),
                artifacts_path=settings.docling_artifacts_path,
            )
            _converter = DocumentConverter(
                allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.PPTX, InputFormat.HTML],
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
            )
        return _converter


def _markdown(doc, page_no=None) -> str:
    return doc.export_to_markdown(
        page_no=page_no, image_placeholder="", escape_html=False, escape_underscores=False
    ).strip()


def _pdf_sources(path: str) -> list[str]:
    """Per page: no text layer → 'ocr'; text layer plus images → 'mixed'; else 'text'."""
    try:
        with pdfplumber.open(path) as pdf:
            return [
                "ocr" if not page.chars else "mixed" if page.images else "text"
                for page in pdf.pages
            ]
    except Exception as e:
        logger.warning(f"Page source detection failed for {path}: {e}")
        return []  # pages default to "text"


def _check_pdf_pages(path: str) -> None:
    try:
        with pdfplumber.open(path) as pdf:
            n = len(pdf.pages)
    except Exception as e:
        raise ValueError(UNREADABLE) from e
    if n > MAX_PDF_PAGES:
        raise ValueError(f"This PDF has {n} pages; the limit is {MAX_PDF_PAGES} pages.")


def parse_with_docling(path: str, ext: str) -> list[dict]:
    if ext == "pdf":
        _check_pdf_pages(path)
    # Outside the try: a missing model or library is a server fault, not a bad file
    converter = _get_converter()
    try:
        doc = converter.convert(path).document
    except Exception as e:
        logger.warning(f"Docling could not convert {path}: {e}")
        raise ValueError(UNREADABLE) from e
    sources = _pdf_sources(path) if ext == "pdf" else []

    if ext in PAGED:
        pages = []
        for n in range(1, doc.num_pages() + 1):
            text = _markdown(doc, n)
            if text:
                source = sources[n - 1] if n <= len(sources) else "text"
                pages.append({"page_number": n, "text": text, "source": source})
    else:
        text = _markdown(doc)
        pages = [{"page_number": None, "text": text, "source": "text"}] if text else []

    if not pages:
        raise ValueError("No readable text was found in this document.")
    return pages
