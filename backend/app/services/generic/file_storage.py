import logging
import os
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def save_raw_file(document_id, filename, content):
    dir_path = os.path.join(settings.raw_dir, document_id)
    logger.debug(f"Saving raw file to directory: {dir_path}")

    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


def owner_path(document_id: str):
    # Kept outside raw/<id>/ because the parser reads the first file in that folder
    return settings.data_dir / "owners" / f"{document_id}.txt"


def save_owner(document_id: str, user_id: str) -> None:
    path = owner_path(document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(user_id, encoding="utf-8")


def get_owner(document_id: str) -> Optional[str]:
    path = owner_path(document_id)
    return path.read_text(encoding="utf-8").strip() if path.exists() else None
