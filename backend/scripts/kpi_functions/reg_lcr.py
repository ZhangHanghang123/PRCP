"""监管指标 · LCR 流动性覆盖率（Liquidity Coverage Ratio）

公式：LCR = 合格优质流动性资产（HQLA） / 未来 30 日现金净流出 × 100

数据源：
- prcp_lcr_param 表（LCR 参数补录）：每条记录的 is_numerator=1 表示计入 HQLA 分子，
  num_factor × current_balance = 该项目的 HQLA 折算贡献；is_denominator=1 表示
  计入 30 天净流出（den_factor × current_balance）。
- prcp_data_basic 表：当前余额（按 node_code + data_date JOIN）

单位：PERCENT（百分比）
监管要求：≥ 100%
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
                SUM(CASE WHEN p.is_numerator   = 1 THEN p.num_factor * d.current_balance ELSE 0 END) AS hqla_total,
                SUM(CASE WHEN p.is_denominator = 1 THEN p.den_factor * d.current_balance ELSE 0 END) AS outflow_total
            FROM prcp_lcr_param p
            JOIN prcp_data_basic d
              ON d.node_code = p.node_code
             AND d.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
             AND d.is_deleted = 0
            WHERE p.scheme_code = :sc
              AND p.data_date  = STR_TO_DATE(:dd, '%Y-%m-%d')
              AND p.is_deleted = 0
        """), {"sc": SCHEME_CODE, "dd": data_date}).fetchone()

    hqla = float(row[0] or 0.0)
    outflow = float(row[1] or 0.0)

    if outflow <= 0:
        return 0.0
    return round(hqla / outflow * 100, 4)