"""v14 落库脚本 · 纯函数层自校验（不连数据库）

校验目标：
  1. 每指标 23 段
  2. 引擎插值 == 解析函数 T(x) 全域
  3. 闭区间重叠仅限相邻段（无跨段非法覆盖）
  4. 峰值 500 可达
  5. 实测得分与 Excel v14 一致
"""
import sys
sys.path.insert(0, r'C:/银行经营/PRCP/backend/scripts')
sys.stdout.reconfigure(encoding='utf-8')

from seed_score_rules_v14 import (IND, ORDER, KPI_CODE_REG, KPI_CODE_PNN,
                                   build_segments, engine_score, theory_score)

EPS = 1e-9
EXPECT = {  # 与 docs/v2/评分标准_v14_锚点重标定.xlsx 得分页一致
    'LCR': 449.14, 'NSFR': 454.17, 'EVE': 486.05, 'CET1': 370.00,
    'CAR': 450.00, 'ROE': 350.86, 'IBL': 436.00, 'LR': 392.94,
}
TOTAL_EXPECT = 422.79

print('=' * 108)
print('v14 落库脚本 · 纯函数层自校验（不连数据库）')
print('=' * 108)
print('%-6s %-6s %-5s %-11s %-11s %-9s %-9s %-9s %-6s %s' % (
    '指标', '方向', '段数', '网格maxΔ', '边界maxΔ', '峰值', 'T(实测)', '库期望', 'Δ', '结论'))

FAIL = []
tot = 0.0
for key in ORDER:
    cfg = IND[key]
    segs = build_segments(cfg)

    # 段数
    n = len(segs)

    # A. 网格扫描
    maxd_grid = 0.0
    lo_all = min(s[1] for s in segs)
    hi_all = max(s[2] for s in segs)
    steps = 4001
    for i in range(steps + 1):
        x = lo_all + (hi_all - lo_all) * i / steps
        e = engine_score(segs, x)
        t = theory_score(cfg, x)
        if e is None:
            continue
        maxd_grid = max(maxd_grid, abs(e - t))

    # B. 边界点
    maxd_bnd = 0.0
    bnd = None
    for s in segs:
        for x in (s[1], s[2]):
            e = engine_score(segs, x)
            t = theory_score(cfg, x)
            if e is None:
                continue
            d = abs(e - t)
            if d > maxd_bnd:
                maxd_bnd = d
                bnd = (x, e, t, s[0])

    # C. 峰值
    peak = 0.0
    for s in segs:
        for x in (s[1], s[2]):
            e = engine_score(segs, x)
            if e is not None and e > peak:
                peak = e

    # D. 跨段非法覆盖（命中段必须两两相邻）
    bad = []
    for s in segs:
        for x in (s[1], s[2]):
            hits = sorted(t[0] for t in segs if x >= t[1] - EPS and x <= t[2] + EPS)
            for i in range(len(hits) - 1):
                if hits[i + 1] - hits[i] > 1:
                    bad.append((x, hits))
                    break

    # E. 实测
    e_real = engine_score(segs, cfg['act'])
    t_real = theory_score(cfg, cfg['act'])
    exp = EXPECT[key]
    d_exp = abs(e_real - exp)
    tot += cfg['w'] * e_real

    ok = (n == 23 and maxd_grid < 1e-9 and maxd_bnd < 1e-9 and peak >= 499.999
          and not bad and d_exp < 0.02)
    if not ok:
        FAIL.append('%s: n=%d gridΔ=%.2e bndΔ=%.2e peak=%.2f bad=%s dExp=%.4f %s'
                    % (key, n, maxd_grid, maxd_bnd, peak, bad[:2], d_exp, bnd))

    print('%-6s %-6s %-5d %-11.3e %-11.3e %-9.2f %-9.2f %-9.2f %-6.4f %s' % (
        key, cfg['dir'], n, maxd_grid, maxd_bnd, peak, t_real, exp, d_exp,
        'PASS' if ok else 'FAIL'))

print()
print('  加权总分 = %.2f / 500   /100 = %.2f   期望 %.2f  Δ=%.4f'
      % (tot, tot / 5.0, TOTAL_EXPECT, abs(tot - TOTAL_EXPECT)))

print()
print('【L 方向指标段序抽样 · EVE】')
segs = build_segments(IND['EVE'])
for s in segs:
    if s[0] in (1, 2, 6, 7, 11, 12, 16, 17, 18, 22, 23):
        e_lo = engine_score(segs, s[1])
        e_hi = engine_score(segs, s[2])
        print('  段%-3s [%8.4f, %8.4f] score=%-6.1f score_min=%-6.1f | '
              'x=lo→%-7.2f  x=hi→%-7.2f  T(lo)=%-7.2f T(hi)=%-7.2f'
              % (s[0], s[1], s[2], s[3], s[4], e_lo, e_hi,
                 theory_score(IND['EVE'], s[1]), theory_score(IND['EVE'], s[2])))

print()
print('=' * 108)
if FAIL:
    print('总体: FAIL')
    for f in FAIL:
        print('  ✗', f)
    sys.exit(1)
print('总体: PASS —— 8 指标段生成与引擎语义完全一致')
print('=' * 108)
