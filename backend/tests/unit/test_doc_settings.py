"""Per-document settings: storage, owner-only endpoints, and use by /query."""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import create_access_token
from app.services.doc_settings import DocSettings
from app.services.generic import file_storage
from app.services.pipeline import QueryResponse, QueryResult

DOC_ID = "550e8400-e29b-41d4-a716-446655440000"


def auth(user_id):
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(file_storage, "owner_path", lambda doc_id: tmp_path / "owners" / f"{doc_id}.txt")
    monkeypatch.setattr(file_storage, "doc_settings_path", lambda doc_id: tmp_path / "doc_settings" / f"{doc_id}.json")
    return tmp_path


@pytest.fixture
def owned(storage):
    file_storage.save_owner(DOC_ID, "owner")
    return storage


def test_round_trip(storage):
    assert file_storage.get_doc_settings(DOC_ID) is None
    file_storage.save_doc_settings(DOC_ID, DocSettings(top_k=6, min_relevance=0.05, applied_from_run="r1"))
    assert file_storage.get_doc_settings(DOC_ID).model_dump()["top_k"] == 6
    file_storage.delete_doc_settings(DOC_ID)
    assert file_storage.get_doc_settings(DOC_ID) is None


def test_owner_can_save_read_and_reset(mock_client, owned):
    url = f"/documents/{DOC_ID}/settings"
    res = mock_client.get(url, headers=auth("owner")).json()
    assert res["settings"] is None and set(res["defaults"]) == {"top_k", "min_relevance"}

    saved = mock_client.put(url, json={"top_k": 6, "min_relevance": 0.05, "applied_from_run": "r1"}, headers=auth("owner"))
    assert saved.status_code == 200
    assert mock_client.get(url, headers=auth("owner")).json()["settings"]["top_k"] == 6

    assert mock_client.delete(url, headers=auth("owner")).status_code == 200
    assert mock_client.get(url, headers=auth("owner")).json()["settings"] is None


@pytest.mark.parametrize("body", [{"top_k": 2, "min_relevance": 0.1}, {"top_k": 6, "min_relevance": 0.5}])
def test_out_of_range_rejected(mock_client, owned, body):
    assert mock_client.put(f"/documents/{DOC_ID}/settings", json=body, headers=auth("owner")).status_code == 422


@pytest.mark.parametrize("headers", [{}, auth("someone-else")])
def test_only_the_owner(mock_client, owned, headers):
    assert mock_client.get(f"/documents/{DOC_ID}/settings", headers=headers).status_code == 404
    body = {"top_k": 6, "min_relevance": 0.05}
    assert mock_client.put(f"/documents/{DOC_ID}/settings", json=body, headers=headers).status_code == 404


def test_anonymous_document_cannot_be_tuned(mock_client, storage):
    # No owner file: anyone may query it, but nobody may change how it answers
    res = mock_client.put(f"/documents/{DOC_ID}/settings", json={"top_k": 6, "min_relevance": 0.05}, headers=auth("x"))
    assert res.status_code == 404


def test_query_uses_saved_settings(mock_client, owned):
    file_storage.save_doc_settings(DOC_ID, DocSettings(top_k=6, min_relevance=0.05))
    fake = AsyncMock(return_value=QueryResult(response=QueryResponse(trace_id="t", question="q", answer="a", sources=[])))
    with patch("app.api.retrieve.answer_question", fake):
        mock_client.post("/query", json={"document_id": DOC_ID, "question": "who is it?"}, headers=auth("owner"))
    assert fake.call_args.kwargs["overrides"].min_relevance == 0.05


def test_deleting_the_document_removes_its_settings(owned):
    from app.services.ingestion.ingestion_service import remove_document_files

    file_storage.save_doc_settings(DOC_ID, DocSettings(top_k=6, min_relevance=0.05))
    remove_document_files(DOC_ID)
    assert file_storage.get_doc_settings(DOC_ID) is None
