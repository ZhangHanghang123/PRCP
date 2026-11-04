"""v14 严格引擎语义对拍 —— 复刻 backend/app/routers/kpi.py 的 PIECEWISE 实现

引擎真实语义（kpi.py L778-812）：
  1) 按 seg_order 升序遍历，**闭区间**命中 [min_value, max_value]（value < mn 或 value > mx 才排除）
  2) 首个命中即 break
  3) 插值：score = score_min + (x - mn)/(mx - mn) * (score - score_min)
     条件：score_min 非空 且 mn 非空 且 mx 非空 且 mx > mn
     否则退化为阶梯：score = score
  4) 单点段 (mx == mn) 不插值，直接取 score

校验目标：
  A. 全域网格：闭区间语义下 引擎得分 == 解析函数 T(x)
  B. 关键边界点：所有段端点值处引擎得分 == T(x)
  C. 峰值可达：500 分真实可达（引擎语义）
  D. 命中段唯一性：每个 x 只命中一段（闭区间重叠检测）
"""
import csv, io, json, sys
sys.stdout.reconfigure(encoding='utf-8')

Tsv = 'C:/银行经营/PRCP/docs/_v14_segments.tsv'

# ---------- 读档位表 ----------
rows = list(csv.reader(io.open(Tsv, encoding='utf-8-sig'), delimiter='\t'))
cur = None
recs = []
for r in rows:
    rr = list(r)
    if rr[0].strip():
        cur = rr[0].strip()
    rr[0] = cur
    recs.append(rr)

SEG = {}
DIR = {}
for r in recs:
    name = r[0]
    SEG.setdefault(name, []).append({
        'seg': int(r[2]),
        'lo': float(r[3]),
        'hi': float(r[4]),
        'score': float(r[9]),      # J 列 = 区间上界分
        'score_min': float(r[8]),  # I 列 = 区间下界分
        'desc': r[7],
    })
    # 方向文本只写在每块首行（合并单元格），仅在非空时赋值
    if r[11].strip():
        DIR[name] = 'L' if '越低越好' in r[11] else 'H'
for name in SEG:
    SEG[name].sort(key=lambda s: s['seg'])

# ---------- 解析函数 T(x)（来自 build_score_standard_v14.py 的锚点定义） ----------
_RAW = json.load(io.open('C:/银行经营/PRCP/docs/_v14_anchors.json', encoding='utf-8-sig'))
_RAW_IND = _RAW['indicators']


def theory_score(cfg, x):
    """与生成器一致的解析分数函数。

    注意单位约定：
      - cfg 中的锚点 a0/a1/a2/a4 是【百分数单位】（120.0 表示 120%）
      - x 也按百分数单位传入（本函数内统一转换）
      调用方传入百分数单位 x_pct，函数内部除以 100 与小数单位对齐。
    """
    d = cfg['dir']
    a0, a1, a2, a4 = cfg['a0'], cfg['a1'], cfg['a2'], cfg['a4']
    over = cfg.get('over', 'penalty')
    floor = float(cfg.get('floor', 300))
    dl = float(cfg.get('delta', 0) or 0)
    if d == 'H':
        if x <= a0:
            return 0.0
        if x <= a1:
            return (x - a0) / (a1 - a0) * 150.0
        if x <= a2:
            return 150.0 + (x - a1) / (a2 - a1) * 150.0
        if x <= a4:
            return 300.0 + (x - a2) / (a4 - a2) * 200.0
        if over == 'flat':
            return 500.0
        if dl <= 0:
            return 500.0
        if x >= a4 + dl:
            return floor
        return 500.0 - (x - a4) / dl * (500.0 - floor)
    else:
        # L 方向：a0(红线,最高) > a1 > a2 > a4(标杆,最低)
        if x >= a0:
            return 0.0
        if x >= a1:
            return (a0 - x) / (a0 - a1) * 150.0
        if x >= a2:
            return 150.0 + (a1 - x) / (a1 - a2) * 150.0
        if x >= a4:
            return 300.0 + (a2 - x) / (a2 - a4) * 200.0
        if over == 'flat':
            return 500.0
        if dl <= 0:
            return 500.0
        if x <= a4 - dl:
            return floor
        return 500.0 - (a4 - x) / dl * (500.0 - floor)


# ---------- 引擎复刻（闭区间 + 首个命中） ----------
def engine_score(segs, x):
    """逐字节复刻 kpi.py PIECEWISE"""
    for s in segs:
        mn, mx = s['lo'], s['hi']
        if mn is not None and x < mn:
            continue
        if mx is not None and x > mx:
            continue
        sc = s['score']
        smin = s['score_min']
        if smin is not None and mx > mn:
            ratio = (x - mn) / (mx - mn)
            return smin + ratio * (sc - smin), s
        return sc, s
    return None, None


def hit_count(segs, x):
    """闭区间下命中该 x 的段数"""
    n = 0
    for s in segs:
        if x >= s['lo'] and x <= s['hi']:
            n += 1
    return n


