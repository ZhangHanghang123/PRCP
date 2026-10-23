"""新业务模拟方案管理 API — 方案 CRUD + 节点配置 + 期限占比子表

模块前缀：/prcp/api/sim

注意：
- 引擎计量相关 endpoint 已抽到 routers/engines.py
- 算法实现见 app.services.calculate_engine.new_business.engine
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/sim", tags=["新业务模拟方案"])


# ============================================================
# Schemas
# ============================================================
class SchemeIn(BaseModel):
    """方案新增/编辑入参（创建后 coa_scheme_id / data_date 不可改）"""
    scheme_code: str = Field(..., max_length=32)
    scheme_name: str = Field(..., max_length=64)
    coa_scheme_id: int
    data_date: str = Field(..., description="基准数据日期 YYYY-MM-DD（模拟起始月）")
    description: Optional[str] = None
    status: str = "ACTIVE"


class StatusToggleIn(BaseModel):
    status: str  # ACTIVE / INACTIVE


class TermRatioIn(BaseModel):
    term_value: int = Field(..., ge=1, le=60, description="期限值（1~60 月）")
    term_unit: str = Field("MONTH", description="期限单位（当前固定 MONTH）")
    business_ratio: float = Field(..., ge=0, le=100, description="业务占比（0~100）")
    interest_rate: float = Field(0.0, ge=0, le=100, description="新业务利率（%），0~100")
    sort_order: int = 0


class NodeConfigIn(BaseModel):
    """节点配置保存入参（覆盖子表）"""
    coa_node_id: int
    annual_growth_rate: float = Field(0.0, ge=0, le=100, description="年化目标增长率（%）")
    term_unit: str = "MONTH"
    is_model_calc: int = Field(2, ge=1, le=2, description="是否模型测算 (1=是, 2=否)")
    rhythm_type: int = Field(1, ge=1, le=2, description="节奏配置类型 (1=线性, 2=自定义)")
    remark: Optional[str] = None
    ratios: List[TermRatioIn] = []


class RhythmWeightIn(BaseModel):
    """节奏配置单月权重入参"""
    month_no: int = Field(..., ge=1, le=12, description="月份序号（1~12）")
    weight: float = Field(0.0, ge=0, le=100, description="权重（%）")
    remark: Optional[str] = None


class RhythmSaveIn(BaseModel):
    """节奏配置保存入参（12 个月权重，整体覆盖）"""
    weights: List[RhythmWeightIn] = Field(..., description="12 个月权重列表")

    @field_validator("weights")
    @classmethod
    def _check_12_months(cls, v: List[RhythmWeightIn]) -> List[RhythmWeightIn]:
        months = sorted({w.month_no for w in v})
        if months != list(range(1, 13)):
            raise ValueError("必须提供 1~12 月共 12 个月的权重配置")
        total = sum(w.weight for w in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"12 个月权重之和必须 = 100%，当前 = {total:.4f}%")
        return v


class GrowthIn(BaseModel):
    """新业务增长配置入参（5 年分期增长参数）

    增长方式 growth_type（字典 PRCP_GROWTH_TYPE）：
      1 = 目标增长百分比（单位 %）
      2 = 目标增长绝对值（单位 金额：万元 / 亿元）
      3 = 增长百分比（单位 %）
      4 = 增长值（单位 金额：万元 / 亿元）
    """
    growth_type: int = Field(1, ge=1, le=4, description="增长方式 (1=目标增长百分比 2=目标增长绝对值 3=增长百分比 4=增长值)")
    year1_value: float = Field(0.0, description="第 1 年增长参数")
    year2_value: float = Field(0.0, description="第 2 年增长参数")
    year3_value: float = Field(0.0, description="第 3 年增长参数")
    year4_value: float = Field(0.0, description="第 4 年增长参数")
    year5_value: float = Field(0.0, description="第 5 年增长参数")
    amount_unit: Optional[str] = Field(None, description="绝对值单位 (WAN=万元 / YI=亿元)，growth_type=2/4 生效")
    remark: Optional[str] = None


# ============================================================
# 工具：拿 user_id
# ============================================================
def _uid(user) -> int:
    return user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)


# ============================================================
# 1. 账户册方案下拉（参数配置页用）
# ============================================================
@router.get("/coa-schemes")
async def list_coa_schemes(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回 ACTIVE + 未删除的账户册方案（供前端方案下拉）"""
    rows = db.execute(
        text("""SELECT id, scheme_code, scheme_name, status, node_count
                FROM prcp_coa_scheme
                WHERE is_deleted=0 AND status='ACTIVE'
                ORDER BY scheme_code"""),
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_code": r[1], "scheme_name": r[2],
                "status": r[3], "node_count": r[4] or 0,
            } for r in rows
        ]
    }


