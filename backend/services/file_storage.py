import os

BASE_PATH = "data/raw"

def save_raw_file(document_id: str, filename: str, content: bytes):
    dir_path = os.path.join(BASE_PATH, document_id)
    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path
