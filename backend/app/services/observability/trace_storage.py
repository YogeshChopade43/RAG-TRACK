import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def _atomic_write_json(file_path: str, data: dict) -> None:
    """Write JSON data atomically using a temp file and rename."""
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_path, file_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class TraceStorage:
    @staticmethod
    def _get_traces_dir() -> str:
        """Get traces directory from settings."""
        traces_dir = settings.data_dir / "traces"
        os.makedirs(traces_dir, exist_ok=True)
        return str(traces_dir)

    @staticmethod
    def save(trace):
        traces_dir = TraceStorage._get_traces_dir()

        file_path = os.path.join(traces_dir, f"{trace.trace_id}.json")

        _atomic_write_json(file_path, trace.model_dump())

        logger.debug(f"Trace saved: {trace.trace_id}")

    @staticmethod
    def save_error(trace, error: str):
        trace.error = error
        TraceStorage.save(trace)

    @staticmethod
    def load(trace_id: str):
        """Load a trace by ID."""
        from app.services.observability.trace_model import TraceModel

        traces_dir = TraceStorage._get_traces_dir()
        file_path = os.path.join(traces_dir, f"{trace_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle datetime deserialization
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

        return TraceModel(**data)

    @staticmethod
    def list_traces(limit: int = 50, older_than: datetime = None) -> list[dict]:
        """
        List recent traces with metadata.

        Args:
            limit: Maximum number of traces to return
            older_than: Only return traces older than this datetime

        Returns:
            List of trace metadata dicts sorted by timestamp descending
        """
        traces_dir = TraceStorage._get_traces_dir()
        if not os.path.exists(traces_dir):
            return []

        traces = []
        for filename in os.listdir(traces_dir):
            if not filename.endswith(".json"):
                continue
            file_path = os.path.join(traces_dir, filename)
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                ts = data.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if older_than and ts and ts >= older_than:
                    continue
                traces.append({
                    "trace_id": data.get("trace_id"),
                    "timestamp": ts,
                    "question": data.get("original_query", "")[:100],
                    "error": data.get("error"),
                })
            except Exception:
                continue

        traces.sort(key=lambda x: x.get("timestamp") or datetime.min, reverse=True)
        return traces[:limit]

    @staticmethod
    def cleanup_old_traces(retention_days: int = 7) -> int:
        """
        Remove trace files older than retention_days.

        Args:
            retention_days: Number of days to retain traces

        Returns:
            Number of trace files removed
        """
        traces_dir = TraceStorage._get_traces_dir()
        if not os.path.exists(traces_dir):
            return 0

        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        removed = 0

        for filename in os.listdir(traces_dir):
            if not filename.endswith(".json"):
                continue
            file_path = os.path.join(traces_dir, filename)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if mtime < cutoff:
                    os.unlink(file_path)
                    removed += 1
            except Exception:
                continue

        if removed:
            logger.info(f"Cleaned up {removed} old trace files (older than {retention_days} days)")
        return removed
