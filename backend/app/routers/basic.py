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
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.database import get_db
from app.auth import get_current_user
from app.services.buckets import BUCKETS, KEYS, NAMES, ORIG_COLS, REM_COLS, all_select_sql

router = APIRouter(prefix="/basic", tags=["基础数据表"])

# 数值字段（原值/剩余值 + 余额/利率）
ORIG_FIELDS = ORIG_COLS
REM_FIELDS = REM_COLS
ALL_NUM_FIELDS = ORIG_FIELDS + REM_FIELDS + [
    "current_balance", "avg_balance", "weighted_rate",
    "interest_amount", "risk_weight",
]
N_BUCKETS = len(BUCKETS)  # 58


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
    # 58+58 期限桶（短端5 + 中端按月48 + 长端5，含 y1）
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
    """将 SQL 行转 dict（含 orig[17]/rem[17] 数组）"""
    # 公共字段共 11 列：id, data_date, coa_node_id, node_code, node_name, node_level,
    # parent_code, is_leaf, category, date_offset, offset_unit
    # col 11 起为 orig_*, col 28 起为 rem_*, col 45 起为度量
    n_b = len(ORIG_FIELDS)  # 17（v2 后）
    base = 11
    orig = [float(r[base + i] or 0) for i in range(n_b)]
    rem = [float(r[base + n_b + i] or 0) for i in range(n_b)]
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
        "asf_rsf": r[base + 2 * n_b],
        "hqla_factor": float(r[base + 2 * n_b + 1] or 0) if r[base + 2 * n_b + 1] is not None else None,
        "current_balance": float(r[base + 2 * n_b + 2] or 0),
        "avg_balance": float(r[base + 2 * n_b + 3] or 0),
        "weighted_rate": float(r[base + 2 * n_b + 4] or 0),
        "interest_amount": float(r[base + 2 * n_b + 5] or 0),
        "risk_weight": float(r[base + 2 * n_b + 6] or 0),
        "calc_note": r[base + 2 * n_b + 7],
        "created_at": r[base + 2 * n_b + 8].isoformat() if r[base + 2 * n_b + 8] else None,
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
                  + all_select_sql(prefix="b.") + ", " \
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
                ORDER BY path, sort_order"""),
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

    # 拉基础数据（**JOIN 过滤 scheme_id**，避免取到其他方案的 coa_node_id）
    rows = db.execute(
        text("""SELECT b.coa_node_id,
                      """ + all_select_sql("b.") + """,
                      b.asf_rsf, b.hqla_factor,
                      b.current_balance, b.avg_balance, b.weighted_rate, b.interest_amount, b.risk_weight
               FROM prcp_data_basic b
               JOIN prcp_coa_node n ON n.id = b.coa_node_id
               WHERE n.scheme_id=:s AND b.data_date=:d AND b.date_offset=:off AND b.offset_unit=:u AND b.is_deleted=0"""),
        {"s": scheme_id, "d": data_date, "off": date_offset, "u": offset_unit},
    ).fetchall()

    # SELECT 顺序：1=coa_node_id, 2-18=orig(17), 19-35=rem(17), 36+=asf_rsf, hqla, 度量
    matrix: dict = {}
    n_buckets = len(ORIG_FIELDS)  # 17（v2 后）
    for r in rows:
        cid = r[0]
        m = matrix.setdefault(cid, {})
        for i, k in enumerate(ORIG_FIELDS):
            m[k] = float(r[i + 1] or 0)
        for i, k in enumerate(REM_FIELDS):
            m[k] = float(r[i + 1 + n_buckets] or 0)
        m["asf_rsf"] = r[1 + 2 * n_buckets] or ""
        m["hqla_factor"] = float(r[2 + 2 * n_buckets]) if r[2 + 2 * n_buckets] is not None else None
        m["current_balance"] = float(r[3 + 2 * n_buckets] or 0)
        m["avg_balance"] = float(r[4 + 2 * n_buckets] or 0)
        m["weighted_rate"] = float(r[5 + 2 * n_buckets] or 0)
        m["interest_amount"] = float(r[6 + 2 * n_buckets] or 0)
        m["risk_weight"] = float(r[7 + 2 * n_buckets] or 0)

    # 按大类汇总（只汇总数值字段，跳过 asf_rsf 等非数值字段）
    NUMERIC_KEYS = ORIG_FIELDS + REM_FIELDS + [
        "current_balance", "avg_balance", "weighted_rate", "interest_amount", "risk_weight",
    ]

    def classify_category(node: dict) -> str:
        """根据节点编码推断业务大类。
        - COA_V6 风格 path = /L1_资产/... → '资产'
        - ZXCOA_V1 风格 node_code = ZX_A001 → '资产' / ZX_L003 → '负债' / ZX_E005 → '权益'
        """
        code = node.get("node_code") or ""
        path = node.get("path") or ""
        # ZXCOA_V1 编码风格
        if code.startswith("ZX_A"):
            return "资产"
        if code.startswith("ZX_L"):
            return "负债"
        if code.startswith("ZX_E"):
            return "权益"
        # COA_V6 风格（从 path 第二段提取 L1_<name>）
        parts = path.split("/")
        if len(parts) >= 2 and parts[1].startswith("L1_"):
            return parts[1][3:]  # 去掉 "L1_"
        return "其他"

    categories: dict = {}
    node_by_id = {n["coa_node_id"]: n for n in nodes}
    # 大类汇总策略：COA_V6 L1 节点无数据 → 累加所有节点（实际只有 L3 有数据）
    # ZXCOA_V1 L1 节点有数据 → 只累加 L1 节点（避免子节点重复累加）
    l1_cids = {n["coa_node_id"] for n in nodes if n.get("node_level") == 1}
    l1_has_data = any(
        matrix.get(cid, {}).get("current_balance", 0)
        for cid in l1_cids
    )
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
        text("""SELECT id, node_code, node_name, node_level, path, sort_order
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0
                ORDER BY path, sort_order"""),
        {"s": scheme_id},
    ).fetchall()

    rows = db.execute(
        text("""SELECT coa_node_id, node_code, node_name, node_level, parent_code, category, is_leaf,
                      """ + all_select_sql() + """,
                      asf_rsf, hqla_factor, current_balance, avg_balance,
                      weighted_rate, interest_amount, risk_weight, calc_note
               FROM prcp_data_basic
               WHERE data_date=:d AND date_offset=:off AND offset_unit=:u AND is_deleted=0"""),
        {"d": data_date, "off": date_offset, "u": offset_unit},
    ).fetchall()
    row_map = {r[0]: r for r in rows}

    wb = Workbook()
    ws = wb.active
    ws.title = "基础数据"

    # === 按 docs/基础数据导出模版.xlsx 格式输出 ===
    # row 1: 标题（col 3 = "账户册总表..."）
    # row 2: 二级表头分组（col 11 = "原始期限(金额)", col 24 = "剩余期限（金额）"）
    # row 3: 详细列名（col 1 = "ID（数据日期-账户册编码）", col 3 = "账户册编码"）
    # row 4+: 数据行

    # row 1: 标题
    ws.cell(1, 3, "账户册总表（资产 / 负债 / 表外 · 按业务层级）——余额：亿元；利率、资本占用比例、风险权重：%；平均利息收支：亿元/月")

    # row 2: 二级表头分组（保留与模板一致）
    ws.cell(2, 11, "原始期限(金额)")
    ws.cell(2, 24, "剩余期限（金额）")

    # row 3: 详细列名（动态生成 58 + 58 + 7 = 123 列）
    n_buckets = len(BUCKETS)
    detail_headers = [
        "ID（数据日期-账户册编码）",                                    # col 1
        "数据日期",                                                     # col 2
        "账户册编码",                                                   # col 3
        "账户册名称",                                                   # col 4
        "账户册层级",                                                   # col 5
        "父级账户册编码",                                               # col 6
        "是否末级节点（0：否，1：是）",                                 # col 7
        "大类（A：资产，L：负债）",                                     # col 8
        "日期偏移量（正整数）",                                         # col 9
        "日期偏移量单位（D：日，W：周，M：月,Y:年）",                   # col 10
    ]
    # col 11-68: 原始期限（58 列）
    for b in BUCKETS:
        detail_headers.append(f"orig_{b['name']}")
    # col 69-126: 剩余期限（58 列）
    for b in BUCKETS:
        detail_headers.append(f"rem_{b['name']}")
    # col 127-133: 度量
    detail_headers += [
        "ASF/RSF（可以放空）",                                         # col 127
        "HQLA折算系数（可以放空）",                                     # col 128
        "当前余额",                                                     # col 129
        "平均余额（月）",                                               # col 130
        "加权平均利率",                                                 # col 131
        "平均利息收支",                                                 # col 132
        "风险权重",                                                     # col 133
    ]
    n_cols = len(detail_headers)  # 133
    for col, h in enumerate(detail_headers, start=1):
        ws.cell(3, col, h)

    # row 4+: 数据行（每个账户册节点一行）
    # === 层级样式 ===
    FILL_L1 = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")  # 浅蓝
    FILL_L2 = PatternFill(start_color="EAF1F8", end_color="EAF1F8", fill_type="solid")  # 更浅蓝
    FILL_SEP = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")  # 浅灰（大类分隔）
    FONT_L1 = Font(bold=True, size=11, color="1F4E78")  # 深蓝加粗
    FONT_L2 = Font(bold=True, size=10)
    FONT_NORMAL = Font(size=10)
    ALIGN_LEFT = Alignment(horizontal="left", vertical="center", indent=0)

    prev_l1_code = None  # 跟踪上一个 L1 编码，用于插入大类分隔空行
    ri = 4

    for n in nodes:
        node_id = n[0]
        node_code = n[1]
        node_name = n[2]
        node_level = n[3] or 1

        # === 大类切换时插入空行作为分隔 ===
        if node_level == 1 and prev_l1_code is not None and node_code != prev_l1_code:
            for col in range(1, n_cols + 1):
                cell = ws.cell(ri, col, "")
                cell.fill = FILL_SEP
            ri += 1
        if node_level == 1:
            prev_l1_code = node_code

        r = row_map.get(node_id)

        # ID = data_date-node_code
        ws.cell(ri, 1, f"{data_date}-{node_code}")
        ws.cell(ri, 2, data_date)
        ws.cell(ri, 3, node_code)

        # === 节点名称：按 level 加全角空格缩进，1 级不加，2 级 2 个，3 级 4 个 ... ===
        indent = "　" * max(node_level - 1, 0)
        name_cell = ws.cell(ri, 4, f"{indent}{node_name}")
        # L1 加粗 + 浅蓝底色，L2 加粗，L3+ 普通
        if node_level == 1:
            name_cell.font = FONT_L1
            name_cell.fill = FILL_L1
        elif node_level == 2:
            name_cell.font = FONT_L2
            name_cell.fill = FILL_L2
        else:
            name_cell.font = FONT_NORMAL
        name_cell.alignment = ALIGN_LEFT

        lv_cell = ws.cell(ri, 5, node_level)
        if node_level == 1:
            lv_cell.font = FONT_L1
            lv_cell.fill = FILL_L1
        elif node_level == 2:
            lv_cell.font = FONT_L2
            lv_cell.fill = FILL_L2
        lv_cell.alignment = Alignment(horizontal="center", vertical="center")

        if r:
            ws.cell(ri, 6, r[4] or "")           # parent_code
            ws.cell(ri, 7, r[6] if r[6] is not None else 0)   # is_leaf (0/1)
            ws.cell(ri, 8, r[5] or "")           # category (A/L)
        else:
            ws.cell(ri, 6, "")
            ws.cell(ri, 7, 0)
            ws.cell(ri, 8, "")

        ws.cell(ri, 9, date_offset)              # 日期偏移量
        ws.cell(ri, 10, offset_unit)             # 偏移单位

        # col 11-(10+17): 原始期限（17 列，r[7]..r[23]）
    if r:
        for i in range(n_buckets):
            ws.cell(ri, 11 + i, float(r[7 + i] or 0))
        # col 69-126: 剩余期限（58 列，r[65]..r[122]）
        if r:
            for i in range(n_buckets):
                ws.cell(ri, 11 + n_buckets + i, float(r[7 + n_buckets + i] or 0))

        # col (10+17+1): ASF/RSF
        ws.cell(ri, 11 + 2 * n_buckets, r[7 + 2 * n_buckets] if r and r[7 + 2 * n_buckets] is not None else "")
        # col (10+17+2): HQLA折算系数
        offset_hqla = 7 + 2 * n_buckets + 1
        if r and r[offset_hqla] is not None:
            ws.cell(ri, 11 + 2 * n_buckets + 1, float(r[offset_hqla]))
        else:
            ws.cell(ri, 11 + 2 * n_buckets + 1, "")
        # col (10+17+3): 当前余额
        offset_cb = 7 + 2 * n_buckets + 2
        ws.cell(ri, 11 + 2 * n_buckets + 2, float(r[offset_cb]) if r and r[offset_cb] is not None else 0)
        # col 130: 平均余额（月） (r[126])
        offset_ab = 7 + 2 * n_buckets + 3
        ws.cell(ri, 11 + 2 * n_buckets + 3, float(r[offset_ab]) if r and r[offset_ab] is not None else 0)
        # col 131: 加权平均利率 (r[127])
        offset_wr = 7 + 2 * n_buckets + 4
        ws.cell(ri, 11 + 2 * n_buckets + 4, float(r[offset_wr]) if r and r[offset_wr] is not None else 0)
        # col 132: 平均利息收支 (r[128])
        offset_ia = 7 + 2 * n_buckets + 5
        ws.cell(ri, 11 + 2 * n_buckets + 5, float(r[offset_ia]) if r and r[offset_ia] is not None else 0)
        # col 133: 风险权重 (r[129])
        offset_rw = 7 + 2 * n_buckets + 6
        ws.cell(ri, 11 + 2 * n_buckets + 6, float(r[offset_rw]) if r and r[offset_rw] is not None else 0)

        # === 给 L1/L2 行的其他数据单元格也加底色，保持视觉一致 ===
        if node_level == 1:
            for col in range(1, n_cols + 1):
                if not ws.cell(ri, col).fill or ws.cell(ri, col).fill.start_color.rgb in (None, "00000000"):
                    ws.cell(ri, col).fill = FILL_L1
        elif node_level == 2:
            for col in range(1, n_cols + 1):
                if not ws.cell(ri, col).fill or ws.cell(ri, col).fill.start_color.rgb in (None, "00000000"):
                    ws.cell(ri, col).fill = FILL_L2

        ri += 1

    # === 列宽自适应（让节点名称列更宽） ===
    from openpyxl.utils import get_column_letter
    ws.column_dimensions["A"].width = 24  # ID
    ws.column_dimensions["B"].width = 12  # 数据日期
    ws.column_dimensions["C"].width = 12  # 账户册编码
    ws.column_dimensions["D"].width = 38  # 账户册名称（缩进后）
    ws.column_dimensions["E"].width = 8   # 层级
    ws.column_dimensions["F"].width = 12  # 父级编码
    ws.column_dimensions["G"].width = 12  # 是否末级
    ws.column_dimensions["H"].width = 8   # 大类
    ws.column_dimensions["I"].width = 10  # 日期偏移量
    ws.column_dimensions["J"].width = 10  # 偏移单位
    # 58 列原始期限 + 58 列剩余期限 = 116 列
    for i in range(n_buckets):
        ws.column_dimensions[get_column_letter(11 + i)].width = 7
    for i in range(n_buckets):
        ws.column_dimensions[get_column_letter(11 + n_buckets + i)].width = 7
    # 度量列
    for i in range(7):
        ws.column_dimensions[get_column_letter(11 + 2 * n_buckets + i)].width = 10

    # === 冻结首行 + 节点名称列 ===
    ws.freeze_panes = "E4"

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
    """导入 Excel：按 docs/基础数据导出模版.xlsx 格式解析

    模板结构（43 列）：
    - col 1: ID（数据日期-账户册编码）  → 冗余字段，可不读
    - col 2: 数据日期  → 缺省时用 query 参数 data_date
    - col 3: 账户册编码  → 必填
    - col 4: 账户册名称  → 冗余字段，按 coa_node 补
    - col 5: 账户册层级  → 冗余字段
    - col 6: 父级账户册编码  → 冗余字段
    - col 7: 是否末级节点  → 0/1
    - col 8: 大类  → A/L
    - col 9: 日期偏移量  → 缺省时用 query 参数 date_offset
    - col 10: 日期偏移量单位  → 缺省时用 query 参数 offset_unit
    - col 11-23: 原始期限金额（1日/7日/1M/3M/6M/1Y/2Y/3Y/5Y/10Y/15Y/20Y/30Y）
    - col 24-36: 剩余期限金额（13 列，同上）
    - col 37: ASF/RSF
    - col 38: HQLA折算系数
    - col 39-43: 当前余额/平均余额/月/加权平均利率/平均利息收支/风险权重

    表头行定位：找包含 "账户册编码" 的行（默认 row 3）
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

    # 找原始期限列起点（第一个 "1M"）和剩余期限列起点（第二个 "1M"）
    orig_col_start = None
    rem_col_start = None
    for cidx in range(1, 50):
        v = ws.cell(header_row, cidx).value
        if v and "1M" in str(v):
            if orig_col_start is None:
                orig_col_start = cidx
            elif rem_col_start is None:
                rem_col_start = cidx
                break

    if not orig_col_start or not rem_col_start:
        raise HTTPException(400, "Excel 中找不到原始/剩余期限桶（缺少 '1M' 列）")

    # 列转 0-indexed 用于 list 索引
    # col 3 = 账户册编码 → row[2]
    # col 11-27 = 原始期限 → row[10..26]（17 列）
    # col 28-44 = 剩余期限 → row[27..43]（17 列）
    # col 45 = ASF/RSF → row[44]
    # col 46 = HQLA → row[45]
    # col 47-51 = 度量 → row[46..50]
    COL_NODE_CODE = 2           # row[2] = 账户册编码
    COL_DATA_DATE = 1           # row[1] = 数据日期
    COL_OFFSET = 8              # row[8] = 日期偏移量
    COL_OFFSET_UNIT = 9         # row[9] = 日期偏移量单位
    COL_ORIG_START = 10         # row[10] = 原始期限第一个（1M）
    N_BUCKETS_IMPORT = len(ORIG_FIELDS)  # 64 = m1~m60 + y10/y15/y20/y30
    COL_REM_START = COL_ORIG_START + N_BUCKETS_IMPORT  # 74 = 剩余期限第一个（1M）
    COL_ASF_RSF = COL_REM_START + N_BUCKETS_IMPORT  # 138
    COL_HQLA = COL_ASF_RSF + 1   # 139
    COL_CURRENT_BAL = COL_HQLA + 1  # 140
    COL_AVG_BAL = COL_CURRENT_BAL + 1  # 141
    COL_WEIGHTED_RATE = COL_AVG_BAL + 1  # 142
    COL_INTEREST_AMOUNT = COL_WEIGHTED_RATE + 1  # 143
    COL_RISK_WEIGHT = COL_INTEREST_AMOUNT + 1  # 144

    inserted = updated = skipped = 0
    errors = []
    for ridx, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=1):
        if not row or len(row) < 3:
            continue
        # 跳过空行（全 None 或 全空）
        if not any(row[:3]):
            continue

        # node_code 在 col 3 (row[2])
        node_code_raw = row[COL_NODE_CODE] if len(row) > COL_NODE_CODE else None
        if not node_code_raw:
            continue
        node_code = str(node_code_raw).strip()
        if not node_code:
            continue

        coa_node_id = code_map.get(node_code)
        if not coa_node_id:
            skipped += 1
            errors.append(f"行 {header_row + ridx}: 账户册编码 {node_code} 不存在")
            continue

        # 数据日期：Excel col 2 > query 参数
        row_date = row[COL_DATA_DATE] if len(row) > COL_DATA_DATE else None
        if row_date:
            if hasattr(row_date, 'strftime'):
                eff_data_date = row_date.strftime("%Y-%m-%d")
            else:
                eff_data_date = str(row_date).strip()
        elif data_date:
            eff_data_date = data_date
        else:
            skipped += 1
            errors.append(f"行 {header_row + ridx}: 缺少数据日期")
            continue

        # 日期偏移量：Excel col 9 > query 参数
        row_offset = row[COL_OFFSET] if len(row) > COL_OFFSET else None
        eff_offset = int(row_offset) if row_offset is not None and str(row_offset).strip() != "" else date_offset

        # 偏移单位
        row_unit = row[COL_OFFSET_UNIT] if len(row) > COL_OFFSET_UNIT else None
        eff_unit = str(row_unit).strip() if row_unit else offset_unit

        # 原始期限 58 列（row[10..67]）
        orig = []
        for i in range(N_BUCKETS_IMPORT):
            v = row[COL_ORIG_START + i] if len(row) > COL_ORIG_START + i else None
            orig.append(float(v) if v not in (None, "") else 0)

        # 剩余期限 58 列（row[68..125]）
        rem = []
        for i in range(N_BUCKETS_IMPORT):
            v = row[COL_REM_START + i] if len(row) > COL_REM_START + i else None
            rem.append(float(v) if v not in (None, "") else 0)

        # ASF/RSF
        asf_rsf_raw = row[COL_ASF_RSF] if len(row) > COL_ASF_RSF else None
        asf_rsf = str(asf_rsf_raw).strip() if asf_rsf_raw not in (None, "") else None
        # HQLA
        hqla_raw = row[COL_HQLA] if len(row) > COL_HQLA else None
        hqla_factor = float(hqla_raw) if hqla_raw not in (None, "") else None
        # 度量
        def _f(idx):
            v = row[idx] if len(row) > idx else None
            return float(v) if v not in (None, "") else 0
        current_balance = _f(COL_CURRENT_BAL)
        avg_balance = _f(COL_AVG_BAL)
        weighted_rate = _f(COL_WEIGHTED_RATE)
        interest_amount = _f(COL_INTEREST_AMOUNT)
        risk_weight = _f(COL_RISK_WEIGHT)

        # 自动补维度
        nr = db.execute(
            text("""SELECT n.node_code, n.node_name, n.node_level,
                          (SELECT node_code FROM prcp_coa_node WHERE id=n.parent_id) AS parent_code
                   FROM prcp_coa_node n WHERE n.id=:id"""),
            {"id": coa_node_id},
        ).first()

        params = {
            "coa_node_id": coa_node_id,
            "data_date": eff_data_date,
            "date_offset": eff_offset,
            "offset_unit": eff_unit,
            "node_code": nr[0] if nr else node_code,
            "node_name": nr[1] if nr else "",
            "node_level": nr[2] if nr else 0,
            "parent_code": nr[3] if nr else "",
            "is_leaf": 0,
            "category": "",
            "asf_rsf": asf_rsf,
            "hqla_factor": hqla_factor,
            "current_balance": current_balance,
            "avg_balance": avg_balance,
            "weighted_rate": weighted_rate,
            "interest_amount": interest_amount,
            "risk_weight": risk_weight,
            "created_by": uid,
            "updated_by": uid,
        }
        for i, k in enumerate(ORIG_FIELDS):
            params[k] = orig[i]
        for i, k in enumerate(REM_FIELDS):
            params[k] = rem[i]

        existing = db.execute(
            text("SELECT id FROM prcp_data_basic WHERE coa_node_id=:coa_node_id AND data_date=:data_date "
                 "AND date_offset=:date_offset AND offset_unit=:offset_unit AND is_deleted=0"),
            {"coa_node_id": coa_node_id, "data_date": eff_data_date,
             "date_offset": eff_offset, "offset_unit": eff_unit},
        ).first()

        if existing:
            set_clause = ", ".join(f"{k}=:{k}" for k in ORIG_FIELDS + REM_FIELDS + [
                "asf_rsf", "hqla_factor", "current_balance", "avg_balance",
                "weighted_rate", "interest_amount", "risk_weight",
            ])
            params["id"] = existing[0]
            db.execute(
                text(f"UPDATE prcp_data_basic SET {set_clause}, updated_by=:updated_by WHERE id=:id"),
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