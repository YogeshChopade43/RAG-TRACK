# app/core/config.py

ALLOWED_EXTENSIONS = {"pdf", "txt"}
MAX_FILE_SIZE_MB = 10

CHUNK_SIZE = 1024
CHUNK_OVERLAP = 500

EMBEDDING_DIR = "data/embeddings"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VECTOR_STORE_DIR = os.path.join(DATA_DIR, "vector_store")
EMBEDDING_DIR = os.path.join(DATA_DIR, "embeddings")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")