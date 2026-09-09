"""PRCP Dashboard 概览 — 账户册 / 报表 / 指标 / 数据 """
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def overview(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """总览 KPI：账户册方案 / 报表 / 指标 / 评分规则数"""
    schemes = db.execute(text("SELECT COUNT(*) FROM prcp_coa_scheme WHERE is_deleted=0")).scalar() or 0
    coa_nodes = db.execute(text("SELECT COUNT(*) FROM prcp_coa_node WHERE is_deleted=0")).scalar() or 0
    reports = db.execute(text("SELECT COUNT(*) FROM prcp_rpt_report WHERE is_deleted=0")).scalar() or 0
    rpt_items = db.execute(text("SELECT COUNT(*) FROM prcp_rpt_item WHERE is_deleted=0")).scalar() or 0
    kpi_schemes = db.execute(text("SELECT COUNT(*) FROM prcp_kpi_scheme WHERE is_deleted=0")).scalar() or 0
    kpi_defs = db.execute(text("SELECT COUNT(*) FROM prcp_kpi_definition WHERE is_deleted=0")).scalar() or 0
    kpi_values = db.execute(text("SELECT COUNT(*) FROM prcp_kpi_value WHERE is_deleted=0")).scalar() or 0
    score_rules = db.execute(text("SELECT COUNT(*) FROM prcp_kpi_score_rule WHERE is_deleted=0")).scalar() or 0

    # 最新数据日期
    latest_date = db.execute(text("SELECT MAX(data_date) FROM prcp_kpi_value WHERE is_deleted=0")).scalar()

    return {
        "kpi": [
            {"label": "账户册方案", "value": schemes, "unit": "个", "color": "#667eea"},
            {"label": "账户册节点", "value": coa_nodes, "unit": "个", "color": "#764ba2"},
            {"label": "报表模板", "value": reports, "unit": "个", "color": "#f59e0b"},
            {"label": "报表表项", "value": rpt_items, "unit": "项", "color": "#52c41a"},
            {"label": "指标方案", "value": kpi_schemes, "unit": "个", "color": "#13c2c2"},
            {"label": "指标定义", "value": kpi_defs, "unit": "个", "color": "#1890ff"},
            {"label": "指标值", "value": kpi_values, "unit": "条", "color": "#722ed1"},
            {"label": "评分规则", "value": score_rules, "unit": "个", "color": "#eb2f96"},
        ],
        "latest_data_date": latest_date.isoformat() if latest_date else None,
    }


@router.get("/kpi-trend")
async def kpi_trend(days: int = 14, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """近 N 天指标值录入趋势"""
    rows = db.execute(text("""
        SELECT DATE(created_at) AS d, COUNT(*) AS n
        FROM prcp_kpi_value
        WHERE is_deleted=0 AND created_at >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        GROUP BY DATE(created_at) ORDER BY d
    """), {"days": days}).fetchall()
    return {
        "items": [{"date": r[0].isoformat(), "count": r[1]} for r in rows]
    }


@router.get("/scheme-distribution")
async def scheme_distribution(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """指标方案下的指标定义分布"""
    rows = db.execute(text("""
        SELECT s.scheme_code, s.scheme_name, COUNT(d.id) AS def_count,
               COALESCE(SUM(CASE WHEN v.score IS NOT NULL THEN 1 ELSE 0 END), 0) AS scored_count
        FROM prcp_kpi_scheme s
        LEFT JOIN prcp_kpi_definition d ON d.scheme_id = s.id AND d.is_deleted=0
        LEFT JOIN prcp_kpi_value v ON v.kpi_id = d.id AND v.is_deleted=0
        WHERE s.is_deleted=0
        GROUP BY s.id, s.scheme_code, s.scheme_name
        ORDER BY def_count DESC LIMIT 8
    """)).fetchall()
    return {
        "items": [
            {"scheme_code": r[0], "scheme_name": r[1], "def_count": int(r[2]), "scored_count": int(r[3])}
            for r in rows
        ]
    }