from app.core.config import CHUNK_SIZE, CHUNK_OVERLAP

class ChunkingService:

    def chunk(self, parsed_load: dict) -> list:

        document_id = parsed_load["document_id"]
        pages = parsed_load["pages"]
        fname = parsed_load["file_name"]
        print(f"Chunking document {document_id} with filename {fname}")

        if not pages:
            raise ValueError("No pages found to chunk")

        if CHUNK_SIZE <= 0:
            raise ValueError("CHUNK_SIZE must be positive")


        chunks = []
        chunk_counter = 1

        # -------- PAGE AWARE CHUNKING --------
        for page in pages:

            page_number = page["page_number"]
            text = page["text"]

            start = 0
            text_length = len(text)

            while start < text_length:
                end = start + CHUNK_SIZE
                chunk_text = text[start:end]

                if chunk_text.strip():
                    chunk_id = f"{document_id}_chunk_{chunk_counter}"

                    chunks.append({
                        "chunk_id": chunk_id,
                        "file_name": fname,
                        "document_id": document_id,
                        "page_number": page_number,
                        "chunk_text": chunk_text,
                        "char_start": start,
                        "char_end": min(end, text_length)
                    })

                    chunk_counter += 1

                start += CHUNK_SIZE - CHUNK_OVERLAP

        print(f"Total chunks created: {len(chunks)}")

        if chunks:
            print("Sample chunk:")
            print(chunks[0])

        return chunks