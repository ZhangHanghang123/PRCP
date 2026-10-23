# -*- coding: utf-8 -*-
"""
中信银行 6 指标 4 档评分规则 v9
=================================
v8 基础上新增 IBA (同业资产比), 6 指标重新分配权重:
  LCR 20% + CET1 20% + NSFR 16% + IBL 16% + LR 14% + IBA 14% = 100%
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUTPUT = r"C:/银行经营/PRCP/docs/v2/评分标准_v9b.xlsx"

# ============================================================
# 6 指标 4 档配置
# ============================================================
INDICATORS = {
    # LCR 流动性覆盖率
    "LCR": {
        "code": "LCR", "name": "流动性覆盖率", "direction": "higher",
        "current": 1.4729, "weight": 0.20,
        "red":    (0.000,  1.00, -500, "严重不达标：<100% 触发监管"),
        "red2":   (1.00,   1.10, -300, "<110% 远低于本行底线"),
        "red3":   (1.10,   1.15, -150, "<115% 接近本行底线"),
        "red4":   (1.15,   1.20,  -50, "<120% 红线 触发重惩罚"),
        "dgr1":   (1.20,   1.25,   10, "危险-重惩罚 120-125%"),
        "dgr2":   (1.25,   1.30,   35, "危险-重惩罚 125-130%"),
        "wrn1":   (1.30,   1.35,   70, "预警-轻惩罚 130-135%"),
        "wrn2":   (1.35,   1.40,   85, "预警-轻惩罚 135-140%"),
        "safe1":  (1.40,   1.50,  100, "⭐安全 140-150% 适度最优"),
        "safe2":  (1.50,   1.80,   95, "安全 150-180% 略高"),
        "safe3":  (1.80,   2.50,   80, "安全 180-250% 过高"),
        "safe4":  (2.50,   5.00,   65, "安全 250%+ 极度过剩"),
    },
    # NSFR 净稳定资金比例
    "NSFR": {
        "code": "NSFR", "name": "净稳定资金比例", "direction": "higher",
        "current": 1.0452, "weight": 0.16,
        "red":    (0.000, 1.00, -500, "严重不达标：<100% 触发监管"),
        "red2":   (1.00, 1.02, -200, "<102% 远低于本行底线"),
        "dgr1":   (1.02, 1.03,  10, "危险-重惩罚 102-103%"),
        "dgr2":   (1.03, 1.04,  35, "危险-重惩罚 103-104%"),
        "wrn1":   (1.04, 1.045, 70, "预警-轻惩罚 104-104.5%"),
        "wrn2":   (1.045, 1.05, 85, "⭐中信银行实测 104.52% 段"),
        "safe1":  (1.05, 1.07, 100, "⭐安全 105-107% 适度最优"),
        "safe2":  (1.07, 1.10,  92, "安全 107-110% 略高"),
        "safe3":  (1.10, 1.15,  85, "安全 110-115% 过高"),
        "safe4":  (1.15, 1.20,  78, "安全 115-120% 显著过高"),
        "safe5":  (1.20, 3.00,  70, "安全 120%+ 极度过剩"),
    },
    # CET1 核心一级资本充足率 (红线 8.7%)
    "CET1": {
        "code": "CET1", "name": "核心一级资本充足率", "direction": "higher",
        "current": 0.0898, "weight": 0.20,
        "red":    (0.000, 0.087, -500, "严重不达标：<8.7% 触发监管"),
        "red2":   (0.087, 0.0875, -50, "刚过红线 8.7-8.75%"),
        "dgr1":   (0.0875, 0.088, 35, "危险-重惩罚 8.75-8.8%"),
        "wrn1":   (0.088, 0.089, 75, "预警-轻惩罚 8.8-8.9%"),
        "wrn2":   (0.089, 0.09, 88, "⭐中信银行实测 8.98% 段 预警-轻惩罚"),
        "safe1":  (0.09, 0.095, 100, "⭐安全 9.0-9.5% 适度最优"),
        "safe2":  (0.095, 0.10, 100, "⭐安全 9.5-10%"),
        "safe3":  (0.10, 0.11,  98, "安全 10-11% 略高"),
        "safe4":  (0.11, 0.13,  90, "安全 11-13% 过高"),
        "safe5":  (0.13, 0.15,  82, "安全 13-15% 显著过高"),
        "safe6":  (0.15, 1.00,  75, "安全 15%+ 极度过剩"),
    },
    # IBL 同业负债占比 (负债端)
    "IBL": {
        "code": "IBL", "name": "同业负债占总负债比例 (负债端)", "direction": "lower",
        "current": 0.24, "weight": 0.16,
        "safe1":  (0.000, 0.20, 100, "⭐安全 ≤20%"),
        "safe2":  (0.20, 0.25,  95, "⭐中信银行实测 24% 段 安全"),
        "wrn1":   (0.25, 0.27,  80, "预警-轻惩罚 25-27%"),
        "wrn2":   (0.27, 0.30,  70, "预警-轻惩罚 27-30%"),
        "dgr1":   (0.30, 0.31,  45, "危险-重惩罚 30-31%"),
        "dgr2":   (0.31, 0.3333, 25, "危险-重惩罚 31-33.33%"),
        "red":    (0.3333, 0.40, -500, "红线 >33.33% 触发监管"),
        "red2":   (0.40, 1.00, -500, "红线 远超标"),
    },
    # LR 杠杆率
    "LR": {
        "code": "LR", "name": "杠杆率", "direction": "higher",
        "current": 0.068, "weight": 0.14,
        "red":    (0.000, 0.04, -500, "红线 <4% 触发监管"),
        "dgr1":   (0.04, 0.045, 20, "危险-重惩罚 4-4.5%"),
        "dgr2":   (0.045, 0.05, 40, "危险-重惩罚 4.5-5%"),
        "wrn1":   (0.05, 0.055, 65, "预警-轻惩罚 5-5.5%"),
        "wrn2":   (0.055, 0.06, 80, "预警-轻惩罚 5.5-6%"),
        "safe1":  (0.06, 0.07, 100, "⭐安全 6-7% 适度最优"),
        "safe2":  (0.07, 0.08, 100, "⭐安全 7-8%"),
        "safe3":  (0.08, 1.00, 100, "⭐安全 8%+ 极优"),
    },
    # IBA 同业资产占比 🆕 (资产端)
    "IBA": {
        "code": "IBA", "name": "同业资产占总资产比例 (资产端) 🆕", "direction": "lower",
        "current": 0.11, "weight": 0.14,
        "safe1":  (0.000, 0.08, 100, "⭐安全 ≤8% 流动性最强"),
        "safe2":  (0.08, 0.12,  95, "⭐中信银行实测 11% 段 安全"),
        "safe3":  (0.12, 0.15,  88, "安全 12-15%"),
        "wrn1":   (0.15, 0.18,  75, "预警-轻惩罚 15-18%"),
        "wrn2":   (0.18, 0.20,  65, "预警-轻惩罚 18-20%"),
        "dgr1":   (0.20, 0.25,  40, "危险-重惩罚 20-25%"),
        "dgr2":   (0.25, 0.30,  20, "危险-重惩罚 25-30%"),
        "red":    (0.30, 1.00, -500, "红线 >30% 过度依赖同业资产"),
    },
}

# 平滑性约束参数
SMOOTH_PENALTY = {
    (0, 0.01):    0,
    (0.01, 0.03): 5,
    (0.03, 0.05): 15,
    (0.05, 0.10): 30,
    (0.10, 0.50): 60,
}


def smooth_penalty(deviation):
    for (lo, hi), factor in SMOOTH_PENALTY.items():
        if lo <= deviation < hi:
            return round(factor * (deviation * 100), 2)
    return 0


def find_segment(segments_dict, value):
    for key, val in segments_dict.items():
        if isinstance(val, tuple) and len(val) == 4:
            lo, hi, score, comment = val
            if lo <= value <= hi:
                return key, lo, hi, score, comment
    last_key = list(segments_dict.keys())[-1]
    lo, hi, score, comment = segments_dict[last_key]
    return last_key, lo, hi, score, comment


# ============================================================
# Excel 输出
# ============================================================
wb = openpyxl.Workbook()
wb.remove(wb.active)

thin = Side(border_style="thin", color="DDDDDD")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

def get_rating(score):
    if score >= 90: return "A+ 卓越"
    elif score >= 85: return "A  优秀"
    elif score >= 80: return "B+ 良好"
    elif score >= 70: return "B  中等"
    elif score >= 60: return "C  及格"
    else: return "D  警示"

def tier_color(score):
    if score <= -100: return PatternFill("solid", fgColor="FFCDD2")
    elif score < 60: return PatternFill("solid", fgColor="FFE0B2")
    elif score < 90: return PatternFill("solid", fgColor="FFF9C4")
    else: return PatternFill("solid", fgColor="A5D6A7")

def tier_label(score):
    if score <= -100: return "红线"
    elif score < 60: return "危险-重惩罚"
    elif score < 90: return "预警-轻惩罚"
    else: return "安全"

# ===== Sheet 1 =====
ws1 = wb.create_sheet("4档评分标准")
ws1.merge_cells("A1:K1")
ws1["A1"] = "中信银行 6 指标 4 档评分规则 v9 (新增 IBA 同业资产比, 6 指标)"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:K2")
ws1["A2"] = "LCR 20% + CET1 20% + NSFR 16% + IBL 16% + LR 14% + IBA 14% = 100% | IBA = 同业资产/总资产 (资产端)"
ws1["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[2].height = 22

headers = ["指标", "档位", "子段", "区间下限", "区间上限", "宽度", "得分", "评语", "距实测", "方向", "红线说明"]
for col, h in enumerate(headers, 1):
    cell = ws1.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws1.row_dimensions[4].height = 30

row_idx = 5
all_results = {}
total_segments = 0

for code, cfg in INDICATORS.items():
    segs = cfg
    current = cfg["current"]
    direction = cfg["direction"]

    actual_key, lo_a, hi_a, actual_score, actual_comment = find_segment(segs, current)
    all_results[code] = {
        "actual_key": actual_key,
        "actual_score": actual_score,
        "weight": cfg["weight"],
        "weighted": actual_score * cfg["weight"] if actual_score is not None else None,
        "current": current,
    }
    total_segments += len(segs)

    start_row = row_idx
    seg_keys = [k for k, v in segs.items() if isinstance(v, tuple) and len(v) == 4]
    seg_count = 0
    for key, val in segs.items():
        if not (isinstance(val, tuple) and len(val) == 4):
            continue
        seg_count += 1
        lo, hi, score, comment = val
        width = abs(hi - lo)
        tier = tier_label(score)
        fill = tier_color(score)
        if "⭐" in comment:
            fill = PatternFill("solid", fgColor="FFE082")

        tier_text = tier

        if seg_count == 1:
            ws1.cell(row=row_idx, column=1, value=code)
            ws1.cell(row=row_idx, column=10, value="越高越好" if direction == "higher" else "越低越好")
            ws1.cell(row=row_idx, column=11, value=comment.split('：')[0] if '：' in comment else comment[:20])

        ws1.cell(row=row_idx, column=2, value=tier_text)
        ws1.cell(row=row_idx, column=3, value=seg_keys.index(key) + 1)
        ws1.cell(row=row_idx, column=4, value=f"{lo*100:.4f}%" if width < 0.01 else f"{lo*100:.2f}%")
        ws1.cell(row=row_idx, column=5, value=f"{hi*100:.4f}%" if width < 0.01 else f"{hi*100:.2f}%")
        ws1.cell(row=row_idx, column=6, value=f"{width*100:.2f}pp" if width >= 0.01 else f"{width*100:.4f}pp")
        ws1.cell(row=row_idx, column=7, value=score)
        ws1.cell(row=row_idx, column=8, value=comment)
        dist = abs(((lo + hi) / 2) - current)
        ws1.cell(row=row_idx, column=9, value=f"{dist*100:.2f}pp")

        for c in range(1, 12):
            cell = ws1.cell(row=row_idx, column=c)
            cell.border = border
            cell.font = Font(name="微软雅黑", size=10)
            if c in [2, 3, 4, 5, 6, 7, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="center" if c in [10, 11] else "left", vertical="center", wrap_text=True)
            if c == 7:
                cell.fill = fill
                cell.font = Font(name="微软雅黑", size=11, bold=True)
        if key == actual_key:
            for c in [3, 8]:
                ws1.cell(row=row_idx, column=c).font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
        row_idx += 1

    if row_idx - 1 > start_row:
        ws1.merge_cells(f"A{start_row}:A{row_idx-1}")
        ws1.merge_cells(f"J{start_row}:J{row_idx-1}")
        ws1.merge_cells(f"K{start_row}:K{row_idx-1}")
        for c in [1, 10, 11]:
            cell = ws1.cell(row=start_row, column=c)
            cell.fill = PatternFill("solid", fgColor="F5F5F5")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.font = Font(name="微软雅黑", size=10, bold=True)

widths1 = [8, 14, 6, 12, 12, 10, 10, 40, 10, 12, 30]
for i, w in enumerate(widths1, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.freeze_panes = "A5"

# ===== Sheet 2: 中信银行得分 =====
ws2 = wb.create_sheet("中信银行得分")
ws2.merge_cells("A1:H1")
ws2["A1"] = "中信银行 6 指标 4 档实测得分 v9"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 30

ws2.merge_cells("A2:H2")
ws2["A2"] = "LCR 20% + CET1 20% + NSFR 16% + IBL 16% + LR 14% + IBA 14% = 100% | 红线 -500 彻底淘汰"
ws2["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[2].height = 22

headers2 = ["指标", "红线", "实测值", "所在档位", "得分", "权重", "加权", "说明"]
for col, h in enumerate(headers2, 1):
    cell = ws2.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[4].height = 30

red_lines = {
    "LCR": "< 120% (本行底线)",
    "NSFR": "< 100% (监管)",
    "CET1": "< 8.7% (7.5+0.5+0.7)",
    "IBL": "> 33.33% (监管, 负债端)",
    "LR": "< 4% (监管)",
    "IBA": "> 30% (同业资产端)",
}
explain = {
    "LCR": "147.29% 在 ≥140% 安全区间",
    "NSFR": "104.52% 在预警区间",
    "CET1": "8.98% 在预警区间 8.9-9.0%",
    "IBL": "24% 在 ≤25% 安全区间 (负债端)",
    "LR": "6.8% 在 ≥6% 安全区间",
    "IBA": "11% 在 ≤12% 安全区间 (资产端)",
}

row_idx = 5
for code, cfg in INDICATORS.items():
    r = all_results[code]
    score_text = str(r["actual_score"]) if r["actual_score"] is not None else "N/A"
    fill = tier_color(r["actual_score"] or 0)
    if "⭐" in r.get("actual_comment", ""):
        fill = PatternFill("solid", fgColor="FFE082")

    ws2.cell(row=row_idx, column=1, value=code)
    ws2.cell(row=row_idx, column=2, value=red_lines[code])
    ws2.cell(row=row_idx, column=3, value=f"{r['current']*100:.2f}%")
    ws2.cell(row=row_idx, column=4, value=tier_label(r["actual_score"] or 0))
    ws2.cell(row=row_idx, column=5, value=score_text)
    ws2.cell(row=row_idx, column=6, value=f"{cfg['weight']*100:.0f}%")
    ws2.cell(row=row_idx, column=7, value=round(r["weighted"], 2) if r["weighted"] is not None else "N/A")
    ws2.cell(row=row_idx, column=8, value=explain[code])

    for c in range(1, 9):
        cell = ws2.cell(row=row_idx, column=c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=(c == 8))
        if c == 5:
            cell.fill = fill
            cell.font = Font(name="微软雅黑", size=11, bold=True)
    row_idx += 1

total_score = sum(r["weighted"] for r in all_results.values() if r["weighted"] is not None)

ws2.cell(row=row_idx, column=1, value="综合得分")
ws2.merge_cells(f"A{row_idx}:F{row_idx}")
ws2.cell(row=row_idx, column=7, value=round(total_score, 2))

for c in range(1, 9):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

rating = get_rating(total_score)

row_idx += 1
ws2.cell(row=row_idx, column=1, value="综合评级")
ws2.merge_cells(f"A{row_idx}:F{row_idx}")
ws2.cell(row=row_idx, column=7, value=rating)

for c in range(1, 9):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="FFE082")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="E65100")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

widths2 = [10, 22, 14, 18, 12, 10, 12, 30]
for i, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A5"

# ===== Sheet 3 =====
ws3 = wb.create_sheet("平滑性约束")
ws3.merge_cells("A1:D1")
ws3["A1"] = "v9 评分规则 + 平滑性约束 + 6 指标说明"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

# 4 档规则
ws3.merge_cells("A3:D3")
ws3["A3"] = "一、4 档评分规则"
ws3["A3"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A3"].fill = PatternFill("solid", fgColor="FFF3E0")
ws3["A3"].alignment = Alignment(horizontal="left", vertical="center")

tier_rules = [
    ("档位", "分值", "含义", "示例"),
    ("红线", "-500", "触发监管 彻底淘汰", "LCR<120% / NSFR<100% / CET1<8.7% / IBL>33.33% / LR<4% / IBA>30%"),
    ("危险-重惩罚", "10-60", "距红线 0-1 档", "LCR 120-130% / CET1 8.7-8.8%"),
    ("预警-轻惩罚", "60-90", "距红线 1-2 档", "LCR 130-140% / CET1 8.8-9.0% / NSFR 103-105%"),
    ("安全", "90-100", "完全合规 满分", "LCR≥140% / CET1≥9.0% / IBL≤25% / LR≥6% / IBA≤12%"),
]
for r, row_data in enumerate(tier_rules, 5):
    for c, val in enumerate(row_data, 1):
        cell = ws3.cell(row=r, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(r == 5))
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if r == 5:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
        elif "红线" in val:
            cell.fill = PatternFill("solid", fgColor="FFCDD2")
        elif "危险" in val:
            cell.fill = PatternFill("solid", fgColor="FFE0B2")
        elif "预警" in val:
            cell.fill = PatternFill("solid", fgColor="FFF9C4")
        elif "安全" in val:
            cell.fill = PatternFill("solid", fgColor="C8E6C9")
        cell.border = border

# 6 指标说明
start_r = 12
ws3.merge_cells(f"A{start_r}:D{start_r}")
ws3.cell(row=start_r, column=1, value="二、6 指标说明")
ws3.cell(row=start_r, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3.cell(row=start_r, column=1).fill = PatternFill("solid", fgColor="FFF3E0")
ws3.cell(row=start_r, column=1).alignment = Alignment(horizontal="left", vertical="center")

ind_desc = [
    ("指标", "权重", "红线", "说明"),
    ("LCR 流动性覆盖率", "20%", "<120% (本行底线)", "短期流动性风险"),
    ("CET1 核心一级资本充足率", "20%", "<8.7% (7.5+0.5+0.7)", "资本充足率"),
    ("NSFR 净稳定资金比例", "16%", "<100%", "长期流动性风险"),
    ("IBL 同业负债占比 (负债端)", "16%", ">33.33%", "同业负债敞口"),
    ("LR 杠杆率", "14%", "<4%", "资本对资产支撑"),
    ("IBA 同业资产占比 (资产端) 🆕", "14%", ">30%", "同业资产敞口"),
]
for r, row_data in enumerate(ind_desc, start_r + 1):
    for c, val in enumerate(row_data, 1):
        cell = ws3.cell(row=r, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(r == start_r + 1))
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if r == start_r + 1:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
        cell.border = border

# 平滑性约束
start_r = start_r + len(ind_desc) + 2
ws3.merge_cells(f"A{start_r}:D{start_r}")
ws3.cell(row=start_r, column=1, value="三、平滑性约束 (避免极端波动方案)")
ws3.cell(row=start_r, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3.cell(row=start_r, column=1).fill = PatternFill("solid", fgColor="FFF3E0")
ws3.cell(row=start_r, column=1).alignment = Alignment(horizontal="left", vertical="center")

header_r = start_r + 2
ws3.cell(row=header_r, column=1, value="变化量")
ws3.cell(row=header_r, column=2, value="扣分系数")
ws3.cell(row=header_r, column=3, value="示例 (偏离 2pp)")
ws3.cell(row=header_r, column=4, value="业务含义")
for c in range(1, 5):
    cell = ws3.cell(row=header_r, column=c)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border

smooth_rows = [
    ("< 1pp", "0", "0 分", "业务可落地"),
    ("1-3pp", "-5/pp", "-10 分", "需注意"),
    ("3-5pp", "-15/pp", "-30 分", "业务论证"),
    ("5-10pp", "-30/pp", "-60 分", "大幅扣分"),
    ("> 10pp", "-60/pp", "-120 分", "极端波动"),
]
for i, (r1, r2, r3, r4) in enumerate(smooth_rows):
    r = header_r + 1 + i
    ws3.cell(row=r, column=1, value=r1)
    ws3.cell(row=r, column=2, value=r2)
    ws3.cell(row=r, column=3, value=r3)
    ws3.cell(row=r, column=4, value=r4)
    for c in range(1, 5):
        cell = ws3.cell(row=r, column=c)
        cell.font = Font(name="微软雅黑", size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        if i == 0:
            cell.fill = PatternFill("solid", fgColor="C8E6C9")
        elif i == 1:
            cell.fill = PatternFill("solid", fgColor="FFF9C4")
        elif i == 2:
            cell.fill = PatternFill("solid", fgColor="FFE0B2")
        else:
            cell.fill = PatternFill("solid", fgColor="FFCDD2")

# 综合评级
start_r = header_r + 8
ws3.merge_cells(f"A{start_r}:D{start_r}")
ws3.cell(row=start_r, column=1, value=f"四、综合评级: {rating} ({round(total_score, 2)} 分)")
ws3.cell(row=start_r, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3.cell(row=start_r, column=1).fill = PatternFill("solid", fgColor="FFF3E0")

widths3 = [18, 18, 22, 32]
for i, w in enumerate(widths3, 1):
    ws3.column_dimensions[get_column_letter(i)].width = w

wb.save(OUTPUT)
print(f"已保存：{OUTPUT}")
print(f"总分段数：{total_segments}（6 指标 4 档）")

print(f"\n=== 中信银行 6 指标 4 档评分结果 (v9) ===")
print(f"{'指标':<8} {'红线':<22} {'实测值':<10} {'档位':<16} {'得分':<6} {'权重':<6} {'加权':<6}")
print("-" * 100)
for code, cfg in INDICATORS.items():
    r = all_results[code]
    tier = tier_label(r["actual_score"] or 0)
    print(f"{code:<8} {red_lines[code]:<22} {r['current']*100:<10.2f} {tier:<16} {r['actual_score']:<6} {cfg['weight']*100:<6.0f} {r['weighted']:<6.2f}")
print("-" * 100)
print(f"综合得分：{round(total_score, 2)}")
print(f"综合评级：{rating}")
