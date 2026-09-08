"""认证路由"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, verify_password
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("SELECT id, username, password_hash, display_name, status FROM sys_user "
             "WHERE username=:u AND is_deleted=0"),
        {"u": form.username},
    ).first()
    if not row or not verify_password(form.password, row[2]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if row[4] != 1:
        raise HTTPException(status_code=403, detail="账号已停用")
    token = create_access_token(row[0], row[1])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": row[0], "username": row[1], "display_name": row[3] or row[1]},
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user