"""
Evaluation dataset management.

Provides utilities for creating, loading, and managing test datasets
for RAG evaluation, including ground truth relevance judgments.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


@dataclass
class EvalQuery:
    """Represents a single evaluation query with ground truth."""

    query_id: str
    question: str
    document_id: str
    relevant_chunk_ids: Set[str] = field(default_factory=set)
    expected_answer_keywords: List[str] = field(default_factory=list)
    is_overview: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["relevant_chunk_ids"] = list(self.relevant_chunk_ids)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvalQuery":
        data["relevant_chunk_ids"] = set(data.get("relevant_chunk_ids", []))
        return cls(**data)


class EvalDataset:
    """
    Collection of evaluation queries for one or more documents.

    Supports loading from JSON files and creating datasets from
    existing system data (parsed documents, traces).
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.queries: List[EvalQuery] = []

    def add_query(self, query: EvalQuery) -> None:
        self.queries.append(query)

    def get_by_document(self, document_id: str) -> List[EvalQuery]:
        return [q for q in self.queries if q.document_id == document_id]

    def save(self, path: Union[str, Path]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "queries": [q.to_dict() for q in self.queries],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "EvalDataset":
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        dataset = cls(name=data.get("name", "loaded"))
        for q_data in data.get("queries", []):
            dataset.add_query(EvalQuery.from_dict(q_data))
        return dataset

    def __len__(self) -> int:
        return len(self.queries)

    def __iter__(self):
        return iter(self.queries)
