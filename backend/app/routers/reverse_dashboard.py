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
from datetime import date, datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/reverse-dashboard", tags=["ReverseDashboard"])

# 大类中文名（与前端 CATEGORY_META 保持一致）
_CAT_LABEL = {
    "ASSET": "资产", "LIABILITY": "负债", "EQUITY": "权益",
    "OFF_BALANCE": "表外", "OTHER": "其他",
}


def _col_letter(idx: int) -> str:
    """1 → A, 27 → AA"""
    s = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s

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
    # 中信 ZX_COA 账户册编码：S01 资产 / S02 负债 / S03 权益 / S04 表外
    if code.startswith("S01") or code.startswith("ZX_A") or p.startswith("/L1_资产") or p == "/L1_ASSET/":
        return "ASSET"
    if code.startswith("S02") or code.startswith("ZX_L") or p.startswith("/L1_负债") or p == "/L1_LIABILITY/":
        return "LIABILITY"
    if code.startswith("S03") or code.startswith("ZX_E") or p.startswith("/L1_权益") or p == "/L1_EQUITY/":
        return "EQUITY"
    if code.startswith("S04") or p.startswith("/L1_表外") or p == "/L1_OFF_BALANCE/":
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


def _leaf_map(db, coa_scheme_id: Optional[int]) -> Dict[str, bool]:
    """末级节点判定 —— 以 prcp_data_basic.is_leaf 为准（数据源自带，权威）"""
    m: Dict[str, bool] = {}
    if not coa_scheme_id:
        return m
    rows = db.execute(text("""
        SELECT b.node_code, MAX(b.is_leaf)
        FROM prcp_data_basic b
        JOIN prcp_coa_node n ON n.id = b.coa_node_id
        WHERE n.scheme_id = :sid AND n.is_deleted = 0 AND b.is_deleted = 0
        GROUP BY b.node_code
    """), {"sid": coa_scheme_id}).fetchall()
    for r in rows:
        if r[0]:
            m[r[0]] = bool(r[1])
    return m


def _node_paths(db, coa_scheme_id: Optional[int]) -> Dict[str, str]:
    """node_code → path（用于 _classify 与 path 前缀推断末级）"""
    m: Dict[str, str] = {}
    if not coa_scheme_id:
        return m
    rows = db.execute(text("""
        SELECT node_code, path FROM prcp_coa_node
        WHERE scheme_id = :sid AND is_deleted = 0
    """), {"sid": coa_scheme_id}).fetchall()
    for r in rows:
        m[r[0]] = r[1] or ""
    return m


def _is_leaf_by_path(nc: str, node_paths: Dict[str, str]) -> bool:
    """path 前缀推断：存在 M 使 M.path 以 N.path + "/" 开头 ⇒ N 非末级"""
    p = node_paths.get(nc)
    if not p:
        return True
    prefix = p.rstrip("/") + "/"
    for other, op in node_paths.items():
        if other != nc and op and op.startswith(prefix) and op != p:
            return False
    return True


def coa_scheme_id_of(db, scheme_code: str) -> Optional[int]:
    """组合方案 → 账户册方案 id"""
    r = db.execute(text("""
        SELECT coa_scheme_id FROM prcp_reverse_scheme
        WHERE scheme_code = :sc AND is_deleted = 0 LIMIT 1
    """), {"sc": scheme_code}).first()
    return r[0] if r else None


