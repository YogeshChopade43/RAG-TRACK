"""Per-document retrieval settings, chosen by the stress test's auto-tune and applied by the owner."""
from typing import Optional

from pydantic import BaseModel, Field


class DocSettings(BaseModel):
    top_k: int = Field(ge=3, le=12)
    min_relevance: float = Field(ge=0.02, le=0.3)
    applied_from_run: Optional[str] = None
    applied_at: Optional[str] = None
