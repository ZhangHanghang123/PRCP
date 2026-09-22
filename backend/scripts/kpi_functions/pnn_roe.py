"""PNN 训练指标 · ROE 净资产收益率（Return on Equity）

公式：ROE = 净利润 / 平均净资产 × 100

PNN 训练时通常会同时维护 KPI_NET_PROFIT（净利润）和 KPI_AVG_EQUITY（平均净资产）。
若同方案下这两个指标在当前 data_date 已有值（ctx.kpi_values），直接套公式；
否则使用占位演示值（确保函数可独立运行，便于 PNN 冷启动调试）。

单位：PERCENT（百分比）
监管参考：商业银行 ROE 一般 10%-20%
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

    net_profit = _get("net_profit", "KPI_NET_PROFIT", 1000.0)
    avg_equity = _get("avg_equity", "KPI_AVG_EQUITY", 10000.0)

    if avg_equity <= 0:
        return 0.0
    return round(net_profit / avg_equity * 100, 4)
