"""服务器端到端验证：真实库数据 + 后端 PIECEWISE 引擎语义。

复刻 backend/app/routers/kpi.py L778-812 的 score_calc 实现，
读线上库真实段数据，验证 8 指标实测得分与 reg_eve.py 口径。
"""
import sys
sys.path.insert(0, '/home/almd/prcp/backend')

from sqlalchemy import create_engine, text
from app.config import settings

eng = create_engine(settings.DATABASE_URL)

EXPECT = {
    'REG_LCR': (144.22, 449.14), 'REG_NSFR': (104.65, 454.17),
    'REG_EVE': (61.39, 454.44), 'REG_CET1': (9.48, 370.00),
    'REG_CAR': (12.80, 450.00), 'REG_ROE': (9.39, 350.86),
    'REG_IBL': (21.60, 436.00), 'REG_LR': (7.09, 392.94),
}
W = {'REG_LCR': 0.16, 'REG_NSFR': 0.13, 'REG_EVE': 0.12, 'REG_CET1': 0.16,
     'REG_CAR': 0.10, 'REG_ROE': 0.12, 'REG_IBL': 0.11, 'REG_LR': 0.10}


def engine_score(segs, value):
    """复刻 kpi.py PIECEWISE：闭区间、seg_order 首个命中、段内线性插值。"""
    for s in segs:
        sid, mn, mx, sc, sc_min, desc, so = s
        if mn is not None and value < float(mn):
            continue
        if mx is not None and value > float(mx):
            continue
        sc = float(sc)
        sc_min_v = float(sc_min) if sc_min is not None else None
        if (sc_min_v is not None and mn is not None and mx is not None
                and float(mx) > float(mn)):
            ratio = (value - float(mn)) / (float(mx) - float(mn))
            return round(sc_min_v + ratio * (sc - sc_min_v), 2), so, desc, 'INTERP'
        return round(sc, 2), so, desc, 'STEP'
    return None, None, None, None


print('=' * 100)
print('服务器端到端验证 · 真实库数据 + 后端引擎语义')
print('=' * 100)
print('%-10s %-6s %-11s %-11s %-9s %-9s %-8s %-7s %s' % (
    '指标', '段数', '引擎得分', '库存分数', '期望', 'Δ', '命中段', '模式', '结论'))

ok = True
tot = 0.0
with eng.connect() as conn:
    for code, (exp_val, exp_score) in EXPECT.items():
        rule = conn.execute(text("""
            SELECT r.id FROM prcp_kpi_score_rule r
            JOIN prcp_kpi_definition d ON d.id=r.kpi_id AND d.is_deleted=0
            WHERE d.kpi_code=:c AND r.is_deleted=0 AND r.calc_method='PIECEWISE'
        """), {'c': code}).fetchone()
        if not rule:
            print('  x %-10s 无有效规则' % code)
            ok = False
            continue
        rid = rule[0]
        segs = conn.execute(text("""
            SELECT id, min_value, max_value, score, score_min, segment_desc, seg_order
            FROM prcp_kpi_score_segment WHERE rule_id=:r AND is_deleted=0 ORDER BY seg_order
        """), {'r': rid}).fetchall()
        vrow = conn.execute(text("""
            SELECT current_value, score FROM prcp_kpi_value
            WHERE kpi_id=(SELECT id FROM prcp_kpi_definition WHERE kpi_code=:c AND is_deleted=0)
              AND data_date='2025-12-31' AND is_deleted=0
        """), {'c': code}).fetchone()
        if not vrow:
            print('  x %-10s 无指标值' % code)
            ok = False
            continue
        x = float(vrow[0])
        stored = float(vrow[1])
        e, so, desc, mode = engine_score(segs, x)
        d = max(abs(e - exp_score), abs(e - stored), abs(x - exp_val))
        good = d < 0.02 and len(segs) == 23
        ok = ok and good
        tot += W[code] * e
        print('%-10s %-6d %-11.2f %-11.2f %-9.2f %-9.4f %-8s %-7s %s' % (
            code, len(segs), e, stored, exp_score, d, so, mode,
            'OK' if good else 'x'))

print()
print('  加权总分 = %.2f / 500   /100 = %.2f' % (tot, tot / 5.0))

with eng.connect() as conn:
    row = conn.execute(text("""
        SELECT SUM(CASE WHEN p.is_asset=1 THEN p.duration*d.current_balance ELSE 0 END)
                 /NULLIF(SUM(CASE WHEN p.is_asset=1 THEN d.current_balance ELSE 0 END),0),
               SUM(CASE WHEN p.is_liability=1 THEN p.duration*d.current_balance ELSE 0 END)
                 /NULLIF(SUM(CASE WHEN p.is_liability=1 THEN d.current_balance ELSE 0 END),0)
        FROM prcp_eve_param p
        JOIN prcp_data_basic d ON d.node_code=p.node_code
          AND d.data_date=STR_TO_DATE('2025-12-31','%Y-%m-%d') AND d.is_deleted=0
        WHERE p.scheme_code='ZX_COA' AND p.data_date=STR_TO_DATE('2025-12-31','%Y-%m-%d')
          AND p.is_deleted=0
    """)).fetchone()
    t1 = conn.execute(text("""
        SELECT current_balance FROM prcp_data_basic WHERE node_code='S030000000000'
          AND data_date=STR_TO_DATE('2025-12-31','%Y-%m-%d') AND is_deleted=0
    """)).scalar()

d_a = float(row[0] or 0)
d_l = float(row[1] or 0)
tier1 = float(t1 or 0)
d_gap = d_a - d_l
eve_loss = -d_gap * tier1 * 0.02
print()
print('  reg_eve.py 口径: D_A=%.6f  D_L=%.6f  D_GAP=%.6f' % (d_a, d_l, d_gap))
print('  Tier1=%.2f 亿   ΔEVE(200bp上移)=%.2f 亿   |ΔEVE|/Tier1=%.4f%%'
      % (tier1 / 1e8, eve_loss / 1e8, abs(eve_loss) / tier1 * 100))
ok = ok and d_l > 0 and abs(eve_loss) > 0

print()
print('=' * 100)
print('端到端验证: %s' % ('PASS' if ok else 'FAIL'))
print('=' * 100)
sys.exit(0 if ok else 1)
