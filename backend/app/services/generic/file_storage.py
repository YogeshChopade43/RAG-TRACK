from app.core.paths import RAW_DIR
import os

def save_raw_file(document_id, filename, content):
    dir_path = os.path.join(RAW_DIR, document_id)
    print(f"Saving raw file to directory: {dir_path}")
    
    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    return file_path
