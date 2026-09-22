"""PNN 训练指标 · △EVE 经济价值变动（Earnings/Equity Value at Risk）

公式：△EVE = 基线 EVE − 冲击后 EVE
EVE = Σ 各期限现金流 / (1 + r)^t
标准冲击场景：±100bp / ±200bp / ±300bp（PNN 训练默认 ±200bp 基线）

PNN 场景下通常由利率风险引擎（rate_engine）预计算后写入 ctx_extra。
本函数既支持 ctx_extra 预计算（生产路径），也支持占位 demo 值（冷启动）。

单位：AMOUNT（金额变动，绝对值，越小越好 — 评分时 higher_is_better=0）
"""
def calc(ctx: dict) -> float:
    extra = ctx.get("ctx_extra", {}) or {}
    kv = ctx.get("kpi_values", {}) or {}

    # 优先从 ctx_extra.delta_eve 取（PNN 利率风险引擎预计算）
    delta_eve = extra.get("delta_eve")
    if delta_eve is not None:
        try:
            return round(float(delta_eve), 4)
        except (TypeError, ValueError):
            pass

    # 其次从 kpi_values 取同方案预存的 EVE 变动
    if "KPI_DELTA_EVE" in kv:
        try:
            return round(float(kv["KPI_DELTA_EVE"]), 4)
        except (TypeError, ValueError):
            pass

    # 占位 demo：模拟 ±200bp 冲击下 ΔEVE
    shock_bp = float(extra.get("shock_bp") or 200.0)
    baseline_eve = float(extra.get("baseline_eve") or 1_000_000.0)
    duration_years = float(extra.get("duration_years") or 3.5)
    delta_eve = -baseline_eve * duration_years * (shock_bp / 10000.0)
    return round(delta_eve, 4)
