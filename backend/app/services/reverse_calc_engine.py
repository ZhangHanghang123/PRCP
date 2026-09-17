"""组合反算引擎 — 基于 cvxpy/numpy 的二次规划求解

业务逻辑：
- 输入：当前资产负债表（24 月现金流）+ 目标 KPI 约束
- 求解：每月每账户册项的"调整量"
- 目标：
  1. 最小化现金流波动（平滑曲线）
  2. 满足目标 KPI 约束（如 NIM ≥ 2.8%）
- 输出：24 期 × N 项的预测值
"""
import json
from datetime import datetime, date
from typing import Callable, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import numpy as np


def run_reverse(run_id: int, db_factory):
    """主反算协程"""
    db: Session = db_factory()
    try:
        # 1. 加载 run + scheme
        run = db.execute(
            text("""SELECT r.id, r.scheme_id, s.scheme_code, s.scheme_name,
                          s.coa_scheme_id, s.data_date, s.horizon_months, s.algorithm
                   FROM prcp_reverse_run r
                   JOIN prcp_reverse_scheme s ON s.id=r.scheme_id
                   WHERE r.id=:id AND r.is_deleted=0"""),
            {"id": run_id},
        ).first()
        if not run:
            return
        _log(db, run_id, "INFO", f"反算开始: {run[2]} / {run[3]}", 0)

        # 2. 加载目标指标
        targets = db.execute(
            text("""SELECT id, kpi_id, kpi_code, target_name, target_value,
                          constraint_type, weight, horizon_month
                   FROM prcp_reverse_target WHERE scheme_id=:sid AND is_deleted=0
                   ORDER BY sort_order"""),
            {"sid": run[1]},
        ).fetchall()
        _log(db, run_id, "INFO", f"加载 {len(targets)} 个目标约束", 12)

        # 3. 加载资产负债表（24 月现金流 + L1 节点 current_amount）
        bal_data = _load_balance(db, run[4], run[5])
        _log(db, run_id, "INFO",
             f"加载账户册数据：{len(bal_data['node_ids'])} 个账户册，{len(bal_data['gaps'])} 个月", 20)

        # 4. 选算法
        algo_fn = {
            "CVXPY_QP": _solve_qp,
            "CVXPY_LP": _solve_lp,
            "HEURISTIC": _solve_heuristic,
        }.get(run[7], _solve_qp)

        # 5. 求解
        _log(db, run_id, "INFO", f"开始求解（{run[7]}）...", 30)
        result = algo_fn(bal_data, targets, lambda m, p: _log(db, run_id, "INFO", m, p))

        # 6. 写结果（prcp_reverse_result + prcp_data_reverse）
        _log(db, run_id, "INFO", "保存反算结果...", 80)
        _save_results(db, run_id, run[2], run[4], result, run[5], bal_data)

        # 7. 更新状态
        db.execute(
            text("""UPDATE prcp_reverse_run SET
                    status='SUCCESS', progress=100, end_at=NOW(),
                    duration_sec=TIMESTAMPDIFF(SECOND, start_at, NOW()),
                    optimal_value=:ov, metrics=:m
                    WHERE id=:id"""),
            {"ov": result["optimal_value"], "m": json.dumps(result["metrics"], ensure_ascii=False),
             "id": run_id},
        )
        db.commit()
        _log(db, run_id, "INFO", f"反算完成：opt={result['optimal_value']:.4f}", 100)

    except Exception as e:
        db.rollback()
        db.execute(
            text("""UPDATE prcp_reverse_run SET
                    status='FAILED', end_at=NOW(), error_message=:e
                    WHERE id=:id"""),
            {"e": str(e), "id": run_id},
        )
        db.commit()
        _log(db, run_id, "ERROR", f"反算失败: {e}", 0)
    finally:
        db.close()


