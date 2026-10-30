import sqlite3
import json
import time
from typing import List, Dict, Any, Optional
from backend.config import DB_PATH
from backend.auth import hash_password

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'viewer', -- 'admin' or 'viewer'
        created_at INTEGER NOT NULL
    );
    """)
    
    # 2. Movies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        release_year INTEGER,
        genre TEXT, -- comma-separated or JSON list
        duration INTEGER DEFAULT 0, -- in seconds
        poster_url TEXT,
        backdrop_url TEXT,
        video_path TEXT NOT NULL,
        resolution TEXT DEFAULT '1080p', -- '4K', '1080p', '720p', etc.
        video_format TEXT DEFAULT 'mp4',
        file_size INTEGER DEFAULT 0,
        rating REAL DEFAULT 8.0,
        is_featured INTEGER DEFAULT 0,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    );
    """)
    
    # 3. Subtitles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subtitles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        label TEXT NOT NULL, -- e.g. "English", "Spanish"
        language_code TEXT NOT NULL, -- "en", "es"
        file_path TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
    );
    """)
    
    # 4. Audio Tracks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audio_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        label TEXT NOT NULL, -- e.g. "English (5.1 Dolby)", "Original Stereo"
        language_code TEXT NOT NULL,
        file_path TEXT,
        is_default INTEGER DEFAULT 1,
        FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
    );
    """)
    
    # 5. Watch Progress table (for Resume Watching across devices)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watch_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        current_time REAL NOT NULL DEFAULT 0.0,
        duration REAL NOT NULL DEFAULT 0.0,
        is_completed INTEGER DEFAULT 0,
        updated_at INTEGER NOT NULL,
        UNIQUE(user_id, movie_id),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
    );
    """)
    
    # 6. Device Pairings (for seamless Android TV code pairing like YouTube/Netflix)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS device_pairings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pairing_code TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        token TEXT,
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'expired'
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
    );
    """)
    
    # 7. Transcoding Jobs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transcode_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
        progress INTEGER DEFAULT 0,
        output_hls_path TEXT,
        error_message TEXT,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    
    # Seed default Admin & Viewer if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        now = int(time.time())
        admin_pass = hash_password("admin123")
        viewer_pass = hash_password("cinecloud2026")
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ("admin", "admin@cinecloud.local", admin_pass, "admin", now)
        )
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ("viewer", "viewer@cinecloud.local", viewer_pass, "viewer", now)
        )
        conn.commit()
        print("[OK] Created default users: admin (admin123) and viewer (cinecloud2026)")
        
    # Seed high-quality demo movies if library is empty
    cursor.execute("SELECT COUNT(*) as count FROM movies")
    count = cursor.fetchone()['count']
    if count == 0:
        seed_demo_movies(conn)
        
    conn.close()

