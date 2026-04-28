import json
import logging
import os

from app.core.config import settings
from app.services.generic.parsers.pdf_parser import parse_pdf
from app.services.generic.parsers.txt_parser import parse_txt
from app.services.generic.utils.parser_utils import normalize_pages
from app.services.text_cleaning.text_cleaning_service import TextCleaningService

logger = logging.getLogger(__name__)

PARSED_BASE = settings.parsed_dir
RAW_BASE = settings.raw_dir
cleaner = TextCleaningService()


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

        if ext == "pdf":
            logger.info(f"Parsing PDF document {filename}")
            pages = parse_pdf(raw_path)
        elif ext == "txt":
            logger.info(f"Parsing TXT document {filename}")
            pages = parse_txt(raw_path)
        else:
            raise ValueError(f"Unsupported source type: {ext}")

        logger.debug(f"Raw pages extracted: {len(pages)}")

        pages = cleaner.clean_pages(pages)
        logger.debug("Text cleaning completed")

        os.makedirs(PARSED_BASE, exist_ok=True)
        out_path = os.path.join(PARSED_BASE, f"{document_id}.json")

        payload = {"filename": filename, "document_id": document_id, "pages": pages}

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        logger.info(f"Parsing completed for document {document_id}")

        return {
            "file_name": filename,
            "document_id": document_id,
            "pages": pages,  # Includes page numbers and text, pages.append({"page_number": i + 1,"text": text})
        }
