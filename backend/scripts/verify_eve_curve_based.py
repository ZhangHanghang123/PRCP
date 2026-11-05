"""用 PRCP 库内国债曲线重算 EVE 现值法，验证能否复现 61.39%。

数据来源：
  - 期限桶现金流：prcp_data_basic 的 orig_m1..m60 + rem_m1..rem_m60
  - 现值曲线：prcp_rate_curv / prcp_rate_point 的 CN_SOV_CNY（已从 CURV 同步+插值）
  - 账户权重：prcp_eve_param 的 is_asset/is_liability + duration

情景：变陡峭（steepener）100bp —— v3 模版口径
  资产：1Y 以内不变，>1Y 每年 +100bp（上限 +100bp）
  负债：base + (asset_rate - base) × β，β=0.5
"""
import sys
from decimal import Decimal

sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, text
from app.config import settings

eng = create_engine(settings.DATABASE_URL)
DD = '2025-12-31'

# 期限桶 → 年数（与 v3 模版一致：1M..60M 按月，10Y/15Y/20Y/30Y）
BUCKETS = []
for m in range(1, 61):
    BUCKETS.append(('m%d' % m, m / 12.0))
for y in (10, 15, 20, 30):
    BUCKETS.append(('y%d' % y, float(y)))

print('=' * 100)
print('EVE 现值法重算（曲线来自 PRCP prcp_rate_curv / prcp_rate_point）')
print('=' * 100)

with eng.connect() as c:
    # ---- 国债曲线（标准键 → 年数, 利率%）----
    curve = {}
    for t, v in c.execute(text("""
        SELECT tenor, rate_value FROM prcp_rate_curv
        WHERE curve_code='CN_SOV_CNY' AND data_date=:dd AND is_deleted=0
    """), {'dd': DD}).fetchall():
        curve[t] = float(v)
    print('\n[1] 国债曲线 %d 点' % len(curve))

    # ---- 账户册：末级节点 + 期限桶 ----
    bucket_cols = ','.join(['orig_%s, rem_%s' % (b, b) for b, _y in BUCKETS])
    sql_b = (
        'SELECT node_code, node_name, current_balance, weighted_rate, ' + bucket_cols +
        ' FROM prcp_data_basic d '
        "WHERE d.data_date=STR_TO_DATE(:dd,'%Y-%m-%d') AND d.is_deleted=0 AND d.is_leaf=1"
    )
    rows = c.execute(text(sql_b), {'dd': DD}).fetchall()

    # ---- 资产/负债标记 ----
    amap = {}
    for nc, ia, il in c.execute(text("""
        SELECT node_code, is_asset, is_liability FROM prcp_eve_param
        WHERE scheme_code='ZX_COA' AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d')
          AND is_deleted=0
    """), {'dd': DD}).fetchall():
        amap[nc] = (ia, il)

    tier1 = float(c.execute(text("""
        SELECT current_balance FROM prcp_data_basic WHERE node_code='S030000000000'
          AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d') AND is_deleted=0
    """), {'dd': DD}).scalar() or 0)

print('[2] 末级账户 %d 个，一级资本 %.2f 亿' % (len(rows), tier1 / 1e8))

# 曲线插值（线性年数）
CURVE_KEYS = sorted([(k, y) for k, y in
                     [('d1', 1 / 365.), ('d7', 7 / 365.), ('m1', 1 / 12.), ('m3', .25),
                      ('m6', .5), ('y1', 1.), ('y2', 2.), ('y3', 3.), ('y5', 5.),
                      ('y10', 10.), ('y15', 15.), ('y20', 20.), ('y30', 30.)]],
                    key=lambda x: x[1])
CURVE_PTS = [(y, curve[k]) for k, y in CURVE_KEYS if k in curve]


def curve_rate(years):
    """按年数从 PRCP 国债曲线取值（线性插值 + flat 外推）"""
    if not CURVE_PTS:
        return 0.0
    ys = [p[0] for p in CURVE_PTS]
    rs = [p[1] for p in CURVE_PTS]
    if years <= ys[0]:
        return rs[0]
    if years >= ys[-1]:
        return rs[-1]
    for i in range(len(ys) - 1):
        if ys[i] <= years <= ys[i + 1]:
            t = (years - ys[i]) / (ys[i + 1] - ys[i])
            return rs[i] + t * (rs[i + 1] - rs[i])
    return rs[-1]


# ---- 计算 EVE（基准 + 变陡峭） ----
BETA = 0.5
SHORT_YEAR = 1.0


def calc_eve(scenario='baseline', amp=0.0):
    apv = lpv = 0.0
    for r in rows:
        nc = r[0]
        ia, il = amap.get(nc, (0, 0))
        if not (ia or il):
            continue        # 无资产/负债标记 → 不参与
        for bi, (bkey, years) in enumerate(BUCKETS):
            orig = r[3 + bi * 2]
            rem = r[4 + bi * 2]
            cf = float(orig or 0) + float(rem or 0)
            if cf == 0:
                continue
            base_r = curve_rate(years)
            if scenario == 'steepener':
                if years <= SHORT_YEAR:
                    a_rate = base_r
                else:
                    a_rate = base_r + min(amp / 100.0, 1.0)
            else:
                a_rate = base_r
            l_rate = base_r + (a_rate - base_r) * BETA
            a_df = 1.0 / (1 + a_rate / 100.0) ** years
            l_df = 1.0 / (1 + l_rate / 100.0) ** years
            if ia:
                apv += cf * a_df
            else:
                lpv += cf * l_df
    return apv, lpv


b_apv, b_lpv = calc_eve('baseline')
base_eve = b_apv - b_lpv
print()
print('[3] 基准情景')
print('    资产PV = %12.2f 亿' % (b_apv / 1e8))
print('    负债PV = %12.2f 亿' % (b_lpv / 1e8))
print('    EVE基准 = %12.2f 亿' % (base_eve / 1e8))

s_apv, s_lpv = calc_eve('steepener', 100.0)
s_eve = s_apv - s_lpv
dev = s_eve - base_eve
pct = abs(dev) / abs(base_eve) * 100 if base_eve else 0
pct_t1 = abs(dev) / tier1 * 100 if tier1 else 0

print()
print('[4] 变陡峭情景 (100bp, β=0.5)')
print('    资产PV = %12.2f 亿' % (s_apv / 1e8))
print('    负债PV = %12.2f 亿' % (s_lpv / 1e8))
print('    EVE    = %12.2f 亿' % (s_eve / 1e8))
print('    ΔEVE   = %12.2f 亿' % (dev / 1e8))
print()
print('    ★ |ΔEVE| / |EVE基准| = %.4f%%   (v3 模版口径)' % pct)
print('    ★ |ΔEVE| / 一级资本   = %.4f%%   (评分标准口径, 模版值 61.39%%)' % pct_t1)
print()
print('    对比：')
print('      EVE_ABS   本次 %10.4f%%  |  模版 %10.4f%%  | Δ %.4f pp'
      % (pct, 175.33, pct - 175.33))
print('      |ΔEVE|/T1 本次 %10.4f%%  |  模版 %10.4f%%  | Δ %.4f pp'
      % (pct_t1, 61.3947, pct_t1 - 61.3947))
