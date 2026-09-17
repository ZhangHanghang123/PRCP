"""基础数据表 API — 按账户册 + 数据日期 + 日期偏移量的二维矩阵
字段定义参考 docs/基础数据表.xlsx
"""
import io
from typing import Optional, List
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openpyxl import Workbook, load_workbook

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/basic", tags=["基础数据表"])

# 13 个期限桶（统一两端：原始 + 剩余）
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

# 数值字段（原值/剩余值 + 余额/利率）
ORIG_FIELDS = [f"orig_{b['key']}" for b in BUCKETS]
REM_FIELDS = [f"rem_{b['key']}" for b in BUCKETS]
ALL_NUM_FIELDS = ORIG_FIELDS + REM_FIELDS + [
    "current_balance", "avg_balance", "weighted_rate",
    "interest_amount", "risk_weight",
]


class BasicIn(BaseModel):
    coa_node_id: int
    data_date: str  # YYYY-MM-DD
    date_offset: int = 0
    offset_unit: str = "D"
    # 维度（冗余，便于查询）
    node_code: Optional[str] = None
    node_name: Optional[str] = None
    node_level: Optional[int] = None
    parent_code: Optional[str] = None
    is_leaf: Optional[int] = 0
    category: Optional[str] = None
    # 13+13 期限桶
    orig: Optional[List[float]] = None
    rem: Optional[List[float]] = None
    # 流动性指标
    asf_rsf: Optional[str] = None
    hqla_factor: Optional[float] = None
    # 余额/利率
    current_balance: float = 0
    avg_balance: float = 0
    weighted_rate: float = 0
    interest_amount: float = 0
    risk_weight: float = 0
    calc_note: Optional[str] = None


def _row_to_dict(r) -> dict:
    """将 SQL 行转 dict（含 orig[13]/rem[13] 数组）"""
    orig = [float(r[i] or 0) for i in range(15, 28)]  # orig_d1..orig_y30
    rem = [float(r[i] or 0) for i in range(28, 41)]   # rem_d1..rem_y30
    return {
        "id": r[0],
        "data_date": r[1].isoformat() if r[1] else None,
        "coa_node_id": r[2],
        "node_code": r[3],
        "node_name": r[4],
        "node_level": r[5],
        "parent_code": r[6],
        "is_leaf": r[7],
        "category": r[8],
        "date_offset": r[9],
        "offset_unit": r[10],
        "orig": orig,
        "rem": rem,
        "asf_rsf": r[41],
        "hqla_factor": float(r[42] or 0) if r[42] is not None else None,
        "current_balance": float(r[43] or 0),
        "avg_balance": float(r[44] or 0),
        "weighted_rate": float(r[45] or 0),
        "interest_amount": float(r[46] or 0),
        "risk_weight": float(r[47] or 0),
        "calc_note": r[48],
        "created_at": r[49].isoformat() if r[49] else None,
    }


