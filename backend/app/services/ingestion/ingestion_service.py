from app.services.parsing.parsing_service import ParsingService
from app.services.chunking.chunking_service import ChunkingService
# from app.services.text_cleaning.text_cleaning_service import TextCleaningService
# from app.services.embedding.embedding_service import EmbeddingService
# from app.services.storage.vector_store import VectorStore
from app.services.generic.utils.parser_utils import get_page_text

parsing_service = ParsingService()
chunking_service = ChunkingService()
# text_cleaning_service = TextCleaningService()
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
    parsed_load = parsing_service.parse(doc_id)
    print(f"😐 Parsed text for document {doc_id}: {parsed_load}\n")                      
#    get_page_text(parsed_load["pages"])

#    return parsed_load                          

    # 2. Chunk parsed text
    chunks = chunking_service.chunk(parsed_load)
    print(f"😐 Length of chunks for document : {len(chunks)}\n")
    print(f"😐 Chunks for document {doc_id}: {chunks}\n")
    
    return parsed_load

# ==============================================================================
# Next thing is Text cleaning / normalization pipeline to clean document noise before chunking. This will be part of separate service.
# ==============================================================================


"""
    # 4. Generate embeddings
    embeddings = embedding_service.embed(chunks)

    # 5. Store embeddings in vector database
    vector_store.store(
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings
    )
"""

    # return {
    #     "parsed": parsed_load,
    #     "chunks": chunked_load,
    #     "embeddings": embedding_load,
    #     "storage": storage_load
    # }
    
