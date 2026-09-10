"""账户册维护 API — 方案 + 树形节点"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/coa", tags=["账户册"])


# ---------- Schemas ----------
class SchemeIn(BaseModel):
    scheme_code: str
    scheme_name: str
    description: Optional[str] = None
    status: str = "ACTIVE"


class NodeIn(BaseModel):
    scheme_id: int
    node_code: str
    node_name: str
    parent_id: Optional[int] = None
    node_type: Optional[str] = None
    sort_order: int = 0
    status: str = "ACTIVE"
    description: Optional[str] = None


# ---------- 账户册方案 ----------
@router.get("/schemes")
async def list_schemes(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["s.is_deleted=0"]
    params = {}
    if keyword:
        where.append("(s.scheme_code LIKE :kw OR s.scheme_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if status:
        where.append("s.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT s.id, s.scheme_code, s.scheme_name, s.description, s.status,
                       s.node_count, s.created_at, s.updated_at,
                       (SELECT COUNT(*) FROM prcp_coa_node n WHERE n.scheme_id=s.id AND n.is_deleted=0) AS real_node_count
                FROM prcp_coa_scheme s
                WHERE {' AND '.join(where)}
                ORDER BY s.id DESC"""),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_code": r[1], "scheme_name": r[2], "description": r[3],
                "status": r[4], "node_count": r[5] or r[8], "real_node_count": r[8],
                "created_at": r[6].isoformat() if r[6] else None,
                "updated_at": r[7].isoformat() if r[7] else None,
            } for r in rows
        ]
    }


@router.post("/schemes")
async def create_scheme(p: SchemeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_coa_scheme
                (scheme_code, scheme_name, description, status, created_by, updated_by)
                VALUES (:c, :n, :d, :s, :u, :u)"""),
            {"c": p.scheme_code, "n": p.scheme_name, "d": p.description,
             "s": p.status, "u": uid},
        ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：方案编码可能重复 ({e})")
    return {"id": rid, "scheme_code": p.scheme_code, "scheme_name": p.scheme_name}


@router.put("/schemes/{sid}")
async def update_scheme(sid: int, p: SchemeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    result = db.execute(
        text("""UPDATE prcp_coa_scheme
            SET scheme_code=:c, scheme_name=:n, description=:d, status=:s, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {"c": p.scheme_code, "n": p.scheme_name, "d": p.description,
         "s": p.status, "u": uid, "id": sid},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "方案不存在")
    return {"ok": True}


@router.delete("/schemes/{sid}")
async def delete_scheme(sid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删方案 + 其下所有节点"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    n = db.execute(
        text("UPDATE prcp_coa_node SET is_deleted=1, updated_by=:u WHERE scheme_id=:id AND is_deleted=0"),
        {"u": uid, "id": sid},
    ).rowcount
    r = db.execute(
        text("UPDATE prcp_coa_scheme SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": sid},
    ).rowcount
    if r == 0:
        raise HTTPException(404, "方案不存在")
    return {"ok": True, "deleted_nodes": n}


