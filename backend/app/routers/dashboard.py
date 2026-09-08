"""PRCP Dashboard 概览 — 头寸 / 调度 / 缺口 KPI"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def overview(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """总览 KPI：组算任务 / 待调度笔数 / 当日缺口 / 总头寸"""
    tasks = db.execute(text("SELECT COUNT(*) FROM prcp_task WHERE is_deleted=0")).scalar() or 0
    pending = db.execute(text("SELECT COUNT(*) FROM prcp_position WHERE status='PENDING' AND is_deleted=0")).scalar() or 0
    settled = db.execute(text("SELECT COUNT(*) FROM prcp_position WHERE status='SETTLED' AND is_deleted=0")).scalar() or 0
    rules = db.execute(text("SELECT COUNT(*) FROM prcp_rule WHERE is_deleted=0")).scalar() or 0

    # 当日缺口总额（假设 amount 单位为元）
    gap = db.execute(text(
        "SELECT COALESCE(SUM(amount),0) FROM prcp_position WHERE status='PENDING' AND is_deleted=0"
    )).scalar() or 0

    return {
        "kpi": [
            {"label": "组算任务", "value": tasks, "unit": "个", "color": "#667eea"},
            {"label": "待调度笔数", "value": pending, "unit": "笔", "color": "#f59e0b"},
            {"label": "已结算笔数", "value": settled, "unit": "笔", "color": "#52c41a"},
            {"label": "缺口规模", "value": round(float(gap) / 10000, 2), "unit": "万元", "color": "#764ba2"},
        ],
        "rules_count": rules,
        "pending_count": pending,
        "settled_count": settled,
    }


@router.get("/task-trend")
async def task_trend(days: int = 14, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """近 N 天组算任务趋势"""
    rows = db.execute(text("""
        SELECT DATE(created_at) AS d, COUNT(*) AS n
        FROM prcp_task
        WHERE is_deleted=0 AND created_at >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        GROUP BY DATE(created_at) ORDER BY d
    """), {"days": days}).fetchall()
    return {
        "items": [{"date": r[0].isoformat(), "count": r[1]} for r in rows]
    }


@router.get("/currency-distribution")
async def currency_distribution(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """币种头寸分布"""
    rows = db.execute(text("""
        SELECT currency, COUNT(*) AS n, COALESCE(SUM(amount),0) AS total
        FROM prcp_position WHERE is_deleted=0
        GROUP BY currency ORDER BY total DESC LIMIT 8
    """)).fetchall()
    return {
        "items": [{"currency": r[0], "count": r[1], "amount": float(r[2])} for r in rows]
    }