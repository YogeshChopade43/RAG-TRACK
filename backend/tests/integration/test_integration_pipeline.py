"""
End-to-end integration pipeline tests for RAG-TRACK.

Runs parsing -> chunking -> embedding with real FAISS and real
sentence-transformers when available. Skips if model download is
unavailable (e.g. offline CI).
"""

import json
import sys
from pathlib import Path

import faiss
import pytest

from app.services.chunking.chunking_service import ChunkingService
from app.services.embedding.embedding_service import EmbeddingService
from app.services.parsing.parsing_service import ParsingService


@pytest.mark.integration
def test_full_pipeline_generates_vector_store(tmp_path, monkeypatch):
    document_id = "integration-test-doc"

    raw_dir = tmp_path / "raw" / document_id
    parsed_dir = tmp_path / "parsed"
    vector_store_dir = tmp_path / "vector_store"
    raw_dir.mkdir(parents=True)
    parsed_dir.mkdir()
    vector_store_dir.mkdir()

    monkeypatch.setattr(
        "app.services.parsing.parsing_service.RAW_BASE",
        str(raw_dir.parent),
    )
    monkeypatch.setattr(
        "app.services.parsing.parsing_service.PARSED_BASE",
        str(parsed_dir),
    )
    monkeypatch.setattr(
        "app.core.config.settings.vector_store_dir",
        vector_store_dir,
    )

    sample_text = (
        "This is a test document for integration testing. "
        "It contains enough text to be chunked meaningfully. "
        "The quick brown fox jumps over the lazy dog. "
        "Lorem ipsum dolor sit amet consectetur adipiscing elit. "
        "RAG-TRACK is an end-to-end retrieval-augmented generation system. "
        "Observability and tracing are first-class features."
    )
    sample_file = raw_dir / "test.txt"
    sample_file.write_text(sample_text, encoding="utf-8")

    parsed = ParsingService().parse(document_id)
    assert parsed["document_id"] == document_id
    assert len(parsed["pages"]) > 0
    assert (parsed_dir / f"{document_id}.json").exists()

    chunks = ChunkingService().chunk(parsed)
    assert len(chunks) > 0
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "chunk_text" in chunk
        assert chunk["document_id"] == document_id

    model_name = "all-MiniLM-L6-v2"
    try:
        st_module = sys.modules.get("sentence_transformers")
        is_dummy = (
            st_module is not None
            and type(getattr(st_module, "SentenceTransformer", None)).__name__
            == "DummySentenceTransformer"
        )
        if is_dummy or st_module is None:
            if "sentence_transformers" in sys.modules:
                del sys.modules["sentence_transformers"]

        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
    except Exception as exc:
        pytest.skip(f"Cannot load sentence-transformers model {model_name}: {exc}")

    from app.services.embedding.shared_model import get_shared_embedding_model

    get_shared_embedding_model.cache_clear()
    monkeypatch.setattr(
        "app.services.embedding.shared_model.get_shared_embedding_model",
        lambda: model,
    )

    embedding_service = EmbeddingService()
    result = embedding_service.embed(chunks)

    assert "index_path" in result
    assert "metadata_path" in result
    assert result["chunks"] == len(chunks)

    index_path = Path(result["index_path"])
    metadata_path = Path(result["metadata_path"])
    assert index_path.exists(), f"FAISS index not created at {index_path}"
    assert metadata_path.exists(), f"Metadata file not created at {metadata_path}"

    index = faiss.read_index(str(index_path))
    assert index.ntotal == len(chunks)

    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)
    assert len(metadata) == len(chunks)
    assert {m["chunk_id"] for m in metadata} == {c["chunk_id"] for c in chunks}
