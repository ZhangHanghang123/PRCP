"""监管指标 · NSFR 净稳定资金比例（Net Stable Funding Ratio）

公式：NSFR = 可用稳定资金（ASF） / 所需稳定资金（RSF） × 100

数据源：
- prcp_nsfr_param 表：is_asf=1 表示计入 ASF 分子；is_rsf=1 表示计入 RSF 分母
- prcp_data_basic 表：当前余额（按 node_code + data_date JOIN）
  说明：prcp_nsfr_param 表本身没有 current_balance 列，必须从 prcp_data_basic 读取

单位：PERCENT
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
                SUM(CASE WHEN p.is_asf = 1 THEN p.asf_factor * d.current_balance ELSE 0 END) AS asf_total,
                SUM(CASE WHEN p.is_rsf = 1 THEN p.rsf_factor * d.current_balance ELSE 0 END) AS rsf_total
            FROM prcp_nsfr_param p
            JOIN prcp_data_basic d
              ON d.node_code = p.node_code
             AND d.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
             AND d.is_deleted = 0
            WHERE p.scheme_code = :sc
              AND p.data_date  = STR_TO_DATE(:dd, '%Y-%m-%d')
              AND p.is_deleted = 0
        """), {"sc": SCHEME_CODE, "dd": data_date}).fetchone()

    asf = float(row[0] or 0.0)
    rsf = float(row[1] or 0.0)

    if rsf <= 0:
        return 0.0
    return round(asf / rsf * 100, 4)