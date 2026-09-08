"""资金组管理 — 头寸组 / 限额组 / 调度组"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/groups", tags=["资金组"])


@router.get("")
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    group_type: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["is_deleted=0"]
    params: dict = {}
    if group_type:
        where.append("group_type=:gt")
        params["gt"] = group_type
    sql_where = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM prcp_group WHERE {sql_where}"), params).scalar() or 0
    rows = db.execute(text(f"""
        SELECT id, group_code, group_name, group_type, currency, total_limit,
               used_limit, status, description, created_at
        FROM prcp_group WHERE {sql_where}
        ORDER BY id DESC LIMIT :lim OFFSET :off
    """), {**params, "lim": page_size, "off": (page - 1) * page_size}).fetchall()
    return {
        "total": total,
        "items": [
            {
                "id": r[0], "group_code": r[1], "group_name": r[2], "group_type": r[3],
                "currency": r[4], "total_limit": float(r[5] or 0),
                "used_limit": float(r[6] or 0),
                "status": r[7], "description": r[8],
                "created_at": r[9].isoformat() if r[9] else None,
            } for r in rows
        ],
    }


@router.post("")
async def create_group(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.execute(text("""
        INSERT INTO prcp_group
          (group_code, group_name, group_type, currency, total_limit, used_limit,
           status, description, created_by, updated_by)
        VALUES (:code,:name,:gt,:cur,:tl,:ul,:st,:desc,:uid,:uid)
    """), {**payload, "uid": user["id"]})
    db.commit()
    return {"message": "ok"}


@router.put("/{gid}")
async def update_group(gid: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    upd = ["group_name", "group_type", "currency", "total_limit", "used_limit", "status", "description"]
    sets, params = [], {"id": gid, "uid": user["id"]}
    for k in upd:
        if k in payload:
            sets.append(f"{k}=:{k}")
            params[k] = payload[k]
    if not sets:
        raise HTTPException(400, "无可更新字段")
    sets += ["updated_by=:uid", "updated_at=NOW()"]
    db.execute(text(f"UPDATE prcp_group SET {', '.join(sets)} WHERE id=:id AND is_deleted=0"), params)
    db.commit()
    return {"message": "ok"}


@router.delete("/{gid}")
async def delete_group(gid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.execute(text("UPDATE prcp_group SET is_deleted=1, updated_by=:uid, updated_at=NOW() WHERE id=:id"),
               {"id": gid, "uid": user["id"]})
    db.commit()
    return {"deleted": gid}