"""PRCP 通用字典 API

提供：
- GET    /prcp/api/dict/types                  所有字典类别
- GET    /prcp/api/dict/{dict_type}            单类别字典项
- GET    /prcp/api/dict/types/items            一次性全量拉取（前端 Context 模式用）
- POST   /prcp/api/dict                        新增字典项
- PUT    /prcp/api/dict/{did}                  更新字典项
- DELETE /prcp/api/dict/{did}                  软删除
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/dict", tags=["字典管理"])


# ============== Schemas ==============
class DictIn(BaseModel):
    dict_type: str
    dict_key: str
    dict_label: str
    color: Optional[str] = None
    sort_order: int = 0
    status: str = "ACTIVE"
    description: Optional[str] = None
    extra_json: Optional[dict] = None


# ============== APIs ==============
@router.get("/types")
async def list_types(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """所有字典类别 + 各类别数量"""
    rows = db.execute(
        text("""SELECT dict_type, COUNT(*) cnt
                FROM sys_dict
                WHERE is_deleted=0 AND status='ACTIVE'
                GROUP BY dict_type
                ORDER BY dict_type"""),
    ).fetchall()
    return {
        "items": [{"dict_type": r[0], "count": r[1]} for r in rows]
    }


@router.get("/types/items")
async def list_all_items(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """一次性拉取所有字典项（前端 DictProvider 用）"""
    rows = db.execute(
        text("""SELECT id, dict_type, dict_key, dict_label, color, sort_order, status, extra_json
                FROM sys_dict
                WHERE is_deleted=0 AND status='ACTIVE'
                ORDER BY dict_type, sort_order, dict_key"""),
    ).fetchall()
    grouped: dict = {}
    for r in rows:
        grouped.setdefault(r[1], []).append({
            "id": r[0],
            "dict_type": r[1],
            "dict_key": r[2],
            "dict_label": r[3],
            "color": r[4],
            "sort_order": r[5],
            "status": r[6],
            "extra": __import__('json').loads(r[7]) if r[7] else None,
        })
    return {"items": grouped}


@router.get("/{dict_type}")
async def list_by_type(dict_type: str, keyword: str = "", include_inactive: bool = False,
                       db: Session = Depends(get_db), user=Depends(get_current_user)):
    """按类型拉取字典项（管理端默认查看所有状态）"""
    where = ["dict_type=:t", "is_deleted=0"]
    params: dict = {"t": dict_type}
    if not include_inactive:
        where.append("status='ACTIVE'")
    if keyword:
        where.append("(dict_key LIKE :kw OR dict_label LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    sql = f"""SELECT id, dict_type, dict_key, dict_label, color, sort_order, status, extra_json
              FROM sys_dict
              WHERE {' AND '.join(where)}
              ORDER BY sort_order, dict_key"""
    rows = db.execute(text(sql), params).fetchall()
    import json as _json
    return {
        "dict_type": dict_type,
        "items": [
            {
                "id": r[0],
                "dict_type": r[1],
                "dict_key": r[2],
                "dict_label": r[3],
                "color": r[4],
                "sort_order": r[5],
                "status": r[6],
                "extra": _json.loads(r[7]) if r[7] else None,
            } for r in rows
        ],
    }


@router.post("")
async def create_dict(p: DictIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """新增字典项"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    import json as _json
    try:
        rid = db.execute(
            text("""INSERT INTO sys_dict
                (dict_type, dict_key, dict_label, color, sort_order, status, description, extra_json, created_by, updated_by)
                VALUES (:t, :k, :l, :c, :so, :s, :d, :e, :u, :u)"""),
            {
                "t": p.dict_type, "k": p.dict_key, "l": p.dict_label,
                "c": p.color, "so": p.sort_order, "s": p.status,
                "d": p.description, "e": _json.dumps(p.extra_json) if p.extra_json else None,
                "u": uid,
            },
        ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "dict_type": p.dict_type, "dict_key": p.dict_key}


@router.put("/{did}")
async def update_dict(did: int, p: DictIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """更新字典项"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    import json as _json
    r = db.execute(
        text("""UPDATE sys_dict SET
            dict_type=:t, dict_key=:k, dict_label=:l, color=:c, sort_order=:so,
            status=:s, description=:d, extra_json=:e, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {
            "t": p.dict_type, "k": p.dict_key, "l": p.dict_label,
            "c": p.color, "so": p.sort_order, "s": p.status,
            "d": p.description, "e": _json.dumps(p.extra_json) if p.extra_json else None,
            "u": uid, "id": did,
        },
    )
    if r.rowcount == 0:
        raise HTTPException(404, "字典项不存在")
    return {"ok": True}


@router.delete("/{did}")
async def delete_dict(did: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删除字典项"""
    r = db.execute(
        text("UPDATE sys_dict SET is_deleted=1 WHERE id=:id AND is_deleted=0"),
        {"id": did},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "字典项不存在")
    return {"ok": True}
