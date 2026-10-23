"""PRCP CET1 参数补录 API

字段：账户册方案 + 账户册编码 + 数据日期 + 是否分子/分母 + 折算系数 + 运算符
字典：CET1_OPERATOR（运算符 + / -）
ID 规则：{scheme_code}_{node_code}_{YYYYMMDD}

端点：
- GET    /cet1-param/                列表（带筛选）
- GET    /cet1-param/options         下拉选项（账户册方案 + 节点 + 运算符字典）
- POST   /cet1-param/                新增
- PUT    /cet1-param/{pid}           更新
- DELETE /cet1-param/{pid}           软删
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/cet1-param", tags=["CET1 参数补录"])


# ---------- Schemas ----------
class CET1ParamIn(BaseModel):
    scheme_id: int
    scheme_code: str
    node_id: int
    node_code: str
    node_name: Optional[str] = None
    data_date: str                       # YYYY-MM-DD
    is_numerator: int = 0                # 0/1
    numerator_factor: float = 0
    numerator_operator: str = "+"
    is_rwa: int = 0
    rwa_weight: float = 0
    rwa_operator: str = "+"
    current_balance: float = 0
    rule_note: Optional[str] = None
    status: str = "ACTIVE"


class CET1ParamUpdate(BaseModel):
    is_numerator: Optional[int] = None
    numerator_factor: Optional[float] = None
    numerator_operator: Optional[str] = None
    is_rwa: Optional[int] = None
    rwa_weight: Optional[float] = None
    rwa_operator: Optional[str] = None
    current_balance: Optional[float] = None
    rule_note: Optional[str] = None
    status: Optional[str] = None


def _build_id(scheme_code: str, node_code: str, data_date: str) -> str:
    """ID 生成：{scheme_code}_{node_code}_{YYYYMMDD}"""
    s = str(data_date).strip()
    if "-" in s:
        s = s.replace("-", "")
    return f"{scheme_code}_{node_code}_{s}"


def _norm_int01(v) -> int:
    """归一化为 0/1"""
    if v is None:
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    try:
        return 1 if int(v) else 0
    except Exception:
        s = str(v).strip().lower()
        if s in ("是", "yes", "y", "true", "1"):
            return 1
        return 0


# ---------- 列表 + 选项 ----------
@router.get("")
async def list_cet1_params(
    scheme_id: Optional[int] = None,
    node_id: Optional[int] = None,
    data_date: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列表查询（默认排除已软删）"""
    where = ["p.is_deleted=0"]
    params: Dict[str, Any] = {}
    if scheme_id:
        where.append("p.scheme_id=:scheme_id")
        params["scheme_id"] = scheme_id
    if node_id:
        where.append("p.node_id=:node_id")
        params["node_id"] = node_id
    if data_date:
        where.append("p.data_date=STR_TO_DATE(:data_date, '%Y-%m-%d')")
        params["data_date"] = data_date
    if keyword:
        where.append("(p.node_code LIKE :kw OR p.node_name LIKE :kw OR p.rule_note LIKE :kw)")
        params["kw"] = f"%{keyword}%"

    rows = db.execute(
        text(f"""
            SELECT p.id, p.scheme_id, p.scheme_code, p.node_id, p.node_code, p.node_name,
                   p.data_date,
                   p.is_numerator, p.numerator_factor, p.numerator_operator,
                   p.is_rwa, p.rwa_weight, p.rwa_operator,
                   p.current_balance, p.rule_note, p.status,
                   p.created_at, p.updated_at,
                   s.scheme_name
            FROM prcp_cet1_param p
            LEFT JOIN prcp_coa_scheme s ON s.id=p.scheme_id
            WHERE {' AND '.join(where)}
            ORDER BY p.data_date DESC, p.scheme_code, p.node_code
            LIMIT 5000
        """),
        params,
    ).fetchall()

    return {
        "items": [
            {
                "id": r[0],
                "scheme_id": r[1], "scheme_code": r[2],
                "node_id": r[3], "node_code": r[4], "node_name": r[5],
                "data_date": r[6].isoformat() if r[6] else None,
                "is_numerator": int(r[7] or 0),
                "numerator_factor": float(r[8] or 0),
                "numerator_operator": r[9],
                "is_rwa": int(r[10] or 0),
                "rwa_weight": float(r[11] or 0),
                "rwa_operator": r[12],
                "current_balance": float(r[13] or 0),
                "rule_note": r[14],
                "status": r[15],
                "created_at": r[16].isoformat() if r[16] else None,
                "updated_at": r[17].isoformat() if r[17] else None,
                "scheme_name": r[18],
            } for r in rows
        ]
    }


