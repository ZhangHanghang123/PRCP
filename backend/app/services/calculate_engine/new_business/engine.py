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

        base_cols = """r.id, r.sim_scheme_code, r.run_id, r.data_date, r.date_offset,
                      r.coa_scheme_id, r.coa_node_id, r.node_code, r.node_name,
                      r.node_level, r.category, r.is_configured, r.is_aggregated,
                      r.current_balance, r.avg_balance, r.weighted_rate, r.interest_amount,
                      r.calc_note"""
        if with_buckets:
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
        # base_cols 含 18 个字段（id..calc_note），桶数据从 idx=18 开始
        bucket_idx_start = 18

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
                "calc_note": r[17],
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
# 步骤 3：按期限拆分 + 叠加
# ============================================================
def apply_term_split(
    state: Dict, month_new: float, term_ratios: List[Dict]
) -> List[Tuple[str, float, float]]:
    """遍历 term_ratios，amount_v = month_new × business_ratio% / 100

    加到 orig_mv + rem_mv
    返回 [(term_value, amount, interest_rate), ...] 用于加权平均利率计算
    """
    additions = []
    for ratio in term_ratios:
        v = int(ratio["term_value"])
        b_pct = float(ratio["business_ratio"])
        r = float(ratio.get("interest_rate", 0.0))
        amount_v = month_new * b_pct / 100.0
        if v in TERM_TO_KEY:
            key = TERM_TO_KEY[v]
            state[f"orig_{key}"] = state.get(f"orig_{key}", 0.0) + amount_v
            state[f"rem_{key}"] = state.get(f"rem_{key}", 0.0) + amount_v
            additions.append((str(v), amount_v, r))
    return additions


# ============================================================
# 步骤 4：桶往前推一月
# ============================================================
def roll_one_month(state: Dict) -> Dict:
    """所有桶往前推一月：

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
      3) 取账户册下所有「有基础数据」+「叶子节点」(node_type='BUSINESS')
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
        # 2) 只取叶子节点（node_type='BUSINESS'）+ LEFT JOIN 配置信息
        leaf_nodes = db.execute(
            text("""SELECT n.id AS coa_node_id, n.node_code, n.node_name,
                           n.node_level, n.parent_id, n.path,
                           c.id AS cfg_id, c.annual_growth_rate
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
                      AND n.node_type = 'BUSINESS'
                    ORDER BY n.path, n.id"""),
            {"sid": scheme_id, "bd": data_date.isoformat(), "coa_sid": coa_scheme_id},
        ).fetchall()

        if not leaf_nodes:
            raise ValueError(
                f"账户册 id={coa_scheme_id} 下没有任何 BUSINESS 节点在 {data_date.isoformat()} 月有基础数据，"
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

        # 4) 取每个叶子节点的初始状态 + 区分配置/未配置
        nodes_data = []
        configured_count = 0
        rolled_count = 0
        for row in leaf_nodes:
            coa_node_id, node_code, node_name, node_level, parent_id, path, cfg_id, growth_rate = row
            init_state = get_initial_state(db, coa_node_id, data_date.isoformat())
            if init_state is None:
                continue

            is_configured = cfg_id is not None
            if is_configured:
                configured_count += 1
                gr = float(growth_rate) if growth_rate else 0.0
                tr = ratios_by_cfg.get(cfg_id, [])
            else:
                rolled_count += 1
                gr = 0.0
                tr = []

            nodes_data.append({
                "coa_node_id": coa_node_id,
                "is_configured": is_configured,
                "growth_rate": gr,
                "term_ratios": tr,
                "state": init_state,
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
        ] + all_cols + ["calc_note"]
        placeholders = ", ".join(f":{c}" for c in insert_cols)
        col_list = ", ".join(insert_cols)
        insert_sql = f"INSERT INTO prcp_sim_result ({col_list}) VALUES ({placeholders})"

        for k in range(1, month_count + 1):
            data_date_k = _add_months(data_date, k)
            data_date_k_str = data_date_k.isoformat()
            rows_k = []

            for nd in nodes_data:
                state = nd["state"]
                growth_rate = nd["growth_rate"]
                term_ratios = nd["term_ratios"]
                is_configured = nd["is_configured"]

                net_new, month_new = compute_month_new(state, growth_rate)

                if is_configured and term_ratios:
                    apply_term_split(state, month_new, term_ratios)

                state = roll_one_month(state)
                new_cb, new_ab, new_wr, new_ia = compute_main_metrics(
                    state, growth_rate, term_ratios, net_new, month_new,
                )
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
                }
                for col in all_cols:
                    row[col] = float(state.get(col, 0.0))
                if is_configured:
                    row["calc_note"] = f"M{k}={data_date_k_str}; growth={growth_rate}%; configured"
                else:
                    row["calc_note"] = f"M{k}={data_date_k_str}; growth=0.0%; rolled-only"
                rows_k.append(row)

            if rows_k:
                db.execute(text(insert_sql), rows_k)

            progress = int(k / month_count * 100)
            db.execute(
                text("UPDATE prcp_sim_run SET progress=:p, processed_nodes=:pn WHERE id=:id"),
                {"p": progress, "pn": len(nodes_data), "id": run_id},
            )

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
    summary_nodes = db.execute(
        text("""SELECT n.id, n.node_code, n.node_name, n.node_level,
                       (SELECT b.category FROM prcp_data_basic b
                        WHERE b.coa_node_id = n.id AND b.data_date = :bd AND b.is_deleted = 0
                        LIMIT 1) AS category
                FROM prcp_coa_node n
                WHERE n.scheme_id = :sid AND n.node_type = 'SUMMARY'
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

        # 递归查所有后代叶子节点（只 BUSINESS）
        leaf_ids_rows = db.execute(
            text("""
                WITH RECURSIVE descendants AS (
                    SELECT id, parent_id FROM prcp_coa_node WHERE parent_id = :pid
                    UNION ALL
                    SELECT n.id, n.parent_id FROM prcp_coa_node n
                    JOIN descendants d ON n.parent_id = d.id
                )
                SELECT id FROM prcp_coa_node
                WHERE id IN (SELECT id FROM descendants)
                  AND scheme_id = :sid AND node_type = 'BUSINESS'
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
            date_offset, agg_current, agg_avg, agg_interest, sum_weighted = r[:5]
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
                "calc_note": f"Aggregated from {len(leaf_ids)} leaves; M{date_offset}={data_date_k_str}",
            }
            # 桶数据：r[5..5+128)
            for i, col in enumerate(ORIG_COLS + REM_COLS):
                v = r[5 + i]
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
