"""引擎统一入口 — 所有引擎的 HTTP API

设计：
- 当前只有 "new_business"（新业务模拟）一个引擎
- 所有引擎通过 GET_ENGINE(type) 获取实例
- 路由路径统一为 /sim/*（保持前端兼容，未来引擎再起新前缀）

API 端点：
  POST /sim/schemes/{sid}/run           → 触发引擎执行
  GET  /sim/runs/{rid}                  → 查询执行状态
  GET  /sim/runs                        → 列出执行历史
  GET  /sim/results                     → 查询结果快照

未来扩展：
- 路径不动仍是 /sim/*，但通过 query 参数 ?engine=new_business 区分
- 或者新增独立前缀 /reverse/run、/stress/run 等
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.services.calculate_engine import get_engine

router = APIRouter(prefix="/sim", tags=["引擎计量"])


# ============================================================
# 引擎默认参数
# ============================================================
DEFAULT_ENGINE_TYPE = "new_business"


def _engine(engine_type: str = DEFAULT_ENGINE_TYPE):
    """获取引擎实例，统一 404 处理"""
    try:
        return get_engine(engine_type)
    except KeyError as e:
        raise HTTPException(404, str(e))


# ============================================================
# 1. 触发引擎执行
# ============================================================
@router.post("/schemes/{sid}/run")
async def run_engine(
    sid: int,
    engine_type: str = Query(DEFAULT_ENGINE_TYPE, description="引擎类型，默认 new_business"),
    month_count: int = Query(60, ge=1, le=60, description="生成月份数（1..60，默认 60）"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """触发引擎计量

    流程：
      1) 获取引擎实例（按 engine_type）
      2) 调用引擎的 run() 方法
      3) 返回 run_id

    引擎具体算法实现见 app.services.calculate_engine.<engine_type>.engine
    """
    engine = _engine(engine_type)
    try:
        run_id = engine.run(db, scheme_id=sid, user=user, month_count=month_count)
        return {
            "ok": True,
            "run_id": run_id,
            "engine_type": engine_type,
            "engine_name": engine.engine_name,
            "month_count": month_count,
            "status": "SUCCESS",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"引擎执行失败：{e}")


# ============================================================
# 2. 查询单次执行状态（前端轮询用）
# ============================================================
@router.get("/runs/{run_id}")
async def get_run(
    run_id: int,
    engine_type: str = Query(DEFAULT_ENGINE_TYPE, description="引擎类型"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询引擎执行状态"""
    engine = _engine(engine_type)
    result = engine.get_run(db, run_id)
    if result is None:
        raise HTTPException(404, "Run 不存在")
    return result


# ============================================================
# 3. 列出执行历史
# ============================================================
@router.get("/runs")
async def list_runs(
    engine_type: str = Query(DEFAULT_ENGINE_TYPE),
    sim_scheme_id: Optional[int] = None,
    sim_scheme_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """列出某方案的所有 Run（按创建时间倒序）"""
    engine = _engine(engine_type)
    items = engine.list_runs(
        db,
        sim_scheme_id=sim_scheme_id,
        sim_scheme_code=sim_scheme_code,
        status=status,
        limit=limit,
    )
    return {"items": items, "engine_type": engine_type}


# ============================================================
# 4. 查询结果快照
# ============================================================
@router.get("/results")
async def list_results(
    engine_type: str = Query(DEFAULT_ENGINE_TYPE),
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
    engine = _engine(engine_type)
    items = engine.list_results(
        db,
        sim_scheme_code=sim_scheme_code,
        run_id=run_id,
        date_offset=date_offset,
        coa_node_id=coa_node_id,
        category=category,
        with_buckets=with_buckets,
    )
    return {"items": items, "engine_type": engine_type}
