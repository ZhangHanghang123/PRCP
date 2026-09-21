"""新业务模拟引擎 v1 — 5 步按月滚动算法

输入：sim_scheme_id, month_count=24
输出：prcp_sim_run + prcp_sim_result

算法 5 步（详见 docs/新业务模拟_引擎算法_v1.md）：
  1. 取基础数据 (prcp_data_basic[T月])
  2. 算当月新增量 = rem_m1 + net_new
  3. 按期限拆分 term_ratios 叠加到 orig_mv + rem_mv
  4. 桶往前推一月（m1..m59 → m0..m58 + 长端自循环）
  5. 主指标重算（current/avg/weighted/interest）
"""
from typing import Dict, List, Optional, Tuple
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.buckets import BUCKETS, KEYS, ORIG_COLS, REM_COLS

# 期限月份数映射（term_value → bucket key）
TERM_TO_KEY = {n: f"m{n}" for n in range(1, 61)}
TERM_TO_KEY[60] = "m60"  # 业务期限最大 60 月，对应 m60 桶


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
    # 查询基础数据表 + JOIN prcp_coa_node 取节点元数据
    # （prcp_data_basic 旧数据这些字段是 NULL，需要从 coa_node 取）
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

    # 64+64 桶
    state = {}
    for i, col in enumerate(ORIG_COLS):
        state[col] = float(row[i]) if row[i] is not None else 0.0
    offset = len(ORIG_COLS)
    for i, col in enumerate(REM_COLS):
        state[col] = float(row[offset + i]) if row[offset + i] is not None else 0.0
    offset += len(REM_COLS)
    # 4 主指标
    state["current_balance"] = float(row[offset]) if row[offset] is not None else 0.0
    state["avg_balance"] = float(row[offset + 1]) if row[offset + 1] is not None else 0.0
    state["weighted_rate"] = float(row[offset + 2]) if row[offset + 2] is not None else 0.0
    state["interest_amount"] = float(row[offset + 3]) if row[offset + 3] is not None else 0.0
    # 元数据（从 prcp_coa_node JOIN 取）
    # SQL 返回顺序：node_code, node_name, node_level, parent_id, coa_scheme_id, category
    meta = offset + 4
    state["node_code"] = row[meta] or ""
    state["node_name"] = row[meta + 1] or ""
    state["node_level"] = int(row[meta + 2]) if row[meta + 2] is not None else 0
    state["parent_id"] = int(row[meta + 3]) if row[meta + 3] is not None else None
    state["coa_scheme_id"] = int(row[meta + 4]) if row[meta + 4] is not None else 0
    state["category"] = row[meta + 5] or ""
    state["parent_code"] = ""  # 服务器 prcp_coa_node 无此字段，留空
    state["is_leaf"] = 1  # 引擎只对叶子节点配置，此处固定为 1

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
      新 m_v (1..59) = 旧 m_(v+1)   # m1 接收旧 m2，..., m59 接收旧 m60
      新 m60 = 旧 y10 / 60         # 5-10 年区间过了一个月，1/60 滚到 m60

    长端桶（自循环）：
      新 y10 = 旧 y10 - 旧 y10/60 + 旧 y15/120
      新 y15 = 旧 y15 - 旧 y15/120 + 旧 y20/120
      新 y20 = 旧 y20 - 旧 y20/120 + 旧 y30/240
      新 y30 = 旧 y30 - 旧 y30/240

    同样的逻辑应用到 rem_* 桶
    """
    new_state = dict(state)  # 浅拷贝（含元数据 + 主指标）

    # 原始期限月桶
    for v in range(1, 60):  # 1..59
        new_state[f"orig_m{v}"] = state[f"orig_m{v+1}"]
    # 原始期限长端
    new_state["orig_m60"] = state["orig_y10"] / 60.0
    new_state["orig_y10"] = state["orig_y10"] - state["orig_y10"] / 60.0 + state["orig_y15"] / 120.0
    new_state["orig_y15"] = state["orig_y15"] - state["orig_y15"] / 120.0 + state["orig_y20"] / 120.0
    new_state["orig_y20"] = state["orig_y20"] - state["orig_y20"] / 120.0 + state["orig_y30"] / 240.0
    new_state["orig_y30"] = state["orig_y30"] - state["orig_y30"] / 240.0

    # 剩余期限月桶
    for v in range(1, 60):
        new_state[f"rem_m{v}"] = state[f"rem_m{v+1}"]
    # 剩余期限长端
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
    monthly_rate = annual_growth_rate / 100.0 / 12.0  # 百分比 → 月小数

    # 1) 当前余额
    new_current = cur * (1.0 + monthly_rate)

    # 2) 平均余额
    new_avg = avg + cur * monthly_rate / 2.0

    # 3) 加权平均利率 = (avg × wr + Σ(amount × rate)) / (avg + month_new)
    weighted_amount = sum(
        (month_new * float(r["business_ratio"]) / 100.0) * float(r.get("interest_rate", 0.0))
        for r in term_ratios
    )
    denom = avg + month_new
    if denom > 0:
        new_wr = (avg * wr + weighted_amount) / denom
    else:
        new_wr = wr  # 退化情况

    # 4) 当月利息
    new_interest = new_avg * new_wr / 12.0

    return new_current, new_avg, new_wr, new_interest


# ============================================================
# 主循环：run_engine
# ============================================================
def run_engine(
    db: Session,
    scheme_id: int,
    user: dict,
    month_count: int = 24,
) -> int:
    """执行引擎，返回 run_id

    步骤：
    1) 创建 prcp_sim_run 记录 (status=RUNNING)
    2) 取方案基础信息 (coa_scheme_id, data_date)
    3) 取所有已配置的节点（按 sim_node_config）
    4) 取每个节点的初始状态 (prcp_data_basic)
    5) 按月滚动 (1..month_count)
    6) 批量 INSERT prcp_sim_result
    7) 更新 run 状态 (SUCCESS / FAILED)
    """
    from datetime import datetime

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

    # 2) 创建 run
    uid = _uid(user)
    target_date = _add_months(data_date, month_count)
    run_id = db.execute(
        text("""INSERT INTO prcp_sim_run
            (sim_scheme_id, sim_scheme_code, base_data_date, month_count,
             target_data_date, status, progress, total_nodes, processed_nodes,
             started_at, created_by)
            VALUES (:sid, :sc, :bd, :mc, :td, 'RUNNING', 0, 0, 0, NOW(), :u)"""),
        {
            "sid": scheme_id, "sc": scheme_code, "bd": data_date.isoformat(),
            "mc": month_count, "td": target_date.isoformat(), "u": uid,
        },
    ).lastrowid

    try:
        # 3) 取所有已配置的节点
        configs = db.execute(
            text("""SELECT c.id AS cfg_id, c.coa_node_id, c.coa_node_code,
                           c.annual_growth_rate,
                           n.node_code, n.node_name, n.node_level, n.parent_id, n.path
                    FROM prcp_sim_node_config c
                    JOIN prcp_coa_node n ON n.id = c.coa_node_id
                    WHERE c.scheme_id=:sid AND c.is_deleted=0
                    ORDER BY c.id"""),
            {"sid": scheme_id},
        ).fetchall()
        if not configs:
            raise ValueError("方案下无任何节点配置，请先在参数配置页设置")

        total_nodes = len(configs)

        # 取每个节点的 term_ratios
        cfg_ids = [c[0] for c in configs]
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

        # 4) 取每个节点的初始状态
        nodes_data = []
        for c in configs:
            cfg_id, coa_node_id, coa_node_code, growth_rate, node_code, node_name, node_level, parent_id, path = c
            init_state = get_initial_state(db, coa_node_id, data_date.isoformat())
            if init_state is None:
                # 跳过无基础数据的节点
                continue
            nodes_data.append({
                "cfg_id": cfg_id,
                "coa_node_id": coa_node_id,
                "growth_rate": float(growth_rate) if growth_rate else 0.0,
                "term_ratios": ratios_by_cfg.get(cfg_id, []),
                "state": init_state,
            })

        if not nodes_data:
            raise ValueError(f"所有节点在 {data_date.isoformat()} 月均无基础数据，请先维护 prcp_data_basic")

        # 更新 run.total_nodes
        db.execute(
            text("UPDATE prcp_sim_run SET total_nodes=:n WHERE id=:id"),
            {"n": len(nodes_data), "id": run_id},
        )

        # 5) 按月滚动
        # 预编译 INSERT 语句（动态列名 + VALUES 占位符）
        all_cols = ORIG_COLS + REM_COLS + [
            "current_balance", "avg_balance", "weighted_rate", "interest_amount",
        ]
        insert_cols = [
            "sim_scheme_code", "sim_scheme_id", "run_id",
            "data_date", "date_offset",
            "coa_scheme_id", "coa_node_id", "node_code", "node_name",
            "node_level", "category",
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

                # 步骤 2
                net_new, month_new = compute_month_new(state, growth_rate)

                # 步骤 3（加新业务到 orig/ rem 桶）
                apply_term_split(state, month_new, term_ratios)

                # 步骤 4（桶往前推）
                state = roll_one_month(state)

                # 步骤 5（主指标重算）
                new_cb, new_ab, new_wr, new_ia = compute_main_metrics(
                    state, growth_rate, term_ratios, net_new, month_new,
                )
                state["current_balance"] = new_cb
                state["avg_balance"] = new_ab
                state["weighted_rate"] = new_wr
                state["interest_amount"] = new_ia
                nd["state"] = state

                # 组装 INSERT 行
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
                }
                for col in all_cols:
                    row[col] = float(state.get(col, 0.0))
                row["calc_note"] = f"M{k}={data_date_k_str}; growth={growth_rate}%"
                rows_k.append(row)

            # 批量 INSERT（单月所有节点一次提交）
            if rows_k:
                db.execute(text(insert_sql), rows_k)

            # 更新进度
            progress = int(k / month_count * 100)
            db.execute(
                text("UPDATE prcp_sim_run SET progress=:p, processed_nodes=:pn WHERE id=:id"),
                {"p": progress, "pn": len(nodes_data), "id": run_id},
            )

        # 6) 标记 SUCCESS
        db.execute(
            text("""UPDATE prcp_sim_run SET
                status='SUCCESS', progress=100, finished_at=NOW(),
                duration_ms=TIMESTAMPDIFF(MICROSECOND, started_at, NOW()) DIV 1000
                WHERE id=:id"""),
            {"id": run_id},
        )
        return run_id

    except Exception as e:
        # 标记 FAILED
        db.execute(
            text("""UPDATE prcp_sim_run SET
                status='FAILED', finished_at=NOW(),
                error_message=:err
                WHERE id=:id"""),
            {"err": str(e)[:1000], "id": run_id},
        )
        raise


# ============================================================
# 删除旧 run 的所有 result（重跑前清理）
# ============================================================
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
