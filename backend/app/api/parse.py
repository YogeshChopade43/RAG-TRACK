from fastapi import APIRouter, HTTPException
from app.services.parsing.parsing_service import ParsingService

router = APIRouter()
service = ParsingService()

@router.post("/{document_id}")
def parse_document(document_id: str):
    try:
        return service.parse(document_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
