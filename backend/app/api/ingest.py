from fastapi import APIRouter, UploadFile, HTTPException
import uuid

from app.core.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.services.generic.file_storage import save_raw_file
from app.services.ingestion.ingestion_service import ingest

router = APIRouter()

@router.post("/")
async def ingest_document(file: UploadFile):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    extension = file.filename.split(".")[-1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    raw_content = await file.read()
    size_mb = len(raw_content) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large")

    document_id = str(uuid.uuid4())

    save_raw_file(
        document_id=document_id,
        filename=file.filename,
        content=raw_content
    )

    # Trigger ingestion pipeline
    parsed_text = ingest(document_id,filename=file.filename)            # Parsed test returning for now, Later will return full data with chunks, embeddings, etc.

    return {
        "document_id": document_id,
        "filename": file.filename,
        "content": parsed_text
    }
