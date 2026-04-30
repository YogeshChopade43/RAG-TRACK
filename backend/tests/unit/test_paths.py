"""
Unit tests for paths configuration.
"""
import pytest
import os
from app.core.paths import (
    BASE_DIR,
    DATA_DIR,
    RAW_DIR,
    METADATA_DIR,
    PARSED_DIR,
    TRACE_DIR,
    CHUNKS_DIR,
)


class TestPaths:
    """Tests for path constants."""

    def test_base_dir_is_absolute_path(self):
        """Test BASE_DIR is an absolute path."""
        assert os.path.isabs(BASE_DIR)

    def test_base_dir_exists(self):
        """Test BASE_DIR exists."""
        assert os.path.exists(BASE_DIR)

    def test_data_dir_structure(self):
        """Test data directory paths are properly derived."""
        assert DATA_DIR.startswith(BASE_DIR)
        assert "data" in DATA_DIR

    def test_all_required_dirs_defined(self):
        """Test all required directory constants exist."""
        required_dirs = [DATA_DIR, RAW_DIR, METADATA_DIR, PARSED_DIR, TRACE_DIR, CHUNKS_DIR]
        for dir_path in required_dirs:
            assert dir_path is not None
            assert isinstance(dir_path, str)

    def test_subdirectory_relationships(self):
        """Test subdirectories are under DATA_DIR."""
        assert RAW_DIR.startswith(DATA_DIR)
        assert METADATA_DIR.startswith(DATA_DIR)
        assert PARSED_DIR.startswith(DATA_DIR)
        assert TRACE_DIR.startswith(DATA_DIR)
        assert CHUNKS_DIR.startswith(DATA_DIR)

    def test_paths_are_strings(self):
        """Test all paths are strings."""
        paths = {
            "BASE_DIR": BASE_DIR,
            "DATA_DIR": DATA_DIR,
            "RAW_DIR": RAW_DIR,
            "METADATA_DIR": METADATA_DIR,
            "PARSED_DIR": PARSED_DIR,
            "TRACE_DIR": TRACE_DIR,
            "CHUNKS_DIR": CHUNKS_DIR,
        }
        for name, path in paths.items():
            assert isinstance(path, str), f"{name} should be a string"
