import json, os
from app.services.generic.parsers.pdf_parser import parse_pdf
from app.services.generic.parsers.txt_parser import parse_txt
from app.core.paths import PARSED_DIR, RAW_DIR
from app.services.generic.utils.parser_utils import normalize_pages


PARSED_BASE = PARSED_DIR
RAW_BASE = RAW_DIR

class ParsingService:
    def parse(self, document_id: str):
        raw_doc_dir = os.path.join(RAW_BASE, document_id)

        if not os.path.isdir(raw_doc_dir):
            raise ValueError("Raw document directory not found")

        files = os.listdir(raw_doc_dir)
        if not files:
            raise ValueError("No files found for document")

        filename = files[0]
        raw_path = os.path.join(raw_doc_dir, filename)

        ext = filename.split(".")[-1].lower()

        #TODO: Fix PDF parsing, currently failing on test PDF document. May need to switch to a different library or debug the current one.
        if ext == "pdf":                                
            print(f"Parsing PDF document {filename}")
            pages = parse_pdf(raw_path)
        elif ext == "txt":
            print(f"Parsing TXT document {filename}")
            pages = parse_txt(raw_path)
        else:
            raise ValueError(f"Unsupported source type: {ext}")
        
        pages = normalize_pages(pages)

        print("Parsing completed.")

        os.makedirs(PARSED_BASE, exist_ok=True)
        out_path = os.path.join(PARSED_BASE, f"{document_id}.json")

        payload = {
            "document_id": document_id,
            "pages": pages
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return {
            "document_id": document_id,
            "pages": len(pages),
            "source_file": filename
        }