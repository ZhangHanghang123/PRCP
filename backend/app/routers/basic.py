"""basic.py v4 改造 — 3 表拆分
- prcp_data_basic 主表（无 128 期限字段）
- prcp_data_basic_orig 原始期限 64 桶
- prcp_data_basic_rem 剩余期限 64 桶
所有 API 通过 (coa_node_id, data_date, date_offset, offset_unit) 四元组 JOIN
"""
"""基础数据表 API — v4 拆分（3 表）
prcp_data_basic（主表）+ prcp_data_basic_orig（原始期限 64 桶）+ prcp_data_basic_rem（剩余期限 64 桶）
通过 (coa_node_id, data_date, date_offset, offset_unit) 四元组 JOIN
"""
import io
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

from app.database import get_db
from app.auth import get_current_user
from app.services.buckets import BUCKETS, KEYS, NAMES, ORIG_COLS, REM_COLS, all_select_sql

router = APIRouter(prefix="/basic", tags=["基础数据表"])

# v4: 期限桶字段在 *_orig / *_rem 子表中
ORIG_TABLE = "prcp_data_basic_orig"
REM_TABLE = "prcp_data_basic_rem"
MAIN_TABLE = "prcp_data_basic"
N_BUCKETS = len(BUCKETS)  # 64


class BasicIn(BaseModel):
    coa_node_id: int
    data_date: str
    date_offset: int = 0
    offset_unit: str = "D"
    # 维度
    node_code: Optional[str] = None
    node_name: Optional[str] = None
    node_level: Optional[int] = None
    parent_code: Optional[str] = None
    is_leaf: Optional[int] = 0
    category: Optional[str] = None
    # 64+64 期限桶
    orig: Optional[List[float]] = None
    rem: Optional[List[float]] = None
    # 流动性
    asf_rsf: Optional[str] = None
    hqla_factor: Optional[float] = None
    # 度量
    current_balance: float = 0
    avg_balance: float = 0
    weighted_rate: float = 0
    interest_amount: float = 0
    risk_weight: float = 0
    calc_note: Optional[str] = None


def _main_cols() -> str:
    """主表 SELECT 字段（11 维度 + 8 度量/流动性 + calc_note + created_at）"""
    return ("b.id, b.data_date, b.coa_node_id, b.node_code, b.node_name, b.node_level, "
            "b.parent_code, b.is_leaf, b.category, b.date_offset, b.offset_unit, "
            "b.asf_rsf, b.hqla_factor, b.current_balance, b.avg_balance, "
            "b.weighted_rate, b.interest_amount, b.risk_weight, b.calc_note, b.created_at")


def _row_to_dict(r, orig_dict: dict, rem_dict: dict) -> dict:
    """主表行 + orig/rem 子表 dict → 合并成 dict"""
    n_b = N_BUCKETS
    orig = [float(orig_dict.get(c, 0) or 0) for c in ORIG_COLS]
    rem = [float(rem_dict.get(c, 0) or 0) for c in REM_COLS]
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
        "asf_rsf": r[11],
        "hqla_factor": float(r[12] or 0) if r[12] is not None else None,
        "current_balance": float(r[13] or 0),
        "avg_balance": float(r[14] or 0),
        "weighted_rate": float(r[15] or 0),
        "interest_amount": float(r[16] or 0),
        "risk_weight": float(r[17] or 0),
        "calc_note": r[18],
        "created_at": r[19].isoformat() if r[19] else None,
        "orig": orig,
        "rem": rem,
    }


