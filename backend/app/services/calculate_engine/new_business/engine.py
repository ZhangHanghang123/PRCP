"""新业务模拟引擎 — 5 步按月滚动算法

入口：NewBusinessEngine().run(db, scheme_id, user, month_count=60)

输入：sim_scheme_id, month_count=60
输出：prcp_sim_run + prcp_sim_result

算法 5 步（详见 docs/新业务模拟_引擎算法_v1.md）：
  1. 取基础数据 (prcp_data_basic[T月])
  2. 算当月新增量 = rem_m1 + net_new
  3. 按期限拆分 term_ratios 叠加到 orig_mv + rem_mv
  4. 桶往前推一月（m1..m59 → m0..m58 + 长端自循环）
  5. 主指标重算（current/avg/weighted/interest）

## 设计说明

继承 EngineBase，对外暴露 run / get_run / list_runs / list_results 四个方法。
所有算法逻辑封装为实例方法（原来是模块级函数）。
模块底部的兼容函数（get_initial_state / compute_month_new / ...）保留为内部辅助。
"""
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.buckets import BUCKETS, KEYS, ORIG_COLS, REM_COLS
from app.services.calculate_engine.base import EngineBase


# 期限月份数映射（term_value → bucket key）
TERM_TO_KEY = {n: f"m{n}" for n in range(1, 61)}
TERM_TO_KEY[60] = "m60"  # 业务期限最大 60 月，对应 m60 桶

# 「目标」类增长方式（业务口径 2026-10-21 确认，按名称是否含「目标」判定）
#   1 = 目标增长百分比 → 当月新增加值 = 分摊净增加值 + 当月到期释放（rem_m1）
#   2 = 目标增长绝对值 → 同上
#   3 = 增长百分比     → 当月新增加值 = 分摊净增加值（到期自然出表，不回补）
#   4 = 增长值         → 同 3
TARGET_GROWTH_TYPES = {1, 2}


class NewBusinessEngine(EngineBase):
    """新业务模拟引擎

    算法：5 步按月滚动（详见模块 docstring + docs/新业务模拟_引擎算法_v1.md）

    数据表：
        输入：prcp_sim_scheme, prcp_sim_node_config, prcp_sim_term_ratio
             + prcp_data_basic（基础数据）
             + prcp_coa_node（节点元数据）
        输出：prcp_sim_run（执行记录） + prcp_sim_result（结果快照）
    """

    engine_type = "new_business"
    engine_name = "新业务模拟引擎"

    # ===== 默认参数 =====
    DEFAULT_MONTH_COUNT = 60
    MIN_MONTH_COUNT = 1
    MAX_MONTH_COUNT = 60

    # ============================================================
    # EngineBase 实现
    # ============================================================

    def run(
        self,
        db: Session,
        scheme_id: int,
        user,
        month_count: int = DEFAULT_MONTH_COUNT,
    ) -> int:
        """触发引擎执行

        Args:
            db: SQLAlchemy Session
            scheme_id: 模拟方案 id（prcp_sim_scheme.id）
            user: 当前登录用户 dict
            month_count: 滚动月数（1..60，默认 60）

        Returns:
            run_id

        Raises:
            ValueError: 方案不存在 / 无节点配置 / 无基础数据
        """
        return _run_engine(db, scheme_id, user, month_count)

    def get_run(self, db: Session, run_id: int) -> Optional[Dict]:
        """查询单次执行的详细状态"""
        row = db.execute(
            text("""SELECT id, sim_scheme_id, sim_scheme_code, base_data_date, month_count,
                           target_data_date, status, progress, total_nodes, processed_nodes,
                           configured_node_count, rolled_node_count, aggregated_node_count,
                           duration_ms, error_message, started_at, finished_at, created_at
                    FROM prcp_sim_run WHERE id=:id"""),
            {"id": run_id},
        ).first()
        if not row:
            return None
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
            "configured_node_count": row[10] or 0,
            "rolled_node_count": row[11] or 0,
            "aggregated_node_count": row[12] or 0,
            "duration_ms": row[13],
            "error_message": row[14],
            "started_at": row[15].isoformat() if row[15] else None,
            "finished_at": row[16].isoformat() if row[16] else None,
            "created_at": row[17].isoformat() if row[17] else None,
        }

    def list_runs(self, db: Session, **filters) -> List[Dict]:
        """列出执行历史

        支持过滤：sim_scheme_id / sim_scheme_code / status / limit
        """
        where = ["1=1"]
        params = {"limit": filters.get("limit", 20)}
        if filters.get("sim_scheme_id"):
            where.append("sim_scheme_id=:sid")
            params["sid"] = filters["sim_scheme_id"]
        if filters.get("sim_scheme_code"):
            where.append("sim_scheme_code=:sc")
            params["sc"] = filters["sim_scheme_code"]
        if filters.get("status"):
            where.append("status=:st")
            params["st"] = filters["status"]

        rows = db.execute(
            text(f"""SELECT id, sim_scheme_id, sim_scheme_code, base_data_date, month_count,
                           target_data_date, status, progress, total_nodes, processed_nodes,
                           configured_node_count, rolled_node_count, aggregated_node_count,
                           duration_ms, started_at, finished_at, created_at
                    FROM prcp_sim_run
                    WHERE {' AND '.join(where)}
                    ORDER BY id DESC LIMIT :limit"""),
            params,
        ).fetchall()
        return [
            {
                "id": r[0], "sim_scheme_id": r[1], "sim_scheme_code": r[2],
                "base_data_date": r[3].isoformat() if r[3] else None,
                "month_count": r[4],
                "target_data_date": r[5].isoformat() if r[5] else None,
                "status": r[6], "progress": r[7],
                "total_nodes": r[8], "processed_nodes": r[9],
                "configured_node_count": r[10] or 0,
                "rolled_node_count": r[11] or 0,
                "aggregated_node_count": r[12] or 0,
                "duration_ms": r[13],
                "started_at": r[14].isoformat() if r[14] else None,
                "finished_at": r[15].isoformat() if r[15] else None,
                "created_at": r[16].isoformat() if r[16] else None,
            } for r in rows
        ]

    def list_results(self, db: Session, **filters) -> List[Dict]:
        """查询结果快照

        支持过滤：sim_scheme_code / run_id / date_offset / coa_node_id / category
        选项：with_buckets（是否返回 64+64 期限桶）

        不传 run_id → 自动取该方案的最新 SUCCESS run
        """
        where = ["r.is_deleted=0"]
        params = {}
        if filters.get("sim_scheme_code"):
            where.append("r.sim_scheme_code=:sc")
            params["sc"] = filters["sim_scheme_code"]
        if filters.get("run_id"):
            where.append("r.run_id=:rid")
            params["rid"] = filters["run_id"]
        else:
            if filters.get("sim_scheme_code"):
                where.append(
                    "r.run_id = (SELECT MAX(id) FROM prcp_sim_run "
                    "WHERE sim_scheme_code=:sc AND status='SUCCESS')"
                )
        if filters.get("date_offset"):
            where.append("r.date_offset=:do")
            params["do"] = filters["date_offset"]
        if filters.get("coa_node_id"):
            where.append("r.coa_node_id=:nid")
            params["nid"] = filters["coa_node_id"]
        if filters.get("category"):
            where.append("r.category=:cat")
            params["cat"] = filters["category"]

        with_buckets = filters.get("with_buckets", False)
        # 上限可调：节点数 × 月数可能远超 2000（57 节点 × 60 月 = 3420）
        limit = int(filters.get("limit") or 20000)

        base_cols = """r.id, r.sim_scheme_code, r.run_id, r.data_date, r.date_offset,
                      r.coa_scheme_id, r.coa_node_id, r.node_code, r.node_name,
                      r.node_level, r.category, r.is_configured, r.is_aggregated,
                      r.current_balance, r.avg_balance, r.weighted_rate, r.interest_amount,
                      r.growth_type, r.year_target, r.rhythm_weight,
                      r.month_add, r.month_release,
                      r.calc_note"""
        if with_buckets:
            bucket_select = ", " + ", ".join(f"r.{c}" for c in ORIG_COLS + REM_COLS)
            sql = f"""SELECT {base_cols}{bucket_select}
                    FROM prcp_sim_result r
                    WHERE {' AND '.join(where)}
                    ORDER BY r.date_offset, r.coa_node_id
                    LIMIT {limit}"""
        else:
            sql = f"""SELECT {base_cols}
                    FROM prcp_sim_result r
                    WHERE {' AND '.join(where)}
                    ORDER BY r.date_offset, r.coa_node_id
                    LIMIT {limit}"""

        total = db.execute(
            text(f"SELECT COUNT(*) FROM prcp_sim_result r WHERE {' AND '.join(where)}"),
            params,
        ).scalar() or 0
        if total > limit:
            import logging
            logging.getLogger(__name__).warning(
                "list_results 结果被截断：实际 %d 行 > LIMIT %d（节点数×月数超限，建议按月查询或加大 limit）",
                total, limit,
            )

        rows = db.execute(text(sql), params).fetchall()
        # base_cols 含 23 个字段（id..calc_note），桶数据从 idx=23 开始
        bucket_idx_start = 23

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
                "is_configured": bool(r[11]) if r[11] is not None else False,
                "is_aggregated": bool(r[12]) if r[12] is not None else False,
                "current_balance": float(r[13]) if r[13] is not None else 0.0,
                "avg_balance": float(r[14]) if r[14] is not None else 0.0,
                "weighted_rate": float(r[15]) if r[15] is not None else 0.0,
                "interest_amount": float(r[16]) if r[16] is not None else 0.0,
                # v2.1：投放分解追溯字段
                "growth_type": int(r[17]) if r[17] is not None else None,
                "year_target": float(r[18]) if r[18] is not None else None,
                "rhythm_weight": float(r[19]) if r[19] is not None else None,
                "month_add": float(r[20]) if r[20] is not None else None,
                "month_release": float(r[21]) if r[21] is not None else None,
                "calc_note": r[22],
            }
            if with_buckets:
                for i, col in enumerate(ORIG_COLS + REM_COLS):
                    v = r[bucket_idx_start + i]
                    item[col] = float(v) if v is not None else 0.0
            items.append(item)

        return items


