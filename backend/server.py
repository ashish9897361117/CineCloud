import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import tornado.ioloop
import tornado.web
import tornado.httpserver
from backend.config import PORT, HOST, DEBUG, UPLOADS_DIR, BASE_DIR
from backend.database import init_db
from backend.handlers.auth_handlers import (
    RegisterHandler, LoginHandler, MeHandler,
    TVPairRequestHandler, TVPairAuthorizeHandler, TVPairCheckHandler
)
from backend.handlers.movie_handlers import (
    MoviesHandler, MovieDetailHandler, CategoriesHandler
)
from backend.handlers.stream_handlers import StreamHandler, SubtitleHandler
from backend.handlers.progress_handlers import ProgressHandler
from backend.handlers.upload_handlers import (
    ChunkUploadHandler, ImageUploadHandler, SubtitleUploadHandler
)

WEB_DIR = BASE_DIR / "web"

def make_app():
    handlers = [
        # Authentication & TV Pairing
        (r"/api/auth/register", RegisterHandler),
        (r"/api/auth/login", LoginHandler),
        (r"/api/auth/me", MeHandler),
        (r"/api/auth/tv-pair/request", TVPairRequestHandler),
        (r"/api/auth/tv-pair/authorize", TVPairAuthorizeHandler),
        (r"/api/auth/tv-pair/check", TVPairCheckHandler),

        # Movie Management & Discovery
        (r"/api/movies/categories", CategoriesHandler),
        (r"/api/movies", MoviesHandler),
        (r"/api/movies/([0-9]+)", MovieDetailHandler),

        # Video Streaming & Subtitles
        (r"/api/stream/([0-9]+)", StreamHandler),
        (r"/api/subtitles/(.+)", SubtitleHandler),

        # Watch Progress & History
        (r"/api/progress/([0-9]+)", ProgressHandler),

        # Resumable Chunked Uploads & Media Assets
        (r"/api/upload/chunk", ChunkUploadHandler),
        (r"/api/upload/poster", ImageUploadHandler),
        (r"/api/upload/subtitle", SubtitleUploadHandler),

        # Uploaded Assets static route
        (r"/uploads/(.*)", tornado.web.StaticFileHandler, {"path": str(UPLOADS_DIR)}),

        # Web & Android TV Frontend
        (r"/(.*)", tornado.web.StaticFileHandler, {
            "path": str(WEB_DIR),
            "default_filename": "index.html"
        }),
    ]

    settings = {
        "debug": DEBUG,
        "cookie_secret": "cinecloud-ultra-secure-cookie-signature-secret",
        "compress_response": True,
        "max_buffer_size": 1024 * 1024 * 1024, # 1 GB
        "max_body_size": 1024 * 1024 * 1024,
    }

    return tornado.web.Application(handlers, **settings)

def main():
    print("=" * 60)
    print("  [CineCloud] - Personal Movie Streaming Platform")
    print("=" * 60)
    print("  Initializing database & media storage...")
    init_db()

    app = make_app()
    server = tornado.httpserver.HTTPServer(app, max_buffer_size=1024*1024*1024, max_body_size=1024*1024*1024)
    server.listen(PORT, address=HOST)

    print(f"  [+] CineCloud Server listening on: http://localhost:{PORT}")
    print(f"  [+] Android TV Leanback interface: http://localhost:{PORT}/#tv")
    print(f"  [+] Admin Upload Studio:           http://localhost:{PORT}/#admin")
    print(f"  [+] Default Admin credentials:     admin / admin123")
    print(f"  [+] Default Viewer credentials:    viewer / cinecloud2026")
    print("=" * 60)

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("\nShutting down CineCloud server gracefully...")

if __name__ == "__main__":
    main()
