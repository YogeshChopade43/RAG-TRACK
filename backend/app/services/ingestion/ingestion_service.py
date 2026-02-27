from app.services.parsing.parsing_service import ParsingService
from app.services.chunking.chunking_service import ChunkingService
from app.services.embedding.embedding_service import EmbeddingService
# from app.services.storage.vector_store import VectorStore
from app.services.generic.utils.parser_utils import get_page_text
from app.services.generic.update_vector_store import save_document_vector_store
import json
parsing_service = ParsingService()
chunking_service = ChunkingService()
embedding_service = EmbeddingService()
# vector_store = VectorStore()

def ingest(document_id: str, filename: str):
    """
    Orchestrates the ingestion pipeline for a document.
    Input: document_id (already uploaded & stored)
    """
    doc_id = document_id
    fname = filename

    # 1. Parse raw file into text and clean extracted text
    parsed_load = parsing_service.parse(doc_id)
    print(f"🎀 Parsed text for document {doc_id}: {parsed_load}\n")                      
#    get_page_text(parsed_load["pages"])
                    

    # 2. Chunk parsed text
    chunks = chunking_service.chunk(parsed_load)
    print(f"🎀 Length of chunks for document : {len(chunks)}\n")
    print(f"🎀 Chunks for document {doc_id}: {chunks}\n")
    
    # 3. Generate embeddings
    embedded_chunks = embedding_service.embed(chunks)
    print(f"🎀 Embeddings for document {fname}: {len(embedded_chunks)} chunks\n")

    # 4. Save into retriever vector store
    save_document_vector_store(doc_id, embedded_chunks)
    print(f"🎀 Updated vector store with embeddings for document {fname}")
        
    return parsed_load

