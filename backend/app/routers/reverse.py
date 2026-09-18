"""组合反算 API — 方案 + 目标 + 执行 + 结果"""
import json
import uuid
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.services.reverse_calc_engine import run_reverse

router = APIRouter(prefix="/reverse", tags=["组合反算"])


# ============================================================
# Schemas
# ============================================================
class SchemeIn(BaseModel):
    scheme_code: str
    scheme_name: str
    scheme_type: str = "OPTIMIZE"
    coa_scheme_id: int
    data_date: str
    horizon_months: int = 24
    algorithm: str = "CVXPY_QP"
    model_id: Optional[int] = None     # 关联的计量模型 prcp_model.id（可空）
    description: Optional[str] = None
    status: str = "DRAFT"


class TargetIn(BaseModel):
    scheme_id: int
    kpi_id: Optional[int] = None
    kpi_code: Optional[str] = None
    target_name: str
    target_value: float
    constraint_type: str = "GE"
    weight: float = 1.0
    horizon_month: int = 0
    sort_order: int = 0
    description: Optional[str] = None


class RunIn(BaseModel):
    scheme_id: int
    description: Optional[str] = None


# ============================================================
# 反算方案 CRUD
# ============================================================
@router.get("/schemes")
async def list_schemes(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["s.is_deleted=0"]
    params = {}
    if keyword:
        where.append("(s.scheme_code LIKE :kw OR s.scheme_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if status:
        where.append("s.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT s.id, s.scheme_code, s.scheme_name, s.scheme_type,
                       s.coa_scheme_id, s.data_date, s.horizon_months, s.algorithm,
                       s.model_id,
                       s.description, s.status, s.created_at, s.updated_at,
                       cs.scheme_code AS coa_code, cs.scheme_name AS coa_name,
                       m.model_code AS model_code, m.model_name AS model_name, m.model_type AS model_type,
                       (SELECT COUNT(*) FROM prcp_reverse_target t WHERE t.scheme_id=s.id AND t.is_deleted=0) AS target_count,
                       (SELECT COUNT(*) FROM prcp_reverse_run r WHERE r.scheme_id=s.id AND r.is_deleted=0) AS run_count
                FROM prcp_reverse_scheme s
                LEFT JOIN prcp_coa_scheme cs ON cs.id=s.coa_scheme_id
                LEFT JOIN prcp_model m ON m.id=s.model_id AND m.is_deleted=0
                WHERE {' AND '.join(where)}
                ORDER BY s.id DESC"""),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_code": r[1], "scheme_name": r[2], "scheme_type": r[3],
                "coa_scheme_id": r[4], "data_date": r[5].isoformat() if r[5] else None,
                "horizon_months": r[6], "algorithm": r[7],
                "model_id": r[8],
                "description": r[9], "status": r[10],
                "coa_code": r[13], "coa_name": r[14],
                "model_code": r[15], "model_name": r[16], "model_type": r[17],
                "target_count": r[18], "run_count": r[19],
                "created_at": r[11].isoformat() if r[11] else None,
                "updated_at": r[12].isoformat() if r[12] else None,
            } for r in rows
        ]
    }


@router.post("/schemes")
async def create_scheme(p: SchemeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 校验 model_id 存在（若提供）
    if p.model_id is not None:
        m = db.execute(
            text("SELECT id FROM prcp_model WHERE id=:id AND is_deleted=0"),
            {"id": p.model_id},
        ).first()
        if not m:
            raise HTTPException(400, "关联的计量模型不存在")
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_reverse_scheme
                (scheme_code, scheme_name, scheme_type, coa_scheme_id, data_date,
                 horizon_months, algorithm, model_id, description, status, created_by, updated_by)
                VALUES (:c, :n, :st, :coa, :d, :h, :algo, :mid, :desc, :s, :u, :u)"""),
            {"c": p.scheme_code, "n": p.scheme_name, "st": p.scheme_type,
             "coa": p.coa_scheme_id, "d": p.data_date, "h": p.horizon_months,
             "algo": p.algorithm, "mid": p.model_id,
             "desc": p.description, "s": p.status, "u": uid},
        ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "scheme_code": p.scheme_code, "model_id": p.model_id}


@router.put("/schemes/{sid}")
async def update_scheme(sid: int, p: SchemeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    if p.model_id is not None:
        m = db.execute(
            text("SELECT id FROM prcp_model WHERE id=:id AND is_deleted=0"),
            {"id": p.model_id},
        ).first()
        if not m:
            raise HTTPException(400, "关联的计量模型不存在")
    r = db.execute(
        text("""UPDATE prcp_reverse_scheme SET
            scheme_code=:c, scheme_name=:n, scheme_type=:st, coa_scheme_id=:coa,
            data_date=:d, horizon_months=:h, algorithm=:algo, model_id=:mid,
            description=:desc, status=:s, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {"c": p.scheme_code, "n": p.scheme_name, "st": p.scheme_type,
         "coa": p.coa_scheme_id, "d": p.data_date, "h": p.horizon_months,
         "algo": p.algorithm, "mid": p.model_id,
         "desc": p.description, "s": p.status,
         "u": uid, "id": sid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "方案不存在")
    return {"ok": True}


# ============== 计量模型下拉选项 ==============
@router.get("/model-options")
async def model_options(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """给反算方案下拉用：列出所有 ACTIVE 模型"""
    rows = db.execute(
        text("""SELECT id, model_code, model_name, model_type, biz_domain, status
                FROM prcp_model
                WHERE is_deleted=0 AND status='ACTIVE'
                ORDER BY id DESC LIMIT 500"""),
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "model_code": r[1], "model_name": r[2],
                "model_type": r[3], "biz_domain": r[4], "status": r[5],
            }
            for r in rows
        ]
    }


@router.delete("/schemes/{sid}")
async def delete_scheme(sid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    db.execute(text("UPDATE prcp_reverse_target SET is_deleted=1 WHERE scheme_id=:s"), {"s": sid})
    db.execute(text("UPDATE prcp_reverse_run SET is_deleted=1 WHERE scheme_id=:s"), {"s": sid})
    r = db.execute(
        text("UPDATE prcp_reverse_scheme SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": sid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "方案不存在")
    return {"ok": True}


# ============================================================
# 目标指标 CRUD
# ============================================================
@router.get("/targets")
async def list_targets(
    scheme_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["t.is_deleted=0"]
    params = {}
    if scheme_id:
        where.append("t.scheme_id=:s")
        params["s"] = scheme_id
    rows = db.execute(
        text(f"""SELECT t.id, t.scheme_id, t.kpi_id, t.kpi_code, t.target_name,
                       t.target_value, t.constraint_type, t.weight, t.horizon_month,
                       t.sort_order, t.description,
                       k.kpi_name AS ref_kpi_name, k.formula AS ref_formula
                FROM prcp_reverse_target t
                LEFT JOIN prcp_kpi_definition k ON k.id=t.kpi_id
                WHERE {' AND '.join(where)}
                ORDER BY t.scheme_id, t.sort_order"""),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_id": r[1], "kpi_id": r[2], "kpi_code": r[3],
                "target_name": r[4], "target_value": float(r[5]),
                "constraint_type": r[6], "weight": float(r[7] or 1),
                "horizon_month": r[8], "sort_order": r[9], "description": r[10],
                "ref_kpi_name": r[11], "ref_formula": r[12],
            } for r in rows
        ]
    }


@router.post("/targets")
async def create_target(p: TargetIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_reverse_target
                (scheme_id, kpi_id, kpi_code, target_name, target_value,
                 constraint_type, weight, horizon_month, sort_order, description,
                 created_by, updated_by)
                VALUES (:sid, :kid, :kc, :n, :tv, :ct, :w, :hm, :so, :d, :u, :u)"""),
            {"sid": p.scheme_id, "kid": p.kpi_id, "kc": p.kpi_code,
             "n": p.target_name, "tv": p.target_value, "ct": p.constraint_type,
             "w": p.weight, "hm": p.horizon_month, "so": p.sort_order,
             "d": p.description, "u": uid},
        ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid}


@router.put("/targets/{tid}")
async def update_target(tid: int, p: TargetIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("""UPDATE prcp_reverse_target SET
            kpi_id=:kid, kpi_code=:kc, target_name=:n, target_value=:tv,
            constraint_type=:ct, weight=:w, horizon_month=:hm,
            sort_order=:so, description=:d, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {"kid": p.kpi_id, "kc": p.kpi_code, "n": p.target_name, "tv": p.target_value,
         "ct": p.constraint_type, "w": p.weight, "hm": p.horizon_month,
         "so": p.sort_order, "d": p.description, "u": uid, "id": tid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "目标不存在")
    return {"ok": True}


@router.delete("/targets/{tid}")
async def delete_target(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("UPDATE prcp_reverse_target SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": tid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "目标不存在")
    return {"ok": True}


@router.get("/kpi-options")
async def kpi_options(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(
        text("""SELECT id, kpi_code, kpi_name, formula, calc_unit
                FROM prcp_kpi_definition WHERE is_deleted=0 ORDER BY id DESC LIMIT 500"""),
    ).fetchall()
    return {
        "items": [
            {"id": r[0], "kpi_code": r[1], "kpi_name": r[2], "formula": r[3], "calc_unit": r[4]}
            for r in rows
        ]
    }


# ============================================================
# 反算执行
# ============================================================
@router.get("/runs")
async def list_runs(
    scheme_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["r.is_deleted=0"]
    params = {}
    if scheme_id:
        where.append("r.scheme_id=:s")
        params["s"] = scheme_id
    if status:
        where.append("r.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT r.id, r.run_code, r.scheme_id, r.status, r.progress,
                       r.start_at, r.end_at, r.duration_sec, r.optimal_value, r.metrics,
                       r.error_message, r.description, r.created_at,
                       s.scheme_code, s.scheme_name, s.horizon_months, s.algorithm
                FROM prcp_reverse_run r
                JOIN prcp_reverse_scheme s ON s.id=r.scheme_id
                WHERE {' AND '.join(where)}
                ORDER BY r.id DESC LIMIT 100"""),
        params,
    ).fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r[0], "run_code": r[1], "scheme_id": r[2], "status": r[3],
            "progress": float(r[4] or 0),
            "start_at": r[5].isoformat() if r[5] else None,
            "end_at": r[6].isoformat() if r[6] else None,
            "duration_sec": r[7],
            "optimal_value": float(r[8]) if r[8] is not None else None,
            "metrics": json.loads(r[9]) if r[9] else None,
            "error_message": r[10], "description": r[11],
            "scheme_code": r[13], "scheme_name": r[14],
            "horizon_months": r[15], "algorithm": r[16],
            "created_at": r[12].isoformat() if r[12] else None,
        })
    return {"items": items}


