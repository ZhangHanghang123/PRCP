"""监管指标 · EVE 经济价值变动（△EVE / IRRBB 银行账簿利率风险）

公式：
  D_A = SUM(资产余额 × 久期) / SUM(资产余额)
  D_L = SUM(负债余额 × 久期) / SUM(负债余额)
  D_GAP = D_A - D_L
  Tier 1 来自 prcp_data_basic 中所有者权益（S030000000000）
  △EVE = - D_GAP × Tier1 × 200bp 平行向上冲击

数据源：
- prcp_eve_param 表：is_asset=1 / is_liability=1 + duration
- prcp_data_basic：当前余额（按 node_code + data_date JOIN）+ Tier1 资本

单位：AMOUNT（元）
监管要求：△EVE 占 Tier 1 资本不超过 15%（即 -0.15 × Tier1 ≤ △EVE ≤ 0）
"""
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


DB_URL = f"mysql+pymysql://prcp:{quote_plus('Prcp@2026')}@127.0.0.1:3306/prcp_db?charset=utf8mb4"
SCHEME_CODE = "ZX_COA"
INTEREST_SHOCK = 0.02  # 200 bp 平行向上冲击（监管 6 情景中最严）


def calc(ctx: dict) -> float:
    data_date = ctx.get("data_date", "2025-12-31")
    engine = create_engine(DB_URL, echo=False)
    with engine.begin() as conn:
        # 资产/负债加权久期
        row = conn.execute(text("""
            SELECT
                SUM(CASE WHEN p.is_asset     = 1 THEN p.duration * d.current_balance ELSE 0 END) /
                  NULLIF(SUM(CASE WHEN p.is_asset     = 1 THEN d.current_balance ELSE 0 END), 0) AS d_a,
                SUM(CASE WHEN p.is_liability = 1 THEN p.duration * d.current_balance ELSE 0 END) /
                  NULLIF(SUM(CASE WHEN p.is_liability = 1 THEN d.current_balance ELSE 0 END), 0) AS d_l
            FROM prcp_eve_param p
            JOIN prcp_data_basic d
              ON d.node_code = p.node_code
             AND d.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
             AND d.is_deleted = 0
            WHERE p.scheme_code = :sc
              AND p.data_date  = STR_TO_DATE(:dd, '%Y-%m-%d')
              AND p.is_deleted = 0
        """), {"sc": SCHEME_CODE, "dd": data_date}).fetchone()

        # Tier 1 资本（一级资本 = 所有者权益）
        tier1_row = conn.execute(text("""
            SELECT d.current_balance FROM prcp_data_basic d
            WHERE d.node_code = 'S030000000000'
              AND d.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
              AND d.is_deleted = 0
        """), {"dd": data_date}).fetchone()

    d_a = float(row[0] or 0.0)
    d_l = float(row[1] or 0.0)
    tier1 = float(tier1_row[0] if tier1_row else 0.0)

    if tier1 <= 0:
        return 0.0

    d_gap = d_a - d_l
    eve_loss = -d_gap * tier1 * INTEREST_SHOCK
    return round(eve_loss, 2)