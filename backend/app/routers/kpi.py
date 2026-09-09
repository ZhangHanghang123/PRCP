"""指标管理 API（v2）— 方案 + 定义（含报表项引用）+ 维护（指标值多版本）"""
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.services.formula_engine import evaluate, validate, FormulaError

router = APIRouter(prefix="/kpi", tags=["指标管理"])


# ============== Schemas ==============
class SchemeIn(BaseModel):
    scheme_code: str
    scheme_name: str
    description: Optional[str] = None
    status: str = "ACTIVE"


class KpiDefIn(BaseModel):
    scheme_id: int
    kpi_code: str
    kpi_name: str
    rpt_id: int
    formula: str
    calc_unit: str = "PERCENT"
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


# ============== 指标方案 ==============
@router.get("/schemes")
async def list_schemes(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["s.is_deleted=0"]
    params: dict = {}
    if keyword:
        where.append("(s.scheme_code LIKE :kw OR s.scheme_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if status:
        where.append("s.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT s.id, s.scheme_code, s.scheme_name, s.description, s.status,
                       s.kpi_count, s.created_at, s.updated_at,
                       (SELECT COUNT(*) FROM prcp_kpi_definition d
                         WHERE d.scheme_id=s.id AND d.is_deleted=0) AS real_kpi_count
                FROM prcp_kpi_scheme s
                WHERE {' AND '.join(where)}
                ORDER BY s.id DESC"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0], "scheme_code": r[1], "scheme_name": r[2], "description": r[3],
            "status": r[4], "kpi_count": r[5] or r[8], "real_kpi_count": r[8],
            "created_at": r[6].isoformat() if r[6] else None,
            "updated_at": r[7].isoformat() if r[7] else None,
        } for r in rows
    ]}


@router.post("/schemes")
async def create_scheme(p: SchemeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_kpi_scheme
                (scheme_code, scheme_name, description, status, created_by, updated_by)
                VALUES (:c, :n, :d, :s, :u, :u)"""),
            {"c": p.scheme_code, "n": p.scheme_name, "d": p.description,
             "s": p.status, "u": uid},
        ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：方案编码可能重复 ({e})")
    return {"id": rid, "scheme_code": p.scheme_code, "scheme_name": p.scheme_name}


@router.put("/schemes/{sid}")
async def update_scheme(sid: int, p: SchemeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("""UPDATE prcp_kpi_scheme SET
            scheme_code=:c, scheme_name=:n, description=:d, status=:s, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {"c": p.scheme_code, "n": p.scheme_name, "d": p.description,
         "s": p.status, "u": uid, "id": sid},
    ).rowcount
    if r == 0:
        raise HTTPException(404, "方案不存在")
    return {"ok": True}


@router.delete("/schemes/{sid}")
async def delete_scheme(sid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删方案 + 其下所有 definition"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    n = db.execute(
        text("UPDATE prcp_kpi_definition SET is_deleted=1, updated_by=:u WHERE scheme_id=:s AND is_deleted=0"),
        {"u": uid, "s": sid},
    ).rowcount
    r = db.execute(
        text("UPDATE prcp_kpi_scheme SET is_deleted=1, updated_by=:u WHERE id=:s AND is_deleted=0"),
        {"u": uid, "s": sid},
    ).rowcount
    if r == 0:
        raise HTTPException(404, "方案不存在")
    return {"ok": True, "deleted_defs": n}


# ============== 报表表项（供指标定义引用） ==============
@router.get("/rpt-items")
async def list_rpt_items(
    rpt_id: Optional[int] = None,
    keyword: Optional[str] = None,
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列出报表表项，供指标定义公式下拉引用"""
    where = ["is_deleted=0"]
    params: dict = {"lim": limit}
    if rpt_id:
        where.append("report_id=:r")
        params["r"] = rpt_id
    if keyword:
        where.append("(item_code LIKE :kw OR item_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    rows = db.execute(
        text(f"""SELECT id, report_id, item_code, item_name, item_level, data_type
                FROM prcp_rpt_item
                WHERE {' AND '.join(where)}
                ORDER BY report_id, path
                LIMIT :lim"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0], "report_id": r[1], "item_code": r[2],
            "item_name": r[3], "level": r[4], "data_type": r[5],
        } for r in rows
    ]}


