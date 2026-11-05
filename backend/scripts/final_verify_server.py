"""服务器最终端到端验证。

模拟 /kpi/{id}/recalculate 的行为：调用 KPI 函数脚本 → 覆盖 current_value →
按 PIECEWISE 引擎重算 score，确认与库中现值一致（幂等，不产生漂移）。
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


print('=' * 104)
print('服务器最终端到端验证 · KPI 重算幂等性 + 评分一致性')
print('=' * 104)

# ---- 1. 调用 REG_EVE 的 KPI 函数脚本（模拟 recalculate）----
print('\n[1] 模拟 /kpi/4/recalculate → 调用 reg_eve_pv.py')
from scripts.kpi_functions import reg_eve_pv
recalc = reg_eve_pv.calc({'data_date': DD})
print('    reg_eve_pv.calc() = %.4f%%' % recalc)

with eng.connect() as c:
    cur = c.execute(text("""
        SELECT v.current_value, v.score FROM prcp_kpi_value v
        JOIN prcp_kpi_definition d ON d.id=v.kpi_id
        WHERE d.kpi_code='REG_EVE' AND v.data_date=:dd AND v.is_deleted=0
    """), {'dd': DD}).fetchone()
print('    库中 current_value = %.4f%%   score = %.2f' % (float(cur[0]), float(cur[1])))
drift = abs(recalc - float(cur[0]))
print('    漂移 = %.6f%%   %s' % (drift, 'OK（重算不改变数据）' if drift < 0.001 else '✗ 有漂移'))

# ---- 2. 全指标引擎复算 ----
print('\n[2] 8 指标 PIECEWISE 引擎复算')
W = {'REG_LCR': .16, 'REG_NSFR': .13, 'REG_EVE': .12, 'REG_CET1': .16,
     'REG_CAR': .10, 'REG_ROE': .12, 'REG_IBL': .11, 'REG_LR': .10}
print('%-10s %-11s %-11s %-11s %-9s %-7s %s' % (
    '指标', '值', '引擎', '库存分', 'Δ', '命中段', '结论'))
ok = drift < 0.001
tot = 0.0
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
        d = abs(e - float(stored))
        good = d < 0.02 and len(segs) == 23
        ok = ok and good
        tot += w * e
        print('%-10s %-11.4f %-11.2f %-11.2f %-9.4f %-7s %s' % (
            code, x, e, float(stored), d, so, 'OK' if good else 'x'))

print('\n  加权总分 = %.2f / 500   /100 = %.2f' % (tot, tot / 5.0))

# ---- 3. 曲线与标记完整性 ----
print('\n[3] 基础数据完整性')
with eng.connect() as c:
    r = c.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM prcp_rate_curv WHERE is_deleted=0),
          (SELECT COUNT(*) FROM prcp_rate_curv WHERE is_deleted=0 AND is_interpolated=1),
          (SELECT COUNT(*) FROM prcp_eve_param WHERE is_deleted=0 AND is_liability=1),
          (SELECT COUNT(*) FROM prcp_eve_param WHERE is_deleted=0 AND is_asset=1),
          (SELECT COUNT(*) FROM prcp_kpi_definition WHERE is_deleted=0 AND kpi_code LIKE 'REG_%'),
          (SELECT COUNT(*) FROM prcp_kpi_score_rule WHERE is_deleted=0 AND rule_name LIKE '%v14.1%')
    """)).fetchone()
    print('    prcp_rate_curv 有效点      = %d (其中插值 %d)' % (r[0], r[1]))
    print('    eve_param 资产/负债标记     = %d / %d' % (r[3], r[2]))
    print('    REG_* 指标定义 / v14.1 规则 = %d / %d' % (r[4], r[5]))
    ok = ok and r[0] == 52 and r[4] == 8 and r[5] == 8

print('\n' + '=' * 104)
print('最终验证: %s' % ('PASS' if ok else 'FAIL'))
print('=' * 104)
sys.exit(0 if ok else 1)