@router.post("/runs")
async def create_run(p: RunIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """创建反算任务（不立即执行）"""
    uid_val = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    code = f"R{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_reverse_run
                (run_code, scheme_id, status, description, created_by, updated_by)
                VALUES (:c, :s, 'PENDING', :d, :u, :u)"""),
            {"c": code, "s": p.scheme_id, "d": p.description, "u": uid_val},
        ).lastrowid
        # 初始日志
        try:
            db.execute(
                text("""INSERT INTO prcp_reverse_run_log (run_id, log_level, log_message, progress)
                        VALUES (:rid, 'INFO', '反算任务已创建', 0)"""),
                {"rid": rid},
            )
        except Exception:
            pass
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "run_code": code}


@router.post("/runs/{rid}/start")
async def start_run(rid: int, background_tasks: BackgroundTasks,
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    r = db.execute(
        text("""UPDATE prcp_reverse_run SET status='RUNNING', start_at=NOW(), progress=0
                WHERE id=:id AND is_deleted=0 AND status='PENDING'"""),
        {"id": rid},
    )
    if r.rowcount == 0:
        raise HTTPException(400, "反算不存在或已运行")
    from app.database import SessionLocal
    background_tasks.add_task(run_reverse, rid, SessionLocal)
    return {"ok": True, "message": "反算已启动"}


@router.post("/runs/{rid}/cancel")
async def cancel_run(rid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    r = db.execute(
        text("""UPDATE prcp_reverse_run SET status='CANCELLED', end_at=NOW(), error_message='用户取消'
                WHERE id=:id AND is_deleted=0 AND status IN ('PENDING','RUNNING')"""),
        {"id": rid},
    )
    if r.rowcount == 0:
        raise HTTPException(400, "无法取消")
    return {"ok": True}


@router.delete("/runs/{rid}")
async def delete_run(rid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("UPDATE prcp_reverse_run SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": rid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "反算不存在")
    return {"ok": True}


@router.get("/runs/{rid}/logs")
async def get_run_logs(rid: int, since_id: int = 0,
                       db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        rows = db.execute(
            text("""SELECT id, log_level, log_message, progress, created_at
                    FROM prcp_reverse_run_log
                    WHERE run_id=:rid AND id > :sid ORDER BY id ASC LIMIT 500"""),
            {"rid": rid, "sid": since_id},
        ).fetchall()
    except Exception:
        return {"items": []}
    return {
        "items": [
            {"id": r[0], "log_level": r[1], "log_message": r[2],
             "progress": float(r[3] or 0),
             "created_at": r[4].isoformat() if r[4] else None}
            for r in rows
        ]
    }


@router.get("/runs/{rid}/result")
async def get_run_result(rid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取反算结果（24 期 × N 节点预测值）"""
    rows = db.execute(
        text("""SELECT id, predict_month, predict_date, rpt_item_id, rpt_item_code,
                       current_value, adjusted_value, delta_value
                FROM prcp_reverse_result
                WHERE run_id=:rid AND is_deleted=0
                ORDER BY predict_month, rpt_item_id"""),
        {"rid": rid},
    ).fetchall()
    items = [
        {
            "id": r[0], "predict_month": r[1],
            "predict_date": r[2].isoformat() if r[2] else None,
            "rpt_item_id": r[3], "rpt_item_code": r[4],
            "current_value": float(r[5]) if r[5] is not None else None,
            "adjusted_value": float(r[6]), "delta_value": float(r[7]) if r[7] is not None else None,
        } for r in rows
    ]
    run = db.execute(
        text("""SELECT id, run_code, status, progress, optimal_value, metrics,
                      scheme_id, duration_sec
               FROM prcp_reverse_run WHERE id=:id"""),
        {"id": rid},
    ).first()
    run_dict = {
        "id": run[0], "run_code": run[1], "status": run[2],
        "progress": float(run[3] or 0),
        "optimal_value": float(run[4]) if run[4] is not None else None,
        "metrics": json.loads(run[5]) if run[5] else None,
        "scheme_id": run[6], "duration_sec": run[7],
    } if run else None
    return {"run": run_dict, "items": items}


@router.get("/algorithms")
async def list_algorithms(user=Depends(get_current_user)):
    """列出反算支持的算法"""
    return {"items": [
        {"code": "CVXPY_QP", "name": "二次规划（推荐）", "desc": "最小化现金流波动 + KPI 约束"},
        {"code": "CVXPY_LP", "name": "线性规划", "desc": "纯线性目标函数"},
        {"code": "HEURISTIC", "name": "启发式", "desc": "基于历史均值 + 趋势外推"},
    ]}