from fastapi import APIRouter, HTTPException
from backend.app.services.ingestion.ingestion_service import ingest

router = APIRouter()

@router.post("/{document_id}")
def ingest_document(document_id: str):
    try:
        return ingest(document_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
