import base64
import hashlib
import hmac
import json
import time
from typing import Optional, Dict, Any
from backend.config import SECRET_KEY, JWT_EXPIRATION_HOURS

def hash_password(password: str) -> str:
    salt = base64.b64encode(hashlib.sha256(str(time.time()).encode()).digest()[:16]).decode('ascii')
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${base64.b64encode(key).decode('ascii')}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, key_b64 = stored_hash.split('$')
        key = base64.b64decode(key_b64.encode('ascii'))
        computed_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hmac.compare_digest(key, computed_key)
    except Exception:
        return False

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

def _b64url_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4)) if len(data_str) % 4 != 0 else ''
    return base64.urlsafe_b64decode((data_str + padding).encode('ascii'))

def create_token(payload: Dict[str, Any], expires_in_hours: int = JWT_EXPIRATION_HOURS) -> str:
    token_data = dict(payload)
    token_data['exp'] = int(time.time()) + (expires_in_hours * 3600)
    token_data['iat'] = int(time.time())
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_bytes = json.dumps(token_data, separators=(',', ':')).encode('utf-8')
    
    header_b64 = _b64url_encode(header_bytes)
    payload_b64 = _b64url_encode(payload_bytes)
    
    signing_input = f"{header_b64}.{payload_b64}".encode('ascii')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        signing_input = f"{header_b64}.{payload_b64}".encode('ascii')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        if payload.get('exp', 0) < time.time():
            return None  # Expired
            
        return payload
    except Exception:
        return None

def extract_user_from_request(handler) -> Optional[Dict[str, Any]]:
    # Check Authorization header (Bearer <token>)
    auth_header = handler.request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    
    # Or check token from query param (useful for video stream tags and Android TV ExoPlayer)
    if not token:
        token = handler.get_query_argument("token", default=None)
        
    # Or check cookie
    if not token:
        token = handler.get_secure_cookie("cinecloud_token")
        if token:
            token = token.decode('utf-8')
            
    if not token:
        return None
        
    return decode_token(token)
