"""Stress-test jobs: lifecycle, report storage, failure handling, key safety, endpoints."""
import asyncio
import json
import os
import time
from unittest.mock import patch

import pytest

from app.core.security import create_access_token
from app.services.doc_settings import DocSettings
from app.services.generic import file_storage
from app.services.pipeline import QueryResponse, QueryResult
from app.services.stress import jobs

DOC_ID = "550e8400-e29b-41d4-a716-446655440000"
SECRET = "sk-or-SECRET-KEY-123"


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "stress_dir", lambda: tmp_path / "stress")
    monkeypatch.setattr(file_storage, "owner_path", lambda d: tmp_path / "owners" / f"{d}.txt")
    monkeypatch.setattr(file_storage, "doc_settings_path", lambda d: tmp_path / "ds" / f"{d}.json")
    file_storage.save_owner(DOC_ID, "owner")
    jobs._active.clear()
    yield tmp_path
    jobs._active.clear()


ITEMS = [
    {"id": "q1", "kind": "direct", "question": "Who?", "expected_answer": "engineer", "source_chunk_id": "c0", "page_number": 1},
    {"id": "q2", "kind": "unanswerable", "question": "Salary?", "expected_answer": None, "source_chunk_id": None, "page_number": None},
]


def fake_answer(scores_by_bar):
    """answer_question stub: the source chunk c0 is kept only when the bar is <= its score."""
    async def answer(document_id, question, *, overrides=None, **_):
        bar = overrides.min_relevance if overrides else 0.1
        c0 = scores_by_bar
        kept = question == "Who?" and c0 >= bar
        cands = [{"chunk_id": "c0", "jev": c0 if question == "Who?" else 0.01, "status": "kept" if kept else "dropped"}]
        status = "answered" if kept else "not_found"
        resp = QueryResponse(trace_id=f"t-{question}-{bar}", question=question, answer="ans" if kept else "nf",
                             sources=[], answer_status=status,
                             usage={"total_tokens": 10, "cost_usd": 0.0001, "jev_cost_included": True})
        from types import SimpleNamespace
        return QueryResult(response=resp, trace=SimpleNamespace(candidates=cands))
    return answer


def grade(question, expected, answer, api_key=None):
    return 0.9 if answer == "ans" else 0.1  # Jev: only a real answer matches the reference


def run_job(answer):
    with patch("app.services.stress.jobs.generate_items", return_value=[dict(i) for i in ITEMS]), \
         patch("app.services.stress.jobs.answer_question", side_effect=answer), \
         patch("app.services.stress.grade.jev.grade_answer", side_effect=grade):
        run_id = jobs.new_report(DOC_ID, 10)
        asyncio.run(jobs.run_job(DOC_ID, run_id, 10, api_key=SECRET, model="m", services=None))
    return run_id, jobs.load_report(DOC_ID, run_id)


def test_happy_path_recommends_validated_settings(storage):
    # Source chunk scores 0.07: invisible at the default 0.1 bar, found at 0.05
    run_id, report = run_job(fake_answer(0.07))
    assert report["status"] == "done" and report["progress"] == {"done": 2, "total": 2}
    assert report["summary"]["correct"] == 0 and report["summary"]["hallucinations"] == 0
    tune = report["tune"]
    assert tune["available"] and tune["best"] == {"min_relevance": 0.05, "top_k": 8}
    assert tune["validation"]["correct"] == 1 and tune["recommend"] is True


def test_no_recommendation_when_current_is_best(storage):
    _, report = run_job(fake_answer(0.9))
    assert report["tune"]["recommend"] is False and report["tune"]["validation"] is None
    assert "already" in report["tune"]["reason"]


def test_failure_mid_run_keeps_items_and_releases_lock(storage):
    calls = {"n": 0}
    ok = fake_answer(0.9)

    async def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("upstream exploded")
        return await ok(*a, **k)

    run_id, report = run_job(flaky)
    assert report["status"] == "failed" and "upstream exploded" in report["error"]
    assert len(report["items"]) == 1
    assert DOC_ID not in jobs._active


def test_key_never_written_to_the_report(storage):
    run_id, _ = run_job(fake_answer(0.07))
    text = (storage / "stress" / DOC_ID / f"{run_id}.json").read_text(encoding="utf-8")
    assert SECRET not in text