def _join_sql(extra_where: str = "", prefix: str = "b.") -> str:
    """返回 3 表 JOIN 的 SELECT SQL（主表字段 + orig/rem 全部字段）

    Args:
        extra_where: 额外的 WHERE 子句
        prefix: 主表别名
    """
    orig_select = ", ".join(f"o.{c} AS {c}" for c in ORIG_COLS)
    rem_select = ", ".join(f"r.{c} AS {c}" for c in REM_COLS)
    sql = (f"SELECT {_main_cols()}, {orig_select}, {rem_select} "
           f"FROM {MAIN_TABLE} {prefix} "
           f"LEFT JOIN {ORIG_TABLE} o ON o.coa_node_id={prefix}coa_node_id "
           f"  AND o.data_date={prefix}data_date "
           f"  AND o.date_offset={prefix}date_offset "
           f"  AND o.offset_unit={prefix}offset_unit "
           f"  AND o.is_deleted=0 "
           f"LEFT JOIN {REM_TABLE} r ON r.coa_node_id={prefix}coa_node_id "
           f"  AND r.data_date={prefix}data_date "
           f"  AND r.date_offset={prefix}date_offset "
           f"  AND r.offset_unit={prefix}offset_unit "
           f"  AND r.is_deleted=0 "
           f"WHERE {prefix}is_deleted=0 {extra_where}")
    return sql


def _fetch_all(db, where_extra: str, params: dict, order_by: str = "b.data_date DESC, b.coa_node_id, b.date_offset", limit: int = 5000):
    """统一查询（v3 单表，145 列：前 15 字段 + 128 桶）"""
    # 拼接 WHERE：固定 b.is_deleted=0 + 动态条件（已含 AND/无前缀）
    where_clause = f"WHERE b.is_deleted=0 {('AND ' + where_extra) if where_extra else ''}"
    sql = (
        f"SELECT b.id, b.data_date, b.coa_node_id, b.node_code, b.node_name, b.node_level, "
        f"b.parent_code, b.is_leaf, b.category, b.date_offset, b.offset_unit, "
        f"b.asf_rsf, b.hqla_factor, b.current_balance, b.avg_balance, "
        f"b.weighted_rate, b.interest_amount, b.risk_weight, b.calc_note, b.created_at, "
        f"{all_select_sql(prefix='')} "
        f"FROM {MAIN_TABLE} b "
        f"{where_clause} "
        f"ORDER BY {order_by} LIMIT {limit}"
    )
    rows = db.execute(text(sql), params).fetchall()
    return rows


def _rows_to_dicts(rows) -> list:
    """把 SQL 行转 dict（v3 单表：前 20 列=主表字段，中间 64=orig，最后 64=rem）"""
    n_b = N_BUCKETS
    items = []
    for r in rows:
        main = r[:20]
        orig_vals = r[20:20 + n_b]
        rem_vals = r[20 + n_b:20 + 2 * n_b]
        orig_dict = {ORIG_COLS[i]: orig_vals[i] for i in range(n_b)}
        rem_dict = {REM_COLS[i]: rem_vals[i] for i in range(n_b)}
        items.append(_row_to_dict(main, orig_dict, rem_dict))
    return items


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
    """列表查询（按筛选条件）— v4 三表 JOIN"""
    where_parts = []
    params = {}
    if coa_node_id:
        where_parts.append("b.coa_node_id=:n")
        params["n"] = coa_node_id
    if data_date:
        where_parts.append("b.data_date=:d")
        params["d"] = data_date
    if start_date:
        where_parts.append("b.data_date>=:sd")
        params["sd"] = start_date
    if end_date:
        where_parts.append("b.data_date<=:ed")
        params["ed"] = end_date
    if category:
        where_parts.append("b.category=:c")
        params["c"] = category
    extra_where = " AND ".join(where_parts)
    rows = _fetch_all(db, extra_where, params)
    items = _rows_to_dicts(rows)
    return {"items": items, "total": len(items)}


