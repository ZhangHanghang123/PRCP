# -*- coding: utf-8 -*-
"""
中信银行 5 指标 4 档评分规则 v8
=================================
按图 1（指标红线）+ 图 2（4 档评分制）设计:
  - 红线 / 危险-重惩罚 / 预警-轻惩罚 / 安全 (4 档)
  - 调整 LCR 红线 100% → 120% (本行底线)
  - 调整 CET1 红线 8% → 8.7% (7.5+0.5+0.7)
  - 新增 同业负债占比 / 杠杆率
  - 平滑性约束: 避免极端波动方案
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUTPUT = r"C:/银行经营/PRCP/docs/v2/评分标准_v8.xlsx"

# ============================================================
# 5 指标 4 档配置
# ============================================================
# direction: 'higher' 越高越好, 'lower' 越低越好
# 4 档: red (红线) / danger (危险-重惩罚) / warn (预警-轻惩罚) / safe (安全)
# 区间: (lo, hi) - 含 lo 不含 hi (除最后一段)
INDICATORS = {
    # ----------------------------------------------------------
    # LCR 流动性覆盖率
    # 红线 < 120% (-500) | 危险 120-130% (10-60) | 预警 130-140% (60-90) | 安全 ≥140% (100)
    # ----------------------------------------------------------
    "LCR": {
        "code": "LCR", "name": "流动性覆盖率", "direction": "higher",
        "current": 1.4729, "weight": 0.24,
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
    # ----------------------------------------------------------
    # NSFR 净稳定资金比例
    # 红线 < 100% | 危险 100-103% | 预警 103-105% | 安全 ≥105%
    # ----------------------------------------------------------
    "NSFR": {
        "code": "NSFR", "name": "净稳定资金比例", "direction": "higher",
        "current": 1.0452, "weight": 0.18,
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
    # ----------------------------------------------------------
    # CET1 核心一级资本充足率 (红线 8.7%)
    # 红线 < 8.7% | 危险 8.7-8.8% | 预警 8.8-9.0% | 安全 ≥9.0%
    # ----------------------------------------------------------
    "CET1": {
        "code": "CET1", "name": "核心一级资本充足率", "direction": "higher",
        "current": 0.0898, "weight": 0.24,
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
    # ----------------------------------------------------------
    # IBL 同业负债占比 (新指标)
    # 红线 > 33.33% | 危险 30-33.33% | 预警 25-30% | 安全 ≤25%
    # ----------------------------------------------------------
    "IBL": {
        "code": "IBL", "name": "同业负债占总负债比例", "direction": "lower",
        "current": 0.24, "weight": 0.18,
        "safe1":  (0.000, 0.20, 100, "⭐安全 ≤20%"),
        "safe2":  (0.20, 0.25,  95, "⭐中信银行实测 24% 段 安全"),
        "wrn1":   (0.25, 0.27,  80, "预警-轻惩罚 25-27%"),
        "wrn2":   (0.27, 0.30,  70, "预警-轻惩罚 27-30%"),
        "dgr1":   (0.30, 0.31,  45, "危险-重惩罚 30-31%"),
        "dgr2":   (0.31, 0.3333, 25, "危险-重惩罚 31-33.33%"),
        "red":    (0.3333, 0.40, -500, "红线 >33.33% 触发监管"),
        "red2":   (0.40, 1.00, -500, "红线 远超标"),
    },
    # ----------------------------------------------------------
    # LR 杠杆率 (新指标)
    # 红线 < 4% | 危险 4-5% | 预警 5-6% | 安全 ≥6%
    # ----------------------------------------------------------
    "LR": {
        "code": "LR", "name": "杠杆率", "direction": "higher",
        "current": 0.068, "weight": 0.16,
        "red":    (0.000, 0.04, -500, "红线 <4% 触发监管"),
        "dgr1":   (0.04, 0.045, 20, "危险-重惩罚 4-4.5%"),
        "dgr2":   (0.045, 0.05, 40, "危险-重惩罚 4.5-5%"),
        "wrn1":   (0.05, 0.055, 65, "预警-轻惩罚 5-5.5%"),
        "wrn2":   (0.055, 0.06, 80, "预警-轻惩罚 5.5-6%"),
        "safe1":  (0.06, 0.07, 100, "⭐安全 6-7% 适度最优"),
        "safe2":  (0.07, 0.08, 100, "⭐安全 7-8%"),
        "safe3":  (0.08, 1.00, 100, "⭐安全 8%+ 极优"),
    },
}

# 平滑性约束参数 (避免极端波动方案)
SMOOTH_PENALTY = {
    # 变化量 (pp) -> 扣分系数
    # 变化 < 1pp 不扣分, 1-3pp 扣 5-30 分, 3-5pp 扣 30-100 分, >5pp 大幅扣分
    (0, 0.01):    0,    # < 1pp: 0 扣分
    (0.01, 0.03): 5,    # 1-3pp: -5 × 偏离度/pp
    (0.03, 0.05): 15,   # 3-5pp: -15 × 偏离度/pp
    (0.05, 0.10): 30,   # 5-10pp: -30 × 偏离度/pp
    (0.10, 0.50): 60,   # >10pp: -60 × 偏离度/pp
}


# ============================================================
# 平滑性扣分
# ============================================================
def smooth_penalty(deviation):
    """根据变化量返回扣分"""
    for (lo, hi), factor in SMOOTH_PENALTY.items():
        if lo <= deviation < hi:
            return round(factor * (deviation * 100), 2)
    return 0


# ============================================================
# 找实测所在段
# ============================================================
def find_segment(segments_dict, value):
    """根据实测值找所在段位 (闭区间 [lo, hi])"""
    for key, val in segments_dict.items():
        if isinstance(val, tuple) and len(val) == 4:
            lo, hi, score, comment = val
            if lo <= value <= hi:
                return key, lo, hi, score, comment
    # 默认最后一段
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

# 评级
def get_rating(score):
    if score >= 90: return "A+ 卓越"
    elif score >= 85: return "A  优秀"
    elif score >= 80: return "B+ 良好"
    elif score >= 70: return "B  中等"
    elif score >= 60: return "C  及格"
    else: return "D  警示"

# 档位颜色
def tier_color(score):
    if score <= -100: return PatternFill("solid", fgColor="FFCDD2")
    elif score < 60: return PatternFill("solid", fgColor="FFE0B2")
    elif score < 90: return PatternFill("solid", fgColor="FFF9C4")
    else: return PatternFill("solid", fgColor="A5D6A7")

# 档位
def tier_label(score):
    if score <= -100: return "红线"
    elif score < 60: return "危险-重惩罚"
    elif score < 90: return "预警-轻惩罚"
    else: return "安全"

# ===== Sheet 1: 4 档评分标准 =====
ws1 = wb.create_sheet("4档评分标准")
ws1.merge_cells("A1:K1")
ws1["A1"] = "中信银行 5 指标 4 档评分规则 v8（红线-500 / 危险-重惩罚 / 预警-轻惩罚 / 安全）"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:K2")
ws1["A2"] = "参考图 1 指标红线 + 图 2 4 档评分制 | LCR 120% 红线 | CET1 8.7% 红线 | 新增 同业负债占比/杠杆率"
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
    segs = cfg  # 内含 red/dgr/wrn/safe 4 档
    current = cfg["current"]
    direction = cfg["direction"]

    # 找实测段
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
    for i, (key, val) in enumerate(segs.items(), 1):
        if not (isinstance(val, tuple) and len(val) == 4):
            continue
        lo, hi, score, comment = val
        width = abs(hi - lo)
        tier = tier_label(score)
        fill = tier_color(score)
        if "⭐" in comment:
            fill = PatternFill("solid", fgColor="FFE082")

        # 档位文字
        if score <= -100:
            tier_text = "红线"
        elif score < 60:
            tier_text = "危险-重惩罚"
        elif score < 90:
            tier_text = "预警-轻惩罚"
        else:
            tier_text = "安全"

        if i == 1:
            ws1.cell(row=row_idx, column=1, value=code)
            ws1.cell(row=row_idx, column=10, value="越高越好" if direction == "higher" else "越低越好")
            ws1.cell(row=row_idx, column=11, value=comment.split('：')[0] if '：' in comment else comment[:20])

        ws1.cell(row=row_idx, column=2, value=tier_text)
        ws1.cell(row=row_idx, column=3, value=i)
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
        if i == actual_key or (isinstance(actual_key, str) and i == list(segs.keys()).index(actual_key) + 1):
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

# ===== Sheet 2: 中信银行 4 档得分 =====
ws2 = wb.create_sheet("中信银行得分")
ws2.merge_cells("A1:H1")
ws2["A1"] = "中信银行 5 指标 4 档实测得分 v8"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[2].height = 30

ws2.merge_cells("A2:H2")
ws2["A2"] = "LCR 24% + CET1 24% + NSFR 18% + IBL 18% + LR 16% = 100% | 红线 -500 彻底淘汰"
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

row_idx = 5
red_lines = {
    "LCR": "< 120% (本行底线)",
    "NSFR": "< 100% (监管)",
    "CET1": "< 8.7% (7.5+0.5+0.7)",
    "IBL": "> 33.33% (监管)",
    "LR": "< 4% (监管)",
}
explain = {
    "LCR": "147.29% 在 ≥140% 安全区间",
    "NSFR": "104.52% 在预警区间",
    "CET1": "8.98% 在预警区间 8.8-9%",
    "IBL": "24% 在 ≤25% 安全区间",
    "LR": "6.8% 在 ≥6% 安全区间",
}

for code, cfg in INDICATORS.items():
    r = all_results[code]
    if r["actual_score"] is None:
        score_text = "N/A"
    else:
        score_text = str(r["actual_score"])
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

# ===== Sheet 3: 平滑性约束 + 评分规则 =====
ws3 = wb.create_sheet("平滑性约束")
ws3.merge_cells("A1:D1")
ws3["A1"] = "v8 评分规则 + 平滑性约束说明"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

# 4 档评分规则
ws3.merge_cells("A3:D3")
ws3["A3"] = "一、4 档评分规则 (参考图 2)"
ws3["A3"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A3"].fill = PatternFill("solid", fgColor="FFF3E0")
ws3["A3"].alignment = Alignment(horizontal="left", vertical="center")

tier_rules = [
    ("档位", "分值", "含义", "示例"),
    ("红线", "-500", "触发监管 彻底淘汰", "LCR<120% / NSFR<100% / CET1<8.7% / IBL>33.33% / LR<4%"),
    ("危险-重惩罚", "10-60", "距红线 0-1 档 大额扣分", "LCR 120-130% / CET1 8.7-8.8% / NSFR 100-103%"),
    ("预警-轻惩罚", "60-90", "距红线 1-2 档 轻扣分", "LCR 130-140% / CET1 8.8-9.0% / NSFR 103-105%"),
    ("安全", "90-100", "完全合规 满分", "LCR≥140% / CET1≥9.0% / NSFR≥105% / IBL≤25% / LR≥6%"),
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

# 平滑性约束
start_r = 12
ws3.merge_cells(f"A{start_r}:D{start_r}")
ws3.cell(row=start_r, column=1, value="二、平滑性约束 (避免极端波动方案)")
ws3.cell(row=start_r, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3.cell(row=start_r, column=1).fill = PatternFill("solid", fgColor="FFF3E0")
ws3.cell(row=start_r, column=1).alignment = Alignment(horizontal="left", vertical="center")

# 解释
ws3.merge_cells(f"A{start_r+1}:D{start_r+1}")
ws3.cell(row=start_r+1, column=1, value="避免出现数学最优但业务无法落地的\"极端波动方案\"，如果相比上一期变动过大，则按照一定比例扣分（该扣分比例较大，以便后续迭代过程中除非四...").font = Font(name="微软雅黑", size=10, italic=True, color="666666")

# 平滑性扣分表
header_r = start_r + 3
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
    ("< 1pp", "0", "0 分", "业务可落地，无需扣分"),
    ("1-3pp", "-5/pp", "-10 分", "需注意，可能可行"),
    ("3-5pp", "-15/pp", "-30 分", "变化较大，需业务论证"),
    ("5-10pp", "-30/pp", "-60 分", "大幅扣分，业务风险高"),
    ("> 10pp", "-60/pp", "-120 分", "极端波动，业务基本不可行"),
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

# 评级标准
start_r = header_r + 8
ws3.merge_cells(f"A{start_r}:D{start_r}")
ws3.cell(row=start_r, column=1, value=f"三、综合评级: {rating} ({round(total_score, 2)} 分)")
ws3.cell(row=start_r, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3.cell(row=start_r, column=1).fill = PatternFill("solid", fgColor="FFF3E0")

rating_rows = [
    ("评级", "分值区间", "示例 (LCR=147, NSFR=104, CET1=8.98, IBL=24, LR=6.8)", ""),
    ("A+ 卓越", "≥ 90", "全部在安全/预警区间", ""),
    ("A  优秀", "85-90", "多数在安全/预警", ""),
    ("B+ 良好", "80-85", "部分在预警/危险", ""),
    ("B  中等", "70-80", "部分指标在危险", ""),
    ("C  及格", "60-70", "至少 1 项接近红线", ""),
    ("D  警示", "< 60", "触发红线 -500 淘汰", ""),
]
for i, row_data in enumerate(rating_rows, start_r + 1):
    for c, val in enumerate(row_data[:3], 1):
        cell = ws3.cell(row=i, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(i == start_r + 1))
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        if i == start_r + 1:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")

widths3 = [16, 14, 22, 32]
for i, w in enumerate(widths3, 1):
    ws3.column_dimensions[get_column_letter(i)].width = w

wb.save(OUTPUT)
print(f"已保存：{OUTPUT}")
print(f"总分段数：{total_segments}（5 指标 4 档）")

print(f"\n=== 中信银行 5 指标 4 档评分结果 (v8) ===")
print(f"{'指标':<8} {'红线':<18} {'实测值':<10} {'档位':<16} {'得分':<8} {'权重':<6} {'加权':<6}")
print("-" * 100)
for code, cfg in INDICATORS.items():
    r = all_results[code]
    tier = tier_label(r["actual_score"] or 0)
    print(f"{code:<8} {red_lines[code]:<18} {r['current']*100:<10.2f} {tier:<16} {r['actual_score']:<8} {cfg['weight']*100:<6.0f} {r['weighted']:<6.2f}")
print("-" * 100)
print(f"综合得分：{round(total_score, 2)}")
print(f"综合评级：{rating}")
