"""用服务器 prcp_eve_param + prcp_data_basic 复算 reg_eve.py 口径，
并尝试复现 62% 这个数值的可能来源。

候选口径：
  A) |ΔEVE| / Tier1资本          （监管口径，reg_eve.py 隐含）
  B) |ΔEVE| / |EVE基准|           （v3 模版 EVE_ABS）
  C) |ΔEVE| / 总资产
  D) |ΔEVE| / 生息资产
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, text
from app.config import settings

eng = create_engine(settings.DATABASE_URL)
DD = '2025-12-31'
SC = 'ZX_COA'

with eng.connect() as conn:
    row = conn.execute(text("""
        SELECT
            SUM(CASE WHEN p.is_asset     = 1 THEN p.duration * d.current_balance ELSE 0 END) /
              NULLIF(SUM(CASE WHEN p.is_asset     = 1 THEN d.current_balance ELSE 0 END), 0) AS d_a,
            SUM(CASE WHEN p.is_liability = 1 THEN p.duration * d.current_balance ELSE 0 END) /
              NULLIF(SUM(CASE WHEN p.is_liability = 1 THEN d.current_balance ELSE 0 END), 0) AS d_l,
            SUM(CASE WHEN p.is_asset = 1 THEN d.current_balance ELSE 0 END) AS a_bal,
            SUM(CASE WHEN p.is_liability = 1 THEN d.current_balance ELSE 0 END) AS l_bal
        FROM prcp_eve_param p
        JOIN prcp_data_basic d
          ON d.node_code = p.node_code
         AND d.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
         AND d.is_deleted = 0
        WHERE p.scheme_code = :sc AND p.data_date = STR_TO_DATE(:dd, '%Y-%m-%d')
          AND p.is_deleted = 0
    """), {"sc": SC, "dd": DD}).fetchone()

    tier1_row = conn.execute(text("""
        SELECT current_balance FROM prcp_data_basic
        WHERE node_code='S030000000000' AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d')
          AND is_deleted=0
    """), {"dd": DD}).fetchone()

    # 资产负债表总量（用于 C/D 口径）
    bs = conn.execute(text("""
        SELECT node_code, current_balance FROM prcp_data_basic
        WHERE data_date=STR_TO_DATE(:dd,'%Y-%m-%d') AND is_deleted=0
          AND (node_code IN ('S010000000000','S020000000000','S030000000000',
                             'S010100000000','S010200000000'))
    """), {"dd": DD}).fetchall()

d_a = float(row[0] or 0)
d_l = float(row[1] or 0)
a_bal = float(row[2] or 0)
l_bal = float(row[3] or 0)
tier1 = float(tier1_row[0]) if tier1_row and tier1_row[0] else 0.0

print('=' * 96)
print('服务器口径复算 · data_date=%s scheme=%s' % (DD, SC))
print('=' * 96)
print('D_A (资产加权久期) = %.6f' % d_a)
print('D_L (负债加权久期) = %.6f' % d_l)
print('D_GAP              = %.6f' % (d_a - d_l))
print('资产余额合计        = %.2f 亿' % (a_bal / 1e8))
print('负债余额合计        = %.2f 亿' % (l_bal / 1e8))
print('Tier1(所有者权益)   = %.2f 亿' % (tier1 / 1e8))
print('资产负债表节点      =', bs)

print()
print('%-6s %-14s %-16s %-14s %-12s %-12s' % (
    '冲击', 'ΔEVE(亿)', '|ΔEVE|/Tier1', '|ΔEVE|/总资产', '|ΔEVE|/A', '|ΔEVE|/L'))
total_assets = a_bal + l_bal + tier1
for bp in (100, 200, 250, 300):
    dev = -(d_a - d_l) * tier1 * (bp / 10000.0)
    print('%-6s %-14.2f %-16.4f%% %-14.4f%% %-12.4f%% %-12.4f%%' % (
        '%dbp' % bp,
        dev / 1e8,
        abs(dev) / tier1 * 100 if tier1 else 0,
        abs(dev) / total_assets * 100 if total_assets else 0,
        abs(dev) / a_bal * 100 if a_bal else 0,
        abs(dev) / l_bal * 100 if l_bal else 0,
    ))

print()
print('※ 目标：找出 ≈62% 的口径')
for bp in (100, 200, 250, 300):
    dev = -(d_a - d_l) * tier1 * (bp / 10000.0)
    cands = {
        '/Tier1': abs(dev) / tier1 * 100 if tier1 else 0,
        '/总资产': abs(dev) / total_assets * 100 if total_assets else 0,
        '/生息资产(A)': abs(dev) / a_bal * 100 if a_bal else 0,
        '/总负债': abs(dev) / l_bal * 100 if l_bal else 0,
        '/(A+L)': abs(dev) / (a_bal + l_bal) * 100 if (a_bal + l_bal) else 0,
    }
    for k, v in cands.items():
        flag = '  <<<≈62%' if 58 <= v <= 66 else ''
        if flag:
            print('  %dbp %-14s = %.4f%%%s' % (bp, k, v, flag))
