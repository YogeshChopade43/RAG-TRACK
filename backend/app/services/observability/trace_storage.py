import json
import os
from datetime import datetime


class TraceStorage:

    BASE_PATH = "traces"

    @staticmethod
    def save(trace):
        os.makedirs(TraceStorage.BASE_PATH, exist_ok=True)

        file_path = os.path.join(
            TraceStorage.BASE_PATH,
            f"{trace.trace_id}.json"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                trace.dict(),
                f,
                indent=2,
                default=str  # handle datetime
            )

    @staticmethod
    def save_error(trace, error: str):
        trace.error = error
        TraceStorage.save(trace)

    @staticmethod
    def load(trace_id: str):
        """Load a trace by ID."""
        from app.services.observability.trace_model import TraceModel

        file_path = os.path.join(
            TraceStorage.BASE_PATH,
            f"{trace_id}.json"
        )

        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return TraceModel(**data)