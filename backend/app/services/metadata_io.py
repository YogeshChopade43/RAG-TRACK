import json, os
from app.core.paths import METADATA_DIR

def load_metadata(document_id: str) -> dict:
    path = os.path.join(METADATA_DIR, f"{document_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_metadata(meta: dict):
    os.makedirs(METADATA_DIR, exist_ok=True)
    path = os.path.join(METADATA_DIR, f"{meta['document_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