@router.post("/")
async def upsert_basic(p: BasicIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """按 (coa_node_id, data_date, date_offset, offset_unit) 唯一 — v3 单表 145 列"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)

    # 自动补全维度
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

    orig = list(p.orig or []) + [0] * (N_BUCKETS - len(p.orig or []))
    rem = list(p.rem or []) + [0] * (N_BUCKETS - len(p.rem or []))
    orig = orig[:N_BUCKETS]
    rem = rem[:N_BUCKETS]

    params = {
        "n": p.coa_node_id, "d": p.data_date, "off": p.date_offset, "unit": p.offset_unit,
        "node_code": p.node_code, "node_name": p.node_name, "node_level": p.node_level,
        "parent_code": p.parent_code, "is_leaf": p.is_leaf, "category": p.category,
        "asf_rsf": p.asf_rsf, "hqla_factor": p.hqla_factor,
        "current_balance": p.current_balance, "avg_balance": p.avg_balance,
        "weighted_rate": p.weighted_rate, "interest_amount": p.interest_amount,
        "risk_weight": p.risk_weight, "calc_note": p.calc_note, "u": uid,
    }
    # 桶字段（orig_m1...orig_y30 + rem_m1...rem_y30）
    for i, k in enumerate(ORIG_COLS):
        params[k] = orig[i]
    for i, k in enumerate(REM_COLS):
        params[k] = rem[i]

    # 查询是否存在
    existing = db.execute(
        text(f"SELECT id FROM {MAIN_TABLE} WHERE coa_node_id=:n AND data_date=:d "
             f"AND date_offset=:off AND offset_unit=:unit AND is_deleted=0"),
        {"n": p.coa_node_id, "d": p.data_date, "off": p.date_offset, "unit": p.offset_unit},
    ).first()

    if existing:
        params["id"] = existing[0]
        # 动态 SET 子句
        set_parts = [
            "node_code=:node_code", "node_name=:node_name", "node_level=:node_level",
            "parent_code=:parent_code", "is_leaf=:is_leaf", "category=:category",
            "asf_rsf=:asf_rsf", "hqla_factor=:hqla_factor",
            "current_balance=:current_balance", "avg_balance=:avg_balance",
            "weighted_rate=:weighted_rate", "interest_amount=:interest_amount",
            "risk_weight=:risk_weight", "calc_note=:calc_note", "updated_by=:u",
        ] + [f"{c}=:{c}" for c in ORIG_COLS + REM_COLS]
        db.execute(
            text(f"UPDATE {MAIN_TABLE} SET {', '.join(set_parts)} WHERE id=:id"),
            params,
        )
        return {"id": existing[0], "action": "updated"}
    else:
        # 单表 INSERT（含全部 128 桶字段）
        cols = ["coa_node_id", "data_date", "date_offset", "offset_unit",
                "node_code", "node_name", "node_level", "parent_code", "is_leaf", "category",
                "asf_rsf", "hqla_factor", "current_balance", "avg_balance",
                "weighted_rate", "interest_amount", "risk_weight", "calc_note"] \
               + ORIG_COLS + REM_COLS + ["created_by", "updated_by"]
        # params 键名映射（n/d/off/u → coa_node_id/data_date/date_offset/...）
        iparams = dict(params)
        iparams["coa_node_id"] = iparams.pop("n")
        iparams["data_date"] = iparams.pop("d")
        iparams["date_offset"] = iparams.pop("off")
        iparams["offset_unit"] = iparams.pop("unit")
        iparams["updated_by"] = iparams.pop("u")
        iparams["created_by"] = uid
        col_list = ", ".join(cols)
        val_list = ", ".join(f":{c}" for c in cols)
        rid = db.execute(
            text(f"INSERT INTO {MAIN_TABLE} ({col_list}) VALUES ({val_list})"),
            iparams,
        ).lastrowid
        return {"id": rid, "action": "created"}


# _upsert_sub_table 已废弃：v3 单表结构不需要子表 upsert


@router.delete("/{bid}")
async def delete_basic(bid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """逻辑删除主表（v3 单表结构）"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text(f"UPDATE {MAIN_TABLE} SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
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
        text(f"SELECT DISTINCT b.data_date FROM {MAIN_TABLE} b "
             f"JOIN prcp_coa_node n ON n.id=b.coa_node_id "
             f"WHERE {' AND '.join(where)} ORDER BY b.data_date DESC LIMIT 100"),
        params,
    ).fetchall()
    return {"items": [r[0].isoformat() for r in rows if r[0]]}