# ============================================================
# 内部辅助函数（实现细节，不对外暴露）
# ============================================================

def _uid(user) -> int:
    return user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)


def _add_months(d: date, months: int) -> date:
    """日期 + N 月（月底处理：1/31 + 1 月 = 2/28）"""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    import calendar
    last_day = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last_day))


# ============================================================
# 步骤 1：取初始状态
# ============================================================
def get_initial_state(db: Session, coa_node_id: int, base_date: str) -> Optional[Dict]:
    """从 prcp_data_basic 取 T 月数据作为引擎初始状态

    返回 state dict，含 orig_*/rem_* 64+64 桶 + 4 主指标
    节点元数据（node_code/name/level/parent_code/is_leaf/category）从 prcp_coa_node JOIN 获取
    找不到则返回 None（跳过该节点）
    """
    cols = ", ".join([f"b.{c}" for c in (ORIG_COLS + REM_COLS)])
    main_cols = ", ".join([f"b.{c}" for c in ["current_balance", "avg_balance", "weighted_rate", "interest_amount"]])
    row = db.execute(
        text(f"""SELECT {cols}, {main_cols},
                       n.node_code, n.node_name, n.node_level,
                       n.parent_id, n.scheme_id AS coa_scheme_id,
                       b.category
                FROM prcp_data_basic b
                JOIN prcp_coa_node n ON n.id = b.coa_node_id
                WHERE b.coa_node_id=:nid AND b.data_date=:d AND b.is_deleted=0
                ORDER BY b.date_offset ASC LIMIT 1"""),
        {"nid": coa_node_id, "d": base_date},
    ).first()
    if not row:
        return None

    state = {}
    for i, col in enumerate(ORIG_COLS):
        state[col] = float(row[i]) if row[i] is not None else 0.0
    offset = len(ORIG_COLS)
    for i, col in enumerate(REM_COLS):
        state[col] = float(row[offset + i]) if row[offset + i] is not None else 0.0
    offset += len(REM_COLS)
    state["current_balance"] = float(row[offset]) if row[offset] is not None else 0.0
    state["avg_balance"] = float(row[offset + 1]) if row[offset + 1] is not None else 0.0
    state["weighted_rate"] = float(row[offset + 2]) if row[offset + 2] is not None else 0.0
    state["interest_amount"] = float(row[offset + 3]) if row[offset + 3] is not None else 0.0
    meta = offset + 4
    state["node_code"] = row[meta] or ""
    state["node_name"] = row[meta + 1] or ""
    state["node_level"] = int(row[meta + 2]) if row[meta + 2] is not None else 0
    state["parent_id"] = int(row[meta + 3]) if row[meta + 3] is not None else None
    state["coa_scheme_id"] = int(row[meta + 4]) if row[meta + 4] is not None else 0
    state["category"] = row[meta + 5] or ""
    state["parent_code"] = ""
    state["is_leaf"] = 1

    return state


# ============================================================
# 步骤 2：算当月新增量
# ============================================================
def compute_month_new(state: Dict, annual_growth_rate: float) -> Tuple[float, float]:
    """当月新增量 = rem_m1（当月到期） + 净新增量（current × growth / 100 / 12）

    注意：annual_growth_rate 是百分比数值（如 10 表示 10%），需 /100 转小数
    """
    monthly_rate = annual_growth_rate / 100.0 / 12.0
    net_new = state["current_balance"] * monthly_rate
    month_new = state["rem_m1"] + net_new
    return net_new, month_new


