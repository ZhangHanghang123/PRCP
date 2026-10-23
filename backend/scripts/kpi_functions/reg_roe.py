"""监管指标 · ROE 净资产收益率（Return on Equity）

公式：ROE = 净利润 / 平均净资产 × 100

数据源（全部来自 prcp_data_basic，按 data_date 过滤）：
- 净利润：所有节点的 interest_amount 累计（资产端为正，负债端为负）
- 平均净资产：所有者权益 S030000000000 的 current_balance

单位：PERCENT
监管参考：商业银行 ROE 一般 8%-15%
"""
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


DB_URL = f"mysql+pymysql://prcp:{quote_plus('Prcp@2026')}@127.0.0.1:3306/prcp_db?charset=utf8mb4"
SCHEME_CODE = "ZX_COA"


def calc(ctx: dict) -> float:
    data_date = ctx.get("data_date", "2025-12-31")
    engine = create_engine(DB_URL, echo=False)
    with engine.begin() as conn:
        np_row = conn.execute(text("""
            SELECT
                SUM(d.interest_amount) AS net_profit,
                SUM(CASE WHEN d.node_code = 'S030000000000' THEN d.current_balance ELSE 0 END) AS avg_equity
            FROM prcp_data_basic d
            WHERE d.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
              AND d.is_deleted = 0
        """), {"dd": data_date}).fetchone()

    net_profit = float(np_row[0] or 0.0)
    avg_equity = float(np_row[1] or 0.0)

    if avg_equity <= 0:
        return 0.0
    return round(net_profit / avg_equity * 100, 4)