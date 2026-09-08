"""资产负债表 API — 单大表 + 24 月现金流缺口"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/balance", tags=["资产负债表"])

GAP_COLS = [f"m{i}_gap" for i in range(1, 25)]


class BalanceIn(BaseModel):
    coa_node_id: int
    data_date: str  # YYYY-MM-DD
    current_amount: float = 0
    gaps: Optional[List[float]] = None  # 24 个数
    calc_note: Optional[str] = None


@router.get("/")
async def list_balance(
    coa_node_id: Optional[int] = None,
    data_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["b.is_deleted=0"]
    params = {}
    if coa_node_id:
        where.append("b.coa_node_id=:n")
        params["n"] = coa_node_id
    if data_date:
        where.append("b.data_date=:d")
        params["d"] = data_date
    if start_date:
        where.append("b.data_date>=:sd")
        params["sd"] = start_date
    if end_date:
        where.append("b.data_date<=:ed")
        params["ed"] = end_date

    rows = db.execute(
        text(f"""SELECT b.id, b.coa_node_id, n.node_code, n.node_name,
                       b.data_date, b.current_amount,
                       {','.join('b.' + c for c in GAP_COLS)},
                       b.calc_note, b.created_at
                FROM prcp_data_balance b
                LEFT JOIN prcp_coa_node n ON n.id=b.coa_node_id
                WHERE {' AND '.join(where)}
                ORDER BY b.data_date DESC, b.coa_node_id
                LIMIT 1000"""),
        params,
    ).fetchall()

    items = []
    for r in rows:
        gaps = [float(r[6 + i]) for i in range(24)]
        items.append({
            "id": r[0], "coa_node_id": r[1],
            "node_code": r[2], "node_name": r[3],
            "data_date": r[4].isoformat() if r[4] else None,
            "current_amount": float(r[5]),
            "gaps": gaps,
            "calc_note": r[30], "created_at": r[31].isoformat() if r[31] else None,
        })
    return {"items": items, "total": len(items)}


@router.post("/")
async def upsert_balance(p: BalanceIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """按 (coa_node_id, data_date) 唯一，存在则更新，否则插入"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    gaps = p.gaps or [0] * 24
    while len(gaps) < 24:
        gaps.append(0)
    gap_values = gaps[:24]

    gap_set = ",".join(f"{c}=:{c}" for c in GAP_COLS)
    gap_insert_cols = ",".join(GAP_COLS)
    gap_insert_vals = ",".join(f":{c}" for c in GAP_COLS)

    with db.begin():
        existing = db.execute(
            text("SELECT id FROM prcp_data_balance WHERE coa_node_id=:n AND data_date=:d AND is_deleted=0"),
            {"n": p.coa_node_id, "d": p.data_date},
        ).first()
        if existing:
            params = {c: gap_values[i] for i, c in enumerate(GAP_COLS)}
            params.update({"amt": p.current_amount, "note": p.calc_note, "u": uid, "id": existing[0]})
            db.execute(
                text(f"""UPDATE prcp_data_balance SET
                    current_amount=:amt, {gap_set}, calc_note=:note, updated_by=:u
                    WHERE id=:id"""),
                params,
            )
            return {"id": existing[0], "action": "updated"}
        else:
            params = {c: gap_values[i] for i, c in enumerate(GAP_COLS)}
            params.update({
                "n": p.coa_node_id, "d": p.data_date,
                "amt": p.current_amount, "note": p.calc_note, "u": uid,
            })
            rid = db.execute(
                text(f"""INSERT INTO prcp_data_balance
                    (coa_node_id, data_date, current_amount, {gap_insert_cols}, calc_note, created_by, updated_by)
                    VALUES (:n, :d, :amt, {gap_insert_vals}, :note, :u, :u)"""),
                params,
            ).lastrowid
            return {"id": rid, "action": "created"}


@router.delete("/{bid}")
async def delete_balance(bid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    with db.begin():
        r = db.execute(
            text("UPDATE prcp_data_balance SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
            {"u": uid, "id": bid},
        ).rowcount
    if r == 0:
        raise HTTPException(404, "记录不存在")
    return {"ok": True}


@router.get("/gap-summary")
async def gap_summary(
    data_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """按日期聚合：每个节点 + 24 月缺口合计"""
    rows = db.execute(
        text(f"""SELECT b.coa_node_id, n.node_code, n.node_name,
                       b.current_amount,
                       {','.join('b.' + c for c in GAP_COLS)}
                FROM prcp_data_balance b
                LEFT JOIN prcp_coa_node n ON n.id=b.coa_node_id
                WHERE b.data_date=:d AND b.is_deleted=0
                ORDER BY b.coa_node_id"""),
        {"d": data_date},
    ).fetchall()
    items = []
    for r in rows:
        gaps = [float(r[4 + i]) for i in range(24)]
        items.append({
            "coa_node_id": r[0], "node_code": r[1], "node_name": r[2],
            "current_amount": float(r[3]), "gaps": gaps,
            "sum_24m": sum(gaps), "min_gap": min(gaps), "max_gap": max(gaps),
        })
    return {"data_date": data_date, "items": items, "total": len(items)}
