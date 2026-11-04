"""v14 落库段 vs Excel 档位表 逐格比对

校验：落库脚本 build_segments() 生成的 184 段，
      与 docs/_v14_segments.tsv（Excel 档位表真源）逐格等价。
单位换算：Excel 小数单位 × 100 = 落库百分数单位。

比对维度：
  - seg_order 一一对应
  - min_value / max_value 相等（容差 1e-6）
  - score / score_min 相等（容差 1e-2）
"""
import csv, io, sys
sys.path.insert(0, r'C:/银行经营/PRCP/backend/scripts')
sys.stdout.reconfigure(encoding='utf-8')

from seed_score_rules_v14 import IND, ORDER, build_segments

TSV = r'C:/银行经营/PRCP/docs/_v14_segments.tsv'

# 读 Excel 档位表（首行即数据，指标名前向填充）
rows = list(csv.reader(io.open(TSV, encoding='utf-8-sig'), delimiter='\t'))
cur = None
excel = {}
for r in rows:
    rr = list(r)
    if rr[0].strip():
        cur = rr[0].strip()
    rr[0] = cur
    excel.setdefault(cur, []).append({
        'seg': int(rr[2]),
        'lo': float(rr[3]) * 100.0,
        'hi': float(rr[4]) * 100.0,
        'score': float(rr[9]),
        'score_min': float(rr[8]),
    })
for k in excel:
    excel[k].sort(key=lambda s: s['seg'])

print('=' * 104)
print('v14 落库段 vs Excel 档位表 · 逐格比对（184 段）')
print('=' * 104)

total = 0
mismatch = []
for key in ORDER:
    segs = build_segments(IND[key])
    ex = excel.get(key, [])
    if len(segs) != len(ex):
        mismatch.append('%s 段数不一致: 落库=%d Excel=%d' % (key, len(segs), len(ex)))
        continue
    n_bad = 0
    for (so, mn, mx, sc, smin, _d), e in zip(segs, ex):
        total += 1
        bad = []
        if so != e['seg']:
            bad.append('seg %s≠%s' % (so, e['seg']))
        if abs(mn - e['lo']) > 1e-6:
            bad.append('lo %.6f≠%.6f' % (mn, e['lo']))
        if abs(mx - e['hi']) > 1e-6:
            bad.append('hi %.6f≠%.6f' % (mx, e['hi']))
        if abs(sc - e['score']) > 0.01:
            bad.append('score %.2f≠%.2f' % (sc, e['score']))
        if abs(smin - e['score_min']) > 0.01:
            bad.append('score_min %.2f≠%.2f' % (smin, e['score_min']))
        if bad:
            n_bad += 1
            mismatch.append('%s 段%-3s: %s' % (key, so, '; '.join(bad)))
    st = '✓' if n_bad == 0 else '✗'
    print('  %s %-6s 段数=%-3d 不一致=%d' % (st, key, len(segs), n_bad))

print()
print('  比对总段数 = %d' % total)
if mismatch:
    print('  不一致明细（前 25 条）:')
    for m in mismatch[:25]:
        print('    ✗', m)
    print('\n总体: FAIL —— %d 处不一致' % len(mismatch))
    sys.exit(1)
print('\n总体: PASS —— 184 段与 Excel 档位表逐格完全一致')
print('=' * 104)
