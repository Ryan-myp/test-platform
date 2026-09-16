"""Authentication API"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import text as sa_text
from typing import Any, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])

async def get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/register")
async def register(data: Dict[str, Any], session=Depends(get_db)):
    """Register new user"""
    from app.auth.security import hash_password
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "")
    role = data.get("role", "member")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    r = await session.execute(sa_text("SELECT id FROM users WHERE username = :u"), {"u": username})
    if r.fetchone():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hash_password(password)
    await session.execute(sa_text("""
        INSERT INTO users (username, password_hash, email, role, is_active, created_at)
        VALUES (:username, :password_hash, :email, :role, 1, datetime('now'))
    """), {"username": username, "password_hash": hashed, "email": email, "role": role})
    await session.commit()
    return {"message": "User created successfully", "username": username}

@router.post("/login", response_model=Dict[str, Any])
async def login(data: Dict[str, Any], session=Depends(get_db)):
    """Login and get token"""
    from app.auth.security import verify_password, create_access_token
    username = data.get("username", "").strip()
    password = data.get("password", "")
    r = await session.execute(sa_text("SELECT id, username, password_hash, role FROM users WHERE username = :u"), {"u": username})
    user = r.fetchone()
    if not user or not verify_password(password, user[2]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await session.execute(sa_text("UPDATE users SET last_login = datetime('now') WHERE id = :id"), {"id": user[0]})
    await session.commit()
    token = create_access_token({"sub": user[1], "uid": user[0], "role": user[3]})
    return {"access_token": token, "token_type": "bearer", "expires_in": 86400, "user": {"id": user[0], "username": user[1], "role": user[3]}}

@router.get("/users")
async def list_users(session=Depends(get_db), current_user: dict = Depends(lambda: None)):
    """List users - admin only"""
    if current_user and current_user.get("role") not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Admin access required")
    r = await session.execute(sa_text("SELECT id, username, email, role, is_active, created_at FROM users ORDER BY id"))
    users = []
    for row in r.fetchall():
        users.append({"id": row[0], "username": row[1], "email": row[2] or "", "role": row[3], "is_active": bool(row[4]), "created_at": row[5]})
    return {"users": users, "total": len(users)}
