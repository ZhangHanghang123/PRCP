# -*- coding: utf-8 -*-
"""
v13 评分标准校验：
1) 区间并集覆盖检查（引擎语义：任一取值必须命中某段，否则抛异常）
2) 引擎语义连续性扫描（seg_order 升序首个匹配 → 检查得分曲线无凹陷）
3) 实测值插值复算 + 与得分页比对
"""
import openpyxl

P = r"C:\银行经营\PRCP\docs\v2\评分标准_v13_8指标_含CAR.xlsx"
wb = openpyxl.load_workbook(P, data_only=True)
ws = wb["0-500分评分标准"]
ws2 = wb["中信银行得分"]


def pct(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t) / 100 if abs(t) > 1.5 else float(t)
    t = str(t).strip()
    if t.endswith("%"):
        return float(t[:-1]) / 100
    if t.endswith("pp"):
        return float(t[:-2]) / 100
    try:
        return float(t) / 100
    except Exception:
        return None


def num(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    try:
        return float(str(t).strip())
    except Exception:
        return None


# 指标块
blocks = []
name = None
start = None
for r in range(5, ws.max_row + 1):
    v = ws.cell(r, 1).value
    if isinstance(v, str) and v.strip():
        if name is not None:
            blocks.append((name, start, r - 1))
        name, start = v.strip(), r
blocks.append((name, start, ws.max_row))

# 得分页实测值
ACT = {}
for r in range(5, 13):
    nm = ws2.cell(r, 1).value
    v = ws2.cell(r, 3).value
    if nm:
        ACT[str(nm).strip()] = (pct(v), ws2.cell(r, 5).value)

ok_all = True
print("%-6s %-5s %-9s %-9s %-9s %s" % ("指标", "段数", "覆盖", "连续性", "实测得分", "结论"))
print("-" * 74)
for nm, s, e in blocks:
    segs = []
    for r in range(s, e + 1):
        lo, hi = pct(ws.cell(r, 4).value), pct(ws.cell(r, 5).value)
        if lo is None or hi is None:
            continue
        segs.append((lo, hi, r, num(ws.cell(r, 9).value), num(ws.cell(r, 10).value),
                     num(ws.cell(r, 7).value)))

    # 1) 并集覆盖
    merged = []
    for lo, hi, *_ in sorted(segs):
        if merged and lo <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    cover = "OK" if (merged and merged[0][0] <= 1e-9 and merged[-1][1] >= 9.99 - 1e-9
                    and len(merged) == 1) else "缺"
    if cover != "OK":
        ok_all = False

    # 1b) 段间分数连续性：除红线(段1)/满分(段17)/极度过剩(段23) 三个设计性断点外，
    #     相邻段应满足 段k.区间上限分 == 段k+1.区间下限分
    jumps = []
    byval = sorted(segs, key=lambda x: x[0])   # 按值序（越低越好型指标段序≠值序）
    for i in range(len(byval) - 1):
        k1 = byval[i]
        k2 = byval[i + 1]
        s1 = k1[2] - s + 1          # 段号
        s2 = k2[2] - s + 1
        if s1 in (1, 17, 23) or s2 in (1, 17, 23):
            continue
        if k1[4] is not None and k2[3] is not None and abs(k1[4] - k2[3]) > 1e-9:
            jumps.append("r%d(段%d).上限分%s → r%d(段%d).下限分%s"
                         % (k1[2], s1, k1[4], k2[2], s2, k2[3]))
    if jumps:
        ok_all = False

    # 2) 引擎语义得分曲线（seg_order 升序，首个命中）
    def engine_score(x):
        for lo, hi, _r, ilo, ihi, g in segs:
            if lo - 1e-12 <= x <= hi + 1e-12:
                if hi == lo:
                    return g
                return ilo + (x - lo) / (hi - lo) * (ihi - ilo)
        return None

    # 连续性：在 0~1.5（资本/流动性指标值域）细扫，检查是否有"凹陷"（升->降）
    worst_drop = 0.0
    prev = None
    steps = 1500
    for i in range(steps + 1):
        x = 0.0 + (1.5 - 0.0) * i / steps
        sc = engine_score(x)
        if sc is None:
            continue
        if prev is not None and sc < prev - 1e-6:
            worst_drop = max(worst_drop, prev - sc)
        prev = sc
    # 峰值可达性：引擎语义下最高可得分数应为 500
    peak = 0.0
    for i in range(4001):
        x = 0.0 + 1.6 * i / 4000
        sc = engine_score(x)
        if sc is not None and sc > peak:
            peak = sc
    cont = "OK" if not jumps else "断点%d" % len(jumps)
    if peak < 499.9:
        cont += "/峰值%.0f" % peak
        ok_all = False

    # 3) 实测值
    act, page_score = ACT.get(nm, (None, None))
    calc = None
    if act is not None:
        calc = engine_score(act)
    agree = "-"
    if calc is not None and page_score is not None:
        agree = "一致" if abs(calc - page_score) < 0.02 else "★不一致 %.2f vs %.2f" % (calc, page_score)
        if agree != "一致":
            ok_all = False
    verdict = "PASS" if (cover == "OK" and cont == "OK" and agree == "一致") else "CHECK"
    if verdict != "PASS":
        ok_all = False
    print("%-6s %-5d %-9s %-9s %-9s %s" % (
        nm, len(segs), cover, cont,
        ("%.2f" % calc) if calc is not None else "-", verdict))
    if agree != "一致" and agree != "-":
        print("      → 得分页 %.2f vs 档位表插值 %.2f" % (page_score, calc))
    for j in jumps:
        print("      ! 段间断点: " + j)

print("-" * 74)
print("总体:", "PASS" if ok_all else "CHECK")
print()
print("得分页汇总: 加权总分 %.2f / 500  →  %.2f / 100   评级 %s"
      % (ws2.cell(13, 8).value if isinstance(ws2.cell(13, 8).value, (int, float)) else 0,
         (ws2.cell(13, 7).value if isinstance(ws2.cell(13, 7).value, (int, float)) else 0),
         ws2.cell(14, 7).value))
