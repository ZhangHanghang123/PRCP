"""监管指标 · CET1 核心一级资本充足率（Common Equity Tier 1 Ratio）

公式：CET1 = 核心一级资本净额 / 风险加权资产（RWA） × 100

数据源：
- prcp_cet1_param 表（CET1 参数补录）：is_numerator / is_rwa + factor
- prcp_data_basic 表：当前余额（按 node_code + data_date JOIN）

单位：PERCENT
监管要求：≥ 7.5%（含 2.5% 储备资本）
"""
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


DB_URL = f"mysql+pymysql://prcp:{quote_plus('Prcp@2026')}@127.0.0.1:3306/prcp_db?charset=utf8mb4"
SCHEME_CODE = "ZX_COA"


def calc(ctx: dict) -> float:
    data_date = ctx.get("data_date", "2025-12-31")
    engine = create_engine(DB_URL, echo=False)
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT
                SUM(CASE WHEN p.is_numerator = 1 THEN p.numerator_factor * d.current_balance ELSE 0 END) AS capital_net,
                SUM(CASE WHEN p.is_rwa       = 1 THEN p.rwa_weight       * d.current_balance ELSE 0 END) AS rwa_total
            FROM prcp_cet1_param p
            JOIN prcp_data_basic d
              ON d.node_code = p.node_code
             AND d.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
             AND d.is_deleted = 0
            WHERE p.scheme_code = :sc
              AND p.data_date  = STR_TO_DATE(:dd, '%Y-%m-%d')
              AND p.is_deleted = 0
        """), {"sc": SCHEME_CODE, "dd": data_date}).fetchone()

    capital_net = float(row[0] or 0.0)
    rwa_total = float(row[1] or 0.0)

    if rwa_total <= 0:
        return 0.0
    return round(capital_net / rwa_total * 100, 4)