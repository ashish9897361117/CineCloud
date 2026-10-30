import time
from backend.handlers.auth_handlers import BaseHandler
from backend.database import get_db, row_to_dict

class ProgressHandler(BaseHandler):
    def get(self, movie_id: str):
        user = self.get_current_user_data()
        if not user:
            return self.write({"progress": None})

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watch_progress WHERE user_id = ? AND movie_id = ?", (user["user_id"], movie_id))
        prog = cursor.fetchone()
        conn.close()

        self.write({"progress": row_to_dict(prog)})

    def post(self, movie_id: str):
        user = self.get_current_user_data()
        if not user:
            return self.write_error_json(401, "Unauthorized")

        data = self.get_json_body()
        current_time = float(data.get("currentTime", 0.0))
        duration = float(data.get("duration", 0.0))
        is_completed = 1 if data.get("isCompleted", False) else 0

        # If user watched more than 92% of the movie, mark as completed
        if duration > 0 and (current_time / duration) > 0.92:
            is_completed = 1

        now = int(time.time())

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO watch_progress (user_id, movie_id, current_time, duration, is_completed, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, movie_id) DO UPDATE SET
                current_time = excluded.current_time,
                duration = excluded.duration,
                is_completed = excluded.is_completed,
                updated_at = excluded.updated_at
        """, (user["user_id"], movie_id, current_time, duration, is_completed, now))
        conn.commit()
        conn.close()

        self.write({
            "success": True,
            "saved": {
                "movie_id": int(movie_id),
                "currentTime": current_time,
                "duration": duration,
                "isCompleted": bool(is_completed)
            }
        })
