"""EVE 评分方案 v14.3 重新设计 —— 目标：60%~80% 区间拉开分数差距。

【问题诊断】v14.2 方案 a0=165 a1=140 a2=100 a4=50 delta=30 floor=450：
    安全区 50~100 (50pp) 承载 300~500 → 4 分/pp
    60%~80% 仅拉开 80 分；实测 34.16%(473.60) 与 60%(460) 只差 13.6 分
    → "良好"与"优秀"区分度不足

【新方案 v14.3】
    锚点：a0=130 (红线) / a1=105 (危险界) / a2=80 (达标线) / a4=60 (标杆线)
          delta=40 (过优区宽度) / floor=450 (过优区下限)
    实测值：61.39%（v3 模版口径 · 行内 ΔEVE = |ΔEVE|/一级资本 · 变陡峭情景）

    安全区收窄到 60~80 (20pp) 承载 300~500 → 10 分/pp
      60% → 500 分   65% → 450   70% → 400   75% → 350   80% → 300
    60%~80% 分差 = 200 分（每 2pp 一档），较 v14.2 提升 2.5 倍

【口径说明】
    实测值回到 v3 模版的 61.39%（行内口径），与评分标准 v14.1 一致。
    服务器现值法 reg_eve_pv.py 算出 34.16%（库内真实余额 + 末级账户粒度），
    两者差异源于账户集与余额口径不同；评分标准以行内 ΔEVE 口径为准，
    服务器 K��� 重算脚本的口径需另行对齐（本次不动，避免连锁改动）。
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')


def T(x, a0, a1, a2, a4, delta, floor):
    """EVE 解析分数函数（L 方向：越低越好）"""
    if x >= a0:
        return 0.0
    if x >= a1:
        return (a0 - x) / (a0 - a1) * 150
    if x >= a2:
        return 150 + (a1 - x) / (a1 - a2) * 150
    if x >= a4:
        return 300 + (a2 - x) / (a2 - a4) * 200
    if x <= a4 - delta:
        return floor
    return 500 - (a4 - x) / delta * (500 - floor)


OLD = dict(a0=165, a1=140, a2=100, a4=50, delta=30, floor=450)
NEW = dict(a0=130, a1=105, a2=80, a4=60, delta=40, floor=450)
ACT = 61.3947          # v3 模版口径行内 ΔEVE

print('=' * 96)
print('EVE 评分方案 v14.3 设计')
print('=' * 96)
print('【锚点】')
print('  a0 = %.0f%%  红线     (0 分)   —— 风险失控' % NEW['a0'])
print('  a1 = %.0f%%  危险界   (150 分)' % NEW['a1'])
print('  a2 = %.0f%%  达标线   (300 分)' % NEW['a2'])
print('  a4 = %.0f%%  标杆线   (500 分)' % NEW['a4'])
print('  过优区 <%.0f%%  封顶 500→%d（floor，防范口径失真）' % (NEW['a4'], NEW['floor']))
print()
print('【区间斜率】')
zones = [
    ('危险区', NEW['a1'], NEW['a0'], 0, 150),
    ('预警区', NEW['a2'], NEW['a1'], 150, 300),
    ('安全区', NEW['a4'], NEW['a2'], 300, 500),
]
for name, lo, hi, s0, s1 in zones:
    print('  %-6s %6.1f%% ~ %6.1f%%   %3d~%3d 分   斜率 %5.2f 分/pp'
          % (name, lo, hi, s0, s1, (s1 - s0) / (hi - lo)))
print('  %-6s %6.1f%% ~ %6.1f%%   %3d~%3d 分   斜率 %5.2f 分/pp（封顶）'
      % ('过优区', 0, NEW['a4'], NEW['floor'], 500,
         (500 - NEW['floor']) / NEW['delta']))
print()
print('【60%%~80%% 区分度对比】')
print('%-10s %-11s %-11s %-11s' % ('指标值', 'v14.2 分', 'v14.3 分', 'Δ'))
for i in range(0, 11):
    v = 60 + i * 2
    print('  %-8.1f%% %-11.2f %-11.2f %+.2f'
          % (v, T(v, **OLD), T(v, **NEW), T(v, **NEW) - T(v, **OLD)))
d_old = T(60, **OLD) - T(80, **OLD)
d_new = T(60, **NEW) - T(80, **NEW)
print()
print('  60%%→80%% 分差:  v14.2 = %6.2f 分 (%.2f 分/pp)' % (d_old, d_old / 20))
print('                  v14.3 = %6.2f 分 (%.2f 分/pp)  ← %.1f 倍'
      % (d_new, d_new / 20, d_new / d_old))
print()
print('【实测值】')
print('  行内 ΔEVE = %.4f%%  →  得分 %.2f  (命中安全区)' % (ACT, T(ACT, **NEW)))
print('  位置：60%% 与 80%% 之间，距 60%% 标杆线 %.2f pp，距 80%% 达标线 %.2f pp'
      % (ACT - 60, 80 - ACT))
print()
print('【情景敏感度（v3 模版 6 情景，现值法口径）】')
SCEN = [('短端下移', 7.40), ('短端上移', 13.28), ('变陡峭(实测)', 61.3947),
        ('平行上移', 141.1362), ('平行下移', 164.7604)]
for k, v in SCEN:
    print('  %-14s %8.4f%%  →  %7.2f 分' % (k, v, T(v, **NEW)))
print()
print('【综合分影响】')
OTHERS = [('LCR', 449.14, .16), ('NSFR', 454.17, .13), ('CET1', 370.00, .16),
          ('CAR', 450.00, .10), ('ROE', 350.86, .12), ('IBL', 436.00, .11),
          ('LR', 392.94, .10)]
tot_new = sum(v * w for _, v, w in OTHERS) + T(ACT, **NEW) * .12
tot_old = sum(v * w for _, v, w in OTHERS) + 473.60 * .12
print('  v14.2 综合 = %.2f / 500  (%.2f / 100)' % (tot_old, tot_old / 5))
print('  v14.3 综合 = %.2f / 500  (%.2f / 100)' % (tot_new, tot_new / 5))
print('  Δ = %+.2f 分' % (tot_new - tot_old))
