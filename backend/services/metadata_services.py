import json
import os
from datetime import datetime

METADATA_BASE_PATH = "data/metadata"

def create_raw_metadata(
    document_id: str,
    filename: str,
    source_type: str,
    size_mb: float,
    storage_path: str
):
    os.makedirs(METADATA_BASE_PATH, exist_ok=True)

    metadata = {
        "document_id": document_id,
        "filename": filename,
        "source_type": source_type,
        "size_mb": size_mb,
        "storage_path": storage_path,
        "status": "RAW_UPLOADED",
        "uploaded_at": datetime.utcnow().isoformat()
    }

    metadata_path = os.path.join(
        METADATA_BASE_PATH,
        f"{document_id}.json"
    )

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata
