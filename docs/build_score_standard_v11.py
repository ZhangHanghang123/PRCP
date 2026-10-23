"""中信银行 7 指标 4 档评分规则 v11
指标: LCR / NSFR / EVE / CET1 / ROE / IBL (同业负债比) / LR (杠杆率)
设计: 4 档制 (红线 -500 / 危险-重惩罚 / 预警-轻惩罚 / 安全)
实测值: 中信银行 2025 年末数据 (ROE 用 2026 H1 数据, LR = 7.06%)
权重: LCR 18% + NSFR 14% + EVE 13% + CET1 18% + ROE 13% + IBL 12% + LR 12% = 100%
"""

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ===================== 1. 指标配置 =====================
INDICATORS = {
    "LCR": {
        "code": "LCR", "name": "流动性覆盖率", "direction": "higher",
        "current": 1.4729, "weight": 0.18,
        "regulation": "< 120% (本行底线, 监管 100%)",
        "red":   (0.000, 1.00,  -500, "严重不达标：<100% 触发监管"),
        "red2":  (1.00,  1.10,  -300, "<110% 远低于本行底线"),
        "red3":  (1.10,  1.15,  -150, "接近本行底线"),
        "red4":  (1.15,  1.20,   -50, "贴近红线 115-120%"),
        "dgr1":  (1.20,  1.25,    10, "危险-重惩罚 120-125%"),
        "dgr2":  (1.25,  1.30,    40, "危险-重惩罚 125-130%"),
        "wrn1":  (1.30,  1.35,    70, "预警-轻惩罚 130-135%"),
        "wrn2":  (1.35,  1.40,    85, "预警-轻惩罚 135-140%"),
        "safe1": (1.40,  1.50,   100, "安全 140-150% 适度最优"),
        "safe2": (1.50,  1.80,    95, "安全 150-180% 略高"),
        "safe3": (1.80,  2.50,    82, "安全 180-250% 过高"),
        "safe4": (2.50,  9.99,    65, "安全 250%+ 极度过剩"),
    },
    "NSFR": {
        "code": "NSFR", "name": "净稳定资金比例", "direction": "higher",
        "current": 1.0452, "weight": 0.14,
        "regulation": "< 100% (监管)",
        "red":   (0.000, 1.00,  -500, "严重不达标：<100% 触发监管"),
        "red2":  (1.00,  1.02,  -200, "远低于监管 100-102%"),
        "dgr1":  (1.02,  1.03,    35, "危险-重惩罚 102-103%"),
        "wrn1":  (1.03,  1.04,    65, "预警-轻惩罚 103-104%"),
        "wrn2":  (1.04,  1.045,   80, "预警-轻惩罚 104-104.5%"),
        "wrn3":  (1.045, 1.05,    85, "⭐中信银行实测 104.52% 段 104.5-105%"),
        "safe1": (1.05,  1.07,   100, "安全 105-107% 适度最优"),
        "safe2": (1.07,  1.10,    95, "安全 107-110% 略高"),
        "safe3": (1.10,  1.15,    85, "安全 110-115% 偏高"),
        "safe4": (1.15,  9.99,    75, "安全 115%+ 过度稳定"),
    },
    "EVE": {
        "code": "EVE", "name": "银行账户利率风险", "direction": "lower",
        "current": 0.1054, "weight": 0.13,
        "regulation": "> 15% (监管)",
        "red":   (0.15,  9.99,  -500, "严重超标：>15% 触发监管上限"),
        "dgr1":  (0.12,  0.15,    20, "危险-重惩罚 12-15%"),
        "wrn1":  (0.10,  0.12,    55, "预警-轻惩罚 10-12%"),
        "wrn2":  (0.105, 0.11,    70, "⭐中信银行实测 10.54% 段 10.5-11%"),
        "wrn3":  (0.10,  0.105,   80, "预警-轻惩罚 10-10.5%"),
        "wrn4":  (0.09,  0.10,    88, "预警-轻惩罚 9-10%"),
        "safe1": (0.08,  0.09,    92, "安全 8-9%"),
        "safe2": (0.06,  0.08,    96, "安全 6-8% 适度最优"),
        "safe3": (0.03,  0.06,    98, "安全 3-6% 极低"),
        "safe4": (0.00,  0.03,    95, "安全 <3% 错失上行收益"),
    },
    "CET1": {
        "code": "CET1", "name": "核心一级资本充足率", "direction": "higher",
        "current": 0.0898, "weight": 0.18,
        "regulation": "< 8.7% (7.5 监管 + 0.5 附加 + 0.7 本行)",
        "red":    (0.000, 0.087,  -500, "严重不达标：<8.7% 触发监管"),
        "red2":   (0.087, 0.0875,  -50, "刚过红线 8.7-8.75%"),
        "dgr1":   (0.0875,0.088,    35, "危险-重惩罚 8.75-8.8%"),
        "wrn1":   (0.088, 0.089,    75, "预警-轻惩罚 8.8-8.9%"),
        "wrn2":   (0.089, 0.09,     88, "⭐中信银行实测 8.98% 段 8.9-9.0%"),
        "safe1":  (0.09,  0.095,   100, "安全 9.0-9.5% 适度最优"),
        "safe2":  (0.095, 0.10,    100, "安全 9.5-10% 适度最优"),
        "safe3":  (0.10,  0.11,     98, "安全 10-11% 略高"),
        "safe4":  (0.11,  0.13,     90, "安全 11-13% 过高"),
        "safe5":  (0.13,  0.15,     82, "安全 13-15% 显著过高"),
        "safe6":  (0.15,  1.00,     75, "安全 15%+ 极度过剩"),
    },
    "ROE": {
        "code": "ROE", "name": "净资产收益率", "direction": "higher",
        "current": 0.0961, "weight": 0.13,  # 2026 H1 = 9.61%
        "regulation": "< 6% (硬约束, 非监管但不可接受)",
        "red":    (0.00, 0.06,    -500, "硬约束不达标：<6% 不可接受"),
        "dgr1":   (0.06, 0.07,      40, "较低 6-7%"),
        "wrn1":   (0.07, 0.08,      60, "行业中下 7-8%"),
        "wrn2":   (0.08, 0.09,      75, "行业中位 8-9%"),
        "wrn3":   (0.09, 0.095,     82, "行业中上 9-9.5%"),
        "wrn4":   (0.095, 0.0961,   85, "⭐中信银行实测 9.61% 段 9.5-9.61%"),
        "wrn5":   (0.0961, 0.10,    88, "行业中上 9.61-10%"),
        "safe1":  (0.10, 0.11,      92, "优秀 10-11%"),
        "safe2":  (0.11, 0.12,      96, "卓越 11-12%"),
        "safe3":  (0.12, 0.15,     100, "满分 ≥12%"),
        "safe4":  (0.15, 9.99,      98, "异常高 需核查"),
    },
    "IBL": {
        "code": "IBL", "name": "同业负债占总负债比例", "direction": "lower",
        "current": 0.2160, "weight": 0.12,  # 实测 21.60% (同业负债 19,777 亿 / 总负债 91,578 亿)
        "regulation": "> 33.33% (监管, 负债端)",
        "red":    (0.3333, 1.00,  -500, "严重超标：>33.33% 触发监管"),
        "red2":   (0.30,  0.3333, -50,  "接近红线 30-33.33%"),
        "dgr1":   (0.27,  0.30,    35, "危险-重惩罚 27-30%"),
        "wrn1":   (0.25,  0.27,    65, "预警-轻惩罚 25-27%"),
        "wrn2":   (0.216, 0.25,    85, "⭐中信银行实测 21.60% 段 21.6-25%"),
        "safe1":  (0.20,  0.216,   95, "安全 20-21.6%"),
        "safe2":  (0.15,  0.20,    95, "安全 15-20%"),
        "safe3":  (0.10,  0.15,    88, "安全 10-15% 偏低"),
        "safe4":  (0.05,  0.10,    80, "安全 5-10% 过低"),
        "safe5":  (0.00,  0.05,    70, "安全 <5% 异常低"),
    },
    "LR": {
        "code": "LR", "name": "杠杆率", "direction": "higher",
        "current": 0.0706, "weight": 0.12,  # 实测 7.06% (一级资本 7,682 亿 / 表内外资产 108,748 亿)
        "regulation": "< 4% (银保监, 巴塞尔 III ≥ 3%)",
        "red":    (0.00,  0.04,   -500, "严重不达标：<4% 触发监管"),
        "red2":   (0.035, 0.04,   -100, "接近红线 3.5-4%"),
        "dgr1":   (0.04,  0.045,    30, "危险-重惩罚 4-4.5%"),
        "wrn1":   (0.045, 0.05,     60, "预警-轻惩罚 4.5-5%"),
        "wrn2":   (0.05,  0.06,     80, "预警-轻惩罚 5-6%"),
        "wrn3":   (0.06,  0.065,    90, "⭐中信银行实测 7.06% 段 6-6.5%"),
        "wrn4":   (0.065, 0.0706,   92, "安全 6.5-7.06%"),
        "safe1":  (0.0706, 0.08,    95, "安全 7.06-8% 适度最优"),
        "safe2":  (0.08,  0.10,     88, "安全 8-10% 偏高"),
        "safe3":  (0.10,  0.12,      80, "安全 10-12% 过高"),
        "safe4":  (0.12,  1.00,      72, "安全 12%+ 极度过剩"),
    },
}

# ===================== 2. 4 档评分辅助函数 =====================
def tier_label(score):
    if score <= -100:
        return "红线"
    elif score < 60:
        return "危险-重惩罚"
    elif score < 90:
        return "预警-轻惩罚"
    else:
        return "安全"

def tier_color(score):
    if score <= -100:
        return PatternFill("solid", fgColor="FFCDD2")  # 红
    elif score < 60:
        return PatternFill("solid", fgColor="FFE0B2")  # 橙
    elif score < 90:
        return PatternFill("solid", fgColor="FFF9C4")  # 黄
    else:
        return PatternFill("solid", fgColor="C8E6C9")  # 绿

def find_segment(segments_dict, value):
    """根据实测值找所在段位 (闭区间 [lo, hi])"""
    last_seg = None
    for key, val in segments_dict.items():
        if not (isinstance(val, tuple) and len(val) == 4):
            continue
        lo, hi, score, comment = val
        last_seg = (key, lo, hi, score, comment)
        if lo <= value <= hi:
            return key, lo, hi, score, comment
    if last_seg:
        return last_seg
    return None, None, None, None, None

def get_rating(score):
    if score >= 90: return "A+ 卓越"
    if score >= 85: return "A 优秀"
    if score >= 80: return "B+ 良好"
    if score >= 70: return "B 中等"
    if score >= 60: return "C 较弱"
    return "D 差"

