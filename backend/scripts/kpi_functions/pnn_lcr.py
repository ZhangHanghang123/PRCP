"""PNN 训练指标 · LCR 流动性覆盖率（Liquidity Coverage Ratio，巴塞尔Ⅲ）

公式：LCR = 合格优质流动性资产（HQLA） / 未来 30 日现金净流出 × 100

监管要求：≥ 100%
HQLA = Level 1 + Level 2A × 0.85 + Level 2B × 0.5
未来 30 日现金净流出 = 预期现金流出 - 预期现金流入（上限 75% 流出）

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

    hqla = _get("hqla", "KPI_HQLA", 80000.0)
    net_cash_outflow = _get("net_cash_outflow_30d", "KPI_NET_CASH_OUT_30D", 60000.0)

    if net_cash_outflow <= 0:
        return 0.0
    return round(hqla / net_cash_outflow * 100, 4)