def test_applied_settings_are_used_and_recorded(storage):
    file_storage.save_doc_settings(DOC_ID, DocSettings(top_k=6, min_relevance=0.05))
    _, report = run_job(fake_answer(0.07))
    assert report["settings_used"] == {"top_k": 6, "min_relevance": 0.05, "source": "document"}
    assert report["summary"]["correct"] == 1


def test_orphaned_running_report_reads_as_failed(storage):
    run_id = jobs.new_report(DOC_ID, 10)  # status generating, but no live task (e.g. after a restart)
    assert jobs.load_report(DOC_ID, run_id)["status"] == "failed"


def test_old_reports_are_cleaned_up(storage):
    old = jobs.new_report(DOC_ID, 10)
    path = storage / "stress" / DOC_ID / f"{old}.json"
    past = time.time() - 10 * 24 * 3600
    os.utime(path, (past, past))
    fresh = jobs.new_report(DOC_ID, 10)
    assert jobs.cleanup_old_reports(retention_days=7) == 1
    assert not path.exists() and (storage / "stress" / DOC_ID / f"{fresh}.json").exists()


# --- endpoints -------------------------------------------------------------

def auth(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': user})}", "X-User-OpenRouter-Key": SECRET}


def test_start_rejects_bad_size_and_non_owner(mock_client, storage):
    url = f"/documents/{DOC_ID}/stress-tests"
    assert mock_client.post(url, json={"size": 7}, headers=auth("owner")).status_code == 422
    assert mock_client.post(url, json={"size": 10}, headers=auth("intruder")).status_code == 404


def test_start_returns_409_while_a_run_is_active(mock_client, storage):
    class Running:
        def done(self):
            return False

    jobs._active[DOC_ID] = Running()
    res = mock_client.post(f"/documents/{DOC_ID}/stress-tests", json={"size": 10}, headers=auth("owner"))
    assert res.status_code == 409


def test_reports_are_readable_by_the_owner(mock_client, storage):
    run_id, _ = run_job(fake_answer(0.07))
    listing = mock_client.get(f"/documents/{DOC_ID}/stress-tests", headers=auth("owner")).json()
    assert [r["run_id"] for r in listing] == [run_id] and listing[0]["status"] == "done"
    report = mock_client.get(f"/documents/{DOC_ID}/stress-tests/{run_id}", headers=auth("owner")).json()
    assert report["tune"]["recommend"] is True
    assert mock_client.get(f"/documents/{DOC_ID}/stress-tests/{run_id}", headers=auth("x")).status_code == 404
    assert mock_client.get(f"/documents/{DOC_ID}/stress-tests/nope", headers=auth("owner")).status_code == 404
    json.dumps(report)  # serialisable


def test_a_pipeline_error_on_one_question_does_not_fail_the_run(storage):
    from fastapi import HTTPException

    ok = fake_answer(0.9)

    async def one_bad(document_id, question, **k):
        if question == "Salary?":
            raise HTTPException(status_code=500, detail="Query processing failed")
        return await ok(document_id, question, **k)

    _, report = run_job(one_bad)
    assert report["status"] == "done"
    bad = next(i for i in report["items"] if i["question"] == "Salary?")
    assert (bad["answer_status"], bad["correct"], bad["hallucinated"]) == ("error", None, False)


def test_run_fails_when_most_questions_error(storage):
    from fastapi import HTTPException

    async def all_bad(*a, **k):
        raise HTTPException(status_code=500, detail="Query processing failed")

    _, report = run_job(all_bad)
    assert report["status"] == "failed" and "errored" in report["error"]


def test_stress_tests_require_the_users_own_key(mock_client, storage, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "server-key")
    headers = {"Authorization": auth("owner")["Authorization"]}  # no X-User-OpenRouter-Key
    res = mock_client.post(f"/documents/{DOC_ID}/stress-tests", json={"size": 10}, headers=headers)
    assert res.status_code == 400


def test_document_id_must_be_a_uuid(mock_client, storage):
    assert mock_client.get("/documents/not-a-uuid/settings", headers=auth("owner")).status_code == 422
    assert mock_client.get("/documents/..%5Cowners/stress-tests", headers=auth("owner")).status_code == 422
