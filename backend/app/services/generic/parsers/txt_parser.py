# =================================================
# # TXT Parser
# # =================================================

from app.services.generic.utils.parser_utils import normalize_text

    
def parse_txt(file_path: str):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = normalize_text(f.read())
    return [{"page_number": None, "text": text}]