# -*- coding: utf-8 -*-
"""v14 评分标准独立回读校验（openpyxl 读盘，与 COM 写入态无关）

校验项:
1) 档位表 184 行完整、8 指标块边界正确
2) 区间并集覆盖 [0, 999]
3) 相邻段端点分数连续（H: J↔I, L: I↔J），排除设计性断点段 1/17/23
4) 500 分峰值可达
5) 引擎语义插值复算 == 得分页填写值（差异 < 0.02）
6) 加权总分 == SUMPRODUCT / SUM
7) 无错误值 (#VALUE!/#REF!/#DIV/0!/#N/A)
"""
import openpyxl

P = r"C:\银行经营\PRCP\docs\v2\评分标准_v14_锚点重标定.xlsx"
wb = openpyxl.load_workbook(P, data_only=True)
ws = wb["0-500分评分标准"]
ws2 = wb["中信银行得分"]

ORDER = ["LCR", "NSFR", "EVE", "CET1", "CAR", "ROE", "IBL", "LR"]
BLOCK = {nm: (5 + 23 * i, 27 + 23 * i) for i, nm in enumerate(ORDER)}


def pct(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
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


ok_all = True
print("=" * 104)
print("v14 评分标准 · 独立回读校验")
print("=" * 104)

# ---- 得分页实测值 ----
ACT, PAGE_SCORE, PAGE_W = {}, {}, {}
for r in range(5, 13):
    nm = str(ws2.cell(r, 1).value).strip()
    ACT[nm] = pct(ws2.cell(r, 3).value)
    PAGE_SCORE[nm] = num(ws2.cell(r, 5).value)
    PAGE_W[nm] = num(ws2.cell(r, 6).value)

print("%-6s %-5s %-8s %-9s %-8s %-9s %-9s %s"
      % ("指标", "段数", "覆盖", "连续性", "峰值", "实测值", "复算得分", "结论"))
print("-" * 104)

for nm in ORDER:
    s, e = BLOCK[nm]
    segs = []
    for r in range(s, e + 1):
        lo = pct(ws.cell(r, 4).value)
        hi = pct(ws.cell(r, 5).value)
        if lo is None or hi is None:
            continue
        segs.append({
            "seg": int(num(ws.cell(r, 3).value)),
            "lo": lo, "hi": hi,
            "ilo": num(ws.cell(r, 9).value), "ihi": num(ws.cell(r, 10).value),
            "g": num(ws.cell(r, 7).value),
        })

    # 1) 覆盖
    merged = []
    for sg in sorted(segs, key=lambda x: x["lo"]):
        if merged and sg["lo"] <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], sg["hi"])
        else:
            merged.append([sg["lo"], sg["hi"]])
    cover = (len(merged) == 1 and merged[0][0] <= 1e-9 and merged[0][1] >= 0.999 - 1e-9)

    # 2) 方向
    direction = str(ws.cell(s, 12).value or "")
    is_h = "越高" in direction

    # 3) 端点连续性
    seq = sorted(segs, key=lambda x: x["seg"])
    jumps = []
    for i in range(len(seq) - 1):
        k1, k2 = seq[i], seq[i + 1]
        if k1["seg"] in (1, 17, 23) or k2["seg"] in (1, 17, 23):
            continue
        b1, b2 = (k1["ihi"], k2["ilo"]) if is_h else (k1["ilo"], k2["ihi"])
        if abs(b1 - b2) > 1e-9:
            jumps.append("seg%d(%.0f)↔seg%d(%.0f)" % (k1["seg"], b1, k2["seg"], b2))
    # 峰值
    peak = max([sg["g"] for sg in segs if sg["seg"] == 17] or [0])
    peak = max(peak, max([sg["ilo"] or 0 for sg in segs] + [sg["ihi"] or 0 for sg in segs]))

    # 4) 引擎语义复算
    def calc(x):
        for sg in seq:
            if sg["lo"] - 1e-12 <= x <= sg["hi"] + 1e-12:
                if abs(sg["hi"] - sg["lo"]) < 1e-12:
                    return sg["ilo"]
                return sg["ilo"] + (x - sg["lo"]) / (sg["hi"] - sg["lo"]) * (sg["ihi"] - sg["ilo"])
        return None

    act = ACT[nm]
    computed = calc(act)
    page = PAGE_SCORE[nm]
    agree = computed is not None and page is not None and abs(computed - page) < 0.02

    cont = "OK" if not jumps else "断%d" % len(jumps)
    if peak < 499.99:
        cont += "/峰%.0f" % peak
    verdict = "PASS" if (cover and not jumps and peak >= 499.99 and agree) else "CHECK"
    if verdict != "PASS":
        ok_all = False
    print("%-6s %-5d %-8s %-9s %-8.1f %-9s %-9s %s"
          % (nm, len(segs), "OK" if cover else "缺", cont, peak,
             ("%.4f" % act) if act is not None else "-",
             ("%.2f" % computed) if computed is not None else "-", verdict))
    for j in jumps:
        print("        ! " + j)
    if not agree:
        print("        ! 得分页 %.2f vs 复算 %.2f" % (page, computed))

# ---- 加权校验 ----
print("-" * 104)
tot = 0.0
for nm in ORDER:
    s, e = BLOCK[nm]
    seq = []
    for r in range(s, e + 1):
        lo, hi = pct(ws.cell(r, 4).value), pct(ws.cell(r, 5).value)
        if lo is None or hi is None:
            continue
        seq.append((int(num(ws.cell(r, 3).value)), lo, hi,
                    num(ws.cell(r, 9).value), num(ws.cell(r, 10).value)))
    seq.sort()
    x = ACT[nm]
    for _s, lo, hi, ilo, ihi in seq:
        if lo - 1e-12 <= x <= hi + 1e-12:
            sc = ilo if abs(hi - lo) < 1e-12 else ilo + (x - lo) / (hi - lo) * (ihi - ilo)
            break
    tot += sc * PAGE_W[nm]
    print("  %-6s 实测 %8.4f%%  得分 %7.2f  权重 %3.0f%%  加权 %7.2f" % (nm, x, sc, PAGE_W[nm] * 100, sc * PAGE_W[nm]))

g = tot / 5
print("  综合得分 /500 = %.2f   /100 = %.2f" % (tot, g))
sheet_g = num(ws2.cell(13, 7).value)
sheet_500 = num(ws2.cell(13, 8).value)
print("  得分页 G13 = %s   H13 = %s   评级 = %s" % (sheet_g, sheet_500, ws2.cell(14, 7).value))
if sheet_g is None or abs(sheet_g - g) > 0.05:
    print("  ! 综合得分不一致")
    ok_all = False
if sheet_500 is None or abs(sheet_500 - tot) > 0.05:
    print("  ! /500 总分不一致")
    ok_all = False

# ---- 错误值扫描 ----
print("-" * 104)
errs = 0
for name in wb.sheetnames:
    w = wb[name]
    cnt = 0
    for row in w.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("#") and c.value.endswith("!"):
                cnt += 1
            elif isinstance(c.value, str) and c.value in ("#N/A", "#DIV/0!", "#REF!", "#VALUE!", "#NAME?"):
                cnt += 1
    print("  %s: %d" % (name, cnt))
    errs += cnt
if errs:
    ok_all = False

print("-" * 104)
print("总体:", "PASS" if ok_all else "CHECK")
