"""
Request-scoped log of model calls (LLM and Jev) for the trace.

A query handler calls start_call_log(); llm_service.chat and jev.decide then
record one entry per call. The log lives in a ContextVar, which asyncio.to_thread
copies into worker threads, so entries from threaded calls land in the same
request's list while concurrent requests keep separate lists.
"""
import time
from contextvars import ContextVar
from typing import Any, Optional

_log: ContextVar[Optional[list[dict[str, Any]]]] = ContextVar("call_log", default=None)
_start: ContextVar[float] = ContextVar("call_log_start", default=0.0)


def start_call_log() -> list[dict[str, Any]]:
    """Begin a fresh log for this request and return it."""
    log: list[dict[str, Any]] = []
    _log.set(log)
    _start.set(time.perf_counter())
    return log


def current_call_log() -> Optional[list[dict[str, Any]]]:
    return _log.get()


def record_call(entry: dict[str, Any]) -> None:
    """Append an entry if a log is active; a no-op outside a request."""
    log = _log.get()
    if log is not None:
        log.append(entry)


def _num(v: Any) -> Optional[float]:
    """Keep real numbers only (providers may omit fields or return other types)."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def call_entry(
    kind: str,
    purpose: str,
    model: str,
    started: float,
    *,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    error: Optional[str] = None,
) -> dict[str, Any]:
    """Build an entry; `started` is a time.perf_counter() value taken before the call."""
    now = time.perf_counter()
    return {
        "kind": kind,
        "purpose": purpose,
        "model": model,
        "start_ms": round((started - _start.get()) * 1000, 1),
        "duration_ms": round((now - started) * 1000, 1),
        "prompt_tokens": _num(prompt_tokens),
        "completion_tokens": _num(completion_tokens),
        "cost_usd": _num(cost_usd),
        "ok": error is None,
        "error": error,
    }
