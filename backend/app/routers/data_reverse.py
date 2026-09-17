"""反算结果查询 API — 与基础数据表结构一致的二维矩阵
表结构 prcp_data_reverse = prcp_data_basic + scheme_code + run_id + record_id
"""
import io
import urllib.parse
from typing import Optional, List
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/data-reverse", tags=["反算结果查询"])

# 与 prcp_data_basic 一致的 13 个期限桶
BUCKETS = [
    {"key": "d1",  "name": "1日",  "col": "D1"},
    {"key": "d7",  "name": "7日",  "col": "D7"},
    {"key": "m1",  "name": "1M",   "col": "M1"},
    {"key": "m3",  "name": "3M",   "col": "M3"},
    {"key": "m6",  "name": "6M",   "col": "M6"},
    {"key": "y1",  "name": "1Y",   "col": "Y1"},
    {"key": "y2",  "name": "2Y",   "col": "Y2"},
    {"key": "y3",  "name": "3Y",   "col": "Y3"},
    {"key": "y5",  "name": "5Y",   "col": "Y5"},
    {"key": "y10", "name": "10Y",  "col": "Y10"},
    {"key": "y15", "name": "15Y",  "col": "Y15"},
    {"key": "y20", "name": "20Y",  "col": "Y20"},
    {"key": "y30", "name": "30Y",  "col": "Y30"},
]
ORIG_FIELDS = [f"orig_{b['key']}" for b in BUCKETS]
REM_FIELDS = [f"rem_{b['key']}" for b in BUCKETS]
NUMERIC_KEYS = ORIG_FIELDS + REM_FIELDS + [
    "current_balance", "avg_balance", "weighted_rate",
    "interest_amount", "risk_weight",
]


# ============================================================
# 1. 反算方案列表（带统计）
# ============================================================
@router.get("/schemes")
async def list_schemes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """列出所有有反算结果的方案 + 最新一次 run"""
    rows = db.execute(text("""
        SELECT s.scheme_code, s.scheme_name,
               (SELECT COUNT(*) FROM prcp_reverse_run r
                WHERE r.scheme_id=s.id AND r.is_deleted=0) AS run_count,
               (SELECT COUNT(*) FROM prcp_data_reverse d
                WHERE d.scheme_code=s.scheme_code AND d.is_deleted=0) AS total_rows,
               (SELECT MAX(created_at) FROM prcp_reverse_run
                WHERE scheme_id=s.id AND is_deleted=0) AS last_run_at
        FROM prcp_reverse_scheme s
        WHERE s.is_deleted=0
        ORDER BY s.scheme_code
    """)).fetchall()
    items = []
    for r in rows:
        if int(r[3] or 0) == 0:
            continue  # 跳过没有反算结果的方案
        items.append({
            "scheme_code": r[0],
            "scheme_name": r[1],
            "run_count": int(r[2] or 0),
            "total_rows": int(r[3] or 0),
            "last_run_at": r[4].isoformat() if r[4] else None,
        })
    return {"items": items, "total": len(items)}


# ============================================================
# 2. 反算执行列表
# ============================================================
@router.get("/runs")
async def list_runs(
    scheme_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """某方案的所有反算执行"""
    where = ["r.is_deleted=0"]
    params = {}
    if scheme_code:
        where.append("s.scheme_code = :sc")
        params["sc"] = scheme_code
    rows = db.execute(text(f"""
        SELECT r.id, r.scheme_id, s.scheme_code, s.scheme_name,
               r.status, r.start_at, r.end_at, r.optimal_value,
               (SELECT COUNT(*) FROM prcp_data_reverse d WHERE d.run_id=r.id AND d.is_deleted=0) AS row_count,
               r.created_at
        FROM prcp_reverse_run r
        JOIN prcp_reverse_scheme s ON s.id=r.scheme_id
        WHERE {' AND '.join(where)}
        ORDER BY r.id DESC
    """), params).fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "scheme_id": r[1],
            "scheme_code": r[2],
            "scheme_name": r[3],
            "status": r[4],
            "start_at": r[5].isoformat() if r[5] else None,
            "end_at": r[6].isoformat() if r[6] else None,
            "optimal_value": float(r[7]) if r[7] is not None else None,
            "row_count": int(r[8] or 0),
            "created_at": r[9].isoformat() if r[9] else None,
        })
    return {"items": items, "total": len(items)}


