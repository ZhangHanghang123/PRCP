# -*- coding: utf-8 -*-
"""ΔEVE v2 独立复算（不读生成结果，直接从源数据算），供 Excel 结果交叉校验"""
import openpyxl

SRC = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v5.xlsx"
src = openpyxl.load_workbook(SRC, data_only=True)["基础数据"]

accounts = []
for r in range(4, 44):
    if src.cell(r, 7).value != 1:
        continue
    accounts.append({
        "sid": src.cell(r, 3).value,
        "name": str(src.cell(r, 4).value).strip(),
        "kind": src.cell(r, 8).value,
        "mint": src.cell(r, 143).value or 0,
        "cf": [src.cell(r, c).value or 0 for c in range(76, 140)],
    })
years = [round((i + 1) / 12, 4) for i in range(60)] + [10, 15, 20, 30]
curve = [src.cell(r, 2).value or 0 for r in range(48, 112)]
BETA = 0.5
LOWER = 0.0
SHORT_Y = 1.0


def build(code, bp):
    out = []
    for i, y in enumerate(years):
        c = curve[i]
        if code == "baseline":
            out.append(c)
        elif code == "parallel_up":
            out.append(max(LOWER, c + bp / 100))
        elif code == "parallel_down":
            out.append(max(LOWER, c - bp / 100))
        elif code == "steepener":
            out.append(c if y <= SHORT_Y else min(c + 1, c + (y - SHORT_Y) * bp / 100))
        elif code == "flattener":
            out.append(max(LOWER, c - bp / 100) if y <= SHORT_Y else c)
        elif code == "short_up":
            out.append(max(LOWER, c + bp / 100) if y <= SHORT_Y else c)
        else:
            out.append(max(LOWER, c - bp / 100) if y <= SHORT_Y else c)
    return out


def pv(cf, rates):
    s = 0.0
    for m in range(60):
        s += cf[m] / (1 + rates[m] / 100) ** ((m + 1) / 12)
    for j, t in enumerate([10, 15, 20, 30]):
        s += cf[60 + j] / (1 + rates[60 + j] / 100) ** t
    return s


SC = [("baseline", 0), ("parallel_up", 250), ("parallel_down", 250), ("steepener", 100),
      ("flattener", 100), ("short_up", 250), ("short_down", 250)]

E = 1e8
base = build("baseline", 0)
res = {}
for code, bp in SC:
    sc_curve = build(code, bp)
    liab_curve = [base[i] + (sc_curve[i] - base[i]) * BETA for i in range(64)]
    apv = lpv = 0.0
    for a in accounts:
        if a["kind"] == "ASSET":
            apv += pv(a["cf"], sc_curve)
        elif a["kind"] == "LIAB":
            lpv += pv(a["cf"], liab_curve)
    res[code] = (apv / E, lpv / E, (apv - lpv) / E)

print("=== ΔEVE v2 Python 独立复算（β=%.2f）===" % BETA)
print("%-16s %14s %14s %14s %14s" % ("情景", "资产PV(亿)", "负债PV(亿)", "EVE(亿)", "ΔEVE(亿)"))
b_eve = res["baseline"][2]
for code, _ in SC:
    a, l, e = res[code]
    print("%-16s %14.2f %14.2f %14.2f %14.2f" % (code, a, l, e, e - b_eve))
print()
print("--- 多口径（最坏情景取 max|ΔEVE|）---")
tot_asset = res["baseline"][0]
dep = sum(pv(a["cf"], base) for a in accounts if a["kind"] == "LIAB" and "存款" in a["name"]
          and "市场化" not in a["name"]) / E
ear = sum(pv(a["cf"], base) for a in accounts if a["kind"] == "ASSET" and "非生息" not in a["name"]) / E
nii = (sum(a["mint"] for a in accounts if a["kind"] == "ASSET")
       - sum(a["mint"] for a in accounts if a["kind"] == "LIAB")) * 12 / E
print("总资产PV=%.2f  存款合计PV=%.2f  生息资产PV=%.2f  NII基准=%.2f 亿" % (tot_asset, dep, ear, nii))
worst = max(SC[1:], key=lambda x: abs(res[x[0]][2] - b_eve))
de = res[worst[0]][2] - b_eve
print("最坏情景=%s  ΔEVE=%.2f亿" % (worst[0], de))
print("  EVE_PCT = %.4f%%" % (de / b_eve * 100))
print("  EVE_ABS = %.4f%%" % (abs(de) / abs(b_eve) * 100))
print("  AST     = %.4f%%" % (de / tot_asset * 100))
print("  DEP     = %.4f%%" % (de / dep * 100))
print("  IAR     = %.4f%%" % (de / ear * 100))
# 久期
def macaulay(cf, rates):
    num = sum(cf[m] * ((m + 1) / 12) / (1 + rates[m] / 100) ** ((m + 1) / 12) for m in range(60))
    for j, t in enumerate([10, 15, 20, 30]):
        num += cf[60 + j] * t / (1 + rates[60 + j] / 100) ** t
    return num / pv(cf, rates)


a_sum = sum(pv(a["cf"], base) for a in accounts if a["kind"] == "ASSET")
l_sum = sum(pv(a["cf"], base) for a in accounts if a["kind"] == "LIAB")
a_dur = sum(pv(a["cf"], base) * macaulay(a["cf"], base) for a in accounts if a["kind"] == "ASSET") / a_sum
l_dur = sum(pv(a["cf"], base) * macaulay(a["cf"], base) for a in accounts if a["kind"] == "LIAB") / l_sum
print("D_A=%.4f 年  D_L=%.4f 年  DGAP=%.4f 年" % (a_dur, l_dur, a_dur - (l_sum / a_sum) * l_dur))