# ============================================================
# 步骤 1（v2.1）：根据增长配置换算「当年目标增量」
# ============================================================
# 增长方式语义（业务口径 2026-10-21 定稿）
#   1 = 目标增长百分比 → 「目标」类：当年增量 = 基数 × 增速%；到期释放回补
#   2 = 目标增长绝对值 → 「目标」类：当年增量 = yearN（金额）；到期释放回补
#   3 = 增长百分比     → 非「目标」类：当年增量 = 基数 × 增速%；到期自然出表
#   4 = 增长值         → 非「目标」类：年末余额锚定，可为负（缩表）；到期自然出表
UNIT_SCALE_BY_UNIT = {
    "WAN": 1e4,   # 万元
    "YI": 1e8,    # 亿元
}


def compute_year_target(
    growth_type: int,
    year_param: float,
    base_balance: float,
    unit_scale: float = 1.0,
) -> float:
    """把「第 N 年的增长参数」换算成「当年目标增量」（元）

    growth_type 语义（v2.1 定稿）：
      1 目标增长百分比：year_param 是目标增速(%)，增量 = 基数 × 增速
      2 目标增长绝对值：year_param 是当年新增总额(金额)，增量 = year_param × 单位换算
      3 增长百分比    ：year_param 是期间增速(%)，增量 = 基数 × 增速（语义同 1，但投放口径不同）
      4 增长值        ：year_param 是年末目标余额(金额)，增量 = 目标余额 − 当前余额
                        → 可为负数（缩表场景）

    返回：当年目标增量（元），可能为负（type 4 缩表）
    """
    if growth_type in (1, 3):
        return base_balance * float(year_param) / 100.0
    if growth_type == 2:
        return float(year_param) * unit_scale
    if growth_type == 4:
        target_balance = float(year_param) * unit_scale
        return target_balance - base_balance
    # 兜底：未知方式按 0 处理（不投放）
    return 0.0


# ============================================================
# 步骤 2（v2.1）：根据节奏配置取「12 个月权重」
# ============================================================
def default_linear_weights() -> List[float]:
    """默认线性节奏：12 个月均匀，每个月 100/12 = 8.3333"""
    return [round(100.0 / 12, 4)] * 12


