"""头寸管理 — 头寸明细 / 调入调出 / 缺口分析"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/positions", tags=["头寸"])


@router.get("")
async def list_positions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    currency: str | None = None,
    status: str | None = None,
    group_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["p.is_deleted=0"]
    params: dict = {}
    if currency:
        where.append("p.currency=:cur"); params["cur"] = currency
    if status:
        where.append("p.status=:st"); params["st"] = status
    if group_id:
        where.append("p.group_id=:gid"); params["gid"] = group_id
    sql_where = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM prcp_position p WHERE {sql_where}"), params).scalar() or 0
    rows = db.execute(text(f"""
        SELECT p.id, p.position_code, p.group_id, g.group_name, p.account_code,
               p.currency, p.direction, p.amount, p.rate, p.status,
               p.trade_date, p.settle_date, p.counterparty, p.description,
               p.created_at
        FROM prcp_position p
        LEFT JOIN prcp_group g ON g.id=p.group_id AND g.is_deleted=0
        WHERE {sql_where}
        ORDER BY p.id DESC LIMIT :lim OFFSET :off
    """), {**params, "lim": page_size, "off": (page - 1) * page_size}).fetchall()
    return {
        "total": total,
        "items": [
            {
                "id": r[0], "position_code": r[1], "group_id": r[2], "group_name": r[3],
                "account_code": r[4], "currency": r[5], "direction": r[6],
                "amount": float(r[7] or 0), "rate": float(r[8] or 0),
                "status": r[9], "trade_date": r[10].isoformat() if r[10] else None,
                "settle_date": r[11].isoformat() if r[11] else None,
                "counterparty": r[12], "description": r[13],
                "created_at": r[14].isoformat() if r[14] else None,
            } for r in rows
        ],
    }


@router.post("")
async def create_position(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.execute(text("""
        INSERT INTO prcp_position
          (position_code, group_id, account_code, currency, direction, amount, rate,
           status, trade_date, settle_date, counterparty, description, created_by, updated_by)
        VALUES (:code,:gid,:acc,:cur,:dir,:amt,:rate,:st,:td,:sd,:cp,:desc,:uid,:uid)
    """), {**payload, "uid": user["id"]})
    db.commit()
    return {"message": "ok"}


@router.put("/{pid}")
async def update_position(pid: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    upd = ["position_code", "group_id", "account_code", "currency", "direction",
           "amount", "rate", "status", "trade_date", "settle_date",
           "counterparty", "description"]
    sets, params = [], {"id": pid, "uid": user["id"]}
    for k in upd:
        if k in payload:
            sets.append(f"{k}=:{k}"); params[k] = payload[k]
    if not sets:
        raise HTTPException(400, "无可更新字段")
    sets += ["updated_by=:uid", "updated_at=NOW()"]
    db.execute(text(f"UPDATE prcp_position SET {', '.join(sets)} WHERE id=:id AND is_deleted=0"), params)
    db.commit()
    return {"message": "ok"}


@router.delete("/{pid}")
async def delete_position(pid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.execute(text("UPDATE prcp_position SET is_deleted=1, updated_by=:uid, updated_at=NOW() WHERE id=:id"),
               {"id": pid, "uid": user["id"]})
    db.commit()
    return {"deleted": pid}


@router.get("/gap")
async def gap_analysis(group_id: int | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """缺口分析：按币种汇总 PENDING 状态头寸"""
    where = "p.is_deleted=0 AND p.status='PENDING'"
    params: dict = {}
    if group_id:
        where += " AND p.group_id=:gid"; params["gid"] = group_id
    rows = db.execute(text(f"""
        SELECT p.currency, p.direction,
               COUNT(*) AS cnt, COALESCE(SUM(p.amount),0) AS total
        FROM prcp_position p WHERE {where}
        GROUP BY p.currency, p.direction ORDER BY p.currency, p.direction
    """), params).fetchall()
    # 按币种合并净缺口
    net: dict = {}
    for r in rows:
        cur = r[0]
        net[cur] = net.get(cur, 0) + (float(r[3]) if r[1] == 'IN' else -float(r[3]))
    return {
        "by_currency_direction": [
            {"currency": r[0], "direction": r[1], "count": r[2], "total": float(r[3])}
            for r in rows
        ],
        "net_gap": [{"currency": c, "net_amount": round(v, 2)} for c, v in net.items()],
    }