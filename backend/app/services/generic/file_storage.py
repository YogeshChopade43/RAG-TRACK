import logging
import os

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
