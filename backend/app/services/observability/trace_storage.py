import json
import logging
import os
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


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

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                trace.model_dump(),
                f,
                indent=2,
                default=str,  # handle datetime
            )

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

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return TraceModel(**data)
