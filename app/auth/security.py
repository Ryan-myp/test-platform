"""Authentication utilities - pure Python implementation"""
from datetime import datetime, timedelta
from typing import Optional
import logging
import hashlib
import hmac
import secrets
import json
import base64

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _base64url_decode(s: str) -> bytes:
    s = s + '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token without jose dependency"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    
    header = _base64url_encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    payload = _base64url_encode(json.dumps(to_encode).encode())
    
    # Simplified signing (in production, use proper HMAC)
    signing_input = f"{header}.{payload}"
    secret = "testpilot-secret-key"  # Would come from settings
    signature = _base64url_encode(
        hashlib.sha256(f"{signing_input}{secret}".encode()).digest()
    )
    
    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> Optional[dict]:
    """Decode JWT token without jose dependency"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        payload = json.loads(_base64url_decode(parts[1]))
        
        # Check expiration
        exp = payload.get('exp')
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return None
        
        return payload
    except Exception:
        return None


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    if '$' not in hashed_password:
        return False
    salt, expected = hashed_password.split('$', 1)
    actual = hashlib.sha256(f"{salt}:{plain_password}".encode()).hexdigest()
    return hmac.compare_digest(actual, expected)
