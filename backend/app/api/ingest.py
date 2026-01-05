from fastapi import APIRouter, UploadFile, HTTPException
import uuid

from app.core.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.services.file_storage import save_raw_file
from app.services.metadata_services import create_raw_metadata
from app.services.parsing_service import ParsingService
from app.services.trace_service import TraceService

trace_service = TraceService()
router = APIRouter()
parsing_service = ParsingService()

@router.post("/")
async def ingest(file: UploadFile):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    extension = file.filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large")

    document_id = str(uuid.uuid4())

    trace_service.create_trace(
        document_id=document_id,
        filename=file.filename,
        file_type=extension,
        size_mb=round(size_mb, 2)
    )

    storage_path = save_raw_file(
        document_id=document_id,
        filename=file.filename,
        content=content
    )

    metadata = create_raw_metadata(
        document_id=document_id,
        filename=file.filename,
        source_type=extension,
        size_mb=round(size_mb, 2),
        storage_path=storage_path,
    )


    parsing_service.parse(document_id)


    trace_service.add_artifact(
        document_id,
        "raw_path",
        storage_path
    )

    trace_service.update_stage(
        document_id,
        stage="ingestion",
        payload={
            "storage_path": storage_path,
            "status": "SUCCESS"
        }
    )



    return metadata
