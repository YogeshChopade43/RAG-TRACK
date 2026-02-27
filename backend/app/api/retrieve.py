from fastapi import APIRouter
from app.services.retrieval.retrieval_service import RetrievalService

router = APIRouter()


@router.post("/query")
def query_docs(document_id: str, question: str):
    retriever = RetrievalService()
    results = retriever.search(document_id, question)
    return {"matches": results}