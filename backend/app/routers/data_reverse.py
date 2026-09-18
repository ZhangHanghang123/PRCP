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
from app.services.buckets import BUCKETS, ORIG_COLS, REM_COLS

router = APIRouter(prefix="/data-reverse", tags=["反算结果查询"])

# 58 个期限桶（与 prcp_data_basic 完全一致）
ORIG_FIELDS = ORIG_COLS
REM_FIELDS = REM_COLS
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
               orig_m13, orig_m14, orig_m15, orig_m16, orig_m17, orig_m18, orig_m19, orig_m20,
               orig_m21, orig_m22, orig_m23, orig_m24, orig_m25, orig_m26, orig_m27, orig_m28,
               orig_m29, orig_m30, orig_m31, orig_m32, orig_m33, orig_m34, orig_m35, orig_m36,
               orig_m37, orig_m38, orig_m39, orig_m40, orig_m41, orig_m42, orig_m43, orig_m44,
               orig_m45, orig_m46, orig_m47, orig_m48, orig_m49, orig_m50, orig_m51, orig_m52,
               orig_m53, orig_m54, orig_m55, orig_m56, orig_m57, orig_m58, orig_m59, orig_m60,
               orig_y1, orig_y10, orig_y15, orig_y20, orig_y30,
               rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
               rem_m13, rem_m14, rem_m15, rem_m16, rem_m17, rem_m18, rem_m19, rem_m20,
               rem_m21, rem_m22, rem_m23, rem_m24, rem_m25, rem_m26, rem_m27, rem_m28,
               rem_m29, rem_m30, rem_m31, rem_m32, rem_m33, rem_m34, rem_m35, rem_m36,
               rem_m37, rem_m38, rem_m39, rem_m40, rem_m41, rem_m42, rem_m43, rem_m44,
               rem_m45, rem_m46, rem_m47, rem_m48, rem_m49, rem_m50, rem_m51, rem_m52,
               rem_m53, rem_m54, rem_m55, rem_m56, rem_m57, rem_m58, rem_m59, rem_m60,
               rem_y1, rem_y10, rem_y15, rem_y20, rem_y30,
               asf_rsf, hqla_factor, current_balance, avg_balance,
               weighted_rate, interest_amount, risk_weight, calc_note,
               data_date, date_offset, record_id
        FROM prcp_data_reverse
        WHERE {' AND '.join(where)}
    """), params).fetchall()

    # 5. 构建 matrix（coa_node_id -> row dict）
    # SELECT 列顺序：
    #   0=coa_node_id, 1=node_code, 2=node_name, 3=node_level, 4=parent_code, 5=category, 6=is_leaf,
    #   7-64=orig (58 列), 65-122=rem (58 列), 123=asf_rsf, 124=hqla_factor,
    #   125=current_balance, 126=avg_balance, 127=weighted_rate, 128=interest_amount, 129=risk_weight,
    #   130=calc_note, 131=data_date, 132=date_offset, 133=record_id
    n_b = len(ORIG_FIELDS)  # 58
    matrix: dict = {}
    for r in rows:
        m = {}
        m["coa_node_id"] = r[0]
        m["node_code"] = r[1]
        m["node_name"] = r[2]
        m["node_level"] = r[3]
        m["parent_code"] = r[4]
        m["category"] = r[5]
        m["is_leaf"] = r[6]
        for i, k in enumerate(ORIG_FIELDS):
            m[k] = float(r[i + 7] or 0)
        for i, k in enumerate(REM_FIELDS):
            m[k] = float(r[i + 7 + n_b] or 0)
        m["asf_rsf"] = r[7 + 2 * n_b]
        m["hqla_factor"] = float(r[7 + 2 * n_b + 1]) if r[7 + 2 * n_b + 1] is not None else None
        m["current_balance"] = float(r[7 + 2 * n_b + 2] or 0)
        m["avg_balance"] = float(r[7 + 2 * n_b + 3] or 0)
        m["weighted_rate"] = float(r[7 + 2 * n_b + 4] or 0)
        m["interest_amount"] = float(r[7 + 2 * n_b + 5] or 0)
        m["risk_weight"] = float(r[7 + 2 * n_b + 6] or 0)
        m["calc_note"] = r[7 + 2 * n_b + 7]
        m["data_date"] = str(r[7 + 2 * n_b + 8]) if r[7 + 2 * n_b + 8] else None
        m["date_offset"] = r[7 + 2 * n_b + 9]
        m["record_id"] = r[7 + 2 * n_b + 10]
        matrix[m["coa_node_id"]] = m

    # 6. 大类汇总（码值国际化：ASSET/LIABILITY/EQUITY/OFF_BALANCE）
    def classify_category(n: dict) -> str:
        code = n.get("node_code") or ""
        path = n.get("path") or ""
        if code.startswith("ZX_A"):
            return "ASSET"
        if code.startswith("ZX_L"):
            return "LIABILITY"
        if code.startswith("ZX_E"):
            return "EQUITY"
        parts = path.split("/")
        if len(parts) >= 2 and parts[1].startswith("L1_"):
            # path 已是 L1_ASSET / L1_LIABILITY / L1_EQUITY / L1_OFF_BALANCE 形式
            raw = parts[1][3:]
            # 兼容旧 path
            mapping = {'资产': 'ASSET', '负债': 'LIABILITY', '权益': 'EQUITY', '表外': 'OFF_BALANCE'}
            return mapping.get(raw, raw)
        return "OTHER"

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
               orig_m13, orig_m14, orig_m15, orig_m16, orig_m17, orig_m18, orig_m19, orig_m20,
               orig_m21, orig_m22, orig_m23, orig_m24, orig_m25, orig_m26, orig_m27, orig_m28,
               orig_m29, orig_m30, orig_m31, orig_m32, orig_m33, orig_m34, orig_m35, orig_m36,
               orig_m37, orig_m38, orig_m39, orig_m40, orig_m41, orig_m42, orig_m43, orig_m44,
               orig_m45, orig_m46, orig_m47, orig_m48, orig_m49, orig_m50, orig_m51, orig_m52,
               orig_m53, orig_m54, orig_m55, orig_m56, orig_m57, orig_m58, orig_m59, orig_m60,
               orig_y1, orig_y10, orig_y15, orig_y20, orig_y30,
               rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
               rem_m13, rem_m14, rem_m15, rem_m16, rem_m17, rem_m18, rem_m19, rem_m20,
               rem_m21, rem_m22, rem_m23, rem_m24, rem_m25, rem_m26, rem_m27, rem_m28,
               rem_m29, rem_m30, rem_m31, rem_m32, rem_m33, rem_m34, rem_m35, rem_m36,
               rem_m37, rem_m38, rem_m39, rem_m40, rem_m41, rem_m42, rem_m43, rem_m44,
               rem_m45, rem_m46, rem_m47, rem_m48, rem_m49, rem_m50, rem_m51, rem_m52,
               rem_m53, rem_m54, rem_m55, rem_m56, rem_m57, rem_m58, rem_m59, rem_m60,
               rem_y1, rem_y10, rem_y15, rem_y20, rem_y30,
               asf_rsf, hqla_factor, current_balance, avg_balance,
               weighted_rate, interest_amount, risk_weight, calc_note,
               record_id
        FROM prcp_data_reverse
        WHERE scheme_code=:sc AND run_id=:rid AND is_deleted=0
    """), {"sc": scheme_code, "rid": run_id}).fetchall()
    row_map = {(r[0], str(r[1]), r[2]): r for r in rows}

    # SELECT 列顺序：0=coa_node_id, 1=data_date, 2=date_offset, 3=node_code, 4=node_name, 5=node_level,
    #   6=parent_code, 7=category, 8=is_leaf,
    #   9-66=orig (58 列), 67-124=rem (58 列), 125=asf_rsf, 126=hqla_factor,
    #   127=current_balance, 128=avg_balance, 129=weighted_rate, 130=interest_amount, 131=risk_weight,
    #   132=calc_note, 133=record_id
    n_b = len(ORIG_FIELDS)  # 58
    orig_offset = 9
    rem_offset = orig_offset + n_b  # 67
    asf_offset = rem_offset + n_b  # 125

    wb = Workbook()
    ws = wb.active
    ws.title = "反算结果"

    # row 1: 标题
    ws.cell(1, 3, f"反算结果 — {scheme_code} ({scheme_name}) · Run#{run_id} · 余额：亿元；利率：%")

    # row 2: 二级表头分组
    n_buckets = len(BUCKETS)
    ws.cell(2, 11, "原始期限(金额)")
    ws.cell(2, 11 + n_buckets, "剩余期限（金额）")

    # row 3: 详细列名（与基础数据表基本一致，但 ID = scheme_code_自增id）
    # col 1=ID, col 2=数据日期, col 3=月份, col 4=编码, col 5=名称, col 6=层级
    # col 7=父级编码, col 8=是否末级, col 9=大类, col 10=偏移量, col 11=偏移单位
    # col 12-69 = orig 58 buckets, col 70-127 = rem 58 buckets
    # col 128=ASF/RSF, col 129=HQLA, col 130-134 = 度量, col 135=备注
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
            record_id = nr[asf_offset + 8]  # record_id 在 SELECT 末尾（asf_offset+8）

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
            # col 12-69: orig buckets (58 列)
            for i in range(n_buckets):
                ws.cell(ri, 12 + i, float(nr[orig_offset + i] or 0))
            # col 70-127: rem buckets (58 列)
            for i in range(n_buckets):
                ws.cell(ri, 12 + n_buckets + i, float(nr[rem_offset + i] or 0))
            # col 128: ASF/RSF
            ws.cell(ri, 12 + 2 * n_buckets, nr[asf_offset] if nr[asf_offset] is not None else "")
            # col 129: HQLA
            if nr[asf_offset + 1] is not None:
                ws.cell(ri, 12 + 2 * n_buckets + 1, float(nr[asf_offset + 1]))
            else:
                ws.cell(ri, 12 + 2 * n_buckets + 1, "")
            # col 130-134: 度量
            ws.cell(ri, 12 + 2 * n_buckets + 2, float(nr[asf_offset + 2]) if nr[asf_offset + 2] is not None else 0)
            ws.cell(ri, 12 + 2 * n_buckets + 3, float(nr[asf_offset + 3]) if nr[asf_offset + 3] is not None else 0)
            ws.cell(ri, 12 + 2 * n_buckets + 4, float(nr[asf_offset + 4]) if nr[asf_offset + 4] is not None else 0)
            ws.cell(ri, 12 + 2 * n_buckets + 5, float(nr[asf_offset + 5]) if nr[asf_offset + 5] is not None else 0)
            ws.cell(ri, 12 + 2 * n_buckets + 6, float(nr[asf_offset + 6]) if nr[asf_offset + 6] is not None else 0)
            ws.cell(ri, 12 + 2 * n_buckets + 7, nr[asf_offset + 7] or "")

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