# ===================== 3. 创建 Excel =====================
OUTPUT = r"C:/银行经营/PRCP/docs/v2/评分标准_v11.xlsx"
wb = Workbook()
wb.remove(wb.active)

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===== Sheet 1: 4 档评分标准 =====
ws1 = wb.create_sheet("4档评分标准")
ws1.merge_cells("A1:K1")
ws1["A1"] = "中信银行 7 指标 4 档评分规则 v11 (LCR / NSFR / EVE / CET1 / ROE / IBL / LR)"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:K2")
ws1["A2"] = "LCR 18% + NSFR 14% + EVE 13% + CET1 18% + ROE 13% + IBL 12% + LR 12% = 100% | 红线 -500 彻底淘汰 | 实测: 中信银行 2025 年末 (ROE 用 2026 H1, LR=7.06%)"
ws1["A2"].font = Font(name="微软雅黑", size=10, bold=False, color="555555")
ws1["A2"].fill = PatternFill("solid", fgColor="FFF3E0")
ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[2].height = 22

# 表头
headers = ["指标", "档位", "子段", "区间下限", "区间上限", "宽度", "得分", "评语", "距实测", "方向", "红线说明"]
for col, h in enumerate(headers, 1):
    cell = ws1.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws1.row_dimensions[4].height = 30

row_idx = 5
all_results = {}
total_segments = 0

