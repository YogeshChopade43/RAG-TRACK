"""Request-scoped call log: every LLM and Jev call lands in the trace with tokens and cost."""
import asyncio
import contextvars
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import jev
from app.services.llm.llm_service import LLMService
from app.services.observability.call_log import (
    current_call_log,
    record_call,
    start_call_log,
)


def test_record_without_log_is_noop():
    contextvars.copy_context().run(lambda: record_call({"kind": "llm"}))  # must not raise
    assert contextvars.copy_context().run(current_call_log) is None


def test_entries_reach_log_from_to_thread():
    async def scenario():
        log = start_call_log()
        await asyncio.to_thread(record_call, {"kind": "jev", "purpose": "rerank"})
        return log

    log = asyncio.run(scenario())
    assert [e["purpose"] for e in log] == ["rerank"]


def test_separate_logs_do_not_mix():
    def request(purpose):
        log = start_call_log()
        record_call({"kind": "llm", "purpose": purpose})
        return log

    a = contextvars.copy_context().run(request, "a")
    b = contextvars.copy_context().run(request, "b")
    assert [e["purpose"] for e in a] == ["a"]
    assert [e["purpose"] for e in b] == ["b"]


def _service(client):
    svc = LLMService.__new__(LLMService)
    svc.client, svc.model, svc.temperature, svc.max_tokens = client, "test/model", 0.0, 100
    return svc


def test_llm_chat_records_usage_and_cost():
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=8, cost=0.00031),
    )

    def run():
        log = start_call_log()
        _service(client).chat("sys", "user", purpose="answer")
        return log

    (entry,) = contextvars.copy_context().run(run)
    assert entry["kind"] == "llm" and entry["purpose"] == "answer" and entry["model"] == "test/model"
    assert (entry["prompt_tokens"], entry["completion_tokens"], entry["cost_usd"]) == (120, 8, 0.00031)
    assert entry["ok"] is True and entry["duration_ms"] >= 0
    # OpenRouter only returns cost when usage accounting is requested
    assert client.chat.completions.create.call_args.kwargs["extra_body"] == {"usage": {"include": True}}


def test_llm_chat_records_failure_without_key(monkeypatch):
    monkeypatch.setattr(LLMService.chat.retry, "sleep", lambda _s: None)
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("upstream 502")

    def run():
        log = start_call_log()
        with pytest.raises(RuntimeError):
            _service(client).chat("sys", "user", api_key=None, purpose="rewrite")
        return log

    log = contextvars.copy_context().run(run)
    assert log and all(e["ok"] is False and e["purpose"] == "rewrite" for e in log)
    assert "upstream 502" in log[-1]["error"]


def test_jev_decide_records_entry_with_null_cost(monkeypatch):
    resp = MagicMock()
    resp.json.return_value = {"answers": {"c0": {"noul": 0.9}}}
    monkeypatch.setattr(jev.httpx, "post", lambda *a, **k: resp)
    monkeypatch.setattr(jev.settings, "jev_enabled", True)

    def run():
        log = start_call_log()
        jev.decide({"q": "x"}, {"c0": {}}, api_key="sk-or-secret", purpose="rerank")
        return log

    (entry,) = contextvars.copy_context().run(run)
    assert entry["kind"] == "jev" and entry["purpose"] == "rerank" and entry["ok"] is True
    assert entry["cost_usd"] is None and entry["prompt_tokens"] is None
    assert "sk-or-secret" not in str(entry)
