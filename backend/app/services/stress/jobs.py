"""
Stress-test jobs: generate questions, run each through the real pipeline, grade, auto-tune,
validate the best settings with a real re-run, and keep a JSON report on disk.

One job per document at a time. The report is rewritten after every step so progress survives
a page reload. The user's API key lives only in the job's arguments; it is never written to
the report, traces or logs.
"""
import asyncio
import json
import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.services.doc_settings import DocSettings
from app.services.generic import file_storage
from app.services.pipeline import answer_question
from app.services.stress.generate import StressError, generate_items
from app.services.stress.grade import grade_item, summarize
from app.services.stress.tune import best_settings, should_recommend

logger = logging.getLogger(__name__)

# document_id -> running asyncio.Task (or anything with .done())
_active: dict[str, Any] = {}

FINAL = ("done", "failed")


def stress_dir() -> Path:
    return settings.data_dir / "stress_tests"


def _path(document_id: str, run_id: str) -> Path:
    return stress_dir() / document_id / f"{run_id}.json"


def _save(report: dict[str, Any]) -> None:
    path = _path(report["document_id"], report["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, default=str), encoding="utf-8")
    tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_running(document_id: str) -> bool:
    task = _active.get(document_id)
    return task is not None and not task.done()


def _current_settings(document_id: str) -> tuple[Optional[DocSettings], dict[str, Any]]:
    saved = file_storage.get_doc_settings(document_id)
    used = (
        {"top_k": saved.top_k, "min_relevance": saved.min_relevance, "source": "document"}
        if saved
        else {"top_k": settings.top_k_retrieval, "min_relevance": settings.jev_min_relevance, "source": "default"}
    )
    return saved, used


def new_report(document_id: str, size: int) -> str:
    run_id = uuid.uuid4().hex[:12]
    _, used = _current_settings(document_id)
    _save({
        "run_id": run_id, "document_id": document_id, "size": size, "status": "generating",
        "progress": {"done": 0, "total": size}, "started_at": _now(), "finished_at": None,
        "settings_used": used, "summary": None, "items": [], "tune": None, "error": None,
    })
    return run_id


async def _run_items(document_id, items, *, api_key, model, services, overrides, on_item=None) -> list[dict]:
    graded = []
    for item in items:
        try:
            result = await answer_question(
                document_id, item["question"], services=services, api_key=api_key, model=model,
                overrides=overrides, use_cache=False,
            )
            g = await asyncio.to_thread(grade_item, item, result, api_key=api_key)
        except HTTPException as e:
            # 400: the safety filter blocked a generated question. Anything else: the pipeline
            # failed on this question. Record it and keep going; one bad question shouldn't sink the run
            blocked = e.status_code == 400
            g = {**item, "answer": None, "answer_status": "blocked" if blocked else "error",
                 "correct": False if blocked else None, "retrieval_hit": False if blocked else None,
                 "hallucinated": False, "trace_id": None, "candidates": [], "grade_score": None,
                 "cost_usd": None, "tokens": None}
        graded.append(g)
        if on_item:
            on_item(graded)
    return graded


async def run_job(document_id: str, run_id: str, size: int, *, api_key, model, services) -> None:
    report = json.loads(_path(document_id, run_id).read_text(encoding="utf-8"))
    current, _ = _current_settings(document_id)
    try:
        items = await asyncio.to_thread(generate_items, document_id, size, api_key=api_key, model=model)
        report.update(status="running", progress={"done": 0, "total": len(items)})
        _save(report)

        def progress(graded):
            report["items"] = graded
            report["progress"]["done"] = len(graded)
            _save(report)

        graded = await _run_items(document_id, items, api_key=api_key, model=model, services=services,
                                  overrides=current, on_item=progress)
        errored = sum(1 for g in graded if g["answer_status"] == "error")
        if errored > len(graded) / 2:
            raise StressError(f"{errored} of {len(graded)} questions errored in the pipeline; try again later.")
        report["summary"] = summarize(graded)
        report["status"] = "tuning"
        _save(report)

        cur = (report["settings_used"]["min_relevance"], report["settings_used"]["top_k"])
        best = best_settings(graded, cur)
        if best is None:
            report["tune"] = {"available": False, "best": None, "validation": None, "recommend": False,
                              "reason": "Jev relevance scores were missing for too many questions to tune."}
        elif best == cur:
            report["tune"] = {"available": True, "best": {"min_relevance": cur[0], "top_k": cur[1]},
                              "validation": None, "recommend": False,
                              "reason": "Your current settings are already the best found."}
        else:
            report["status"] = "validating"
            _save(report)
            candidate = DocSettings(min_relevance=best[0], top_k=best[1])
            validated = await _run_items(document_id, items, api_key=api_key, model=model, services=services,
                                         overrides=candidate)
            val = summarize(validated)
            recommend = should_recommend(report["summary"], val)
            report["tune"] = {
                "available": True, "best": {"min_relevance": best[0], "top_k": best[1]},
                "validation": {k: val[k] for k in ("correct", "hallucinations", "retrieval_hits", "cost_usd")},
                "recommend": recommend,
                "reason": None if recommend else "The best replayed settings didn't improve real answers.",
            }
        report.update(status="done", finished_at=_now())
    except Exception as e:  # any failure ends the run with a message; finished items are kept
        logger.warning(f"[{document_id}] stress test {run_id} failed: {e}")
        report.update(status="failed", error=str(e)[:500], finished_at=_now())
    finally:
        _save(report)
        _active.pop(document_id, None)


def start_run(document_id: str, size: int, *, api_key, model, services) -> str:
    if is_running(document_id):
        raise HTTPException(status_code=409, detail="A stress test is already running for this document.")
    run_id = new_report(document_id, size)
    _active[document_id] = asyncio.create_task(
        run_job(document_id, run_id, size, api_key=api_key, model=model, services=services)
    )
    return run_id


def load_report(document_id: str, run_id: str) -> Optional[dict[str, Any]]:
    path = _path(document_id, run_id)
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    if report["status"] not in FINAL and not is_running(document_id):
        # Nothing is working on it (e.g. the server restarted mid-run)
        report.update(status="failed", error="The run was interrupted (server restart).", finished_at=_now())
        _save(report)
    return report


def list_reports(document_id: str) -> list[dict[str, Any]]:
    folder = stress_dir() / document_id
    if not folder.exists():
        return []
    reports = [load_report(document_id, p.stem) for p in folder.glob("*.json")]
    keys = ("run_id", "status", "size", "started_at", "finished_at", "summary", "settings_used")
    rows = [{k: r.get(k) for k in keys} for r in reports if r]
    return sorted(rows, key=lambda r: r["started_at"] or "", reverse=True)


def cleanup_old_reports(retention_days: int) -> int:
    """Reports contain document text (questions, answers): delete them with the traces."""
    root = stress_dir()
    if retention_days <= 0 or not root.exists():
        return 0
    cutoff = time.time() - retention_days * 24 * 3600
    removed = 0
    for path in root.glob("*/*.json"):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def delete_document_reports(document_id: str) -> None:
    shutil.rmtree(stress_dir() / document_id, ignore_errors=True)
