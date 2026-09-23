"""PRCP 组合反算 · 结果驾驶舱

设计目标：所有数据均在系统中能查询到，默认以「组合方案 2026」为查询项。

数据来源（全部基于 prcp_* 业务表）：
- 方案配置：prcp_reverse_scheme + prcp_coa_scheme
- Run 信息：prcp_reverse_run（最新 SUCCESS）
- 月份列表：prcp_data_reverse (distinct date_offset)
- 节点元数据：prcp_coa_node（按 coa_scheme_id）
- 5 监管指标：prcp_metric_coefficient（ROE/CET1/LCR/NSFR/DELTA_EVE）
- 节点余额与利率：prcp_data_reverse.current_balance / weighted_rate

端点：
- GET /reverse-dashboard/options                  方案/Run/月份下拉
- GET /reverse-dashboard/snapshot                 驾驶舱快照（一次拉全）
"""
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/reverse-dashboard", tags=["ReverseDashboard"])

# 监管阈值（用于风险预警展示）
THRESHOLDS = {
    "CET1": {"min": 8.5, "direction": "down"},   # 银保监要求 ≥ 8.5%
    "LCR":  {"min": 100, "direction": "down"},    # 银保监要求 ≥ 100%
    "NSFR": {"min": 100, "direction": "down"},    # 银保监要求 ≥ 100%
    "ROE":  {"min": 11, "direction": "down"},     # 行业参考 ≥ 11%
    "DELTA_EVE": {"max_abs": 5.0, "direction": "abs"},  # |ΔEVE| ≤ 5% (内部参考)
}

DEFAULT_METRIC_TYPES = ["ROE", "CET1", "LCR", "NSFR", "DELTA_EVE"]


# ---------- 工具：分类节点（与 ReverseMetricTable 一致） ----------
def _classify(node_code: str, path: str) -> str:
    code = node_code or ""
    p = path or ""
    if code.startswith("ZX_A") or p.startswith("/L1_资产") or p == "/L1_ASSET/":
        return "ASSET"
    if code.startswith("ZX_L") or p.startswith("/L1_负债") or p == "/L1_LIABILITY/":
        return "LIABILITY"
    if code.startswith("ZX_E") or p.startswith("/L1_权益") or p == "/L1_EQUITY/":
        return "EQUITY"
    if p.startswith("/L1_表外") or p == "/L1_OFF_BALANCE/":
        return "OFF_BALANCE"
    return "OTHER"


@router.get("/options")
async def options(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """下拉选项：所有组合反算方案 + 每个方案的 Run 列表 + 默认方案"""
    schemes = db.execute(text("""
        SELECT s.id AS rev_id, s.scheme_code, s.scheme_name, s.coa_scheme_id, s.data_date,
               c.scheme_code AS coa_code, c.scheme_name AS coa_name, s.horizon_months
        FROM prcp_reverse_scheme s
        LEFT JOIN prcp_coa_scheme c ON c.id = s.coa_scheme_id
        WHERE s.is_deleted = 0
        ORDER BY s.id DESC
    """)).fetchall()

    scheme_items = [{
        "rev_id": r[0],
        "scheme_code": r[1],
        "scheme_name": r[2],
        "coa_scheme_id": r[3],
        "base_data_date": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]) if r[4] else None,
        "coa_scheme_code": r[5],
        "coa_scheme_name": r[6],
        "horizon_months": r[7] or 24,
    } for r in schemes]

    # 默认方案
    default = next((s for s in scheme_items if s["scheme_code"] == "2026"),
                   scheme_items[0] if scheme_items else None)

    # 默认方案的默认 run（最新 SUCCESS）+ 月份
    default_run = None
    default_date_offset = 1
    if default:
        run = db.execute(text("""
            SELECT id, status, start_at, end_at, duration_sec FROM prcp_reverse_run
            WHERE scheme_id = :sid AND status = 'SUCCESS' AND is_deleted = 0
            ORDER BY id DESC LIMIT 1
        """), {"sid": default["rev_id"]}).first()
        if run:
            default_run = {"run_id": run[0], "status": run[1],
                           "start_at": run[2].isoformat() if hasattr(run[2], "isoformat") else str(run[2]),
                           "end_at": run[3].isoformat() if hasattr(run[3], "isoformat") else str(run[3]),
                           "duration_sec": run[4] or 0}
            # 该 run 的最大 date_offset
            max_off = db.execute(text("""
                SELECT MAX(date_offset) FROM prcp_data_reverse
                WHERE scheme_code = :sc AND run_id = :rid AND is_deleted = 0
            """), {"sc": default["scheme_code"], "rid": run[0]}).scalar()
            default_date_offset = int(max_off or 1)

    return {
        "schemes": scheme_items,
        "default": {
            "scheme_code": default["scheme_code"] if default else None,
            "run_id": default_run["run_id"] if default_run else None,
            "date_offset": default_date_offset,
        },
    }


