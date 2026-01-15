import os

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
METADATA_DIR = os.path.join(DATA_DIR, "metadata")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
TRACE_DIR = os.path.join(DATA_DIR, "trace")
CHUNKS_DIR = os.path.join(DATA_DIR, "chunks")
