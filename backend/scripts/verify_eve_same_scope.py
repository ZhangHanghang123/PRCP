"""同口径对比：把模版的 24 个汇总账户映射到库内 leaf 账户，
用 PRCP 国债曲线重算变陡峭情景 |ΔEVE|/Tier1，与 v3 模版的 61.3947% 对比。

目的：区分「口径差异」与「计算错误」。
  模版账户集 → 库内 node_code 映射：
    2.1.1 金市自营债券 → 拆成 AC/FVOCI/FVTPL 三个 (S010102010101/102/103)
    2.1.2 司库债券    → 拆成三个 (S010102010201/202/203)
    2.2 人民币市场化负债 → 拆成 S0201020101xx + S0201020202xx + 公开市场回购
    3.2 其他非生息资产 → S010103020100 + S010103020200
"""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, text
from app.config import settings

eng = create_engine(settings.DATABASE_URL)
DD = '2025-12-31'
BETA = 0.5
SHORT_YEAR = 1.0

BUCKETS = [('m%d' % m, m / 12.0) for m in range(1, 61)] + \
          [('y%d' % y, float(y)) for y in (10, 15, 20, 30)]

# 模版账户 → 库内 node_code 列表（模版用汇总，库里用末级）
TEMPLATE_MAP = {
    # 资产
    '1.1. 对公一般贷款': ['S010101010000'],
    '1.2. 个人贷款': ['S010101020000'],
    '1.3. 信用卡贷款': ['S010101030000'],
    '1.4. 票据贴现': ['S010101040000'],
    '1.5. 非银贷款': ['S010101050000'],
    '2.1.1 金市自营债券': ['S010102010101', 'S010102010102', 'S010102010103'],
    '2.1.2 司库债券': ['S010102010201', 'S010102010202', 'S010102010203'],
    '2.2. 结构化融资': ['S010102020000'],
    '2.3. 同业资产（不含拆放': ['S010102030000'],
    '2.4. 存款准备金': ['S010102040000'],
    '3.1. FVTPL类资产': ['S010103010000'],
    '3.2. 其他非生息资产': ['S010103020100', 'S010103020200'],
    '1. 外币贷款': ['S010201000000'],
    '2.1. 外币债券': ['S010202010000'],
    '2.2. 同业资产': ['S010202020000'],
    '3. 外币非生息资产': ['S010203000000'],
    # 负债
    '1.1.1 对公活期存款': ['S020101010100'],
    '1.1.2 对公定期存款': ['S020101010200'],
    '1.2.1 零售活期存款': ['S020101020100'],
    '1.2.2 零售定期存款': ['S020101020200'],
    '2. 人民币市场化负债': ['S020102010100', 'S020102010200', 'S020102010300',
                            'S020102010400', 'S020102010500', 'S020102020100',
                            'S020102020200', 'S020102020300', 'S020102020400',
                            'S020202000000'],
    '1. 外币存款': ['S020201000000'],
    '2. 外币市场化负债': ['S020202000000'],
    # 权益（现金流 0，仅记录）
    '所有者权益': ['S030000000000'],
}
ASSET_KEYS = set(list(TEMPLATE_MAP.keys())[:17])
LIAB_KEYS = set(list(TEMPLATE_MAP.keys())[17:24])


def build_curves(curve):
    """构造各情景利率曲线"""
    keys = sorted([('d1', 1 / 365.), ('d7', 7 / 365.), ('m1', 1 / 12.), ('m3', .25),
                   ('m6', .5), ('y1', 1.), ('y2', 2.), ('y3', 3.), ('y5', 5.),
                   ('y10', 10.), ('y15', 15.), ('y20', 20.), ('y30', 30.)],
                  key=lambda x: x[1])
    pts = [(y, curve[k]) for k, y in keys if k in curve]

    def rate_at(years):
        ys = [p[0] for p in pts]
        rs = [p[1] for p in pts]
        if years <= ys[0]:
            return rs[0]
        if years >= ys[-1]:
            return rs[-1]
        for i in range(len(ys) - 1):
            if ys[i] <= years <= ys[i + 1]:
                t = (years - ys[i]) / (ys[i + 1] - ys[i])
                return rs[i] + t * (rs[i + 1] - rs[i])
        return rs[-1]
    return rate_at


