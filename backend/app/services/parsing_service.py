import json, os
from app.services.parsers import parse_pdf, parse_txt
from app.services.metadata_io import load_metadata, save_metadata
from app.core.paths import PARSED_DIR

PARSED_BASE = PARSED_DIR

class ParsingService:
    def parse(self, document_id: str):
        meta = load_metadata(document_id)
        raw_path = meta["storage_path"]
        ext = meta["source_type"]

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

        meta["status"] = "PARSED"
        meta["parsed_path"] = out_path
        save_metadata(meta)

        return {"document_id": document_id, "pages": len(pages)}
