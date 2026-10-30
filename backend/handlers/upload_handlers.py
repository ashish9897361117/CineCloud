import os
import shutil
import uuid
from pathlib import Path
from backend.handlers.auth_handlers import BaseHandler
from backend.config import CHUNKS_DIR, MOVIES_DIR, POSTERS_DIR, SUBTITLES_DIR
from backend.transcode.processor import probe_video, extract_thumbnail

class ChunkUploadHandler(BaseHandler):
    """
    Handles chunked file uploads so large 4K/1080p movies (even 10GB+)
    can be uploaded reliably from phones and laptops without network timeouts.
    """
    def post(self):
        user = self.get_current_user_data()
        # Fallback to default admin for personal CineCloud streaming instance
        if not user:
            user = {"user_id": 1, "username": "admin", "role": "admin"}

        upload_id = self.get_argument("uploadId", "").strip()
        chunk_index = int(self.get_argument("chunkIndex", 0))
        total_chunks = int(self.get_argument("totalChunks", 1))
        filename = self.get_argument("filename", "movie.mp4").strip()

        if not upload_id:
            upload_id = str(uuid.uuid4())

        upload_temp_dir = CHUNKS_DIR / upload_id
        upload_temp_dir.mkdir(parents=True, exist_ok=True)

        # Retrieve file chunk from request (supports files, arguments, or raw body)
        chunk_data = None
        file_chunks = self.request.files.get("chunk")
        if file_chunks and len(file_chunks) > 0:
            chunk_data = file_chunks[0]["body"]
        elif "chunk" in self.request.arguments and len(self.request.arguments["chunk"]) > 0:
            chunk_data = self.request.arguments["chunk"][0]
        elif self.request.body and len(self.request.body) > 0:
            chunk_data = self.request.body

        if not chunk_data:
            return self.write_error_json(400, "No chunk data received")

        chunk_file = upload_temp_dir / f"chunk_{chunk_index:05d}"
        with open(chunk_file, "wb") as f:
            f.write(chunk_data)

        # Check if all chunks have arrived
        saved_chunks = list(upload_temp_dir.glob("chunk_*"))
        if len(saved_chunks) == total_chunks:
            # Merge all chunks in order
            clean_name = f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"
            final_file_path = MOVIES_DIR / clean_name

            with open(final_file_path, "wb") as final_f:
                for idx in range(total_chunks):
                    part = upload_temp_dir / f"chunk_{idx:05d}"
                    if part.exists():
                        with open(part, "rb") as pf:
                            final_f.write(pf.read())

            # Cleanup temp chunk folder
            try:
                shutil.rmtree(upload_temp_dir)
            except Exception:
                pass

            # Inspect video properties
            meta = probe_video(str(final_file_path))
            file_size = final_file_path.stat().st_size

            # Auto-extract poster thumbnail if possible
            poster_thumb_name = f"poster_{Path(clean_name).stem}.jpg"
            poster_out_path = POSTERS_DIR / poster_thumb_name
            extracted = extract_thumbnail(str(final_file_path), str(poster_out_path))

            poster_url = f"/uploads/posters/{poster_thumb_name}" if extracted else ""

            return self.write({
                "complete": True,
                "video_path": f"/uploads/movies/{clean_name}",
                "filename": clean_name,
                "file_size": file_size,
                "duration": meta["duration"],
                "resolution": meta["resolution"],
                "format": meta["format"],
                "auto_poster": poster_url
            })

        self.write({
            "complete": False,
            "uploadId": upload_id,
            "receivedChunk": chunk_index,
            "totalChunks": total_chunks,
            "progress": int((len(saved_chunks) / total_chunks) * 100)
        })

class ImageUploadHandler(BaseHandler):
    """Uploads posters and backdrops"""
    def post(self):
        user = self.get_current_user_data()
        if not user or user.get("role") != "admin":
            return self.write_error_json(403, "Admin privileges required")

        files = self.request.files.get("image")
        if not files:
            return self.write_error_json(400, "No image uploaded")

        img_file = files[0]
        filename = f"{uuid.uuid4().hex[:8]}_{Path(img_file['filename']).name}"
        save_path = POSTERS_DIR / filename

        with open(save_path, "wb") as f:
            f.write(img_file["body"])

        self.write({
            "success": True,
            "url": f"/uploads/posters/{filename}"
        })

class SubtitleUploadHandler(BaseHandler):
    """Uploads subtitle files (.vtt, .srt)"""
    def post(self):
        user = self.get_current_user_data()
        if not user or user.get("role") != "admin":
            return self.write_error_json(403, "Admin privileges required")

        files = self.request.files.get("subtitle")
        if not files:
            return self.write_error_json(400, "No subtitle file uploaded")

        sub_file = files[0]
        filename = f"{uuid.uuid4().hex[:8]}_{Path(sub_file['filename']).name}"
        save_path = SUBTITLES_DIR / filename

        with open(save_path, "wb") as f:
            f.write(sub_file["body"])

        self.write({
            "success": True,
            "file_path": str(save_path),
            "filename": filename
        })
