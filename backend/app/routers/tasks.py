"""组算任务 — 计划 / 执行 / 结果"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/tasks", tags=["组算任务"])


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["is_deleted=0"]
    params: dict = {}
    if status:
        where.append("status=:st"); params["st"] = status
    sql_where = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM prcp_task WHERE {sql_where}"), params).scalar() or 0
    rows = db.execute(text(f"""
        SELECT id, task_code, task_name, schedule_date, total_amount,
               matched_amount, matched_count, gap_amount, status, description,
               started_at, finished_at, created_at
        FROM prcp_task WHERE {sql_where}
        ORDER BY id DESC LIMIT :lim OFFSET :off
    """), {**params, "lim": page_size, "off": (page - 1) * page_size}).fetchall()
    return {
        "total": total,
        "items": [
            {
                "id": r[0], "task_code": r[1], "task_name": r[2],
                "schedule_date": r[3].isoformat() if r[3] else None,
                "total_amount": float(r[4] or 0), "matched_amount": float(r[5] or 0),
                "matched_count": r[6] or 0, "gap_amount": float(r[7] or 0),
                "status": r[8], "description": r[9],
                "started_at": r[10].isoformat() if r[10] else None,
                "finished_at": r[11].isoformat() if r[11] else None,
                "created_at": r[12].isoformat() if r[12] else None,
            } for r in rows
        ],
    }


@router.post("")
async def create_task(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """新建组算任务"""
    db.execute(text("""
        INSERT INTO prcp_task
          (task_code, task_name, schedule_date, total_amount, status, description,
           created_by, updated_by)
        VALUES (:code,:name,:sd,:amt,'PENDING',:desc,:uid,:uid)
    """), {**payload, "uid": user["id"]})
    db.commit()
    return {"message": "ok"}


@router.post("/{tid}/run")
async def run_task(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """执行组算：基于 PENDING 头寸和 ACTIVE 规则做简单撮合（演示）"""
    task = db.execute(text("SELECT id, task_name, status FROM prcp_task WHERE id=:id AND is_deleted=0"),
                      {"id": tid}).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task[2] == "RUNNING":
        raise HTTPException(400, "任务已在运行中")
    db.execute(text("UPDATE prcp_task SET status='RUNNING', started_at=NOW(), updated_by=:uid WHERE id=:id"),
               {"id": tid, "uid": user["id"]})
    db.commit()

    # 简单撮合：按币种聚合 IN / OUT，差额作为缺口
    positions = db.execute(text("""
        SELECT currency, direction, SUM(amount) AS total, COUNT(*) AS cnt
        FROM prcp_position WHERE is_deleted=0 AND status='PENDING'
        GROUP BY currency, direction
    """)).fetchall()
    matched_amt, matched_cnt, gap_amt = 0.0, 0, 0.0
    summary: dict = {}
    for r in positions:
        summary.setdefault(r[0], {"IN": 0.0, "OUT": 0.0})
        summary[r[0]][r[1]] = float(r[2])
    # 净额撮合
    for cur, v in summary.items():
        matched = min(v["IN"], v["OUT"])
        gap_amt += abs(v["IN"] - v["OUT"])
        matched_amt += matched
        matched_cnt += int(matched / max(1, min(v["IN"], v["OUT"]) / max(1, v["IN"] + v["OUT"]))) if matched > 0 else 0
    matched_cnt = matched_cnt if matched_cnt else int(matched_amt > 0)

    # 头寸批量标记 SETTLED
    db.execute(text("""
        UPDATE prcp_position SET status='SETTLED', updated_by=:uid, updated_at=NOW()
        WHERE is_deleted=0 AND status='PENDING'
    """), {"uid": user["id"]})

    # 写流水
    db.execute(text("""
        INSERT INTO prcp_task_log
          (task_id, log_type, summary_json, created_by)
        VALUES (:tid, 'RUN_RESULT', :sj, :uid)
    """), {"tid": tid, "sj": json.dumps(
        {"summary_by_currency": summary, "matched_amount": matched_amt,
         "matched_count": matched_cnt, "gap_amount": gap_amt}, ensure_ascii=False, default=str),
        "uid": user["id"]})

    db.execute(text("""
        UPDATE prcp_task SET status='DONE', matched_amount=:ma, matched_count=:mc,
               gap_amount=:ga, finished_at=NOW(), updated_by=:uid WHERE id=:id
    """), {"ma": matched_amt, "mc": matched_cnt, "ga": gap_amt, "uid": user["id"], "id": tid})
    db.commit()

    return {
        "task_id": tid,
        "summary_by_currency": summary,
        "matched_amount": round(matched_amt, 2),
        "matched_count": matched_cnt,
        "gap_amount": round(gap_amt, 2),
        "status": "DONE",
    }


@router.get("/{tid}/log")
async def task_log(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT id, log_type, summary_json, created_at
        FROM prcp_task_log WHERE task_id=:tid ORDER BY id DESC
    """), {"tid": tid}).fetchall()
    items = []
    for r in rows:
        try:
            payload = json.loads(r[2]) if r[2] else {}
        except Exception:
            payload = {"raw": r[2]}
        items.append({
            "id": r[0], "log_type": r[1], "payload": payload,
            "created_at": r[3].isoformat() if r[3] else None,
        })
    return {"items": items}