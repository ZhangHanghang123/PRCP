"""指标管理 API — 指标定义（含公式）+ 指标值（多版本）"""
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.services.formula_engine import evaluate, validate, FormulaError

router = APIRouter(prefix="/kpi", tags=["指标"])


class KpiDefIn(BaseModel):
    kpi_code: str
    kpi_name: str
    rpt_id: int
    formula: str
    calc_unit: str = "PERCENT"  # PERCENT / BP / RATIO / AMOUNT
    formula_desc: Optional[str] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    status: str = "ACTIVE"


class KpiValueIn(BaseModel):
    kpi_id: int
    data_date: str
    version: str = "V1.0"
    current_value: float
    prev_value: Optional[float] = None
    prev_year_value: Optional[float] = None
    calc_source: str = "MANUAL"
    calc_log: Optional[str] = None


# ---------- 指标定义 ----------
@router.get("/definitions")
async def list_defs(
    rpt_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["d.is_deleted=0"]
    params = {}
    if rpt_id:
        where.append("d.rpt_id=:r")
        params["r"] = rpt_id
    if keyword:
        where.append("(d.kpi_code LIKE :kw OR d.kpi_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    rows = db.execute(
        text(f"""SELECT d.id, d.kpi_code, d.kpi_name, d.rpt_id, r.report_name,
                       d.formula, d.calc_unit, d.formula_desc,
                       d.threshold_min, d.threshold_max, d.status,
                       d.created_at
                FROM prcp_kpi_definition d
                LEFT JOIN prcp_rpt_report r ON r.id=d.rpt_id AND r.is_deleted=0
                WHERE {' AND '.join(where)}
                ORDER BY d.id DESC"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0], "kpi_code": r[1], "kpi_name": r[2],
            "rpt_id": r[3], "report_name": r[4],
            "formula": r[5], "calc_unit": r[6], "formula_desc": r[7],
            "threshold_min": float(r[8]) if r[8] is not None else None,
            "threshold_max": float(r[9]) if r[9] is not None else None,
            "status": r[10],
            "created_at": r[11].isoformat() if r[11] else None,
        } for r in rows
    ]}


@router.post("/definitions")
async def create_def(p: KpiDefIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 公式校验
    v = validate(p.formula)
    if not v["ok"]:
        raise HTTPException(400, f"公式语法错误: {v['error']}")
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_kpi_definition
                (kpi_code, kpi_name, rpt_id, formula, calc_unit, formula_desc,
                 threshold_min, threshold_max, status, created_by, updated_by)
                VALUES (:c, :n, :r, :f, :u, :d, :min, :max, :s, :by, :by)"""),
            {
                "c": p.kpi_code, "n": p.kpi_name, "r": p.rpt_id,
                "f": p.formula, "u": p.calc_unit, "d": p.formula_desc,
                "min": p.threshold_min, "max": p.threshold_max,
                "s": p.status, "by": uid,
            },
        ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：kpi_code 可能重复 ({e})")
    return {"id": rid, "kpi_code": p.kpi_code}


@router.put("/definitions/{kid}")
async def update_def(kid: int, p: KpiDefIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    v = validate(p.formula)
    if not v["ok"]:
        raise HTTPException(400, f"公式语法错误: {v['error']}")
    r = db.execute(
        text("""UPDATE prcp_kpi_definition SET
            kpi_code=:c, kpi_name=:n, rpt_id=:r, formula=:f, calc_unit=:u,
            formula_desc=:d, threshold_min=:min, threshold_max=:max,
            status=:s, updated_by=:by
            WHERE id=:id AND is_deleted=0"""),
        {
            "c": p.kpi_code, "n": p.kpi_name, "r": p.rpt_id,
            "f": p.formula, "u": p.calc_unit, "d": p.formula_desc,
            "min": p.threshold_min, "max": p.threshold_max,
            "s": p.status, "by": uid, "id": kid,
        },
    ).rowcount
    if r == 0:
        raise HTTPException(404, "指标不存在")
    return {"ok": True}


@router.delete("/definitions/{kid}")
async def delete_def(kid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("UPDATE prcp_kpi_definition SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": kid},
    ).rowcount
    if r == 0:
        raise HTTPException(404, "指标不存在")
    return {"ok": True}


# ---------- 公式引擎 ----------
@router.post("/formula/eval")
async def formula_eval(payload: dict, user=Depends(get_current_user)):
    """在线求值（dry-run），body = {"formula": "...", "ctx": {...}}"""
    formula = payload.get("formula", "")
    ctx = payload.get("ctx", {})
    try:
        val = evaluate(formula, ctx)
        return {"ok": True, "result": val}
    except FormulaError as e:
        raise HTTPException(400, f"公式错误: {e}")


@router.post("/formula/validate")
async def formula_validate(payload: dict, user=Depends(get_current_user)):
    """只校验语法，不求值"""
    return validate(payload.get("formula", ""))


# ---------- 指标值 ----------
@router.get("/values")
async def list_values(
    kpi_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    version: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["v.is_deleted=0"]
    params = {}
    if kpi_id:
        where.append("v.kpi_id=:k")
        params["k"] = kpi_id
    if start_date:
        where.append("v.data_date>=:s")
        params["s"] = start_date
    if end_date:
        where.append("v.data_date<=:e")
        params["e"] = end_date
    if version:
        where.append("v.version=:v")
        params["v"] = version
    rows = db.execute(
        text(f"""SELECT v.id, v.kpi_id, k.kpi_code, k.kpi_name, k.calc_unit,
                       v.data_date, v.version, v.current_value, v.prev_value, v.prev_year_value,
                       v.calc_source, v.calc_log, v.created_at
                FROM prcp_kpi_value v
                LEFT JOIN prcp_kpi_definition k ON k.id=v.kpi_id AND k.is_deleted=0
                WHERE {' AND '.join(where)}
                ORDER BY v.data_date DESC, v.kpi_id
                LIMIT 2000"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0], "kpi_id": r[1], "kpi_code": r[2], "kpi_name": r[3], "calc_unit": r[4],
            "data_date": r[5].isoformat() if r[5] else None,
            "version": r[6],
            "current_value": float(r[7]) if r[7] is not None else None,
            "prev_value": float(r[8]) if r[8] is not None else None,
            "prev_year_value": float(r[9]) if r[9] is not None else None,
            "calc_source": r[10], "calc_log": r[11],
            "created_at": r[12].isoformat() if r[12] else None,
        } for r in rows
    ]}


@router.post("/values")
async def upsert_value(p: KpiValueIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    existing = db.execute(
        text("""SELECT id FROM prcp_kpi_value
            WHERE kpi_id=:k AND data_date=:d AND version=:v AND is_deleted=0"""),
        {"k": p.kpi_id, "d": p.data_date, "v": p.version},
    ).first()
    if existing:
        db.execute(
            text("""UPDATE prcp_kpi_value SET
                current_value=:c, prev_value=:p, prev_year_value=:py,
                calc_source=:cs, calc_log=:cl, updated_by=:u
                WHERE id=:id"""),
            {
                "c": p.current_value, "p": p.prev_value, "py": p.prev_year_value,
                "cs": p.calc_source, "cl": p.calc_log, "u": uid, "id": existing[0],
            },
        )
        return {"id": existing[0], "action": "updated"}
    rid = db.execute(
        text("""INSERT INTO prcp_kpi_value
            (kpi_id, data_date, version, current_value, prev_value, prev_year_value,
             calc_source, calc_log, created_by, updated_by)
            VALUES (:k, :d, :v, :c, :p, :py, :cs, :cl, :u, :u)"""),
        {
            "k": p.kpi_id, "d": p.data_date, "v": p.version,
            "c": p.current_value, "p": p.prev_value, "py": p.prev_year_value,
            "cs": p.calc_source, "cl": p.calc_log, "u": uid,
        },
    ).lastrowid
    return {"id": rid, "action": "created"}


@router.delete("/values/{vid}")
async def delete_value(vid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("UPDATE prcp_kpi_value SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": vid},
    ).rowcount
    if r == 0:
        raise HTTPException(404, "指标值不存在")
    return {"ok": True}


# ---------- 公式引擎：用数据日期的指标值作为 ctx 批量计算 ----------
@router.post("/recalc")
async def recalc_kpi(
    kpi_id: int = Query(...),
    data_date: str = Query(...),
    ctx_values: dict = None,  # 可选：注入额外 ctx（覆盖数据库值）
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """计算某 KPI 在某数据日期的指标值
    步骤：
    1. 取指标公式
    2. 解析公式中的"rpt:XXX"引用 → 查 prcp_kpi_value / prcp_data_balance 取该日期值
    3. 注入 ctx_values 覆盖
    4. 求值
    5. 写入 prcp_kpi_value
    """
    kpi = db.execute(
        text("SELECT formula, kpi_code, kpi_name FROM prcp_kpi_definition WHERE id=:id AND is_deleted=0"),
        {"id": kpi_id},
    ).first()
    if not kpi:
        raise HTTPException(404, "指标不存在")
    formula = kpi[0]
    # 解析 ctx：先取同报表下所有指标在该日期的值
    ctx = {}
    other_kpis = db.execute(
        text("""SELECT kpi_code, id FROM prcp_kpi_definition
            WHERE rpt_id=(SELECT rpt_id FROM prcp_kpi_definition WHERE id=:id) AND is_deleted=0"""),
        {"id": kpi_id},
    ).fetchall()
    for kc, kid in other_kpis:
        v = db.execute(
            text("SELECT current_value FROM prcp_kpi_value WHERE kpi_id=:k AND data_date=:d AND is_deleted=0 LIMIT 1"),
            {"k": kid, "d": data_date},
        ).first()
        ctx[kc] = float(v[0]) if v and v[0] is not None else 0.0

    # 注入用户覆盖
    if ctx_values:
        ctx.update(ctx_values)

    try:
        result = evaluate(formula, ctx)
    except FormulaError as e:
        raise HTTPException(400, f"公式求值失败: {e}")
    # 写入（V1.0）
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    existing = db.execute(
        text("SELECT id FROM prcp_kpi_value WHERE kpi_id=:k AND data_date=:d AND version='V1.0' AND is_deleted=0"),
        {"k": kpi_id, "d": data_date},
    ).first()
    log = f"ctx={ctx}"
    if existing:
        db.execute(
            text("""UPDATE prcp_kpi_value SET
                current_value=:c, calc_source='MODEL', calc_log=:cl, updated_by=:u
                WHERE id=:id"""),
            {"c": result, "cl": log[:5000], "u": uid, "id": existing[0]},
        )
        return {"id": existing[0], "value": result, "action": "updated", "ctx": ctx}
    rid = db.execute(
        text("""INSERT INTO prcp_kpi_value
            (kpi_id, data_date, version, current_value, calc_source, calc_log, created_by, updated_by)
            VALUES (:k, :d, 'V1.0', :c, 'MODEL', :cl, :u, :u)"""),
        {"k": kpi_id, "d": data_date, "c": result, "cl": log[:5000], "u": uid},
    ).lastrowid
    return {"id": rid, "value": result, "action": "created", "ctx": ctx}