@router.get("/runs")
async def list_runs(
    scheme_code: str = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """方案下的所有 Run"""
    rev = db.execute(text("""
        SELECT id FROM prcp_reverse_scheme WHERE scheme_code=:sc AND is_deleted=0
    """), {"sc": scheme_code}).first()
    if not rev:
        raise HTTPException(404, f"方案 {scheme_code} 不存在")
    rev_id = rev[0]

    rows = db.execute(text("""
        SELECT r.id, r.status, r.run_code, r.start_at, r.end_at, r.duration_sec, r.optimal_value
        FROM prcp_reverse_run r
        WHERE r.scheme_id = :sid AND r.is_deleted = 0
        ORDER BY r.id DESC
    """), {"sid": rev_id}).fetchall()

    return {
        "scheme_code": scheme_code,
        "items": [{
            "run_id": r[0], "status": r[1], "run_code": r[2],
            "start_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]) if r[3] else None,
            "end_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]) if r[4] else None,
            "duration_sec": r[5] or 0,
            "optimal_value": float(r[6] or 0),
        } for r in rows],
    }


@router.get("/dates")
async def list_dates(
    scheme_code: str = Query(...),
    run_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Run 下的所有月份（M1..M24）"""
    rows = db.execute(text("""
        SELECT DISTINCT date_offset, data_date
        FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND is_deleted = 0
          AND offset_unit = 'M'
        ORDER BY date_offset ASC
    """), {"sc": scheme_code, "rid": run_id}).fetchall()
    return {
        "scheme_code": scheme_code,
        "run_id": run_id,
        "items": [{"date_offset": d[0], "data_date": str(d[1])} for d in rows],
    }


@router.get("/snapshot")
async def snapshot(
    scheme_code: str = Query("2026", description="组合方案编码，默认 2026"),
    run_id: Optional[int] = Query(None, description="Run id；缺省取最新 SUCCESS"),
    date_offset: int = Query(1, description="预测月份 M1..M24"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """驾驶舱快照：KPI + 趋势 + 大类分布 + 节点矩阵 + Top 榜 + 风险预警"""
    # 1. 取方案 + coa_scheme_id
    rev = db.execute(text("""
        SELECT s.id, s.coa_scheme_id, s.scheme_name, s.data_date, s.horizon_months,
               c.scheme_code AS coa_code, c.scheme_name AS coa_name
        FROM prcp_reverse_scheme s
        LEFT JOIN prcp_coa_scheme c ON c.id = s.coa_scheme_id
        WHERE s.scheme_code = :sc AND s.is_deleted = 0
    """), {"sc": scheme_code}).first()
    if not rev:
        raise HTTPException(404, f"方案 {scheme_code} 不存在")
    rev_id, coa_scheme_id, scheme_name, base_date, horizon_months, coa_code, coa_name = rev

    # 2. Run（缺省取最新 SUCCESS）
    if run_id is None:
        latest = db.execute(text("""
            SELECT id FROM prcp_reverse_run
            WHERE scheme_id = :sid AND status = 'SUCCESS' AND is_deleted = 0
            ORDER BY id DESC LIMIT 1
        """), {"sid": rev_id}).first()
        if not latest:
            raise HTTPException(404, "该方案无 SUCCESS 运行记录")
        run_id = int(latest[0])

    # 3. 当前月份的 data_date
    dd_row = db.execute(text("""
        SELECT data_date FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND date_offset = :do
          AND offset_unit = 'M' AND is_deleted = 0
        ORDER BY data_date DESC LIMIT 1
    """), {"sc": scheme_code, "rid": run_id, "do": date_offset}).first()
    if not dd_row:
        raise HTTPException(404, f"未找到 M{date_offset}")
    data_date = dd_row[0]

    # 4. 节点元数据
    nodes = []
    if coa_scheme_id:
        nrows = db.execute(text("""
            SELECT id, node_code, node_name, node_level, path
            FROM prcp_coa_node
            WHERE scheme_id = :s AND is_deleted = 0
            ORDER BY path, node_level
        """), {"s": coa_scheme_id}).fetchall()
        nodes = [{
            "coa_node_id": n[0],
            "node_code": n[1],
            "node_name": n[2],
            "node_level": n[3] or 1,
            "path": n[4] or "",
        } for n in nrows]

    # 5. 当前月份的余额/利率
    rev_rows = db.execute(text("""
        SELECT coa_node_id, node_code, current_balance, weighted_rate, interest_amount, risk_weight
        FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND date_offset = :do
          AND offset_unit = 'M' AND is_deleted = 0
    """), {"sc": scheme_code, "rid": run_id, "do": date_offset}).fetchall()
    rev_map: Dict[str, Dict] = {r[1]: {
        "coa_node_id": r[0], "current_balance": float(r[2] or 0),
        "weighted_rate": float(r[3] or 0), "interest_amount": float(r[4] or 0),
        "risk_weight": float(r[5] or 0),
    } for r in rev_rows}

    # 6. 当前月份的 5 个指标
    metric_map: Dict[str, Dict[str, float]] = {}
    if nodes:
        ph = ",".join([f":n{i}" for i in range(len(nodes))])
        params = {"sc": coa_code, "dd": data_date}
        for i, n in enumerate(nodes):
            params[f"n{i}"] = n["node_code"]
        ph2 = ",".join([f":m{i}" for i in range(len(DEFAULT_METRIC_TYPES))])
        for i, m in enumerate(DEFAULT_METRIC_TYPES):
            params[f"m{i}"] = m
        mrows = db.execute(text(f"""
            SELECT node_code, metric_type, current_value
            FROM prcp_metric_coefficient
            WHERE is_deleted = 0
              AND scheme_code = :sc
              AND data_date = :dd
              AND node_code IN ({ph})
              AND metric_type IN ({ph2})
        """), params).fetchall()
        for r in mrows:
            metric_map.setdefault(r[0], {})[r[1]] = float(r[2] or 0)

    # 7. KPI 聚合
    total_nodes = len(nodes)
    with_metrics = sum(1 for n in nodes if metric_map.get(n["node_code"]))
    asset_total = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                      if _classify(n["node_code"], n["path"]) == "ASSET" and n["node_code"] in rev_map)
    liability_total = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                          if _classify(n["node_code"], n["path"]) == "LIABILITY" and n["node_code"] in rev_map)
    equity_total = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                       if _classify(n["node_code"], n["path"]) == "EQUITY" and n["node_code"] in rev_map)
    off_balance = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                      if _classify(n["node_code"], n["path"]) == "OFF_BALANCE" and n["node_code"] in rev_map)

    metric_avg: Dict[str, Optional[float]] = {}
    metric_max: Dict[str, Optional[float]] = {}
    metric_min: Dict[str, Optional[float]] = {}
    for m in DEFAULT_METRIC_TYPES:
        vals = [metric_map[n["node_code"]].get(m) for n in nodes if metric_map.get(n["node_code"], {}).get(m) is not None]
        metric_avg[m] = round(sum(vals) / len(vals), 4) if vals else None
        metric_max[m] = round(max(vals), 4) if vals else None
        metric_min[m] = round(min(vals), 4) if vals else None

    kpi = {
        "total_nodes": total_nodes,
        "with_metrics": with_metrics,
        "asset_total": round(asset_total, 2),
        "liability_total": round(liability_total, 2),
        "equity_total": round(equity_total, 2),
        "off_balance": round(off_balance, 2),
        "metric_avg": metric_avg,
        "metric_max": metric_max,
        "metric_min": metric_min,
    }

    # 8. 24 月趋势（5 指标每月平均值）
    trend_rows = db.execute(text("""
        SELECT date_offset, data_date FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND offset_unit = 'M' AND is_deleted = 0
        GROUP BY date_offset, data_date ORDER BY date_offset ASC
    """), {"sc": scheme_code, "rid": run_id}).fetchall()
    month_dates = [{"date_offset": int(t[0]), "data_date": str(t[1])} for t in trend_rows]

    # 一次性查所有指标（24 × 40 × 5 = 4800 行）
    if nodes and month_dates:
        ph_n = ",".join([f":n{i}" for i in range(len(nodes))])
        ph_m = ",".join([f":m{i}" for i in range(len(DEFAULT_METRIC_TYPES))])
        params = {"sc": coa_code}
        for i, n in enumerate(nodes):
            params[f"n{i}"] = n["node_code"]
        for i, m in enumerate(DEFAULT_METRIC_TYPES):
            params[f"m{i}"] = m
        all_metric_rows = db.execute(text(f"""
            SELECT data_date, node_code, metric_type, current_value
            FROM prcp_metric_coefficient
            WHERE is_deleted = 0 AND scheme_code = :sc
              AND node_code IN ({ph_n})
              AND metric_type IN ({ph_m})
        """), params).fetchall()
    else:
        all_metric_rows = []

    # 按月份聚合
    from collections import defaultdict
    month_metric_vals: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in all_metric_rows:
        dd = str(r[0])
        m = r[2]
        month_metric_vals[dd][m].append(float(r[3] or 0))

    trend = {"months": [], "ROE": [], "CET1": [], "LCR": [], "NSFR": [], "DELTA_EVE": []}
    for md in month_dates:
        dd = md["data_date"]
        trend["months"].append(md["data_date"].replace("-", "")[2:])  # YYMMDD
        for m in DEFAULT_METRIC_TYPES:
            vals = month_metric_vals.get(dd, {}).get(m, [])
            avg = round(sum(vals) / len(vals), 4) if vals else None
            trend[m].append(avg)

    # 9. 大类分布（饼图）
    cat_dist: Dict[str, float] = {"ASSET": 0, "LIABILITY": 0, "EQUITY": 0, "OFF_BALANCE": 0, "OTHER": 0}
    cat_count: Dict[str, int] = {"ASSET": 0, "LIABILITY": 0, "EQUITY": 0, "OFF_BALANCE": 0, "OTHER": 0}
    for n in nodes:
        cat = _classify(n["node_code"], n["path"])
        cat_count[cat] += 1
        cat_dist[cat] += rev_map.get(n["node_code"], {}).get("current_balance", 0)
    category_distribution = {
        "by_count": cat_count,
        "by_balance": {k: round(v, 2) for k, v in cat_dist.items()},
    }

    # 10. 节点详情矩阵（用于热力图 + Top 榜）
    node_matrix = []
    for n in nodes:
        nc = n["node_code"]
        cat = _classify(nc, n["path"])
        mv = metric_map.get(nc, {})
        r_data = rev_map.get(nc, {})
        node_matrix.append({
            "coa_node_id": n["coa_node_id"],
            "node_code": nc,
            "node_name": n["node_name"],
            "node_level": n["node_level"],
            "category": cat,
            "current_balance": r_data.get("current_balance", 0),
            "weighted_rate": r_data.get("weighted_rate", 0),
            "metric_values": mv,
        })

    # 11. Top 10 节点（按余额排序）
    top_nodes = sorted(node_matrix, key=lambda x: abs(x["current_balance"]), reverse=True)[:10]

    # 12. 风险预警（指标超限节点）
    alerts = []
    for n in node_matrix:
        mv = n["metric_values"]
        if not mv:
            continue
        node_alerts = []
        # CET1 / LCR / NSFR / ROE 下限
        for mk in ["CET1", "LCR", "NSFR", "ROE"]:
            v = mv.get(mk)
            if v is None:
                continue
            thr = THRESHOLDS[mk]["min"]
            if v < thr:
                node_alerts.append({"metric": mk, "value": v, "threshold": thr,
                                    "severity": "critical" if v < thr * 0.9 else "warn",
                                    "msg": f"{mk}={v} 低于阈值 {thr}"})
        # ΔEVE 绝对值上限
        de = mv.get("DELTA_EVE")
        if de is not None:
            thr_abs = THRESHOLDS["DELTA_EVE"]["max_abs"]
            if abs(de) > thr_abs:
                node_alerts.append({"metric": "DELTA_EVE", "value": de, "threshold": thr_abs,
                                    "severity": "critical" if abs(de) > thr_abs * 1.2 else "warn",
                                    "msg": f"|ΔEVE|={abs(de)} 超过阈值 {thr_abs}"})
        if node_alerts:
            alerts.append({
                "node_code": n["node_code"],
                "node_name": n["node_name"],
                "category": n["category"],
                "current_balance": n["current_balance"],
                "alerts": node_alerts,
                "alert_count": len(node_alerts),
            })
    alerts.sort(key=lambda a: (-a["alert_count"], -a["current_balance"]))

    return {
        "scheme_code": scheme_code,
        "scheme_name": scheme_name,
        "coa_scheme_code": coa_code,
        "coa_scheme_name": coa_name,
        "base_data_date": base_date.isoformat() if hasattr(base_date, "isoformat") else str(base_date) if base_date else None,
        "horizon_months": horizon_months,
        "run_id": run_id,
        "date_offset": date_offset,
        "data_date": data_date.isoformat() if isinstance(data_date, date) else str(data_date),
        "kpi": kpi,
        "trend": trend,
        "category_distribution": category_distribution,
        "node_matrix": node_matrix,
        "top_nodes": top_nodes,
        "risk_alerts": alerts,
        "risk_alert_total": len(alerts),
        "thresholds": THRESHOLDS,
    }