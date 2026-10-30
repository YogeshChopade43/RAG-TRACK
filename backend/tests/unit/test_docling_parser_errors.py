"""Docling parser error mapping (no real Docling needed: the converter is faked)."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.generic.parsers import docling_parser


def fake_doc(pages=2):
    doc = MagicMock()
    doc.num_pages.return_value = pages
    doc.export_to_markdown.side_effect = lambda page_no=None, **_: f"# Page {page_no}"
    return doc


def fake_pdf(n_pages, chars=True):
    page = SimpleNamespace(chars=[1] if chars else [], images=[])
    pdf = MagicMock()
    pdf.__enter__.return_value = SimpleNamespace(pages=[page] * n_pages)
    return pdf


def test_setup_failure_is_not_reported_as_a_corrupt_file():
    with patch.object(docling_parser, "_get_converter", side_effect=RuntimeError("model files missing")), \
         patch.object(docling_parser.pdfplumber, "open", return_value=fake_pdf(1)):
        with pytest.raises(RuntimeError, match="model files missing"):
            docling_parser.parse_with_docling("x.pdf", "pdf")


def test_conversion_failure_is_a_readable_error():
    conv = MagicMock()
    conv.convert.side_effect = Exception("bad xref")
    with patch.object(docling_parser, "_get_converter", return_value=conv), \
         patch.object(docling_parser.pdfplumber, "open", return_value=fake_pdf(1)):
        with pytest.raises(ValueError, match="Couldn't read this file"):
            docling_parser.parse_with_docling("x.pdf", "pdf")


def test_pdf_over_the_page_limit_is_refused_before_converting():
    conv = MagicMock()
    with patch.object(docling_parser, "_get_converter", return_value=conv), \
         patch.object(docling_parser.pdfplumber, "open", return_value=fake_pdf(docling_parser.MAX_PDF_PAGES + 1)):
        with pytest.raises(ValueError, match=f"limit is {docling_parser.MAX_PDF_PAGES} pages"):
            docling_parser.parse_with_docling("x.pdf", "pdf")
    conv.convert.assert_not_called()


def test_page_source_detection_failure_falls_back_to_text():
    conv = MagicMock()
    conv.convert.return_value = SimpleNamespace(document=fake_doc(2))
    opened = [fake_pdf(2), Exception("pdfplumber choked")]
    with patch.object(docling_parser, "_get_converter", return_value=conv), \
         patch.object(docling_parser.pdfplumber, "open", side_effect=lambda *_: _next(opened)):
        pages = docling_parser.parse_with_docling("x.pdf", "pdf")
    assert [p["source"] for p in pages] == ["text", "text"]


def _next(items):
    item = items.pop(0)
    if isinstance(item, Exception):
        raise item
    return item