# ============================================================
# 2. 账户册节点树
# ============================================================
@router.get("/coa-tree")
async def coa_tree(
    coa_scheme_id: int = Query(...),
    sim_scheme_id: int = Query(None, description="方案 id（用于标记哪些节点已有配置）"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回某账户册方案的节点树（仅未删除 + ACTIVE）

    传 sim_scheme_id 时，每个节点带 has_config 标记（该节点在该方案下是否已有配置），
    前端据此把「已配置」的末级节点标绿。
    """
    rows = db.execute(
        text("""SELECT id, node_code, node_name, parent_id, node_level, node_type,
                       path, sort_order, status
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0
                ORDER BY sort_order, path"""),
        {"s": coa_scheme_id},
    ).fetchall()

    # 已配置节点集合（该 sim 方案下存在未删除的 node_config）
    configured: set = set()
    if sim_scheme_id is not None:
        cfg_rows = db.execute(
            text("""SELECT DISTINCT coa_node_id
                    FROM prcp_sim_node_config
                    WHERE scheme_id=:sid AND is_deleted=0"""),
            {"sid": sim_scheme_id},
        ).fetchall()
        configured = {r[0] for r in cfg_rows}

    by_path: dict = {}
    for r in rows:
        by_path[r[6]] = {
            "key": str(r[0]),
            "title": f"{r[2]} ({r[1]})",
            "code": r[1], "name": r[2],
            "id": r[0], "level": r[4], "type": r[5],
            "path": r[6], "sort_order": r[7], "status": r[8],
            "isLeaf": False,  # 默认 False，后面如果有子节点则 True；这里前端通过 children 判断
            "has_config": r[0] in configured,
            "children": [],
        }

    roots = []
    for node in by_path.values():
        path = node["path"]
        last_slash = path[:-1].rfind("/") + 1
        parent_path = path[:last_slash]
        parent = by_path.get(parent_path)
        if parent:
            parent["children"].append(node)
            parent["isLeaf"] = False
        else:
            roots.append(node)

    # 标记叶子（无 children 的节点）
    def _mark_leaf(nodes):
        for n in nodes:
            if not n["children"]:
                n["isLeaf"] = True
            else:
                _mark_leaf(n["children"])

    _mark_leaf(roots)
    return {
        "scheme_id": coa_scheme_id,
        "items": roots,
        "total": len(by_path),
        "configured_count": len(configured),
    }


# ============================================================
# 3. 节点基础信息 + 当前余额
# ============================================================
@router.get("/node-info/{coa_node_id}")
async def node_info(
    coa_node_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回节点基础信息 + 最新一条余额数据"""
    node = db.execute(
        text("""SELECT n.id, n.scheme_id, n.node_code, n.node_name, n.node_level, n.node_type,
                       n.path, n.parent_id, n.status,
                       s.scheme_code, s.scheme_name
                FROM prcp_coa_node n
                JOIN prcp_coa_scheme s ON s.id = n.scheme_id
                WHERE n.id=:id AND n.is_deleted=0"""),
        {"id": coa_node_id},
    ).first()
    if not node:
        raise HTTPException(404, "节点不存在")

    # 最新余额（取 data_date 最大的一行）
    bal = db.execute(
        text("""SELECT data_date, current_amount
                FROM prcp_data_balance
                WHERE coa_node_id=:id AND is_deleted=0
                ORDER BY data_date DESC LIMIT 1"""),
        {"id": coa_node_id},
    ).first()
    return {
        "id": node[0], "scheme_id": node[1], "node_code": node[2], "node_name": node[3],
        "node_level": node[4], "node_type": node[5], "path": node[6], "parent_id": node[7],
        "status": node[8], "coa_scheme_code": node[9], "coa_scheme_name": node[10],
        "current_balance_date": bal[0].isoformat() if bal and bal[0] else None,
        "current_balance_amount": float(bal[1]) if bal and bal[1] is not None else 0.0,
    }


# ============================================================
# 4. 方案列表
# ============================================================
@router.get("/schemes")
async def list_schemes(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    coa_scheme_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列出所有未删除的模拟方案"""
    where = ["s.is_deleted=0"]
    params = {}
    if keyword:
        where.append("(s.scheme_code LIKE :kw OR s.scheme_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if status:
        where.append("s.status=:st")
        params["st"] = status
    if coa_scheme_id is not None:
        where.append("s.coa_scheme_id=:cs")
        params["cs"] = coa_scheme_id

    rows = db.execute(
        text(f"""SELECT s.id, s.scheme_code, s.scheme_name, s.coa_scheme_id,
                       s.data_date, s.description, s.config_node_count, s.status,
                       s.created_at, s.updated_at,
                       cs.scheme_code AS coa_code, cs.scheme_name AS coa_name
                FROM prcp_sim_scheme s
                LEFT JOIN prcp_coa_scheme cs ON cs.id = s.coa_scheme_id
                WHERE {' AND '.join(where)}
                ORDER BY s.id DESC"""),
        params,
    ).fetchall()
    return {
        "items": [
            {
                "id": r[0], "scheme_code": r[1], "scheme_name": r[2],
                "coa_scheme_id": r[3], "data_date": r[4].isoformat() if r[4] else None,
                "description": r[5],
                "config_node_count": r[6] or 0, "status": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
                "updated_at": r[9].isoformat() if r[9] else None,
                "coa_scheme_code": r[10], "coa_scheme_name": r[11],
            } for r in rows
        ]
    }


@router.post("/schemes")
async def create_scheme(
    p: SchemeIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """新建方案（coa_scheme_id 必须存在；data_date 必填 YYYY-MM-DD）"""
    uid = _uid(user)
    # 校验账户册方案存在
    coa = db.execute(
        text("SELECT id FROM prcp_coa_scheme WHERE id=:id AND is_deleted=0 AND status='ACTIVE'"),
        {"id": p.coa_scheme_id},
    ).first()
    if not coa:
        raise HTTPException(400, "关联账户册方案不存在或已停用")
    # 校验 data_date 格式
    try:
        from datetime import datetime
        datetime.strptime(p.data_date, "%Y-%m-%d")
    except Exception:
        raise HTTPException(400, f"data_date 格式错误：应为 YYYY-MM-DD，实际 {p.data_date!r}")
    try:
        rid = db.execute(
            text("""INSERT INTO prcp_sim_scheme
                (scheme_code, scheme_name, coa_scheme_id, data_date, description, status, created_by, updated_by)
                VALUES (:c, :n, :cs, :dd, :d, :st, :u, :u)"""),
            {"c": p.scheme_code, "n": p.scheme_name, "cs": p.coa_scheme_id,
             "dd": p.data_date, "d": p.description, "st": p.status, "u": uid},
        ).lastrowid
    except Exception as e:
        msg = str(e)
        if "Duplicate" in msg or "uk_scheme_code" in msg:
            raise HTTPException(400, f"方案编码已存在：{p.scheme_code}")
        raise HTTPException(400, f"创建失败：{e}")
    return {"id": rid, "scheme_code": p.scheme_code, "scheme_name": p.scheme_name, "data_date": p.data_date}


@router.put("/schemes/{sid}")
async def update_scheme(
    sid: int,
    p: SchemeIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """更新方案（coa_scheme_id / data_date 创建后不可改，应用层忽略）"""
    uid = _uid(user)
    # 校验方案存在 + 取当前 coa_scheme_id + data_date
    cur = db.execute(
        text("SELECT coa_scheme_id, data_date FROM prcp_sim_scheme WHERE id=:id AND is_deleted=0"),
        {"id": sid},
    ).first()
    if not cur:
        raise HTTPException(404, "方案不存在")

    actual_coa = cur[0]
    actual_data_date = cur[1].isoformat() if cur[1] else None
    try:
        result = db.execute(
            text("""UPDATE prcp_sim_scheme
                SET scheme_code=:c, scheme_name=:n, description=:d,
                    status=:st, updated_by=:u
                WHERE id=:id AND is_deleted=0"""),
            {"c": p.scheme_code, "n": p.scheme_name, "d": p.description,
             "st": p.status, "u": uid, "id": sid},
        )
        if result.rowcount == 0:
            raise HTTPException(404, "方案不存在")
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "Duplicate" in msg or "uk_scheme_code" in msg:
            raise HTTPException(400, f"方案编码已存在：{p.scheme_code}")
        raise HTTPException(400, f"更新失败：{e}")
    return {
        "ok": True,
        "coa_scheme_id_locked": actual_coa,
        "data_date_locked": actual_data_date,
    }


@router.patch("/schemes/{sid}/status")
async def toggle_scheme_status(
    sid: int,
    p: StatusToggleIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """切换方案状态 ACTIVE/INACTIVE"""
    if p.status not in ("ACTIVE", "INACTIVE"):
        raise HTTPException(400, "status 必须为 ACTIVE/INACTIVE")
    uid = _uid(user)
    result = db.execute(
        text("UPDATE prcp_sim_scheme SET status=:st, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"st": p.status, "u": uid, "id": sid},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "方案不存在")
    return {"ok": True}


@router.delete("/schemes/{sid}")
async def delete_scheme(
    sid: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """软删方案 + 级联软删其下节点配置和期限占比"""
    uid = _uid(user)
    # 1) 软删方案
    r = db.execute(
        text("UPDATE prcp_sim_scheme SET is_deleted=1, updated_by=:u WHERE id=:id AND is_deleted=0"),
        {"u": uid, "id": sid},
    ).rowcount
    if r == 0:
        raise HTTPException(404, "方案不存在")
    # 2) 软删节点配置
    cn = db.execute(
        text("UPDATE prcp_sim_node_config SET is_deleted=1, updated_by=:u "
             "WHERE scheme_id=:id AND is_deleted=0"),
        {"u": uid, "id": sid},
    ).rowcount
    # 3) 软删期限占比（通过 config_id 关联）
    tr = db.execute(
        text("""UPDATE prcp_sim_term_ratio t
                JOIN prcp_sim_node_config c ON c.id = t.config_id
                SET t.is_deleted=1, t.updated_by=:u
                WHERE c.scheme_id=:id AND t.is_deleted=0"""),
        {"u": uid, "id": sid},
    ).rowcount
    # 3.1) 软删节奏配置（通过 config_id 关联）
    rh = db.execute(
        text("""UPDATE prcp_sim_rhythm r
                JOIN prcp_sim_node_config c ON c.id = r.config_id
                SET r.is_deleted=1, r.updated_by=:u
                WHERE c.scheme_id=:id AND r.is_deleted=0"""),
        {"u": uid, "id": sid},
    ).rowcount
    # 3.2) 软删新业务增长配置（通过 config_id 关联）
    gc = db.execute(
        text("""UPDATE prcp_sim_growth_config g
                JOIN prcp_sim_node_config c ON c.id = g.config_id
                SET g.is_deleted=1, g.updated_by=:u
                WHERE c.scheme_id=:id AND g.is_deleted=0"""),
        {"u": uid, "id": sid},
    ).rowcount
    return {
        "ok": True, "deleted_configs": cn,
        "deleted_ratios": tr, "deleted_rhythms": rh,
        "deleted_growths": gc,
    }


# ============================================================
# 5. 节点配置 + 期限占比子表
# ============================================================
@router.get("/node-config")
async def get_node_config(
    scheme_id: int = Query(...),
    coa_node_id: int = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取某个节点在该方案下的配置 + 期限占比子表"""
    # 取方案 data_date（用于配置页展示）
    sch = db.execute(
        text("SELECT data_date FROM prcp_sim_scheme WHERE id=:id AND is_deleted=0"),
        {"id": scheme_id},
    ).first()
    scheme_data_date = sch[0].isoformat() if sch and sch[0] else None

    cfg = db.execute(
        text("""SELECT id, scheme_id, coa_node_id, coa_node_code,
                       annual_growth_rate, term_unit, term_count, remark,
                       is_model_calc, rhythm_type
                FROM prcp_sim_node_config
                WHERE scheme_id=:s AND coa_node_id=:n AND is_deleted=0"""),
        {"s": scheme_id, "n": coa_node_id},
    ).first()
    if not cfg:
        return {
            "exists": False, "config": None, "ratios": [], "rhythm": [],
            "growth": {
                "exists": False, "growth_type": 1,
                "year1_value": 0.0, "year2_value": 0.0, "year3_value": 0.0,
                "year4_value": 0.0, "year5_value": 0.0,
                "unit": "%", "amount_unit": None, "remark": None,
            },
            "scheme_data_date": scheme_data_date,
        }
    rows = db.execute(
        text("""SELECT id, term_value, term_unit, business_ratio, interest_rate, sort_order, remark
                FROM prcp_sim_term_ratio
                WHERE config_id=:cid AND is_deleted=0
                ORDER BY sort_order, term_value"""),
        {"cid": cfg[0]},
    ).fetchall()

    # 节奏配置（12 个月权重）
    rhythm_rows = db.execute(
        text("""SELECT month_no, month_label, weight, remark
                FROM prcp_sim_rhythm
                WHERE config_id=:cid AND is_deleted=0
                ORDER BY month_no"""),
        {"cid": cfg[0]},
    ).fetchall()

    # 新业务增长配置（增长方式 + 5 年参数）
    growth = _read_growth(db, cfg[0])

    # 无节奏数据 → 默认线性（12 个月均匀 100/12）
    if not rhythm_rows:
        rhythm_rows = [(m, f"{m}月", round(100.0 / 12, 4), "默认线性（12 个月均匀）")
                       for m in range(1, 13)]

    return {
        "exists": True,
        "config": {
            "id": cfg[0], "scheme_id": cfg[1], "coa_node_id": cfg[2], "coa_node_code": cfg[3],
            "annual_growth_rate": float(cfg[4]) if cfg[4] is not None else 0.0,
            "term_unit": cfg[5], "term_count": cfg[6] or 0, "remark": cfg[7],
            "is_model_calc": int(cfg[8]) if cfg[8] is not None else 2,
            "rhythm_type": int(cfg[9]) if cfg[9] is not None else 1,
        },
        "ratios": [
            {
                "id": r[0], "term_value": r[1], "term_unit": r[2],
                "business_ratio": float(r[3]) if r[3] is not None else 0.0,
                "interest_rate": float(r[4]) if r[4] is not None else 0.0,
                "sort_order": r[5], "remark": r[6],
            } for r in rows
        ],
        "rhythm": [
            {
                "month_no": r[0], "month_label": r[1],
                "weight": float(r[2]) if r[2] is not None else 0.0,
                "remark": r[3],
            } for r in rhythm_rows
        ],
        "growth": growth,
        "scheme_data_date": scheme_data_date,
    }


@router.post("/node-config")
async def save_node_config(
    scheme_id: int = Query(..., description="方案 id"),
    p: NodeConfigIn = ...,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """保存节点配置（覆盖期限占比子表）

    流程：
      1) 应用层校验：业务占比之和必须=100%（允许误差 0.01）
      2) 校验节点存在
      3) UPSERT 节点配置（软删除复活 + 新建）
      4) 软删旧占比 + 插入新占比
      5) 更新 scheme.config_node_count
    """
    uid = _uid(user)

    # 1) 校验：业务占比之和必须=100%
    if not p.ratios:
        raise HTTPException(400, "期限占比子表不能为空，至少 1 行")
    total = sum(r.business_ratio for r in p.ratios)
    if abs(total - 100.0) > 0.01:
        raise HTTPException(400, f"业务占比之和必须为 100%，当前 = {total:.4f}%")

    # 2) 校验：节点存在
    node = db.execute(
        text("SELECT id, node_code FROM prcp_coa_node WHERE id=:id AND is_deleted=0"),
        {"id": p.coa_node_id},
    ).first()
    if not node:
        raise HTTPException(404, "节点不存在")

    # 3) 校验：方案存在
    sch = db.execute(
        text("SELECT id FROM prcp_sim_scheme WHERE id=:id AND is_deleted=0"),
        {"id": scheme_id},
    ).first()
    if not sch:
        raise HTTPException(404, "方案不存在")

    # 4) UPSERT 节点配置
    # 先找当前 scheme 下该节点的软删除+非删除记录
    cur = db.execute(
        text("""SELECT id, is_deleted FROM prcp_sim_node_config
                WHERE scheme_id=:s AND coa_node_id=:n"""),
        {"s": scheme_id, "n": p.coa_node_id},
    ).first()

    if cur:
        # 复活或更新
        # 注意：annual_growth_rate 列是 decimal(8,4)（上限 9999.9999），
        #   绝对值类增长方式（growth_type 2/4）的 year1_value 可能超上限，
        #   写入会溢出，故此处做上限保护（超限时保留原值不写）。
        legacy_rate = p.annual_growth_rate if p.annual_growth_rate <= 9999.9999 else None
        if cur[1] == 0:
            # 非删除 → 直接更新
            cfg_id = cur[0]
            if legacy_rate is None:
                db.execute(
                    text("""UPDATE prcp_sim_node_config SET
                        term_unit=:tu, remark=:rm,
                        is_model_calc=:imc, rhythm_type=:rt, updated_by=:u
                        WHERE id=:id"""),
                    {"tu": p.term_unit, "rm": p.remark,
                     "imc": p.is_model_calc, "rt": p.rhythm_type,
                     "u": uid, "id": cfg_id},
                )
            else:
                db.execute(
                    text("""UPDATE prcp_sim_node_config SET
                        annual_growth_rate=:r, term_unit=:tu, remark=:rm,
                        is_model_calc=:imc, rhythm_type=:rt, updated_by=:u
                        WHERE id=:id"""),
                    {"r": legacy_rate, "tu": p.term_unit, "rm": p.remark,
                     "imc": p.is_model_calc, "rt": p.rhythm_type,
                     "u": uid, "id": cfg_id},
                )
        else:
            # 软删除 → 复活
            cfg_id = cur[0]
            if legacy_rate is None:
                db.execute(
                    text("""UPDATE prcp_sim_node_config SET
                        is_deleted=0, term_unit=:tu, remark=:rm,
                        is_model_calc=:imc, rhythm_type=:rt, updated_by=:u
                        WHERE id=:id"""),
                    {"tu": p.term_unit, "rm": p.remark,
                     "imc": p.is_model_calc, "rt": p.rhythm_type,
                     "u": uid, "id": cfg_id},
                )
            else:
                db.execute(
                    text("""UPDATE prcp_sim_node_config SET
                        is_deleted=0, annual_growth_rate=:r, term_unit=:tu, remark=:rm,
                        is_model_calc=:imc, rhythm_type=:rt, updated_by=:u
                        WHERE id=:id"""),
                    {"r": legacy_rate, "tu": p.term_unit, "rm": p.remark,
                     "imc": p.is_model_calc, "rt": p.rhythm_type,
                     "u": uid, "id": cfg_id},
                )
    else:
        # 新建
        cfg_id = db.execute(
            text("""INSERT INTO prcp_sim_node_config
                (scheme_id, coa_node_id, coa_node_code, annual_growth_rate,
                 term_unit, term_count, remark, is_model_calc, rhythm_type,
                 created_by, updated_by)
                VALUES (:s, :n, :nc, :r, :tu, 0, :rm, :imc, :rt, :u, :u)"""),
            {"s": scheme_id, "n": p.coa_node_id, "nc": node[1],
             "r": legacy_rate if legacy_rate is not None else 0,
             "tu": p.term_unit, "rm": p.remark,
             "imc": p.is_model_calc, "rt": p.rhythm_type, "u": uid},
        ).lastrowid

    # 5) 软删旧占比
    db.execute(
        text("UPDATE prcp_sim_term_ratio SET is_deleted=1, updated_by=:u "
             "WHERE config_id=:cid AND is_deleted=0"),
        {"u": uid, "cid": cfg_id},
    )
    # 6) 插入新占比
    for idx, r in enumerate(p.ratios):
        # 强制 term_unit = MONTH（应用层兜底）
        tu = r.term_unit or "MONTH"
        if tu != "MONTH":
            raise HTTPException(400, "期限单位当前仅支持 MONTH（月）")
        db.execute(
            text("""INSERT INTO prcp_sim_term_ratio
                (config_id, term_value, term_unit, business_ratio, interest_rate, sort_order, remark, created_by, updated_by)
                VALUES (:cid, :tv, :tu, :br, :ir, :so, NULL, :u, :u)"""),
            {"cid": cfg_id, "tv": r.term_value, "tu": tu,
             "br": r.business_ratio, "ir": r.interest_rate,
             "so": r.sort_order or (idx + 1), "u": uid},
        )
    # 7) 更新 term_count + config_node_count
    db.execute(
        text("UPDATE prcp_sim_node_config SET term_count=:tc, updated_by=:u WHERE id=:id"),
        {"tc": len(p.ratios), "u": uid, "id": cfg_id},
    )
    db.execute(
        text("""UPDATE prcp_sim_scheme s
                SET config_node_count = (
                  SELECT COUNT(*) FROM prcp_sim_node_config c
                  WHERE c.scheme_id=s.id AND c.is_deleted=0
                ), updated_by=:u
                WHERE id=:id"""),
        {"u": uid, "id": scheme_id},
    )

    return {
        "ok": True, "config_id": cfg_id, "term_count": len(p.ratios),
        "total_ratio": round(total, 4),
    }


# ============================================================
# ============================================================
# 新业务增长配置 CRUD（增长方式 + 5 年分期增长参数）
# ============================================================
# 增长方式 → 单位映射：1/3 用 %，2/4 用绝对值
_GROWTH_UNIT_BY_TYPE = {1: "%", 2: "ABS", 3: "%", 4: "ABS"}


def _read_growth(db, cfg_id: int):
    """读某节点配置的增长配置（无数据 → 返回默认值：目标增长百分比 + 5 年全 0）"""
    g = db.execute(
        text("""SELECT growth_type, year1_value, year2_value, year3_value,
                      year4_value, year5_value, unit, amount_unit, remark, id
                FROM prcp_sim_growth_config
                WHERE config_id=:cid AND is_deleted=0"""),
        {"cid": cfg_id},
    ).first()
    if not g:
        return {
            "exists": False,
            "growth_type": 1,
            "year1_value": 0.0, "year2_value": 0.0, "year3_value": 0.0,
            "year4_value": 0.0, "year5_value": 0.0,
            "unit": "%", "amount_unit": None, "remark": None,
        }
    return {
        "exists": True,
        "id": g[9],
        "growth_type": int(g[0]) if g[0] is not None else 1,
        "year1_value": float(g[1]) if g[1] is not None else 0.0,
        "year2_value": float(g[2]) if g[2] is not None else 0.0,
        "year3_value": float(g[3]) if g[3] is not None else 0.0,
        "year4_value": float(g[4]) if g[4] is not None else 0.0,
        "year5_value": float(g[5]) if g[5] is not None else 0.0,
        "unit": g[6] or "%",
        "amount_unit": g[7],
        "remark": g[8],
    }


@router.get("/growth/{cfg_id}")
async def get_growth(
    cfg_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """读取某节点配置的新业务增长配置（增长方式 + 5 年增长参数）

    - 无数据 → 返回默认值：growth_type=1（目标增长百分比），5 年参数全 0
    - 一并返回关联维度（方案编码 / 账户册节点编码）
    """
    cfg = db.execute(
        text("""SELECT c.id, c.scheme_id, s.scheme_code, s.scheme_name,
                      c.coa_node_id, c.coa_node_code, n.node_name
                FROM prcp_sim_node_config c
                LEFT JOIN prcp_sim_scheme s ON s.id = c.scheme_id AND s.is_deleted = 0
                LEFT JOIN prcp_coa_node  n ON n.id = c.coa_node_id AND n.is_deleted = 0
                WHERE c.id=:id AND c.is_deleted=0"""),
        {"id": cfg_id},
    ).first()
    if not cfg:
        raise HTTPException(404, "节点配置不存在")

    growth = _read_growth(db, cfg_id)
    growth.update({
        "config_id": cfg_id,
        "scheme_id": cfg[1], "scheme_code": cfg[2], "scheme_name": cfg[3],
        "coa_node_id": cfg[4], "coa_node_code": cfg[5], "coa_node_name": cfg[6],
    })
    return growth


@router.put("/growth/{cfg_id}")
async def save_growth(
    cfg_id: int,
    p: GrowthIn = ...,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """保存新业务增长配置（增长方式 + 5 年参数，UPSERT 覆盖）

    - 增长方式 1/3 → unit = '%'
    - 增长方式 2/4 → unit = 'ABS'（需配 amount_unit：WAN=万元 / YI=亿元）
    - 写入后同步更新 prcp_sim_node_config.annual_growth_rate = year1_value
      （保持向后兼容，老字段作为 year1 的镜像）
    """
    uid = _uid(user)

    # 1) 校验 config 存在 + 取关联维度
    cfg = db.execute(
        text("""SELECT c.id, c.scheme_id, s.scheme_code, s.scheme_name,
                      c.coa_node_id, c.coa_node_code, n.node_name
                FROM prcp_sim_node_config c
                LEFT JOIN prcp_sim_scheme s ON s.id = c.scheme_id AND s.is_deleted = 0
                LEFT JOIN prcp_coa_node  n ON n.id = c.coa_node_id AND n.is_deleted = 0
                WHERE c.id=:id AND c.is_deleted=0"""),
        {"id": cfg_id},
    ).first()
    if not cfg:
        raise HTTPException(404, "节点配置不存在")

    # 2) 绝对值方式必须指定金额单位
    unit = _GROWTH_UNIT_BY_TYPE.get(p.growth_type, "%")
    amount_unit = p.amount_unit
    if unit == "ABS" and not amount_unit:
        amount_unit = "WAN"  # 默认万元
    if unit == "%":
        amount_unit = None

    # 3) UPSERT（UNIQUE KEY uk_config 保证 config_id 唯一）
    exists = db.execute(
        text("SELECT id FROM prcp_sim_growth_config WHERE config_id=:cid"),
        {"cid": cfg_id},
    ).first()
    if exists:
        db.execute(
            text("""UPDATE prcp_sim_growth_config SET
                    growth_type=:gt,
                    year1_value=:y1, year2_value=:y2, year3_value=:y3,
                    year4_value=:y4, year5_value=:y5,
                    unit=:u, amount_unit=:au, remark=:rm,
                    is_deleted=0, updated_by=:uid
                WHERE config_id=:cid"""),
            {"gt": p.growth_type,
             "y1": p.year1_value, "y2": p.year2_value, "y3": p.year3_value,
             "y4": p.year4_value, "y5": p.year5_value,
             "u": unit, "au": amount_unit, "rm": p.remark,
             "uid": uid, "cid": cfg_id},
        )
        gid = exists[0]
        action = "updated"
    else:
        gid = db.execute(
            text("""INSERT INTO prcp_sim_growth_config
                    (scheme_id, scheme_code, scheme_name,
                     coa_node_id, coa_node_code, coa_node_name,
                     config_id, growth_type,
                     year1_value, year2_value, year3_value, year4_value, year5_value,
                     unit, amount_unit, remark, is_deleted, created_by, updated_by)
                    VALUES (:sid, :sc, :sn, :nid, :nc, :nn, :cid, :gt,
                            :y1, :y2, :y3, :y4, :y5,
                            :u, :au, :rm, 0, :uid, :uid)"""),
            {"sid": cfg[1], "sc": cfg[2], "sn": cfg[3],
             "nid": cfg[4], "nc": cfg[5], "nn": cfg[6],
             "cid": cfg_id, "gt": p.growth_type,
             "y1": p.year1_value, "y2": p.year2_value, "y3": p.year3_value,
             "y4": p.year4_value, "y5": p.year5_value,
             "u": unit, "au": amount_unit, "rm": p.remark, "uid": uid},
        ).lastrowid
        action = "created"

    # 4) 同步老字段 annual_growth_rate = year1_value
    #    注意：annual_growth_rate 列是 decimal(8,4)（上限 9999.9999），
    #    只有「百分比」类增长方式（growth_type 1/3）才同步；
    #    绝对值类（2/4）数值可能超上限，同步会溢出，故不同步。
    if unit == "%":
        db.execute(
            text("UPDATE prcp_sim_node_config SET annual_growth_rate=:y1, updated_by=:uid WHERE id=:id"),
            {"y1": p.year1_value, "uid": uid, "id": cfg_id},
        )

    return {
        "ok": True, "action": action, "growth_id": gid, "config_id": cfg_id,
        "growth_type": p.growth_type, "unit": unit, "amount_unit": amount_unit,
        "year1_value": p.year1_value, "year2_value": p.year2_value,
        "year3_value": p.year3_value, "year4_value": p.year4_value,
        "year5_value": p.year5_value,
    }


@router.delete("/growth/{cfg_id}")
async def delete_growth(
    cfg_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """删除增长配置（软删），下次 GET 返回默认值"""
    uid = _uid(user)
    r = db.execute(
        text("UPDATE prcp_sim_growth_config SET is_deleted=1, updated_by=:uid "
             "WHERE config_id=:cid AND is_deleted=0"),
        {"uid": uid, "cid": cfg_id},
    ).rowcount
    return {"ok": True, "deleted": r}


# ============================================================
# 节奏配置 CRUD（12 个月权重）
# ============================================================
@router.get("/rhythm/{cfg_id}")
async def get_rhythm(
    cfg_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """读取某节点配置的 12 个月节奏权重

    - 若 prcp_sim_rhythm 无数据 → 返回默认线性（12 个月均匀 100/12）
    - 一并返回 rhythm_type（1=线性 2=自定义）
    """
    # 1) 校验 config 存在
    cfg = db.execute(
        text("""SELECT id, scheme_id, coa_node_id, coa_node_code, rhythm_type
                FROM prcp_sim_node_config WHERE id=:id AND is_deleted=0"""),
        {"id": cfg_id},
    ).first()
    if not cfg:
        raise HTTPException(404, "节点配置不存在")

    # 2) 读 12 个月权重
    rows = db.execute(
        text("""SELECT month_no, month_label, weight, remark
                FROM prcp_sim_rhythm
                WHERE config_id=:cid AND is_deleted=0
                ORDER BY month_no"""),
        {"cid": cfg_id},
    ).fetchall()

    rhythm_type = int(cfg[4]) if cfg[4] is not None else 1

    if not rows:
        # 默认线性：12 个月均匀
        items = [{
            "month_no": m, "month_label": f"{m}月",
            "weight": round(100.0 / 12, 4),
            "remark": "默认线性（12 个月均匀）",
        } for m in range(1, 13)]
        return {
            "config_id": cfg_id, "rhythm_type": rhythm_type,
            "exists": False, "is_default_linear": True,
            "items": items, "total_weight": 100.0,
        }

    items = [{
        "month_no": r[0], "month_label": r[1],
        "weight": float(r[2]) if r[2] is not None else 0.0,
        "remark": r[3],
    } for r in rows]
    total = round(sum(i["weight"] for i in items), 4)
    return {
        "config_id": cfg_id, "rhythm_type": rhythm_type,
        "exists": True, "is_default_linear": False,
        "items": items, "total_weight": total,
    }


@router.put("/rhythm/{cfg_id}")
async def save_rhythm(
    cfg_id: int,
    p: RhythmSaveIn = ...,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """保存 12 个月节奏权重（整体覆盖）

    校验：
      1) 必须提供 1~12 月共 12 项（Pydantic validator 已校验）
      2) 12 月权重之和必须 = 100%（容差 0.01，Pydantic validator 已校验）
    保存后自动把 rhythm_type 置为 2（自定义）
    """
    uid = _uid(user)

    # 1) 校验 config 存在
    cfg = db.execute(
        text("""SELECT id, scheme_id, coa_node_id
                FROM prcp_sim_node_config WHERE id=:id AND is_deleted=0"""),
        {"id": cfg_id},
    ).first()
    if not cfg:
        raise HTTPException(404, "节点配置不存在")

    # 2) 二次校验（防绕过 Pydantic）
    total = sum(w.weight for w in p.weights)
    if abs(total - 100.0) > 0.01:
        raise HTTPException(400, f"12 个月权重之和必须 = 100%，当前 = {total:.4f}%")

    # 3) 软删旧节奏数据
    db.execute(
        text("UPDATE prcp_sim_rhythm SET is_deleted=1, updated_by=:u "
             "WHERE config_id=:cid AND is_deleted=0"),
        {"u": uid, "cid": cfg_id},
    )

    # 4) 插入新 12 个月数据
    for w in sorted(p.weights, key=lambda x: x.month_no):
        # 软删复活优先（唯一键 config_id+month_no）
        ex = db.execute(
            text("SELECT id FROM prcp_sim_rhythm "
                 "WHERE config_id=:cid AND month_no=:mn"),
            {"cid": cfg_id, "mn": w.month_no},
        ).first()
        if ex:
            db.execute(
                text("""UPDATE prcp_sim_rhythm SET
                        is_deleted=0, month_label=:ml, weight=:w, sort_order=:so,
                        remark=:rm, updated_by=:u
                        WHERE id=:id"""),
                {"ml": f"{w.month_no}月", "w": w.weight, "so": w.month_no,
                 "rm": w.remark, "u": uid, "id": ex[0]},
            )
        else:
            db.execute(
                text("""INSERT INTO prcp_sim_rhythm
                        (config_id, scheme_id, coa_node_id, month_no, month_label,
                         weight, sort_order, remark, is_deleted, created_by, updated_by)
                        VALUES (:cid, :sid, :nid, :mn, :ml, :w, :so, :rm, 0, :u, :u)"""),
                {"cid": cfg_id, "sid": cfg[1], "nid": cfg[2],
                 "mn": w.month_no, "ml": f"{w.month_no}月", "w": w.weight,
                 "so": w.month_no, "rm": w.remark, "u": uid},
            )

    # 5) 自动把 rhythm_type 置为 2（自定义）
    db.execute(
        text("UPDATE prcp_sim_node_config SET rhythm_type=2, updated_by=:u WHERE id=:id"),
        {"u": uid, "id": cfg_id},
    )

    return {
        "ok": True, "config_id": cfg_id, "rhythm_type": 2,
        "month_count": len(p.weights), "total_weight": round(total, 4),
    }


@router.post("/rhythm/{cfg_id}/reset-linear")
async def reset_rhythm_linear(
    cfg_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """重置为线性节奏（12 个月均匀 100/12），并把 rhythm_type 置回 1"""
    uid = _uid(user)

    cfg = db.execute(
        text("SELECT id FROM prcp_sim_node_config WHERE id=:id AND is_deleted=0"),
        {"id": cfg_id},
    ).first()
    if not cfg:
        raise HTTPException(404, "节点配置不存在")

    # 软删自定义节奏数据（下次 GET 会返回默认线性）
    db.execute(
        text("UPDATE prcp_sim_rhythm SET is_deleted=1, updated_by=:u "
             "WHERE config_id=:cid AND is_deleted=0"),
        {"u": uid, "cid": cfg_id},
    )
    db.execute(
        text("UPDATE prcp_sim_node_config SET rhythm_type=1, updated_by=:u WHERE id=:id"),
        {"u": uid, "id": cfg_id},
    )
    return {"ok": True, "config_id": cfg_id, "rhythm_type": 1, "message": "已重置为线性节奏"}


@router.delete("/node-config/{cfg_id}")
async def delete_node_config(
    cfg_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """删除节点配置 + 级联软删期限占比"""
    uid = _uid(user)
    cur = db.execute(
        text("SELECT scheme_id FROM prcp_sim_node_config WHERE id=:id AND is_deleted=0"),
        {"id": cfg_id},
    ).first()
    if not cur:
        raise HTTPException(404, "节点配置不存在")
    scheme_id = cur[0]
    # 软删节点配置
    db.execute(
        text("UPDATE prcp_sim_node_config SET is_deleted=1, updated_by=:u WHERE id=:id"),
        {"u": uid, "id": cfg_id},
    )
    # 软删期限占比
    n = db.execute(
        text("UPDATE prcp_sim_term_ratio SET is_deleted=1, updated_by=:u "
             "WHERE config_id=:cid AND is_deleted=0"),
        {"u": uid, "cid": cfg_id},
    ).rowcount
    # 软删节奏配置
    db.execute(
        text("UPDATE prcp_sim_rhythm SET is_deleted=1, updated_by=:u "
             "WHERE config_id=:cid AND is_deleted=0"),
        {"u": uid, "cid": cfg_id},
    )
    # 软删新业务增长配置
    db.execute(
        text("UPDATE prcp_sim_growth_config SET is_deleted=1, updated_by=:u "
             "WHERE config_id=:cid AND is_deleted=0"),
        {"u": uid, "cid": cfg_id},
    )
    # 更新方案 config_node_count
    db.execute(
        text("""UPDATE prcp_sim_scheme s
                SET config_node_count = (
                  SELECT COUNT(*) FROM prcp_sim_node_config c
                  WHERE c.scheme_id=s.id AND c.is_deleted=0
                ), updated_by=:u
                WHERE id=:id"""),
        {"u": uid, "id": scheme_id},
    )
    return {"ok": True, "deleted_ratios": n}


# ============================================================
# 引擎计量相关 endpoint 已抽到 routers/engines.py
# ============================================================
