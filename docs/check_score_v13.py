# -*- coding: utf-8 -*-
"""校验 v13 评分标准：区间覆盖完整性 / 重叠 / 空洞 + 插值得分复算"""
import openpyxl
import re

P = r"C:\银行经营\PRCP\docs\v2\评分标准_v13_8指标_含CAR.xlsx"
wb = openpyxl.load_workbook(P, data_only=True)
ws = wb["0-500分评分标准"]


def num(txt):
    if txt is None:
        return None
    t = str(txt).strip()
    if t.endswith("%"):
        return float(t[:-1]) / 100
    if t.endswith("pp"):
        return float(t[:-2]) / 100
    return None


# 找指标块起始行
blocks = []
cur = None
for r in range(5, ws.max_row + 1):
    v = ws.cell(r, 1).value
    if isinstance(v, str) and v.strip():
        cur = (v.strip(), r)
    if cur:
        blocks.append((cur[0], cur[1], r))
blocks = [(n, s, e) for (n, s, e) in blocks if n != blocks[0][0] or s == blocks[0][1]]

# 更稳：按 A 列有值分段
segs = []
start = None
name = None
for r in range(5, ws.max_row + 1):
    v = ws.cell(r, 1).value
    if isinstance(v, str) and v.strip():
        if name is not None:
            segs.append((name, start, r - 1))
        name = v.strip()
        start = r
if name:
    segs.append((name, start, ws.max_row))

print("指标块:", [(n, s, e) for n, s, e in segs])
print()
ACT = {"LCR": 1.4729, "NSFR": 1.0452, "EVE": 0.1054, "CET1": 0.0898,
       "CAR": 0.1280, "ROE": 0.0961, "IBL": 0.2160, "LR": 0.0706}
DIR = {"LCR": "up", "NSFR": "up", "EVE": "down", "CET1": "up",
       "CAR": "up", "ROE": "up", "IBL": "down", "LR": "up"}

allok = True
for nm, s, e in segs:
    ivs = []
    for r in range(s, e + 1):
        lo, hi = num(ws.cell(r, 4).value), num(ws.cell(r, 5).value)
        if lo is None or hi is None:
            continue
        ivs.append((lo, hi, r, ws.cell(r, 3).value, ws.cell(r, 7).value,
                    ws.cell(r, 9).value, ws.cell(r, 10).value))
    issues = []
    # 段号连续
    segs_no = [x[3] for x in ivs]
    if segs_no != list(range(segs_no[0], segs_no[0] + len(segs_no))):
        issues.append("段号不连续: %s" % segs_no)
    # 区间重叠 / 空洞（按方向排序）
    srt = sorted(ivs, key=lambda x: x[0])
    for i in range(1, len(srt)):
        prev, cur = srt[i - 1], srt[i]
        if cur[0] < prev[1] - 1e-9:
            issues.append("重叠: r%d(%.4f~%.4f) 与 r%d(%.4f~%.4f)"
                          % (prev[2], prev[0], prev[1], cur[2], cur[0], cur[1]))
        elif cur[0] > prev[1] + 1e-9:
            issues.append("空洞: (%.4f, %.4f)" % (prev[1], cur[0]))
    # 覆盖端点
    lo_min = min(x[0] for x in ivs)
    hi_max = max(x[1] for x in ivs)
    if lo_min > 1e-9:
        issues.append("低端未覆盖至 0 (起点 %.4f)" % lo_min)
    if hi_max < 9.99 - 1e-9:
        issues.append("高端未覆盖至 999 (终点 %.4f)" % hi_max)
    # 插值得分复算
    act = ACT.get(nm)
    score = None
    if act is not None:
        hit = [x for x in ivs if x[0] - 1e-12 <= act <= x[1] + 1e-12]
        if not hit:
            issues.append("★ 实测值 %.4f 无匹配区间（引擎会抛异常）" % act)
        else:
            lo, hi, rr, sg, g, ilo, ihi = hit[0]
            if hi == lo:
                score = g
            else:
                score = ilo + (act - lo) / (hi - lo) * (ihi - ilo)
    flag = "OK " if not issues else "!! "
    if issues:
        allok = False
    print("%s%-5s 段数=%2d  实测得分=%s" % (flag, nm, len(ivs),
          ("%.2f" % score) if score is not None else "-"))
    for i in issues:
        print("      - " + i)

print()
print("=== 全部指标档位覆盖检查:", "PASS" if allok else "FAIL", "===")

# 权重与总分
ws2 = wb["中信银行得分"]
tw = 0.0
th = 0.0
print("\n=== 得分页 ===")
for r in range(5, 13):
    nm = ws2.cell(r, 1).value
    e = ws2.cell(r, 5).value
    f = ws2.cell(r, 6).value
    tw += f or 0
    th += (e or 0) * (f or 0)
    print("  %-6s 实测=%-9s 档位=%-8s 得分=%-8s 权重=%-6s" %
          (nm, ws2.cell(r, 3).value, ws2.cell(r, 4).value, e, f))
print("  权重合计 = %.4f   加权总分 = %.2f / 500  →  %.2f / 100" % (tw, th, th / 5))
