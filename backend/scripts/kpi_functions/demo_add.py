"""函数指标 demo：将 ctx 中两个报表项相加后 * 100
ctx 结构见 services/kpi_function_runner.py
"""
def calc(ctx: dict) -> float:
    ri = ctx.get("rpt_items", {})
    # 取前两个 item 的值相加；缺则视为 0
    vals = list(ri.values())[:2]
    base = sum(vals) if vals else 0.0
    return float(base) * 100