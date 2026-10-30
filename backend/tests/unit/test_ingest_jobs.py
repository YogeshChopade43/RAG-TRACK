"""Background ingestion: stages, failures, one-at-a-time, restart, and the endpoints that must wait."""
import asyncio
import json
import threading
from unittest.mock import patch

import pytest

from app.core.exceptions import IngestionError
from app.services.ingestion import jobs

DOC_ID = "550e8400-e29b-41d4-a716-446655440010"


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "status_dir", lambda: tmp_path / "ingest_status")
    jobs._tasks.clear()
    jobs._status.clear()
    yield tmp_path
    jobs._tasks.clear()
    jobs._status.clear()


def all_stages(document_id, filename, on_stage=None):
    on_stage("parsing")
    on_stage("chunking", pages=2)
    on_stage("embedding")
    return {"chunks_count": 3}


async def drain():
    while any(not t.done() for t in jobs._tasks.values()):
        await asyncio.sleep(0.01)


def test_stages_reach_ready():
    seen = []
    real_write = jobs._write

    def spy(document_id, **fields):
        seen.append(fields["status"])
        real_write(document_id, **fields)

    async def main():
        with patch.object(jobs, "ingest", all_stages), patch.object(jobs, "_write", spy):
            jobs.start("doc-1", "a.pdf")
            await drain()

    asyncio.run(main())
    assert seen == ["queued", "parsing", "chunking", "embedding", "ready"]
    assert jobs.get_status("doc-1") == {"document_id": "doc-1", "status": "ready", "error": None, "pages": 2}


def test_value_error_becomes_failed_with_message():
    def bad(document_id, filename, on_stage=None):
        on_stage("parsing")
        try:
            raise ValueError("Couldn't read this file. It may be corrupt or password-protected.")
        except ValueError as e:
            raise IngestionError(message="Failed to parse document", stage="parsing", document_id=document_id) from e

    async def main():
        with patch.object(jobs, "ingest", bad):
            jobs.start("doc-2", "a.pdf")
            await drain()

    asyncio.run(main())
    s = jobs.get_status("doc-2")
    assert s["status"] == "failed" and s["error"].startswith("Couldn't read this file")


def test_unexpected_error_hides_details():
    def boom(document_id, filename, on_stage=None):
        raise RuntimeError("C:\\secret\\path exploded")

    async def main():
        with patch.object(jobs, "ingest", boom):
            jobs.start("doc-3", "a.pdf")
            await drain()

    asyncio.run(main())
    assert jobs.get_status("doc-3")["error"] == "Failed to process document"


def test_second_upload_waits_for_first():
    release = threading.Event()

    def slow(document_id, filename, on_stage=None):
        if document_id == "a":
            release.wait(5)
        return all_stages(document_id, filename, on_stage)

    async def main():
        with patch.object(jobs, "ingest", slow):
            jobs.start("a", "a.pdf")
            jobs.start("b", "b.pdf")
            await asyncio.sleep(0.1)
            assert jobs.get_status("b")["status"] == "queued"
            assert jobs.is_processing("b")
            release.set()
            await drain()

    asyncio.run(main())
    assert jobs.get_status("b")["status"] == "ready"
    assert not jobs.is_processing("b")


def test_orphaned_status_reads_failed(storage):
    (storage / "ingest_status").mkdir()
    (storage / "ingest_status" / "x.json").write_text(
        json.dumps({"document_id": "x", "status": "parsing", "error": None, "pages": None}), encoding="utf-8"
    )
    s = jobs.get_status("x")
    assert s["status"] == "failed"
    assert s["error"] == "Processing was interrupted (server restarted). Please upload again."
    assert not jobs.is_processing("x")


def test_unknown_document_has_no_status():
    assert jobs.get_status("nope") is None
    assert not jobs.is_processing("nope")


# --- endpoints ----------------------------------------------------------------

@pytest.fixture
def client(mock_client):
    return mock_client


def test_upload_returns_processing_and_queues(client):
    with patch("app.api.ingest.save_raw_file"), patch("app.api.ingest.jobs.start") as start:
        r = client.post("/ingest", files={"file": ("cv.docx", b"x", "application/octet-stream")})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "processing" and body["filename"] == "cv.docx"
    start.assert_called_once_with(body["document_id"], "cv.docx")


def test_status_endpoint(client, storage):
    jobs._write(DOC_ID, status="chunking", pages=4)
    jobs._tasks[DOC_ID] = _LiveTask()
    r = client.get(f"/ingest/{DOC_ID}/status")
    assert r.status_code == 200
    assert r.json() == {"document_id": DOC_ID, "status": "chunking", "error": None, "pages": 4}


def test_status_for_pre_docling_upload_is_ready(client, storage, tmp_path, monkeypatch):
    from app.core.config import settings

    raw = settings.raw_dir / DOC_ID
    raw.mkdir(parents=True, exist_ok=True)
    try:
        assert client.get(f"/ingest/{DOC_ID}/status").json()["status"] == "ready"
    finally:
        raw.rmdir()


def test_status_unknown_and_invalid(client):
    assert client.get(f"/ingest/{DOC_ID}/status").status_code == 404
    assert client.get("/ingest/not-a-uuid/status").status_code == 400


@pytest.mark.parametrize("call", [
    lambda c: c.post("/query", json={"document_id": DOC_ID, "question": "What is this?"}),
    lambda c: c.post(f"/documents/{DOC_ID}/stress-tests", json={"size": 10},
                     headers={"X-User-OpenRouter-Key": "sk-or-x"}),
    lambda c: c.delete(f"/ingest/{DOC_ID}"),
])
def test_busy_document_returns_409(client, call):
    with patch("app.services.ingestion.jobs.is_processing", return_value=True), \
         patch("app.api.documents.require_document_owner"):
        r = call(client)
    assert r.status_code == 409
    assert r.json()["detail"] == "Document is still processing"


def test_delete_removes_status_file(client, storage):
    jobs._write(DOC_ID, status="ready")
    assert client.delete(f"/ingest/{DOC_ID}").status_code == 200
    assert jobs.get_status(DOC_ID) is None


class _LiveTask:
    def done(self):
        return False


def test_status_reads_never_see_a_half_written_file():
    """Stage writes come from the executor thread while polls read on the loop."""
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            jobs._write("race", status=("parsing", "chunking", "embedding")[i % 3], pages=i)
            i += 1

    jobs._write("race", status="queued")
    jobs._tasks["race"] = _LiveTask()
    t = threading.Thread(target=writer)
    t.start()
    try:
        for _ in range(3000):
            assert jobs.get_status("race")["status"] in ("queued", "parsing", "chunking", "embedding")
    finally:
        stop.set()
        t.join()
