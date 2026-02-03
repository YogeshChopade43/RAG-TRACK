import json, os
from backend.app.services.generic.parsers import parse_pdf, parse_txt
from app.core.paths import PARSED_DIR



PARSED_BASE = PARSED_DIR

class ParsingService:
    def parse(self, document_id: str):
        raw_path_pdf = os.path.join(PARSED_BASE, f"{document_id}.pdf")
        raw_path_txt = os.path.join(PARSED_BASE, f"{document_id}.txt")
        if os.path.exists(raw_path_pdf):
            raw_path = raw_path_pdf
            ext = "pdf"
        elif os.path.exists(raw_path_txt):
            raw_path = raw_path_txt
            ext = "txt"
        else:
            raise ValueError("Unsupported source type or file not found")

        if ext == "pdf":
            pages = parse_pdf(raw_path)
        elif ext == "txt":
            pages = parse_txt(raw_path)
        else:
            raise ValueError("Unsupported source type")

        os.makedirs(PARSED_BASE, exist_ok=True)
        out_path = os.path.join(PARSED_BASE, f"{document_id}.json")

        payload = {
            "document_id": document_id,
            "pages": pages
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return {"document_id": document_id, "pages": len(pages)}
