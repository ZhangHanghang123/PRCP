"""PNN 训练指标 · NSFR 净稳定资金比例（Net Stable Funding Ratio，巴塞尔Ⅲ）

公式：NSFR = 可用稳定资金（ASF） / 所需稳定资金（RSF） × 100

监管要求：≥ 100%
ASF = 一级资本 + 二级资本 + 长期负债 × 稳定系数（0-100%）
RSF = 各资产类别 × RSF 系数（现金 0%，住房抵押贷款 65% 等）

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

    asf = _get("asf", "KPI_ASF", 500000.0)
    rsf = _get("rsf", "KPI_RSF", 450000.0)

    if rsf <= 0:
        return 0.0
    return round(asf / rsf * 100, 4)