def get_rhythm_weights(
    rhythm_type: int, rhythm_rows: Optional[List[Dict]] = None
) -> List[float]:
    """取 12 个月节奏权重（v2.1）

    rhythm_type：
      1 线性   → 12 个月均匀（8.3333%），忽略表中数据
      2 自定义 → 取 prcp_sim_rhythm 的 12 行权重；无数据时降级为线性

    返回长度固定为 12 的权重列表（单位 %，和为 100）
    """
    if rhythm_type != 2:
        return default_linear_weights()

    if not rhythm_rows:
        return default_linear_weights()

    weights = default_linear_weights()
    got = 0
    for r in rhythm_rows:
        try:
            m = int(r["month_no"])
            w = float(r["weight"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= m <= 12:
            weights[m - 1] = w
            got += 1

    # 未配置满 12 个月（或未配置任何月）→ 降级线性
    if got < 12:
        return default_linear_weights()

    # 权重和容差校验：偏差 > 0.1% 时降级线性，避免脏数据放大
    total = sum(weights)
    if abs(total - 100.0) > 0.1:
        return default_linear_weights()

    return weights


# ============================================================
# 步骤 2（v2.1）：算当月投放（按增长方式名称判定是否回补到期）
# ============================================================
def compute_month_new_v2(
    growth_type: int,
    base_balance: float,
    year_target: float,
    rhythm_weight: float,
    release: float,
    year_values: Optional[List[float]] = None,
    unit_scale: float = 1.0,
    remaining_weight: Optional[float] = None,
) -> Tuple[float, float, float]:
    """计算第 M 月的 (add, release, month_new)

    业务口径（2026-10-21 确认）：**按增长方式名称是否含「目标」判定是否回补到期**

      「目标」类 —— growth_type 1 目标增长百分比 / 2 目标增长绝对值
          当月新增加值 = 分摊的净增加值 + 当月剩余期限余额（rem_m1）
          → 到期回补，保证余额净增长达到目标

      非「目标」类 —— growth_type 3 增长百分比 / 4 增长值
          当月新增加值 = 分摊的净增加值
          → 不回补，当月到期自然出表

      add     = 当月分摊的净新增投放（元），可为负（type 4 缩表）
      release = 当月到期释放（元）= 上月末 rem_m1

    四种方式统一采用「固定年增量 × 节奏权重」分摊到月：
      Σ(add over 12 months) = year_target × Σ(w)/100 = year_target
      → 全年投放额恒等于年目标增量，且不会因余额漂移而放大或衰减。
      year_target 由 compute_year_target 按 growth_type 换算：
        1/3 → base_balance × pct%      （相对基数）
        2   → param × unit_scale        （固定新增额）
        4   → param × unit_scale − 年初余额（余额锚定，年初锚定一次）
    """
    # 固定年增量按节奏权重分摊到月（Σw = 100 → 全年合计 = year_target）
    add = year_target * (rhythm_weight / 100.0)

    # 按增长方式名称判定：1/2 含「目标」→ 回补到期；3/4 → 不回补
    if growth_type in TARGET_GROWTH_TYPES:
        month_new = release + add
    else:
        month_new = add

    return add, release, month_new


# ============================================================
# 步骤 3：按期限占比拆分 + 按「绝对到期月」落桶
# ============================================================
def apply_term_split(
    state: Dict,
    month_new: float,
    term_ratios: List[Dict],
    cur_month: int = 1,
    full_plan: Optional[Dict[int, float]] = None,
) -> List[Tuple[str, float, float]]:
    """按期限占比拆分 month_new，并直接落到「距基准日第 cur_month+v 个月到期」的格子

    v2.2 口径（2026-10-21 业务确认）：
      **取消「剩余期限桶整体前移」**，改为按绝对到期月直接落桶。

        rem_mk 语义 = 「距基准日第 k 个月到期的金额」（绝对到期月，非剩余期限）
        orig_mv 语义 = 「原始期限为 v 个月的累计投放额」（只进不出，不随月份变化）

      第 M 月投放一笔期限 v 的业务 → 直接落到 rem_m{M+v}
      第 M 月的到期释放 = 取走 rem_m{M} 并清零

      基准日时「剩余期限」恰好等于「距基准日到期月数」，故存量数据无需转换。

    Returns [(term_value, amount, interest_rate), ...] 用于加权平均利率计算
    """
    additions = []
    for ratio in term_ratios:
        v = int(ratio["term_value"])
        b_pct = float(ratio["business_ratio"])
        r = float(ratio.get("interest_rate", 0.0))
        amount_v = month_new * b_pct / 100.0

        # ① 原始期限桶：只进不出（记录投放时的原始期限）
        if v in TERM_TO_KEY:
            key = TERM_TO_KEY[v]
            state[f"orig_{key}"] = state.get(f"orig_{key}", 0.0) + amount_v

        # ② 绝对到期月桶：落到 cur_month + v
        #    超出 60 月落到长端桶（y10/y15/y20/y30 按超出月数就近归档）
        tkey = _due_key(cur_month + v)
        state[f"rem_{tkey}"] = state.get(f"rem_{tkey}", 0.0) + amount_v

        # v2.4：把每笔投放的落点累加进「完整 60 月排期」（与是否已取走无关）
        if full_plan is not None:
            tgt_m = cur_month + v
            if tgt_m <= 60:
                full_plan[tgt_m] = full_plan.get(tgt_m, 0.0) + amount_v

        additions.append((str(v), amount_v, r))
    return additions


def _due_key(target_month: int) -> str:
    """绝对到期月 → 桶名（不含 rem_ 前缀）

    ≤60 月 → m1..m60
    >60 月 → 按超出月数归档到 y10 / y15 / y20 / y30（10Y / 15Y / 20Y / 30Y）
    """
    if target_month <= 60:
        return f"m{target_month}"
    if target_month <= 120:
        return "y10"
    if target_month <= 180:
        return "y15"
    if target_month <= 240:
        return "y20"
    return "y30"


def _due_state_key(target_month: int) -> str:
    """绝对到期月 → state / row 中的完整键名（rem_ 前缀）"""
    return f"rem_{_due_key(target_month)}"


def take_due(state: Dict, cur_month: int) -> float:
    """第 cur_month 的到期释放：取走 rem_m{cur_month} 并清零

    v2.2：不再前移，直接按绝对到期月取走当月应到期金额。
    """
    key = _due_state_key(cur_month)
    due = float(state.get(key, 0.0))
    state[key] = 0.0
    return due


def peek_due(state: Dict, cur_month: int) -> float:
    """查看第 cur_month 的计划到期额（不清零）

    v2.3：用于在 take_due 之前快照「计划到期」，使结果表保留到期信息。
    """
    return float(state.get(_due_state_key(cur_month), 0.0))


def snapshot_future_plan(state: Dict, from_month: int, month_count: int) -> Dict[int, float]:
    """快照「从 from_month 到 month_count 各月的计划到期额」（截至当前月的增量）

    v2.3：纯读取，不修改 state。
    ⚠️ 局限：只包含「截至本月已投放」的部分，看不到未来月份的投放。
       完整排期见 accumulate_plan / apply_final_plan。
    """
    plan: Dict[int, float] = {}
    for tgt in range(from_month, month_count + 1):
        amt = float(state.get(_due_state_key(tgt), 0.0))
        if abs(amt) > 1e-9:
            plan[tgt] = amt
    return plan


def accumulate_plan(plan: Dict[int, float], state: Dict, month_count: int) -> None:
    """把 state 中所有剩余桶累加进 plan（用于汇总完整 60 月到期排期）

    v2.4：解决「每格都应有值」的问题 ——
      state 是「截至当前月已投放」的存量，每取走一格就少一格；
      plan 则是把 60 个月里**每一笔投放的落点**都累加起来，
      得到「整个 5 年预测期内各月的最终到期额」，与是否已取走无关。
    """
    for tgt in range(1, month_count + 1):
        amt = float(state.get(_due_state_key(tgt), 0.0))
        if abs(amt) > 1e-9:
            plan[tgt] = plan.get(tgt, 0.0) + amt


def apply_final_plan(row: Dict, final_plan: Dict[int, float]) -> None:
    """把完整 60 月到期排期写入结果行

    v2.4：让每一行（含 M1）都能看到「未来 5 年每个月都有到期」的完整时间轴，
          每个格子都有值 —— 因为它包含存量 + 全部 60 个月投放的落点。
    """
    for tgt, amt in final_plan.items():
        row[_due_state_key(tgt)] = float(amt)


# ============================================================
# 步骤 4：桶往前推一月
# ============================================================
def roll_one_month(state: Dict) -> Dict:
    """【已废弃 · v2.2】所有桶往前推一月

    ⚠️ 业务口径 2026-10-21 变更：不再需要「剩余期限桶整体前移」。
       rem_* 语义已改为「距基准日第 k 个月到期」，投放时直接落到 rem_m{M+v}，
       到期时按月取走 rem_m{M}。本函数保留仅作历史参考，引擎不再调用。

    月桶：
      新 m_v (1..59) = 旧 m_(v+1)
      新 m60 = 旧 y10 / 60

    长端桶（自循环）：
      新 y10 = 旧 y10 - 旧 y10/60 + 旧 y15/120
      新 y15 = 旧 y15 - 旧 y15/120 + 旧 y20/120
      新 y20 = 旧 y20 - 旧 y20/120 + 旧 y30/240
      新 y30 = 旧 y30 - 旧 y30/240

    同样的逻辑应用到 rem_* 桶
    """
    new_state = dict(state)

    # 原始期限月桶
    for v in range(1, 60):
        new_state[f"orig_m{v}"] = state[f"orig_m{v+1}"]
    new_state["orig_m60"] = state["orig_y10"] / 60.0
    new_state["orig_y10"] = state["orig_y10"] - state["orig_y10"] / 60.0 + state["orig_y15"] / 120.0
    new_state["orig_y15"] = state["orig_y15"] - state["orig_y15"] / 120.0 + state["orig_y20"] / 120.0
    new_state["orig_y20"] = state["orig_y20"] - state["orig_y20"] / 120.0 + state["orig_y30"] / 240.0
    new_state["orig_y30"] = state["orig_y30"] - state["orig_y30"] / 240.0

    # 剩余期限月桶
    for v in range(1, 60):
        new_state[f"rem_m{v}"] = state[f"rem_m{v+1}"]
    new_state["rem_m60"] = state["rem_y10"] / 60.0
    new_state["rem_y10"] = state["rem_y10"] - state["rem_y10"] / 60.0 + state["rem_y15"] / 120.0
    new_state["rem_y15"] = state["rem_y15"] - state["rem_y15"] / 120.0 + state["rem_y20"] / 120.0
    new_state["rem_y20"] = state["rem_y20"] - state["rem_y20"] / 120.0 + state["rem_y30"] / 240.0
    new_state["rem_y30"] = state["rem_y30"] - state["rem_y30"] / 240.0

    return new_state


# ============================================================
# 步骤 5：主表指标重算
# ============================================================
def compute_main_metrics(
    state: Dict,
    annual_growth_rate: float,
    term_ratios: List[Dict],
    net_new: float,
    month_new: float,
) -> Tuple[float, float, float, float]:
    """返回 (new_current_balance, new_avg_balance, new_weighted_rate, new_interest_amount)"""
    cur = state["current_balance"]
    avg = state["avg_balance"]
    wr = state["weighted_rate"]
    monthly_rate = annual_growth_rate / 100.0 / 12.0

    new_current = cur * (1.0 + monthly_rate)
    new_avg = avg + cur * monthly_rate / 2.0

    weighted_amount = sum(
        (month_new * float(r["business_ratio"]) / 100.0) * float(r.get("interest_rate", 0.0))
        for r in term_ratios
    )
    denom = avg + month_new
    if denom > 0:
        new_wr = (avg * wr + weighted_amount) / denom
    else:
        new_wr = wr

    new_interest = new_avg * new_wr / 12.0

    return new_current, new_avg, new_wr, new_interest


# ============================================================
# 主循环：run_engine（内部函数，NewBusinessEngine.run 调用此）
# ============================================================
def _run_engine(
    db: Session,
    scheme_id: int,
    user: dict,
    month_count: int = NewBusinessEngine.DEFAULT_MONTH_COUNT,
) -> int:
    """执行引擎，返回 run_id

    步骤：
      1) 创建 prcp_sim_run 记录 (status=RUNNING)
      2) 取方案基础信息 (coa_scheme_id, data_date)
      3) 取账户册下所有「有基础数据」+「末级节点」（无子节点）
         - 已配置叶子节点 (is_configured=1)：按 growth_rate + term_ratios 计算
         - 未配置叶子节点 (is_configured=0)：仅做时间桶滚动
      4) 按月滚动 (1..month_count) — 仅叶子节点
      5) 聚合 SUMMARY 节点：递归查所有后代叶子，按 date_offset 聚合
         加权利率按当前余额加权：wr = Σ(c.current × c.wr) / Σ(c.current)
      6) 批量 INSERT prcp_sim_result（is_configured + is_aggregated 双标记）
      7) 更新 run 状态 (SUCCESS / FAILED)
    """
    # 1) 校验 + 创建 run
    scheme = db.execute(
        text("""SELECT id, scheme_code, scheme_name, coa_scheme_id, data_date
                FROM prcp_sim_scheme WHERE id=:id AND is_deleted=0"""),
        {"id": scheme_id},
    ).first()
    if not scheme:
        raise ValueError(f"方案不存在 id={scheme_id}")

    scheme_id_, scheme_code, scheme_name, coa_scheme_id, data_date = scheme
    if not coa_scheme_id or not data_date:
        raise ValueError("方案缺少 coa_scheme_id 或 data_date")

    uid = _uid(user)
    target_date = _add_months(data_date, month_count)
    run_id = db.execute(
        text("""INSERT INTO prcp_sim_run
            (sim_scheme_id, sim_scheme_code, base_data_date, month_count,
             target_data_date, status, progress, total_nodes, processed_nodes,
             configured_node_count, rolled_node_count, aggregated_node_count,
             started_at, created_by)
            VALUES (:sid, :sc, :bd, :mc, :td, 'RUNNING', 0, 0, 0, 0, 0, 0, NOW(), :u)"""),
            {
                "sid": scheme_id, "sc": scheme_code, "bd": data_date.isoformat(),
                "mc": month_count, "td": target_date.isoformat(), "u": uid,
            },
        ).lastrowid

    try:
        # 2) 只取末级（叶子）节点 + LEFT JOIN 配置信息（v2.1 带 is_model_calc / rhythm_type）
        #    末级判定：node_type='BUSINESS'（若账户册用该类型）或「无子节点」（通用兜底）
        #    说明：不同账户册方案 node_type 取值不统一（如 ASSET/LIABILITY/EQUITY），
        #         因此以「无子节点」作为末级的权威判定，与前端树的末级口径一致。
        leaf_nodes = db.execute(
            text("""SELECT n.id AS coa_node_id, n.node_code, n.node_name,
                           n.node_level, n.parent_id, n.path,
                           c.id AS cfg_id, c.annual_growth_rate,
                           COALESCE(c.is_model_calc, 2) AS is_model_calc,
                           COALESCE(c.rhythm_type, 1) AS rhythm_type
                    FROM prcp_coa_node n
                    JOIN prcp_data_basic b
                         ON b.coa_node_id = n.id
                        AND b.data_date = :bd
                        AND b.is_deleted = 0
                    LEFT JOIN prcp_sim_node_config c
                         ON c.coa_node_id = n.id
                        AND c.scheme_id  = :sid
                        AND c.is_deleted = 0
                    WHERE n.scheme_id = :coa_sid
                      AND n.is_deleted = 0
                      AND NOT EXISTS (
                            SELECT 1 FROM prcp_coa_node ch
                            WHERE ch.parent_id = n.id AND ch.is_deleted = 0
                          )
                    ORDER BY n.path, n.id"""),
            {"sid": scheme_id, "bd": data_date.isoformat(), "coa_sid": coa_scheme_id},
        ).fetchall()

        if not leaf_nodes:
            raise ValueError(
                f"账户册 id={coa_scheme_id} 下没有任何末级（叶子）节点在 {data_date.isoformat()} 月有基础数据，"
                f"请先维护 prcp_data_basic"
            )

        # 3) 取所有已配置节点的 term_ratios
        cfg_ids = [row[6] for row in leaf_nodes if row[6] is not None]
        if cfg_ids:
            ratio_rows = db.execute(
                text(f"""SELECT config_id, term_value, term_unit, business_ratio, interest_rate, sort_order
                        FROM prcp_sim_term_ratio
                        WHERE config_id IN ({','.join(str(i) for i in cfg_ids)}) AND is_deleted=0
                        ORDER BY config_id, sort_order"""),
            ).fetchall()
        else:
            ratio_rows = []

        ratios_by_cfg = {}
        for r in ratio_rows:
            ratios_by_cfg.setdefault(r[0], []).append({
                "term_value": r[1], "term_unit": r[2],
                "business_ratio": r[3], "interest_rate": r[4],
                "sort_order": r[5],
            })

        # 3.1) v2.1：取所有已配置节点的 growth_config（增长方式 + 5 年参数）
        growth_by_cfg = {}
        if cfg_ids:
            growth_rows = db.execute(
                text(f"""SELECT config_id, growth_type,
                               year1_value, year2_value, year3_value, year4_value, year5_value,
                               amount_unit
                        FROM prcp_sim_growth_config
                        WHERE config_id IN ({','.join(str(i) for i in cfg_ids)}) AND is_deleted=0"""),
            ).fetchall()
            for g in growth_rows:
                growth_by_cfg[g[0]] = {
                    "growth_type": int(g[1]) if g[1] is not None else 1,
                    "year_values": [
                        float(g[2] or 0), float(g[3] or 0), float(g[4] or 0),
                        float(g[5] or 0), float(g[6] or 0),
                    ],
                    "amount_unit": g[7] or "WAN",
                }

        # 3.2) v2.1：取所有已配置节点的 rhythm（12 个月节奏权重）
        rhythm_by_cfg = {}
        if cfg_ids:
            rhythm_rows = db.execute(
                text(f"""SELECT config_id, month_no, weight
                        FROM prcp_sim_rhythm
                        WHERE config_id IN ({','.join(str(i) for i in cfg_ids)}) AND is_deleted=0
                        ORDER BY config_id, month_no"""),
            ).fetchall()
            for r in rhythm_rows:
                rhythm_by_cfg.setdefault(r[0], []).append({
                    "month_no": r[1], "weight": r[2],
                })

        # 4) 取每个叶子节点的初始状态 + 区分配置/未配置
        nodes_data = []
        configured_count = 0
        rolled_count = 0
        for row in leaf_nodes:
            (coa_node_id, node_code, node_name, node_level, parent_id, path,
             cfg_id, growth_rate, is_model_calc, rhythm_type) = row
            init_state = get_initial_state(db, coa_node_id, data_date.isoformat())
            if init_state is None:
                continue

            # v2.1：分支判定改为「是否模型测算」，而非「有无配置」
            #   is_model_calc=1 → 走模型测算分支（读 3 类配置）
            #   is_model_calc=2 → 走存量保持分支（只滚桶不投放）
            is_configured = (cfg_id is not None) and (int(is_model_calc) == 1)
            if is_configured:
                configured_count += 1
                gr = float(growth_rate) if growth_rate else 0.0
                tr = ratios_by_cfg.get(cfg_id, [])

                gc = growth_by_cfg.get(cfg_id)
                if gc:
                    growth_type = gc["growth_type"]
                    year_values = gc["year_values"]
                    unit_scale = UNIT_SCALE_BY_UNIT.get(gc["amount_unit"], 1e4)
                else:
                    # 未配 growth_config → 5 年参数全 0（只滚桶不投放）
                    growth_type, year_values, unit_scale = 1, [0.0] * 5, 1e4

                weights = get_rhythm_weights(int(rhythm_type or 1), rhythm_by_cfg.get(cfg_id))
            else:
                rolled_count += 1
                gr = 0.0
                tr = []
                growth_type, year_values, unit_scale = 1, [0.0] * 5, 1e4
                weights = default_linear_weights()

            # v2.4：完整 60 月到期排期 —— 先装入基准日存量，
            #         后续 60 个月的每笔投放落点都会累加进来
            full_plan: Dict[int, float] = {}
            accumulate_plan(full_plan, init_state, month_count)

            nodes_data.append({
                "coa_node_id": coa_node_id,
                "is_configured": is_configured,
                "growth_rate": gr,
                "term_ratios": tr,
                "state": init_state,
                # v2.1 新增
                "growth_type": growth_type,
                "year_values": year_values,
                "unit_scale": unit_scale,
                "rhythm_weights": weights,
                # v2.4：完整排期容器
                "full_plan": full_plan,
            })

        # 5) 按月滚动（叶子节点）
        all_cols = ORIG_COLS + REM_COLS + [
            "current_balance", "avg_balance", "weighted_rate", "interest_amount",
        ]
        insert_cols = [
            "sim_scheme_code", "sim_scheme_id", "run_id",
            "data_date", "date_offset",
            "coa_scheme_id", "coa_node_id", "node_code", "node_name",
            "node_level", "category", "is_configured", "is_aggregated",
            # v2.1：投放分解追溯字段
            "growth_type", "year_target", "rhythm_weight", "month_add", "month_release",
            # v2.3：计划到期（体现未来 5 年每月新增的影响）
            "planned_due", "cum_planned",
        ] + all_cols + ["calc_note"]
        placeholders = ", ".join(f":{c}" for c in insert_cols)
        col_list = ", ".join(insert_cols)
        insert_sql = f"INSERT INTO prcp_sim_result ({col_list}) VALUES ({placeholders})"

        # v2.4：完整 60 月到期排期（按节点累积）+ 全量结果行（延后统一 INSERT）
        all_rows: List[Dict] = []

        for k in range(1, month_count + 1):
            data_date_k = _add_months(data_date, k)
            data_date_k_str = data_date_k.isoformat()
            rows_k = []

            # v2.1：第 k 月对应的年份索引（1~5）与年内月份（1~12）
            #       month_count 上限 60 → y 恒在 1~5 内，不存在超出（v2.1 口径 #3）
            y = (k - 1) // 12 + 1
            m_in_year = (k - 1) % 12 + 1

            for nd in nodes_data:
                state = nd["state"]
                growth_rate = nd["growth_rate"]
                term_ratios = nd["term_ratios"]
                is_configured = nd["is_configured"]

                growth_type = nd["growth_type"]
                year_values = nd["year_values"]
                unit_scale = nd["unit_scale"]
                weights = nd["rhythm_weights"]
                base_balance = state["current_balance"]

                # ===== 步骤 1：年目标增量 =====
                #  v2.1 修正（type 4 余额锚定）：目标 = 配置的年末余额 − 年初余额。
                #  年初余额每年锚定一次（m_in_year==1 时记录），后续月份沿用，
                #  否则余额逐月增长会让目标逐年递减，导致年末余额偏离配置值。
                if is_configured:
                    year_param = year_values[y - 1] if y <= len(year_values) else 0.0
                    if growth_type == 4:
                        if m_in_year == 1:
                            nd["year_base_balance"] = base_balance
                        year_base = nd.get("year_base_balance", base_balance)
                        year_target = float(year_param) * unit_scale - year_base
                    else:
                        year_target = compute_year_target(
                            growth_type, year_param, base_balance, unit_scale,
                        )
                else:
                    year_target = 0.0

                # ===== 步骤 2：节奏权重 → 当月新增 =====
                rhythm_weight = weights[m_in_year - 1] if m_in_year <= len(weights) else 0.0
                # type 4 需要「剩余权重」（本月至年末的权重之和），用于按剩余缺口分摊
                remaining_weight = (
                    sum(weights[m_in_year - 1:]) if m_in_year <= len(weights) else 0.0
                )

                # ===== 当月投放（按增长方式名称判定是否回补到期）=====
                # 规则（业务口径 2026-10-21 确认）：
                #   「目标」类增长方式（growth_type 1 目标增长百分比、2 目标增长绝对值）
                #     → 当月新增加值 = 分摊的净增加值 + 当月到期释放
                #       即「到期回补」，保证余额净增长达到目标
                #   非「目标」类（3 增长百分比、4 增长值）
                #     → 当月新增加值 = 分摊的净增加值（不回补），到期自然出表
                #
                # v2.3：在 take_due 清零「之前」先快照计划到期额
                planned_due_k = peek_due(state, k)
                release = take_due(state, k)
                add, release, month_new = compute_month_new_v2(
                    growth_type, base_balance, year_target, rhythm_weight, release,
                    unit_scale=unit_scale, remaining_weight=remaining_weight,
                )
                nd["cum_planned"] = nd.get("cum_planned", 0.0) + month_new

                # ===== 步骤 3：按期限占比拆分 + 按绝对到期月落桶 =====
                #  第 k 月投放期限 v 的业务 → 直接落到 rem_m{k+v}
                #  v2.4：同时把落点累加进该节点的「完整 60 月排期」
                if is_configured and term_ratios:
                    apply_term_split(
                        state, month_new, term_ratios,
                        cur_month=k, full_plan=nd["full_plan"],
                    )

                # ===== 主表指标重算 =====
                if is_configured:
                    new_cb = base_balance + add
                    new_ab = state["avg_balance"] + add / 2.0
                    # ⚠️ 利率单位口径（曾导致月利息虚高 100 倍）：
                    #   prcp_data_basic.weighted_rate  存「小数」（0.045 = 4.5%）
                    #   prcp_sim_term_ratio.interest_rate 存「百分数」（3.5 = 3.5%）
                    #   两者直接相加会让新投放利率被放大 100 倍，
                    #   故此处统一除以 100 换算成小数后再加权。
                    weighted_amount = sum(
                        (month_new * float(r["business_ratio"]) / 100.0)
                        * (float(r.get("interest_rate", 0.0)) / 100.0)
                        for r in term_ratios
                    )
                    denom = state["avg_balance"] + month_new
                    new_wr = (
                        (state["avg_balance"] * state["weighted_rate"] + weighted_amount) / denom
                        if denom > 0 else state["weighted_rate"]
                    )
                    new_ia = new_ab * new_wr / 12.0
                else:
                    # 分支 A（存量保持）：余额与利率都不变，只滚桶
                    new_cb = base_balance
                    new_ab = state["avg_balance"]
                    new_wr = state["weighted_rate"]
                    new_ia = new_ab * new_wr / 12.0

                state["current_balance"] = new_cb
                state["avg_balance"] = new_ab
                state["weighted_rate"] = new_wr
                state["interest_amount"] = new_ia
                nd["state"] = state

                row = {
                    "sim_scheme_code": scheme_code,
                    "sim_scheme_id": scheme_id,
                    "run_id": run_id,
                    "data_date": data_date_k_str,
                    "date_offset": k,
                    "coa_scheme_id": coa_scheme_id,
                    "coa_node_id": nd["coa_node_id"],
                    "node_code": state.get("node_code", ""),
                    "node_name": state.get("node_name", ""),
                    "node_level": state.get("node_level", 0),
                    "category": state.get("category", ""),
                    "is_configured": 1 if is_configured else 0,
                    "is_aggregated": 0,
                    # v2.1：投放分解追溯字段
                    "growth_type": growth_type if is_configured else None,
                    "year_target": year_target if is_configured else None,
                    "rhythm_weight": rhythm_weight if is_configured else None,
                    "month_add": add if is_configured else None,
                    "month_release": release if is_configured else None,
                    # v2.3：计划到期（take_due 前快照，保留到期信息）+ 累计计划投放
                    "planned_due": (planned_due_k if is_configured else 0.0),
                    "cum_planned": (nd.get("cum_planned", 0.0) if is_configured else 0.0),
                }
                for col in all_cols:
                    row[col] = float(state.get(col, 0.0))

                # v2.4：rem_* 桶改由「完整 60 月排期」在**全部月份跑完后**统一回填
                #   （见循环后的 apply_final_plan），
                #   这样每一行（含 M1）都能看到「未来 5 年每月都有到期」的完整时间轴。

                if is_configured:
                    row["calc_note"] = (
                        f"M{k}={data_date_k_str}; y{y}m{m_in_year}; "
                        f"gt={growth_type}; w={rhythm_weight:.4f}%; "
                        f"add={add:.2f}; rel={release:.2f}"
                    )
                else:
                    row["calc_note"] = f"M{k}={data_date_k_str}; rolled-only (is_model_calc=2)"
                rows_k.append(row)

            # v2.4：先暂存，60 个月全部跑完、完整排期确定后再统一 INSERT
            all_rows.extend(rows_k)

            progress = int(k / month_count * 100)
            db.execute(
                text("UPDATE prcp_sim_run SET progress=:p, processed_nodes=:pn WHERE id=:id"),
                {"p": progress, "pn": len(nodes_data), "id": run_id},
            )

        # 5.5) v2.4：把「完整 60 月到期排期」回填到每个节点的每一行
        #   这样任意一行（含 M1）都能看到「未来 5 年每个月都有到期」，
        #   每个格子都有值（存量 + 全部 60 个月投放的落点）。
        plan_by_node = {
            nd["coa_node_id"]: nd["full_plan"]
            for nd in nodes_data if nd["is_configured"]
        }
        for r in all_rows:
            fp = plan_by_node.get(r["coa_node_id"])
            if fp:
                apply_final_plan(r, fp)
                r["calc_note"] = (
                    f"{r['calc_note']}; full_plan={len(fp)}M"
                )

        # 5.6) 统一 INSERT 全部结果行（叶子）
        if all_rows:
            for i in range(0, len(all_rows), 500):
                db.execute(text(insert_sql), all_rows[i:i + 500])

        # 6) 聚合 SUMMARY 节点：从所有后代叶子按 date_offset 聚合
        aggregated_count = _aggregate_summary_nodes(
            db=db,
            run_id=run_id,
            coa_scheme_id=coa_scheme_id,
            scheme_code=scheme_code,
            sim_scheme_id=scheme_id,
            base_date=data_date,
            month_count=month_count,
            insert_sql=insert_sql,
            all_cols=all_cols,
        )

        # 7) 更新 run 总节点数 = 叶子 + 汇总
        total_count = len(nodes_data) + aggregated_count
        db.execute(
            text("""UPDATE prcp_sim_run SET
                total_nodes=:tn, processed_nodes=:pn,
                configured_node_count=:cn, rolled_node_count=:rn,
                aggregated_node_count=:an
                WHERE id=:id"""),
            {
                "tn": total_count,
                "pn": total_count,
                "cn": configured_count,
                "rn": rolled_count,
                "an": aggregated_count,
                "id": run_id,
            },
        )

        # 8) 标记 SUCCESS
        db.execute(
            text("""UPDATE prcp_sim_run SET
                status='SUCCESS', progress=100, finished_at=NOW(),
                duration_ms=TIMESTAMPDIFF(MICROSECOND, started_at, NOW()) DIV 1000
                WHERE id=:id"""),
            {"id": run_id},
        )
        return run_id

    except Exception as e:
        db.execute(
            text("""UPDATE prcp_sim_run SET
                status='FAILED', finished_at=NOW(),
                error_message=:err
                WHERE id=:id"""),
            {"err": str(e)[:1000], "id": run_id},
        )
        raise


def _aggregate_summary_nodes(
    db: Session,
    run_id: int,
    coa_scheme_id: int,
    scheme_code: str,
    sim_scheme_id: int,
    base_date: date,
    month_count: int,
    insert_sql: str,
    all_cols: list,
) -> int:
    """递归聚合所有 SUMMARY 节点

    算法：
      对每个 SUMMARY 节点，用递归 CTE 查所有后代叶子节点（BUSINESS）
      按 date_offset 分组聚合：
        - current_balance = SUM(child.current)
        - avg_balance     = SUM(child.avg)
        - interest_amount = SUM(child.interest)
        - 加权利率        = SUM(child.current × child.wr) / SUM(child.current)
        - 各桶 orig_*/rem_* = SUM(child.bucket)
        - is_configured=0, is_aggregated=1
        - calc_note = "Aggregated from N leaves"

    返回聚合成功的 SUMMARY 节点数
    """
    # 汇总节点 = 所有「有子节点」且不是末级的节点（node_type='SUMMARY' 时也覆盖）
    summary_nodes = db.execute(
        text("""SELECT n.id, n.node_code, n.node_name, n.node_level,
                       (SELECT b.category FROM prcp_data_basic b
                        WHERE b.coa_node_id = n.id AND b.data_date = :bd AND b.is_deleted = 0
                        LIMIT 1) AS category
                FROM prcp_coa_node n
                WHERE n.scheme_id = :sid
                  AND (n.node_type = 'SUMMARY'
                       OR EXISTS (SELECT 1 FROM prcp_coa_node ch
                                  WHERE ch.parent_id = n.id AND ch.is_deleted = 0))
                ORDER BY n.node_level DESC"""),
        {"sid": coa_scheme_id, "bd": base_date.isoformat()},
    ).fetchall()

    if not summary_nodes:
        return 0

    # 聚合桶数据列
    bucket_sum_exprs = ", ".join(f"SUM(r.{c}) AS {c}" for c in (ORIG_COLS + REM_COLS))

    aggregated_count = 0

    for sn in summary_nodes:
        sn_id, sn_code, sn_name, sn_level, sn_cat = sn

        # 递归查所有后代叶子节点（只「最深的 BUSINESS」节点 — 即无子节点的）
        leaf_ids_rows = db.execute(
            text("""
                WITH RECURSIVE descendants AS (
                    SELECT id, parent_id FROM prcp_coa_node WHERE parent_id = :pid
                    UNION ALL
                    SELECT n.id, n.parent_id FROM prcp_coa_node n
                    JOIN descendants d ON n.parent_id = d.id
                )
                SELECT d.id FROM descendants d
                WHERE NOT EXISTS (
                    SELECT 1 FROM prcp_coa_node c WHERE c.parent_id = d.id
                )
                  AND d.id IN (SELECT id FROM prcp_coa_node WHERE scheme_id = :sid)
            """),
            {"pid": sn_id, "sid": coa_scheme_id},
        ).fetchall()

        leaf_ids = [r[0] for r in leaf_ids_rows]
        if not leaf_ids:
            continue

        # 按 date_offset 聚合
        leaf_placeholders = ",".join(str(i) for i in leaf_ids)
        agg_sql = f"""
            SELECT r.date_offset,
                   SUM(r.current_balance) AS agg_current,
                   SUM(r.avg_balance)     AS agg_avg,
                   SUM(r.interest_amount) AS agg_interest,
                   SUM(r.current_balance * r.weighted_rate) AS sum_weighted,
                   SUM(r.year_target)     AS agg_year_target,
                   SUM(r.month_add)       AS agg_month_add,
                   SUM(r.month_release)   AS agg_month_release,
                   {bucket_sum_exprs}
            FROM prcp_sim_result r
            WHERE r.run_id = :rid AND r.coa_node_id IN ({leaf_placeholders})
            GROUP BY r.date_offset
            ORDER BY r.date_offset
        """
        agg_rows = db.execute(text(agg_sql), {"rid": run_id}).fetchall()

        if not agg_rows:
            continue

        # 构造批量 INSERT 数据
        rows_to_insert = []
        for r in agg_rows:
            (date_offset, agg_current, agg_avg, agg_interest, sum_weighted,
             agg_year_target, agg_month_add, agg_month_release) = r[:8]
            # 加权利率：按当前余额加权
            agg_wr = float(sum_weighted) / float(agg_current) if agg_current and float(agg_current) > 0 else 0.0

            data_date_k = _add_months(base_date, date_offset)
            data_date_k_str = data_date_k.isoformat()

            row = {
                "sim_scheme_code": scheme_code,
                "sim_scheme_id": sim_scheme_id,
                "run_id": run_id,
                "data_date": data_date_k_str,
                "date_offset": date_offset,
                "coa_scheme_id": coa_scheme_id,
                "coa_node_id": sn_id,
                "node_code": sn_code,
                "node_name": sn_name,
                "node_level": sn_level,
                "category": sn_cat or "",
                "is_configured": 0,
                "is_aggregated": 1,
                "current_balance": float(agg_current) if agg_current else 0.0,
                "avg_balance": float(agg_avg) if agg_avg else 0.0,
                "weighted_rate": agg_wr,
                "interest_amount": float(agg_interest) if agg_interest else 0.0,
                # v2.1：汇总节点的投放分解 = 后代叶子之和
                "growth_type": None,
                "year_target": float(agg_year_target) if agg_year_target else 0.0,
                "rhythm_weight": None,
                "month_add": float(agg_month_add) if agg_month_add else 0.0,
                "month_release": float(agg_month_release) if agg_month_release else 0.0,
                # v2.3：计划到期汇总
                "planned_due": 0.0,
                "cum_planned": 0.0,
                "calc_note": f"Aggregated from {len(leaf_ids)} leaves; M{date_offset}={data_date_k_str}",
            }
            # 桶数据：r[8 .. 8+128)（前 8 列是聚合标量）
            for i, col in enumerate(ORIG_COLS + REM_COLS):
                v = r[8 + i]
                row[col] = float(v) if v is not None else 0.0
            rows_to_insert.append(row)

        if rows_to_insert:
            db.execute(text(insert_sql), rows_to_insert)
            aggregated_count += 1

    return aggregated_count


def cleanup_run_results(db: Session, sim_scheme_code: str, run_id: Optional[int] = None) -> int:
    """删除某 run_id（或某 scheme 所有）的 result

    返回删除的行数
    """
    if run_id:
        r = db.execute(
            text("DELETE FROM prcp_sim_result WHERE run_id=:rid"),
            {"rid": run_id},
        )
    else:
        r = db.execute(
            text("DELETE FROM prcp_sim_result WHERE sim_scheme_code=:sc"),
            {"sc": sim_scheme_code},
        )
    return r.rowcount