def main():
    with eng.connect() as c:
        curve = {t: float(v) for t, v in c.execute(text("""
            SELECT tenor, rate_value FROM prcp_rate_curv
            WHERE curve_code='CN_SOV_CNY' AND data_date=:dd AND is_deleted=0
        """), {'dd': DD}).fetchall()}

        bucket_cols = ','.join(['orig_%s, rem_%s' % (b, b) for b, _y in BUCKETS])
        sql_b = ('SELECT node_code, current_balance, ' + bucket_cols +
                 ' FROM prcp_data_basic d '
                 "WHERE d.data_date=STR_TO_DATE(:dd,'%Y-%m-%d') "
                 "AND d.is_deleted=0 AND d.is_leaf=1")
        rows = {r[0]: r for r in c.execute(text(sql_b), {'dd': DD}).fetchall()}

        tier1 = float(c.execute(text("""
            SELECT current_balance FROM prcp_data_basic WHERE node_code='S030000000000'
              AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d') AND is_deleted=0
        """), {'dd': DD}).scalar() or 0)

    rate_at = build_curves(curve)

    def calc(scenario, amp):
        apv = lpv = 0.0
        for tname, codes in TEMPLATE_MAP.items():
            if tname == '所有者权益':
                continue
            is_asset = tname in ASSET_KEYS
            for nc in codes:
                r = rows.get(nc)
                if not r:
                    continue
                for bi, (bkey, years) in enumerate(BUCKETS):
                    cf = float(r[2 + bi * 2] or 0) + float(r[3 + bi * 2] or 0)
                    if cf == 0:
                        continue
                    base_r = rate_at(years)
                    if scenario == 'steepener':
                        a_rate = base_r if years <= SHORT_YEAR else base_r + min(amp / 100.0, 1.0)
                    elif scenario == 'parallel_up':
                        a_rate = base_r + amp / 100.0
                    elif scenario == 'parallel_down':
                        a_rate = max(0.0, base_r - amp / 100.0)
                    else:
                        a_rate = base_r
                    l_rate = base_r + (a_rate - base_r) * BETA
                    a_df = 1.0 / (1 + a_rate / 100.0) ** years
                    l_df = 1.0 / (1 + l_rate / 100.0) ** years
                    if is_asset:
                        apv += cf * a_df
                    else:
                        lpv += cf * l_df
        return apv, lpv

    b_apv, b_lpv = calc('baseline', 0)
    base_eve = b_apv - b_lpv
    print('=' * 100)
    print('同口径对比：模版 24 账户 × 库内真实余额 × PRCP 国债曲线')
    print('=' * 100)
    print('  资产PV = %12.2f 亿   负债PV = %12.2f 亿   EVE基准 = %12.2f 亿'
          % (b_apv / 1e8, b_lpv / 1e8, base_eve / 1e8))
    print('  （模版：资产 94847.54 亿 / 负债 97600.54 亿 / EVE基准 −2753.00 亿）')
    print()
    print('%-18s %-12s %-14s %-14s %-12s %-12s' % (
        '情景', 'ΔEVE(亿)', 'EVE_ABS(%)', '模版EVE_ABS', '|ΔEVE|/T1(%)', '模版/T1'))
    MODEL = {'steepener': (175.33, 61.3947), 'parallel_up': (403.06, 141.1362),
             'parallel_down': (470.53, 164.7604)}
    for sc, amp in (('steepener', 100.0), ('parallel_up', 250.0), ('parallel_down', 250.0)):
        a, l = calc(sc, amp)
        dev = (a - l) - base_eve
        abs_pct = abs(dev) / abs(base_eve) * 100 if base_eve else 0
        pct_t1 = abs(dev) / tier1 * 100 if tier1 else 0
        m_abs, m_t1 = MODEL[sc]
        print('%-18s %-12.2f %-14.4f %-14.2f %-12.4f %-12.2f' % (
            sc, dev / 1e8, abs_pct, m_abs, pct_t1, m_t1))
    print()
    print('  注：模版用的是模拟余额（24 账户），库内是真实余额 + 末级拆分，')
    print('      故 EVE 基准量级不同；/Tier1 口径更可比。')


if __name__ == '__main__':
    main()
