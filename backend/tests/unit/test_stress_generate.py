"""Stress test question generation: mix, sampling, parsing and failure modes."""
import json
from unittest.mock import Mock

import pytest

from app.services.stress.generate import (
    StressError,
    generate_items,
    plan_mix,
    sample_chunks,
)

LONG = "x" * 120


def chunk(i, text=None, page=None):
    return {"chunk_id": f"c{i}", "chunk_text": text or f"{LONG} fact {i}", "page_number": page or i, "file_name": "f.pdf"}


@pytest.mark.parametrize("size,expected", [
    (10, {"direct": 4, "reworded": 2, "messy": 2, "unanswerable": 2}),
    (20, {"direct": 8, "reworded": 4, "messy": 3, "unanswerable": 5}),
    (50, {"direct": 20, "reworded": 10, "messy": 8, "unanswerable": 12}),
])
def test_plan_mix(size, expected):
    assert plan_mix(size) == expected and sum(expected.values()) == size


def test_sampling_spreads_across_the_document_and_skips_short_chunks():
    chunks = [chunk(i) for i in range(100)] + [chunk(999, text="too short")]
    picked = sample_chunks(chunks, 5)
    assert [c["chunk_id"] for c in picked] == ["c0", "c20", "c40", "c60", "c80"]
    with pytest.raises(StressError):
        sample_chunks([chunk(1, text="tiny")], 3)


def fake_llm(answers):
    """LLM stub returning queued replies; extra calls reuse the last reply."""
    llm = Mock()
    queue = list(answers)
    llm.chat.side_effect = lambda *a, **k: queue.pop(0) if len(queue) > 1 else queue[0]
    return llm


def qa(q="What is fact?", a="fact"):
    return json.dumps({"question": q, "answer": a})


def test_items_carry_source_chunk_and_kind(monkeypatch):
    chunks = [chunk(i) for i in range(30)]
    monkeypatch.setattr("app.services.stress.generate.load_chunks", lambda doc_id: chunks)
    replies = [qa()] * 8 + [json.dumps(["Unanswerable 1?", "Unanswerable 2?"])]
    items = generate_items("doc", 10, api_key=None, model=None, llm=fake_llm(replies))
    answerable = [i for i in items if i["kind"] != "unanswerable"]
    assert len(answerable) == 8 and all(i["source_chunk_id"] and i["expected_answer"] for i in answerable)
    assert {i["kind"] for i in answerable} == {"direct", "reworded", "messy"}
    unanswerable = [i for i in items if i["kind"] == "unanswerable"]
    assert len(unanswerable) == 2 and all(i["source_chunk_id"] is None for i in unanswerable)
    assert len({i["id"] for i in items}) == len(items)


def test_bad_json_is_retried_once_then_skipped(monkeypatch):
    monkeypatch.setattr("app.services.stress.generate.load_chunks", lambda doc_id: [chunk(i) for i in range(30)])
    # first item: garbage then valid (retried); second item: garbage twice (skipped); rest valid
    replies = ["not json", qa("Q1?"), "nope", "still nope"] + [qa()] * 6 + [json.dumps(["U1?", "U2?"])]
    items = generate_items("doc", 10, api_key=None, model=None, llm=fake_llm(replies))
    assert items[0]["question"] == "Q1?"
    assert len([i for i in items if i["kind"] != "unanswerable"]) == 7


def test_too_few_generated_is_an_error(monkeypatch):
    monkeypatch.setattr("app.services.stress.generate.load_chunks", lambda doc_id: [chunk(i) for i in range(30)])
    with pytest.raises(StressError, match="could only generate"):
        generate_items("doc", 10, api_key=None, model=None, llm=fake_llm(["garbage"]))


def test_document_without_usable_chunks_is_an_error(monkeypatch):
    monkeypatch.setattr("app.services.stress.generate.load_chunks", lambda doc_id: [])
    with pytest.raises(StressError, match="no text"):
        generate_items("doc", 10, api_key=None, model=None, llm=fake_llm([qa()]))
