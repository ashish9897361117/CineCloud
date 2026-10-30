import os
from pathlib import Path
from typing import Generator
from backend.storage.base import BaseStorage
from backend.config import UPLOADS_DIR, MOVIES_DIR, POSTERS_DIR, SUBTITLES_DIR

class LocalStorage(BaseStorage):
    def __init__(self):
        self.base_dir = UPLOADS_DIR
        self.folders = {
            "movies": MOVIES_DIR,
            "posters": POSTERS_DIR,
            "subtitles": SUBTITLES_DIR
        }

    def _get_target_dir(self, folder: str) -> Path:
        return self.folders.get(folder, self.base_dir / folder)

    def save_file(self, filename: str, content: bytes, folder: str = "movies") -> str:
        target_dir = self._get_target_dir(folder)
        target_dir.mkdir(parents=True, exist_ok=True)
        # Avoid path traversal
        clean_filename = Path(filename).name
        file_path = target_dir / clean_filename
        with open(file_path, "wb") as f:
            f.write(content)
        # Return path relative to base or absolute
        return str(file_path)

    def delete_file(self, filepath: str) -> bool:
        try:
            p = Path(filepath)
            if p.exists() and p.is_file():
                p.unlink()
                return True
        except Exception:
            pass
        return False

    def file_exists(self, filepath: str) -> bool:
        return Path(filepath).exists()

    def get_file_size(self, filepath: str) -> int:
        return Path(filepath).stat().st_size

    def get_byte_range(self, filepath: str, start: int, end: int, chunk_size: int = 128 * 1024) -> Generator[bytes, None, None]:
        with open(filepath, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                read_amount = min(chunk_size, remaining)
                chunk = f.read(read_amount)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