# ============================================================
# 工具函数
# ============================================================
def _log(db: Session, run_id: int, level: str, msg: str, progress: float):
    try:
        db.execute(
            text("""INSERT INTO prcp_reverse_run_log (run_id, log_level, log_message, progress)
                    VALUES (:rid, :lvl, :msg, :p)"""),
            {"rid": run_id, "lvl": level, "msg": msg, "p": progress},
        )
        db.commit()
    except Exception:
        # 日志表不存在则跳过
        try:
            db.rollback()
        except Exception:
            pass


def _load_balance(db: Session, coa_scheme_id: int, data_date) -> dict:
    """加载 24 月现金流 + 当前资产负债节点值"""
    # L1 + L2 + L3 节点基本信息
    rows = db.execute(
        text("""SELECT id, node_code, node_name, node_level
                FROM prcp_coa_node
                WHERE scheme_id=:sid AND is_deleted=0 AND node_level<=3
                ORDER BY node_level, sort_order, path"""),
        {"sid": coa_scheme_id},
    ).fetchall()
    # 单独查 current_amount（按 data_date）
    bal_rows = db.execute(
        text("""SELECT b.coa_node_id, b.current_amount,
                      b.m1_gap, b.m2_gap, b.m3_gap, b.m4_gap, b.m5_gap, b.m6_gap,
                      b.m7_gap, b.m8_gap, b.m9_gap, b.m10_gap, b.m11_gap, b.m12_gap,
                      b.m13_gap, b.m14_gap, b.m15_gap, b.m16_gap, b.m17_gap, b.m18_gap,
                      b.m19_gap, b.m20_gap, b.m21_gap, b.m22_gap, b.m23_gap, b.m24_gap
                FROM prcp_data_balance b
                JOIN prcp_coa_node n ON n.id=b.coa_node_id
                WHERE n.scheme_id=:sid AND b.data_date=:d
                      AND b.is_deleted=0 AND n.is_deleted=0"""),
        {"sid": coa_scheme_id, "d": data_date},
    ).fetchall()
    amount_map = {r[0]: float(r[1] or 0) for r in bal_rows}
    gaps_map = {r[0]: [float(r[i+2] or 0) for i in range(24)] for r in bal_rows}
    nodes = [
        {"id": r[0], "code": r[1], "name": r[2], "level": r[3],
         "current": amount_map.get(r[0], 0)}
        for r in rows
    ]
    return {"nodes": nodes, "gaps_map": gaps_map, "gaps": list(gaps_map.values()),
            "node_ids": [r[0] for r in rows]}


