"""模型管理 API — 模型/版本/参数/训练 完整 CRUD"""
import json
import asyncio
import uuid
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.services.model_train_engine import run_train

router = APIRouter(prefix="/model", tags=["模型管理"])

# ============================================================
# Schemas
# ============================================================
class ModelIn(BaseModel):
    model_code: str
    model_name: str
    model_type: str = "LINEAR_REGRESSION"
    biz_domain: Optional[str] = None
    kpi_scheme_id: Optional[int] = None    # 关联指标方案 prcp_kpi_scheme.id（可空）
    description: Optional[str] = None
    algo_config: Optional[dict] = None
    status: str = "ACTIVE"


class VersionIn(BaseModel):
    model_id: int
    version_code: str
    version_name: str
    description: Optional[str] = None
    status: str = "DRAFT"


class ParamIn(BaseModel):
    version_id: int
    kpi_id: int
    kpi_code: Optional[str] = None
    param_code: str
    param_name: str
    param_type: str = "BASE"
    param_value: float
    unit: Optional[str] = None
    formula: Optional[str] = None
    formula_desc: Optional[str] = None
    sort_order: int = 0
    description: Optional[str] = None


class TrainIn(BaseModel):
    model_id: int
    version_id: int
    coa_scheme_id: int
    balance_date_from: str
    balance_date_to: str
    description: Optional[str] = None


# ============================================================
# 算法注册表（字典形式：code/name/category/desc/engine/params_schema）
# ============================================================
ALGORITHMS = [
    {"code": "LINEAR_REGRESSION", "name": "线性回归",
     "category": "传统机器学习", "engine": "sklearn.linear_model",
     "desc": "普通最小二乘法，适合线性关系拟合"},
    {"code": "LOGISTIC_GROWTH", "name": "逻辑斯蒂增长",
     "category": "传统机器学习", "engine": "numpy",
     "desc": "S 形曲线，适合存款增长等饱和场景"},
    {"code": "MONTE_CARLO", "name": "蒙特卡洛模拟",
     "category": "传统机器学习", "engine": "numpy",
     "desc": "随机抽样，适合不确定性/压力测试"},
    {"code": "LINEAR_PROGRAM", "name": "线性规划",
     "category": "运筹优化", "engine": "cvxpy",
     "desc": "CVXPY 求解，适合资产结构优化"},
    {"code": "ANT_COLONY", "name": "蚁群算法",
     "category": "智能优化", "engine": "services/ant_colony_engine",
     "desc": "模拟蚂蚁觅食的群体智能优化，适合组合优化/路径规划"},
    {"code": "ARIMA", "name": "ARIMA 时间序列",
     "category": "传统机器学习", "engine": "statsmodels",
     "desc": "自回归滑动平均（需 statsmodels）"},
    {"code": "FNN_LLM", "name": "FNN 大模型",
     "category": "深度学习大模型", "engine": "services/fnn_llm_engine",
     "desc": "前馈神经网络（FNN）大模型，适合非线性特征提取与预测"},
]


# ============================================================
# 模型 CRUD
# ============================================================
@router.get("/algorithms")
async def list_algorithms(user=Depends(get_current_user)):
    """列出所有支持的算法（含分类/引擎/说明）"""
    return {"items": ALGORITHMS}


@router.get("/scheme-options")
async def scheme_options(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """给模型编辑下拉用：列出所有 ACTIVE 指标方案"""
    rows = db.execute(
        text("""SELECT id, scheme_code, scheme_name, kpi_count, status
                FROM prcp_kpi_scheme
                WHERE is_deleted=0 AND status='ACTIVE'
                ORDER BY id DESC LIMIT 500"""),
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_code": r[1], "scheme_name": r[2],
                "kpi_count": r[3] or 0, "status": r[4],
            }
            for r in rows
        ]
    }


