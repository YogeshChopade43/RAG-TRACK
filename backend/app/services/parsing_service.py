import json, os
from app.services.parsers import parse_pdf, parse_txt
from app.services.metadata_io import load_metadata, save_metadata
from app.core.paths import PARSED_DIR
from app.services.trace_service import TraceService


PARSED_BASE = PARSED_DIR

class ParsingService:
    def parse(self, document_id: str):
        self.trace_service = TraceService()

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

        self.trace_service.add_artifact(
        document_id,
        "parsed_path",
        out_path
        )

        self.trace_service.update_stage(
            document_id,
            stage="parsing",
            payload={
                "parser_used": ext,
                "total_pages": len(pages),
                "parsed_path": out_path,
                "status": "SUCCESS"
            },
            status="PARSED"
        )


        return {"document_id": document_id, "pages": len(pages)}
