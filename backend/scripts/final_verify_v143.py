"""服务器最终验证 · EVE v14.3 区间重设。

验证：
  1. 8 指标规则段数 / 方向 / 引擎复算一致性
  2. EVE 60%~80% 区间的实际区分度（档位表逐点复算）
  3. REG_EVE 已解绑脚本绑定（重算不会覆盖库值）
  4. 综合总分
"""
import sys
sys.path.insert(0, '/home/almd/prcp/backend')
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, text
from app.config import settings

eng = create_engine(settings.DATABASE_URL)
DD = '2025-12-31'


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


W = {'REG_LCR': .16, 'REG_NSFR': .13, 'REG_EVE': .12, 'REG_CET1': .16,
     'REG_CAR': .10, 'REG_ROE': .12, 'REG_IBL': .11, 'REG_LR': .10}
ok = True

print('=' * 100)
print('服务器最终验证 · EVE v14.3 区间重设')
print('=' * 100)

with eng.connect() as c:
    # ---- 1. 8 指标引擎复算 ----
    print('\n[1] 8 指标 PIECEWISE 引擎复算')
    print('%-10s %-11s %-11s %-11s %-9s %-7s %s' % (
        '指标', '值', '引擎', '库存分', 'Δ', '命中段', '结论'))
    tot = 0.0
    eve_segs = None
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
        d = abs(e - float(stored))
        good = d < 0.02 and len(segs) == 23
        ok = ok and good
        tot += w * e
        if code == 'REG_EVE':
            eve_segs = segs
        print('%-10s %-11.4f %-11.2f %-11.2f %-9.4f %-7s %s' % (
            code, x, e, float(stored), d, so, 'OK' if good else 'x'))
    print('\n  加权总分 = %.2f / 500   /100 = %.2f' % (tot, tot / 5.0))

    # ---- 2. EVE 60~80% 区分度（用库中真实段逐点复算）----
    print('\n[2] EVE 60%%~80%% 区分度（库中真实档位逐点复算）')
    pts = [60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80]
    scores = []
    for v in pts:
        e, so = engine_score(eve_segs, float(v))
        scores.append(e)
        print('    %5.1f%%  →  %7.2f 分   (命中段 %s)' % (v, e, so))
    diff = scores[0] - scores[-1]
    slope = diff / 20.0
    print('\n    60%%→80%% 分差 = %.2f 分   斜率 %.2f 分/pp' % (diff, slope))
    if diff < 190 or slope < 9.5:
        print('    x 区分度不足')
        ok = False
    else:
        print('    OK 区分度达标（目标 ≥190 分 / ≥9.5 分/pp）')

    # ---- 3. 关键区间边界核对 ----
    print('\n[3] EVE 区间边界核对')
    bounds = [(170, 0.0, '红线'), (140, 150.0, '危险界'), (80, 300.0, '达标线'),
              (60, 500.0, '标杆线')]
    for bv, expect, label in bounds:
        e, so = engine_score(eve_segs, float(bv))
        good = abs(e - expect) < 0.02
        ok = ok and good
        print('    %-8s %6.1f%%  期望 %6.1f  实得 %7.2f  %s'
              % (label, bv, expect, e, 'OK' if good else 'x'))

    # ---- 4. 脚本绑定状态 ----
    print('\n[4] REG_EVE 脚本绑定状态')
    sp = c.execute(text("""
        SELECT script_path, calc_unit, formula_desc FROM prcp_kpi_definition
        WHERE kpi_code='REG_EVE' AND is_deleted=0
    """)).fetchone()
    print('    script_path = %s' % (sp[0] if sp[0] else '(NULL · 已解绑，重算不会覆盖库值)'))
    print('    calc_unit   = %s' % sp[1])
    print('    formula_desc= %s' % sp[2])
    if sp[0] is not None:
        print('    x 仍绑定脚本，重算会覆盖库值')
        ok = False

print('\n' + '=' * 100)
print('最终验证: %s' % ('PASS' if ok else 'FAIL'))
print('=' * 100)
sys.exit(0 if ok else 1)