@router.get("/")
async def list_basic(
    coa_node_id: Optional[int] = None,
    data_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列表查询（按筛选条件）"""
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
    if category:
        where.append("b.category=:c")
        params["c"] = category

    select_cols = "b.id, b.data_date, b.coa_node_id, b.node_code, b.node_name, b.node_level, " \
                  "b.parent_code, b.is_leaf, b.category, b.date_offset, b.offset_unit, " \
                  "b.orig_d1, b.orig_d7, b.orig_m1, b.orig_m3, b.orig_m6, b.orig_y1, b.orig_y2, b.orig_y3, " \
                  "b.orig_y5, b.orig_y10, b.orig_y15, b.orig_y20, b.orig_y30, " \
                  "b.rem_d1, b.rem_d7, b.rem_m1, b.rem_m3, b.rem_m6, b.rem_y1, b.rem_y2, b.rem_y3, " \
                  "b.rem_y5, b.rem_y10, b.rem_y15, b.rem_y20, b.rem_y30, " \
                  "b.asf_rsf, b.hqla_factor, b.current_balance, b.avg_balance, " \
                  "b.weighted_rate, b.interest_amount, b.risk_weight, b.calc_note, b.created_at"

    rows = db.execute(
        text(f"SELECT {select_cols} FROM prcp_data_basic b WHERE {' AND '.join(where)} "
             "ORDER BY b.data_date DESC, b.coa_node_id, b.date_offset LIMIT 5000"),
        params,
    ).fetchall()
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post("/")
async def upsert_basic(p: BasicIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """按 (coa_node_id, data_date, date_offset, offset_unit) 唯一"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)

    # 自动补全维度字段（从 coa_node JOIN）
    if not p.node_code or not p.node_name:
        nr = db.execute(
            text("""SELECT n.node_code, n.node_name, n.node_level, n.parent_id,
                          (SELECT node_code FROM prcp_coa_node WHERE id=n.parent_id) AS parent_code
                   FROM prcp_coa_node n WHERE n.id=:id AND n.is_deleted=0"""),
            {"id": p.coa_node_id},
        ).first()
        if nr:
            p.node_code = p.node_code or nr[0]
            p.node_name = p.node_name or nr[1]
            p.node_level = p.node_level or nr[2]
            p.parent_code = p.parent_code or nr[3]
        else:
            raise HTTPException(404, f"账户册节点不存在：{p.coa_node_id}")

    orig = (p.orig or [0] * 13)
    rem = (p.rem or [0] * 13)
    while len(orig) < 13:
        orig.append(0)
    while len(rem) < 13:
        rem.append(0)

    params = {
        "n": p.coa_node_id,
        "d": p.data_date,
        "off": p.date_offset,
        "unit": p.offset_unit,
        "node_code": p.node_code,
        "node_name": p.node_name,
        "node_level": p.node_level,
        "parent_code": p.parent_code,
        "is_leaf": p.is_leaf,
        "category": p.category,
        "asf_rsf": p.asf_rsf,
        "hqla_factor": p.hqla_factor,
        "current_balance": p.current_balance,
        "avg_balance": p.avg_balance,
        "weighted_rate": p.weighted_rate,
        "interest_amount": p.interest_amount,
        "risk_weight": p.risk_weight,
        "calc_note": p.calc_note,
        "u": uid,
    }
    for i, k in enumerate(ORIG_FIELDS):
        params[k] = orig[i]
    for i, k in enumerate(REM_FIELDS):
        params[k] = rem[i]

    existing = db.execute(
        text("SELECT id FROM prcp_data_basic WHERE coa_node_id=:n AND data_date=:d "
             "AND date_offset=:off AND offset_unit=:unit AND is_deleted=0"),
        {"n": p.coa_node_id, "d": p.data_date, "off": p.date_offset, "unit": p.offset_unit},
    ).first()

    if existing:
        set_clause = ", ".join(f"{k}=:{k}" for k in ORIG_FIELDS + REM_FIELDS + [
            "asf_rsf", "hqla_factor", "current_balance", "avg_balance",
            "weighted_rate", "interest_amount", "risk_weight", "calc_note",
        ])
        params["id"] = existing[0]
        db.execute(
            text(f"""UPDATE prcp_data_basic SET {set_clause},
                node_code=:node_code, node_name=:node_name, node_level=:node_level,
                parent_code=:parent_code, is_leaf=:is_leaf, category=:category,
                updated_by=:u WHERE id=:id"""),
            params,
        )
        return {"id": existing[0], "action": "updated"}
    else:
        cols = ["coa_node_id", "data_date", "date_offset", "offset_unit",
                "node_code", "node_name", "node_level", "parent_code", "is_leaf", "category",
                "asf_rsf", "hqla_factor", "current_balance", "avg_balance",
                "weighted_rate", "interest_amount", "risk_weight", "calc_note",
                "created_by", "updated_by"] + ORIG_FIELDS + REM_FIELDS
        col_list = ", ".join(cols)
        val_list = ", ".join(f":{c}" for c in cols)
        rid = db.execute(
            text(f"INSERT INTO prcp_data_basic ({col_list}) VALUES ({val_list})"),
            params,
        ).lastrowid
        return {"id": rid, "action": "created"}


@router.delete("/{bid}")
async def delete_basic(bid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("UPDATE prcp_data_basic SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": bid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "记录不存在或已删除")
    return {"id": bid, "action": "deleted"}


@router.get("/dates")
async def list_dates(
    scheme_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回已录入的数据日期列表"""
    where = ["b.is_deleted=0"]
    params = {}
    if scheme_id:
        where.append("n.scheme_id=:s")
        params["s"] = scheme_id
    rows = db.execute(
        text(f"SELECT DISTINCT b.data_date FROM prcp_data_basic b "
             f"JOIN prcp_coa_node n ON n.id=b.coa_node_id "
             f"WHERE {' AND '.join(where)} ORDER BY b.data_date DESC LIMIT 100"),
        params,
    ).fetchall()
    return {"items": [r[0].isoformat() for r in rows if r[0]]}


@router.get("/by-scheme-matrix")
async def by_scheme_matrix(
    scheme_id: int = Query(...),
    data_date: str = Query(..., description="YYYY-MM-DD 目标数据日期"),
    date_offset: int = Query(0, description="日期偏移量，0=当期"),
    offset_unit: str = Query("D", description="D=日,W=周,Y=年"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """二维矩阵：行 = 账户册 × 列 = (原始期限 + 剩余期限) 共 26 列

    返回结构：
    - nodes: 账户册树节点
    - matrix: {coa_node_id: {col_key: value}}
    - categories: 按大类汇总
    """
    node_rows = db.execute(
        text("""SELECT id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, description
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0
                ORDER BY sort_order, path"""),
        {"s": scheme_id},
    ).fetchall()
    nodes = []
    for r in node_rows:
        path = r[6] or ""
        cat = ""
        if "/" in path:
            cat = path.split("/")[1].replace("L1_", "")
        nodes.append({
            "coa_node_id": r[0], "node_code": r[1], "node_name": r[2],
            "parent_id": r[3], "node_level": r[4], "node_type": r[5], "path": r[6],
            "sort_order": r[7] or 0, "category": cat, "description": r[8] or "",
        })

    # 拉基础数据
    rows = db.execute(
        text("""SELECT coa_node_id, orig_d1, orig_d7, orig_m1, orig_m3, orig_m6,
                      orig_y1, orig_y2, orig_y3, orig_y5, orig_y10, orig_y15, orig_y20, orig_y30,
                      rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
                      rem_y1, rem_y2, rem_y3, rem_y5, rem_y10, rem_y15, rem_y20, rem_y30,
                      current_balance, avg_balance, weighted_rate, interest_amount, risk_weight
               FROM prcp_data_basic
               WHERE data_date=:d AND date_offset=:off AND offset_unit=:u AND is_deleted=0"""),
        {"d": data_date, "off": date_offset, "u": offset_unit},
    ).fetchall()

    matrix: dict = {}
    for r in rows:
        cid = r[0]
        m = matrix.setdefault(cid, {})
        for i, k in enumerate(ORIG_FIELDS):
            m[f"orig_{k}"] = float(r[i + 1] or 0)
        for i, k in enumerate(REM_FIELDS):
            m[f"rem_{k}"] = float(r[i + 14] or 0)
        m["current_balance"] = float(r[27] or 0)
        m["avg_balance"] = float(r[28] or 0)
        m["weighted_rate"] = float(r[29] or 0)
        m["interest_amount"] = float(r[30] or 0)
        m["risk_weight"] = float(r[31] or 0)

    # 按大类汇总
    categories: dict = {}
    node_by_id = {n["coa_node_id"]: n for n in nodes}
    for cid, m in matrix.items():
        n = node_by_id.get(cid)
        if not n or not n["path"]:
            continue
        cat = n["path"].split("/")[1].replace("L1_", "") if "/" in n["path"] else "其他"
        bucket = categories.setdefault(cat, {k: 0.0 for k in m.keys()})
        for k, v in m.items():
            bucket[k] += v
    for cat in categories:
        for k in categories[cat]:
            categories[cat][k] = round(categories[cat][k], 4)

    return {
        "scheme_id": scheme_id,
        "data_date": data_date,
        "date_offset": date_offset,
        "offset_unit": offset_unit,
        "nodes": nodes,
        "matrix": matrix,
        "categories": categories,
    }


@router.get("/export-xlsx")
async def export_xlsx(
    scheme_id: int = Query(...),
    data_date: str = Query(...),
    date_offset: int = Query(0),
    offset_unit: str = Query("D"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """导出 Excel：每账户册 × 13+13 期限桶的二维表"""
    nodes = db.execute(
        text("""SELECT id, node_code, node_name, node_level, category, path, sort_order
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0 ORDER BY sort_order, path"""),
        {"s": scheme_id},
    ).fetchall()

    rows = db.execute(
        text("""SELECT coa_node_id, node_code, node_name, node_level, parent_code, category, is_leaf,
                      orig_d1, orig_d7, orig_m1, orig_m3, orig_m6,
                      orig_y1, orig_y2, orig_y3, orig_y5, orig_y10, orig_y15, orig_y20, orig_y30,
                      rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
                      rem_y1, rem_y2, rem_y3, rem_y5, rem_y10, rem_y15, rem_y20, rem_y30,
                      asf_rsf, hqla_factor, current_balance, avg_balance,
                      weighted_rate, interest_amount, risk_weight, calc_note
               FROM prcp_data_basic
               WHERE data_date=:d AND date_offset=:off AND offset_unit=:u AND is_deleted=0"""),
        {"d": data_date, "off": date_offset, "u": offset_unit},
    ).fetchall()
    row_map = {r[0]: r for r in rows}

    wb = Workbook()
    ws = wb.active
    ws.title = "基础数据表"

    # 双层表头
    ws.cell(1, 1, "数据日期:")
    ws.cell(1, 2, data_date)
    ws.cell(2, 1, "日期偏移量:")
    ws.cell(2, 2, f"{date_offset}{offset_unit}")

    # 二级表头：基础字段 + 原始期限 + 剩余期限
    fixed_headers = ["账户册编码", "账户册名称", "账户册层级", "父级账户册编码",
                     "是否末级", "大类", "日期偏移量", "偏移单位"]
    bucket_names = [b["name"] for b in BUCKETS]
    extra_headers = ["ASF/RSF", "HQLA折算系数", "当前余额", "平均余额",
                     "加权平均利率", "平均利息收支", "风险权重"]

    # row 4 是二级表头分组
    group_row = 4
    detail_row = 5
    col = 1
    for h in fixed_headers:
        ws.cell(group_row, col, "")
        ws.cell(detail_row, col, h)
        col += 1
    ws.cell(group_row, col, "原始期限(金额)")
    for k in bucket_names:
        ws.cell(detail_row, col, k)
        col += 1
    ws.cell(group_row, col, "剩余期限(金额)")
    for k in bucket_names:
        ws.cell(detail_row, col, k)
        col += 1
    for h in extra_headers:
        ws.cell(group_row, col, "")
        ws.cell(detail_row, col, h)
        col += 1

    # 数据行
    for ri, n in enumerate(nodes, start=6):
        node_id = n[0]
        r = row_map.get(node_id)
        ws.cell(ri, 1, n[1])  # node_code
        ws.cell(ri, 2, n[2])  # node_name
        ws.cell(ri, 3, n[3])  # node_level
        if r:
            ws.cell(ri, 4, r[4])  # parent_code
            ws.cell(ri, 5, "是" if r[6] else "否")  # is_leaf
            ws.cell(ri, 6, r[5])  # category
        else:
            ws.cell(ri, 4, "")
            ws.cell(ri, 5, "")
            ws.cell(ri, 6, "")
        ws.cell(ri, 7, date_offset)
        ws.cell(ri, 8, offset_unit)

        c = 9
        if r:
            for i in range(13):
                ws.cell(ri, c + i, float(r[7 + i] or 0))
            c += 13
            for i in range(13):
                ws.cell(ri, c + i, float(r[20 + i] or 0))
            c += 13
            ws.cell(ri, c, r[32])  # asf_rsf
            ws.cell(ri, c + 1, float(r[33] or 0) if r[33] is not None else "")
            ws.cell(ri, c + 2, float(r[34] or 0))
            ws.cell(ri, c + 3, float(r[35] or 0))
            ws.cell(ri, c + 4, float(r[36] or 0))
            ws.cell(ri, c + 5, float(r[37] or 0))
            ws.cell(ri, c + 6, float(r[38] or 0))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"prcp_basic_{data_date}_{date_offset}{offset_unit}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fn}"},
    )


@router.post("/import-xlsx")
async def import_xlsx(
    file: UploadFile = File(...),
    scheme_id: int = Query(...),
    data_date: Optional[str] = Query(None, description="可选，Excel 无日期列时使用"),
    date_offset: int = Query(0),
    offset_unit: str = Query("D"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """导入 Excel：按 (coa_node_id, data_date, date_offset, offset_unit) upsert

    期望表结构：
    - 第 1 列：账户册编码（对应 prcp_coa_node.node_code）
    - 第 3 列（offset=8）：原始期限金额起点
    - 第 16 列（offset=21）：剩余期限金额起点
    """
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)

    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(400, f"无法解析 Excel：{e}")

    # 加载方案下所有账户册 node_code → id 映射
    code_rows = db.execute(
        text("SELECT id, node_code FROM prcp_coa_node WHERE scheme_id=:s AND is_deleted=0"),
        {"s": scheme_id},
    ).fetchall()
    code_map = {r[1]: r[0] for r in code_rows}

    # 找表头行：找包含 "账户册编码" 的行
    header_row = None
    for ridx, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
        if row and any(v and "账户册编码" in str(v) for v in row):
            header_row = ridx
            break
    if not header_row:
        raise HTTPException(400, "Excel 中找不到 '账户册编码' 表头行")

    # 找原始期限列起点（含 "1日"）
    orig_col_start = None
    rem_col_start = None
    for cidx, v in enumerate(ws[header_row], start=1):
        if v and "1日" in str(v):
            if orig_col_start is None:
                orig_col_start = cidx
            elif rem_col_start is None:
                rem_col_start = cidx
                break

    inserted = updated = skipped = 0
    errors = []
    for ridx, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=1):
        if not row or not row[0]:
            continue
        node_code = str(row[0]).strip()
        coa_node_id = code_map.get(node_code)
        if not coa_node_id:
            skipped += 1
            errors.append(f"行 {row-1}: 账户册编码 {node_code} 不存在")
            continue

        orig = [float(row[orig_col_start + i] or 0) for i in range(13)] if orig_col_start else [0] * 13
        rem = [float(row[rem_col_start + i] or 0) for i in range(13)] if rem_col_start else [0] * 13

        # 找到原始 + 剩余 + 余额字段的偏移列（按 extra_headers 顺序）
        # extra_headers = ["ASF/RSF", "HQLA折算系数", "当前余额", "平均余额",
        #                  "加权平均利率", "平均利息收支", "风险权重"]
        # 起始列 = rem_col_start + 13
        extra_col = (rem_col_start or 0) + 13
        asf_rsf = row[extra_col] if extra_col < len(row) else None
        hqla = row[extra_col + 1] if (extra_col + 1) < len(row) else None
        current_balance = row[extra_col + 2] if (extra_col + 2) < len(row) else 0
        avg_balance = row[extra_col + 3] if (extra_col + 3) < len(row) else 0
        weighted_rate = row[extra_col + 4] if (extra_col + 4) < len(row) else 0
        interest_amount = row[extra_col + 5] if (extra_col + 5) < len(row) else 0
        risk_weight = row[extra_col + 6] if (extra_col + 6) < len(row) else 0

        # 自动补维度
        nr = db.execute(
            text("""SELECT n.node_code, n.node_name, n.node_level,
                          (SELECT node_code FROM prcp_coa_node WHERE id=n.parent_id) AS parent_code
                   FROM prcp_coa_node n WHERE n.id=:id"""),
            {"id": coa_node_id},
        ).first()

        params = {
            "n": coa_node_id, "d": data_date, "off": date_offset, "u": offset_unit,
            "node_code": nr[0] if nr else node_code,
            "node_name": nr[1] if nr else "",
            "node_level": nr[2] if nr else 0,
            "parent_code": nr[3] if nr else "",
            "is_leaf": 0,
            "category": "",
            "asf_rsf": asf_rsf,
            "hqla_factor": float(hqla) if hqla not in (None, "") else None,
            "current_balance": float(current_balance or 0),
            "avg_balance": float(avg_balance or 0),
            "weighted_rate": float(weighted_rate or 0),
            "interest_amount": float(interest_amount or 0),
            "risk_weight": float(risk_weight or 0),
            "calc_note": None,
            "uid": uid,
        }
        for i, k in enumerate(ORIG_FIELDS):
            params[k] = orig[i]
        for i, k in enumerate(REM_FIELDS):
            params[k] = rem[i]

        existing = db.execute(
            text("SELECT id FROM prcp_data_basic WHERE coa_node_id=:n AND data_date=:d "
                 "AND date_offset=:off AND offset_unit=:u AND is_deleted=0"),
            {"n": coa_node_id, "d": data_date, "off": date_offset, "u": offset_unit},
        ).first()

        if existing:
            set_clause = ", ".join(f"{k}=:{k}" for k in ORIG_FIELDS + REM_FIELDS + [
                "asf_rsf", "hqla_factor", "current_balance", "avg_balance",
                "weighted_rate", "interest_amount", "risk_weight",
            ])
            params["id"] = existing[0]
            db.execute(
                text(f"UPDATE prcp_data_basic SET {set_clause}, updated_by=:uid WHERE id=:id"),
                params,
            )
            updated += 1
        else:
            cols = ["coa_node_id", "data_date", "date_offset", "offset_unit",
                    "node_code", "node_name", "node_level", "parent_code", "category",
                    "asf_rsf", "hqla_factor", "current_balance", "avg_balance",
                    "weighted_rate", "interest_amount", "risk_weight",
                    "created_by", "updated_by"] + ORIG_FIELDS + REM_FIELDS
            col_list = ", ".join(cols)
            val_list = ", ".join(f":{c}" for c in cols)
            db.execute(
                text(f"INSERT INTO prcp_data_basic ({col_list}) VALUES ({val_list})"),
                params,
            )
            inserted += 1

    db.commit()
    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "total_errors": len(errors),
        "errors": errors[:20],
    }