# ---------- 校验 ----------
FAIL = []
print('=' * 108)
print('v14 · 严格引擎语义对拍（闭区间 + seg_order 首个命中，复刻 kpi.py PIECEWISE）')
print('=' * 108)
print('%-6s %-6s %-11s %-11s %-9s %-9s %-8s %-8s %s' % (
    '指标', '方向', '网格maxΔ', '边界maxΔ', '峰值', 'T(实测)', '区间重叠', '插值段', '结论'))

for name in SEG:
    cfg = _RAW_IND.get(name)
    if cfg is None:
        FAIL.append('%s: anchors.json 缺配置' % name)
        continue
    segs = SEG[name]

    # A. 网格扫描：全域 0~1.0 之间 + 超出区间
    xs = [i / 10000.0 for i in range(0, 10001)]
    xs += [i / 1000.0 for i in range(0, 1001, 1)]
    maxd_grid = 0.0
    for x in xs:
        e, s = engine_score(segs, x)
        t = theory_score(cfg, x * 100.0)   # 小数单位 → 百分数单位
        if e is None:
            continue
        maxd_grid = max(maxd_grid, abs(e - t))

    # B. 边界点：所有段的 lo/hi
    maxd_bnd = 0.0
    bnd_detail = []
    for s in segs:
        for x in (s['lo'], s['hi']):
            e, hs = engine_score(segs, x)
            t = theory_score(cfg, x * 100.0)
            if e is None:
                continue
            d = abs(e - t)
            if d > maxd_bnd:
                maxd_bnd = d
                bnd_detail = (x, e, t, s['seg'], hs['seg'] if hs else None)

    # C. 峰值可达（引擎语义）
    peak = 0.0
    peak_x = None
    cand = sorted(set([s['lo'] for s in segs] + [s['hi'] for s in segs]))
    for x in cand:
        e, _ = engine_score(segs, x)
        if e is not None and e > peak:
            peak, peak_x = e, x

    # D. 闭区间重叠检测（同一 x 被多段覆盖）
    #    合法重叠源：①相邻段共享端点（闭区间必然重叠于边界点）
    #                ②单点峰值段(段17)与段16/18 在 a4 处重合
    #    非法重叠：非相邻段重叠 ⇒ 区间设计错误
    overlap = 0
    bad_overlap = []
    for s in segs:
        for x in (s['lo'], s['hi']):
            hits = [t['seg'] for t in segs if x >= t['lo'] and x <= t['hi']]
            c = len(hits)
            if c > overlap:
                overlap = c
            # 合法性：命中的段必须两两相邻（差值 ≤1）
            if c > 1:
                hs = sorted(hits)
                for i in range(len(hs) - 1):
                    if hs[i + 1] - hs[i] > 1:
                        bad_overlap.append((x, hs))
                        break

    # E. 插值段数（应有 score_min 且 mx>mn 的段数）
    n_interp = sum(1 for s in segs if s['score_min'] is not None and s['hi'] > s['lo'])

    # 实测值（cfg['act'] 为百分数单位）
    t_real = theory_score(cfg, cfg['act'])

    ok = (maxd_grid < 1e-9 and maxd_bnd < 1e-9 and peak >= 499.999
          and not bad_overlap and n_interp >= 20)
    if not ok:
        FAIL.append('%s: gridΔ=%.2e bndΔ=%.2e peak=%.2f overlap=%d bad=%s interp=%d %s'
                    % (name, maxd_grid, maxd_bnd, peak, overlap,
                       bad_overlap[:2], n_interp, bnd_detail))

    print('%-6s %-6s %-11.3e %-11.3e %-9.2f %-9.2f %-8d %-8d %s' % (
        name, DIR[name], maxd_grid, maxd_bnd, peak, t_real, overlap, n_interp,
        'PASS' if ok else 'FAIL'))

print()
print('-' * 108)

# ---------- 关键边界点明细（展示闭区间首命中效应） ----------
print()
print('【闭区间首个命中 · 端点归属实测】')
for name in ('LCR', 'EVE', 'IBL'):
    segs = SEG[name]
    print('\n  %s (%s):' % (name, DIR[name]))
    for s in segs:
        if s['seg'] in (1, 16, 17, 18, 22, 23):
            for x in (s['lo'], s['hi']):
                e, hs = engine_score(segs, x)
                t = theory_score(_RAW_IND[name], x * 100.0)
                print('    x=%-10.6f  引擎=%-8.2f (命中段%-3s)  T(x)=%-8.2f  Δ=%.2e  %s'
                      % (x, e, hs['seg'] if hs else '-', t, abs(e - t),
                         'OK' if abs(e - t) < 1e-6 else 'MISMATCH'))

print()
print('=' * 108)
if FAIL:
    print('总体: FAIL')
    for f in FAIL:
        print('  ✗', f)
    sys.exit(1)
print('总体: PASS —— 8 指标在引擎真实闭区间语义下，T(x) 与引擎插值全域一致，500 分峰值可达')
print('=' * 108)
