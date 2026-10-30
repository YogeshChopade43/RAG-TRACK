"""
Background ingestion: uploads are processed one at a time per process, off the
event loop, with each stage mirrored to data/ingest_status/<id>.json so the
frontend can show real progress.
"""
import asyncio
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.core.exceptions import IngestionError
from app.services.ingestion.ingestion_service import ingest

logger = logging.getLogger(__name__)

FINAL = ("ready", "failed")
GENERIC_ERROR = "Failed to process document"
INTERRUPTED = "Processing was interrupted (server restarted). Please upload again."

_tasks: dict[str, Any] = {}
# This process's statuses (the disk copy serves restarts); written from the executor thread too
_status: dict[str, dict[str, Any]] = {}
_status_lock = threading.Lock()
# ponytail: one in-process lock = one ingestion at a time per worker process; a job queue if several workers
_lock: Optional[asyncio.Lock] = None
_lock_loop: Optional[asyncio.AbstractEventLoop] = None


def status_dir() -> Path:
    return settings.data_dir / "ingest_status"


def _path(document_id: str) -> Path:
    return status_dir() / f"{document_id}.json"


def _read(document_id: str) -> Optional[dict[str, Any]]:
    with _status_lock:
        if document_id in _status:
            return dict(_status[document_id])
    return _read_disk(document_id)


def _write(document_id: str, **fields: Any) -> None:
    """Update the in-memory status (read by this process) and mirror it to disk atomically."""
    with _status_lock:
        current = _status.get(document_id) or _read_disk(document_id) or {
            "document_id": document_id, "status": "queued", "error": None, "pages": None,
        }
        current.update(fields)
        _status[document_id] = current
        data = json.dumps(current)
    path = _path(document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{threading.get_ident()}.tmp")
    tmp.write_text(data, encoding="utf-8")
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: a reader has the file open
            time.sleep(0.02 * (attempt + 1))
    tmp.unlink(missing_ok=True)
    logger.warning(f"[{document_id}] Could not mirror ingest status to disk")


def _read_disk(document_id: str) -> Optional[dict[str, Any]]:
    try:
        return json.loads(_path(document_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _live(document_id: str) -> bool:
    task = _tasks.get(document_id)
    return task is not None and not task.done()


def get_status(document_id: str) -> Optional[dict[str, Any]]:
    status = _read(document_id)
    if status and status["status"] not in FINAL and not _live(document_id):
        # Written by a worker that no longer exists (server restarted mid-ingest)
        return {**status, "status": "failed", "error": INTERRUPTED}
    return status


def is_processing(document_id: str) -> bool:
    status = _read(document_id)
    return bool(status) and status["status"] not in FINAL and _live(document_id)


def delete_status(document_id: str) -> None:
    with _status_lock:
        _status.pop(document_id, None)
    _path(document_id).unlink(missing_ok=True)


def _get_lock() -> asyncio.Lock:
    global _lock, _lock_loop
    loop = asyncio.get_running_loop()
    if _lock is None or _lock_loop is not loop:
        _lock, _lock_loop = asyncio.Lock(), loop
    return _lock


async def _run(document_id: str, filename: str) -> None:
    async with _get_lock():
        def on_stage(stage: str, **info: Any) -> None:
            _write(document_id, status=stage, **info)

        try:
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: ingest(document_id, filename, on_stage=on_stage)
            )
        except IngestionError as e:
            # A ValueError underneath means bad input (e.g. an unreadable file): show its message
            error = str(e.__cause__) if isinstance(e.__cause__, ValueError) else GENERIC_ERROR
            logger.warning(f"[{document_id}] Ingestion failed: {e}")
            _write(document_id, status="failed", error=error)
        except Exception:
            logger.exception(f"[{document_id}] Ingestion failed")
            _write(document_id, status="failed", error=GENERIC_ERROR)
        else:
            _write(document_id, status="ready")


def start(document_id: str, filename: str) -> None:
    """Queue a saved upload for ingestion; returns immediately."""
    _write(document_id, status="queued", error=None, pages=None)
    _tasks[document_id] = asyncio.create_task(_run(document_id, filename))
