"""PRCP ESG 场景工厂 — 后端 API Router（22 endpoint）

设计：
    - 单 router 文件（PRCP 现有约定）
    - prefix=/esg, tags=["ESG 场景工厂"]
    - 主路径 /prcp/api/esg/...
    - Pydantic Schema 只用 XxxIn 后缀（PRCP 约定）

核心功能：
    - 方案管理：CRUD + Clone + 状态切换
    - 三步执行：fit-pca + generate-hjm + generate-scenario + run-all
    - 情景集：列表 + 详情 + 下载 .npz
    - 运行历史：方案级 + 全局
    - Svensson 曲线：CRUD + 单日还原
    - 一键演示：run-one-click-case

注册方式（main.py）：
    from app.routers import esg
    app.include_router(esg.router, prefix="/prcp/api")
"""
import json
import logging
import os
import time
import uuid
from typing import Optional, List, Dict, Any

import numpy as np

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.services.esg import (
    SvenssonYieldCurve,
    YieldCurveGenerator,
    ScenarioSet,
    validate_paths,
    validate_factor_loadings,
    DEFAULT_MATURITIES_MONTHS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/esg", tags=["ESG 场景工厂"])


# ===================== 配置 =====================

def _get_case_dir() -> str:
    """HJM .npz 输出目录（可由 PRCP_CASE_DIR 环境变量覆盖）"""
    case_dir = os.environ.get("PRCP_CASE_DIR", "/var/lib/prcp/esg_cases")
    os.makedirs(case_dir, exist_ok=True)
    return case_dir


# per-scheme YieldCurveGenerator 缓存（避免 selector 跨方案丢失 PCA 拟合结果）
_STORE: Dict[int, YieldCurveGenerator] = {}


# ===================== Pydantic Schemas =====================

class EsgSchemeIn(BaseModel):
    scheme_code: str = Field(..., min_length=3, max_length=32)
    scheme_name: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    data_source: str = Field("ECB", pattern="^(ECB|FRB|CUSTOM|BANK)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    n_factors: int = Field(3, ge=1, le=6)
    maturities_months: List[int] = Field(default_factory=lambda: list(DEFAULT_MATURITIES_MONTHS))
    n_scenarios: int = Field(1000, ge=10, le=10000)
    n_steps: int = Field(120, ge=12, le=360)
    seed: int = Field(42, ge=0)
    initial_yields_pct: Optional[List[float]] = None
    status: str = Field("DRAFT", pattern="^(DRAFT|READY|ARCHIVED)$")


class EsgSchemeUpdate(BaseModel):
    scheme_name: Optional[str] = None
    description: Optional[str] = None
    data_source: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    n_factors: Optional[int] = None
    maturities_months: Optional[List[int]] = None
    n_scenarios: Optional[int] = None
    n_steps: Optional[int] = None
    seed: Optional[int] = None
    initial_yields_pct: Optional[List[float]] = None
    status: Optional[str] = None


class EsgPcaRunIn(BaseModel):
    n_factors: Optional[int] = Field(None, ge=1, le=6)


class EsgHjmRunIn(BaseModel):
    n_scenarios: Optional[int] = Field(None, ge=10, le=10000)
    n_steps: Optional[int] = Field(None, ge=12, le=360)
    seed: Optional[int] = None


class EsgCloneIn(BaseModel):
    new_scheme_code: str = Field(..., min_length=3, max_length=32)
    new_scheme_name: Optional[str] = None


class SvenssonCurveIn(BaseModel):
    curve_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    source: str = Field("ECB", pattern="^(ECB|FRB|CUSTOM|BANK)$")
    theta0: float
    theta1: float
    theta2: float
    theta3: float
    lambda1: float = Field(..., gt=0)
    lambda2: float = Field(..., gt=0)
    raw_data_json: Optional[dict] = None
    description: Optional[str] = None


class SvenssonBulkIn(BaseModel):
    points: List[SvenssonCurveIn]


class SvenssonRatesIn(BaseModel):
    tenors: List[int] = Field(..., min_items=1)
    source: Optional[str] = None


# ===================== 辅助 =====================

def _uid(user) -> int:
    return user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)


def _load_scheme(db: Session, scheme_id: int) -> dict:
    row = db.execute(text(
        "SELECT * FROM prcp_esg_scheme WHERE id=:i AND is_deleted=0"
    ), {"i": scheme_id}).first()
    if not row:
        raise HTTPException(404, f"scheme {scheme_id} 不存在或已删除")
    keys = ["id", "scheme_code", "scheme_name", "description", "data_source",
            "start_date", "end_date", "n_factors", "maturities_json", "n_scenarios",
            "n_steps", "seed", "initial_yields_json", "status", "is_deleted",
            "created_by", "updated_by", "created_at", "updated_at"]
    d = dict(zip(keys, row))
    # JSON 字段反序列化
    if d.get("maturities_json"):
        try:
            d["maturities_months"] = json.loads(d["maturities_json"])
        except Exception:
            d["maturities_months"] = list(DEFAULT_MATURITIES_MONTHS)
    else:
        d["maturities_months"] = list(DEFAULT_MATURITIES_MONTHS)
    if d.get("initial_yields_json"):
        try:
            d["initial_yields_pct"] = json.loads(d["initial_yields_json"])
        except Exception:
            d["initial_yields_pct"] = None
    else:
        d["initial_yields_pct"] = None
    # 日期转字符串
    for k in ("start_date", "end_date"):
        if d.get(k):
            d[k] = d[k].isoformat() if hasattr(d[k], "isoformat") else str(d[k])
    for k in ("created_at", "updated_at"):
        if d.get(k):
            d[k] = d[k].isoformat() if hasattr(d[k], "isoformat") else str(d[k])
    return d


def _load_curve_points(db: Session, scheme: dict) -> List[dict]:
    """从 prcp_esg_curve_point 加载某方案的 Svensson 参数点列表"""
    where = ["source = :c"]
    params = {"c": scheme["data_source"]}
    if scheme.get("start_date"):
        where.append("curve_date >= :sd")
        params["sd"] = scheme["start_date"]
    if scheme.get("end_date"):
        where.append("curve_date <= :ed")
        params["ed"] = scheme["end_date"]
    rows = db.execute(text(f"""
        SELECT curve_date, theta0, theta1, theta2, theta3, lambda1, lambda2
        FROM prcp_esg_curve_point
        WHERE is_deleted=0 AND {' AND '.join(where)}
        ORDER BY curve_date ASC
    """), params).fetchall()
    return [
        {"curve_date": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
         "theta0": float(r[1]), "theta1": float(r[2]),
         "theta2": float(r[3]), "theta3": float(r[4]),
         "lambda1": float(r[5]), "lambda2": float(r[6])}
        for r in rows
    ]


def _add_run_count(d: dict, db: Session) -> dict:
    """为方案附加 run_count + last_run_at"""
    row = db.execute(text("""
        SELECT COUNT(*), MAX(created_at) FROM prcp_esg_run WHERE scheme_id=:i
    """), {"i": d["id"]}).first()
    d["run_count"] = int(row[0] or 0)
    d["last_run_at"] = row[1].isoformat() if row[1] else None
    return d


# ===================== 方案管理 =====================

@router.get("/schemes")
async def list_schemes(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    rows = db.execute(text(f"""
        SELECT s.id, s.scheme_code, s.scheme_name, s.description, s.data_source,
               s.start_date, s.end_date, s.n_factors, s.maturities_json, s.n_scenarios,
               s.n_steps, s.seed, s.initial_yields_json, s.status,
               s.created_at, s.updated_at,
               (SELECT COUNT(*) FROM prcp_esg_run r WHERE r.scheme_id=s.id) AS run_count,
               (SELECT MAX(created_at) FROM prcp_esg_run r WHERE r.scheme_id=s.id) AS last_run_at
        FROM prcp_esg_scheme s
        WHERE {' AND '.join(where)}
        ORDER BY s.id DESC
        LIMIT :lim OFFSET :off
    """), {**params, "lim": page_size, "off": (page - 1) * page_size}).fetchall()

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM prcp_esg_scheme s WHERE {' AND '.join(where)}
    """), params).scalar() or 0

    items = []
    for r in rows:
        d = {
            "id": r[0], "scheme_code": r[1], "scheme_name": r[2],
            "description": r[3], "data_source": r[4],
            "start_date": r[5].isoformat() if r[5] else None,
            "end_date": r[6].isoformat() if r[6] else None,
            "n_factors": r[7],
            "maturities_months": json.loads(r[8]) if r[8] else list(DEFAULT_MATURITIES_MONTHS),
            "n_scenarios": r[9], "n_steps": r[10], "seed": r[11],
            "initial_yields_pct": json.loads(r[12]) if r[12] else None,
            "status": r[13],
            "created_at": r[14].isoformat() if r[14] else None,
            "updated_at": r[15].isoformat() if r[15] else None,
            "run_count": int(r[16] or 0),
            "last_run_at": r[17].isoformat() if r[17] else None,
        }
        items.append(d)
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.post("/schemes")
async def create_scheme(p: EsgSchemeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    # 唯一性检查
    exists = db.execute(text(
        "SELECT id FROM prcp_esg_scheme WHERE scheme_code=:c AND is_deleted=0"
    ), {"c": p.scheme_code}).first()
    if exists:
        raise HTTPException(409, f"scheme_code '{p.scheme_code}' 已存在")
    try:
        rid = db.execute(text("""
            INSERT INTO prcp_esg_scheme
            (scheme_code, scheme_name, description, data_source, start_date, end_date,
             n_factors, maturities_json, n_scenarios, n_steps, seed, initial_yields_json,
             status, created_by, updated_by)
            VALUES (:c, :n, :d, :ds, :sd, :ed, :nf, :mj, :ns, :nst, :sd2, :iy, :st, :u, :u)
        """), {
            "c": p.scheme_code, "n": p.scheme_name, "d": p.description,
            "ds": p.data_source,
            "sd": p.start_date, "ed": p.end_date,
            "nf": p.n_factors,
            "mj": json.dumps(p.maturities_months),
            "ns": p.n_scenarios, "nst": p.n_steps,
            "sd2": p.seed,
            "iy": json.dumps(p.initial_yields_pct) if p.initial_yields_pct else None,
            "st": p.status, "u": uid,
        }).lastrowid
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "scheme_code": p.scheme_code, "scheme_name": p.scheme_name}


@router.get("/schemes/{scheme_id}")
async def get_scheme(scheme_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    d = _load_scheme(db, scheme_id)
    _add_run_count(d, db)
    return d


@router.put("/schemes/{scheme_id}")
async def update_scheme(scheme_id: int, p: EsgSchemeUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    scheme = _load_scheme(db, scheme_id)  # 校验存在
    updates = {}
    if p.scheme_name is not None:
        updates["scheme_name"] = p.scheme_name
    if p.description is not None:
        updates["description"] = p.description
    if p.data_source is not None:
        updates["data_source"] = p.data_source
    if p.start_date is not None:
        updates["start_date"] = p.start_date
    if p.end_date is not None:
        updates["end_date"] = p.end_date
    if p.n_factors is not None:
        updates["n_factors"] = p.n_factors
    if p.maturities_months is not None:
        updates["maturities_json"] = json.dumps(p.maturities_months)
    if p.n_scenarios is not None:
        updates["n_scenarios"] = p.n_scenarios
    if p.n_steps is not None:
        updates["n_steps"] = p.n_steps
    if p.seed is not None:
        updates["seed"] = p.seed
    if p.initial_yields_pct is not None:
        updates["initial_yields_json"] = json.dumps(p.initial_yields_pct)
    if p.status is not None:
        updates["status"] = p.status
    if not updates:
        return {"ok": True, "message": "无字段更新"}

    set_clause = ", ".join([f"{k}=:{k}" for k in updates.keys()])
    db.execute(text(f"""
        UPDATE prcp_esg_scheme SET {set_clause}, updated_by=:u
        WHERE id=:i AND is_deleted=0
    """), {**updates, "u": uid, "i": scheme_id})
    db.commit()
    # PRCP 优化：更新方案时清缓存（防止 PCA/HJM 用旧配置）
    _STORE.pop(scheme_id, None)
    return {"ok": True}


@router.delete("/schemes/{scheme_id}")
async def delete_scheme(scheme_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    r = db.execute(text("""
        UPDATE prcp_esg_scheme SET is_deleted=1, updated_by=:u
        WHERE id=:i AND is_deleted=0
    """), {"u": uid, "i": scheme_id}).rowcount
    if r == 0:
        raise HTTPException(404, "scheme 不存在")
    db.commit()
    _STORE.pop(scheme_id, None)
    return {"ok": True}


@router.post("/schemes/{scheme_id}/clone")
async def clone_scheme(scheme_id: int, p: EsgCloneIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    src = _load_scheme(db, scheme_id)
    # 唯一性检查
    exists = db.execute(text(
        "SELECT id FROM prcp_esg_scheme WHERE scheme_code=:c AND is_deleted=0"
    ), {"c": p.new_scheme_code}).first()
    if exists:
        raise HTTPException(409, f"scheme_code '{p.new_scheme_code}' 已存在")
    new_name = p.new_scheme_name or f"{src['scheme_name']} (副本)"
    rid = db.execute(text("""
        INSERT INTO prcp_esg_scheme
        (scheme_code, scheme_name, description, data_source, start_date, end_date,
         n_factors, maturities_json, n_scenarios, n_steps, seed, initial_yields_json,
         status, created_by, updated_by)
        VALUES (:c, :n, :d, :ds, :sd, :ed, :nf, :mj, :ns, :nst, :sd2, :iy, 'DRAFT', :u, :u)
    """), {
        "c": p.new_scheme_code, "n": new_name, "d": src.get("description"),
        "ds": src["data_source"], "sd": src.get("start_date"), "ed": src.get("end_date"),
        "nf": src["n_factors"], "mj": json.dumps(src["maturities_months"]),
        "ns": src["n_scenarios"], "nst": src["n_steps"], "sd2": src["seed"],
        "iy": json.dumps(src.get("initial_yields_pct")) if src.get("initial_yields_pct") else None,
        "u": uid,
    }).lastrowid
    db.commit()
    return {"id": rid, "scheme_code": p.new_scheme_code, "scheme_name": new_name}


# ===================== 三步执行 =====================

@router.post("/schemes/{scheme_id}/fit-pca")
async def scheme_fit_pca(scheme_id: int, body: EsgPcaRunIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    scheme = _load_scheme(db, scheme_id)
    n_factors = body.n_factors or scheme["n_factors"]
    maturities = scheme["maturities_months"]

    # 取/建 Generator
    generator = _STORE.get(scheme_id)
    if not generator or generator.n_factors != n_factors or not np.array_equal(generator.maturities, np.array(maturities)):
        generator = YieldCurveGenerator(
            n_factors=n_factors,
            maturities_months=maturities,
            seed=scheme["seed"],
        )
        _STORE[scheme_id] = generator

    # 加载曲线数据 + PCA 拟合
    t0 = time.time()
    curve_points = _load_curve_points(db, scheme)
    if len(curve_points) < 2:
        # 无足够数据 → 冷启动默认参数
        generator.set_default_params()
    else:
        generator.fit_from_db_params(curve_points)

    duration_ms = int((time.time() - t0) * 1000)
    summary = generator.get_summary()

    # 写 prcp_esg_run
    rid = db.execute(text("""
        INSERT INTO prcp_esg_run
        (scheme_id, scheme_code, run_type, status, params_json, output_json, duration_ms, created_by)
        VALUES (:s, :c, 'PCA_FIT', 'SUCCESS', :p, :o, :d, :u)
    """), {
        "s": scheme_id, "c": scheme["scheme_code"],
        "p": json.dumps({"n_factors": n_factors, "data_source": scheme["data_source"],
                         "n_samples": len(curve_points)}),
        "o": json.dumps(summary),
        "d": duration_ms, "u": uid,
    }).lastrowid
    db.commit()
    return {"run_id": rid, "summary": summary}


@router.post("/schemes/{scheme_id}/generate-hjm")
async def scheme_generate_hjm(scheme_id: int, body: EsgHjmRunIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    scheme = _load_scheme(db, scheme_id)
    generator = _STORE.get(scheme_id)
    if not generator or not generator._pca_fitted:
        raise HTTPException(400, "请先跑 PCA")

    n_scenarios = body.n_scenarios or scheme["n_scenarios"]
    n_steps = body.n_steps or scheme["n_steps"]
    seed = body.seed if body.seed is not None else scheme["seed"]
    initial_yields = scheme.get("initial_yields_pct")

    t0 = time.time()
    paths = generator.generate_hjm_paths(
        n_scenarios=n_scenarios,
        n_steps=n_steps,
        seed=seed,
        initial_yields_pct=np.asarray(initial_yields) if initial_yields else None,
    )
    duration_ms = int((time.time() - t0) * 1000)

    # PRCP 优化：路径校验
    v = validate_paths(paths, min_threshold_pct=-0.5, volatility_warn=True)
    if not v["valid"]:
        # 负利率太多 → 抛 400
        if v["n_negative"] > n_scenarios * n_steps * 0.1:  # > 10% 负值才拒绝
            raise HTTPException(400, f"HJM 路径严重异常：{v['warnings']}")

    # 持久化 .npz
    case_dir = _get_case_dir()
    hjm_filename = f"hjm_{scheme_id}_{int(time.time() * 1000)}.npz"
    file_path = os.path.join(case_dir, hjm_filename)
    sc = ScenarioSet(
        n_scenarios=n_scenarios, n_steps=n_steps, n_maturities=paths.shape[2],
        paths=paths, maturities_months=generator.maturities,
        initial_yields_pct=np.asarray(initial_yields) if initial_yields else np.full(paths.shape[2], 3.0),
        seed=seed,
        description=f"HJM 中间产物 scheme={scheme_id}",
    )
    sc.save_to_npz(file_path)

    summary = sc.to_summary_json()
    summary["volatility_decaying"] = v["vol_decaying"]
    summary["validation_warnings"] = v["warnings"]

    rid = db.execute(text("""
        INSERT INTO prcp_esg_run
        (scheme_id, scheme_code, run_type, status, params_json, output_json, file_path, duration_ms, created_by)
        VALUES (:s, :c, 'HJM_GENERATE', 'SUCCESS', :p, :o, :f, :d, :u)
    """), {
        "s": scheme_id, "c": scheme["scheme_code"],
        "p": json.dumps({"n_scenarios": n_scenarios, "n_steps": n_steps, "seed": seed}),
        "o": json.dumps(summary),
        "f": file_path, "d": duration_ms, "u": uid,
    }).lastrowid
    db.commit()
    return {"run_id": rid, "file_path": file_path, "summary": summary}


@router.post("/schemes/{scheme_id}/generate")
async def scheme_generate_scenarios(scheme_id: int, body: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """生成情景集 = 把最后一次 HJM 路径保存为正式 scenario .npz"""
    uid = _uid(user)
    scheme = _load_scheme(db, scheme_id)
    generator = _STORE.get(scheme_id)
    if not generator or not generator._hjm_generated or generator.last_hjm_paths is None:
        raise HTTPException(400, "请先生成 HJM")

    paths = generator.last_hjm_paths
    scenario_code = uuid.uuid4().hex[:12]
    case_dir = _get_case_dir()
    sc_filename = f"scenario_{scheme_id}_{scenario_code}.npz"
    file_path = os.path.join(case_dir, sc_filename)

    sc = ScenarioSet(
        n_scenarios=paths.shape[0], n_steps=paths.shape[1], n_maturities=paths.shape[2],
        paths=paths, maturities_months=generator.maturities,
        initial_yields_pct=generator.initial_yields if hasattr(generator, "initial_yields") else np.full(paths.shape[2], 3.0),
        seed=generator.seed if hasattr(generator, "seed") else 42,
        description=f"ESG 方案 #{scheme_id} 情景集 {scenario_code}",
        metadata={"scheme_id": scheme_id, "scheme_code": scheme["scheme_code"]},
    )
    sc.save_to_npz(file_path)
    file_size = os.path.getsize(file_path)

    # B 方案：把 .npz 完整字节流读入 BLOB
    with open(file_path, "rb") as f:
        paths_blob = f.read()

    # D 方案：预计算 9 个 JSON 统计（前端展示免算）
    summary = sc.to_summary_json()
    n_zeros = int((paths == 0).sum())
    n_negatives = int((paths < 0).sum())

    # 写 prcp_esg_scenario（B+D 双写：blob + 派生统计 + 元数据）
    sc_id = db.execute(text("""
        INSERT INTO prcp_esg_scenario
        (scheme_id, scenario_code, scenario_type, file_path, n_scenarios, n_steps, n_maturities, seed,
         maturities_json, file_size_bytes, description, created_by,
         paths_blob,
         p10_json, p50_json, p90_json,
         final_mean_json, final_std_json, final_min_json, final_max_json,
         vol_per_maturity_json, n_zeros, n_negatives)
        VALUES
        (:s, :sc, 'esg_factory', :f, :ns, :nst, :nm, :sd,
         :mj, :fs, :desc, :u,
         :blob,
         :p10, :p50, :p90,
         :fmean, :fstd, :fmin, :fmax,
         :vol, :nz, :nn)
    """), {
        "s": scheme_id, "sc": scenario_code, "f": file_path,
        "ns": paths.shape[0], "nst": paths.shape[1], "nm": paths.shape[2],
        "sd": sc.seed, "mj": json.dumps(generator.maturities.tolist()),
        "fs": file_size, "desc": sc.description, "u": uid,
        "blob": paths_blob,
        "p10": json.dumps(summary["p10"]),
        "p50": json.dumps(summary["p50"]),
        "p90": json.dumps(summary["p90"]),
        "fmean": json.dumps(summary["final_distribution_mean"]),
        "fstd": json.dumps(summary["final_distribution_std"]),
        "fmin": json.dumps(summary["final_distribution_min"]),
        "fmax": json.dumps(summary["final_distribution_max"]),
        "vol": json.dumps(summary["vol_per_maturity"]),
        "nz": n_zeros, "nn": n_negatives,
    }).lastrowid

    # 写 prcp_esg_run
    rid = db.execute(text("""
        INSERT INTO prcp_esg_run
        (scheme_id, scheme_code, run_type, status, params_json, output_json, file_path, duration_ms, created_by)
        VALUES (:s, :c, 'SCENARIO_GENERATE', 'SUCCESS', :p, :o, :f, :d, :u)
    """), {
        "s": scheme_id, "c": scheme["scheme_code"],
        "p": json.dumps({"scenario_code": scenario_code}),
        "o": json.dumps({"scenario_code": scenario_code, "sc_id": sc_id,
                         "file_size_bytes": file_size, "paths_shape": list(paths.shape)}),
        "f": file_path, "d": 0, "u": uid,
    }).lastrowid

    db.execute(text("UPDATE prcp_esg_scenario SET last_run_id=:r WHERE id=:i"),
               {"r": rid, "i": sc_id})
    db.commit()

    return {"run_id": rid, "scenario_code": scenario_code, "sc_id": sc_id, "file_path": file_path}


@router.post("/schemes/{scheme_id}/run-all")
async def scheme_run_all(scheme_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """一键三步：PCA + HJM + Scenario"""
    pca_r = await scheme_fit_pca(scheme_id, EsgPcaRunIn(), db, user)
    hjm_r = await scheme_generate_hjm(scheme_id, EsgHjmRunIn(), db, user)
    sc_r = await scheme_generate_scenarios(scheme_id, {}, db, user)
    return {
        "scheme_id": scheme_id,
        "pca_run_id": pca_r["run_id"],
        "hjm_run_id": hjm_r["run_id"],
        "scenario_run_id": sc_r["run_id"],
        "scenario_code": sc_r["scenario_code"],
        "sc_id": sc_r["sc_id"],
        "file_path": sc_r["file_path"],
    }


# ===================== 运行历史 =====================

@router.get("/schemes/{scheme_id}/runs")
async def list_scheme_runs(scheme_id: int,
                            run_type: Optional[str] = None,
                            status: Optional[str] = None,
                            limit: int = Query(50, ge=1, le=200),
                            db: Session = Depends(get_db),
                            user=Depends(get_current_user)):
    _load_scheme(db, scheme_id)  # 校验存在
    where = ["scheme_id=:s"]
    params: dict = {"s": scheme_id, "lim": limit}
    if run_type:
        where.append("run_type=:t")
        params["t"] = run_type
    if status:
        where.append("status=:st")
        params["st"] = status
    rows = db.execute(text(f"""
        SELECT id, scheme_id, scheme_code, run_type, status, params_json, output_json,
               file_path, duration_ms, error_message, created_at
        FROM prcp_esg_run
        WHERE {' AND '.join(where)}
        ORDER BY id DESC
        LIMIT :lim
    """), params).fetchall()
    return {"items": [_row_to_run(r) for r in rows]}


@router.get("/runs")
async def list_all_runs(scheme_id: Optional[int] = None,
                          run_type: Optional[str] = None,
                          status: Optional[str] = None,
                          page: int = Query(1, ge=1),
                          page_size: int = Query(50, ge=1, le=200),
                          db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
    where = ["1=1"]
    params: dict = {"lim": page_size, "off": (page - 1) * page_size}
    if scheme_id:
        where.append("scheme_id=:s")
        params["s"] = scheme_id
    if run_type:
        where.append("run_type=:t")
        params["t"] = run_type
    if status:
        where.append("status=:st")
        params["st"] = status
    rows = db.execute(text(f"""
        SELECT id, scheme_id, scheme_code, run_type, status, params_json, output_json,
               file_path, duration_ms, error_message, created_at
        FROM prcp_esg_run
        WHERE {' AND '.join(where)}
        ORDER BY id DESC
        LIMIT :lim OFFSET :off
    """), params).fetchall()
    total = db.execute(text(f"SELECT COUNT(*) FROM prcp_esg_run WHERE {' AND '.join(where)}"),
                       params).scalar() or 0
    return {"items": [_row_to_run(r) for r in rows], "total": int(total),
            "page": page, "page_size": page_size}


@router.get("/runs/{run_id}")
async def get_run(run_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(text("""
        SELECT id, scheme_id, scheme_code, run_type, status, params_json, output_json,
               file_path, duration_ms, error_message, created_at
        FROM prcp_esg_run WHERE id=:i
    """), {"i": run_id}).first()
    if not row:
        raise HTTPException(404, f"run {run_id} 不存在")
    return _row_to_run(row)


def _row_to_run(r) -> dict:
    def _json_or_none(v):
        if v is None:
            return None
        try:
            return json.loads(v)
        except Exception:
            return str(v)
    return {
        "id": r[0], "scheme_id": r[1], "scheme_code": r[2],
        "run_type": r[3], "status": r[4],
        "params": _json_or_none(r[5]),
        "output": _json_or_none(r[6]),
        "file_path": r[7],
        "duration_ms": r[8],
        "error_message": r[9],
        "created_at": r[10].isoformat() if r[10] else None,
    }


# ===================== 情景集 =====================

@router.get("/scenarios")
async def list_scenarios(scheme_id: Optional[int] = None,
                          page: int = Query(1, ge=1),
                          page_size: int = Query(20, ge=1, le=100),
                          db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
    where = ["is_deleted=0"]
    params: dict = {"lim": page_size, "off": (page - 1) * page_size}
    if scheme_id:
        where.append("scheme_id=:s")
        params["s"] = scheme_id
    rows = db.execute(text(f"""
        SELECT id, scheme_id, scenario_code, last_run_id, scenario_type, file_path, n_scenarios,
               n_steps, n_maturities, seed, maturities_json, file_size_bytes,
               description, created_at,
               paths_blob IS NOT NULL AND LENGTH(paths_blob) > 0 AS has_blob,
               n_zeros, n_negatives
        FROM prcp_esg_scenario
        WHERE {' AND '.join(where)}
        ORDER BY id DESC
        LIMIT :lim OFFSET :off
    """), params).fetchall()
    total = db.execute(text(f"SELECT COUNT(*) FROM prcp_esg_scenario WHERE {' AND '.join(where)}"),
                       params).scalar() or 0
    items = []
    for r in rows:
        items.append({
            "id": r[0], "scheme_id": r[1], "scenario_code": r[2], "last_run_id": r[3],
            "scenario_type": r[4], "file_path": r[5],
            "n_scenarios": r[6], "n_steps": r[7], "n_maturities": r[8],
            "seed": r[9], "maturities_months": json.loads(r[10]) if r[10] else None,
            "file_size_bytes": r[11], "description": r[12],
            "created_at": r[13].isoformat() if r[13] else None,
            # B+D v2 字段
            "has_blob": bool(r[14]),  # paths_blob 是否非空
            "n_zeros": r[15] or 0,
            "n_negatives": r[16] or 0,
        })
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.get("/scenarios/{scenario_code}")
async def get_scenario(scenario_code: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(text("""
        SELECT id, scheme_id, scenario_code, last_run_id, scenario_type, file_path, n_scenarios,
               n_steps, n_maturities, seed, maturities_json, file_size_bytes,
               description, created_at,
               paths_blob IS NOT NULL AND LENGTH(paths_blob) > 0 AS has_blob,
               n_zeros, n_negatives
        FROM prcp_esg_scenario WHERE scenario_code=:sc AND is_deleted=0
    """), {"sc": scenario_code}).first()
    if not row:
        raise HTTPException(404, f"scenario {scenario_code} 不存在")
    return {
        "id": row[0], "scheme_id": row[1], "scenario_code": row[2], "last_run_id": row[3],
        "scenario_type": row[4], "file_path": row[5],
        "n_scenarios": row[6], "n_steps": row[7], "n_maturities": row[8],
        "seed": row[9], "maturities_months": json.loads(row[10]) if row[10] else None,
        "file_size_bytes": row[11], "description": row[12],
        "created_at": row[13].isoformat() if row[13] else None,
        # B+D v2 字段
        "has_blob": bool(row[14]),
        "n_zeros": row[15] or 0,
        "n_negatives": row[16] or 0,
    }


@router.get("/scenarios/{scenario_code}/stats")
async def get_scenario_stats(scenario_code: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取预计算的派生统计（前端展示免算）

    返回：
      - p10/p50/p90: (n_steps, n_maturities) 二维数组
      - final_mean/final_std/final_min/final_max: (n_maturities,) 一维数组
      - vol_per_maturity: (n_maturities,) 一维数组
      - n_zeros/n_negatives: 异常计数
    """
    row = db.execute(text("""
        SELECT n_scenarios, n_steps, n_maturities, seed, maturities_json,
               p10_json, p50_json, p90_json,
               final_mean_json, final_std_json, final_min_json, final_max_json,
               vol_per_maturity_json, n_zeros, n_negatives
        FROM prcp_esg_scenario
        WHERE scenario_code=:sc AND is_deleted=0
    """), {"sc": scenario_code}).first()
    if not row:
        raise HTTPException(404, f"scenario {scenario_code} 不存在")
    if row[5] is None:
        raise HTTPException(409, f"scenario {scenario_code} 没有预计算统计（旧数据请先迁移）")
    return {
        "scenario_code": scenario_code,
        "n_scenarios": row[0], "n_steps": row[1], "n_maturities": row[2],
        "seed": row[3], "maturities_months": json.loads(row[4]) if row[4] else None,
        "p10": json.loads(row[5]),
        "p50": json.loads(row[6]),
        "p90": json.loads(row[7]),
        "final_mean": json.loads(row[8]),
        "final_std": json.loads(row[9]),
        "final_min": json.loads(row[10]),
        "final_max": json.loads(row[11]),
        "vol_per_maturity": json.loads(row[12]),
        "n_zeros": row[13] or 0,
        "n_negatives": row[14] or 0,
    }


@router.get("/scenarios/{scenario_code}/download")
async def download_scenario(scenario_code: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """下载 .npz 文件
    B+D 方案：优先从 paths_blob 读取，缺失则回退到 file_path
    """
    from fastapi.responses import Response
    row = db.execute(text("""
        SELECT paths_blob, file_path, scenario_code FROM prcp_esg_scenario
        WHERE scenario_code=:sc AND is_deleted=0
    """), {"sc": scenario_code}).first()
    if not row:
        raise HTTPException(404, f"scenario {scenario_code} 不存在")
    paths_blob, file_path, sc_code = row[0], row[1], row[2]

    # 优先从 blob 读取
    if paths_blob is not None and len(paths_blob) > 0:
        return Response(
            content=paths_blob,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="scenario_{sc_code}.npz"',
                "Content-Length": str(len(paths_blob)),
            },
        )

    # 兼容旧场景（仅有 file_path）：从磁盘读取
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="scenario_{sc_code}.npz"',
                "Content-Length": str(len(data)),
            },
        )

    raise HTTPException(404, f"scenario {sc_code} 数据源不可用（blob 和 file_path 都为空）")


