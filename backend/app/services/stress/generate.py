"""
Generate a stress-test question set for one document.

Answerable questions come from evenly sampled chunks (each remembers its source chunk,
so the run can check whether retrieval found it). Unanswerable questions are about the
document's subject but not stated in it: the system should say "not found".
"""
import json
import logging
import re
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

MIN_CHUNK_CHARS = 80
EXCERPT_CHARS = 1500

STYLES = {
    "direct": "Ask a direct question whose answer is stated in the passage.",
    "reworded": "Ask about one fact in the passage using different words than the passage uses (copy no phrases).",
    "messy": "Ask about one fact in the passage the way a hurried user types: all lowercase, a typo or two, no punctuation.",
}
SYSTEM = "You write test questions for a document question-answering system. Reply with JSON only, no prose."


class StressError(Exception):
    """The stress test can't run (no usable text, or too few questions generated)."""


def plan_mix(size: int) -> dict[str, int]:
    """40% direct, 20% reworded, 25% unanswerable (at least 2); the rest messy."""
    unanswerable = max(2, round(size * 0.25))
    direct, reworded = round(size * 0.4), round(size * 0.2)
    return {"direct": direct, "reworded": reworded, "messy": size - unanswerable - direct - reworded,
            "unanswerable": unanswerable}


def load_chunks(document_id: str) -> list[dict[str, Any]]:
    path = settings.vector_store_dir / f"{document_id}_metadata.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def sample_chunks(chunks: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """n chunks spread evenly through the document (repeats allowed if it is short)."""
    usable = [c for c in chunks if len((c.get("chunk_text") or "").strip()) >= MIN_CHUNK_CHARS]
    if not usable:
        raise StressError("The document has no text long enough to test.")
    return [usable[int(i * len(usable) / n)] for i in range(n)]


def _parse_json(text: str, kind: type) -> Optional[Any]:
    """First JSON object/array in the reply, or None."""
    match = re.search(r"\{.*\}" if kind is dict else r"\[.*\]", text or "", re.DOTALL)
    try:
        value = json.loads(match.group(0)) if match else None
    except ValueError:
        return None
    return value if isinstance(value, kind) else None


def _ask(llm, prompt: str, kind: type, api_key, model) -> Optional[Any]:
    """One LLM call, retried once if the reply isn't the JSON we asked for."""
    for _ in range(2):
        value = _parse_json(llm.chat(SYSTEM, prompt, api_key=api_key, model=model, purpose="stress_generate"), kind)
        if value is not None:
            return value
    return None


def generate_items(document_id: str, size: int, *, api_key: Optional[str], model: Optional[str], llm=None) -> list[dict]:
    if llm is None:
        from app.services.llm.llm_service import LLMService

        llm = LLMService.get_instance()
    chunks = load_chunks(document_id)
    mix = plan_mix(size)
    kinds = [k for k in ("direct", "reworded", "messy") for _ in range(mix[k])]
    sampled = sample_chunks(chunks, len(kinds))

    items: list[dict] = []
    for kind, c in zip(kinds, sampled):
        reply = _ask(
            llm,
            f'{STYLES[kind]}\nReturn {{"question": "...", "answer": "..."}}, where answer is short and taken '
            f"only from the passage.\n\nPassage:\n{c['chunk_text']}",
            dict, api_key, model,
        )
        question, answer = (reply or {}).get("question"), (reply or {}).get("answer")
        if not (isinstance(question, str) and question.strip() and isinstance(answer, str) and answer.strip()):
            logger.info(f"[{document_id}] stress: skipped a {kind} question (no usable reply)")
            continue
        items.append({"kind": kind, "question": question.strip(), "expected_answer": answer.strip(),
                      "source_chunk_id": c["chunk_id"], "page_number": c.get("page_number")})

    excerpt = "\n".join(c["chunk_text"] for c in chunks[:3])[:EXCERPT_CHARS]
    questions = _ask(
        llm,
        f"Here is the start of a document. Write {mix['unanswerable']} questions a user might plausibly ask "
        "about this document's subject that the document does NOT answer. Return a JSON list of strings."
        f"\n\nDocument start:\n{excerpt}",
        list, api_key, model,
    ) or []
    for q in [q for q in questions if isinstance(q, str) and q.strip()][: mix["unanswerable"]]:
        items.append({"kind": "unanswerable", "question": q.strip(), "expected_answer": None,
                      "source_chunk_id": None, "page_number": None})

    if len(items) < size / 2:
        raise StressError(f"The model could only generate {len(items)} of {size} test questions. Try again.")
    for i, item in enumerate(items, start=1):
        item["id"] = f"q{i}"
    return items