# ============== 指标定义 ==============
@router.get("/definitions")
async def list_defs(
    scheme_id: Optional[int] = None,
    rpt_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["d.is_deleted=0"]
    params: dict = {}
    if scheme_id:
        where.append("d.scheme_id=:s")
        params["s"] = scheme_id
    if rpt_id:
        where.append("d.rpt_id=:r")
        params["r"] = rpt_id
    if keyword:
        where.append("(d.kpi_code LIKE :kw OR d.kpi_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    rows = db.execute(
        text(f"""SELECT d.id, d.scheme_id, s.scheme_code, s.scheme_name,
                       d.kpi_code, d.kpi_name, d.rpt_id, r.report_code, r.report_name,
                       d.formula, d.calc_unit, d.formula_desc,
                       d.threshold_min, d.threshold_max, d.status,
                       d.created_at, d.updated_at
                FROM prcp_kpi_definition d
                LEFT JOIN prcp_kpi_scheme s ON s.id=d.scheme_id
                LEFT JOIN prcp_rpt_report r ON r.id=d.rpt_id
                WHERE {' AND '.join(where)}
                ORDER BY d.scheme_id, d.id DESC"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0],
            "scheme_id": r[1], "scheme_code": r[2], "scheme_name": r[3],
            "kpi_code": r[4], "kpi_name": r[5],
            "rpt_id": r[6], "report_code": r[7], "report_name": r[8],
            "formula": r[9], "calc_unit": r[10], "formula_desc": r[11],
            "threshold_min": float(r[12]) if r[12] is not None else None,
            "threshold_max": float(r[13]) if r[13] is not None else None,
            "status": r[14],
            "created_at": r[15].isoformat() if r[15] else None,
            "updated_at": r[16].isoformat() if r[16] else None,
        } for r in rows
    ]}


@router.post("/definitions")
async def create_def(p: KpiDefIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 公式校验
    v = validate(p.formula)
    if not v["ok"]:
        raise HTTPException(400, f"公式语法错误: {v['error']}")
    # 检查 scheme_id 存在
    if not db.execute(text("SELECT id FROM prcp_kpi_scheme WHERE id=:id AND is_deleted=0"), {"id": p.scheme_id}).first():
        raise HTTPException(400, "方案不存在")
    # 检查 rpt_id 存在
    if not db.execute(text("SELECT id FROM prcp_rpt_report WHERE id=:id AND is_deleted=0"), {"id": p.rpt_id}).first():
        raise HTTPException(400, "报表不存在")
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_kpi_definition
                (scheme_id, kpi_code, kpi_name, rpt_id, formula, calc_unit, formula_desc,
                 threshold_min, threshold_max, status, created_by, updated_by)
                VALUES (:s, :c, :n, :r, :f, :u, :d, :min, :max, :st, :by, :by)"""),
            {
                "s": p.scheme_id, "c": p.kpi_code, "n": p.kpi_name, "r": p.rpt_id,
                "f": p.formula, "u": p.calc_unit, "d": p.formula_desc,
                "min": p.threshold_min, "max": p.threshold_max,
                "st": p.status, "by": uid,
            },
        ).lastrowid
        db.execute(text("UPDATE prcp_kpi_scheme SET kpi_count=kpi_count+1 WHERE id=:s"), {"s": p.scheme_id})
    except Exception as e:
        raise HTTPException(400, f"创建失败：kpi_code 在本方案下重复 ({e})")
    return {"id": rid, "kpi_code": p.kpi_code, "scheme_id": p.scheme_id}


@router.put("/definitions/{kid}")
async def update_def(kid: int, p: KpiDefIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    v = validate(p.formula)
    if not v["ok"]:
        raise HTTPException(400, f"公式语法错误: {v['error']}")
    r = db.execute(
        text("""UPDATE prcp_kpi_definition SET
            scheme_id=:s, kpi_code=:c, kpi_name=:n, rpt_id=:r, formula=:f,
            calc_unit=:u, formula_desc=:d, threshold_min=:min, threshold_max=:max,
            status=:st, updated_by=:by
            WHERE id=:id AND is_deleted=0"""),
        {
            "s": p.scheme_id, "c": p.kpi_code, "n": p.kpi_name, "r": p.rpt_id,
            "f": p.formula, "u": p.calc_unit, "d": p.formula_desc,
            "min": p.threshold_min, "max": p.threshold_max,
            "st": p.status, "by": uid, "id": kid,
        },
    ).rowcount
    if r == 0:
        raise HTTPException(404, "指标不存在")
    return {"ok": True}


@router.delete("/definitions/{kid}")
async def delete_def(kid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    cur = db.execute(
        text("SELECT scheme_id FROM prcp_kpi_definition WHERE id=:id AND is_deleted=0"),
        {"id": kid},
    ).first()
    if not cur:
        raise HTTPException(404, "指标不存在")
    scheme_id = cur[0]
    # 软删指标值 + 指标定义
    db.execute(
        text("UPDATE prcp_kpi_value SET is_deleted=1 WHERE kpi_id=:id AND is_deleted=0"),
        {"id": kid},
    )
    db.execute(
        text("UPDATE prcp_kpi_definition SET is_deleted=1, updated_by=:u WHERE id=:id"),
        {"u": uid, "id": kid},
    )
    db.execute(
        text("UPDATE prcp_kpi_scheme SET kpi_count=GREATEST(0, kpi_count-1) WHERE id=:s"),
        {"s": scheme_id},
    )
    return {"ok": True}


# ============== 公式引擎 ==============
@router.post("/formula/eval")
async def formula_eval(payload: dict, user=Depends(get_current_user)):
    formula = payload.get("formula", "")
    ctx = payload.get("ctx", {})
    try:
        val = evaluate(formula, ctx)
        return {"ok": True, "result": val}
    except FormulaError as e:
        raise HTTPException(400, f"公式错误: {e}")


@router.post("/formula/validate")
async def formula_validate(payload: dict, user=Depends(get_current_user)):
    return validate(payload.get("formula", ""))


# ============== 指标值（维护） ==============
@router.get("/values")
async def list_values(
    kpi_id: Optional[int] = None,
    scheme_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    version: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["v.is_deleted=0"]
    params: dict = {}
    if kpi_id:
        where.append("v.kpi_id=:k")
        params["k"] = kpi_id
    if scheme_id:
        where.append("d.scheme_id=:s")
        params["s"] = scheme_id
    if start_date:
        where.append("v.data_date>=:sd")
        params["sd"] = start_date
    if end_date:
        where.append("v.data_date<=:ed")
        params["ed"] = end_date
    if version:
        where.append("v.version=:v")
        params["v"] = version
    rows = db.execute(
        text(f"""SELECT v.id, v.kpi_id, d.kpi_code, d.kpi_name, d.calc_unit,
                       s.scheme_code, s.scheme_name,
                       v.data_date, v.version, v.current_value, v.prev_value, v.prev_year_value,
                       v.calc_source, v.calc_log, v.created_at
                FROM prcp_kpi_value v
                LEFT JOIN prcp_kpi_definition d ON d.id=v.kpi_id
                LEFT JOIN prcp_kpi_scheme s ON s.id=d.scheme_id
                WHERE {' AND '.join(where)}
                ORDER BY v.data_date DESC, v.kpi_id
                LIMIT 2000"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0], "kpi_id": r[1], "kpi_code": r[2], "kpi_name": r[3],
            "calc_unit": r[4],
            "scheme_code": r[5], "scheme_name": r[6],
            "data_date": r[7].isoformat() if r[7] else None,
            "version": r[8],
            "current_value": float(r[9]) if r[9] is not None else None,
            "prev_value": float(r[10]) if r[10] is not None else None,
            "prev_year_value": float(r[11]) if r[11] is not None else None,
            "calc_source": r[12], "calc_log": r[13],
            "created_at": r[14].isoformat() if r[14] else None,
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


# ============== 重算 ==============
@router.post("/recalc")
async def recalc_kpi(
    kpi_id: int = Query(...),
    data_date: str = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """按公式 + 同方案下其他指标在指定日期的值，重新计算"""
    kpi = db.execute(
        text("SELECT formula, kpi_code, kpi_name, scheme_id, rpt_id FROM prcp_kpi_definition WHERE id=:id AND is_deleted=0"),
        {"id": kpi_id},
    ).first()
    if not kpi:
        raise HTTPException(404, "指标不存在")
    formula, kpi_code, kpi_name, scheme_id, rpt_id = kpi
    # ctx = 同方案下其他定义作为变量
    ctx = {}
    other = db.execute(
        text("""SELECT kpi_code, id FROM prcp_kpi_definition
            WHERE scheme_id=:s AND is_deleted=0"""),
        {"s": scheme_id},
    ).fetchall()
    for kc, kid in other:
        v = db.execute(
            text("SELECT current_value FROM prcp_kpi_value WHERE kpi_id=:k AND data_date=:d AND is_deleted=0 LIMIT 1"),
            {"k": kid, "d": data_date},
        ).first()
        ctx[kc] = float(v[0]) if v and v[0] is not None else 0.0
    try:
        result = evaluate(formula, ctx)
    except FormulaError as e:
        raise HTTPException(400, f"公式求值失败: {e}")
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    log = f"scheme={scheme_id}, ctx={ctx}"
    existing = db.execute(
        text("SELECT id FROM prcp_kpi_value WHERE kpi_id=:k AND data_date=:d AND version='V1.0' AND is_deleted=0"),
        {"k": kpi_id, "d": data_date},
    ).first()
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


# ============== 指标评分（v3 新增） ==============
class SegmentIn(BaseModel):
    seg_order: int = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    score: float
    segment_desc: Optional[str] = None


class ScoreRuleIn(BaseModel):
    scheme_id: int
    kpi_id: int
    rule_name: str
    calc_method: str = "PIECEWISE"   # PIECEWISE 分段 / LINEAR 线性
    total_score: float = 100.0
    higher_is_better: int = 1
    description: Optional[str] = None
    status: str = "ACTIVE"
    segments: List[SegmentIn] = []   # 新建时一并保存


@router.get("/score-rules")
async def list_score_rules(
    scheme_id: Optional[int] = None,
    kpi_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列出评分规则，可按方案/指标过滤；返回时附带 segments"""
    where = ["r.is_deleted=0"]
    params: dict = {}
    if scheme_id:
        where.append("r.scheme_id=:s")
        params["s"] = scheme_id
    if kpi_id:
        where.append("r.kpi_id=:k")
        params["k"] = kpi_id
    rules = db.execute(
        text(f"""SELECT r.id, r.scheme_id, r.kpi_id, r.rule_name, r.calc_method,
                       r.total_score, r.higher_is_better, r.description, r.status,
                       d.kpi_code, d.kpi_name, s.scheme_code, s.scheme_name
                FROM prcp_kpi_score_rule r
                LEFT JOIN prcp_kpi_definition d ON d.id=r.kpi_id AND d.is_deleted=0
                LEFT JOIN prcp_kpi_scheme s ON s.id=r.scheme_id
                WHERE {' AND '.join(where)}
                ORDER BY r.id DESC"""),
        params,
    ).fetchall()
    if not rules:
        return {"items": []}
    rule_ids = [r[0] for r in rules]
    segs = db.execute(
        text(f"""SELECT id, rule_id, seg_order, min_value, max_value, score, segment_desc
                FROM prcp_kpi_score_segment
                WHERE rule_id IN :ids AND is_deleted=0
                ORDER BY rule_id, seg_order"""),
        {"ids": tuple(rule_ids)},
    ).fetchall()
    seg_map: dict = {}
    for s in segs:
        seg_map.setdefault(s[1], []).append({
            "id": s[0], "rule_id": s[1], "seg_order": s[2],
            "min_value": float(s[3]) if s[3] is not None else None,
            "max_value": float(s[4]) if s[4] is not None else None,
            "score": float(s[5]), "segment_desc": s[6],
        })
    return {"items": [{
        "id": r[0], "scheme_id": r[1], "kpi_id": r[2], "rule_name": r[3],
        "calc_method": r[4], "total_score": float(r[5]), "higher_is_better": r[6],
        "description": r[7], "status": r[8],
        "kpi_code": r[9], "kpi_name": r[10],
        "scheme_code": r[11], "scheme_name": r[12],
        "segments": seg_map.get(r[0], []),
    } for r in rules]}


@router.post("/score-rules")
async def create_score_rule(p: ScoreRuleIn, db: Session = Depends(get_db),
                            user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 校验 KPI 存在
    kpi = db.execute(
        text("SELECT id FROM prcp_kpi_definition WHERE id=:i AND is_deleted=0"),
        {"i": p.kpi_id},
    ).first()
    if not kpi:
        raise HTTPException(404, "指标不存在")
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_kpi_score_rule
                (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,
                 description, status, created_by, updated_by)
                VALUES (:s, :k, :n, :m, :t, :h, :d, :st, :u, :u)"""),
            {"s": p.scheme_id, "k": p.kpi_id, "n": p.rule_name, "m": p.calc_method,
             "t": p.total_score, "h": p.higher_is_better, "d": p.description,
             "st": p.status, "u": uid},
        ).lastrowid
        for seg in p.segments:
            db.execute(
                text("""INSERT INTO prcp_kpi_score_segment
                    (rule_id, seg_order, min_value, max_value, score, segment_desc)
                    VALUES (:r, :o, :mn, :mx, :sc, :d)"""),
                {"r": rid, "o": seg.seg_order,
                 "mn": seg.min_value, "mx": seg.max_value,
                 "sc": seg.score, "d": seg.segment_desc},
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"创建失败: {e}")
    return {"id": rid, "message": "ok", "segment_count": len(p.segments)}


@router.put("/score-rules/{rid}")
async def update_score_rule(rid: int, p: ScoreRuleIn, db: Session = Depends(get_db),
                            user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    exist = db.execute(
        text("SELECT id FROM prcp_kpi_score_rule WHERE id=:i AND is_deleted=0"),
        {"i": rid},
    ).first()
    if not exist:
        raise HTTPException(404, "规则不存在")
    try:
        db.execute(
            text("""UPDATE prcp_kpi_score_rule SET
                scheme_id=:s, kpi_id=:k, rule_name=:n, calc_method=:m,
                total_score=:t, higher_is_better=:h, description=:d, status=:st,
                updated_by=:u WHERE id=:i"""),
            {"s": p.scheme_id, "k": p.kpi_id, "n": p.rule_name, "m": p.calc_method,
             "t": p.total_score, "h": p.higher_is_better, "d": p.description,
             "st": p.status, "u": uid, "i": rid},
        )
        # 整段替换：软删旧段，插入新段
        db.execute(
            text("UPDATE prcp_kpi_score_segment SET is_deleted=1 WHERE rule_id=:r"),
            {"r": rid},
        )
        for seg in p.segments:
            db.execute(
                text("""INSERT INTO prcp_kpi_score_segment
                    (rule_id, seg_order, min_value, max_value, score, segment_desc)
                    VALUES (:r, :o, :mn, :mx, :sc, :d)"""),
                {"r": rid, "o": seg.seg_order,
                 "mn": seg.min_value, "mx": seg.max_value,
                 "sc": seg.score, "d": seg.segment_desc},
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"更新失败: {e}")
    return {"id": rid, "message": "ok"}


@router.delete("/score-rules/{rid}")
async def delete_score_rule(rid: int, db: Session = Depends(get_db),
                            user=Depends(get_current_user)):
    db.execute(
        text("UPDATE prcp_kpi_score_rule SET is_deleted=1 WHERE id=:i"),
        {"i": rid},
    )
    db.execute(
        text("UPDATE prcp_kpi_score_segment SET is_deleted=1 WHERE rule_id=:i"),
        {"i": rid},
    )
    db.commit()
    return {"id": rid, "message": "ok"}


@router.post("/score-calc")
async def score_calc(payload: dict, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    """根据指标值 + 规则 ID 计算分数"""
    rule_id = payload.get("rule_id")
    value = payload.get("value")
    if rule_id is None or value is None:
        raise HTTPException(400, "缺少 rule_id 或 value")
    rule = db.execute(
        text("""SELECT calc_method, higher_is_better FROM prcp_kpi_score_rule
            WHERE id=:i AND is_deleted=0"""),
        {"i": rule_id},
    ).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    segs = db.execute(
        text("""SELECT min_value, max_value, score, segment_desc
            FROM prcp_kpi_score_segment
            WHERE rule_id=:r AND is_deleted=0 ORDER BY seg_order"""),
        {"r": rule_id},
    ).fetchall()
    matched = None
    for s in segs:
        mn, mx, sc, desc = s
        in_range = True
        if mn is not None and value < float(mn):
            in_range = False
        if mx is not None and value > float(mx):
            in_range = False
        if in_range:
            matched = {"score": float(sc), "min_value": float(mn) if mn is not None else None,
                       "max_value": float(mx) if mx is not None else None,
                       "segment_desc": desc}
            break
    if matched is None:
        return {"matched": False, "value": value, "score": None,
                "message": "所有区间均不匹配，请检查规则配置"}
    return {"matched": True, "value": value, "score": matched["score"],
            "matched_range": {k: v for k, v in matched.items() if k != "score"},
            "higher_is_better": rule[1]}