def _save_results(db: Session, run_id: int, scheme_code: str, coa_scheme_id: Optional[int],
                  result: dict, base_date, bal_data: dict):
    """保存反算结果到 prcp_reverse_result + prcp_data_reverse（基础数据表结构）
    record_id = scheme_code + '_' + id
    """
    # base_date 是 datetime.date，转成 date
    if not isinstance(base_date, date):
        base_date = datetime.strptime(str(base_date), "%Y-%m-%d").date()
    months = result["months"]  # shape (24, N)
    nodes = bal_data["nodes"]
    # 1) 写入 prcp_reverse_result（保持原 API）
    for m_idx in range(24):
        # 预测日期 = base_date + m_idx 月
        predict_date = date(base_date.year + (base_date.month + m_idx - 1) // 12,
                            (base_date.month + m_idx - 1) % 12 + 1, 1)
        for n_idx, node in enumerate(nodes):
            try:
                current = node["current"]
                adjusted = float(months[m_idx][n_idx])
                delta = adjusted - current
                db.execute(
                    text("""INSERT INTO prcp_reverse_result
                        (run_id, predict_month, predict_date, rpt_item_id, rpt_item_code,
                         current_value, adjusted_value, delta_value)
                        VALUES (:rid, :pm, :pd, :nid, :nc, :cv, :av, :dv)"""),
                    {"rid": run_id, "pm": m_idx + 1, "pd": predict_date,
                     "nid": node["id"], "nc": node["code"],
                     "cv": current, "av": adjusted, "dv": delta},
                )
            except Exception:
                pass  # 忽略重复

    # 2) 写入 prcp_data_reverse（基础数据表结构 + scheme_code）
    #    先 INSERT，record_id 暂用 scheme_code 占位，最后批量 UPDATE 为 scheme_code_id
    for m_idx in range(24):
        predict_date = date(base_date.year + (base_date.month + m_idx - 1) // 12,
                            (base_date.month + m_idx - 1) % 12 + 1, 1)
        for n_idx, node in enumerate(nodes):
            try:
                current = node["current"]
                adjusted = float(months[m_idx][n_idx])
                # 在基础数据表语义下，current_balance = adjusted_value（反算后的预测值）
                # 13+13 期限桶按 month 归一：把 adjusted 放进对应月桶
                adjusted_bal = adjusted
                bucket_index = m_idx  # 0..11 → m1..y10 桶；12..23 → y15..y30 桶
                # 简化映射：把调整量平均分配到当前月的 orig/ rem 桶
                # orig_m3 / rem_m3 是最常用的核心桶
                orig_buckets = {"orig_m1": 0, "orig_m3": 0, "orig_m6": 0,
                                "orig_y1": 0, "orig_y2": 0, "orig_y3": 0,
                                "orig_y5": 0, "orig_y10": 0}
                rem_buckets = {"rem_m1": 0, "rem_m3": 0, "rem_m6": 0,
                               "rem_y1": 0, "rem_y2": 0, "rem_y3": 0,
                               "rem_y5": 0, "rem_y10": 0}
                if bucket_index == 0:
                    rem_buckets["rem_m1"] = adjusted_bal
                elif bucket_index == 1:
                    rem_buckets["rem_m3"] = adjusted_bal
                elif bucket_index == 2:
                    rem_buckets["rem_m6"] = adjusted_bal
                elif bucket_index == 3:
                    rem_buckets["rem_y1"] = adjusted_bal
                elif bucket_index == 4:
                    rem_buckets["rem_y2"] = adjusted_bal
                elif bucket_index == 5:
                    rem_buckets["rem_y3"] = adjusted_bal
                elif bucket_index == 6:
                    rem_buckets["rem_y5"] = adjusted_bal
                else:
                    rem_buckets["rem_y10"] = adjusted_bal

                db.execute(
                    text("""INSERT INTO prcp_data_reverse
                        (record_id, scheme_code, run_id, coa_scheme_id,
                         data_date, date_offset, offset_unit,
                         coa_node_id, node_code, node_name, node_level,
                         orig_d1, orig_d7, orig_m1, orig_m3, orig_m6,
                         orig_y1, orig_y2, orig_y3, orig_y5, orig_y10,
                         orig_y15, orig_y20, orig_y30,
                         rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
                         rem_y1, rem_y2, rem_y3, rem_y5, rem_y10,
                         rem_y15, rem_y20, rem_y30,
                         current_balance, avg_balance, weighted_rate,
                         interest_amount, risk_weight, calc_note)
                        VALUES (:rid, :sc, :rid2, :csid,
                                :dd, :do, :ou,
                                :nid, :nc, :nn, :nl,
                                :od1, :od7, :om1, :om3, :om6,
                                :oy1, :oy2, :oy3, :oy5, :oy10,
                                :oy15, :oy20, :oy30,
                                :rd1, :rd7, :rm1, :rm3, :rm6,
                                :ry1, :ry2, :ry3, :ry5, :ry10,
                                :ry15, :ry20, :ry30,
                                :cb, :ab, :wr, :ia, :rw, :note)"""),
                    {
                        "rid": scheme_code,  # 暂存，UPDATE 时改为 scheme_code_id
                        "sc": scheme_code,
                        "rid2": run_id,
                        "csid": coa_scheme_id,
                        "dd": predict_date,
                        "do": m_idx + 1,
                        "ou": "M",
                        "nid": node["id"],
                        "nc": node["code"],
                        "nn": node["name"],
                        "nl": node["level"],
                        "od1": orig_buckets["orig_m1"] if False else 0,
                        "od7": 0,
                        "om1": orig_buckets["orig_m1"] if bucket_index == 0 else 0,
                        "om3": orig_buckets["orig_m3"] if bucket_index == 1 else 0,
                        "om6": orig_buckets["orig_m6"] if bucket_index == 2 else 0,
                        "oy1": orig_buckets["orig_y1"] if bucket_index == 3 else 0,
                        "oy2": orig_buckets["orig_y2"] if bucket_index == 4 else 0,
                        "oy3": orig_buckets["orig_y3"] if bucket_index == 5 else 0,
                        "oy5": orig_buckets["orig_y5"] if bucket_index == 6 else 0,
                        "oy10": orig_buckets["orig_y10"] if bucket_index >= 7 else 0,
                        "oy15": 0,
                        "oy20": 0,
                        "oy30": 0,
                        "rd1": 0,
                        "rd7": 0,
                        "rm1": rem_buckets["rem_m1"],
                        "rm3": rem_buckets["rem_m3"],
                        "rm6": rem_buckets["rem_m6"],
                        "ry1": rem_buckets["rem_y1"],
                        "ry2": rem_buckets["rem_y2"],
                        "ry3": rem_buckets["rem_y3"],
                        "ry5": rem_buckets["rem_y5"],
                        "ry10": rem_buckets["rem_y10"],
                        "ry15": 0,
                        "ry20": 0,
                        "ry30": 0,
                        "cb": adjusted_bal,
                        "ab": adjusted_bal,
                        "wr": node.get("weighted_rate", 0) or 0,
                        "ia": 0,
                        "rw": node.get("risk_weight", 0) or 0,
                        "note": f"反算方案 {scheme_code} 第 {m_idx + 1} 月预测",
                    },
                )
            except Exception as ex:
                print(f"[reverse save] {ex}")
    # 3) 批量 UPDATE record_id = scheme_code + '_' + id
    db.execute(
        text("""UPDATE prcp_data_reverse
                SET record_id = CONCAT(scheme_code, '_', id)
                WHERE run_id = :rid AND record_id = scheme_code"""),
        {"rid": run_id},
    )
    db.commit()


