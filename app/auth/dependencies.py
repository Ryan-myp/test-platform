from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text as sa_text
import logging

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    from app.auth.security import decode_access_token
    from app.database import AsyncSessionLocal
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    username = payload.get("sub")
    if not username:
        raise credentials_exception
    async with AsyncSessionLocal() as session:
        r = await session.execute(sa_text("SELECT id, username, email, role, is_active FROM users WHERE username = :u"), {"u": username})
        user = r.fetchone()
    if not user:
        raise credentials_exception
    return {"id": user[0], "username": user[1], "email": user[2], "role": user[3], "is_active": bool(user[4])}

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ("admin", "manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
