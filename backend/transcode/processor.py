import os
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from backend.config import FFMPEG_PATH, HLS_SEGMENT_DURATION, UPLOADS_DIR

def is_ffmpeg_available() -> bool:
    try:
        res = subprocess.run([FFMPEG_PATH, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return res.returncode == 0
    except Exception:
        # Check standard PATH
        return shutil.which("ffmpeg") is not None

def probe_video(video_path: str) -> Dict[str, Any]:
    """Inspects video resolution, duration, audio channels, and codecs using ffprobe"""
    info = {
        "duration": 0,
        "width": 1920,
        "height": 1080,
        "resolution": "1080p",
        "format": "mp4",
        "has_audio": True,
        "subtitles": []
    }
    
    if not is_ffmpeg_available():
        # Fallback inspection by file extension and size
        ext = Path(video_path).suffix.lower().replace(".", "")
        info["format"] = ext if ext in ["mp4", "mkv", "webm"] else "mp4"
        return info

    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            # Duration
            format_info = data.get("format", {})
            info["duration"] = int(float(format_info.get("duration", 0)))
            
            # Video stream
            for stream in data.get("streams", []):
                codec_type = stream.get("codec_type")
                if codec_type == "video" and "width" in stream:
                    w = int(stream["width"])
                    h = int(stream["height"])
                    info["width"] = w
                    info["height"] = h
                    if w >= 3840 or h >= 2160:
                        info["resolution"] = "4K Ultra HD"
                    elif w >= 1920 or h >= 1080:
                        info["resolution"] = "1080p Full HD"
                    elif w >= 1280 or h >= 720:
                        info["resolution"] = "720p HD"
                    else:
                        info["resolution"] = "SD 480p"
                elif codec_type == "subtitle":
                    tags = stream.get("tags", {})
                    info["subtitles"].append({
                        "language": tags.get("language", "und"),
                        "title": tags.get("title", f"Track {len(info['subtitles']) + 1}")
                    })
    except Exception as e:
        print(f"ffprobe error: {e}")
        
    return info

def extract_thumbnail(video_path: str, output_path: str, timestamp_sec: int = 15) -> bool:
    """Extracts a high quality frame from the video to use as backdrop/poster"""
    if not is_ffmpeg_available():
        return False
        
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            FFMPEG_PATH,
            "-y",
            "-ss", str(timestamp_sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return res.returncode == 0
    except Exception as e:
        print(f"Error extracting thumbnail: {e}")
        return False

def generate_hls(video_path: str, output_dir: str, segment_duration: int = HLS_SEGMENT_DURATION) -> Tuple[bool, str]:
    """
    Transcodes or repacks video into HLS (.m3u8 playlist and .ts segments)
    for seamless, buffer-free playback across TV and web.
    """
    if not is_ffmpeg_available():
        return False, "FFmpeg is not installed on host. Using direct byte-range streaming."
        
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    m3u8_file = out_dir / "index.m3u8"
    ts_pattern = str(out_dir / "segment_%03d.ts")
    
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", video_path,
        "-c:v", "copy",  # Direct stream copy where possible for ultra-fast packaging
        "-c:a", "aac",
        "-b:a", "192k",
        "-hls_time", str(segment_duration),
        "-hls_list_size", "0",
        "-hls_segment_filename", ts_pattern,
        "-f", "hls",
        str(m3u8_file)
    ]
    
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if res.returncode == 0:
            return True, str(m3u8_file)
        else:
            # Fallback re-encode if stream copy fails due to codec mismatch
            fallback_cmd = [
                FFMPEG_PATH,
                "-y",
                "-i", video_path,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "160k",
                "-hls_time", str(segment_duration),
                "-hls_list_size", "0",
                "-hls_segment_filename", ts_pattern,
                "-f", "hls",
                str(m3u8_file)
            ]
            res2 = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
            if res2.returncode == 0:
                return True, str(m3u8_file)
            return False, res2.stderr.decode('utf-8', errors='ignore')
    except Exception as e:
        return False, str(e)