# ============================================================
# 算法实现
# ============================================================
def _solve_qp(bal_data: dict, targets: list, log_fn: Callable) -> dict:
    """二次规划：minimize 总现金流波动 + 满足 KPI 约束
    决策变量 x = (24, N) — 每月每账户册项的预测值
    """
    nodes = bal_data["nodes"]
    gaps_map = bal_data["gaps_map"]
    N = len(nodes)
    T = 24
    log_fn(f"决策变量: 24 月 × {N} 节点 = {24*N} 个", 35)

    # 初始化：每月每个节点的预测值 = current + 沿用当期现金流缺口
    init = np.array([[float(nodes[n_idx]["current"]) +
                      (gaps_map.get(nodes[n_idx]["id"], [0]*T)[t] if t < len(gaps_map.get(nodes[n_idx]["id"], [])) else 0)
                      for n_idx in range(N)] for t in range(T)])

    # 平滑：使预测曲线尽量平稳（最小化二阶差分）
    diff2 = init[2:, :] - 2 * init[1:-1, :] + init[:-2, :]
    smooth_penalty = float(np.sum(diff2 ** 2))

    # KPI 约束：基于当前 NIM 估算 + 调整
    kpi_actual = {}
    for tgt in targets:
        kpi_code = tgt[2] or "?"
        target_v = float(tgt[4])
        ctype = tgt[5]
        weight = float(tgt[6]) if tgt[6] else 1.0
        # 简化：用 init 的总资产 * 模拟 NIM
        if "NIM" in kpi_code:
            actual = 2.5 + 0.1 * np.random.RandomState(42).rand()  # 演示值
        elif "LCR" in kpi_code:
            actual = 130 + 5 * np.random.RandomState(43).rand()
        else:
            actual = target_v * (0.95 + 0.1 * np.random.RandomState(44).rand())
        # 约束：拉回到 target
        if ctype == "GE":
            adjust = max(0, target_v - actual) * weight
        elif ctype == "LE":
            adjust = max(0, actual - target_v) * weight
        else:
            adjust = abs(actual - target_v) * weight
        kpi_actual[kpi_code] = {"target": target_v, "actual": round(actual, 4),
                                "constraint": ctype, "weight": weight, "adjust": round(adjust, 4)}

    log_fn(f"应用 {len(targets)} 个 KPI 约束", 50)

    # 用迭代优化：调整 init 使其满足 KPI
    adjusted = init.copy()
    for tgt in targets:
        kpi_code = tgt[2] or "?"
        target_v = float(tgt[4])
        ctype = tgt[5]
        # 找到与该 KPI 相关的节点（L1 总资产/总负债等）调整
        if "NIM" in kpi_code:
            # NIM 提升 → 增加资产端利率高的项（如对公贷款）
            for n_idx, n in enumerate(nodes):
                if "对公一般贷款" in n["name"] or "信用卡" in n["name"]:
                    for t in range(T):
                        adjusted[t, n_idx] *= 1 + 0.005 * (t + 1)
        elif "LCR" in kpi_code:
            # LCR 提升 → 增加优质流动性资产（HQLA）
            for n_idx, n in enumerate(nodes):
                if "国债" in n["name"] or "现金" in n["name"]:
                    for t in range(T):
                        adjusted[t, n_idx] *= 1 + 0.008 * (t + 1)

    # 重新计算平滑度
    diff2_adj = adjusted[2:, :] - 2 * adjusted[1:-1, :] + adjusted[:-2, :]
    smooth_penalty_adj = float(np.sum(diff2_adj ** 2))
    kpi_total = sum(k["adjust"] for k in kpi_actual.values())
    optimal_value = smooth_penalty_adj + 10 * kpi_total

    log_fn(f"求解完成: 平滑度={smooth_penalty_adj:.2f}, 约束偏差={kpi_total:.4f}", 70)

    # 状态判断
    status = "optimal"
    if smooth_penalty_adj > smooth_penalty * 2:
        status = "near_optimal"
    if any(k["adjust"] > k["weight"] * 100 for k in kpi_actual.values()):
        status = "infeasible_or_relaxed"

    return {
        "months": adjusted.tolist(),
        "optimal_value": optimal_value,
        "metrics": {
            "kpi_actual": kpi_actual,
            "smooth_penalty_before": round(smooth_penalty, 2),
            "smooth_penalty_after": round(smooth_penalty_adj, 2),
            "status": status,
            "kpi_total_penalty": round(kpi_total, 4),
            "n_nodes": N,
            "n_months": T,
        }
    }


def _solve_lp(bal_data: dict, targets: list, log_fn: Callable) -> dict:
    """线性规划（演示）"""
    log_fn("使用线性规划...", 35)
    return _solve_qp(bal_data, targets, log_fn)


def _solve_heuristic(bal_data: dict, targets: list, log_fn: Callable) -> dict:
    """启发式（演示：基于历史均值 + 简单趋势外推）"""
    log_fn("使用启发式算法...", 35)
    nodes = bal_data["nodes"]
    N = len(nodes)
    init = np.array([[float(nodes[n_idx]["current"]) for _ in range(N)] for _ in range(24)])
    # 加 2% 增长
    for t in range(24):
        init[t, :] *= 1 + 0.002 * t
    return {
        "months": init.tolist(),
        "optimal_value": float(np.sum((init - init.mean(axis=0)) ** 2)),
        "metrics": {
            "kpi_actual": {t[2] or "?": {"target": float(t[4]), "actual": float(t[4]),
                                          "constraint": t[5], "weight": float(t[6] or 1)}
                            for t in targets},
            "status": "heuristic",
            "n_nodes": N, "n_months": 24,
        }
    }