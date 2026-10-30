"""Docling parser against small committed fixtures.

Needs real torch/pdfplumber, which conftest stubs by default. Run with:
    RAGTRACK_REAL_ML=1 pytest tests/unit/test_docling_parser.py   (Python 3.10+, venv311)
"""
import os
from pathlib import Path

import pytest

if not os.environ.get("RAGTRACK_REAL_ML"):
    pytest.skip("Docling tests need RAGTRACK_REAL_ML=1 (real ML libraries)", allow_module_level=True)
pytest.importorskip("docling")

from app.services.generic.parsers.docling_parser import parse_with_docling  # noqa: E402

FIX = Path(__file__).parents[1] / "fixtures" / "docling"


def test_pdf_headings_tables_and_pages():
    pages = parse_with_docling(str(FIX / "digital_table.pdf"), "pdf")
    assert [p["page_number"] for p in pages] == [1, 2]
    assert any(line.startswith("#") for line in pages[0]["text"].splitlines())
    assert "| ---" in pages[1]["text"] or "|---" in pages[1]["text"]
    assert {p["source"] for p in pages} == {"text"}


def test_scanned_pdf_is_ocrd():
    pages = parse_with_docling(str(FIX / "scanned.pdf"), "pdf")
    assert pages[0]["source"] == "ocr"
    assert "4200" in pages[0]["text"]


def test_pptx_slides_are_pages():
    assert [p["page_number"] for p in parse_with_docling(str(FIX / "sample.pptx"), "pptx")] == [1, 2]


@pytest.mark.parametrize("name,ext", [("sample.docx", "docx"), ("sample.html", "html")])
def test_docx_html_single_unpaged_entry(name, ext):
    pages = parse_with_docling(str(FIX / name), ext)
    assert len(pages) == 1 and pages[0]["page_number"] is None and pages[0]["source"] == "text"


def test_corrupt_file_raises_readable_error():
    with pytest.raises(ValueError, match="Couldn't read this file"):
        parse_with_docling(str(FIX / "corrupt.pdf"), "pdf")
