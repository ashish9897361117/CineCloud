import json
import time
from backend.handlers.auth_handlers import BaseHandler
from backend.database import get_db, row_to_dict

class MoviesHandler(BaseHandler):
    def get(self):
        query = self.get_query_argument("query", default="").strip()
        genre = self.get_query_argument("genre", default="").strip()
        year = self.get_query_argument("year", default="").strip()
        sort_by = self.get_query_argument("sort", default="recent")
        limit = int(self.get_query_argument("limit", default=50))
        offset = int(self.get_query_argument("offset", default=0))

        conn = get_db()
        cursor = conn.cursor()

        sql = "SELECT * FROM movies WHERE 1=1"
        params = []

        if query:
            sql += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        if genre and genre.lower() != "all":
            sql += " AND genre LIKE ?"
            params.append(f"%{genre}%")

        if year:
            sql += " AND release_year = ?"
            params.append(int(year))

        if sort_by == "rating":
            sql += " ORDER BY rating DESC"
        elif sort_by == "title":
            sql += " ORDER BY title ASC"
        elif sort_by == "year":
            sql += " ORDER BY release_year DESC"
        else:
            sql += " ORDER BY id DESC"

        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        movies = [row_to_dict(r) for r in cursor.fetchall()]

        # Attach subtitles & audio tracks count
        for m in movies:
            cursor.execute("SELECT id, label, language_code FROM subtitles WHERE movie_id = ?", (m["id"],))
            m["subtitles"] = [row_to_dict(s) for s in cursor.fetchall()]
            cursor.execute("SELECT id, label, language_code FROM audio_tracks WHERE movie_id = ?", (m["id"],))
            m["audio_tracks"] = [row_to_dict(a) for a in cursor.fetchall()]

        conn.close()
        self.write({"movies": movies, "count": len(movies)})

    def post(self):
        user = self.get_current_user_data()
        if not user or user.get("role") != "admin":
            return self.write_error_json(403, "Admin privileges required")

        data = self.get_json_body()
        title = data.get("title", "").strip()
        if not title:
            return self.write_error_json(400, "Title is required")

        conn = get_db()
        cursor = conn.cursor()
        now = int(time.time())

        cursor.execute("""
            INSERT INTO movies (
                title, description, release_year, genre, duration,
                poster_url, backdrop_url, video_path, resolution, video_format,
                file_size, rating, is_featured, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            data.get("description", ""),
            int(data.get("release_year", 2025)),
            data.get("genre", "Action, Sci-Fi"),
            int(data.get("duration", 0)),
            data.get("poster_url", ""),
            data.get("backdrop_url", ""),
            data.get("video_path", ""),
            data.get("resolution", "1080p Full HD"),
            data.get("video_format", "mp4"),
            int(data.get("file_size", 0)),
            float(data.get("rating", 8.0)),
            1 if data.get("is_featured") else 0,
            now, now
        ))
        movie_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.write({"success": True, "movie_id": movie_id})

class MovieDetailHandler(BaseHandler):
    def get(self, movie_id: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        movie = cursor.fetchone()
        if not movie:
            conn.close()
            return self.write_error_json(404, "Movie not found")

        movie_dict = row_to_dict(movie)

        # Get subtitles
        cursor.execute("SELECT * FROM subtitles WHERE movie_id = ?", (movie_id,))
        movie_dict["subtitles"] = [row_to_dict(s) for s in cursor.fetchall()]

        # Get audio tracks
        cursor.execute("SELECT * FROM audio_tracks WHERE movie_id = ?", (movie_id,))
        movie_dict["audio_tracks"] = [row_to_dict(a) for a in cursor.fetchall()]

        # Get user progress if logged in
        user = self.get_current_user_data()
        movie_dict["watch_progress"] = None
        if user:
            cursor.execute("SELECT * FROM watch_progress WHERE user_id = ? AND movie_id = ?", (user["user_id"], movie_id))
            prog = cursor.fetchone()
            if prog:
                movie_dict["watch_progress"] = row_to_dict(prog)

        conn.close()
        self.write({"movie": movie_dict})

    def put(self, movie_id: str):
        user = self.get_current_user_data()
        if not user or user.get("role") != "admin":
            return self.write_error_json(403, "Admin privileges required")

        data = self.get_json_body()
        conn = get_db()
        cursor = conn.cursor()
        now = int(time.time())

        cursor.execute("""
            UPDATE movies SET
                title = COALESCE(?, title),
                description = COALESCE(?, description),
                release_year = COALESCE(?, release_year),
                genre = COALESCE(?, genre),
                duration = COALESCE(?, duration),
                poster_url = COALESCE(?, poster_url),
                backdrop_url = COALESCE(?, backdrop_url),
                resolution = COALESCE(?, resolution),
                rating = COALESCE(?, rating),
                is_featured = COALESCE(?, is_featured),
                updated_at = ?
            WHERE id = ?
        """, (
            data.get("title"),
            data.get("description"),
            data.get("release_year"),
            data.get("genre"),
            data.get("duration"),
            data.get("poster_url"),
            data.get("backdrop_url"),
            data.get("resolution"),
            data.get("rating"),
            1 if data.get("is_featured") else 0 if "is_featured" in data else None,
            now, movie_id
        ))
        conn.commit()
        conn.close()
        self.write({"success": True})

    def delete(self, movie_id: str):
        user = self.get_current_user_data()
        if not user or user.get("role") != "admin":
            return self.write_error_json(403, "Admin privileges required")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        cursor.execute("DELETE FROM subtitles WHERE movie_id = ?", (movie_id,))
        cursor.execute("DELETE FROM audio_tracks WHERE movie_id = ?", (movie_id,))
        cursor.execute("DELETE FROM watch_progress WHERE movie_id = ?", (movie_id,))
        conn.commit()
        conn.close()
        self.write({"success": True})

class CategoriesHandler(BaseHandler):
    """Returns curated rows for modern streaming carousel layout"""
    def get(self):
        conn = get_db()
        cursor = conn.cursor()
        user = self.get_current_user_data()

        # 1. Continue Watching (if user is logged in)
        continue_watching = []
        if user:
            cursor.execute("""
                SELECT m.*, p.current_time, p.duration as progress_duration, p.updated_at as watched_at
                FROM watch_progress p
                JOIN movies m ON p.movie_id = m.id
                WHERE p.user_id = ? AND p.is_completed = 0 AND p.current_time > 10
                ORDER BY p.updated_at DESC
                LIMIT 10
            """, (user["user_id"],))
            continue_watching = [row_to_dict(r) for r in cursor.fetchall()]

        # 2. Featured / Spotlight
        cursor.execute("SELECT * FROM movies WHERE is_featured = 1 ORDER BY rating DESC LIMIT 5")
        featured = [row_to_dict(r) for r in cursor.fetchall()]
        if not featured:
            cursor.execute("SELECT * FROM movies ORDER BY rating DESC LIMIT 5")
            featured = [row_to_dict(r) for r in cursor.fetchall()]

        # 3. Recently Added
        cursor.execute("SELECT * FROM movies ORDER BY id DESC LIMIT 15")
        recently_added = [row_to_dict(r) for r in cursor.fetchall()]

        # 4. Top Rated
        cursor.execute("SELECT * FROM movies ORDER BY rating DESC LIMIT 15")
        top_rated = [row_to_dict(r) for r in cursor.fetchall()]

        # 5. Sci-Fi & Action
        cursor.execute("SELECT * FROM movies WHERE genre LIKE '%Sci-Fi%' OR genre LIKE '%Action%' ORDER BY id DESC LIMIT 15")
        action_scifi = [row_to_dict(r) for r in cursor.fetchall()]

        # 6. Drama & Thriller
        cursor.execute("SELECT * FROM movies WHERE genre LIKE '%Drama%' OR genre LIKE '%Thriller%' OR genre LIKE '%Mystery%' ORDER BY id DESC LIMIT 15")
        drama_thriller = [row_to_dict(r) for r in cursor.fetchall()]

        # 7. All Available Genres list
        cursor.execute("SELECT DISTINCT genre FROM movies")
        genre_set = set()
        for r in cursor.fetchall():
            if r["genre"]:
                for g in r["genre"].split(","):
                    g_strip = g.strip()
                    if g_strip:
                        genre_set.add(g_strip)

        conn.close()

        self.write({
            "featured": featured,
            "continue_watching": continue_watching,
            "sections": [
                {"id": "recent", "title": "Recently Added", "movies": recently_added},
                {"id": "top_rated", "title": "Critically Acclaimed", "movies": top_rated},
                {"id": "action_scifi", "title": "Action & Sci-Fi Universe", "movies": action_scifi},
                {"id": "drama_thriller", "title": "Suspense & Masterpieces", "movies": drama_thriller}
            ],
            "genres": sorted(list(genre_set))
        })
