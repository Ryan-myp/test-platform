"""Authentication utilities - using hashlib for compatibility"""
from datetime import datetime, timedelta
from typing import Optional
import logging
import hashlib
import hmac
import secrets
from jose import JWTError, jwt
from app.config import settings

logger = logging.getLogger(__name__)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except JWTError:
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
