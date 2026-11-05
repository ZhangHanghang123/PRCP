"""服务器：把 REG_EVE 实测值更新为现值法实测 34.1595%，并重算得分。

同时按后端 PIECEWISE 引擎语义复算全部 8 指标，确认与库存一致。
"""
import sys
sys.path.insert(0, '/home/almd/prcp/backend')
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, text
from app.config import settings

eng = create_engine(settings.DATABASE_URL)
DD = '2025-12-31'

# v14.1 锚点（L 方向：越低越好）
A0, A1, A2, A4, DELTA, FLOOR = 165.0, 140.0, 100.0, 50.0, 30.0, 450.0
EVE_NEW = 34.1595


def theory(x):
    if x >= A0:
        return 0.0
    if x >= A1:
        return (A0 - x) / (A0 - A1) * 150
    if x >= A2:
        return 150 + (A1 - x) / (A1 - A2) * 150
    if x >= A4:
        return 300 + (A2 - x) / (A2 - A4) * 200
    if x <= A4 - DELTA:
        return FLOOR
    return 500 - (A4 - x) / DELTA * (500 - FLOOR)


def engine_score(segs, value):
    """复刻 kpi.py PIECEWISE"""
    for s in segs:
        sid, mn, mx, sc, sc_min, desc, so = s
        if mn is not None and value < float(mn):
            continue
        if mx is not None and value > float(mx):
            continue
        sc = float(sc)
        sm = float(sc_min) if sc_min is not None else None
        if sm is not None and mn is not None and mx is not None and float(mx) > float(mn):
            r = (value - float(mn)) / (float(mx) - float(mn))
            return round(sm + r * (sc - sm), 2), so
        return round(sc, 2), so
    return None, None


print('=' * 100)
print('REG_EVE 实测值更新（现值法）+ 全量得分重算')
print('=' * 100)

with eng.begin() as c:
    c.execute(text("""
        UPDATE prcp_kpi_value
        SET current_value = :v, score = :s, calc_source = 'MODEL',
            calc_log = :lg, updated_by = 1, updated_at = NOW()
        WHERE kpi_id = (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_EVE' AND is_deleted=0)
          AND data_date = :dd AND version = 'V1.0' AND is_deleted = 0
    """), {
        'v': EVE_NEW, 's': round(theory(EVE_NEW), 2), 'dd': DD,
        'lg': 'v14.1 现金流现值法（reg_eve_pv.py）变陡峭情景 |ΔEVE|/Tier1',
    })
print('\n[1] REG_EVE 实测值 → %.4f%%  得分 %.2f' % (EVE_NEW, theory(EVE_NEW)))

W = {'REG_LCR': .16, 'REG_NSFR': .13, 'REG_EVE': .12, 'REG_CET1': .16,
     'REG_CAR': .10, 'REG_ROE': .12, 'REG_IBL': .11, 'REG_LR': .10}

print('\n[2] 全量得分校验')
print('%-10s %-9s %-11s %-11s %-11s %-9s %-7s %s' % (
    '指标', '值', '引擎', '解析', '库存', 'Δ', '命中段', '结论'))
tot = 0.0
ok = True
with eng.connect() as c:
    for code, w in W.items():
        rid = c.execute(text("""
            SELECT r.id FROM prcp_kpi_score_rule r
            JOIN prcp_kpi_definition d ON d.id=r.kpi_id AND d.is_deleted=0
            WHERE d.kpi_code=:c AND r.is_deleted=0 AND r.calc_method='PIECEWISE'
        """), {'c': code}).fetchone()
        segs = c.execute(text("""
            SELECT id, min_value, max_value, score, score_min, segment_desc, seg_order
            FROM prcp_kpi_score_segment WHERE rule_id=:r AND is_deleted=0 ORDER BY seg_order
        """), {'r': rid[0]}).fetchall()
        v, stored = c.execute(text("""
            SELECT current_value, score FROM prcp_kpi_value
            WHERE kpi_id=(SELECT id FROM prcp_kpi_definition WHERE kpi_code=:c AND is_deleted=0)
              AND data_date=:dd AND is_deleted=0
        """), {'c': code, 'dd': DD}).fetchone()
        x = float(v)
        e, so = engine_score(segs, x)
        t = theory(x) if code == 'REG_EVE' else None
        d = abs(e - float(stored))
        if t is not None:
            d = max(d, abs(e - t))
        good = d < 0.02
        ok = ok and good
        tot += w * e
        print('%-10s %-9.4f %-11.2f %-11s %-11.2f %-9.4f %-7s %s' % (
            code, x, e, ('%.2f' % t) if t is not None else '-', float(stored), d, so,
            'OK' if good else 'x'))

print('\n  加权总分 = %.2f / 500   /100 = %.2f' % (tot, tot / 5.0))
print('\n' + '=' * 100)
print('结果: %s' % ('PASS' if ok else 'FAIL'))
print('=' * 100)
sys.exit(0 if ok else 1)
