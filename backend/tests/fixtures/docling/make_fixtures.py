"""Regenerate the Docling parser fixtures (needs reportlab, python-docx, python-pptx, Pillow).

Run: python backend/tests/fixtures/docling/make_fixtures.py
"""
from pathlib import Path

from docx import Document
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

HERE = Path(__file__).parent


def digital_table_pdf():
    ss = getSampleStyleSheet()
    rows = [["Quarter", "Revenue", "Customers"]] + [[f"Q{i}", str(i * 1200), str(i * 37)] for i in (1, 2, 3, 4)]
    table = Table(rows)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    SimpleDocTemplate(str(HERE / "digital_table.pdf"), pagesize=A4).build([
        Paragraph("Company Overview", ss["Heading1"]),
        Paragraph("Acme builds retrieval systems for document search.", ss["Normal"]),
        PageBreak(),
        Paragraph("Quarterly Results", ss["Heading1"]),
        Paragraph("Revenue grew every quarter.", ss["Normal"]),
        table,
    ])


def scanned_pdf():
    img = Image.new("L", (1240, 600), "white")
    font = ImageFont.truetype("arial.ttf", 44)
    ImageDraw.Draw(img).text((100, 250), "Scanned invoice total 4200", fill="black", font=font)
    img.save(HERE / "scanned.pdf", "PDF", resolution=150)


def docx():
    d = Document()
    d.add_heading("Project Charter", level=1)
    d.add_paragraph("The project delivers a hybrid search service.")
    d.save(HERE / "sample.docx")


def pptx():
    p = Presentation()
    for title, body in [("Roadmap", "Ship Docling ingestion"), ("Risks", "OCR speed on large scans")]:
        s = p.slides.add_slide(p.slide_layouts[1])
        s.shapes.title.text = title
        s.placeholders[1].text = body
    p.save(HERE / "sample.pptx")


def html():
    (HERE / "sample.html").write_text(
        "<html><body><h1>Pricing</h1><p>Plans are billed monthly.</p>"
        "<table><tr><th>Plan</th><th>Price</th></tr><tr><td>Pro</td><td>20</td></tr></table></body></html>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    digital_table_pdf()
    scanned_pdf()
    docx()
    pptx()
    html()
    (HERE / "corrupt.pdf").write_bytes(b"<html><body>not a pdf</body></html>")
    print("fixtures written to", HERE)
