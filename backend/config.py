import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

UPLOADS_DIR = BASE_DIR / "uploads"
MOVIES_DIR = UPLOADS_DIR / "movies"
POSTERS_DIR = UPLOADS_DIR / "posters"
SUBTITLES_DIR = UPLOADS_DIR / "subtitles"
CHUNKS_DIR = UPLOADS_DIR / "chunks"

for directory in (MOVIES_DIR, POSTERS_DIR, SUBTITLES_DIR, CHUNKS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Database
DB_PATH = DATA_DIR / "cinecloud.db"

# Server Configuration
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
DEBUG = os.environ.get("DEBUG", "true").lower() in ("true", "1", "yes")

# Security & Secrets
SECRET_KEY = os.environ.get("SECRET_KEY", "cinecloud-super-secret-vault-key-2026")
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days session
STREAM_TOKEN_EXPIRATION_HOURS = 12

# Cloud Storage Settings (Optional S3 / Cloudflare R2 / MinIO integration)
STORAGE_DRIVER = os.environ.get("STORAGE_DRIVER", "local")  # 'local' or 's3'
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

# Video Processing & Transcoding
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")
ENABLE_TRANSCODING = os.environ.get("ENABLE_TRANSCODING", "false").lower() in ("true", "1", "yes")
HLS_SEGMENT_DURATION = 6  # seconds