@router.get("/balance-export")
async def balance_export(
    scheme_code: str = Query("2026", description="组合方案编码"),
    run_id: Optional[int] = Query(None, description="Run id；缺省取最新 SUCCESS"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """结果导出：按账户册导出测算期每月预测余额（xlsx）

    Sheet1 账户册结构   —— 树形展示全部账户册节点（名称按层级缩进）
                           末级节点 = 自身预测余额；父节点 = 子树汇总（roll-up 上卷）
    Sheet2 按层级汇总   —— L1..Ln 每层节点数 + 逐月汇总 + 末级合计行
    Sheet3 末级节点大类汇总 —— 资产/负债/权益/表外/其他 逐月合计
    Sheet4 口径说明     —— 方案/Run/基准日/月份区间/节点数/余额口径/数据源
    """
    # 1. 方案 + Run
    rev = db.execute(text("""
        SELECT s.id, s.scheme_name, s.coa_scheme_id, s.data_date, s.horizon_months,
               c.scheme_code AS coa_code, c.scheme_name AS coa_name
        FROM prcp_reverse_scheme s
        LEFT JOIN prcp_coa_scheme c ON c.id = s.coa_scheme_id
        WHERE s.scheme_code = :sc AND s.is_deleted = 0
    """), {"sc": scheme_code}).first()
    if not rev:
        raise HTTPException(404, f"方案 {scheme_code} 不存在")
    rev_id, scheme_name, coa_scheme_id, base_date, horizon, coa_code, coa_name = rev

    if run_id is None:
        latest = db.execute(text("""
            SELECT id FROM prcp_reverse_run
            WHERE scheme_id = :sid AND status = 'SUCCESS' AND is_deleted = 0
            ORDER BY id DESC LIMIT 1
        """), {"sid": rev_id}).first()
        if not latest:
            raise HTTPException(404, "该方案无 SUCCESS 运行记录")
        run_id = int(latest[0])

    # 2. 月份（M1..M24；offset 0 与 1 同为基准月，跳过 0）
    month_rows = db.execute(text("""
        SELECT DISTINCT date_offset, data_date FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND is_deleted = 0
          AND offset_unit = 'M' AND date_offset >= 1
        ORDER BY date_offset ASC
    """), {"sc": scheme_code, "rid": run_id}).fetchall()
    months = [(int(m[0]), str(m[1])) for m in month_rows]
    if not months:
        raise HTTPException(404, "该 Run 无月度预测数据")

    # 3. 节点元数据（账户册结构）
    node_rows = db.execute(text("""
        SELECT node_code, node_name, node_level, path, id, parent_id, sort_order
        FROM prcp_coa_node
        WHERE scheme_id = :sid AND is_deleted = 0
        ORDER BY node_level, sort_order, node_code
    """), {"sid": coa_scheme_id}).fetchall() if coa_scheme_id else []
    node_paths = {n[0]: n[3] or "" for n in node_rows}
    node_level = {n[0]: (n[2] or 1) for n in node_rows}
    node_name = {n[0]: n[1] or n[0] for n in node_rows}
    node_parent = {n[0]: n[5] for n in node_rows}          # parent_id
    node_id_by_code = {n[0]: n[4] for n in node_rows}
    children_of: Dict[Optional[int], List[str]] = {}
    for n in node_rows:
        children_of.setdefault(n[5], []).append(n[0])

    # 4. 末级判定
    leaf_map = _leaf_map(db, coa_scheme_id)

    def _is_leaf_of(nc: str) -> bool:
        if nc in leaf_map:
            return leaf_map[nc]
        return _is_leaf_by_path(nc, node_paths)

    # 5. 月度余额矩阵（末级节点自身值）
    val_rows = db.execute(text("""
        SELECT date_offset, node_code, current_balance
        FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND is_deleted = 0
          AND offset_unit = 'M' AND date_offset >= 1
    """), {"sc": scheme_code, "rid": run_id}).fetchall()
    off_idx = {o: i for i, (o, _) in enumerate(months)}
    vals: Dict[str, List[float]] = {}
    for r in val_rows:
        o, nc, bal = r[0], r[1], float(r[2] or 0)
        if o not in off_idx:
            continue
        vals.setdefault(nc, [0.0] * len(months))[off_idx[o]] = bal

    # 5b. 层级汇总（roll-up）：末级取自身值，父节点取子树之和（自底向上上卷）
    #     只采信末级节点的自身值 —— 避免父子重复计算
    rolled: Dict[str, List[float]] = {}
    for nc in vals:
        if _is_leaf_of(nc):
            rolled[nc] = list(vals[nc])

    def _rollup(nc: str, depth: int = 0) -> List[float]:
        """返回该节点子树内所有末级节点的余额之和"""
        if nc in rolled:
            return rolled[nc]
        if depth > 12:
            return [0.0] * len(months)
        kids = children_of.get(node_id_by_code.get(nc), [])
        if not kids:
            rolled[nc] = [0.0] * len(months)
            return rolled[nc]
        acc = [0.0] * len(months)
        for k in kids:
            kv = _rollup(k, depth + 1)
            for i in range(len(acc)):
                acc[i] += kv[i]
        rolled[nc] = acc
        return acc

    for n in node_rows:
        _rollup(n[0])
    for nc in vals:
        if nc not in rolled:
            rolled[nc] = list(vals[nc])

    # 6. 生成 xlsx
    from io import BytesIO
    from urllib.parse import quote
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    HDR_FILL = PatternFill("solid", fgColor="1F4E9C")
    HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
    SUB_FILL = PatternFill("solid", fgColor="EAF1FB")
    TITLE_FONT = Font(bold=True, size=12)
    THIN = Side(style="thin", color="BFBFBF")
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
    NUM_FMT = '#,##0.00'

    def _write_header(ws, headers, row=1):
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=c, value=h)
            cell.fill = HDR_FILL
            cell.font = HDR_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = BORDER

    # ---- Sheet1：账户册结构（树形展示 + 层级汇总）----
    ws = wb.active
    ws.title = "账户册结构"
    m_headers = [f"M{o}\n{d}" for o, d in months]
    headers = ["节点编码", "节点名称", "层级", "大类", "末级节点"] + m_headers
    _write_header(ws, headers)
    ws.row_dimensions[1].height = 32

    # 树序：按 path 排序，保证父节点紧邻其子节点
    ordered = sorted(
        [n[0] for n in node_rows] or list(vals.keys()),
        key=lambda nc: (node_paths.get(nc, ""), node_level.get(nc, 9), nc))
    r = 2
    for nc in ordered:
        cat = _classify(nc, node_paths.get(nc, ""))
        is_leaf = _is_leaf_of(nc)
        # 末级节点显示自身值；父节点显示子树汇总（roll-up）
        series = rolled.get(nc) or vals.get(nc) or [0.0] * len(months)
        lvl = node_level.get(nc, 1)
        ws.cell(row=r, column=1, value=nc).border = BORDER
        c = ws.cell(row=r, column=2, value=node_name.get(nc, nc))
        c.alignment = Alignment(horizontal="left", vertical="center", indent=(lvl - 1) * 2)
        c.border = BORDER
        if not is_leaf:
            c.font = Font(bold=True, size=10)
        ws.cell(row=r, column=3, value=lvl).border = BORDER
        ws.cell(row=r, column=4, value=_CAT_LABEL.get(cat, cat)).border = BORDER
        ws.cell(row=r, column=5, value="是" if is_leaf else "").border = BORDER
        for i, v in enumerate(series):
            c = ws.cell(row=r, column=6 + i, value=v)
            c.number_format = NUM_FMT
            c.border = BORDER
            if not is_leaf:
                c.font = Font(bold=True, size=10)
        if not is_leaf:
            for cc in range(1, 6 + len(months)):
                ws.cell(row=r, column=cc).fill = SUB_FILL
        r += 1

    ws.freeze_panes = "F2"
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 6
    ws.column_dimensions["D"].width = 10
    ws.column_dimensions["E"].width = 10
    for i in range(len(months)):
        ws.column_dimensions[_col_letter(6 + i)].width = 16

    # ---- Sheet2：按层级汇总 ----
    ws_lv = wb.create_sheet("按层级汇总")
    _write_header(ws_lv, ["层级", "节点数", "末级节点数"] + m_headers)
    ws_lv.row_dimensions[1].height = 32
    levels = sorted(set(node_level.values()))
    r = 2
    for lv in levels:
        lv_nodes = [nc for nc in ordered if node_level.get(nc, 1) == lv]
        lv_leaf = [nc for nc in lv_nodes if _is_leaf_of(nc)]
        acc = [0.0] * len(months)
        for nc in lv_nodes:
            ser = rolled.get(nc) or [0.0] * len(months)
            for i in range(len(acc)):
                acc[i] += ser[i]
        ws_lv.cell(row=r, column=1, value=f"L{lv}").font = Font(bold=True)
        ws_lv.cell(row=r, column=2, value=len(lv_nodes))
        ws_lv.cell(row=r, column=3, value=len(lv_leaf))
        for i, v in enumerate(acc):
            c = ws_lv.cell(row=r, column=4 + i, value=v)
            c.number_format = NUM_FMT
        r += 1
    # 末级节点合计行
    all_leaf = [nc for nc in ordered if _is_leaf_of(nc)]
    acc = [0.0] * len(months)
    for nc in all_leaf:
        ser = rolled.get(nc) or [0.0] * len(months)
        for i in range(len(acc)):
            acc[i] += ser[i]
    ws_lv.cell(row=r, column=1, value="末级合计").font = Font(bold=True)
    ws_lv.cell(row=r, column=2, value=len(all_leaf)).font = Font(bold=True)
    for i, v in enumerate(acc):
        c = ws_lv.cell(row=r, column=4 + i, value=v)
        c.number_format = NUM_FMT
        c.font = Font(bold=True)
    ws_lv.column_dimensions["A"].width = 14
    ws_lv.column_dimensions["B"].width = 10
    ws_lv.column_dimensions["C"].width = 12
    for i in range(len(months)):
        ws_lv.column_dimensions[_col_letter(4 + i)].width = 16

    # ---- Sheet3：末级节点大类汇总 ----
    ws2 = wb.create_sheet("末级节点大类汇总")
    _write_header(ws2, ["大类"] + m_headers)
    ws2.row_dimensions[1].height = 32
    cat_tot = {k: [0.0] * len(months) for k in _CAT_LABEL}
    for nc in ordered:
        if not _is_leaf_of(nc):
            continue
        series = rolled.get(nc) or vals.get(nc) or [0.0] * len(months)
        cat = _classify(nc, node_paths.get(nc, ""))
        for i, v in enumerate(series):
            cat_tot[cat][i] += v
    r = 2
    for cat in ["ASSET", "LIABILITY", "EQUITY", "OFF_BALANCE", "OTHER"]:
        ws2.cell(row=r, column=1, value=_CAT_LABEL[cat]).font = Font(bold=True)
        for i, v in enumerate(cat_tot[cat]):
            c = ws2.cell(row=r, column=2 + i, value=v)
            c.number_format = NUM_FMT
        r += 1
    # 合计行
    ws2.cell(row=r, column=1, value="合计").font = Font(bold=True)
    for i in range(len(months)):
        c = ws2.cell(row=r, column=2 + i, value=sum(cat_tot[k][i] for k in cat_tot))
        c.number_format = NUM_FMT
        c.font = Font(bold=True)
    ws2.column_dimensions["A"].width = 16
    for i in range(len(months)):
        ws2.column_dimensions[_col_letter(2 + i)].width = 16

    # ---- Sheet4：口径说明 ----
    ws3 = wb.create_sheet("口径说明")
    _write_header(ws3, ["项目", "内容"])
    meta_rows = [
        ("组合方案", f"{scheme_code} · {scheme_name}"),
        ("Run ID", str(run_id)),
        ("账户册方案", f"{coa_code or '-'} · {coa_name or '-'}"),
        ("基准日", str(base_date) if base_date else "-"),
        ("预测期", f"{horizon or len(months)} 个月"),
        ("月份区间", f"M{months[0][0]} ({months[0][1]}) ~ M{months[-1][0]} ({months[-1][1]})"),
        ("账户册节点数", f"{len(node_rows)} 个（含末级 {sum(1 for nc in ordered if _is_leaf_of(nc))} 个）"),
        ("有预测值节点数", f"{len(vals)} 个"),
        ("数据来源", "prcp_data_reverse（组合反算结果）+ prcp_coa_node（账户册结构）+ prcp_data_basic（末级判定）"),
        ("导出时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("余额口径", "末级节点 = 自身预测余额；非末级节点 = 其子树内末级节点余额之和（层级汇总，上卷计算）"),
        ("单位说明", "与源表一致（1 = 1 元）；各层级互不重叠，末级合计 = 账户册总额"),
    ]
    for i, (k, v) in enumerate(meta_rows, start=2):
        ws3.cell(row=i, column=1, value=k).font = Font(bold=True)
        ws3.cell(row=i, column=2, value=v)
    ws3.column_dimensions["A"].width = 16
    ws3.column_dimensions["B"].width = 95

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"组合反算结果导出_{scheme_code}_run{run_id}_{months[0][1][:7]}至{months[-1][1][:7]}.xlsx"
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"},
    )


@router.get("/balance-trend")
async def balance_trend(
    scheme_code: str = Query("2026", description="组合方案编码"),
    run_id: Optional[int] = Query(None, description="Run id；缺省取最新 SUCCESS"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """末级账户册余额走势 —— 测算期每个月月末余额

    返回：
      months     : [{offset, date}]        M1..M24
      categories : [{key,label,values}]    按大类汇总的走势
      nodes      : [{code,name,category,values,total}]  末级节点明细走势
    """
    # 1. 定位 run
    if run_id is None:
        latest = db.execute(text("""
            SELECT r.id FROM prcp_reverse_run r
            JOIN prcp_reverse_scheme s ON s.id = r.scheme_id
            WHERE s.scheme_code = :sc AND r.status = 'SUCCESS' AND r.is_deleted = 0
            ORDER BY r.id DESC LIMIT 1
        """), {"sc": scheme_code}).first()
        if not latest:
            raise HTTPException(404, "该方案无 SUCCESS 运行记录")
        run_id = int(latest[0])

    # 2. 月份序列（M1..M24；date_offset=0 与 1 同为基准月，跳过 0）
    month_rows = db.execute(text("""
        SELECT DISTINCT date_offset, data_date
        FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND is_deleted = 0
          AND offset_unit = 'M' AND date_offset >= 1
        ORDER BY date_offset ASC
    """), {"sc": scheme_code, "rid": run_id}).fetchall()
    months = [{"offset": m[0], "date": str(m[1])} for m in month_rows]
    offsets = [m["offset"] for m in months]

    # 3. 末级节点月度余额
    #    注意：不同 Run 写入的 is_leaf / category 标记并不可靠
    #    （如 REV_ANT_REG 全为 0、category 为 NULL），
    #    故末级判定以 prcp_data_basic.is_leaf 为准，无 basic 行时回退 path 前缀推断。
    rows = db.execute(text("""
        SELECT date_offset, node_code, node_name, category, current_balance
        FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND is_deleted = 0
          AND offset_unit = 'M' AND date_offset >= 1
        ORDER BY date_offset ASC
    """), {"sc": scheme_code, "rid": run_id}).fetchall()

    # 末级判定
    leaf_map = _leaf_map(db, coa_scheme_id_of(db, scheme_code))
    node_paths = _node_paths(db, coa_scheme_id_of(db, scheme_code))

    def _is_leaf_of(nc: str) -> bool:
        if nc in leaf_map:
            return leaf_map[nc]
        return _is_leaf_by_path(nc, node_paths)

    off_idx = {o: i for i, o in enumerate(offsets)}
    node_meta: Dict[str, Dict] = {}
    node_vals: Dict[str, List[float]] = {}
    for r in rows:
        o, nc, nn, cat, bal = r[0], r[1], r[2], r[3], float(r[4] or 0)
        if o not in off_idx:
            continue
        if nc not in node_meta:
            node_meta[nc] = {"code": nc, "name": nn or nc, "category": cat or "OTHER"}
            node_vals[nc] = [0.0] * len(offsets)
        node_vals[nc][off_idx[o]] = bal

    # 4. 按大类汇总（末级节点）
    cat_keys = ["ASSET", "LIABILITY", "EQUITY", "OFF_BALANCE", "OTHER"]
    cat_vals: Dict[str, List[float]] = {k: [0.0] * len(offsets) for k in cat_keys}
    for nc, meta in node_meta.items():
        if not _is_leaf_of(nc):
            continue
        cat = meta["category"] if meta["category"] in cat_vals else "OTHER"
        if cat == "OTHER" and meta["category"] not in cat_vals:
            cat = _classify(nc, node_paths.get(nc, ""))
        for i, v in enumerate(node_vals[nc]):
            cat_vals[cat][i] += v

    # 5. 节点明细按期末余额降序
    nodes = sorted(
        [{"code": nc, "name": meta["name"], "category": meta["category"],
          "values": node_vals[nc],
          "total": sum(abs(v) for v in node_vals[nc])} for nc, meta in node_meta.items()],
        key=lambda x: x["total"], reverse=True)

    return {
        "scheme_code": scheme_code,
        "run_id": run_id,
        "months": months,
        "categories": [
            {"key": k, "values": [round(v, 2) for v in cat_vals[k]]} for k in cat_keys
        ],
        "nodes": nodes,
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
        SELECT coa_node_id, node_code, current_balance, avg_balance,
               weighted_rate, interest_amount, risk_weight
        FROM prcp_data_reverse
        WHERE scheme_code = :sc AND run_id = :rid AND date_offset = :do
          AND offset_unit = 'M' AND is_deleted = 0
    """), {"sc": scheme_code, "rid": run_id, "do": date_offset}).fetchall()
    rev_map: Dict[str, Dict] = {r[1]: {
        "coa_node_id": r[0], "current_balance": float(r[2] or 0),
        "avg_balance": float(r[3] or 0),
        "weighted_rate": float(r[4] or 0), "interest_amount": float(r[5] or 0),
        "risk_weight": float(r[6] or 0),
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
        # 如果该 schema 没有任何指标数据，回退到任何 scheme_code（兼容 ZXCOA_V1 数据）
        if not mrows:
            params2 = {"dd": data_date}
            for i, n in enumerate(nodes):
                params2[f"n{i}"] = n["node_code"]
            for i, m in enumerate(DEFAULT_METRIC_TYPES):
                params2[f"m{i}"] = m
            mrows = db.execute(text(f"""
                SELECT node_code, metric_type, current_value
                FROM prcp_metric_coefficient
                WHERE is_deleted = 0
                  AND data_date = :dd
                  AND node_code IN ({ph})
                  AND metric_type IN ({ph2})
            """), params2).fetchall()
        for r in mrows:
            metric_map.setdefault(r[0], {})[r[1]] = float(r[2] or 0)

    # 7. KPI 聚合（仅汇总叶子节点，避免父节点合计被重复计算）
    total_nodes = len(nodes)
    with_metrics = sum(1 for n in nodes if metric_map.get(n["node_code"]))

    # ZX_COA 编码是按位置分层的（如 S01 / S0101 / S010101），不能用 startsWith 判断父子关系
    # 用 path 字段（"/" 分隔）判断：节点 N 有子节点 ⇔ 存在节点 M 使 M.path 以 N.path + "/" 开头
    node_paths = {n["node_code"]: n["path"] for n in nodes}
    parent_set = set()
    for nc_a, p_a in node_paths.items():
        if not p_a:
            continue
        for nc_b, p_b in node_paths.items():
            if nc_a == nc_b or not p_b:
                continue
            if p_b.startswith(p_a.rstrip("/") + "/") and p_b != p_a:
                parent_set.add(nc_a)
                break

    def _is_leaf(nc: str) -> bool:
        return nc not in parent_set

    asset_total = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                      if _classify(n["node_code"], n["path"]) == "ASSET"
                      and _is_leaf(n["node_code"])
                      and n["node_code"] in rev_map)
    liability_total = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                          if _classify(n["node_code"], n["path"]) == "LIABILITY"
                          and _is_leaf(n["node_code"])
                          and n["node_code"] in rev_map)
    equity_total = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                       if _classify(n["node_code"], n["path"]) == "EQUITY"
                       and _is_leaf(n["node_code"])
                       and n["node_code"] in rev_map)
    off_balance = sum(rev_map[n["node_code"]]["current_balance"] for n in nodes
                      if _classify(n["node_code"], n["path"]) == "OFF_BALANCE"
                      and _is_leaf(n["node_code"])
                      and n["node_code"] in rev_map)

    metric_avg: Dict[str, Optional[float]] = {}
    metric_max: Dict[str, Optional[float]] = {}
    metric_min: Dict[str, Optional[float]] = {}
    for m in DEFAULT_METRIC_TYPES:
        vals = [metric_map[n["node_code"]].get(m) for n in nodes if metric_map.get(n["node_code"], {}).get(m) is not None]
        metric_avg[m] = round(sum(vals) / len(vals), 4) if vals else None
        metric_max[m] = round(max(vals), 4) if vals else None
        metric_min[m] = round(min(vals), 4) if vals else None

    # 贷款的加权平均利率：境内各项人民币贷款（S010101*）下属 L4 节点按余额加权平均
    loan_weighted_num = 0.0
    loan_weighted_den = 0.0
    for n in nodes:
        nc = n["node_code"]
        # 只取 L4 子节点（不含 L3 父节点 S010101000000）
        if not (nc.startswith("S01010101") or nc.startswith("S01010102") or
                nc.startswith("S01010103") or nc.startswith("S01010104") or
                nc.startswith("S01010105")):
            continue
        r = rev_map.get(nc)
        if not r:
            continue
        bal = r["current_balance"]
        rate = r["weighted_rate"]
        if abs(bal) < 0.01:
            continue
        loan_weighted_num += bal * rate
        loan_weighted_den += bal
    loan_weighted_rate = round(loan_weighted_num / loan_weighted_den, 6) if loan_weighted_den > 0 else None

    kpi = {
        "total_nodes": total_nodes,
        "with_metrics": with_metrics,
        "asset_total": round(asset_total, 2),
        "liability_total": round(liability_total, 2),
        "equity_total": round(equity_total, 2),
        "off_balance": round(off_balance, 2),
        "loan_weighted_rate": loan_weighted_rate,
        "metric_avg": metric_avg,
        "metric_max": metric_max,
        "metric_min": metric_min,
    }

    # 指标评分（5 个 REG_* 指标）：按 prcp_kpi_value.score 聚合（基期数据日期 base_date）
    kpi_scores = []
    kpi_score_rows = db.execute(text("""
        SELECT d.kpi_code, d.kpi_name, v.current_value, v.score,
               s.min_value AS seg_min, s.max_value AS seg_max, s.segment_desc
        FROM prcp_kpi_definition d
        LEFT JOIN prcp_kpi_value v
               ON v.kpi_id = d.id AND v.data_date = :bdd AND v.is_deleted = 0
        LEFT JOIN prcp_kpi_score_rule r
               ON r.kpi_id = d.id AND r.is_deleted = 0
        LEFT JOIN prcp_kpi_score_segment s
               ON s.rule_id = r.id AND s.is_deleted = 0
               AND (s.min_value IS NULL OR v.current_value >= s.min_value)
               AND (s.max_value IS NULL OR v.current_value <  s.max_value)
        WHERE d.is_deleted = 0 AND d.kpi_code LIKE 'REG_%'
        ORDER BY d.id
    """), {"bdd": base_date}).fetchall()
    for r in kpi_score_rows:
        kpi_scores.append({
            "kpi_code": r[0],
            "kpi_name": r[1],
            "value": float(r[2]) if r[2] is not None else None,
            "score": float(r[3]) if r[3] is not None else None,
            "segment_min": float(r[4]) if r[4] is not None else None,
            "segment_max": float(r[5]) if r[5] is not None else None,
            "segment_desc": r[6],
        })

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
        # 兼容 ZXCOA_V1：如果当前 scheme_code 没数据，回退到任意 scheme_code
        if not all_metric_rows:
            params2 = {}
            for i, n in enumerate(nodes):
                params2[f"n{i}"] = n["node_code"]
            for i, m in enumerate(DEFAULT_METRIC_TYPES):
                params2[f"m{i}"] = m
            all_metric_rows = db.execute(text(f"""
                SELECT data_date, node_code, metric_type, current_value
                FROM prcp_metric_coefficient
                WHERE is_deleted = 0
                  AND node_code IN ({ph_n})
                  AND metric_type IN ({ph_m})
            """), params2).fetchall()
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

    # 9b. 大类当前余额分布
    #     数据源：prcp_data_basic（账户册基础数据，按方案 + 基准日）
    #     口径：仅叶子节点累加（与 asset_total/liability_total KPI 卡片一致，
    #           避免父子节点重复计算 —— 非叶子节点也存有余额，全量累加会翻倍）
    #     语义：反映方案基准日的【当前余额结构】，不随预测月份漂移
    balance_date = None
    base_bal_map: Dict[str, float] = {}
    base_leaf_map: Dict[str, bool] = {}
    if coa_scheme_id:
        # 优先取反算方案的基准日；该日无数据时回退到该方案最新的可用日期
        bd_row = db.execute(text("""
            SELECT MAX(b.data_date) FROM prcp_data_basic b
            JOIN prcp_coa_node n ON n.id = b.coa_node_id
            WHERE n.scheme_id = :sid AND n.is_deleted = 0
              AND b.is_deleted = 0
              AND (:dd IS NULL OR b.data_date <= :dd)
        """), {"sid": coa_scheme_id, "dd": base_date}).first()
        if bd_row and bd_row[0]:
            balance_date = str(bd_row[0])
            bal_rows = db.execute(text("""
                SELECT b.node_code, b.current_balance, n.path, b.is_leaf
                FROM prcp_data_basic b
                JOIN prcp_coa_node n ON n.id = b.coa_node_id
                WHERE n.scheme_id = :sid AND n.is_deleted = 0
                  AND b.is_deleted = 0 AND b.data_date = :dd
            """), {"sid": coa_scheme_id, "dd": balance_date}).fetchall()
            for r in bal_rows:
                base_bal_map[r[0]] = float(r[1] or 0)
                base_leaf_map[r[0]] = bool(r[3])
                # 大类汇总只统计末级节点（与 asset_total/liability_total KPI 卡片一致）
                if r[3]:
                    cat_dist[_classify(r[0], r[2])] += float(r[1] or 0)

    # 9c. 大类【当月预测余额】分布（对照口径）
    #     数据源：prcp_data_reverse（反算结果，当前选中的预测月）
    #     口径：与 9b 相同的末级节点集合，保证两张图可直接对比
    cat_dist_forecast: Dict[str, float] = {"ASSET": 0, "LIABILITY": 0, "EQUITY": 0, "OFF_BALANCE": 0, "OTHER": 0}
    for n in nodes:
        nc = n["node_code"]
        if not base_leaf_map.get(nc, _is_leaf(nc)):
            continue
        r_data = rev_map.get(nc)
        if r_data:
            cat_dist_forecast[_classify(nc, n["path"])] += float(r_data.get("current_balance", 0) or 0)

    category_distribution = {
        "by_count": cat_count,
        # 基准日当前余额（prcp_data_basic）
        "by_balance": {k: round(v, 2) for k, v in cat_dist.items()},
        "balance_date": balance_date,
        "balance_source": "prcp_data_basic",
        # 当月预测余额（prcp_data_reverse，随预测月份变化）
        "by_balance_forecast": {k: round(v, 2) for k, v in cat_dist_forecast.items()},
        "forecast_date": str(data_date) if data_date else None,
        "forecast_source": "prcp_data_reverse",
    }

    # 10. 节点详情矩阵（用于当前余额柱状图 + Top 榜）
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
            # 末级节点判定：以基础数据的 is_leaf 为准（数据源自带），
            # 无基础数据行时回退到 path 前缀推断
            "is_leaf": base_leaf_map.get(nc, _is_leaf(nc)),
            "category": cat,
            "current_balance": r_data.get("current_balance", 0),
            "base_balance": base_bal_map.get(nc, 0),
            "avg_balance": r_data.get("avg_balance", 0),
            "weighted_rate": r_data.get("weighted_rate", 0),
            "interest_amount": r_data.get("interest_amount", 0),
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
        "kpi_scores": kpi_scores,
        "trend": trend,
        "category_distribution": category_distribution,
        "node_matrix": node_matrix,
        "top_nodes": top_nodes,
        "risk_alerts": alerts,
        "risk_alert_total": len(alerts),
        "thresholds": THRESHOLDS,
    }