from urllib import request
from httpx import request

from fastapi import APIRouter
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.generation.generation_service import GenerationService
from pydantic import BaseModel

router = APIRouter()

retriever = RetrievalService()
generator = GenerationService()

class QueryRequest(BaseModel):
    document_id: str
    question: str

@router.post("")
def query_docs(request: QueryRequest):

    # Retrieve relevant chunks
    retrieval_result = retriever.search(request.document_id, request.question)
    retrieved_chunks = retrieval_result["matches"]

    # Safety: no context found
    if not retrieved_chunks:
        return {
            "answer": "I could not find relevant information in the document.",
            "sources": []
        }

    # Send context to LLM
    answer = generator.generate(request.question, retrieved_chunks)

    # remove duplicate citations
    unique_sources = {}
    for chunk in retrieved_chunks:
        key = (chunk["file_name"], chunk["page_number"])
        unique_sources[key] = {
            "file_name": chunk["file_name"],
            "page_number": chunk["page_number"]
        }

    sources = list(unique_sources.values())

    return {
        "question": request.question,
        "answer": answer,
        "sources": sources
    }