@router.get("/by-scheme-matrix")
async def by_scheme_matrix(
    scheme_id: int = Query(...),
    data_date: str = Query(...),
    date_offset: int = Query(0),
    offset_unit: str = Query("D"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """二维矩阵（v3 单表，145 列直接 JOIN prcp_coa_node）
    注意：服务器数据库是 prcp_data_basic 单表结构（v3 兼容），不走 v4 三表 JOIN。
    """
    # 1) 取账户册节点（注意 prcp_coa_node 没有 category 字段，从 node_type 推断）
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
        node_type = r[5] or ""
        # category 从 node_type 推断（如 ASSET_LEAF -> ASSET）或从 path 推断
        cat = ""
        if node_type:
            cat = node_type.split("_")[0]
        elif "/" in path and path.split("/")[1].startswith("L1_"):
            cat = path.split("/")[1].replace("L1_", "")
        nodes.append({
            "coa_node_id": r[0], "node_code": r[1], "node_name": r[2],
            "parent_id": r[3], "node_level": r[4], "node_type": r[5], "path": r[6],
            "sort_order": r[7] or 0, "category": cat, "description": r[8] or "",
        })

    # 2) 单表 JOIN 取矩阵数据（v3：15 主表字段 + 128 桶）
    rows = db.execute(
        text(f"""SELECT b.coa_node_id, b.data_date, b.node_code, b.node_name, b.node_level,
                       b.parent_code, b.is_leaf, b.category, b.date_offset, b.offset_unit,
                       b.asf_rsf, b.hqla_factor, b.current_balance, b.avg_balance,
                       b.weighted_rate, b.interest_amount, b.risk_weight,
                       {all_select_sql(prefix='')}
                FROM {MAIN_TABLE} b
                JOIN prcp_coa_node n ON n.id = b.coa_node_id
                WHERE b.data_date=:d AND b.date_offset=:off AND b.offset_unit=:u
                  AND b.is_deleted=0 AND n.scheme_id=:s
                ORDER BY b.coa_node_id"""),
        {"s": scheme_id, "d": data_date, "off": date_offset, "u": offset_unit},
    ).fetchall()

    # 行结构（共 15+128 = 143 列）：
    #   0..14: 主表字段（coa_node_id ... risk_weight）
    #   15..78: orig_m1..m60 + orig_y10/y15/y20/y30
    #   79..142: rem_m1..m60 + rem_y10/y15/y20/y30
    matrix: dict = {}
    for r in rows:
        cid = r[0]
        m = matrix.setdefault(cid, {
            "asf_rsf": r[10] or "",
            "hqla_factor": float(r[11] or 0) if r[11] is not None else None,
            "current_balance": float(r[12] or 0),
            "avg_balance": float(r[13] or 0),
            "weighted_rate": float(r[14] or 0),
            "interest_amount": float(r[15] or 0),
            "risk_weight": float(r[16] or 0),
        })
        for i, k in enumerate(ORIG_COLS):
            m[k] = float(r[15 + i] or 0) if r[15 + i] is not None else 0
        for i, k in enumerate(REM_COLS):
            m[k] = float(r[15 + N_BUCKETS + i] or 0) if r[15 + N_BUCKETS + i] is not None else 0

    # 3) 大类汇总
    NUMERIC_KEYS = ORIG_COLS + REM_COLS + [
        "current_balance", "avg_balance", "weighted_rate", "interest_amount", "risk_weight",
    ]

    def classify_category(node: dict) -> str:
        code = node.get("node_code") or ""
        path = node.get("path") or ""
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
    l1_has_data = any(
        matrix.get(cid, {}).get("current_balance", 0) for cid in l1_cids
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
    """导出 Excel（基础数据表 → 与前端 BasicDataSheet 二级表头保持一致）

    表头（145 列 = 10 基础 + 64 原始 + 64 剩余 + 7 度量）：
      Row 1: 标题
      Row 2: 二级表头分组（原始期限 / 剩余期限 / 度量）
      Row 3: 详细列名（账户册编码、原始期限 m1~m60+y10/y15/y20/y30、剩余期限 ...、度量列）
      Row 4+: 数据行（按方案节点顺序，每个节点一行）

    注意：当前数据库是单表 prcp_data_basic（145 列），不走 v4 三表 JOIN。
    """
    # 1) 节点列表（按 path 排序，与前端账户册矩阵对齐）
    # 注意：服务器 prcp_coa_node 没有 category 字段，从 node_type 推断
    node_rows = db.execute(
        text("""SELECT id, node_code, node_name, node_level, parent_id, path, sort_order, node_type
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0
                ORDER BY path, sort_order"""),
        {"s": scheme_id},
    ).fetchall()
    if not node_rows:
        raise HTTPException(404, "方案下无节点")

    # 2) 基础数据（v3 单表结构：145 列）
    rows = db.execute(
        text(f"""SELECT coa_node_id, data_date, node_code, node_name, node_level,
                       parent_code, is_leaf, category, asf_rsf, hqla_factor,
                       current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
                       {all_select_sql(prefix='')}
                FROM {MAIN_TABLE}
                WHERE data_date=:d AND date_offset=:off AND offset_unit=:u AND is_deleted=0"""),
        {"d": data_date, "off": date_offset, "u": offset_unit},
    ).fetchall()
    # key = coa_node_id
    row_map = {r[0]: r for r in rows}

    # 3) 构建 Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "基础数据"

    # === 列布局 ===
    # col 1: ID（数据日期-节点编码）
    # col 2: 数据日期
    # col 3: 账户册编码
    # col 4: 账户册名称
    # col 5: 层级
    # col 6: 父级编码
    # col 7: 是否末级
    # col 8: 大类
    # col 9: ASF/RSF
    # col 10: HQLA 折算系数
    # col 11 ~ 11+63: 原始期限（m1~m60 + y10/y15/y20/y30，64 列）
    # col 75 ~ 138: 剩余期限（64 列）
    # col 139 ~ 145: 度量（当前余额 / 平均余额 / 加权利率 / 利息 / 风险权重）

    # === Row 1: 标题 ===
    ws.cell(1, 1, f"账户册基础数据表 — 方案 {scheme_id} / {data_date}（{date_offset}{offset_unit}）")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10 + 2 * N_BUCKETS + 5)
    ws.cell(1, 1).font = Font(bold=True, size=14, color="1F4E78")
    ws.cell(1, 1).alignment = Alignment(horizontal="center", vertical="center")

    # === Row 2: 二级表头分组（与前端一致：原始期限(金额) / 剩余期限(金额) / 度量）===
    ws.cell(2, 11, "原始期限（金额）")
    ws.merge_cells(start_row=2, start_column=11, end_row=2, end_column=10 + N_BUCKETS)
    ws.cell(2, 11).font = Font(bold=True, color="1d39c4")
    ws.cell(2, 11).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(2, 11).fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")

    ws.cell(2, 11 + N_BUCKETS, "剩余期限（金额）")
    ws.merge_cells(start_row=2, start_column=11 + N_BUCKETS, end_row=2, end_column=10 + 2 * N_BUCKETS)
    ws.cell(2, 11 + N_BUCKETS).font = Font(bold=True, color="1d39c4")
    ws.cell(2, 11 + N_BUCKETS).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(2, 11 + N_BUCKETS).fill = PatternFill(start_color="EAF1F8", end_color="EAF1F8", fill_type="solid")

    ws.cell(2, 11 + 2 * N_BUCKETS, "度量")
    ws.merge_cells(start_row=2, start_column=11 + 2 * N_BUCKETS, end_row=2, end_column=10 + 2 * N_BUCKETS + 5)
    ws.cell(2, 11 + 2 * N_BUCKETS).font = Font(bold=True, color="1d39c4")
    ws.cell(2, 11 + 2 * N_BUCKETS).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(2, 11 + 2 * N_BUCKETS).fill = PatternFill(start_color="FBEAF0", end_color="FBEAF0", fill_type="solid")

    # === Row 3: 详细列名 ===
    base_headers = [
        "ID（数据日期-账户册编码）",   # col 1
        "数据日期",                     # col 2
        "账户册编码",                   # col 3
        "账户册名称",                   # col 4
        "账户册层级",                   # col 5
        "父级账户册编码",               # col 6
        "是否末级",                     # col 7
        "大类",                         # col 8
        "ASF/RSF",                      # col 9
        "HQLA折算系数",                 # col 10
    ]
    for col, h in enumerate(base_headers, start=1):
        cell = ws.cell(3, col, h)
        cell.font = Font(bold=True, size=10)
        cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # col 11 ~ : 原始期限（按 buckets 顺序，列名 = "原始期限·1M" 等）
    for i, b in enumerate(BUCKETS):
        col = 11 + i
        cell = ws.cell(3, col, f"原始·{b['name']}")
        cell.font = Font(size=10, color="13c2c2")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 剩余期限
    for i, b in enumerate(BUCKETS):
        col = 11 + N_BUCKETS + i
        cell = ws.cell(3, col, f"剩余·{b['name']}")
        cell.font = Font(size=10, color="722ed1")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 度量列
    measure_headers = ["当前余额", "平均余额（月）", "加权平均利率(%)", "平均利息收支", "风险权重(%)"]
    for i, h in enumerate(measure_headers):
        col = 11 + 2 * N_BUCKETS + i
        cell = ws.cell(3, col, h)
        cell.font = Font(bold=True, size=10, color="eb2f96")
        cell.fill = PatternFill(start_color="FBEAF0", end_color="FBEAF0", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    n_cols = 10 + 2 * N_BUCKETS + 5  # 145

    # === Row 4+: 数据行 ===
    # 样式
    FILL_L1 = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    FILL_L2 = PatternFill(start_color="EAF1F8", end_color="EAF1F8", fill_type="solid")
    FILL_SEP = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    FONT_L1 = Font(bold=True, size=11, color="1F4E78")
    FONT_L2 = Font(bold=True, size=10)
    FONT_NORMAL = Font(size=10)
    ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
    ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
    ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

    prev_l1_code = None
    ri = 4

    for n in node_rows:
        node_id, node_code, node_name, node_level, parent_id, path, sort_order, node_type = n
        node_level = node_level or 1
        # 从 node_type 推断 category（ASSET/LIAB/EQUITY/OTHER）
        if node_type:
            category = node_type.split("_")[0]
        else:
            category = ""

        # === 大类切换时插入空行作为分隔 ===
        if node_level == 1 and prev_l1_code is not None and node_code != prev_l1_code:
            for col in range(1, n_cols + 1):
                cell = ws.cell(ri, col, "")
                cell.fill = FILL_SEP
            ri += 1
        if node_level == 1:
            prev_l1_code = node_code

        r = row_map.get(node_id)

        # 元数据
        ws.cell(ri, 1, f"{data_date}-{node_code}")
        ws.cell(ri, 2, data_date)
        ws.cell(ri, 3, node_code)
        # 节点名称（按层级缩进）
        indent = "　" * max(node_level - 1, 0)
        name_cell = ws.cell(ri, 4, f"{indent}{node_name}")
        name_cell.alignment = ALIGN_LEFT
        if node_level == 1:
            name_cell.font = FONT_L1
            name_cell.fill = FILL_L1
        elif node_level == 2:
            name_cell.font = FONT_L2
            name_cell.fill = FILL_L2
        else:
            name_cell.font = FONT_NORMAL
        # 层级
        lv_cell = ws.cell(ri, 5, node_level)
        lv_cell.alignment = ALIGN_CENTER
        if node_level == 1:
            lv_cell.font = FONT_L1
            lv_cell.fill = FILL_L1
        elif node_level == 2:
            lv_cell.font = FONT_L2
            lv_cell.fill = FILL_L2

        if r:
            # 主表行：r = (coa_node_id, data_date, node_code, node_name, node_level,
            #              parent_code, is_leaf, category, asf_rsf, hqla_factor,
            #              current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
            #              orig_m1...orig_m60, orig_y10/y15/y20/y30,
            #              rem_m1...rem_m60, rem_y10/y15/y20/y30)
            ws.cell(ri, 6, r[5] or "")        # parent_code
            ws.cell(ri, 7, r[6] if r[6] is not None else 0)  # is_leaf
            ws.cell(ri, 8, r[7] or "")        # category
            ws.cell(ri, 9, r[8] or "")        # asf_rsf
            hqla = r[9]
            ws.cell(ri, 10, float(hqla) if hqla is not None else "")
            # 原始期限（64 桶，r[15] ~ r[15+63]）
            for i in range(N_BUCKETS):
                v = r[15 + i]
                ws.cell(ri, 11 + i, float(v) if v is not None else 0).alignment = ALIGN_RIGHT
            # 剩余期限（64 桶，r[15+64] ~ r[15+127]）
            for i in range(N_BUCKETS):
                v = r[15 + N_BUCKETS + i]
                ws.cell(ri, 11 + N_BUCKETS + i, float(v) if v is not None else 0).alignment = ALIGN_RIGHT
            # 度量（5 列）：当前余额/平均余额/加权利率/利息/风险权重
            ws.cell(ri, 11 + 2 * N_BUCKETS + 0, float(r[10] or 0)).alignment = ALIGN_RIGHT  # current_balance
            ws.cell(ri, 11 + 2 * N_BUCKETS + 1, float(r[11] or 0)).alignment = ALIGN_RIGHT  # avg_balance
            # 加权利率：存为小数（0.041 = 4.1%），导出时 * 100 显示百分比
            wr = float(r[12] or 0) * 100
            ws.cell(ri, 11 + 2 * N_BUCKETS + 2, round(wr, 4)).alignment = ALIGN_RIGHT
            ws.cell(ri, 11 + 2 * N_BUCKETS + 3, float(r[13] or 0)).alignment = ALIGN_RIGHT  # interest_amount
            rw = float(r[14] or 0) * 100
            ws.cell(ri, 11 + 2 * N_BUCKETS + 4, round(rw, 4)).alignment = ALIGN_RIGHT
        else:
            # 没有基础数据时只填元数据
            ws.cell(ri, 6, "")
            ws.cell(ri, 7, 0)
            ws.cell(ri, 8, "")
            ws.cell(ri, 9, "")
            ws.cell(ri, 10, "")
            for i in range(N_BUCKETS):
                ws.cell(ri, 11 + i, 0).alignment = ALIGN_RIGHT
            for i in range(N_BUCKETS):
                ws.cell(ri, 11 + N_BUCKETS + i, 0).alignment = ALIGN_RIGHT
            for i in range(5):
                ws.cell(ri, 11 + 2 * N_BUCKETS + i, 0).alignment = ALIGN_RIGHT

        # L1/L2 整行底色
        if node_level == 1:
            for col in range(1, n_cols + 1):
                if not ws.cell(ri, col).fill or ws.cell(ri, col).fill.start_color.rgb in (None, "00000000"):
                    ws.cell(ri, col).fill = FILL_L1
        elif node_level == 2:
            for col in range(1, n_cols + 1):
                if not ws.cell(ri, col).fill or ws.cell(ri, col).fill.start_color.rgb in (None, "00000000"):
                    ws.cell(ri, col).fill = FILL_L2
        ri += 1

    # === 列宽 ===
    ws.column_dimensions["A"].width = 26  # ID
    ws.column_dimensions["B"].width = 12  # 数据日期
    ws.column_dimensions["C"].width = 12  # 账户册编码
    ws.column_dimensions["D"].width = 38  # 账户册名称（缩进后）
    ws.column_dimensions["E"].width = 8   # 层级
    ws.column_dimensions["F"].width = 14  # 父级编码
    ws.column_dimensions["G"].width = 8   # 是否末级
    ws.column_dimensions["H"].width = 8   # 大类
    ws.column_dimensions["I"].width = 8   # ASF/RSF
    ws.column_dimensions["J"].width = 10  # HQLA
    # 桶列宽
    for i in range(2 * N_BUCKETS):
        ws.column_dimensions[get_column_letter(11 + i)].width = 9
    # 度量列
    for i in range(5):
        ws.column_dimensions[get_column_letter(11 + 2 * N_BUCKETS + i)].width = 14

    # === 行高 + 冻结 ===
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 32
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


# ================== v4 兼容：原 BasicIn / 接口签名 ==================
# 旧的 _row_to_dict 调用方代码（前端的 BasicDataSheet.tsx）未变，依然能解析 orig/rem 数组