def seed_demo_movies(conn):
    cursor = conn.cursor()
    now = int(time.time())
    
    demo_movies = [
        {
            "title": "Cosmic Odyssey: Beyond Horizons",
            "description": "When an interstellar anomaly appears near Saturn, an elite expedition voyages into uncharted celestial frontiers, confronting time dilation, rogue exoplanets, and the ultimate origins of cosmic intelligence.",
            "release_year": 2025,
            "genre": "Sci-Fi, Adventure, Mystery",
            "duration": 7440, # 2h 4m
            "poster_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80",
            "backdrop_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80",
            "video_path": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "resolution": "4K Ultra HD",
            "video_format": "mp4",
            "file_size": 4294967296,
            "rating": 9.2,
            "is_featured": 1
        },
        {
            "title": "Neon Syndicate",
            "description": "In a rain-drenched cyberpunk metropolis of 2088, an ex-enforcer and a rogue cyberneticist uncover a neural manipulation syndicate operating within the highest echelons of the synthetic conglomerate.",
            "release_year": 2024,
            "genre": "Cyberpunk, Action, Thriller",
            "duration": 6820,
            "poster_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=600&q=80",
            "backdrop_url": "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=1600&q=80",
            "video_path": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
            "resolution": "4K Ultra HD",
            "video_format": "mp4",
            "file_size": 3810000000,
            "rating": 8.7,
            "is_featured": 1
        },
        {
            "title": "The Last Sentinel",
            "description": "Stationed alone at an orbital defense array guarding an irradiated Earth, a lone commander intercepts an encrypted distress signal from deep space that could alter humanity's destiny.",
            "release_year": 2024,
            "genre": "Sci-Fi, Drama",
            "duration": 5800,
            "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80",
            "backdrop_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1600&q=80",
            "video_path": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
            "resolution": "1080p Full HD",
            "video_format": "mp4",
            "file_size": 2400000000,
            "rating": 8.4,
            "is_featured": 0
        },
        {
            "title": "Shadows of Kyoto",
            "description": "An undercover operative infiltrates an ancient shadow order hidden behind modern international espionage, where honor and betrayal clash under neon-lit bamboo sanctuaries.",
            "release_year": 2023,
            "genre": "Action, Crime, Mystery",
            "duration": 6480,
            "poster_url": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=600&q=80",
            "backdrop_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=1600&q=80",
            "video_path": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
            "resolution": "4K Ultra HD",
            "video_format": "mp4",
            "file_size": 3100000000,
            "rating": 8.9,
            "is_featured": 0
        },
        {
            "title": "Submerged Protocol",
            "description": "Deep within the Mariana Trench, an underwater abyssal research station loses communication after drilling into a subterranean chamber holding prehistoric organic energy.",
            "release_year": 2025,
            "genre": "Sci-Fi, Horror, Thriller",
            "duration": 6120,
            "poster_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=600&q=80",
            "backdrop_url": "https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1600&q=80",
            "video_path": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "resolution": "1080p Full HD",
            "video_format": "mp4",
            "file_size": 1950000000,
            "rating": 8.1,
            "is_featured": 0
        },
        {
            "title": "Chronicles of Aethelgard",
            "description": "A mythical epic chronicling the rise of the celestial guardians who protect the ancient realm against the rising tide of primordial chaos.",
            "release_year": 2024,
            "genre": "Fantasy, Adventure",
            "duration": 8100,
            "poster_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80",
            "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1600&q=80",
            "video_path": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
            "resolution": "4K Ultra HD",
            "video_format": "mp4",
            "file_size": 4100000000,
            "rating": 9.0,
            "is_featured": 0
        }
    ]
    
    for m in demo_movies:
        cursor.execute("""
            INSERT INTO movies (
                title, description, release_year, genre, duration,
                poster_url, backdrop_url, video_path, resolution, video_format,
                file_size, rating, is_featured, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["title"], m["description"], m["release_year"], m["genre"], m["duration"],
            m["poster_url"], m["backdrop_url"], m["video_path"], m["resolution"], m["video_format"],
            m["file_size"], m["rating"], m["is_featured"], now, now
        ))
        movie_id = cursor.lastrowid
        
        # Add default subtitles
        cursor.execute("""
            INSERT INTO subtitles (movie_id, label, language_code, file_path, is_default)
            VALUES (?, 'English (CC)', 'en', '/api/subtitles/sample_en.vtt', 1)
        """, (movie_id,))
        cursor.execute("""
            INSERT INTO subtitles (movie_id, label, language_code, file_path, is_default)
            VALUES (?, 'Spanish', 'es', '/api/subtitles/sample_es.vtt', 0)
        """, (movie_id,))
        
        # Add default audio tracks
        cursor.execute("""
            INSERT INTO audio_tracks (movie_id, label, language_code, is_default)
            VALUES (?, 'English 5.1 Surround', 'en', 1)
        """, (movie_id,))
        cursor.execute("""
            INSERT INTO audio_tracks (movie_id, label, language_code, is_default)
            VALUES (?, 'English Stereo (Original)', 'en', 0)
        """, (movie_id,))
        
    conn.commit()
    print(f"[OK] Seeded {len(demo_movies)} initial movies with subtitles and audio tracks")

def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    if not row:
        return None
    return dict(row)
