import time
import json
import urllib.request
import urllib.parse
import threading
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.config import PORT
from backend.database import init_db
from backend.server import make_app
import tornado.ioloop
import tornado.httpserver

def run_tests(loop):
    time.sleep(1.0)
    base_url = f"http://127.0.0.1:{PORT}"
    print(f"\n[TESTING] Probing CineCloud API at {base_url}...", flush=True)

    try:
        # 1. Test Static Index HTML
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8')
            assert "CineCloud" in content, "CineCloud branding not in index.html"
            print("[PASS] 1. Static Web / Android TV Leanback Frontend served successfully (HTTP 200)", flush=True)

        # 2. Test Login API
        login_data = json.dumps({"username": "admin", "password": "admin123"}).encode('utf-8')
        req = urllib.request.Request(
            f"{base_url}/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            assert "token" in data, "Token missing in login response"
            token = data["token"]
            print(f"[PASS] 2. User Authentication & JWT generation successful (Token: {token[:18]}...)", flush=True)

        # 3. Test Categories API
        req = urllib.request.Request(
            f"{base_url}/api/movies/categories",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req) as resp:
            cat_data = json.loads(resp.read().decode('utf-8'))
            assert len(cat_data["featured"]) > 0, "No featured movies returned"
            assert len(cat_data["sections"]) > 0, "No category sections returned"
            print(f"[PASS] 3. Movie Discovery Categories returned ({len(cat_data['sections'])} sections, {len(cat_data['genres'])} genres)", flush=True)

        # 4. Test Movie Detail API
        req = urllib.request.Request(f"{base_url}/api/movies/1")
        with urllib.request.urlopen(req) as resp:
            movie_data = json.loads(resp.read().decode('utf-8'))
            assert "movie" in movie_data
            m = movie_data["movie"]
            print(f"[PASS] 4. Movie Details retrieved: '{m['title']}' ({m['release_year']}) - Subtitles: {len(m['subtitles'])}, Audio: {len(m['audio_tracks'])}", flush=True)

        # 5. Test Watch Progress Sync (Resume Watching)
        progress_data = json.dumps({
            "currentTime": 2540.5,
            "duration": 7440.0,
            "isCompleted": False
        }).encode('utf-8')
        req = urllib.request.Request(
            f"{base_url}/api/progress/1",
            data=progress_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        with urllib.request.urlopen(req) as resp:
            prog_res = json.loads(resp.read().decode('utf-8'))
            assert prog_res.get("success") is True
            print("[PASS] 5. Playback Progress Synced successfully (currentTime: 2540.5s)", flush=True)

        # 6. Verify Continue Watching rail now includes Movie 1
        req = urllib.request.Request(
            f"{base_url}/api/movies/categories",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req) as resp:
            cat_data = json.loads(resp.read().decode('utf-8'))
            cw = cat_data.get("continue_watching", [])
            assert len(cw) > 0, "Movie 1 not found in Continue Watching rail"
            assert cw[0]["id"] == 1
            print(f"[PASS] 6. Continue Watching Rail updated across devices: '{cw[0]['title']}' at {cw[0]['current_time']}s", flush=True)

        # 7. Test Subtitle WebVTT serving
        req = urllib.request.Request(f"{base_url}/api/subtitles/sample_en.vtt")
        with urllib.request.urlopen(req) as resp:
            vtt = resp.read().decode('utf-8')
            assert "WEBVTT" in vtt
            print("[PASS] 7. Subtitles WebVTT delivery verified", flush=True)

        print("\n[ALL TESTS PASSED] CineCloud core server & APIs are 100% operational!\n", flush=True)
    except Exception as e:
        print(f"\n[TEST FAILED]: {e}", flush=True)
    finally:
        loop.add_callback(loop.stop)

if __name__ == "__main__":
    init_db()
    app = make_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(PORT, address="127.0.0.1")
    loop = tornado.ioloop.IOLoop.current()
    t = threading.Thread(target=run_tests, args=(loop,))
    t.daemon = True
    t.start()
    loop.start()
