"""报表表项管理 API — 6 类报表 + 树形表项"""
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["报表"])


class ReportIn(BaseModel):
    report_code: str
    report_name: str
    report_type: str  # BALANCE/INCOME/CASHFLOW/INDICATOR/RISK/LIQUIDITY
    scheme_id: int
    description: Optional[str] = None
    status: str = "ACTIVE"


class ItemIn(BaseModel):
    report_id: int
    item_code: str
    item_name: str
    parent_id: Optional[int] = None
    data_type: str = "DECIMAL"
    formula: Optional[str] = None
    coa_node_ids: Optional[List[int]] = None
    sort_order: int = 0
    status: str = "ACTIVE"
    description: Optional[str] = None


# ---------- 报表定义 ----------
@router.get("/")
async def list_reports(
    report_type: Optional[str] = None,
    scheme_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["r.is_deleted=0"]
    params = {}
    if report_type:
        where.append("r.report_type=:t")
        params["t"] = report_type
    if scheme_id:
        where.append("r.scheme_id=:s")
        params["s"] = scheme_id
    if keyword:
        where.append("(r.report_code LIKE :kw OR r.report_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    rows = db.execute(
        text(f"""SELECT r.id, r.report_code, r.report_name, r.report_type, r.scheme_id,
                       s.scheme_name, r.description, r.item_count, r.status,
                       r.created_at, r.updated_at
                FROM prcp_rpt_report r
                LEFT JOIN prcp_coa_scheme s ON s.id=r.scheme_id AND s.is_deleted=0
                WHERE {' AND '.join(where)}
                ORDER BY r.id DESC"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0], "report_code": r[1], "report_name": r[2],
            "report_type": r[3], "scheme_id": r[4], "scheme_name": r[5],
            "description": r[6], "item_count": r[7], "status": r[8],
            "created_at": r[9].isoformat() if r[9] else None,
            "updated_at": r[10].isoformat() if r[10] else None,
        } for r in rows
    ]}


@router.post("/")
async def create_report(p: ReportIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        with db.begin():
            rid = db.execute(
                text("""INSERT INTO prcp_rpt_report
                    (report_code, report_name, report_type, scheme_id, description, status, created_by, updated_by)
                    VALUES (:c, :n, :t, :s, :d, :st, :u, :u)"""),
                {"c": p.report_code, "n": p.report_name, "t": p.report_type,
                 "s": p.scheme_id, "d": p.description, "st": p.status, "u": uid},
            ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：报表编码可能重复 ({e})")
    return {"id": rid, "report_code": p.report_code}


@router.put("/{rid}")
async def update_report(rid: int, p: ReportIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    with db.begin():
        r = db.execute(
            text("""UPDATE prcp_rpt_report SET
                report_code=:c, report_name=:n, report_type=:t, scheme_id=:s,
                description=:d, status=:st, updated_by=:u
                WHERE id=:id AND is_deleted=0"""),
            {"c": p.report_code, "n": p.report_name, "t": p.report_type,
             "s": p.scheme_id, "d": p.description, "st": p.status,
             "u": uid, "id": rid},
        ).rowcount
    if r == 0:
        raise HTTPException(404, "报表不存在")
    return {"ok": True}


@router.delete("/{rid}")
async def delete_report(rid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删报表 + 其所有表项"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    with db.begin():
        n = db.execute(
            text("UPDATE prcp_rpt_item SET is_deleted=1, updated_by=:u WHERE report_id=:id AND is_deleted=0"),
            {"u": uid, "id": rid},
        ).rowcount
        r = db.execute(
            text("UPDATE prcp_rpt_report SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
            {"u": uid, "id": rid},
        ).rowcount
    if r == 0:
        raise HTTPException(404, "报表不存在")
    return {"ok": True, "deleted_items": n}


# ---------- 报表表项（树形） ----------
@router.get("/items")
async def list_items(
    report_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = db.execute(
        text("""SELECT id, report_id, item_code, item_name, parent_id, item_level, data_type,
                       formula, coa_node_ids, path, sort_order, status, description
                FROM prcp_rpt_item
                WHERE report_id=:r AND is_deleted=0
                ORDER BY path, sort_order"""),
        {"r": report_id},
    ).fetchall()
    items = []
    for r in rows:
        coa_ids = []
        if r[8]:
            try:
                coa_ids = json.loads(r[8]) if isinstance(r[8], str) else r[8]
            except Exception:
                coa_ids = []
        items.append({
            "id": r[0], "report_id": r[1], "item_code": r[2], "item_name": r[3],
            "parent_id": r[4], "item_level": r[5], "data_type": r[6],
            "formula": r[7], "coa_node_ids": coa_ids,
            "path": r[9], "sort_order": r[10], "status": r[11], "description": r[12],
        })
    return {"items": items}


@router.get("/items/tree")
async def tree_items(
    report_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = db.execute(
        text("""SELECT id, item_code, item_name, parent_id, item_level, data_type,
                       formula, coa_node_ids, path, sort_order, status
                FROM prcp_rpt_item
                WHERE report_id=:r AND is_deleted=0
                ORDER BY path, sort_order"""),
        {"r": report_id},
    ).fetchall()
    by_path: dict = {}
    for r in rows:
        coa_ids = []
        if r[7]:
            try:
                coa_ids = json.loads(r[7]) if isinstance(r[7], str) else r[7]
            except Exception:
                pass
        by_path[r[8]] = {
            "key": str(r[0]),
            "title": f"{r[2]} ({r[1]})",
            "code": r[1], "name": r[2], "id": r[0],
            "level": r[4], "data_type": r[5], "formula": r[6],
            "coa_node_ids": coa_ids,
            "path": r[8], "sort_order": r[9], "status": r[10],
            "children": [],
        }
    roots = []
    for node in by_path.values():
        path = node["path"]
        last_slash = path[:-1].rfind("/") + 1
        parent_path = path[:last_slash]
        parent = by_path.get(parent_path)
        if parent:
            parent["children"].append(node)
        else:
            roots.append(node)
    return {"report_id": report_id, "items": roots, "total": len(by_path)}


@router.post("/items")
async def create_item(p: ItemIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    if p.parent_id:
        parent = db.execute(
            text("SELECT path, item_level FROM prcp_rpt_item WHERE id=:id AND is_deleted=0"),
            {"id": p.parent_id},
        ).first()
        if not parent:
            raise HTTPException(400, "父表项不存在")
        path = f"{parent[0]}{p.item_code}/"
        level = parent[1] + 1
    else:
        path = f"/{p.item_code}/"
        level = 1
    coa_json = json.dumps(p.coa_node_ids or [])
    try:
        with db.begin():
            nid = db.execute(
                text("""INSERT INTO prcp_rpt_item
                    (report_id, item_code, item_name, parent_id, item_level, data_type,
                     formula, coa_node_ids, path, sort_order, status, description, created_by, updated_by)
                    VALUES (:r, :c, :n, :p, :l, :t, :f, :coa, :path, :so, :st, :d, :u, :u)"""),
                {
                    "r": p.report_id, "c": p.item_code, "n": p.item_name,
                    "p": p.parent_id, "l": level, "t": p.data_type,
                    "f": p.formula, "coa": coa_json, "path": path,
                    "so": p.sort_order, "st": p.status, "d": p.description, "u": uid,
                },
            ).lastrowid
            db.execute(
                text("UPDATE prcp_rpt_report SET item_count=item_count+1 WHERE id=:r"),
                {"r": p.report_id},
            )
    except Exception as e:
        raise HTTPException(400, f"创建失败：表项编码可能重复 ({e})")
    return {"id": nid, "path": path, "level": level}


@router.put("/items/{nid}")
async def update_item(nid: int, p: ItemIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    coa_json = json.dumps(p.coa_node_ids or [])
    with db.begin():
        r = db.execute(
            text("""UPDATE prcp_rpt_item SET
                item_code=:c, item_name=:n, parent_id=:p, data_type=:t,
                formula=:f, coa_node_ids=:coa, sort_order=:so, status=:st,
                description=:d, updated_by=:u
                WHERE id=:id AND is_deleted=0"""),
            {
                "c": p.item_code, "n": p.item_name, "p": p.parent_id, "t": p.data_type,
                "f": p.formula, "coa": coa_json, "so": p.sort_order, "st": p.status,
                "d": p.description, "u": uid, "id": nid,
            },
        ).rowcount
    if r == 0:
        raise HTTPException(404, "表项不存在")
    return {"ok": True}


@router.delete("/items/{nid}")
async def delete_item(nid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删表项 + 其所有子孙"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    cur = db.execute(
        text("SELECT report_id, path FROM prcp_rpt_item WHERE id=:id AND is_deleted=0"),
        {"id": nid},
    ).first()
    if not cur:
        raise HTTPException(404, "表项不存在")
    report_id, path = cur
    with db.begin():
        n = db.execute(
            text("UPDATE prcp_rpt_item SET is_deleted=1, updated_by=:u WHERE path LIKE :p AND is_deleted=0"),
            {"u": uid, "p": f"{path}%"},
        ).rowcount
        db.execute(
            text("UPDATE prcp_rpt_report SET item_count=GREATEST(0, item_count-:n) WHERE id=:r"),
            {"n": n, "r": report_id},
        )
    return {"ok": True, "deleted": n}


# 增三改：批量新增 + 替换 + 删除
@router.post("/items/batch")
async def batch_items(
    report_id: int = Query(...),
    create: Optional[List[ItemIn]] = None,
    update: Optional[List[dict]] = None,
    delete_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """增三改：批量新增 create / 修改 update / 删除 delete_ids"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    created = updated = deleted = 0
    with db.begin():
        if create:
            for it in create:
                if it.parent_id:
                    p = db.execute(
                        text("SELECT path, item_level FROM prcp_rpt_item WHERE id=:id AND is_deleted=0"),
                        {"id": it.parent_id},
                    ).first()
                    if p:
                        path = f"{p[0]}{it.item_code}/"
                        level = p[1] + 1
                    else:
                        path = f"/{it.item_code}/"
                        level = 1
                else:
                    path = f"/{it.item_code}/"
                    level = 1
                db.execute(
                    text("""INSERT INTO prcp_rpt_item
                        (report_id, item_code, item_name, parent_id, item_level,
                         data_type, formula, coa_node_ids, path, sort_order, status, description, created_by, updated_by)
                        VALUES (:r, :c, :n, :p, :l, :t, :f, :coa, :path, :so, :st, :d, :u, :u)"""),
                    {
                        "r": report_id, "c": it.item_code, "n": it.item_name,
                        "p": it.parent_id, "l": level, "t": it.data_type,
                        "f": it.formula, "coa": json.dumps(it.coa_node_ids or []),
                        "path": path, "so": it.sort_order, "st": it.status,
                        "d": it.description, "u": uid,
                    },
                )
                created += 1
        if update:
            for d in update:
                if "id" not in d:
                    continue
                fields = {k: v for k, v in d.items() if k != "id"}
                if "coa_node_ids" in fields:
                    fields["coa_node_ids"] = json.dumps(fields["coa_node_ids"])
                fields["updated_by"] = uid
                set_clause = ", ".join(f"{k}=:{k}" for k in fields)
                db.execute(
                    text(f"UPDATE prcp_rpt_item SET {set_clause} WHERE id=:id AND is_deleted=0"),
                    {**fields, "id": d["id"]},
                )
                updated += 1
        if delete_ids:
            for did in delete_ids:
                cur = db.execute(
                    text("SELECT path FROM prcp_rpt_item WHERE id=:id AND is_deleted=0"),
                    {"id": did},
                ).first()
                if not cur:
                    continue
                path = cur[0]
                n = db.execute(
                    text("UPDATE prcp_rpt_item SET is_deleted=1, updated_by=:u WHERE path LIKE :p AND is_deleted=0"),
                    {"u": uid, "p": f"{path}%"},
                ).rowcount
                deleted += n
        # 更新报表 item_count
        if created or deleted:
            db.execute(
                text("UPDATE prcp_rpt_report SET item_count=item_count+:c-:d WHERE id=:r"),
                {"c": created, "d": deleted, "r": report_id},
            )
    return {"ok": True, "created": created, "updated": updated, "deleted": deleted}
