import json
import os

from app.core.paths import PARSED_DIR, CHUNKS_DIR
from app.services.trace_service import TraceService


class ChunkingService:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.trace_service = TraceService()

    def chunk_document(self, document_id: str):
        parsed_path = os.path.join(PARSED_DIR, f"{document_id}.json")

        if not os.path.exists(parsed_path):
            raise FileNotFoundError("Parsed file not found")

        with open(parsed_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)

        pages = parsed["pages"]
        chunks = []

        for page in pages:
            page_number = page["page_number"]
            text = page["text"]

            page_chunks = self._chunk_page(
                document_id=document_id,
                page_number=page_number,
                text=text
            )
            chunks.extend(page_chunks)

        os.makedirs(CHUNKS_DIR, exist_ok=True)
        out_path = os.path.join(CHUNKS_DIR, f"{document_id}.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "document_id": document_id,
                    "total_chunks": len(chunks),
                    "chunks": chunks
                },
                f,
                indent=2
            )

        # TRACE UPDATE (facts only)
        self.trace_service.update_stage(
            document_id=document_id,
            stage="chunking",
            payload={
                "strategy": "page_aware_fixed",
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
                "total_chunks": len(chunks),
                "chunks_path": out_path
            },
            status="CHUNKED"
        )

        self.trace_service.add_artifact(
            document_id,
            "chunks_path",
            out_path
        )

        return {
            "document_id": document_id,
            "total_chunks": len(chunks)
        }

    def _chunk_page(self, document_id: str, page_number: int, text: str):
        chunks = []
        start = 0
        chunk_index = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk_text = text[start:end]

            chunk_id = f"{document_id}_p{page_number}_c{chunk_index}"

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "start_offset": start,
                    "end_offset": min(end, text_length)
                }
            )

            chunk_index += 1
            start = end - self.overlap

            if start < 0:
                start = 0

        return chunks