# ===================== 一键演示 =====================

@router.post("/case/run")
async def run_one_click_case(body: dict = {}, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """一键演示：自动创建 PRCP_ESG_DEMO_001 方案 + 跑三步"""
    uid = _uid(user)
    data_source = body.get("data_source", "ECB") if body else "ECB"
    code = "PRCP_ESG_DEMO_001"
    existing = db.execute(text(
        "SELECT id FROM prcp_esg_scheme WHERE scheme_code=:c AND is_deleted=0"
    ), {"c": code}).first()
    if existing:
        scheme_id = existing[0]
    else:
        scheme_id = db.execute(text("""
            INSERT INTO prcp_esg_scheme
            (scheme_code, scheme_name, description, data_source, start_date, end_date,
             n_factors, maturities_json, n_scenarios, n_steps, seed, status, created_by, updated_by)
            VALUES (:c, '一键案例（演示）', 'PRCP ESG 一键演示方案',
                    :ds, '2024-01-01', '2026-04-01',
                    3, :mj, 50, 24, 42, 'READY', :u, :u)
        """), {
            "c": code, "ds": data_source,
            "mj": json.dumps([1, 3, 6, 12, 24, 60, 84, 120, 240, 360]),
            "u": uid,
        }).lastrowid
        db.commit()

    # 跑三步
    try:
        pca_r = await scheme_fit_pca(scheme_id, EsgPcaRunIn(n_factors=3), db, user)
        hjm_r = await scheme_generate_hjm(
            scheme_id,
            EsgHjmRunIn(n_scenarios=50, n_steps=24, seed=42),
            db, user,
        )
        sc_r = await scheme_generate_scenarios(scheme_id, {}, db, user)
    except HTTPException as e:
        raise HTTPException(500, f"一键案例执行失败：{e.detail}")

    return {
        "scheme_id": scheme_id,
        "scheme_code": code,
        "pca_run_id": pca_r["run_id"],
        "hjm_run_id": hjm_r["run_id"],
        "scenario_run_id": sc_r["run_id"],
        "scenario_code": sc_r["scenario_code"],
        "sc_id": sc_r["sc_id"],
        "file_path": sc_r["file_path"],
    }


# ===================== Svensson 曲线 =====================

@router.get("/curves")
async def list_curves(source: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       page: int = Query(1, ge=1),
                       page_size: int = Query(50, ge=1, le=200),
                       db: Session = Depends(get_db),
                       user=Depends(get_current_user)):
    where = ["is_deleted=0"]
    params: dict = {"lim": page_size, "off": (page - 1) * page_size}
    if source:
        where.append("source=:s")
        params["s"] = source
    if start_date:
        where.append("curve_date>=:sd")
        params["sd"] = start_date
    if end_date:
        where.append("curve_date<=:ed")
        params["ed"] = end_date
    rows = db.execute(text(f"""
        SELECT id, curve_date, source, theta0, theta1, theta2, theta3, lambda1, lambda2,
               description, created_at
        FROM prcp_esg_curve_point
        WHERE {' AND '.join(where)}
        ORDER BY curve_date DESC, source
        LIMIT :lim OFFSET :off
    """), params).fetchall()
    total = db.execute(text(f"SELECT COUNT(*) FROM prcp_esg_curve_point WHERE {' AND '.join(where)}"),
                       params).scalar() or 0
    items = [{
        "id": r[0], "curve_date": r[1].isoformat() if r[1] else None,
        "source": r[2], "theta0": float(r[3]), "theta1": float(r[4]),
        "theta2": float(r[5]), "theta3": float(r[6]),
        "lambda1": float(r[7]), "lambda2": float(r[8]),
        "description": r[9],
        "created_at": r[10].isoformat() if r[10] else None,
    } for r in rows]
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.get("/curves/sources")
async def curve_sources(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT source, COUNT(*) AS n, MIN(curve_date) AS min_date, MAX(curve_date) AS max_date
        FROM prcp_esg_curve_point
        WHERE is_deleted=0
        GROUP BY source
    """)).fetchall()
    return {"items": [{
        "source": r[0],
        "count": int(r[1]),
        "min_date": r[2].isoformat() if r[2] else None,
        "max_date": r[3].isoformat() if r[3] else None,
    } for r in rows]}


@router.get("/curves/{curve_date}")
async def get_curve(curve_date: str,
                     source: Optional[str] = None,
                     db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    where = ["is_deleted=0", "curve_date=:d"]
    params: dict = {"d": curve_date}
    if source:
        where.append("source=:s")
        params["s"] = source
    rows = db.execute(text(f"""
        SELECT id, curve_date, source, theta0, theta1, theta2, theta3, lambda1, lambda2,
               raw_data_json, description, created_at
        FROM prcp_esg_curve_point
        WHERE {' AND '.join(where)}
    """), params).fetchall()
    if not rows:
        raise HTTPException(404, f"curve_date={curve_date} source={source} 未找到")
    items = []
    for r in rows:
        items.append({
            "id": r[0], "curve_date": r[1].isoformat() if r[1] else None,
            "source": r[2], "theta0": float(r[3]), "theta1": float(r[4]),
            "theta2": float(r[5]), "theta3": float(r[6]),
            "lambda1": float(r[7]), "lambda2": float(r[8]),
            "raw_data_json": json.loads(r[9]) if r[9] else None,
            "description": r[10],
            "created_at": r[11].isoformat() if r[11] else None,
        })
    return {"items": items}


@router.post("/curves")
async def upsert_curve(p: SvenssonCurveIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    try:
        rid = db.execute(text("""
            INSERT INTO prcp_esg_curve_point
            (curve_date, source, theta0, theta1, theta2, theta3, lambda1, lambda2,
             raw_data_json, description, created_by, updated_by)
            VALUES (:d, :s, :t0, :t1, :t2, :t3, :l1, :l2, :raw, :desc, :u, :u)
            ON DUPLICATE KEY UPDATE
              theta0=VALUES(theta0), theta1=VALUES(theta1), theta2=VALUES(theta2), theta3=VALUES(theta3),
              lambda1=VALUES(lambda1), lambda2=VALUES(lambda2),
              raw_data_json=VALUES(raw_data_json), description=VALUES(description), updated_by=VALUES(updated_by)
        """), {
            "d": p.curve_date, "s": p.source,
            "t0": p.theta0, "t1": p.theta1, "t2": p.theta2, "t3": p.theta3,
            "l1": p.lambda1, "l2": p.lambda2,
            "raw": json.dumps(p.raw_data_json) if p.raw_data_json else None,
            "desc": p.description, "u": uid,
        }).lastrowid
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"upsert 失败：{e}")
    return {"id": rid, "curve_date": p.curve_date, "source": p.source}


@router.post("/curves/bulk")
async def bulk_upsert_curves(p: SvenssonBulkIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    uid = _uid(user)
    n_success = 0
    n_fail = []
    for pt in p.points:
        try:
            db.execute(text("""
                INSERT INTO prcp_esg_curve_point
                (curve_date, source, theta0, theta1, theta2, theta3, lambda1, lambda2,
                 raw_data_json, description, created_by, updated_by)
                VALUES (:d, :s, :t0, :t1, :t2, :t3, :l1, :l2, :raw, :desc, :u, :u)
                ON DUPLICATE KEY UPDATE
                  theta0=VALUES(theta0), theta1=VALUES(theta1), theta2=VALUES(theta2), theta3=VALUES(theta3),
                  lambda1=VALUES(lambda1), lambda2=VALUES(lambda2),
                  raw_data_json=VALUES(raw_data_json), description=VALUES(description), updated_by=VALUES(updated_by)
            """), {
                "d": pt.curve_date, "s": pt.source,
                "t0": pt.theta0, "t1": pt.theta1, "t2": pt.theta2, "t3": pt.theta3,
                "l1": pt.lambda1, "l2": pt.lambda2,
                "raw": json.dumps(pt.raw_data_json) if pt.raw_data_json else None,
                "desc": pt.description, "u": uid,
            })
            n_success += 1
        except Exception as e:
            n_fail.append({"curve_date": pt.curve_date, "source": pt.source, "error": str(e)})
    db.commit()
    return {"success": n_success, "failed": len(n_fail), "fail_details": n_fail}


@router.post("/curves/{curve_date}/rates")
async def svensson_rates_endpoint(curve_date: str,
                                   p: SvenssonRatesIn,
                                   db: Session = Depends(get_db),
                                   user=Depends(get_current_user)):
    where = ["is_deleted=0", "curve_date=:d"]
    params: dict = {"d": curve_date}
    if p.source:
        where.append("source=:s")
        params["s"] = p.source
    rows = db.execute(text(f"""
        SELECT theta0, theta1, theta2, theta3, lambda1, lambda2, source
        FROM prcp_esg_curve_point WHERE {' AND '.join(where)}
    """), params).fetchall()
    if not rows:
        raise HTTPException(404, f"curve_date={curve_date} 未找到")

    results = []
    for r in rows:
        curve = SvenssonYieldCurve(
            theta0=float(r[0]), theta1=float(r[1]),
            theta2=float(r[2]), theta3=float(r[3]),
            lambda1=float(r[4]), lambda2=float(r[5]),
        )
        yields = curve.yields_pct(p.tenors)
        results.append({
            "source": r[6],
            "curve_date": curve_date,
            "tenors_months": p.tenors,
            "rates_pct": yields.tolist(),
            "rates_decimal": (yields / 100.0).tolist(),
        })
    return {"items": results}


# ===================== 缓存诊断（运维用）=====================

@router.get("/cache-info")
async def cache_info(user=Depends(get_current_user)):
    """返回 _Store 缓存诊断（运维用）"""
    return {
        "cached_schemes": list(_STORE.keys()),
        "total_cached": len(_STORE),
        "details": {sid: {
            "n_factors": g.n_factors,
            "n_maturities": g.n_maturities,
            "n_samples": g.n_samples,
            "pca_fitted": g._pca_fitted,
            "hjm_generated": g._hjm_generated,
            "seed": g.seed,
        } for sid, g in _STORE.items()},
    }