@router.get("/options")
async def list_options(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """下拉选项：账户册方案 + 该方案下的节点 + CET1_OPERATOR 字典"""
    schemes = db.execute(text("""
        SELECT id, scheme_code, scheme_name, status
        FROM prcp_coa_scheme
        WHERE is_deleted=0 AND status='ACTIVE'
        ORDER BY scheme_code
    """)).fetchall()
    nodes = db.execute(text("""
        SELECT id, scheme_id, node_code, node_name, node_level, status
        FROM prcp_coa_node
        WHERE is_deleted=0 AND status='ACTIVE'
        ORDER BY scheme_id, path, sort_order
    """)).fetchall()
    operators = db.execute(text("""
        SELECT dict_key, dict_label, sort_order
        FROM sys_dict
        WHERE is_deleted=0 AND status='ACTIVE' AND dict_type='CET1_OPERATOR'
        ORDER BY sort_order, dict_key
    """)).fetchall()
    dates = db.execute(text("""
        SELECT DISTINCT data_date
        FROM prcp_cet1_param
        WHERE is_deleted=0
        ORDER BY data_date DESC
        LIMIT 60
    """)).fetchall()
    return {
        "schemes": [
            {"id": r[0], "scheme_code": r[1], "scheme_name": r[2], "status": r[3]}
            for r in schemes
        ],
        "nodes": [
            {
                "id": r[0], "scheme_id": r[1],
                "node_code": r[2], "node_name": r[3],
                "node_level": r[4], "status": r[5],
                "label": f"{r[2]} | {r[3]}",
            } for r in nodes
        ],
        "operators": [
            {"dict_key": r[0], "dict_label": r[1], "sort_order": r[2]}
            for r in operators
        ],
        "data_dates": [r[0].isoformat() for r in dates if r[0]],
    }


# ---------- 新增 / 更新 / 软删 ----------
@router.post("")
async def create_cet1_param(payload: CET1ParamIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """新增：主键冲突返回 400；自动补充 node_name"""
    scheme_id = payload.scheme_id
    scheme_code = payload.scheme_code
    node_id = payload.node_id
    node_code = payload.node_code
    node_name = payload.node_name

    # 自动补充 node_name（前端未传时，从节点表查）
    if not node_name:
        r = db.execute(text("""
            SELECT node_name FROM prcp_coa_node
            WHERE id=:nid AND is_deleted=0 LIMIT 1
        """), {"nid": node_id}).fetchone()
        if r:
            node_name = r[0]

    new_id = _build_id(scheme_code, node_code, payload.data_date)
    uid = user["id"]
    is_num = _norm_int01(payload.is_numerator)
    is_den = _norm_int01(payload.is_rwa)

    try:
        db.execute(text("""
            INSERT INTO prcp_cet1_param
              (id, scheme_id, scheme_code, node_id, node_code, node_name, data_date,
               is_numerator, numerator_factor, numerator_operator,
               is_rwa, rwa_weight, rwa_operator,
               current_balance, rule_note, status, created_by, updated_by)
            VALUES
              (:id, :sid, :sc, :nid, :nc, :nn, STR_TO_DATE(:dd, '%Y-%m-%d'),
               :is_n, :n_f, :n_op,
               :is_d, :d_f, :d_op,
               :bal, :note, :status, :uid, :uid)
        """), {
            "id": new_id, "sid": scheme_id, "sc": scheme_code,
            "nid": node_id, "nc": node_code, "nn": node_name or "",
            "dd": payload.data_date,
            "is_n": is_num, "n_f": payload.numerator_factor, "n_op": payload.numerator_operator,
            "is_d": is_den, "d_f": payload.rwa_weight, "d_op": payload.rwa_operator,
            "bal": payload.current_balance, "note": payload.rule_note,
            "status": payload.status, "uid": uid,
        })
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"新增失败：{str(e)}")

    return {"ok": True, "id": new_id}


@router.put("/{pid}")
async def update_cet1_param(pid: str, payload: CET1ParamUpdate,
                            db: Session = Depends(get_db), user=Depends(get_current_user)):
    """更新（数值/运算符/余额/规则说明/状态）"""
    set_clauses = []
    params: Dict[str, Any] = {"id": pid}

    field_map = {
        "is_numerator": ("is_numerator", lambda v: _norm_int01(v)),
        "numerator_factor":   ("numerator_factor", lambda v: float(v)),
        "numerator_operator": ("numerator_operator", lambda v: str(v)),
        "is_rwa": ("is_rwa", lambda v: _norm_int01(v)),
        "rwa_weight":   ("rwa_weight", lambda v: float(v)),
        "rwa_operator": ("rwa_operator", lambda v: str(v)),
        "current_balance": ("current_balance", lambda v: float(v)),
        "rule_note":    ("rule_note", lambda v: v),
        "status":       ("status", lambda v: v),
    }
    for k, (col, conv) in field_map.items():
        v = getattr(payload, k)
        if v is not None:
            set_clauses.append(f"{col}=:{k}")
            params[k] = conv(v)

    if not set_clauses:
        return {"ok": True, "id": pid, "updated": 0}

    set_clauses.append("updated_by=:uid")
    params["uid"] = user["id"]

    sql = f"UPDATE prcp_cet1_param SET {', '.join(set_clauses)} WHERE id=:id AND is_deleted=0"
    res = db.execute(text(sql), params)
    db.commit()
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True, "id": pid, "updated": res.rowcount}


@router.delete("/{pid}")
async def delete_cet1_param(pid: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删"""
    res = db.execute(text("""
        UPDATE prcp_cet1_param SET is_deleted=1, updated_by=:uid
        WHERE id=:id AND is_deleted=0
    """), {"id": pid, "uid": user["id"]})
    db.commit()
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True, "id": pid}