for code, cfg in INDICATORS.items():
    segs = cfg  # cfg 已经包含段位元组
    current = cfg["current"]
    direction = cfg["direction"]
    regulation = cfg["regulation"]

    # 找实测段位
    actual_key, a_lo, a_hi, actual_score, actual_comment = find_segment(segs, current)

    all_results[code] = {
        "code": code,
        "name": cfg["name"],
        "current": current,
        "current_text": f"{current*100:.2f}%" if current >= 0.01 else f"{current*100:.4f}%",
        "regulation": regulation,
        "direction": direction,
        "actual_key": actual_key,
        "actual_score": actual_score,
        "weight": cfg["weight"],
        "weighted": actual_score * cfg["weight"] if actual_score is not None else None,
    }
    total_segments += sum(1 for v in segs.values() if isinstance(v, tuple) and len(v) == 4)

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

        if seg_count == 1:
            ws1.cell(row=row_idx, column=1, value=code)
            ws1.cell(row=row_idx, column=10, value="越高越好" if direction == "higher" else "越低越好")
            ws1.cell(row=row_idx, column=11, value=regulation)

        ws1.cell(row=row_idx, column=2, value=tier)
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

widths1 = [8, 16, 6, 12, 12, 10, 10, 40, 10, 12, 30]
for i, w in enumerate(widths1, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.freeze_panes = "A5"

# ===== Sheet 2: 中信银行得分 =====
ws2 = wb.create_sheet("中信银行得分")
ws2.merge_cells("A1:H1")
ws2["A1"] = "中信银行 7 指标 4 档实测得分 v11"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 30

ws2.merge_cells("A2:H2")
ws2["A2"] = "LCR 18% + NSFR 14% + EVE 13% + CET1 18% + ROE 13% + IBL 12% + LR 12% = 100% | 红线 -500 彻底淘汰"
ws2["A2"].font = Font(name="微软雅黑", size=10, bold=False, color="555555")
ws2["A2"].fill = PatternFill("solid", fgColor="FFF3E0")
ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[2].height = 22

headers2 = ["指标", "红线", "实测值", "所在档位", "得分", "权重", "加权", "说明"]
for col, h in enumerate(headers2, 1):
    cell = ws2.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[4].height = 30

row_idx = 5
for code in INDICATORS.keys():
    r = all_results[code]
    tier = tier_label(r["actual_score"])
    fill = tier_color(r["actual_score"])

    ws2.cell(row=row_idx, column=1, value=r["code"])
    ws2.cell(row=row_idx, column=2, value=r["regulation"])
    ws2.cell(row=row_idx, column=3, value=r["current_text"])
    ws2.cell(row=row_idx, column=4, value=tier)
    ws2.cell(row=row_idx, column=5, value=r["actual_score"])
    ws2.cell(row=row_idx, column=6, value=f"{r['weight']*100:.0f}%")
    ws2.cell(row=row_idx, column=7, value=round(r["weighted"], 2))
    ws2.cell(row=row_idx, column=8, value=f"{r['name']} 实测在 {r['current_text']}")

    for c in range(1, 9):
        cell = ws2.cell(row=row_idx, column=c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10)
        if c in [1, 3, 4, 5, 6, 7]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws2.cell(row=row_idx, column=5).fill = fill
    ws2.cell(row=row_idx, column=5).font = Font(name="微软雅黑", size=11, bold=True)
    row_idx += 1

# 综合得分
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

widths2 = [10, 24, 14, 18, 12, 10, 12, 30]
for i, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A5"

# ===== Sheet 3: 评分规则与平滑性约束 =====
ws3 = wb.create_sheet("评分规则说明")
ws3.merge_cells("A1:D1")
ws3["A1"] = "v11 评分规则 + 平滑性约束 + 7 指标说明"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

# 一、4 档规则
ws3.merge_cells("A3:D3")
ws3["A3"] = "一、4 档评分规则"
ws3["A3"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A3"].fill = PatternFill("solid", fgColor="FFF3E0")
ws3["A3"].alignment = Alignment(horizontal="left", vertical="center")

tier_rules = [
    ("档位", "分值", "含义", "示例"),
    ("红线", "-500", "触发监管 彻底淘汰", "LCR<120% / NSFR<100% / EVE>15% / CET1<8.7% / ROE<6% / IBL>33.33% / LR<4%"),
    ("危险-重惩罚", "10-60", "距红线 0-1 档", "LCR 120-130% / CET1 8.7-8.8% / EVE 12-15% / IBL 27-30% / LR 4-4.5%"),
    ("预警-轻惩罚", "60-90", "距红线 1-2 档", "LCR 130-140% / CET1 8.8-9.0% / NSFR 103-105% / EVE 10-12% / LR 4.5-6%"),
    ("安全", "90-100", "完全合规 满分", "LCR≥140% / CET1≥9.0% / EVE≤8% / IBL≤25% / ROE≥10% / LR 6-8%"),
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

# 二、平滑性约束
start_r = 12
ws3.merge_cells(f"A{start_r}:D{start_r}")
ws3.cell(row=start_r, column=1, value="二、平滑性约束 (避免极端波动方案)")
ws3.cell(row=start_r, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3.cell(row=start_r, column=1).fill = PatternFill("solid", fgColor="FFF3E0")
ws3.cell(row=start_r, column=1).alignment = Alignment(horizontal="left", vertical="center")

smooth_rules = [
    ("变化量", "扣分系数", "业务含义", ""),
    ("< 1pp", "0", "业务可落地", ""),
    ("1-3pp", "-5/pp", "需注意", ""),
    ("3-5pp", "-15/pp", "业务论证", ""),
    ("5-10pp", "-30/pp", "大幅扣分", ""),
    ("> 10pp", "-60/pp", "极端波动", ""),
]
for r, row_data in enumerate(smooth_rules, start_r+2):
    for c, val in enumerate(row_data, 1):
        cell = ws3.cell(row=r, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(r == start_r+2))
        cell.alignment = Alignment(horizontal="center", vertical="center")
        if r == start_r+2:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
        cell.border = border

# 三、7 指标说明
start_r = 21
ws3.merge_cells(f"A{start_r}:D{start_r}")
ws3.cell(row=start_r, column=1, value="三、7 指标说明")
ws3.cell(row=start_r, column=1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3.cell(row=start_r, column=1).fill = PatternFill("solid", fgColor="FFF3E0")
ws3.cell(row=start_r, column=1).alignment = Alignment(horizontal="left", vertical="center")

metric_desc = [
    ("指标", "类型", "红线", "说明"),
    ("LCR 流动性覆盖率", "适度最优", "< 120% (本行底线)", "LCR 太高意味着资金闲置"),
    ("NSFR 净稳定资金比例", "适度最优", "< 100% (监管)", "衡量长期资金稳定性"),
    ("EVE 银行账户利率风险", "越低越好", "> 15% (监管)", "利率风险敞口, 越低越安全"),
    ("CET1 核心一级资本充足率", "适度最优", "< 8.7% (7.5+0.5+0.7)", "过高 ROE 承压"),
    ("ROE 净资产收益率", "越高越好+硬约束", "< 6% (硬约束)", "非监管但低于 6% 不可接受"),
    ("IBL 同业负债占总负债比", "越低越好", "> 33.33% (监管)", "衡量同业负债依赖度"),
    ("LR 杠杆率", "适度最优", "< 4% (银保监)", "过高意味着资本冗余"),
]
for r, row_data in enumerate(metric_desc, start_r+2):
    for c, val in enumerate(row_data, 1):
        cell = ws3.cell(row=r, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(r == start_r+2))
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if r == start_r+2:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
        cell.border = border

widths3 = [22, 20, 22, 35]
for i, w in enumerate(widths3, 1):
    ws3.column_dimensions[get_column_letter(i)].width = w

wb.save(OUTPUT)
print(f"已保存: {OUTPUT}")
print(f"总分段数: {total_segments} (6 指标 4 档)")

# ===== 打印结果 =====
print("\n=== 中信银行 6 指标 4 档评分结果 (v10) ===")
print(f"{'指标':<8}{'红线':<28}{'实测值':<10}{'档位':<16}{'得分':<8}{'权重':<6}{'加权':<8}")
print("-" * 84)
for code in INDICATORS.keys():
    r = all_results[code]
    print(f"{r['code']:<8}{r['regulation']:<28}{r['current_text']:<10}{tier_label(r['actual_score']):<16}{r['actual_score']:<8}{r['weight']*100:<6.0f}{r['weighted']:<8.2f}")
print("-" * 84)
print(f"综合得分: {round(total_score, 2)}")
print(f"综合评级: {rating}")