@router.get("/models")
async def list_models(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["m.is_deleted=0"]
    params = {}
    if keyword:
        where.append("(m.model_code LIKE :kw OR m.model_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if status:
        where.append("m.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT m.id, m.model_code, m.model_name, m.model_type, m.biz_domain,
                       m.kpi_scheme_id, m.description, m.algo_config, m.status,
                       m.created_at, m.updated_at,
                       (SELECT COUNT(*) FROM prcp_model_version v WHERE v.model_id=m.id AND v.is_deleted=0) AS version_count,
                       ks.scheme_code AS kpi_scheme_code, ks.scheme_name AS kpi_scheme_name
                FROM prcp_model m
                LEFT JOIN prcp_kpi_scheme ks ON ks.id=m.kpi_scheme_id AND ks.is_deleted=0
                WHERE {' AND '.join(where)}
                ORDER BY m.id DESC"""),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "model_code": r[1], "model_name": r[2], "model_type": r[3],
                "biz_domain": r[4], "kpi_scheme_id": r[5],
                "kpi_scheme_code": r[12], "kpi_scheme_name": r[13],
                "description": r[6],
                "algo_config": json.loads(r[7]) if r[7] else None,
                "status": r[8], "version_count": r[11],
                "created_at": r[9].isoformat() if r[9] else None,
                "updated_at": r[10].isoformat() if r[10] else None,
            } for r in rows
        ]
    }


@router.post("/models")
async def create_model(p: ModelIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 校验 kpi_scheme_id 存在（如果提供）
    if p.kpi_scheme_id is not None:
        s = db.execute(
            text("SELECT id FROM prcp_kpi_scheme WHERE id=:id AND is_deleted=0"),
            {"id": p.kpi_scheme_id},
        ).first()
        if not s:
            raise HTTPException(400, "关联的指标方案不存在")
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_model
                (model_code, model_name, model_type, biz_domain, kpi_scheme_id,
                 description, algo_config, status, created_by, updated_by)
                VALUES (:c, :n, :t, :bd, :ksid, :d, :cfg, :s, :u, :u)"""),
            {
                "c": p.model_code, "n": p.model_name, "t": p.model_type,
                "bd": p.biz_domain, "ksid": p.kpi_scheme_id,
                "d": p.description,
                "cfg": json.dumps(p.algo_config) if p.algo_config else None,
                "s": p.status, "u": uid,
            },
        ).lastrowid
        # 自动创建 V1_BASELINE 版本
        db.execute(
            text("""INSERT INTO prcp_model_version
                (model_id, version_code, version_name, description, status, created_by, updated_by)
                VALUES (:mid, 'V1_BASELINE', '基准情景', '自动创建的初始版本', 'DRAFT', :u, :u)"""),
            {"mid": rid, "u": uid},
        )
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "model_code": p.model_code, "model_name": p.model_name,
            "kpi_scheme_id": p.kpi_scheme_id}


