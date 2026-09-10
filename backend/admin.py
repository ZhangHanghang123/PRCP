"""PRCP 系统管理 API — 用户 / 角色 / 字典"""
import hashlib
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["系统管理"])


def _hash_pw(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


# ============== 用户管理 ==============
class UserIn(BaseModel):
    username: str
    password: Optional[str] = None  # 仅创建/重置时使用
    display_name: Optional[str] = None
    role: str = "user"
    status: int = 1
    role_ids: List[int] = []        # 关联角色


class UserPwdIn(BaseModel):
    old_password: Optional[str] = None  # 改自己密码时需要
    new_password: str


@router.get("/users")
async def list_users(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["u.is_deleted=0"]
    params: dict = {}
    if keyword:
        where.append("(u.username LIKE :kw OR u.display_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if status is not None:
        where.append("u.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT u.id, u.username, u.display_name, u.role, u.status,
                       u.created_at, u.updated_at,
                       (SELECT COUNT(*) FROM sys_user_role ur WHERE ur.user_id=u.id) AS role_count
                FROM sys_user u
                WHERE {' AND '.join(where)}
                ORDER BY u.id"""),
        params,
    ).fetchall()
    # 取所有用户的角色
    user_ids = [r[0] for r in rows]
    roles_by_user: dict = {}
    if user_ids:
        rr = db.execute(
            text("""SELECT ur.user_id, r.id, r.role_code, r.role_name
                    FROM sys_user_role ur
                    JOIN sys_role r ON r.id=ur.role_id AND r.is_deleted=0
                    WHERE ur.user_id IN :ids"""),
            {"ids": tuple(user_ids)},
        ).fetchall()
        for uid, rid, rc, rn in rr:
            roles_by_user.setdefault(uid, []).append({"id": rid, "role_code": rc, "role_name": rn})
    return {"items": [{
        "id": r[0], "username": r[1], "display_name": r[2] or r[1],
        "role": r[3], "status": r[4],
        "created_at": r[5].isoformat() if r[5] else None,
        "updated_at": r[6].isoformat() if r[6] else None,
        "role_count": r[7], "roles": roles_by_user.get(r[0], []),
    } for r in rows]}


@router.post("/users")
async def create_user(p: UserIn, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    if not p.password:
        raise HTTPException(400, "新建用户必须设置初始密码")
    exist = db.execute(
        text("SELECT id FROM sys_user WHERE username=:u AND is_deleted=0"),
        {"u": p.username},
    ).first()
    if exist:
        raise HTTPException(400, f"用户名 {p.username} 已存在")
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        new_id = db.execute(
            text("""INSERT INTO sys_user (username, password_hash, display_name, role, status, created_by, updated_by)
                    VALUES (:u, :p, :n, :r, :s, :c, :c)"""),
            {"u": p.username, "p": _hash_pw(p.password),
             "n": p.display_name or p.username, "r": p.role, "s": p.status, "c": uid},
        ).lastrowid
        # 关联角色
        for rid in p.role_ids:
            db.execute(
                text("INSERT INTO sys_user_role (user_id, role_id) VALUES (:u, :r)"),
                {"u": new_id, "r": rid},
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"创建失败: {e}")
    return {"id": new_id, "message": "ok"}


@router.put("/users/{uid}")
async def update_user(uid: int, p: UserIn, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    exist = db.execute(
        text("SELECT id FROM sys_user WHERE id=:i AND is_deleted=0"),
        {"i": uid},
    ).first()
    if not exist:
        raise HTTPException(404, "用户不存在")
    editor = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        # 更新密码（如提供）
        if p.password:
            db.execute(
                text("UPDATE sys_user SET password_hash=:p WHERE id=:i"),
                {"p": _hash_pw(p.password), "i": uid},
            )
        db.execute(
            text("""UPDATE sys_user SET display_name=:n, role=:r, status=:s, updated_by=:u
                WHERE id=:i"""),
            {"n": p.display_name, "r": p.role, "s": p.status, "u": editor, "i": uid},
        )
        # 重置角色关联
        db.execute(text("DELETE FROM sys_user_role WHERE user_id=:u"), {"u": uid})
        for rid in p.role_ids:
            db.execute(
                text("INSERT INTO sys_user_role (user_id, role_id) VALUES (:u, :r)"),
                {"u": uid, "r": rid},
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"更新失败: {e}")
    return {"id": uid, "message": "ok"}


@router.delete("/users/{uid}")
async def delete_user(uid: int, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    if uid == 1:
        raise HTTPException(400, "默认 admin 用户不可删除")
    db.execute(
        text("UPDATE sys_user SET is_deleted=1 WHERE id=:i"),
        {"i": uid},
    )
    db.execute(text("DELETE FROM sys_user_role WHERE user_id=:u"), {"u": uid})
    db.commit()
    return {"id": uid, "message": "ok"}


@router.post("/users/{uid}/reset-password")
async def reset_password(uid: int, p: UserPwdIn, db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
    if not p.new_password or len(p.new_password) < 6:
        raise HTTPException(400, "新密码长度至少 6 位")
    db.execute(
        text("UPDATE sys_user SET password_hash=:p WHERE id=:i"),
        {"p": _hash_pw(p.new_password), "i": uid},
    )
    db.commit()
    return {"message": "ok"}


# ============== 角色管理 ==============
class RoleIn(BaseModel):
    role_code: str
    role_name: str
    description: Optional[str] = None
    status: int = 1


@router.get("/roles")
async def list_roles(
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["is_deleted=0"]
    params: dict = {}
    if keyword:
        where.append("(role_code LIKE :kw OR role_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    rows = db.execute(
        text(f"""SELECT id, role_code, role_name, description, status,
                       created_at, updated_at,
                       (SELECT COUNT(*) FROM sys_user_role ur WHERE ur.role_id=r.id) AS user_count
                FROM sys_role r WHERE {' AND '.join(where)} ORDER BY id"""),
        params,
    ).fetchall()
    return {"items": [{
        "id": r[0], "role_code": r[1], "role_name": r[2], "description": r[3],
        "status": r[4],
        "created_at": r[5].isoformat() if r[5] else None,
        "updated_at": r[6].isoformat() if r[6] else None,
        "user_count": r[7],
    } for r in rows]}


@router.post("/roles")
async def create_role(p: RoleIn, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        rid = db.execute(
            text("""INSERT INTO sys_role (role_code, role_name, description, status, created_by, updated_by)
                    VALUES (:c, :n, :d, :s, :u, :u)"""),
            {"c": p.role_code, "n": p.role_name, "d": p.description,
             "s": p.status, "u": uid},
        ).lastrowid
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"创建失败: {e}")
    return {"id": rid, "message": "ok"}


@router.put("/roles/{rid}")
async def update_role(rid: int, p: RoleIn, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    editor = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        db.execute(
            text("""UPDATE sys_role SET role_code=:c, role_name=:n, description=:d,
                status=:s, updated_by=:u WHERE id=:i"""),
            {"c": p.role_code, "n": p.role_name, "d": p.description,
             "s": p.status, "u": editor, "i": rid},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"更新失败: {e}")
    return {"message": "ok"}


@router.delete("/roles/{rid}")
async def delete_role(rid: int, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    db.execute(text("UPDATE sys_role SET is_deleted=1 WHERE id=:i"), {"i": rid})
    db.execute(text("DELETE FROM sys_user_role WHERE role_id=:r"), {"r": rid})
    db.commit()
    return {"message": "ok"}


# ============== 字典管理 ==============
class DictIn(BaseModel):
    dict_code: str
    dict_name: str
    description: Optional[str] = None
    status: int = 1


class DictItemIn(BaseModel):
    item_code: str
    item_name: str
    item_value: Optional[str] = None
    sort_order: int = 0
    status: int = 1


@router.get("/dicts")
async def list_dicts(keyword: Optional[str] = None,
                     db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    where = ["is_deleted=0"]
    params: dict = {}
    if keyword:
        where.append("(dict_code LIKE :kw OR dict_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    rows = db.execute(
        text(f"""SELECT id, dict_code, dict_name, description, status, created_at, updated_at,
                       (SELECT COUNT(*) FROM sys_dict_item di WHERE di.dict_id=d.id AND di.is_deleted=0) AS item_count
                FROM sys_dict d WHERE {' AND '.join(where)} ORDER BY id"""),
        params,
    ).fetchall()
    return {"items": [{
        "id": r[0], "dict_code": r[1], "dict_name": r[2], "description": r[3],
        "status": r[4],
        "created_at": r[5].isoformat() if r[5] else None,
        "updated_at": r[6].isoformat() if r[6] else None,
        "item_count": r[7],
    } for r in rows]}


@router.post("/dicts")
async def create_dict(p: DictIn, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        did = db.execute(
            text("""INSERT INTO sys_dict (dict_code, dict_name, description, status, created_by, updated_by)
                    VALUES (:c, :n, :d, :s, :u, :u)"""),
            {"c": p.dict_code, "n": p.dict_name, "d": p.description,
             "s": p.status, "u": uid},
        ).lastrowid
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"创建失败: {e}")
    return {"id": did, "message": "ok"}


@router.put("/dicts/{did}")
async def update_dict(did: int, p: DictIn, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    editor = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        db.execute(
            text("""UPDATE sys_dict SET dict_code=:c, dict_name=:n, description=:d,
                status=:s, updated_by=:u WHERE id=:i"""),
            {"c": p.dict_code, "n": p.dict_name, "d": p.description,
             "s": p.status, "u": editor, "i": did},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"更新失败: {e}")
    return {"message": "ok"}


@router.delete("/dicts/{did}")
async def delete_dict(did: int, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    db.execute(text("UPDATE sys_dict SET is_deleted=1 WHERE id=:i"), {"i": did})
    db.execute(text("UPDATE sys_dict_item SET is_deleted=1 WHERE dict_id=:d"), {"d": did})
    db.commit()
    return {"message": "ok"}


# 字典项
@router.get("/dicts/{did}/items")
async def list_dict_items(did: int, db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
    rows = db.execute(
        text("""SELECT id, dict_id, item_code, item_name, item_value, sort_order, status
            FROM sys_dict_item WHERE dict_id=:d AND is_deleted=0 ORDER BY sort_order, id"""),
        {"d": did},
    ).fetchall()
    return {"items": [{
        "id": r[0], "dict_id": r[1], "item_code": r[2], "item_name": r[3],
        "item_value": r[4], "sort_order": r[5], "status": r[6],
    } for r in rows]}


@router.post("/dicts/{did}/items")
async def create_dict_item(did: int, p: DictItemIn, db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        iid = db.execute(
            text("""INSERT INTO sys_dict_item
                (dict_id, item_code, item_name, item_value, sort_order, status, created_by, updated_by)
                VALUES (:d, :c, :n, :v, :o, :s, :u, :u)"""),
            {"d": did, "c": p.item_code, "n": p.item_name, "v": p.item_value,
             "o": p.sort_order, "s": p.status, "u": uid},
        ).lastrowid
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"创建失败: {e}")
    return {"id": iid, "message": "ok"}


@router.put("/dict-items/{iid}")
async def update_dict_item(iid: int, p: DictItemIn, db: Session = Depends(get_db),
                           user=Depends(get_current_user)):
    editor = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        db.execute(
            text("""UPDATE sys_dict_item SET item_code=:c, item_name=:n, item_value=:v,
                sort_order=:o, status=:s, updated_by=:u WHERE id=:i"""),
            {"c": p.item_code, "n": p.item_name, "v": p.item_value,
             "o": p.sort_order, "s": p.status, "u": editor, "i": iid},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"更新失败: {e}")
    return {"message": "ok"}


@router.delete("/dict-items/{iid}")
async def delete_dict_item(iid: int, db: Session = Depends(get_db),
                           user=Depends(get_current_user)):
    db.execute(text("UPDATE sys_dict_item SET is_deleted=1 WHERE id=:i"), {"i": iid})
    db.commit()
    return {"message": "ok"}