# ---------- 账户册节点（树形） ----------
@router.get("/nodes")
async def list_nodes(
    scheme_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回某方案的所有节点（扁平）"""
    rows = db.execute(
        text("""SELECT id, scheme_id, node_code, node_name, parent_id, node_level, node_type,
                       path, sort_order, status, description
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0
                ORDER BY sort_order, path"""),
        {"s": scheme_id},
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_id": r[1], "node_code": r[2], "node_name": r[3],
                "parent_id": r[4], "node_level": r[5], "node_type": r[6],
                "path": r[7], "sort_order": r[8], "status": r[9], "description": r[10],
            } for r in rows
        ]
    }


@router.get("/nodes/tree")
async def tree_nodes(
    scheme_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回树形结构（用 path 前缀匹配父子）"""
    rows = db.execute(
        text("""SELECT id, node_code, node_name, parent_id, node_level, node_type,
                       path, sort_order, status
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0
                ORDER BY sort_order, path"""),
        {"s": scheme_id},
    ).fetchall()

    by_path: dict = {}
    for r in rows:
        by_path[r[6]] = {
            "key": str(r[0]),
            "title": f"{r[2]} ({r[1]})",
            "code": r[1], "name": r[2],
            "id": r[0], "level": r[4], "type": r[5],
            "path": r[6], "sort_order": r[7], "status": r[8],
            "children": [],
        }

    roots = []
    for node in by_path.values():
        path = node["path"]
        # 父节点 path = 去末段 "/code/"
        # 末段是 "/<this_code>/"
        last_slash = path[:-1].rfind("/") + 1
        parent_path = path[:last_slash]
        parent = by_path.get(parent_path)
        if parent:
            parent["children"].append(node)
        else:
            roots.append(node)

    return {"scheme_id": scheme_id, "items": roots, "total": len(by_path)}


@router.post("/nodes")
async def create_node(p: NodeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 计算 path + level
    if p.parent_id:
        parent = db.execute(
            text("SELECT path, node_level FROM prcp_coa_node WHERE id=:id AND is_deleted=0"),
            {"id": p.parent_id},
        ).first()
        if not parent:
            raise HTTPException(400, "父节点不存在")
        path = f"{parent[0]}{p.node_code}/"
        level = parent[1] + 1
    else:
        path = f"/{p.node_code}/"
        level = 1

    try:
        nid = db.execute(
            text("""INSERT INTO prcp_coa_node
                (scheme_id, node_code, node_name, parent_id, node_level, node_type,
                 path, sort_order, status, description, created_by, updated_by)
                VALUES (:s, :c, :n, :p, :l, :t, :path, :so, :st, :d, :u, :u)"""),
            {
                "s": p.scheme_id, "c": p.node_code, "n": p.node_name,
                "p": p.parent_id, "l": level, "t": p.node_type,
                "path": path, "so": p.sort_order, "st": p.status,
                "d": p.description, "u": uid,
            },
        ).lastrowid
        # 更新方案的 node_count
        db.execute(
            text("UPDATE prcp_coa_scheme SET node_count=node_count+1 WHERE id=:s"),
            {"s": p.scheme_id},
        )
    except Exception as e:
        raise HTTPException(400, f"创建失败：节点编码可能重复 ({e})")
    return {"id": nid, "path": path, "level": level}


@router.put("/nodes/{nid}")
async def update_node(nid: int, p: NodeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 取出当前节点
    cur = db.execute(
        text("SELECT scheme_id, parent_id, node_code, path, node_level FROM prcp_coa_node WHERE id=:id AND is_deleted=0"),
        {"id": nid},
    ).first()
    if not cur:
        raise HTTPException(404, "节点不存在")
    # 禁止把父节点设为自己或自己的子节点
    if p.parent_id == nid:
        raise HTTPException(400, "不能把自己设为父节点")
    if p.parent_id:
        sub = db.execute(
            text("SELECT id FROM prcp_coa_node WHERE path LIKE :p AND is_deleted=0 LIMIT 1"),
            {"p": f"{cur[3]}%"},
        ).first()
        # 如果新父是当前节点的子孙，就拒绝
        new_parent = db.execute(
            text("SELECT path FROM prcp_coa_node WHERE id=:id"), {"id": p.parent_id},
        ).first()
        if new_parent and new_parent[0].startswith(cur[3]):
            raise HTTPException(400, "不能把父节点设为自己或子孙节点")

    db.execute(
        text("""UPDATE prcp_coa_node SET
            node_code=:c, node_name=:n, parent_id=:p, node_type=:t,
            sort_order=:so, status=:st, description=:d, updated_by=:u
            WHERE id=:id"""),
        {
            "c": p.node_code, "n": p.node_name, "p": p.parent_id, "t": p.node_type,
            "so": p.sort_order, "st": p.status, "d": p.description,
            "u": uid, "id": nid,
        },
    )
    return {"ok": True}


@router.delete("/nodes/{nid}")
async def delete_node(nid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删节点 + 其所有子孙"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    cur = db.execute(
        text("SELECT scheme_id, path FROM prcp_coa_node WHERE id=:id AND is_deleted=0"),
        {"id": nid},
    ).first()
    if not cur:
        raise HTTPException(404, "节点不存在")
    scheme_id, path = cur
    n = db.execute(
        text("UPDATE prcp_coa_node SET is_deleted=1, updated_by=:u WHERE path LIKE :p AND is_deleted=0"),
        {"u": uid, "p": f"{path}%"},
    ).rowcount
    db.execute(
        text("UPDATE prcp_coa_scheme SET node_count=GREATEST(0, node_count-:n) WHERE id=:s"),
        {"n": n, "s": scheme_id},
    )
    return {"ok": True, "deleted": n}
