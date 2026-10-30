import json
import time
import random
import string
import tornado.web
from backend.database import get_db, row_to_dict
from backend.auth import hash_password, verify_password, create_token, extract_user_from_request

class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Range")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()

    def get_json_body(self):
        try:
            return json.loads(self.request.body.decode('utf-8'))
        except Exception:
            return {}

    def get_current_user_data(self):
        return extract_user_from_request(self)

    def write_error_json(self, status_code: int, message: str):
        self.set_status(status_code)
        self.write({"error": True, "message": message})

class RegisterHandler(BaseHandler):
    def post(self):
        data = self.get_json_body()
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        role = data.get("role", "viewer")

        if not username or not email or not password:
            return self.write_error_json(400, "Username, email, and password are required")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            conn.close()
            return self.write_error_json(409, "Username or email already exists")

        now = int(time.time())
        pwd_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, email, pwd_hash, role, now)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        token = create_token({"user_id": user_id, "username": username, "role": role})
        self.write({
            "token": token,
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "role": role
            }
        })

class LoginHandler(BaseHandler):
    def post(self):
        data = self.get_json_body()
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return self.write_error_json(400, "Username and password required")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
        user = cursor.fetchone()
        conn.close()

        if not user or not verify_password(password, user["password_hash"]):
            return self.write_error_json(401, "Invalid credentials")

        token = create_token({
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"]
        })

        self.write({
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            }
        })

class MeHandler(BaseHandler):
    def get(self):
        user_payload = self.get_current_user_data()
        if not user_payload:
            return self.write_error_json(401, "Unauthorized")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_payload["user_id"],))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return self.write_error_json(404, "User not found")

        self.write({"user": row_to_dict(user)})

class TVPairRequestHandler(BaseHandler):
    """Generates a 6-character code for easy remote TV sign-in"""
    def post(self):
        code = "".join(random.choices(string.ascii_uppercase + "23456789", k=6))
        now = int(time.time())
        expires = now + 600 # 10 minutes
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO device_pairings (pairing_code, status, created_at, expires_at) VALUES (?, 'pending', ?, ?)",
            (code, now, expires)
        )
        conn.commit()
        conn.close()
        
        self.write({
            "pairing_code": code,
            "expires_in": 600,
            "url": f"/pair?code={code}"
        })

class TVPairAuthorizeHandler(BaseHandler):
    """User visits /pair on phone or laptop to approve TV"""
    def post(self):
        user_payload = self.get_current_user_data()
        if not user_payload:
            return self.write_error_json(401, "Please log in first")
            
        data = self.get_json_body()
        code = data.get("code", "").strip().upper()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_pairings WHERE pairing_code = ? AND status = 'pending'", (code,))
        pairing = cursor.fetchone()
        
        if not pairing or pairing["expires_at"] < time.time():
            conn.close()
            return self.write_error_json(400, "Invalid or expired pairing code")
            
        tv_token = create_token({
            "user_id": user_payload["user_id"],
            "username": user_payload["username"],
            "role": user_payload["role"]
        }, expires_in_hours=24 * 30) # 30 days for TV device
        
        cursor.execute(
            "UPDATE device_pairings SET status = 'approved', user_id = ?, token = ? WHERE id = ?",
            (user_payload["user_id"], tv_token, pairing["id"])
        )
        conn.commit()
        conn.close()
        
        self.write({"success": True, "message": "TV successfully authorized!"})

class TVPairCheckHandler(BaseHandler):
    """TV polls this endpoint to detect when user has authorized it"""
    def get(self):
        code = self.get_query_argument("code", "").strip().upper()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_pairings WHERE pairing_code = ?", (code,))
        pairing = cursor.fetchone()
        conn.close()
        
        if not pairing:
            return self.write({"status": "invalid"})
        if pairing["status"] == "approved":
            return self.write({
                "status": "approved",
                "token": pairing["token"]
            })
        if pairing["expires_at"] < time.time():
            return self.write({"status": "expired"})
            
        return self.write({"status": "pending"})
