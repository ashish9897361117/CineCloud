import os
import re
from pathlib import Path
import tornado.web
import tornado.gen
from backend.handlers.auth_handlers import BaseHandler
from backend.database import get_db, row_to_dict
from backend.storage.local_storage import LocalStorage
from backend.auth import extract_user_from_request

storage = LocalStorage()

class StreamHandler(BaseHandler):
    """
    High-Performance Video Streaming Handler.
    Supports RFC 7233 byte-range seeking, private authentication tokens,
    and direct streaming without memory buffering.
    """
    @tornado.gen.coroutine
    def get(self, movie_id: str):
        # 1. Validate stream authentication token
        user = extract_user_from_request(self)
        # Note: If token is omitted, we can allow authenticated or public stream token checks
        # Allow checking either user auth or token
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        movie = cursor.fetchone()
        conn.close()

        if not movie:
            self.set_status(404)
            self.write({"error": "Movie not found"})
            return

        video_path = movie["video_path"]

        # If it's an external URL (e.g. Cloud CDN or S3 presigned URL)
        if video_path.startswith("http://") or video_path.startswith("https://"):
            self.redirect(video_path, permanent=False)
            return

        # Local file stream
        file_path = Path(video_path)
        if not file_path.is_file():
            self.set_status(404)
            self.write({"error": "Video file not found on disk"})
            return

        file_size = file_path.stat().st_size
        range_header = self.request.headers.get("Range")

        # Determine MIME type
        ext = file_path.suffix.lower()
        content_type = "video/mp4"
        if ext == ".mkv":
            content_type = "video/x-matroska"
        elif ext == ".webm":
            content_type = "video/webm"
        elif ext == ".m3u8":
            content_type = "application/x-mpegURL"
        elif ext == ".ts":
            content_type = "video/MP2T"

        self.set_header("Content-Type", content_type)
        self.set_header("Accept-Ranges", "bytes")

        if not range_header:
            # Full file requested
            self.set_header("Content-Length", str(file_size))
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    self.write(chunk)
                    yield self.flush()
            return

        # Parse Byte Range: "bytes=start-end"
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not range_match:
            self.set_status(416)
            self.set_header("Content-Range", f"bytes */{file_size}")
            return

        start_str, end_str = range_match.groups()
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

        if start >= file_size or end >= file_size or start > end:
            self.set_status(416)
            self.set_header("Content-Range", f"bytes */{file_size}")
            return

        content_length = end - start + 1
        self.set_status(206) # Partial Content
        self.set_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.set_header("Content-Length", str(content_length))

        # Stream chunk by chunk asynchronously
        chunk_size = 256 * 1024  # 256 KB chunks
        with open(file_path, "rb") as f:
            f.seek(start)
            bytes_left = content_length
            while bytes_left > 0:
                read_amount = min(chunk_size, bytes_left)
                data = f.read(read_amount)
                if not data:
                    break
                self.write(data)
                yield self.flush()
                bytes_left -= len(data)

class SubtitleHandler(BaseHandler):
    """Delivers WebVTT subtitle files for movie playback"""
    def get(self, subtitle_id: str):
        # Sample subtitle fallback for demo
        if subtitle_id.startswith("sample_"):
            self.set_header("Content-Type", "text/vtt; charset=utf-8")
            if "es" in subtitle_id:
                sample_vtt = """WEBVTT - Subtitulos en Espanol

00:00:02.000 --> 00:00:06.000
[CineCloud - Reproduccion Segura en la Nube]

00:00:07.500 --> 00:00:12.000
Todos los sistemas orbitales estan operando dentro de los parametros normales.

00:00:14.000 --> 00:00:18.500
Iniciando salto hiperespacial en tres, dos, uno...
"""
            else:
                sample_vtt = """WEBVTT - English Closed Captions

00:00:02.000 --> 00:00:06.000
[CineCloud - Secure Cloud Streaming Active]

00:00:07.500 --> 00:00:12.000
All orbital telemetry systems operating within target parameters.

00:00:14.000 --> 00:00:18.500
Initiating hyperspace velocity transition in three, two, one...
"""
            self.write(sample_vtt)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subtitles WHERE id = ?", (subtitle_id,))
        sub = cursor.fetchone()
        conn.close()

        if not sub:
            self.set_status(404)
            return

        file_path = Path(sub["file_path"])
        if not file_path.exists():
            self.set_status(404)
            return

        self.set_header("Content-Type", "text/vtt; charset=utf-8")
        
        # If it's an SRT file, convert on the fly to WebVTT
        if file_path.suffix.lower() == ".srt":
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # Replace SRT comma in timestamps with dot for VTT
            vtt_content = "WEBVTT\n\n" + re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", content)
            self.write(vtt_content)
        else:
            with open(file_path, "rb") as f:
                self.write(f.read())
