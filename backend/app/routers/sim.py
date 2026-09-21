"""新业务模拟方案配置 API — 方案 CRUD + 节点配置 + 期限占比子表

模块前缀：/prcp/api/sim
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.services.buckets import ORIG_COLS, REM_COLS

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
    remark: Optional[str] = None
    ratios: List[TermRatioIn] = []


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
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回某账户册方案的节点树（仅未删除 + ACTIVE）"""
    rows = db.execute(
        text("""SELECT id, node_code, node_name, parent_id, node_level, node_type,
                       path, sort_order, status
                FROM prcp_coa_node
                WHERE scheme_id=:s AND is_deleted=0
                ORDER BY sort_order, path"""),
        {"s": coa_scheme_id},
    ).fetchall()

    by_path: dict = {}
    for r in rows:
        by_path[r[6]] = {
            "key": str(r[0]),
            "title": f"{r[2]} ({r[1]})",
            "code": r[1], "name": r[2],
            "id": r[0], "level": r[4], "type": r[5],
            "path": r[6], "sort_order": r[7], "status": r[8],
            "isLeaf": False,  # 默认 False，后面如果有子节点则 True；这里前端通过 children 判断
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
    return {"scheme_id": coa_scheme_id, "items": roots, "total": len(by_path)}


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
    return {"ok": True, "deleted_configs": cn, "deleted_ratios": tr}


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
                       annual_growth_rate, term_unit, term_count, remark
                FROM prcp_sim_node_config
                WHERE scheme_id=:s AND coa_node_id=:n AND is_deleted=0"""),
        {"s": scheme_id, "n": coa_node_id},
    ).first()
    if not cfg:
        return {
            "exists": False, "config": None, "ratios": [],
            "scheme_data_date": scheme_data_date,
        }
    rows = db.execute(
        text("""SELECT id, term_value, term_unit, business_ratio, interest_rate, sort_order, remark
                FROM prcp_sim_term_ratio
                WHERE config_id=:cid AND is_deleted=0
                ORDER BY sort_order, term_value"""),
        {"cid": cfg[0]},
    ).fetchall()
    return {
        "exists": True,
        "config": {
            "id": cfg[0], "scheme_id": cfg[1], "coa_node_id": cfg[2], "coa_node_code": cfg[3],
            "annual_growth_rate": float(cfg[4]) if cfg[4] is not None else 0.0,
            "term_unit": cfg[5], "term_count": cfg[6] or 0, "remark": cfg[7],
        },
        "ratios": [
            {
                "id": r[0], "term_value": r[1], "term_unit": r[2],
                "business_ratio": float(r[3]) if r[3] is not None else 0.0,
                "interest_rate": float(r[4]) if r[4] is not None else 0.0,
                "sort_order": r[5], "remark": r[6],
            } for r in rows
        ],
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
        if cur[1] == 0:
            # 非删除 → 直接更新
            cfg_id = cur[0]
            db.execute(
                text("""UPDATE prcp_sim_node_config SET
                    annual_growth_rate=:r, term_unit=:tu, remark=:rm, updated_by=:u
                    WHERE id=:id"""),
                {"r": p.annual_growth_rate, "tu": p.term_unit, "rm": p.remark,
                 "u": uid, "id": cfg_id},
            )
        else:
            # 软删除 → 复活
            cfg_id = cur[0]
            db.execute(
                text("""UPDATE prcp_sim_node_config SET
                    is_deleted=0, annual_growth_rate=:r, term_unit=:tu, remark=:rm,
                    updated_by=:u
                    WHERE id=:id"""),
                {"r": p.annual_growth_rate, "tu": p.term_unit, "rm": p.remark,
                 "u": uid, "id": cfg_id},
            )
    else:
        # 新建
        cfg_id = db.execute(
            text("""INSERT INTO prcp_sim_node_config
                (scheme_id, coa_node_id, coa_node_code, annual_growth_rate,
                 term_unit, term_count, remark, created_by, updated_by)
                VALUES (:s, :n, :nc, :r, :tu, 0, :rm, :u, :u)"""),
            {"s": scheme_id, "n": p.coa_node_id, "nc": node[1],
             "r": p.annual_growth_rate, "tu": p.term_unit, "rm": p.remark, "u": uid},
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
# 6. 引擎计量（5 步按月滚动算法）
# ============================================================
@router.post("/schemes/{sid}/run")
async def run_engine(
    sid: int,
    month_count: int = Query(24, ge=1, le=60, description="生成月份数（1..60，默认 24）"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """触发引擎计量：按月滚动生成快照

    流程：
      1) 创建 prcp_sim_run 记录 (status=RUNNING)
      2) 取所有已配置的节点
      3) 取每个节点的初始状态 (prcp_data_basic[T月])
      4) 按月滚动 1..month_count
      5) 批量 INSERT prcp_sim_result
      6) 更新 run 状态
    """
    from app.services.sim_engine import run_engine as _run_engine
    try:
        run_id = _run_engine(db, sid, user, month_count)
        return {
            "ok": True,
            "run_id": run_id,
            "month_count": month_count,
            "status": "SUCCESS",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"引擎执行失败：{e}")


@router.get("/runs/{run_id}")
async def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询引擎执行状态（前端轮询用）"""
    row = db.execute(
        text("""SELECT id, sim_scheme_id, sim_scheme_code, base_data_date, month_count,
                       target_data_date, status, progress, total_nodes, processed_nodes,
                       duration_ms, error_message, started_at, finished_at, created_at
                FROM prcp_sim_run WHERE id=:id"""),
        {"id": run_id},
    ).first()
    if not row:
        raise HTTPException(404, "Run 不存在")
    return {
        "id": row[0],
        "sim_scheme_id": row[1],
        "sim_scheme_code": row[2],
        "base_data_date": row[3].isoformat() if row[3] else None,
        "month_count": row[4],
        "target_data_date": row[5].isoformat() if row[5] else None,
        "status": row[6],
        "progress": row[7],
        "total_nodes": row[8],
        "processed_nodes": row[9],
        "duration_ms": row[10],
        "error_message": row[11],
        "started_at": row[12].isoformat() if row[12] else None,
        "finished_at": row[13].isoformat() if row[13] else None,
        "created_at": row[14].isoformat() if row[14] else None,
    }


