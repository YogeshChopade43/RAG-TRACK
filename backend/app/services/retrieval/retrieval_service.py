import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import VECTOR_STORE_DIR, MODEL_NAME


class RetrievalService:
    """
    Handles semantic retrieval for a specific document.
    Loads only the document's vector store instead of all documents.
    """

    def __init__(self):
        print("🔎 Initializing Retrieval Service...")
        self.model = SentenceTransformer(MODEL_NAME)

    # -----------------------------
    # Load a single document store
    # -----------------------------
    def _load_document_store(self, document_id: str):
        """
        Loads embeddings for a specific document.
        Returns list of chunk objects.
        """

        doc_store_path = os.path.join(VECTOR_STORE_DIR, f"{document_id}.json")

        if not os.path.exists(doc_store_path):
            print(f"⚠️ No vector store found for document: {document_id}")
            return []

        with open(doc_store_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert embeddings to numpy arrays (VERY IMPORTANT for speed)
        for item in data:
            item["embedding"] = np.array(item["embedding"], dtype=np.float32)

        print(f"📚 Loaded {len(data)} chunks for document {document_id}")
        return data

    # -----------------------------
    # Cosine similarity
    # -----------------------------
    def _cosine_similarity(self, a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    # -----------------------------
    # Main search function
    # -----------------------------
    def search(self, document_id: str, query: str, top_k: int = 3):
        """
        Performs semantic search inside ONE document.
        """

        # 1️⃣ Load document embeddings
        vector_store = self._load_document_store(document_id)

        if not vector_store:
            return {
                "matches": [],
                "message": "No embeddings found for this document. Upload and ingest first."
            }

        # 2️⃣ Convert query → embedding
        print("🧠 Encoding query...")
        query_embedding = self.model.encode(query)
        query_embedding = np.array(query_embedding, dtype=np.float32)

        # 3️⃣ Compare with all chunks
        scores = []
        for item in vector_store:
            similarity = self._cosine_similarity(query_embedding, item["embedding"])
            scores.append((similarity, item))

        # 4️⃣ Sort by best semantic match
        scores.sort(key=lambda x: x[0], reverse=True)

        # 5️⃣ Prepare response
        results = []
        for score, item in scores[:top_k]:
            results.append({
                "score": round(score, 4),
                "chunk_text": item["chunk_text"],
                "file_name": item["file_name"],
                "page_number": item["page_number"],
                "chunk_id": item["chunk_id"]
            })

        print(f"✅ Retrieved {len(results)} relevant chunks")
        return {"matches": results}