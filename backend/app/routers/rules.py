"""组算规则引擎 — 规则定义 / 规则调度 / 执行流水"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/rules", tags=["组算规则"])


@router.get("")
async def list_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    rule_type: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["is_deleted=0"]
    params: dict = {}
    if rule_type:
        where.append("rule_type=:rt"); params["rt"] = rule_type
    sql_where = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM prcp_rule WHERE {sql_where}"), params).scalar() or 0
    rows = db.execute(text(f"""
        SELECT id, rule_code, rule_name, rule_type, priority, source_group,
               target_group, currency, threshold, action, status, description, updated_at
        FROM prcp_rule WHERE {sql_where}
        ORDER BY priority DESC, id DESC LIMIT :lim OFFSET :off
    """), {**params, "lim": page_size, "off": (page - 1) * page_size}).fetchall()
    return {
        "total": total,
        "items": [
            {
                "id": r[0], "rule_code": r[1], "rule_name": r[2], "rule_type": r[3],
                "priority": r[4], "source_group": r[5], "target_group": r[6],
                "currency": r[7], "threshold": float(r[8] or 0), "action": r[9],
                "status": r[10], "description": r[11],
                "updated_at": r[12].isoformat() if r[12] else None,
            } for r in rows
        ],
    }


@router.post("")
async def create_rule(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.execute(text("""
        INSERT INTO prcp_rule
          (rule_code, rule_name, rule_type, priority, source_group, target_group,
           currency, threshold, action, status, description, created_by, updated_by)
        VALUES (:code,:name,:rt,:prio,:sg,:tg,:cur,:th,:act,:st,:desc,:uid,:uid)
    """), {**payload, "uid": user["id"]})
    db.commit()
    return {"message": "ok"}


@router.put("/{rid}")
async def update_rule(rid: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    upd = ["rule_name", "rule_type", "priority", "source_group", "target_group",
           "currency", "threshold", "action", "status", "description"]
    sets, params = [], {"id": rid, "uid": user["id"]}
    for k in upd:
        if k in payload:
            sets.append(f"{k}=:{k}"); params[k] = payload[k]
    if not sets:
        raise HTTPException(400, "无可更新字段")
    sets += ["updated_by=:uid", "updated_at=NOW()"]
    db.execute(text(f"UPDATE prcp_rule SET {', '.join(sets)} WHERE id=:id AND is_deleted=0"), params)
    db.commit()
    return {"message": "ok"}


@router.delete("/{rid}")
async def delete_rule(rid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.execute(text("UPDATE prcp_rule SET is_deleted=1, updated_by=:uid, updated_at=NOW() WHERE id=:id"),
               {"id": rid, "uid": user["id"]})
    db.commit()
    return {"deleted": rid}