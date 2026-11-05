"""监管指标 · EVE 经济价值变动（△EVE / IRRBB 银行账簿利率风险）

口径（v14.1 起，与 0-500 评分标准一致）：
    行内 ΔEVE = |ΔEVE| / 一级资本 × 100   （单位：%）
    数值越小越好（higher_is_better = 0）

计算式（久期缺口近似）：
    D_A   = SUM(资产余额 × 久期) / SUM(资产余额)
    D_L   = SUM(负债余额 × 久期) / SUM(负债余额)
    D_GAP = D_A - D_L
    Tier1 = 所有者权益（S030000000000）
    ΔEVE  = - D_GAP × Tier1 × 200bp 平行向上冲击
    行内ΔEVE% = |ΔEVE| / Tier1 × 100 = D_GAP × 200bp × 100

数据源：
- prcp_eve_param 表：is_asset=1 / is_liability=1 + duration
- prcp_data_basic：当前余额（按 node_code + data_date JOIN）+ Tier1 资本

监管要求（巴塞尔 IRRBB SRP31.82）：
    最大情景下 |ΔEVE| 不得超过 Tier 1 资本的 15%

⚠ 历史口径：v14.1 之前本函数返回【金额】（AMOUNT，元）。
  由于 0-500 评分规则需要百分比输入，且 KPI 重算接口
  （/kpi/{id}/recalculate）会用本函数返回值直接覆盖 prcp_kpi_value.current_value，
  已统一改为返回百分比。评分标准档位见
  docs/v2/评分标准_v14.1_EVE口径修正.xlsx（红线 165% / 达标 100% / 标杆 50%）。
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

    # 久期缺口 → ΔEVE 金额 → 转百分比（|ΔEVE| / Tier1 × 100）
    d_gap = d_a - d_l
    eve_loss = -d_gap * tier1 * INTEREST_SHOCK
    return round(abs(eve_loss) / tier1 * 100.0, 4)
