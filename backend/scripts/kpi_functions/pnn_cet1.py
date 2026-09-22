"""PNN 训练指标 · 核心一级资本充足率（CET1 Ratio，巴塞尔Ⅲ）

公式：核心一级资本充足率 = 核心一级资本净额 / 风险加权资产 × 100

监管要求：≥ 7.5%（含 2.5% 储备资本）
本指标对应 prcp_kpi_score_rule 中 higher_is_better=1 的分段评分。

单位：PERCENT
"""
def calc(ctx: dict) -> float:
    extra = ctx.get("ctx_extra", {}) or {}
    kv = ctx.get("kpi_values", {}) or {}

    def _get(extra_key: str, kv_key: str, default: float) -> float:
        """优先 ctx_extra[k] → 其次 kv[k]（含 0/负数）→ 最后默认；避免 0 被 or 短路吞掉。"""
        if extra_key in extra and extra[extra_key] is not None:
            return float(extra[extra_key])
        if kv_key in kv and kv[kv_key] is not None:
            return float(kv[kv_key])
        return default

    cet1_capital = _get("cet1_capital", "KPI_CET1_CAPITAL", 50000.0)
    rwa = _get("rwa", "KPI_RWA", 400000.0)

    if rwa <= 0:
        return 0.0
    return round(cet1_capital / rwa * 100, 4)
