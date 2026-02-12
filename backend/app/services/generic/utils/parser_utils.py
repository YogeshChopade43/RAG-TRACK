from pypdf import PdfReader

# =================================================
# Utility Functions
# =================================================

def normalize_text(text: str) -> str:
    return " ".join(text.split())

def normalize_pages(pages):
    normalized = []
    for p in pages:
        if isinstance(p, bytes):
            normalized.append(p.decode("utf-8", errors="ignore"))
        else:
            normalized.append(str(p))
    return normalized

# =================================================
# PDF Parser
# =================================================

# def parse_pdf(file_path: str):
#     reader = PdfReader(file_path)
#     pages = []
#     for i, page in enumerate(reader.pages):
#         text = page.extract_text() or ""
#         text = normalize_text(text)
#         if text.strip():
#             pages.append({"page_number": i + 1, "text": text})
#     return pages

# # =================================================
# # TXT Parser
# # =================================================

# def parse_txt(file_path: str):
#     with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
#         text = normalize_text(f.read())
#     return [{"page_number": None, "text": text}]

