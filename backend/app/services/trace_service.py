import json
import os
from datetime import datetime
from uuid import uuid4

from app.core.paths import TRACE_DIR


def _now():
    return datetime.utcnow().isoformat()


class TraceService:
    """
    Responsible ONLY for:
    - creating trace.json
    - appending stage-level execution info
    """

    def create_trace(self, document_id: str, filename: str, file_type: str, size_mb: float):
        os.makedirs(TRACE_DIR, exist_ok=True)

        trace = {
            "trace_id": str(uuid4()),
            "document_id": document_id,
            "created_at": _now(),
            "last_updated_at": _now(),
            "status": "INGESTED",

            "source": {
                "filename": filename,
                "file_type": file_type,
                "size_mb": size_mb
            },

            "artifacts": {},

            "stages": {
                "ingestion": {},
                "parsing": {},
                "chunking": {},
                "embedding": {},
                "retrieval": {},
                "reranking": {},
                "generation": {}
            },

            "errors": []
        }

        path = self._trace_path(document_id)
        self._write(trace, path)

        return path

    def update_stage(self, document_id: str, stage: str, payload: dict, status: str = None):
        trace = self.load_trace(document_id)

        if stage not in trace["stages"]:
            raise ValueError(f"Invalid stage: {stage}")

        trace["stages"][stage] = {
            **payload,
            "timestamp": _now()
        }

        if status:
            trace["status"] = status

        trace["last_updated_at"] = _now()

        self._write(trace, self._trace_path(document_id))

    def add_artifact(self, document_id: str, key: str, value: str):
        trace = self.load_trace(document_id)
        trace["artifacts"][key] = value
        trace["last_updated_at"] = _now()
        self._write(trace, self._trace_path(document_id))

    def add_error(self, document_id: str, stage: str, message: str, fatal: bool = False):
        trace = self.load_trace(document_id)

        trace["errors"].append({
            "stage": stage,
            "timestamp": _now(),
            "message": message,
            "fatal": fatal
        })

        trace["status"] = "FAILED"
        trace["last_updated_at"] = _now()

        self._write(trace, self._trace_path(document_id))

    def load_trace(self, document_id: str) -> dict:
        path = self._trace_path(document_id)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _trace_path(self, document_id: str) -> str:
        return os.path.join(TRACE_DIR, f"{document_id}.json")

    def _write(self, data: dict, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_trace(self, document_id: str) -> dict:
        path = self._trace_path(document_id)
        if not os.path.exists(path):
            raise RuntimeError(
                f"Trace not initialized for document_id={document_id}. "
                "Call create_trace() first."
            )
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
