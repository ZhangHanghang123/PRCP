"""PRCP JWT 认证"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/prcp/api/auth/login", auto_error=False)


def _hash_pw(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_password(plain: str, hashed: str) -> bool:
    return _hash_pw(plain) == hashed


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub", "0"))
        username = payload.get("username", "")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    row = db.execute(
        text("SELECT id, username, display_name, role, status FROM sys_user WHERE id=:id AND is_deleted=0"),
        {"id": user_id},
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return {"id": row[0], "username": row[1], "display_name": row[2] or row[1], "role": row[3], "status": row[4]}


def init_admin(db: Session) -> None:
    """确保默认 admin 用户存在"""
    row = db.execute(text("SELECT id FROM sys_user WHERE username='admin'")).first()
    if row:
        return
    db.execute(
        text("""INSERT INTO sys_user (username, password_hash, display_name, role, status, created_by, updated_by)
                VALUES ('admin', :pwd, '系统管理员', 'admin', 1, 1, 1)"""),
        {"pwd": _hash_pw("admin123")},
    )
    db.commit()