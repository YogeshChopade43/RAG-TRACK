"""
Per-document endpoints: retrieval settings (applied from auto-tune) and stress tests.

Owner only: these change how a document answers or spend the owner's model credit.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel

from app.api.retrieve import (
    get_generation_service,
    get_multi_query_service,
    get_query_decomposition_service,
    get_query_rewrite_service,
    get_retriever,
)
from app.core.auth import require_document_owner
from app.core.config import settings
from app.core.ratelimit import limiter
from app.services.doc_settings import DocSettings
from app.services.generic import file_storage
from app.services.ingestion import jobs as ingest_jobs
from app.services.pipeline import Services
from app.services.stress import jobs

router = APIRouter()

# Document ids become file paths: accept UUIDs only (422 otherwise)
DocId = Path(pattern=r"^[a-f0-9-]{36}$")


@router.get("/{document_id}/settings")
async def get_settings(request: Request, document_id: str = DocId):
    require_document_owner(document_id, request)
    saved = file_storage.get_doc_settings(document_id)
    return {
        "settings": saved.model_dump() if saved else None,
        "defaults": {"top_k": settings.top_k_retrieval, "min_relevance": settings.jev_min_relevance},
    }


@router.put("/{document_id}/settings")
async def put_settings(body: DocSettings, request: Request, document_id: str = DocId):
    require_document_owner(document_id, request)
    file_storage.save_doc_settings(document_id, body)
    return {"settings": body.model_dump()}


@router.delete("/{document_id}/settings")
async def reset_settings(request: Request, document_id: str = DocId):
    require_document_owner(document_id, request)
    file_storage.delete_doc_settings(document_id)
    return {"settings": None}


# --- stress tests -------------------------------------------------------------

class StressTestRequest(BaseModel):
    size: Literal[10, 20, 50] = 20


@router.post("/{document_id}/stress-tests")
@limiter.limit("5/hour")
async def start_stress_test(
    body: StressTestRequest,
    request: Request,
    document_id: str = DocId,
    retriever=Depends(get_retriever),
    rewriter=Depends(get_query_rewrite_service),
    decomposer=Depends(get_query_decomposition_service),
    multi_query=Depends(get_multi_query_service),
    generator=Depends(get_generation_service),
):
    require_document_owner(document_id, request)
    if ingest_jobs.is_processing(document_id):
        raise HTTPException(status_code=409, detail="Document is still processing")
    # The user's own key only: a run is hundreds of model calls, never billed to the server's key
    api_key = request.headers.get("X-User-OpenRouter-Key", "").strip() or None
    if not api_key:
        raise HTTPException(status_code=400, detail="Connect your own OpenRouter key to run a stress test.")
    run_id = jobs.start_run(
        document_id, body.size,
        api_key=api_key,
        model=request.headers.get("X-User-OpenRouter-Model", "").strip() or None,
        services=Services(retriever, rewriter, decomposer, multi_query, generator),
    )
    return {"run_id": run_id}


@router.get("/{document_id}/stress-tests")
async def list_stress_tests(request: Request, document_id: str = DocId):
    require_document_owner(document_id, request)
    return jobs.list_reports(document_id)


@router.get("/{document_id}/stress-tests/{run_id}")
async def get_stress_test(run_id: str, request: Request, document_id: str = DocId):
    require_document_owner(document_id, request)
    report = jobs.load_report(document_id, run_id) if run_id.isalnum() else None
    if report is None:
        raise HTTPException(status_code=404, detail="Stress test not found")
    return report
