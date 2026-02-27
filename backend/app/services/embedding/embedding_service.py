import os
import json
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np
from app.core.config import EMBEDDING_DIR, MODEL_NAME


class EmbeddingService:
    """
    Converts chunks -> embeddings (vectors)

    Output:
        Each chunk gets a vector representation.
        We store vector + metadata for retrieval.
    """

    def __init__(self):
        print("Loading embedding model...")
        self.model = SentenceTransformer(MODEL_NAME)
        os.makedirs(EMBEDDING_DIR, exist_ok=True)
        print("Embedding model loaded")

    def embed(self, chunks: List[Dict]) -> Dict:
        """
        Input:
            List of chunk dictionaries

        Output:
            embedding file saved + metadata
        """

        if not chunks:
            raise ValueError("No chunks provided for embedding")

        document_id = chunks[0]["document_id"]

        print(f"Generating embeddings for document {document_id}")

        # -------- Extract text --------
        texts = [chunk["chunk_text"] for chunk in chunks]

        # -------- Generate vectors --------
        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True
        )

        # -------- Build storage payload --------
        records = []

        for chunk, vector in zip(chunks, vectors):
            record = {
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "file_name": chunk["file_name"],
                "page_number": chunk["page_number"],
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"],
                "chunk_text": chunk["chunk_text"],
                "embedding": vector.tolist()  # numpy -> json
            }

            records.append(record)

        # -------- Save to disk --------
        out_path = os.path.join(EMBEDDING_DIR, f"{document_id}.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f)

        print(f"Embeddings stored at {out_path}")

        return records