import json
import os
from app.core.config import VECTOR_STORE_DIR


def save_document_vector_store(document_id: str, embedded_chunks: list):
    """
    Saves embeddings specific to a single document.
    """

    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    doc_store_path = os.path.join(VECTOR_STORE_DIR, f"{document_id}.json")

    with open(doc_store_path, "w", encoding="utf-8") as f:
        json.dump(embedded_chunks, f, indent=2)

    print(f"🧠 Stored {len(embedded_chunks)} chunks for document {document_id}")