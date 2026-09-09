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
MEASURE_COLS = ["begin_balance", "avg_balance", "interest_rate",
               "interest_amount", "capital_ratio", "risk_weight"]


class BalanceIn(BaseModel):
    coa_node_id: int
    data_date: str  # YYYY-MM-DD
    current_amount: float = 0
    begin_balance: Optional[float] = 0
    avg_balance: Optional[float] = 0
    interest_rate: Optional[float] = 0
    interest_amount: Optional[float] = 0
    capital_ratio: Optional[float] = 0
    risk_weight: Optional[float] = 0
    gaps: Optional[List[float]] = None  # 24 个数
    calc_note: Optional[str] = None


@router.get("/")
async def list_balance(
    coa_node_id: Optional[int] = None,
    data_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    scheme_id: Optional[int] = None,
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
    if scheme_id:
        where.append("n.scheme_id=:s")
        params["s"] = scheme_id

    rows = db.execute(
        text(f"""SELECT b.id, b.coa_node_id, n.node_code, n.node_name, n.node_level,
                       n.path, n.node_type,
                       b.data_date, b.current_amount,
                       b.begin_balance, b.avg_balance, b.interest_rate,
                       b.interest_amount, b.capital_ratio, b.risk_weight,
                       {','.join('b.' + c for c in GAP_COLS)},
                       b.calc_note, b.created_at
                FROM prcp_data_balance b
                LEFT JOIN prcp_coa_node n ON n.id=b.coa_node_id
                WHERE {' AND '.join(where)}
                ORDER BY n.path, b.data_date DESC, b.coa_node_id
                LIMIT 2000"""),
        params,
    ).fetchall()

    items = []
    for r in rows:
        gaps = [float(r[15 + i]) for i in range(24)]
        items.append({
            "id": r[0], "coa_node_id": r[1],
            "node_code": r[2], "node_name": r[3],
            "node_level": r[4], "path": r[5], "node_type": r[6],
            "data_date": r[7].isoformat() if r[7] else None,
            "current_amount": float(r[8] or 0),
            "begin_balance": float(r[9] or 0),
            "avg_balance": float(r[10] or 0),
            "interest_rate": float(r[11] or 0),
            "interest_amount": float(r[12] or 0),
            "capital_ratio": float(r[13] or 0),
            "risk_weight": float(r[14] or 0),
            "gaps": gaps,
            "calc_note": r[39], "created_at": r[40].isoformat() if r[40] else None,
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
    measure_set = ",".join(f"{c}=:{c}" for c in MEASURE_COLS)
    measure_insert_cols = ",".join(MEASURE_COLS)
    measure_insert_vals = ",".join(f":{c}" for c in MEASURE_COLS)

    existing = db.execute(
        text("SELECT id FROM prcp_data_balance WHERE coa_node_id=:n AND data_date=:d AND is_deleted=0"),
        {"n": p.coa_node_id, "d": p.data_date},
    ).first()
    if existing:
        params = {c: gap_values[i] for i, c in enumerate(GAP_COLS)}
        params.update({c: getattr(p, c) or 0 for c in MEASURE_COLS})
        params.update({"amt": p.current_amount, "note": p.calc_note, "u": uid, "id": existing[0]})
        db.execute(
            text(f"""UPDATE prcp_data_balance SET
                current_amount=:amt, {measure_set}, {gap_set}, calc_note=:note, updated_by=:u
                WHERE id=:id"""),
            params,
        )
        return {"id": existing[0], "action": "updated"}
    else:
        params = {c: gap_values[i] for i, c in enumerate(GAP_COLS)}
        params.update({c: getattr(p, c) or 0 for c in MEASURE_COLS})
        params.update({
            "n": p.coa_node_id, "d": p.data_date,
            "amt": p.current_amount, "note": p.calc_note, "u": uid,
        })
        rid = db.execute(
            text(f"""INSERT INTO prcp_data_balance
                (coa_node_id, data_date, current_amount,
                 {measure_insert_cols}, {gap_insert_cols},
                 calc_note, created_by, updated_by)
                VALUES (:n, :d, :amt, {measure_insert_vals}, {gap_insert_vals}, :note, :u, :u)"""),
            params,
        ).lastrowid
        return {"id": rid, "action": "created"}


@router.delete("/{bid}")
async def delete_balance(bid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
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


@router.get("/by-scheme")
async def list_by_scheme(
    scheme_id: int = Query(...),
    data_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """按账户册方案 + 数据日期聚合：每行 = 一个账户册节点 + 当月 7 个度量"""
    rows = db.execute(
        text(f"""SELECT b.id, b.coa_node_id, n.node_code, n.node_name,
                       n.node_level, n.node_type, n.path,
                       b.current_amount, b.begin_balance, b.avg_balance,
                       b.interest_rate, b.interest_amount,
                       b.capital_ratio, b.risk_weight,
                       {','.join('b.' + c for c in GAP_COLS)},
                       b.calc_note
                FROM prcp_data_balance b
                JOIN prcp_coa_node n ON n.id=b.coa_node_id
                WHERE b.data_date=:d AND b.is_deleted=0
                  AND n.scheme_id=:s
                ORDER BY n.path"""),
        {"d": data_date, "s": scheme_id},
    ).fetchall()

    items = []
    for r in rows:
        gaps = [float(r[14 + i]) for i in range(24)]
        items.append({
            "id": r[0], "coa_node_id": r[1],
            "node_code": r[2], "node_name": r[3],
            "node_level": r[4], "node_type": r[5], "path": r[6],
            "current_amount": float(r[7] or 0),
            "begin_balance": float(r[8] or 0),
            "avg_balance": float(r[9] or 0),
            "interest_rate": float(r[10] or 0),
            "interest_amount": float(r[11] or 0),
            "capital_ratio": float(r[12] or 0),
            "risk_weight": float(r[13] or 0),
            "gaps": gaps,
            "sum_24m": sum(gaps),
            "calc_note": r[38],
        })
    return {"scheme_id": scheme_id, "data_date": data_date,
            "items": items, "total": len(items)}


@router.get("/dates")
async def list_dates(
    scheme_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回 prcp_data_balance 中所有有数据的数据日期（按倒序），可选 scheme 过滤"""
    where = ["b.is_deleted=0"]
    params = {}
    if scheme_id:
        where.append("n.scheme_id=:s")
        params["s"] = scheme_id
    rows = db.execute(
        text(f"""SELECT b.data_date, COUNT(*) AS cnt,
                       SUM(b.current_amount) AS total_amt,
                       SUM(b.interest_amount) AS total_int
                FROM prcp_data_balance b
                JOIN prcp_coa_node n ON n.id=b.coa_node_id
                WHERE {' AND '.join(where)}
                GROUP BY b.data_date
                ORDER BY b.data_date DESC"""),
        params,
    ).fetchall()
    items = [{
        "data_date": r[0].isoformat() if r[0] else None,
        "record_count": int(r[1]),
        "total_amount": float(r[2] or 0),
        "total_interest": float(r[3] or 0),
    } for r in rows]
    return {"items": items, "total": len(items)}


@router.get("/category-summary")
async def category_summary(
    data_date: str = Query(..., description="YYYY-MM-DD"),
    scheme_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """按大类（资产/负债/表外）汇总当月数据"""
    where = ["b.is_deleted=0", "b.data_date=:d", "n.node_level=3"]
    params = {"d": data_date}
    if scheme_id:
        where.append("n.scheme_id=:s")
        params["s"] = scheme_id

    # 先把所有 L3 节点及其 path 抓出来，然后按 L1 大类名（path 首段）聚合
    rows = db.execute(
        text(f"""SELECT n.id, n.node_code, n.node_name, n.path,
                       b.current_amount, b.begin_balance, b.avg_balance,
                       b.interest_rate, b.interest_amount,
                       b.capital_ratio, b.risk_weight,
                       {','.join('b.' + c for c in GAP_COLS)}
                FROM prcp_data_balance b
                JOIN prcp_coa_node n ON n.id=b.coa_node_id
                WHERE {' AND '.join(where)}"""),
        params,
    ).fetchall()

    # 按 L1 分类（path 第 1 段：/L1_xxx/）
    buckets: dict = {}
    for r in rows:
        path = r[3] or ""
        cat = path.split('/')[1] if '/' in path else '其他'
        cat = cat.replace('L1_', '')
        b = buckets.setdefault(cat, {
            "category": cat, "account_count": 0,
            "total_amount": 0.0, "total_begin": 0.0, "total_avg": 0.0,
            "total_interest": 0.0, "weighted_rate_sum": 0.0, "weighted_cap_sum": 0.0,
            "weighted_rw_sum": 0.0, "sum_24m": 0.0,
        })
        b["account_count"] += 1
        amt = float(r[4] or 0)
        avg = float(r[6] or 0)
        b["total_amount"] += amt
        b["total_begin"] += float(r[5] or 0)
        b["total_avg"] += avg
        b["total_interest"] += float(r[8] or 0)
        b["weighted_rate_sum"] += float(r[7] or 0) * avg
        b["weighted_cap_sum"] += float(r[9] or 0) * avg
        b["weighted_rw_sum"] += float(r[10] or 0) * avg
        gaps = [float(r[11 + i]) for i in range(24)]
        b["sum_24m"] += sum(gaps)

    items = []
    for b in buckets.values():
        avg = b["total_avg"] or 1
        items.append({
            "category": b["category"],
            "account_count": b["account_count"],
            "total_amount": round(b["total_amount"], 2),
            "total_begin": round(b["total_begin"], 2),
            "total_avg": round(b["total_avg"], 2),
            "total_interest": round(b["total_interest"], 2),
            "weighted_rate": round(b["weighted_rate_sum"] / avg, 4),
            "weighted_capital": round(b["weighted_cap_sum"] / avg, 4),
            "weighted_risk_weight": round(b["weighted_rw_sum"] / avg, 4),
            "sum_24m": round(b["sum_24m"], 2),
        })
    return {"data_date": data_date, "items": items, "total": len(items)}