# ============================================================
# 3. 矩阵视图（核心 API）
# ============================================================
@router.get("/by-scheme-matrix")
async def by_scheme_matrix(
    scheme_code: str = Query(...),
    run_id: Optional[int] = Query(None),
    data_date: Optional[str] = Query(None),
    date_offset: Optional[int] = Query(None),
    offset_unit: str = Query("M"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """按反算方案 + 数据日期 + 偏移量 矩阵
    scheme_code: 必填
    run_id: 可选，缺省取最新一次 SUCCESS 的 run
    data_date: 可选，缺省取最早一个月
    date_offset: 月份数（1..24），可选
    offset_unit: 'M'（月），固定
    """
    # 1. 取 run_id（缺省取最新 SUCCESS）
    if run_id is None:
        latest = db.execute(text("""
            SELECT r.id FROM prcp_reverse_run r
            JOIN prcp_reverse_scheme s ON s.id=r.scheme_id
            WHERE s.scheme_code=:sc AND r.status='SUCCESS' AND r.is_deleted=0
            ORDER BY r.id DESC LIMIT 1"""), {"sc": scheme_code}).first()
        if not latest:
            return {"nodes": [], "matrix": {}, "categories": {},
                    "scheme_code": scheme_code, "run_id": None, "data_date": None,
                    "date_offset": None, "offset_unit": offset_unit,
                    "months_list": []}
        run_id = latest[0]

    # 2. 取 coa_scheme_id（用于拉账户册节点）
    coa_row = db.execute(text("""
        SELECT s.coa_scheme_id FROM prcp_reverse_scheme s WHERE s.scheme_code=:sc"""),
        {"sc": scheme_code}).first()
    coa_scheme_id = coa_row[0] if coa_row else None

    # 3. 拉账户册节点
    nodes = []
    if coa_scheme_id:
        node_rows = db.execute(text("""
            SELECT id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, description
            FROM prcp_coa_node
            WHERE scheme_id=:s AND is_deleted=0
            ORDER BY path, sort_order"""), {"s": coa_scheme_id}).fetchall()
        nodes = [{
            "coa_node_id": r[0], "node_code": r[1], "node_name": r[2],
            "parent_id": r[3], "node_level": r[4] or 1,
            "node_type": r[5] or "", "path": r[6] or "",
            "sort_order": r[7] or 0, "description": r[8] or "",
        } for r in node_rows]

    # 4. 拉反算结果行（按 run_id + data_date + date_offset）
    where = ["scheme_code=:sc", "run_id=:rid", "is_deleted=0"]
    params = {"sc": scheme_code, "rid": run_id}
    if data_date:
        where.append("data_date=:dd")
        params["dd"] = data_date
    if date_offset is not None:
        where.append("date_offset=:do")
        params["do"] = date_offset
    if offset_unit:
        where.append("offset_unit=:ou")
        params["ou"] = offset_unit

    rows = db.execute(text(f"""
        SELECT coa_node_id, node_code, node_name, node_level, parent_code, category, is_leaf,
               orig_d1, orig_d7, orig_m1, orig_m3, orig_m6,
               orig_y1, orig_y2, orig_y3, orig_y5, orig_y10, orig_y15, orig_y20, orig_y30,
               rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
               rem_y1, rem_y2, rem_y3, rem_y5, rem_y10, rem_y15, rem_y20, rem_y30,
               asf_rsf, hqla_factor, current_balance, avg_balance,
               weighted_rate, interest_amount, risk_weight, calc_note,
               data_date, date_offset, record_id
        FROM prcp_data_reverse
        WHERE {' AND '.join(where)}
    """), params).fetchall()

    # 5. 构建 matrix（coa_node_id -> row dict）
    matrix: dict = {}
    for r in rows:
        m = {}
        # 注意：列顺序对应上面 SELECT 列表
        idx = 0
        m["coa_node_id"] = r[idx]; idx += 1
        m["node_code"] = r[idx]; idx += 1
        m["node_name"] = r[idx]; idx += 1
        m["node_level"] = r[idx]; idx += 1
        m["parent_code"] = r[idx]; idx += 1
        m["category"] = r[idx]; idx += 1
        m["is_leaf"] = r[idx]; idx += 1
        # 13 + 13 = 26 buckets
        for k in ORIG_FIELDS + REM_FIELDS:
            m[k] = float(r[idx] or 0); idx += 1
        m["asf_rsf"] = r[idx]; idx += 1
        m["hqla_factor"] = float(r[idx]) if r[idx] is not None else None; idx += 1
        m["current_balance"] = float(r[idx] or 0); idx += 1
        m["avg_balance"] = float(r[idx] or 0); idx += 1
        m["weighted_rate"] = float(r[idx] or 0); idx += 1
        m["interest_amount"] = float(r[idx] or 0); idx += 1
        m["risk_weight"] = float(r[idx] or 0); idx += 1
        m["calc_note"] = r[idx]; idx += 1
        m["data_date"] = str(r[idx]) if r[idx] else None; idx += 1
        m["date_offset"] = r[idx]; idx += 1
        m["record_id"] = r[idx]; idx += 1
        matrix[m["coa_node_id"]] = m

    # 6. 大类汇总
    def classify_category(n: dict) -> str:
        code = n.get("node_code") or ""
        path = n.get("path") or ""
        if code.startswith("ZX_A"):
            return "资产"
        if code.startswith("ZX_L"):
            return "负债"
        if code.startswith("ZX_E"):
            return "权益"
        parts = path.split("/")
        if len(parts) >= 2 and parts[1].startswith("L1_"):
            return parts[1][3:]
        return "其他"

    categories: dict = {}
    node_by_id = {n["coa_node_id"]: n for n in nodes}
    l1_cids = {n["coa_node_id"] for n in nodes if n.get("node_level") == 1}
    l1_has_data = any(matrix.get(cid, {}).get("current_balance", 0) for cid in l1_cids)
    target_cids = l1_cids if l1_has_data else set(matrix.keys())
    for cid, m in matrix.items():
        if cid not in target_cids:
            continue
        n = node_by_id.get(cid)
        cat = classify_category(n)
        bucket = categories.setdefault(cat, {k: 0.0 for k in NUMERIC_KEYS})
        for k in NUMERIC_KEYS:
            bucket[k] += float(m.get(k) or 0)
    for cat in categories:
        for k in categories[cat]:
            categories[cat][k] = round(categories[cat][k], 4)

    # 7. 拉所有可选月份（用于前端选择）
    months_rows = db.execute(text("""
        SELECT DISTINCT data_date, date_offset FROM prcp_data_reverse
        WHERE scheme_code=:sc AND run_id=:rid AND is_deleted=0
        ORDER BY date_offset"""), {"sc": scheme_code, "rid": run_id}).fetchall()
    months_list = [{"data_date": str(r[0]), "date_offset": r[1]} for r in months_rows]

    return {
        "scheme_code": scheme_code,
        "run_id": run_id,
        "data_date": data_date,
        "date_offset": date_offset,
        "offset_unit": offset_unit,
        "nodes": nodes,
        "matrix": matrix,
        "categories": categories,
        "months_list": months_list,
    }


# ============================================================
# 4. 导出 Excel（按方案 + run）
# ============================================================
@router.get("/export-xlsx")
async def export_xlsx(
    scheme_code: str = Query(...),
    run_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """导出 Excel：每账户册 × 24 月的二维表（含 13+13 期限桶）"""
    if run_id is None:
        latest = db.execute(text("""
            SELECT r.id FROM prcp_reverse_run r
            JOIN prcp_reverse_scheme s ON s.id=r.scheme_id
            WHERE s.scheme_code=:sc AND r.status='SUCCESS' AND r.is_deleted=0
            ORDER BY r.id DESC LIMIT 1"""), {"sc": scheme_code}).first()
        if not latest:
            raise HTTPException(404, "无可导出的 SUCCESS run")
        run_id = latest[0]

    # 拉账户册节点
    coa_row = db.execute(text("""
        SELECT s.coa_scheme_id, s.scheme_name FROM prcp_reverse_scheme s WHERE s.scheme_code=:sc"""),
        {"sc": scheme_code}).first()
    coa_scheme_id = coa_row[0] if coa_row else None
    scheme_name = coa_row[1] if coa_row else scheme_code

    nodes = []
    if coa_scheme_id:
        node_rows = db.execute(text("""
            SELECT id, node_code, node_name, node_level, path, sort_order
            FROM prcp_coa_node
            WHERE scheme_id=:s AND is_deleted=0
            ORDER BY path, sort_order"""), {"s": coa_scheme_id}).fetchall()
        nodes = node_rows

    # 拉所有反算结果
    rows = db.execute(text("""
        SELECT coa_node_id, data_date, date_offset, node_code, node_name, node_level,
               parent_code, category, is_leaf,
               orig_d1, orig_d7, orig_m1, orig_m3, orig_m6,
               orig_y1, orig_y2, orig_y3, orig_y5, orig_y10, orig_y15, orig_y20, orig_y30,
               rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
               rem_y1, rem_y2, rem_y3, rem_y5, rem_y10, rem_y15, rem_y20, rem_y30,
               asf_rsf, hqla_factor, current_balance, avg_balance,
               weighted_rate, interest_amount, risk_weight, calc_note,
               record_id
        FROM prcp_data_reverse
        WHERE scheme_code=:sc AND run_id=:rid AND is_deleted=0
    """), {"sc": scheme_code, "rid": run_id}).fetchall()
    row_map = {(r[0], str(r[1]), r[2]): r for r in rows}

    wb = Workbook()
    ws = wb.active
    ws.title = "反算结果"

    # row 1: 标题
    ws.cell(1, 3, f"反算结果 — {scheme_code} ({scheme_name}) · Run#{run_id} · 余额：亿元；利率：%")

    # row 2: 二级表头分组
    ws.cell(2, 11, "原始期限(金额)")
    ws.cell(2, 24, "剩余期限（金额）")

    # row 3: 详细列名（与基础数据表基本一致，但 ID = scheme_code_自增id）
    # col 1=ID, col 2=数据日期, col 3=月份, col 4=编码, col 5=名称, col 6=层级
    # col 7=父级编码, col 8=是否末级, col 9=大类, col 10=偏移量, col 11=偏移单位
    # col 12-24 = orig 13 buckets, col 25-37 = rem 13 buckets
    # col 38=ASF/RSF, col 39=HQLA, col 40-44 = 度量, col 45=备注
    detail_headers = ["ID（方案编码_自增ID）", "数据日期", "月份(M)",
                      "账户册编码", "账户册名称", "账户册层级",
                      "父级账户册编码", "是否末级节点", "大类",
                      "偏移量", "偏移单位"]
    for b in BUCKETS:
        detail_headers.append(f"orig_{b['key']}")
    for b in BUCKETS:
        detail_headers.append(f"rem_{b['key']}")
    detail_headers += ["ASF/RSF", "HQLA", "当前余额", "平均余额", "加权平均利率",
                      "平均利息收支", "风险权重", "备注"]
    for col, h in enumerate(detail_headers, start=1):
        ws.cell(3, col, h)

    # 样式
    FILL_L1 = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    FILL_L2 = PatternFill(start_color="EAF1F8", end_color="EAF1F8", fill_type="solid")
    FILL_SEP = PatternFill(start_color="FFF7E6", end_color="FFF7E6", fill_type="solid")
    FONT_L1 = Font(bold=True, size=11, color="1F4E78")
    FONT_L2 = Font(bold=True, size=10)
    FONT_NORMAL = Font(size=10)

    prev_l1_code = None
    ri = 4
    for n in nodes:
        node_id, node_code, node_name, node_level, _path, _sort = n
        # 拉这个节点的所有月份（24 行）
        node_rows_for_n = sorted(
            [r for r in rows if r[0] == node_id],
            key=lambda x: x[2]
        )
        if not node_rows_for_n:
            continue

        # 大类分隔空行
        if node_level == 1 and prev_l1_code is not None and node_code != prev_l1_code:
            for col in range(1, len(detail_headers) + 1):
                cell = ws.cell(ri, col, "")
                cell.fill = FILL_SEP
            ri += 1
        if node_level == 1:
            prev_l1_code = node_code

        # 缩进
        indent = "　" * max((node_level or 1) - 1, 0)
        display_name = f"{indent}{node_name}"

        for nr in node_rows_for_n:
            data_date_val = str(nr[1])
            date_offset_val = nr[2]
            record_id = nr[43]  # record_id 是第 44 个字段（idx 43）

            # ID = scheme_code_自增id（业务拼接 ID）
            ws.cell(ri, 1, record_id)
            ws.cell(ri, 2, data_date_val)
            ws.cell(ri, 3, date_offset_val)
            ws.cell(ri, 4, node_code)
            name_cell = ws.cell(ri, 5, display_name)
            if node_level == 1:
                name_cell.font = FONT_L1; name_cell.fill = FILL_L1
            elif node_level == 2:
                name_cell.font = FONT_L2; name_cell.fill = FILL_L2
            else:
                name_cell.font = FONT_NORMAL
            ws.cell(ri, 6, node_level)
            ws.cell(ri, 7, nr[6] or "")
            ws.cell(ri, 8, nr[8] if nr[8] is not None else 0)
            ws.cell(ri, 9, nr[7] or "")
            ws.cell(ri, 10, date_offset_val)
            ws.cell(ri, 11, "M")
            # col 12-24: orig buckets
            for i in range(13):
                ws.cell(ri, 12 + i, float(nr[9 + i] or 0))
            # col 25-37: rem buckets
            for i in range(13):
                ws.cell(ri, 25 + i, float(nr[22 + i] or 0))
            # col 38: ASF/RSF
            ws.cell(ri, 38, nr[35] if nr[35] is not None else "")
            # col 39: HQLA
            if nr[36] is not None:
                ws.cell(ri, 39, float(nr[36]))
            else:
                ws.cell(ri, 39, "")
            # col 40-44: 度量
            ws.cell(ri, 40, float(nr[37]) if nr[37] is not None else 0)
            ws.cell(ri, 41, float(nr[38]) if nr[38] is not None else 0)
            ws.cell(ri, 42, float(nr[39]) if nr[39] is not None else 0)
            ws.cell(ri, 43, float(nr[40]) if nr[40] is not None else 0)
            ws.cell(ri, 44, float(nr[41]) if nr[41] is not None else 0)
            ws.cell(ri, 45, nr[42] or "")

            # L1 整行底色
            if node_level == 1:
                for col in range(1, len(detail_headers) + 1):
                    cell = ws.cell(ri, col)
                    if not cell.fill or cell.fill.start_color.rgb in (None, "00000000"):
                        cell.fill = FILL_L1
            ri += 1

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 8
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 36
    ws.freeze_panes = "F4"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    # 中文文件名（RFC 5987）
    fname = f"反算结果_{scheme_code}_run{run_id}.xlsx"
    quoted = urllib.parse.quote(fname)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"reverse.xlsx\"; filename*=UTF-8''{quoted}",
        },
    )


# ============================================================
# 5. 拉某 run 的所有 data_date 选项
# ============================================================
@router.get("/dates")
async def list_dates(
    scheme_code: str = Query(...),
    run_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """某 run 的所有月份（用于前端选择器）"""
    if run_id is None:
        latest = db.execute(text("""
            SELECT r.id FROM prcp_reverse_run r
            JOIN prcp_reverse_scheme s ON s.id=r.scheme_id
            WHERE s.scheme_code=:sc AND r.status='SUCCESS' AND r.is_deleted=0
            ORDER BY r.id DESC LIMIT 1"""), {"sc": scheme_code}).first()
        if not latest:
            return {"items": [], "total": 0}
        run_id = latest[0]

    rows = db.execute(text("""
        SELECT DISTINCT data_date, date_offset FROM prcp_data_reverse
        WHERE scheme_code=:sc AND run_id=:rid AND is_deleted=0
        ORDER BY date_offset"""), {"sc": scheme_code, "rid": run_id}).fetchall()
    items = [{"data_date": str(r[0]), "date_offset": r[1]} for r in rows]
    return {"items": items, "total": len(items)}