@router.get("/runs")
async def list_runs(
    sim_scheme_id: Optional[int] = None,
    sim_scheme_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列出某方案的所有 Run（按创建时间倒序）"""
    where = ["1=1"]
    params = {"limit": limit}
    if sim_scheme_id:
        where.append("sim_scheme_id=:sid")
        params["sid"] = sim_scheme_id
    if sim_scheme_code:
        where.append("sim_scheme_code=:sc")
        params["sc"] = sim_scheme_code
    if status:
        where.append("status=:st")
        params["st"] = status
    rows = db.execute(
        text(f"""SELECT id, sim_scheme_id, sim_scheme_code, base_data_date, month_count,
                       target_data_date, status, progress, total_nodes, processed_nodes,
                       duration_ms, started_at, finished_at, created_at
                FROM prcp_sim_run
                WHERE {' AND '.join(where)}
                ORDER BY id DESC LIMIT :limit"""),
        params,
    ).fetchall()
    return {"items": [
        {
            "id": r[0], "sim_scheme_id": r[1], "sim_scheme_code": r[2],
            "base_data_date": r[3].isoformat() if r[3] else None,
            "month_count": r[4],
            "target_data_date": r[5].isoformat() if r[5] else None,
            "status": r[6], "progress": r[7],
            "total_nodes": r[8], "processed_nodes": r[9],
            "duration_ms": r[10],
            "started_at": r[11].isoformat() if r[11] else None,
            "finished_at": r[12].isoformat() if r[12] else None,
            "created_at": r[13].isoformat() if r[13] else None,
        } for r in rows
    ]}


@router.get("/results")
async def list_results(
    sim_scheme_code: Optional[str] = Query(None, description="业务量方案编码"),
    run_id: Optional[int] = Query(None, description="执行 ID（不传取最新 SUCCESS）"),
    date_offset: Optional[int] = Query(None, ge=1, le=60),
    coa_node_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    with_buckets: bool = Query(False, description="是否返回 64+64 期限桶（数据量会变大）"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询引擎快照结果

    不传 sim_scheme_code → 返回所有方案
    不传 run_id → 自动取该方案的最新 SUCCESS run
    with_buckets=true → 返回 64+64 桶（供结果快照表格类似基础数据界面展示）
    """
    where = ["r.is_deleted=0"]
    params = {}
    if sim_scheme_code:
        where.append("r.sim_scheme_code=:sc")
        params["sc"] = sim_scheme_code
    if run_id:
        where.append("r.run_id=:rid")
        params["rid"] = run_id
    else:
        # 取最新 SUCCESS run
        if sim_scheme_code:
            where.append("r.run_id = (SELECT MAX(id) FROM prcp_sim_run WHERE sim_scheme_code=:sc AND status='SUCCESS')")
    if date_offset:
        where.append("r.date_offset=:do")
        params["do"] = date_offset
    if coa_node_id:
        where.append("r.coa_node_id=:nid")
        params["nid"] = coa_node_id
    if category:
        where.append("r.category=:cat")
        params["cat"] = category

    base_cols = """r.id, r.sim_scheme_code, r.run_id, r.data_date, r.date_offset,
                  r.coa_scheme_id, r.coa_node_id, r.node_code, r.node_name,
                  r.node_level, r.category,
                  r.current_balance, r.avg_balance, r.weighted_rate, r.interest_amount,
                  r.calc_note"""
    if with_buckets:
        # 拼接 128 桶列
        bucket_select = ", " + ", ".join(f"r.{c}" for c in ORIG_COLS + REM_COLS)
        sql = f"""SELECT {base_cols}{bucket_select}
                FROM prcp_sim_result r
                WHERE {' AND '.join(where)}
                ORDER BY r.date_offset, r.coa_node_id
                LIMIT 2000"""
    else:
        sql = f"""SELECT {base_cols}
                FROM prcp_sim_result r
                WHERE {' AND '.join(where)}
                ORDER BY r.date_offset, r.coa_node_id
                LIMIT 2000"""

    rows = db.execute(text(sql), params).fetchall()
    bucket_idx_start = 16  # base cols 数量

    items = []
    for r in rows:
        item = {
            "id": r[0],
            "sim_scheme_code": r[1], "run_id": r[2],
            "data_date": r[3].isoformat() if r[3] else None,
            "date_offset": r[4],
            "coa_scheme_id": r[5], "coa_node_id": r[6],
            "node_code": r[7], "node_name": r[8],
            "node_level": r[9], "category": r[10],
            "current_balance": float(r[11]) if r[11] is not None else 0.0,
            "avg_balance": float(r[12]) if r[12] is not None else 0.0,
            "weighted_rate": float(r[13]) if r[13] is not None else 0.0,
            "interest_amount": float(r[14]) if r[14] is not None else 0.0,
            "calc_note": r[15],
        }
        if with_buckets:
            for i, col in enumerate(ORIG_COLS + REM_COLS):
                v = r[bucket_idx_start + i]
                item[col] = float(v) if v is not None else 0.0
        items.append(item)

    return {"items": items}
