"""函数指标 demo：模拟净息差（NIM）计算
    NIM ≈ 利息净收入 / 生息资产平均余额 × 100
    这里从 ctx.rpt_items 找特定 code（若不存在则给示例值）
"""
def calc(ctx: dict) -> float:
    ri = ctx.get("rpt_items", {})
    interest_income = ri.get("001001001001") or 1000.0
    interest_expense = ri.get("001001001002") or 300.0
    avg_earning_asset = ri.get("001001001003") or 20000.0
    net_interest = interest_income - interest_expense
    if avg_earning_asset <= 0:
        return 0.0
    return round(net_interest / avg_earning_asset * 100, 4)