@router.put("/models/{mid}")
async def update_model(mid: int, p: ModelIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    if p.kpi_scheme_id is not None:
        s = db.execute(
            text("SELECT id FROM prcp_kpi_scheme WHERE id=:id AND is_deleted=0"),
            {"id": p.kpi_scheme_id},
        ).first()
        if not s:
            raise HTTPException(400, "关联的指标方案不存在")
    r = db.execute(
        text("""UPDATE prcp_model SET
            model_code=:c, model_name=:n, model_type=:t, biz_domain=:bd, kpi_scheme_id=:ksid,
            description=:d, algo_config=:cfg, status=:s, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {
            "c": p.model_code, "n": p.model_name, "t": p.model_type,
            "bd": p.biz_domain, "ksid": p.kpi_scheme_id,
            "d": p.description,
            "cfg": json.dumps(p.algo_config) if p.algo_config else None,
            "s": p.status, "u": uid, "id": mid,
        },
    )
    if r.rowcount == 0:
        raise HTTPException(404, "模型不存在")
    return {"ok": True}


@router.delete("/models/{mid}")
async def delete_model(mid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """软删模型 + 其下所有版本 + 参数 + 训练"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 先软删参数
    db.execute(
        text("""UPDATE prcp_model_param SET is_deleted=1, updated_by=:u
                WHERE version_id IN (SELECT id FROM prcp_model_version WHERE model_id=:mid AND is_deleted=0)"""),
        {"u": uid, "mid": mid},
    )
    # 软删版本
    db.execute(
        text("UPDATE prcp_model_version SET is_deleted=1, updated_by=:u WHERE model_id=:mid AND is_deleted=0"),
        {"u": uid, "mid": mid},
    )
    # 软删训练
    db.execute(
        text("UPDATE prcp_model_train SET is_deleted=1, updated_by=:u WHERE model_id=:mid AND is_deleted=0"),
        {"u": uid, "mid": mid},
    )
    # 软删模型
    r = db.execute(
        text("UPDATE prcp_model SET is_deleted=1, updated_by=:u WHERE id=:mid AND is_deleted=0"),
        {"u": uid, "mid": mid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "模型不存在")
    return {"ok": True}


# ============================================================
# 参数版本 CRUD
# ============================================================
@router.get("/versions")
async def list_versions(
    model_id: Optional[int] = None,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["v.is_deleted=0"]
    params = {}
    if model_id:
        where.append("v.model_id=:mid")
        params["mid"] = model_id
    if keyword:
        where.append("(v.version_code LIKE :kw OR v.version_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if status:
        where.append("v.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT v.id, v.model_id, v.version_code, v.version_name, v.parent_version_id,
                       v.param_count, v.description, v.status, v.created_at, v.updated_at,
                       m.model_code, m.model_name,
                       pv.version_code AS parent_version_code
                FROM prcp_model_version v
                JOIN prcp_model m ON m.id=v.model_id AND m.is_deleted=0
                LEFT JOIN prcp_model_version pv ON pv.id=v.parent_version_id AND pv.is_deleted=0
                WHERE {' AND '.join(where)}
                ORDER BY v.model_id, v.id DESC"""),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "model_id": r[1], "version_code": r[2], "version_name": r[3],
                "parent_version_id": r[4], "param_count": r[5],
                "description": r[6], "status": r[7],
                "model_code": r[10], "model_name": r[11],
                "parent_version_code": r[12],
                "created_at": r[8].isoformat() if r[8] else None,
                "updated_at": r[9].isoformat() if r[9] else None,
            } for r in rows
        ]
    }


@router.post("/versions")
async def create_version(p: VersionIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_model_version
                (model_id, version_code, version_name, description, status, created_by, updated_by)
                VALUES (:mid, :vc, :vn, :d, :s, :u, :u)"""),
            {"mid": p.model_id, "vc": p.version_code, "vn": p.version_name,
             "d": p.description, "s": p.status, "u": uid},
        ).lastrowid
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "version_code": p.version_code}


@router.put("/versions/{vid}")
async def update_version(vid: int, p: VersionIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("""UPDATE prcp_model_version SET
            version_code=:vc, version_name=:vn, description=:d, status=:s, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {"vc": p.version_code, "vn": p.version_name, "d": p.description,
         "s": p.status, "u": uid, "id": vid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "版本不存在")
    return {"ok": True}


@router.delete("/versions/{vid}")
async def delete_version(vid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 软删参数
    db.execute(
        text("UPDATE prcp_model_param SET is_deleted=1, updated_by=:u WHERE version_id=:vid AND is_deleted=0"),
        {"u": uid, "vid": vid},
    )
    # 软删版本
    r = db.execute(
        text("UPDATE prcp_model_version SET is_deleted=1, updated_by=:u WHERE id=:vid AND is_deleted=0"),
        {"u": uid, "vid": vid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "版本不存在")
    return {"ok": True}


@router.post("/versions/{vid}/copy")
async def copy_version(vid: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """复制版本：生成新版本 + 复制所有参数"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    new_code = payload.get("version_code")
    new_name = payload.get("version_name") or f"复制自 {vid}"
    if not new_code:
        raise HTTPException(400, "version_code 必填")
    src = db.execute(
        text("""SELECT id, model_id, version_code FROM prcp_model_version WHERE id=:id AND is_deleted=0"""),
        {"id": vid},
    ).first()
    if not src:
        raise HTTPException(404, "源版本不存在")
    try:
        new_id = db.execute(
            text("""INSERT INTO prcp_model_version
                (model_id, version_code, version_name, parent_version_id, description, status, created_by, updated_by)
                VALUES (:mid, :vc, :vn, :pid, :d, 'DRAFT', :u, :u)"""),
            {"mid": src[1], "vc": new_code, "vn": new_name, "pid": vid,
             "d": f"从 {src[2]} 复制", "u": uid},
        ).lastrowid
        # 复制参数
        params = db.execute(
            text("""SELECT kpi_id, kpi_code, param_code, param_name, param_type,
                           param_value, unit, formula, formula_desc, sort_order, description
                    FROM prcp_model_param WHERE version_id=:vid AND is_deleted=0"""),
            {"vid": vid},
        ).fetchall()
        for r in params:
            db.execute(
                text("""INSERT INTO prcp_model_param
                    (version_id, kpi_id, kpi_code, param_code, param_name, param_type,
                     param_value, unit, formula, formula_desc, sort_order, description, created_by, updated_by)
                    VALUES (:vid, :kid, :kc, :pc, :pn, :pt, :pv, :u2, :f, :fd, :so, :d, :u, :u)"""),
                {"vid": new_id, "kid": r[0], "kc": r[1], "pc": r[2], "pn": r[3], "pt": r[4],
                 "pv": r[5], "u2": r[6], "f": r[7], "fd": r[8], "so": r[9] or 0, "d": r[10],
                 "u": uid},
            )
        # 更新 param_count
        db.execute(
            text("UPDATE prcp_model_version SET param_count=:n WHERE id=:id"),
            {"n": len(params), "id": new_id},
        )
    except Exception as e:
        raise HTTPException(400, f"复制失败：{e}")
    return {"id": new_id, "version_code": new_code, "copied_params": len(params)}


# ============================================================
# 参数明细 CRUD
# ============================================================
@router.get("/params")
async def list_params(
    version_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["p.is_deleted=0"]
    params = {}
    if version_id:
        where.append("p.version_id=:vid")
        params["vid"] = version_id
    rows = db.execute(
        text(f"""SELECT p.id, p.version_id, p.kpi_id, p.kpi_code, p.param_code, p.param_name,
                       p.param_type, p.param_value, p.unit, p.formula, p.formula_desc,
                       p.sort_order, p.description, p.created_at, p.updated_at,
                       k.kpi_name AS ref_kpi_name, k.formula AS ref_formula
                FROM prcp_model_param p
                LEFT JOIN prcp_kpi_definition k ON k.id=p.kpi_id AND k.is_deleted=0
                WHERE {' AND '.join(where)}
                ORDER BY p.version_id, p.sort_order, p.id"""),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "version_id": r[1], "kpi_id": r[2], "kpi_code": r[3],
                "param_code": r[4], "param_name": r[5], "param_type": r[6],
                "param_value": float(r[7]), "unit": r[8],
                "formula": r[9], "formula_desc": r[10],
                "sort_order": r[11], "description": r[12],
                "ref_kpi_name": r[15], "ref_formula": r[16],
                "created_at": r[13].isoformat() if r[13] else None,
                "updated_at": r[14].isoformat() if r[14] else None,
            } for r in rows
        ]
    }


@router.post("/params")
async def create_param(p: ParamIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 校验版本存在
    v = db.execute(
        text("SELECT id FROM prcp_model_version WHERE id=:id AND is_deleted=0"),
        {"id": p.version_id},
    ).first()
    if not v:
        raise HTTPException(404, "版本不存在")
    # 校验 KPI 存在
    k = db.execute(
        text("SELECT kpi_code FROM prcp_kpi_definition WHERE id=:id AND is_deleted=0"),
        {"id": p.kpi_id},
    ).first()
    if not k:
        raise HTTPException(404, "KPI 不存在")
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_model_param
                (version_id, kpi_id, kpi_code, param_code, param_name, param_type,
                 param_value, unit, formula, formula_desc, sort_order, description, created_by, updated_by)
                VALUES (:vid, :kid, :kc, :pc, :pn, :pt, :pv, :u2, :f, :fd, :so, :d, :u, :u)"""),
            {"vid": p.version_id, "kid": p.kpi_id, "kc": p.kpi_code or k[0],
             "pc": p.param_code, "pn": p.param_name, "pt": p.param_type,
             "pv": p.param_value, "u2": p.unit, "f": p.formula, "fd": p.formula_desc,
             "so": p.sort_order, "d": p.description, "u": uid},
        ).lastrowid
        # 更新版本的 param_count
        db.execute(
            text("""UPDATE prcp_model_version SET param_count=(
                SELECT COUNT(*) FROM prcp_model_param WHERE version_id=:vid AND is_deleted=0
            ) WHERE id=:vid"""),
            {"vid": p.version_id},
        )
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "param_code": p.param_code}


@router.put("/params/{pid}")
async def update_param(pid: int, p: ParamIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("""UPDATE prcp_model_param SET
            kpi_id=:kid, kpi_code=:kc, param_code=:pc, param_name=:pn, param_type=:pt,
            param_value=:pv, unit=:u2, formula=:f, formula_desc=:fd,
            sort_order=:so, description=:d, updated_by=:u
            WHERE id=:id AND is_deleted=0"""),
        {"kid": p.kpi_id, "kc": p.kpi_code, "pc": p.param_code, "pn": p.param_name,
         "pt": p.param_type, "pv": p.param_value, "u2": p.unit,
         "f": p.formula, "fd": p.formula_desc, "so": p.sort_order,
         "d": p.description, "u": uid, "id": pid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "参数不存在")
    return {"ok": True}


@router.delete("/params/{pid}")
async def delete_param(pid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("UPDATE prcp_model_param SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": pid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "参数不存在")
    # 更新 param_count
    ver_id = db.execute(text("SELECT version_id FROM prcp_model_param WHERE id=:id"),
                        {"id": pid}).first()
    if ver_id:
        db.execute(
            text("""UPDATE prcp_model_version SET param_count=(
                SELECT COUNT(*) FROM prcp_model_param WHERE version_id=:vid AND is_deleted=0
            ) WHERE id=:vid"""),
            {"vid": ver_id[0]},
        )
    return {"ok": True}


@router.get("/kpi-options")
async def kpi_options(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """给参数编辑下拉用：列出所有 KPI 定义"""
    rows = db.execute(
        text("""SELECT id, kpi_code, kpi_name, formula, calc_unit
                FROM prcp_kpi_definition
                WHERE is_deleted=0
                ORDER BY id DESC LIMIT 500"""),
    ).fetchall()
    return {
        "items": [
            {"id": r[0], "kpi_code": r[1], "kpi_name": r[2], "formula": r[3], "calc_unit": r[4]}
            for r in rows
        ]
    }


# ============================================================
# 训练任务 CRUD
# ============================================================
@router.get("/trains")
async def list_trains(
    model_id: Optional[int] = None,
    version_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    where = ["t.is_deleted=0"]
    params = {}
    if model_id:
        where.append("t.model_id=:mid")
        params["mid"] = model_id
    if version_id:
        where.append("t.version_id=:vid")
        params["vid"] = version_id
    if status:
        where.append("t.status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT t.id, t.train_code, t.model_id, t.version_id, t.coa_scheme_id,
                       t.balance_date_from, t.balance_date_to, t.status, t.progress,
                       t.start_at, t.end_at, t.duration_sec, t.metrics, t.error_message,
                       t.description, t.created_at,
                       m.model_code, m.model_name, m.model_type,
                       v.version_code, v.version_name,
                       s.scheme_code, s.scheme_name
                FROM prcp_model_train t
                JOIN prcp_model m ON m.id=t.model_id
                JOIN prcp_model_version v ON v.id=t.version_id
                LEFT JOIN prcp_coa_scheme s ON s.id=t.coa_scheme_id
                WHERE {' AND '.join(where)}
                ORDER BY t.id DESC LIMIT 200"""),
        params,
    ).fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r[0], "train_code": r[1], "model_id": r[2], "version_id": r[3],
            "coa_scheme_id": r[4], "balance_date_from": r[5].isoformat() if r[5] else None,
            "balance_date_to": r[6].isoformat() if r[6] else None,
            "status": r[7], "progress": float(r[8] or 0),
            "start_at": r[9].isoformat() if r[9] else None,
            "end_at": r[10].isoformat() if r[10] else None,
            "duration_sec": r[11],
            "metrics": json.loads(r[12]) if r[12] else None,
            "error_message": r[13], "description": r[14],
            "model_code": r[16], "model_name": r[17], "model_type": r[18],
            "version_code": r[19], "version_name": r[20],
            "scheme_code": r[21], "scheme_name": r[22],
            "created_at": r[15].isoformat() if r[15] else None,
        })
    return {"items": items}


@router.post("/trains")
async def create_train(p: TrainIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """创建训练任务（不立即执行）"""
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 自动生成 train_code: T<date>_<6位随机>
    code = f"T{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_model_train
                (train_code, model_id, version_id, coa_scheme_id,
                 balance_date_from, balance_date_to, status, description, created_by, updated_by)
                VALUES (:c, :mid, :vid, :sid, :df, :dt, 'PENDING', :d, :u, :u)"""),
            {"c": code, "mid": p.model_id, "vid": p.version_id, "sid": p.coa_scheme_id,
             "df": p.balance_date_from, "dt": p.balance_date_to,
             "d": p.description, "u": uid},
        ).lastrowid
        # 写一条初始日志
        db.execute(
            text("""INSERT INTO prcp_model_train_log (train_id, log_level, log_message, progress)
                    VALUES (:tid, 'INFO', '训练任务已创建', 0)"""),
            {"tid": rid},
        )
    except Exception as e:
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "train_code": code}


@router.post("/trains/{tid}/start")
async def start_train(tid: int, background_tasks: BackgroundTasks,
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    """开始训练（异步执行）"""
    r = db.execute(
        text("""UPDATE prcp_model_train SET status='RUNNING', start_at=NOW(), progress=0
                WHERE id=:id AND is_deleted=0 AND status='PENDING'"""),
        {"id": tid},
    )
    if r.rowcount == 0:
        raise HTTPException(400, "训练任务不存在或已运行")
    # 启动后台任务
    from app.database import SessionLocal
    background_tasks.add_task(run_train, tid, SessionLocal)
    return {"ok": True, "message": "训练已启动"}


@router.post("/trains/{tid}/cancel")
async def cancel_train(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """取消训练（仅 PENDING/RUNNING 可取消）"""
    r = db.execute(
        text("""UPDATE prcp_model_train SET status='CANCELLED', end_at=NOW(), error_message='用户手动取消'
                WHERE id=:id AND is_deleted=0 AND status IN ('PENDING', 'RUNNING')"""),
        {"id": tid},
    )
    if r.rowcount == 0:
        raise HTTPException(400, "训练不存在或无法取消（已完成/已失败）")
    db.execute(
        text("""INSERT INTO prcp_model_train_log (train_id, log_level, log_message, progress)
                VALUES (:tid, 'WARN', '训练已被用户取消', 0)"""),
        {"tid": tid},
    )
    return {"ok": True}


@router.delete("/trains/{tid}")
async def delete_train(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    r = db.execute(
        text("UPDATE prcp_model_train SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": tid},
    )
    if r.rowcount == 0:
        raise HTTPException(404, "训练不存在")
    return {"ok": True}


@router.get("/trains/{tid}/logs")
async def get_train_logs(tid: int, since_id: int = 0,
                         db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取训练日志（支持 since_id 增量拉取）"""
    rows = db.execute(
        text("""SELECT id, log_level, log_message, progress, created_at
                FROM prcp_model_train_log
                WHERE train_id=:tid AND id > :sid
                ORDER BY id ASC LIMIT 500"""),
        {"tid": tid, "sid": since_id},
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "log_level": r[1], "log_message": r[2],
                "progress": float(r[3] or 0),
                "created_at": r[4].isoformat() if r[4] else None,
            } for r in rows
        ]
    }


@router.get("/trains/{tid}/result")
async def get_train_result(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取训练结果（每期预测值）"""
    rows = db.execute(
        text("""SELECT id, rpt_item_id, rpt_item_code, predict_period,
                       predicted_value, actual_value, confidence_low, confidence_high
                FROM prcp_model_train_result
                WHERE train_id=:tid AND is_deleted=0
                ORDER BY rpt_item_id, predict_period"""),
        {"tid": tid},
    ).fetchall()
    items = [
        {
            "id": r[0], "rpt_item_id": r[1], "rpt_item_code": r[2],
            "predict_period": r[3].isoformat() if r[3] else None,
            "predicted_value": float(r[4]), "actual_value": float(r[5]) if r[5] is not None else None,
            "confidence_low": float(r[6]) if r[6] is not None else None,
            "confidence_high": float(r[7]) if r[7] is not None else None,
        } for r in rows
    ]
    # 同时返回训练任务本身
    train = db.execute(
        text("""SELECT id, train_code, status, progress, metrics, model_id, version_id,
                       balance_date_from, balance_date_to, duration_sec
                FROM prcp_model_train WHERE id=:id"""),
        {"id": tid},
    ).first()
    train_dict = {
        "id": train[0], "train_code": train[1], "status": train[2],
        "progress": float(train[3] or 0),
        "metrics": json.loads(train[4]) if train[4] else None,
        "model_id": train[5], "version_id": train[6],
        "balance_date_from": train[7].isoformat() if train[7] else None,
        "balance_date_to": train[8].isoformat() if train[8] else None,
        "duration_sec": train[9],
    } if train else None
    return {"train": train_dict, "items": items}