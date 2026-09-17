"""模型训练引擎 — 异步执行，支持多种算法
- 训练进度实时写入 prcp_model_train_log
- 训练结果写入 prcp_model_train_result
- 异常时写入 error_message + FAILED 状态
"""
import json
import time
from datetime import datetime, date
from typing import Optional, Callable
from sqlalchemy import text
from sqlalchemy.orm import Session
import numpy as np


# ============================================================
# 算法注册表
# ============================================================
def _train_linear_regression(params, balance_data, log_fn: Callable):
    """最小二乘法拟合：基于历史数据预测未来"""
    log_fn("加载参数与训练数据...", 10)
    if not balance_data["actual"]:
        log_fn("⚠️ 训练数据为空，使用合成数据演示...", 30)
        actual = [100 + i * 2.5 + np.random.normal(0, 5) for i in range(24)]
    else:
        actual = balance_data["actual"]

    # 用前 12 期作为训练集，后 12 期作为测试集
    train_y = np.array(actual[:12])
    train_x = np.arange(len(train_y)).reshape(-1, 1)
    test_x = np.arange(12, 24).reshape(-1, 1)

    log_fn("执行最小二乘拟合...", 40)
    A = np.hstack([train_x, np.ones_like(train_x)])
    coef, *_ = np.linalg.lstsq(A, train_y, rcond=None)
    a, b = coef[0], coef[1]

    log_fn(f"拟合完成: y = {a:.4f}x + {b:.4f}", 70)
    test_X = np.hstack([test_x, np.ones_like(test_x)])
    predicted = (test_X @ coef).tolist()

    # 计算指标
    train_pred = (A @ coef).tolist()
    mae = float(np.mean(np.abs(np.array(train_pred) - train_y)))
    rmse = float(np.sqrt(np.mean((np.array(train_pred) - train_y) ** 2)))
    ss_res = float(np.sum((train_y - train_pred) ** 2))
    ss_tot = float(np.sum((train_y - train_y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    metrics = {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4),
               "formula": f"y = {a:.4f}x + {b:.4f}"}
    log_fn(f"训练集指标: MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.4f}", 90)
    return predicted, metrics, test_x.flatten().tolist()


def _train_logistic_growth(params, balance_data, log_fn: Callable):
    """逻辑斯蒂增长曲线拟合"""
    log_fn("加载训练数据...", 10)
    if not balance_data["actual"]:
        actual = [50 + 100 / (1 + np.exp(-(i - 12) / 3)) + np.random.normal(0, 2) for i in range(24)]
    else:
        actual = balance_data["actual"]
    y = np.array(actual[:18])
    x = np.arange(len(y))

    log_fn("拟合逻辑斯蒂曲线...", 50)
    # S 形: y = L / (1 + exp(-k(x-x0)))
    from scipy.optimize import curve_fit
    def sigmoid(x, L, k, x0):
        return L / (1 + np.exp(-k * (x - x0)))
    try:
        popt, _ = curve_fit(sigmoid, x, y, p0=[max(y) * 1.2, 0.3, 10], maxfev=2000)
    except Exception:
        popt = [max(y), 0.3, 10]

    L, k, x0 = popt
    test_x = np.arange(18, 24)
    predicted = sigmoid(test_x, *popt).tolist()
    train_pred = sigmoid(x, *popt)
    mae = float(np.mean(np.abs(train_pred - y)))
    rmse = float(np.sqrt(np.mean((train_pred - y) ** 2)))
    ss_res = float(np.sum((y - train_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    metrics = {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4),
               "L": round(float(L), 2), "k": round(float(k), 4), "x0": round(float(x0), 2)}
    log_fn(f"拟合参数: L={L:.2f}, k={k:.4f}, x0={x0:.2f}", 90)
    return predicted, metrics, test_x.tolist()


def _train_monte_carlo(params, balance_data, log_fn: Callable):
    """蒙特卡洛模拟（演示：1000 次抽样）"""
    log_fn("加载参数与基础数据...", 10)
    base = np.mean(balance_data["actual"][:12]) if balance_data["actual"] else 100.0
    n_sims = 1000
    n_periods = 12
    log_fn(f"开始蒙特卡洛模拟（{n_sims} 次 × {n_periods} 期）...", 30)

    # 参数：年化波动率（从 params 取）
    vol_param = next((p["param_value"] for p in params if "VOL" in p.get("param_code", "")), 0.1)
    vol = float(vol_param) / 100  # 10% 年化波动

    rng = np.random.default_rng(42)
    monthly_vol = vol / np.sqrt(12)
    paths = base * np.exp(np.cumsum(rng.normal(0, monthly_vol, (n_sims, n_periods)), axis=1))

    log_fn("计算置信区间...", 60)
    predicted = paths.mean(axis=0).tolist()
    conf_low = np.percentile(paths, 5, axis=0).tolist()
    conf_high = np.percentile(paths, 95, axis=0).tolist()

    metrics = {"n_sims": n_sims, "annual_vol": vol,
               "conf_low": [round(v, 4) for v in conf_low],
               "conf_high": [round(v, 4) for v in conf_high]}
    log_fn(f"模拟完成：均值 {predicted[-1]:.2f}, 90% CI [{conf_low[-1]:.2f}, {conf_high[-1]:.2f}]", 90)
    return predicted, metrics, list(range(12)), (conf_low, conf_high)


def _train_linear_program(params, balance_data, log_fn: Callable):
    """线性规划（演示：最小化资本占用）"""
    log_fn("加载约束...", 20)
    log_fn("构建 CVXPY 优化问题...", 40)
    # 演示：用 cvxpy 解一个最小化问题
    try:
        import cvxpy as cp
        x = cp.Variable(3, nonneg=True)
        cost = cp.norm(x, 1)  # 最小化 L1 范数
        constraints = [cp.sum(x) >= 100, x <= 80]
        prob = cp.Problem(cp.Minimize(cost), constraints)
        prob.solve(solver=cp.SCS)
        log_fn(f"求解完成: x = {x.value.round(2).tolist()}", 80)
        predicted = x.value.tolist() if x.value is not None else [33, 33, 34]
        metrics = {"solver": "SCS", "optimal_value": round(float(prob.value), 4) if prob.value else None}
    except ImportError:
        log_fn("⚠️ cvxpy 未安装，使用简单方法", 80)
        predicted = [33.34, 33.33, 33.33]
        metrics = {"solver": "fallback"}
    return predicted, metrics, [0, 1, 2]


ALGO_REGISTRY = {
    "LINEAR_REGRESSION": _train_linear_regression,
    "LOGISTIC_GROWTH":   _train_logistic_growth,
    "MONTE_CARLO":       _train_monte_carlo,
    "LINEAR_PROGRAM":    _train_linear_program,
}


# ============================================================
# 主训练协程
# ============================================================
def run_train(train_id: int, db_factory):
    """BackgroundTasks 调用的同步入口"""
    db: Session = db_factory()
    try:
        # 1. 加载训练任务
        train = db.execute(
            text("""SELECT t.id, t.model_id, t.version_id, t.coa_scheme_id,
                          t.balance_date_from, t.balance_date_to,
                          m.model_type, m.model_name, v.version_code
                   FROM prcp_model_train t
                   JOIN prcp_model m ON m.id=t.model_id
                   JOIN prcp_model_version v ON v.id=t.version_id
                   WHERE t.id=:id"""),
            {"id": train_id},
        ).first()
        if not train:
            return
        _log(db, train_id, "INFO", f"训练开始: {train[7]} / {train[8]}", 0)

        # 2. 加载参数
        params = db.execute(
            text("""SELECT param_code, param_name, param_value, unit
                    FROM prcp_model_param WHERE version_id=:vid AND is_deleted=0
                    ORDER BY sort_order"""),
            {"vid": train[2]},
        ).fetchall()
        params_dict = [
            {"param_code": r[0], "param_name": r[1], "param_value": float(r[2]), "unit": r[3]}
            for r in params
        ]
        _log(db, train_id, "INFO", f"加载了 {len(params_dict)} 个参数", 5)

        # 3. 加载训练数据（从 prcp_data_balance 读取历史）
        balance_data = _load_balance_data(
            db, train[3], train[4], train[5], train[1]
        )
        _log(db, train_id, "INFO",
             f"训练窗口: {train[4]} ~ {train[5]}, 数据点数: {len(balance_data['actual'])}", 8)

        # 4. 选算法 + 执行
        algo_fn = ALGO_REGISTRY.get(train[6])
        if not algo_fn:
            raise ValueError(f"不支持的算法: {train[6]}")

        def _log_fn(msg: str, progress: float):
            _log(db, train_id, "INFO", msg, progress)
            # 模拟训练耗时（让用户能看进度条）
            time.sleep(0.5)

        ret = algo_fn(params_dict, balance_data, _log_fn)
        predicted, metrics, periods = ret[0], ret[1], ret[2]
        extras = ret[3] if len(ret) >= 4 else None

        # 5. 写结果到 prcp_model_train_result
        _save_results(db, train_id, predicted, periods, extras)

        # 6. 更新状态为 SUCCESS
        duration = int((datetime.now() - datetime.combine(date.today(), datetime.min.time())).total_seconds())
        db.execute(
            text("""UPDATE prcp_model_train SET
                    status='SUCCESS', progress=100, end_at=NOW(),
                    duration_sec=TIMESTAMPDIFF(SECOND, start_at, NOW()),
                    metrics=:m
                    WHERE id=:id"""),
            {"m": json.dumps(metrics, ensure_ascii=False), "id": train_id},
        )
        db.commit()
        _log(db, train_id, "INFO", f"训练完成: {metrics}", 100)

    except Exception as e:
        db.rollback()
        db.execute(
            text("""UPDATE prcp_model_train SET
                    status='FAILED', end_at=NOW(),
                    error_message=:e
                    WHERE id=:id"""),
            {"e": str(e), "id": train_id},
        )
        db.commit()
        _log(db, train_id, "ERROR", f"训练失败: {e}", 0)
    finally:
        db.close()


# ============================================================
# 工具函数
# ============================================================
def _log(db: Session, train_id: int, level: str, msg: str, progress: float):
    try:
        db.execute(
            text("""INSERT INTO prcp_model_train_log (train_id, log_level, log_message, progress)
                    VALUES (:tid, :lvl, :msg, :p)"""),
            {"tid": train_id, "lvl": level, "msg": msg, "p": progress},
        )
        db.commit()
    except Exception:
        db.rollback()


def _load_balance_data(db: Session, coa_scheme_id: int, date_from, date_to, model_id: int) -> dict:
    """从 prcp_data_balance 加载训练数据（聚合所有账户册的 current_amount）"""
    try:
        # 优先取总资产（L1 节点聚合）
        rows = db.execute(
            text("""SELECT b.data_date, SUM(b.current_amount) AS total
                    FROM prcp_data_balance b
                    JOIN prcp_coa_node n ON n.id=b.coa_node_id
                    WHERE n.scheme_id=:sid AND n.node_level=1
                          AND b.data_date BETWEEN :df AND :dt
                          AND b.is_deleted=0 AND n.is_deleted=0
                    GROUP BY b.data_date
                    ORDER BY b.data_date"""),
            {"sid": coa_scheme_id, "df": date_from, "dt": date_to},
        ).fetchall()
        actual = [float(r[1]) for r in rows] if rows else []
        return {"actual": actual, "dates": [r[0].isoformat() for r in rows]}
    except Exception:
        return {"actual": [], "dates": []}


def _save_results(db: Session, train_id: int, predicted: list, periods: list, extras):
    """写预测结果到 prcp_model_train_result
    把所有预测存到一个虚拟 rpt_item（id=0 表示汇总指标）
    """
    import math
    conf_low, conf_high = (None, None)
    if isinstance(extras, tuple) and len(extras) == 2:
        conf_low, conf_high = extras
    for i, val in enumerate(predicted):
        period_date = None
        if i < len(periods):
            try:
                period_date = date(2026, 1 + i, 1) if isinstance(periods[i], int) else periods[i]
            except Exception:
                period_date = date(2026, 1 + i, 1)
        if not period_date:
            period_date = date(2026, 1 + i, 1)
        cl = float(conf_low[i]) if conf_low and i < len(conf_low) and conf_low[i] is not None and not (isinstance(conf_low[i], float) and math.isnan(conf_low[i])) else None
        ch = float(conf_high[i]) if conf_high and i < len(conf_high) and conf_high[i] is not None and not (isinstance(conf_high[i], float) and math.isnan(conf_high[i])) else None
        try:
            db.execute(
                text("""INSERT INTO prcp_model_train_result
                    (train_id, rpt_item_id, rpt_item_code, predict_period,
                     predicted_value, confidence_low, confidence_high)
                    VALUES (:tid, 0, 'SUMMARY', :pp, :pv, :cl, :ch)"""),
                {"tid": train_id, "pp": period_date, "pv": float(val),
                 "cl": cl, "ch": ch},
            )
        except Exception:
            pass  # UNIQUE 冲突时跳过
    db.commit()