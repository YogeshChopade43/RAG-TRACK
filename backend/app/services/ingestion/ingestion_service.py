from app.services.parsing.parsing_service import ParsingService
# from app.services.chunking.chunking_service import ChunkingService
# from app.services.embedding.embedding_service import EmbeddingService
# from app.services.storage.vector_store import VectorStore

parsing_service = ParsingService()
# chunking_service = ChunkingService()
# embedding_service = EmbeddingService()
# vector_store = VectorStore()

def ingest(document_id: str, filename: str):
    """
    Orchestrates the ingestion pipeline for a document.
    Input: document_id (already uploaded & stored)
    """
    doc_id = document_id
    fname = filename

    # 1. Parse raw file into text
    text = parsing_service.parse(doc_id)
    print(f"Parsed text for document {doc_id}: {text}")

"""
    # 2. Chunk parsed text
    chunks = chunking_service.chunk(text)

    # 3. Generate embeddings
    embeddings = embedding_service.embed(chunks)

    # 4. Store embeddings with metadata
    vector_store.store(
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings
    )
"""
    # return {
    #     "document_id": doc_id,
    #     "chunks": len(chunks)
    # }
