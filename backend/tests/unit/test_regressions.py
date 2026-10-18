"""
Regression tests for bugs fixed in the October 2026 clean-up.
"""
from unittest.mock import patch

import pytest

from app.core.exceptions import IngestionError
from app.core.security import create_access_token
from app.services.chunking.chunking_service import ChunkingService

DOC_ID = "550e8400-e29b-41d4-a716-446655440000"


def test_sentences_keep_single_punctuation_and_spaces():
    service = ChunkingService()
    assert service._split_into_sentences("One here. Two there! Three?! Version 2.5 is out") == [
        "One here.", "Two there!", "Three?!", "Version 2.5 is out",
    ]
    chunks = service.chunk({
        "document_id": "d", "file_name": "f.txt",
        "pages": [{"page_number": 1, "text": "Alpha beta gamma. " * 40}],
    })
    assert len(chunks) > 1
    assert all(".." not in c["chunk_text"] for c in chunks)
    assert "gamma. Alpha" in chunks[0]["chunk_text"]
    assert all(len(c["chunk_text"]) <= service.chunk_size for c in chunks)


def test_scanned_pdf_returns_400_with_parser_message(mock_client):
    err = IngestionError("Failed to parse document", stage="parsing")
    err.__cause__ = ValueError("This PDF appears to be image-based (scanned)")
    with patch("app.api.ingest.save_raw_file"), patch("app.api.ingest.ingest", side_effect=err):
        res = mock_client.post("/ingest", files={"file": ("scan.pdf", b"%PDF", "application/pdf")})

    assert res.status_code == 400
    assert "scanned" in res.json()["detail"]


def test_unexpected_ingestion_error_is_500(mock_client):
    err = IngestionError("boom")
    err.__cause__ = RuntimeError("disk full")
    with patch("app.api.ingest.save_raw_file"), patch("app.api.ingest.ingest", side_effect=err):
        res = mock_client.post("/ingest", files={"file": ("a.txt", b"x", "text/plain")})

    assert res.status_code == 500


def test_full_evaluation_overall_score():
    from app.evaluation.dataset import EvalDataset
    from app.evaluation.runner import EvaluationRunner

    runner = EvaluationRunner()
    perfect = {"aggregated_metrics": {"precision@5": 1.0, "recall@5": 1.0, "ndcg@5": 1.0}}
    with patch.object(runner, "run_retrieval_evaluation", return_value=perfect), \
         patch.object(runner, "run_pipeline_evaluation", return_value={"aggregated_metrics": {"error_rate": 0.5}}):
        report = runner.run_full_evaluation(EvalDataset())

    # retrieval 1.0 (weight 0.4) + reliability 0.5 (weight 0.2), renormalized over 0.6
    assert report.overall_score == pytest.approx((1.0 * 0.4 + 0.5 * 0.2) / 0.6)


def test_trace_cleanup_loop_deletes_old_traces():
    import asyncio

    from app.main import _trace_cleanup_loop

    async def run_inline(func, *args):  # no worker thread needed in a test
        return func(*args)

    with patch(
        "app.services.observability.trace_storage.TraceStorage.cleanup_old_traces", return_value=0
    ) as cleanup, patch("app.main.asyncio.to_thread", side_effect=run_inline), \
            patch("app.main.asyncio.sleep", side_effect=asyncio.CancelledError):
        coro = _trace_cleanup_loop()
        with pytest.raises(asyncio.CancelledError):  # stop the loop at its first daily sleep
            coro.send(None)  # drive the coroutine directly: no event loop, no threads

    # Whatever TRACE_RETENTION_DAYS is configured to (env or .env), not a hard-coded 7
    from app.core.config import settings

    cleanup.assert_called_once_with(settings.trace_retention_days)


def test_trace_cleanup_uses_real_file_age_regardless_of_timezone(tmp_path, monkeypatch):
    import os
    import time

    from app.services.observability.trace_storage import TraceStorage

    monkeypatch.setattr(TraceStorage, "_get_traces_dir", staticmethod(lambda: str(tmp_path)))
    day = 24 * 3600
    old = tmp_path / "old.json"
    fresh = tmp_path / "fresh.json"
    for f in (old, fresh):
        f.write_text("{}")
    now = time.time()
    os.utime(old, (now - 7 * day - 60, now - 7 * day - 60))  # just past 7 days
    os.utime(fresh, (now - 7 * day + 3600, now - 7 * day + 3600))  # an hour inside 7 days

    assert TraceStorage.cleanup_old_traces(retention_days=7) == 1
    assert not old.exists()
    assert fresh.exists()


@pytest.fixture
def owned_document(tmp_path, monkeypatch):
    from app.services.generic import file_storage

    monkeypatch.setattr(file_storage, "owner_path", lambda doc_id: tmp_path / f"{doc_id}.txt")
    file_storage.save_owner(DOC_ID, "user-a")


def _auth(user_id):
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


@pytest.mark.parametrize("headers,expected", [
    ({}, 404),  # anonymous
    (_auth("user-b"), 404),  # someone else
])
def test_owned_document_hidden_from_others(mock_client, owned_document, headers, expected):
    res = mock_client.post("/query", json={"document_id": DOC_ID, "question": "what is this?"}, headers=headers)
    assert res.status_code == expected
    assert mock_client.get(f"/ingest/{DOC_ID}", headers=headers).status_code == 404


def test_owner_can_query_own_document(mock_client, owned_document):
    res = mock_client.post(
        "/query", json={"document_id": DOC_ID, "question": "what is this?"}, headers=_auth("user-a")
    )
    assert res.status_code == 200  # no index exists, so it answers "could not find"
