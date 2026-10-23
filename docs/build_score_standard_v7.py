# -*- coding: utf-8 -*-
"""
中信银行 6 指标 深度评分规则 v7 (修订)
=====================================
7 大设计原则 + 控制总段数 ≤ 30/指标
  1. 监管/硬约束不达标 → -500 (彻底淘汰)
  2. 每指标段数 ≤ 30 (实测附近精细, 远处粗)
  3. 最高分 = 可行最优值
  4. 10 亿 ≈ 1bp 精度 (实测前后 10bp 精细)
  5. 靠近实测分值密集
  6. LCR/CET1/NSFR/NIM 适度最优 (单峰)
  7. ROE < 6% 硬约束
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUTPUT = r"C:/银行经营/PRCP/docs/v2/评分标准_v7.xlsx"

# ============================================================
# 6 指标段位定义 (直接手工定义, 每指标 ≤ 30 段)
# ============================================================
# 格式: [(lo, hi, score, comment), ...]
# lo/hi 区间用比例 (0-1), comment 含 ⭐ 标记中信实测位置

SEGMENTS = {
    # ----------------------------------------------------------
    # LCR 流动性覆盖率 (适度最优, 单峰)
    # 监管 ≥100% (-500) / 满分区间 120-140% / 过高减分
    # 实测 147.29% (略超最优, 轻微资金闲置扣分)
    # 30 段
    # ----------------------------------------------------------
    "LCR": [
        (0.00, 1.00, -500, "不达标：<100% 触发监管"),
        (1.00, 1.05,   50, "刚达标：缓冲极薄"),
        (1.05, 1.10,   60, "刚达标"),
        (1.10, 1.15,   70, "达标偏低"),
        (1.15, 1.20,   78, "接近良好"),
        (1.20, 1.25,   85, "良好"),
        (1.25, 1.30,   92, "接近最优"),
        (1.30, 1.35,   97, "接近最优"),
        (1.35, 1.40,  100, "⭐适度最优 满分 120-140%"),
        (1.40, 1.42,  100, "⭐适度最优 满分"),
        (1.42, 1.44,   99, "⭐适度最优 满分"),
        (1.44, 1.46,   98, "⭐略超最优 开始减分"),
        (1.46, 1.473, 97, "⭐中信银行实测 147.29% 段"),
        (1.473, 1.48, 96, "略高：资金开始闲置"),
        (1.48, 1.50,   94, "略高：资金闲置"),
        (1.50, 1.60,   90, "过高：资金闲置"),
        (1.60, 1.80,   85, "过高：收益率受损"),
        (1.80, 2.00,   78, "显著过高"),
        (2.00, 2.50,   72, "极度过剩"),
        (2.50, 5.00,   65, "极度过剩 资产运用效率极低"),
    ],
    # ----------------------------------------------------------
    # NSFR 净稳定资金比例 (适度最优)
    # 监管 ≥100% / 满分区间 105-107% / 过高减分
    # 实测 104.52% (略低于最优, 满分前 1 段)
    # 22 段
    # ----------------------------------------------------------
    "NSFR": [
        (0.00, 1.00, -500, "不达标：<100% 触发监管"),
        (1.00, 1.01,   55, "刚达标：期限错配严重"),
        (1.01, 1.02,   65, "刚达标"),
        (1.02, 1.03,   75, "达标偏低"),
        (1.03, 1.04,   85, "接近良好"),
        (1.04, 1.045,  92, "良好 接近最优"),
        (1.045, 1.05,  96, "⭐中信银行实测 104.52% 段"),
        (1.05, 1.06,  100, "⭐适度最优 满分 105-106%"),
        (1.06, 1.07,  100, "⭐适度最优 满分 106-107%"),
        (1.07, 1.08,   96, "略高 长期资金开始过多"),
        (1.08, 1.10,   92, "略高"),
        (1.10, 1.15,   86, "过高：长期资金占比过高"),
        (1.15, 1.20,   80, "过高"),
        (1.20, 1.30,   75, "显著过高"),
        (1.30, 1.50,   72, "极度过剩 盈利性下降"),
        (1.50, 3.00,   70, "极度过剩"),
    ],
    # ----------------------------------------------------------
    # EVE 银行账户利率风险 (越低越好)
    # 监管 ≤15% / 满分点 6% / 8% 优秀
    # 实测 10.54% (中等偏上)
    # 20 段
    # ----------------------------------------------------------
    "EVE": [
        (0.15, 0.30, -500, "不达标：>15% 触发监管"),
        (0.14, 0.15,   55, "接近监管 即将超标"),
        (0.13, 0.14,   65, "接近上限"),
        (0.12, 0.13,   72, "偏高 久期缺口较大"),
        (0.115, 0.12,  78, "偏高"),
        (0.11, 0.115,  82, "中等偏上"),
        (0.105, 0.11,  86, "⭐中信银行实测 10.54% 段"),
        (0.10, 0.105,  90, "可控"),
        (0.095, 0.10,  92, "良好 久期管理良好"),
        (0.09, 0.095,  94, "良好"),
        (0.08, 0.09,   96, "低风险 缺口管理优秀"),
        (0.07, 0.08,   98, "低风险"),
        (0.06, 0.07,  100, "⭐满分 极低风险"),
        (0.05, 0.06,  100, "⭐满分 极低风险"),
        (0.04, 0.05,  100, "⭐满分"),
        (0.00, 0.04,  100, "⭐满分 几乎无风险"),
    ],
    # ----------------------------------------------------------
    # CET1 核心一级资本充足率 (适度最优)
    # 监管 ≥8% / 满分区间 9.5-10.5% / 过高减分
    # 实测 8.98% (刚过监管, 接近满分区间)
    # 22 段
    # ----------------------------------------------------------
    "CET1": [
        (0.00, 0.08, -500, "不达标：<8% 触发监管"),
        (0.08, 0.085,  70, "刚达监管：缓冲不足 50bp"),
        (0.085, 0.09,  80, "⭐中信银行实测 8.98% 段"),
        (0.09, 0.092,  87, "接近良好"),
        (0.092, 0.095, 92, "良好 接近最优"),
        (0.095, 0.10, 100, "⭐适度最优 满分 9.5-10%"),
        (0.10, 0.105, 100, "⭐适度最优 满分 10-10.5%"),
        (0.105, 0.11,  98, "略高 资本开始冗余"),
        (0.11, 0.115,  95, "略高"),
        (0.115, 0.12,  92, "略高"),
        (0.12, 0.13,   88, "过高 资本冗余"),
        (0.13, 0.15,   82, "过高：ROE 承压"),
        (0.15, 0.20,   75, "显著过高"),
        (0.20, 0.30,   68, "极度过剩 股东回报受损"),
        (0.30, 1.00,   65, "极度过剩"),
    ],
    # ----------------------------------------------------------
    # ROE 净资产收益率 (越高越好, 6% 硬约束)
    # 硬约束 ≥6% (-500) / 满分点 12%+ / 单调递增
    # 实测 9.61% (2026 H1, 中等偏上)
    # 22 段
    # ----------------------------------------------------------
    "ROE": [
        (0.00, 0.06, -500, "硬约束不达标：<6%"),
        (0.06, 0.065,  50, "刚达硬约束"),
        (0.065, 0.07,  58, "接近行业中位"),
        (0.07, 0.075,  65, "接近均值"),
        (0.075, 0.08,  70, "行业中下"),
        (0.08, 0.085,  74, "接近行业中位"),
        (0.085, 0.09,  78, "行业中位"),
        (0.09, 0.092,  82, "行业中上 接近中信"),
        (0.092, 0.095, 86, "接近中信"),
        (0.095, 0.097, 88, "⭐中信银行实测 9.61% 段"),
        (0.097, 0.10,  90, "行业中上"),
        (0.10, 0.105,  92, "优秀 股份制头部"),
        (0.105, 0.11,  94, "优秀"),
        (0.11, 0.115,  96, "卓越 招行级别"),
        (0.115, 0.12,  98, "卓越"),
        (0.12, 0.13,  100, "⭐满分 顶级水平"),
        (0.13, 0.15,  100, "⭐满分"),
        (0.15, 0.20,   99, "异常：可能含一次性收益"),
        (0.20, 1.00,   98, "异常 需核查"),
    ],
    # ----------------------------------------------------------
    # NIM 净息差 (适度最优, 单峰)
    # <1% 极低 (-500) / 满分区间 1.7-1.8% / 过高减分
    # 实测 1.62% (2026 H1, 略低于满分)
    # 22 段
    # ----------------------------------------------------------
    "NIM": [
        (0.000, 0.010, -500, "硬约束不达标：<1% 极低"),
        (0.010, 0.012,  45, "极低 盈利能力严重不足"),
        (0.012, 0.014,  58, "低于行业 息差持续承压"),
        (0.014, 0.015,  68, "行业中下 定价能力弱"),
        (0.015, 0.016,  76, "行业中位 六大行均值"),
        (0.016, 0.0162, 88, "⭐中信银行实测 1.62% 段"),
        (0.0162, 0.017, 92, "行业中上 接近最优"),
        (0.017, 0.0175, 100, "⭐满分 适度最优 1.7-1.75%"),
        (0.0175, 0.018, 100, "⭐满分 适度最优 1.75-1.8%"),
        (0.018, 0.019,  95, "略高 可能含高风险溢价"),
        (0.019, 0.020,  85, "略高"),
        (0.020, 0.022,  72, "过高 资产端风险异常"),
        (0.022, 0.025,  60, "异常 可能监管套利"),
        (0.025, 0.030,  50, "异常"),
        (0.030, 0.050,  45, "极异常 需立即核查"),
    ],
}

# ============================================================
# 指标元数据
# ============================================================
INDICATORS = {
    "LCR": {
        "code": "LCR", "name": "流动性覆盖率", "type": "moderate",
        "reg_label": "≥100% (银保监)", "current": 1.4729, "current_label": "147.29% (2025 年末)",
        "weight": 0.20,
    },
    "NSFR": {
        "code": "NSFR", "name": "净稳定资金比例", "type": "moderate",
        "reg_label": "≥100% (银保监)", "current": 1.0452, "current_label": "104.52% (2025 年末)",
        "weight": 0.15,
    },
    "EVE": {
        "code": "EVE", "name": "银行账户利率风险(EVE)", "type": "upper",
        "reg_label": "≤15% (银保监 IRRBB)", "current": 0.1054, "current_label": "10.54% (2025 年末)",
        "weight": 0.15,
    },
    "CET1": {
        "code": "CET1", "name": "核心一级资本充足率", "type": "moderate",
        "reg_label": "≥8% (用户新规)", "current": 0.0898, "current_label": "8.98% (2025 年末)",
        "weight": 0.20,
    },
    "ROE": {
        "code": "ROE", "name": "净资产收益率(ROAE)", "type": "lower",
        "reg_label": "≥6% (硬约束, 非监管)", "current": 0.0961, "current_label": "9.61% (2026 H1)",
        "weight": 0.15,
    },
    "NIM": {
        "code": "NIM", "name": "净息差", "type": "moderate",
        "reg_label": "<1% 极低 (硬约束)", "current": 0.0162, "current_label": "1.62% (2026 H1)",
        "weight": 0.15,
    },
}


# ============================================================
# 找实测所在段
# ============================================================
def find_segment(segments, value):
    """根据实测值找所在段位 (闭区间 [lo, hi])"""
    for i, (lo, hi, score, comment) in enumerate(segments, 1):
        if lo <= value <= hi:
            return i, lo, hi, score, comment
    return None, None, None, None, None


# ============================================================
# Excel 输出
# ============================================================
wb = openpyxl.Workbook()
wb.remove(wb.active)

thin = Side(border_style="thin", color="DDDDDD")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

# ===== Sheet 1: 评分标准 =====
ws1 = wb.create_sheet("评分标准")
ws1.merge_cells("A1:J1")
ws1["A1"] = "中信银行 6 大指标 深度评分规则 v7（每指标 ≤ 30 段, 监管不达标 -500）"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:J2")
ws1["A2"] = "7 大原则: ① 监管/硬约束不达标 -500 ② 每指标 ≤30 段 ③ 满分=可行最优 ④ 10亿≈1bp 精度 ⑤ 靠近实测密集 ⑥ LCR/CET1/NSFR/NIM 适度最优 ⑦ ROE <6% 硬约束"
ws1["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[2].height = 22

headers = ["指标", "段位", "区间下限", "区间上限", "宽度", "得分", "评语", "距实测", "类型", "监管/硬约束"]
for col, h in enumerate(headers, 1):
    cell = ws1.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws1.row_dimensions[4].height = 30

row_idx = 5
total_segments = 0
all_results = {}

for code, cfg in INDICATORS.items():
    segments = SEGMENTS[code]
    current = cfg["current"]
    total_segments += len(segments)

    # 找实测段
    actual_seg, lo_a, hi_a, actual_score, actual_comment = find_segment(segments, current)
    all_results[code] = {
        "actual_seg": actual_seg,
        "actual_score": actual_score,
        "weight": cfg["weight"],
        "weighted": actual_score * cfg["weight"] if actual_score is not None else None,
        "current": current,
    }

    start_row = row_idx
    for i, (lo, hi, score, comment) in enumerate(segments, 1):
        width = abs(hi - lo)
        # 颜色
        if "⭐" in comment:
            score_fill = PatternFill("solid", fgColor="FFE082")
        elif score <= -100:
            score_fill = PatternFill("solid", fgColor="FFCDD2")
        elif score < 60:
            score_fill = PatternFill("solid", fgColor="FFE0B2")
        elif score < 80:
            score_fill = PatternFill("solid", fgColor="FFF9C4")
        elif score < 95:
            score_fill = PatternFill("solid", fgColor="C8E6C9")
        else:
            score_fill = PatternFill("solid", fgColor="A5D6A7")

        if i == 1:
            ws1.cell(row=row_idx, column=1, value=code)
            ws1.cell(row=row_idx, column=9, value=cfg["type"])
            ws1.cell(row=row_idx, column=10, value=cfg["reg_label"])
        ws1.cell(row=row_idx, column=2, value=i)
        ws1.cell(row=row_idx, column=3, value=f"{lo*100:.4f}%" if width < 0.01 else f"{lo*100:.2f}%")
        ws1.cell(row=row_idx, column=4, value=f"{hi*100:.4f}%" if width < 0.01 else f"{hi*100:.2f}%")
        ws1.cell(row=row_idx, column=5, value=f"{width*100:.2f}pp" if width >= 0.01 else f"{width*100:.4f}pp")
        ws1.cell(row=row_idx, column=6, value=score)
        ws1.cell(row=row_idx, column=7, value=comment)
        dist = abs(((lo + hi) / 2) - current)
        ws1.cell(row=row_idx, column=8, value=f"{dist*100:.2f}pp")

        for c in range(1, 11):
            cell = ws1.cell(row=row_idx, column=c)
            cell.border = border
            cell.font = Font(name="微软雅黑", size=10)
            if c in [2, 3, 4, 5, 6, 8]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="center" if c in [9, 10] else "left", vertical="center", wrap_text=True)
            if c == 6:
                cell.fill = score_fill
                cell.font = Font(name="微软雅黑", size=11, bold=True)
        if i == actual_seg:
            for c in [2, 7]:
                ws1.cell(row=row_idx, column=c).font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
        row_idx += 1

    if row_idx - 1 > start_row:
        ws1.merge_cells(f"A{start_row}:A{row_idx-1}")
        ws1.merge_cells(f"I{start_row}:I{row_idx-1}")
        ws1.merge_cells(f"J{start_row}:J{row_idx-1}")
        for c in [1, 9, 10]:
            cell = ws1.cell(row=start_row, column=c)
            cell.fill = PatternFill("solid", fgColor="F5F5F5")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.font = Font(name="微软雅黑", size=10, bold=True)

widths1 = [8, 6, 14, 14, 12, 10, 42, 10, 12, 24]
for i, w in enumerate(widths1, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.freeze_panes = "A5"

# ===== Sheet 2: 中信银行得分 =====
ws2 = wb.create_sheet("中信银行得分")
ws2.merge_cells("A1:I1")
ws2["A1"] = "中信银行 6 大指标 2025-2026 实测得分"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 30

ws2.merge_cells("A2:I2")
ws2["A2"] = "规则: 监管/硬约束不达标 = -500 (彻底淘汰) | 适度最优指标单峰 (两端减分) | 单调指标越优越高分"
ws2["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[2].height = 22

headers2 = ["指标", "类型", "实测值", "监管/硬约束", "达标", "段位", "总段数", "得分", "加权"]
for col, h in enumerate(headers2, 1):
    cell = ws2.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[4].height = 30

results_sorted = sorted(all_results.items(), key=lambda x: x[1]["actual_score"], reverse=True)

row_idx = 5
for code, cfg in INDICATORS.items():
    r = all_results[code]
    total = len(SEGMENTS[code])

    if r["actual_score"] is None:
        compliant = "—"
        score_text = "N/A"
    elif r["actual_score"] <= -100:
        compliant = "✗ 不达标"
        score_text = str(r["actual_score"])
    else:
        compliant = "✓ 达标"
        score_text = str(r["actual_score"])

    if r["actual_score"] is None:
        score_fill = PatternFill("solid", fgColor="FFCDD2")
    elif r["actual_score"] <= -100:
        score_fill = PatternFill("solid", fgColor="FFCDD2")
    elif r["actual_score"] < 60:
        score_fill = PatternFill("solid", fgColor="FFE0B2")
    elif r["actual_score"] < 80:
        score_fill = PatternFill("solid", fgColor="FFF9C4")
    elif r["actual_score"] < 95:
        score_fill = PatternFill("solid", fgColor="C8E6C9")
    else:
        score_fill = PatternFill("solid", fgColor="A5D6A7")

    type_text = {"moderate": "适度最优", "lower": "越高越好", "upper": "越低越好"}[cfg["type"]]

    ws2.cell(row=row_idx, column=1, value=code)
    ws2.cell(row=row_idx, column=2, value=type_text)
    ws2.cell(row=row_idx, column=3, value=f"{r['current']*100:.2f}%")
    ws2.cell(row=row_idx, column=4, value=cfg["reg_label"])
    ws2.cell(row=row_idx, column=5, value=compliant)
    ws2.cell(row=row_idx, column=6, value=f"第 {r['actual_seg']} 段" if r['actual_seg'] else "N/A")
    ws2.cell(row=row_idx, column=7, value=total)
    ws2.cell(row=row_idx, column=8, value=score_text)
    ws2.cell(row=row_idx, column=9, value=round(r["weighted"], 2) if r["weighted"] is not None else "N/A")

    for c in range(1, 10):
        cell = ws2.cell(row=row_idx, column=c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        if c == 8:
            cell.fill = score_fill
            cell.font = Font(name="微软雅黑", size=11, bold=True)
        if c == 5:
            if compliant.startswith("✓"):
                cell.fill = PatternFill("solid", fgColor="C8E6C9")
                cell.font = Font(name="微软雅黑", size=10, bold=True, color="1B5E20")
            elif compliant.startswith("✗"):
                cell.fill = PatternFill("solid", fgColor="FFCDD2")
                cell.font = Font(name="微软雅黑", size=10, bold=True, color="B71C1C")
    row_idx += 1

# 综合得分
total_score = sum(r["weighted"] for r in all_results.values() if r["weighted"] is not None)

ws2.cell(row=row_idx, column=1, value="综合得分")
ws2.merge_cells(f"A{row_idx}:G{row_idx}")
ws2.cell(row=row_idx, column=8, value=round(total_score, 2))
ws2.cell(row=row_idx, column=9, value=round(total_score, 2))

for c in range(1, 10):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

row_idx += 1
if total_score >= 90:
    rating = "A+ 卓越"
elif total_score >= 85:
    rating = "A  优秀"
elif total_score >= 80:
    rating = "B+ 良好"
elif total_score >= 70:
    rating = "B  中等"
elif total_score >= 60:
    rating = "C  及格"
else:
    rating = "D  警示"

ws2.cell(row=row_idx, column=1, value="综合评级")
ws2.merge_cells(f"A{row_idx}:G{row_idx}")
ws2.cell(row=row_idx, column=8, value=rating)
ws2.cell(row=row_idx, column=9, value=round(total_score, 1))

for c in range(1, 10):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="FFE082")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="E65100")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

widths2 = [10, 12, 14, 18, 12, 12, 12, 12, 12]
for i, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A5"

# ===== Sheet 3: 评分规则说明 =====
ws3 = wb.create_sheet("评分规则")
ws3.merge_cells("A1:C1")
ws3["A1"] = "v7 评分规则与方法论 (7 大设计原则)"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

rules = [
    ("1. 监管/硬约束不达标 → -500 (彻底淘汰)", "全部 6 指标", "LCR/NSFR/EVE/CET1 不达标 -500；ROE < 6% 硬约束 -500；NIM < 1% 硬约束 -500"),
    ("", "", ""),
    ("2. 每指标段数 ≤ 30", "本次设计", f"实际总段数 {total_segments}, 每指标 15-20 段"),
    ("", "", ""),
    ("3. 最高分 = 可行最优值", "满分 100 分取值", "LCR 120-140% / NSFR 105-107% / EVE ≤6% / CET1 9.5-10.5% / ROE ≥12% / NIM 1.7-1.8%"),
    ("", "", ""),
    ("4. 10 亿变动 → 1bp 精度", "中信总资产 10.38 万亿", "1bp ≈ 10.4 亿；实测附近段位 1bp-5bp 宽度"),
    ("", "", ""),
    ("5. 靠近实测分值密集", "实测前后 ≤ 5bp 段位", "实测所在段位宽度 0.5-1pp (1bp-5bp)，比 1pp 段位更细"),
    ("", "", ""),
    ("6. LCR/CET1/NSFR/NIM 适度最优 (单峰)", "4 个指标", "低于监管 -500 + 满分区间 100 + 过高适度减分 + 极度过剩低分"),
    ("6.1 LCR", "120-140% 满分", ">150% 资金闲置减分；>200% 严重低效"),
    ("6.2 NSFR", "105-107% 满分", ">115% 过度稳定减分"),
    ("6.3 CET1", "9.5-10.5% 满分", ">13% 资本冗余 ROE 承压减分"),
    ("6.4 NIM", "1.7-1.8% 满分", ">2% 可能含高风险溢价减分"),
    ("6.5 EVE (越低越好)", "≤6% 满分", "无过高减分 (越低越好)"),
    ("", "", ""),
    ("7. ROE < 6% 硬约束", "非监管但硬底线", "< 6% 直接 -500 (即使不属于监管硬性指标)"),
    ("", "", ""),
    ("权重分配", "LCR 20% + CET1 20% + NSFR 15% + EVE 15% + ROE 15% + NIM 15%", "监管资本+流动性 70% / 业绩指标 30%"),
    ("", "", ""),
    ("评级标准", "A+(≥90) / A(85-90) / B+(80-85) / B(70-80) / C(60-70) / D(<60)", f"本次综合 {round(total_score, 2)} → {rating}"),
    ("", "", ""),
    ("中信银行 6 指标实测", "数据来源", "LCR/NSFR/EVE/CET1 取 2025 年末；ROE/NIM 取 2026 H1"),
]

for i, (a, b, c) in enumerate(rules, 2):
    if a:
        ws3.cell(row=i, column=1, value=a).font = Font(name="微软雅黑", size=11, bold=True, color="C7000B")
    if b:
        ws3.cell(row=i, column=2, value=b).font = Font(name="微软雅黑", size=10)
    if c:
        ws3.cell(row=i, column=3, value=c).font = Font(name="微软雅黑", size=10)
    for cc in [1, 2, 3]:
        cell = ws3.cell(row=i, column=cc)
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

ws3.column_dimensions["A"].width = 36
ws3.column_dimensions["B"].width = 22
ws3.column_dimensions["C"].width = 56

wb.save(OUTPUT)
print(f"已保存：{OUTPUT}")
print(f"总分段数：{total_segments}（每指标 15-20 段）")

print(f"\n=== 中信银行 6 大指标 评分结果 (v7) ===")
print(f"{'指标':<8} {'类型':<10} {'实测值':<10} {'达标':<8} {'段位':<10} {'得分':<8} {'加权':<6} 评语")
print("-" * 110)
for code, cfg in INDICATORS.items():
    r = all_results[code]
    seg_comment = SEGMENTS[code][r["actual_seg"]-1][3] if r['actual_seg'] else "N/A"
    compliant = "✓" if r["actual_score"] and r["actual_score"] > -100 else "✗"
    type_text = {"moderate": "适度最优", "lower": "越高越好", "upper": "越低越好"}[cfg["type"]]
    print(f"{code:<8} {type_text:<10} {r['current']*100:<10.2f} {compliant:<8} 第 {r['actual_seg']} 段  {r['actual_score']:<8} {r['weighted']:<6.2f}  {seg_comment[:30]}")
print("-" * 110)
print(f"综合得分：{round(total_score, 2)}")
print(f"综合评级：{rating}")
