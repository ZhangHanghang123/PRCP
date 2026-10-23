"""中信银行 7 指标 0-500 分评分规则 v12

设计原则:
- 0-500 分制, 无负分
- 监管不达标 = 0 分 (替代 v11 的 -500)
- 每个指标 0-500 分, 通过线性插值计算
- 适度最优指标 (LCR/NSFR/CET1/LR/NIM) 超过最优区间减分
- 越低越好指标 (EVE/IBL) 超过红线 = 0, 低于最优减分

实测值: 中信银行 2025 年末 (ROE 用 2026 H1, LR=7.06%)
权重: LCR 18% + NSFR 14% + EVE 13% + CET1 18% + ROE 13% + IBL 12% + LR 12% = 100%
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ===================== 1. 指标配置 (0-500 分制) =====================
# score 公式: 0-500 分线性插值
# direction: 'higher' (越高越好) 或 'lower' (越低越好)
# 关键节点: red (0 分线), danger_top (150), warn_top (300), safe_top (500, 适度最优)
# 可选: excess_top (过优减分上界), excess_floor (过优最低分)

INDICATORS = {
    "LCR": {
        "code": "LCR", "name": "流动性覆盖率", "direction": "higher",
        "current": 1.4729, "weight": 0.18,
        "regulation": "< 120% (本行底线, 监管 100%)",
        # 关键节点: red=1.20 (0分), danger_top=1.30 (150), warn_top=1.40 (300), safe_top=1.50 (500)
        # 过优: 1.50-2.00 (500→350), excess_floor=300
        "red": 1.20, "danger_top": 1.30, "warn_top": 1.40, "safe_top": 1.50,
        "excess_top": 2.00, "excess_floor": 300,
    },
    "NSFR": {
        "code": "NSFR", "name": "净稳定资金比例", "direction": "higher",
        "current": 1.0452, "weight": 0.14,
        "regulation": "< 100% (监管)",
        # 关键节点: red=1.00 (0), danger_top=1.03 (150), warn_top=1.05 (300), safe_top=1.07 (500)
        # 过优: 1.07-1.15 (500→350), excess_floor=300
        "red": 1.00, "danger_top": 1.03, "warn_top": 1.05, "safe_top": 1.07,
        "excess_top": 1.15, "excess_floor": 300,
    },
    "EVE": {
        "code": "EVE", "name": "银行账户利率风险", "direction": "lower",
        "current": 0.1054, "weight": 0.13,
        "regulation": "> 15% (监管)",
        # 关键节点 (越低越好): red=0.15 (0), danger_top=0.12 (150), warn_top=0.10 (300), safe_top=0.08 (500)
        # 过优 (太低): <0.03 → excess_floor=450
        "red": 0.15, "danger_top": 0.12, "warn_top": 0.10, "safe_top": 0.08,
        "excess_top": 0.03, "excess_floor": 450,
    },
    "CET1": {
        "code": "CET1", "name": "核心一级资本充足率", "direction": "higher",
        "current": 0.0898, "weight": 0.18,
        "regulation": "< 8.7% (7.5 监管 + 0.5 附加 + 0.7 本行)",
        # 关键节点: red=0.087 (0), danger_top=0.088 (150), warn_top=0.09 (300), safe_top=0.10 (500)
        # 过优: 0.10-0.13 (500→350), excess_floor=300
        "red": 0.087, "danger_top": 0.088, "warn_top": 0.09, "safe_top": 0.10,
        "excess_top": 0.13, "excess_floor": 300,
    },
    "ROE": {
        "code": "ROE", "name": "净资产收益率", "direction": "higher",
        "current": 0.0961, "weight": 0.13,
        "regulation": "< 6% (硬约束, 非监管但不可接受)",
        # 关键节点: red=0.06 (0), danger_top=0.08 (150), warn_top=0.09 (300), safe_top=0.12 (500)
        # 无过优减分 (越高越好)
        "red": 0.06, "danger_top": 0.08, "warn_top": 0.09, "safe_top": 0.12,
    },
    "IBL": {
        "code": "IBL", "name": "同业负债占总负债比例", "direction": "lower",
        "current": 0.2160, "weight": 0.12,
        "regulation": "> 33.33% (监管, 负债端)",
        # 关键节点: red=0.3333 (0), danger_top=0.30 (150), warn_top=0.25 (300), safe_top=0.20 (500)
        # 过优 (太低): <0.05 → excess_floor=380
        "red": 0.3333, "danger_top": 0.30, "warn_top": 0.25, "safe_top": 0.20,
        "excess_top": 0.05, "excess_floor": 380,
    },
    "LR": {
        "code": "LR", "name": "杠杆率", "direction": "higher",
        "current": 0.0706, "weight": 0.12,
        "regulation": "< 4% (银保监, 巴塞尔 III ≥ 3%)",
        # 关键节点: red=0.04 (0), danger_top=0.045 (150), warn_top=0.06 (300), safe_top=0.08 (500)
        # 过优: 0.08-0.12 (500→350), excess_floor=300
        "red": 0.04, "danger_top": 0.045, "warn_top": 0.06, "safe_top": 0.08,
        "excess_top": 0.12, "excess_floor": 300,
    },
}

# ===================== 2. 0-500 分线性插值 =====================
def calc_score(value, cfg):
    """根据指标配置计算 0-500 分"""
    d = cfg["direction"]
    red = cfg["red"]
    danger_top = cfg["danger_top"]
    warn_top = cfg["warn_top"]
    safe_top = cfg["safe_top"]
    excess_top = cfg.get("excess_top")
    excess_floor = cfg.get("excess_floor", 300)

    if d == "higher":
        # value < red → 0
        if value < red:
            return 0
        # value >= safe_top 进入过优
        if value > safe_top and excess_top and value <= excess_top:
            t = (value - safe_top) / (excess_top - safe_top)
            return round(500 - 200 * t, 2)
        # value > excess_top → excess_floor
        if value > safe_top and excess_top and value > excess_top:
            return excess_floor
        # value == safe_top 刚好 500
        if value == safe_top:
            return 500
        # value 在 [warn_top, safe_top] → 300-500
        if value >= warn_top:
            t = (value - warn_top) / (safe_top - warn_top)
            return round(300 + 200 * t, 2)
        # value 在 [danger_top, warn_top] → 150-300
        if value >= danger_top:
            t = (value - danger_top) / (warn_top - danger_top)
            return round(150 + 150 * t, 2)
        # value 在 [red, danger_top] → 0-150
        t = (value - red) / (danger_top - red)
        return round(150 * t, 2)
    else:  # lower 越低越好
        # value > red → 0
        if value > red:
            return 0
        # value < excess_top 进入过优 (太低)
        if value < safe_top and excess_top and value >= excess_top:
            t = (safe_top - value) / (safe_top - excess_top)
            return round(500 - 200 * t, 2)
        # value < excess_top → excess_floor
        if value < safe_top and excess_top and value < excess_top:
            return excess_floor
        # value == safe_top 刚好 500
        if value == safe_top:
            return 500
        # value 在 [safe_top, warn_top] → 300-500
        if value <= warn_top:
            t = (warn_top - value) / (warn_top - safe_top)
            return round(300 + 200 * t, 2)
        # value 在 [warn_top, danger_top] → 150-300
        if value <= danger_top:
            t = (danger_top - value) / (danger_top - warn_top)
            return round(150 + 150 * t, 2)
        # value 在 [danger_top, red] → 0-150
        t = (red - value) / (red - danger_top)
        return round(150 * t, 2)
    return 0

def tier_label(score):
    """根据得分返回档位标签"""
    if score == 0:
        return "🔴 不达标"
    elif score < 150:
        return "🟠 危险"
    elif score < 300:
        return "🟡 预警"
    elif score < 500:
        return "🟢 安全"
    else:
        return "🟢🟢 满分"

def tier_color(score):
    if score == 0:
        return PatternFill("solid", fgColor="FFCDD2")  # 红
    elif score < 150:
        return PatternFill("solid", fgColor="FFE0B2")  # 橙
    elif score < 300:
        return PatternFill("solid", fgColor="FFF9C4")  # 黄
    elif score < 500:
        return PatternFill("solid", fgColor="C8E6C9")  # 绿
    else:
        return PatternFill("solid", fgColor="66BB6A")  # 深绿

def get_rating(score):
    """综合得分评级 (输入 0-100 加权得分)"""
    if score >= 90: return "A+ 卓越"
    if score >= 85: return "A 优秀"
    if score >= 80: return "B+ 良好"
    if score >= 70: return "B 中等"
    if score >= 60: return "C 较弱"
    return "D 差"

# ===================== 3. 生成段位 (用于 Sheet 1) =====================
def generate_segments(cfg):
    """根据配置生成 0-500 分段位 (用于 Sheet 1 展示)"""
    d = cfg["direction"]
    red = cfg["red"]
    danger_top = cfg["danger_top"]
    warn_top = cfg["warn_top"]
    safe_top = cfg["safe_top"]
    excess_top = cfg.get("excess_top")
    excess_floor = cfg.get("excess_floor", 300)

    segs = []
    if d == "higher":
        segs.append((0, red, 0, "不达标 (≤红线)"))
        segs.append((red, danger_top, None, "危险 0-150 分 (插值)"))
        segs.append((danger_top, warn_top, None, "预警 150-300 分 (插值)"))
        segs.append((warn_top, safe_top, None, "安全 300-500 分 (插值)"))
        segs.append((safe_top, safe_top, 500, "⭐适度最优 500 分"))
        if excess_top:
            segs.append((safe_top, excess_top, None, "过优 500→减分 (插值)"))
            segs.append((excess_top, 9.99, excess_floor, f"极度过剩 {excess_floor} 分"))
    else:  # lower
        segs.append((red, 9.99, 0, "不达标 (≥红线)"))
        segs.append((danger_top, red, None, "危险 0-150 分 (插值)"))
        segs.append((warn_top, danger_top, None, "预警 150-300 分 (插值)"))
        segs.append((safe_top, warn_top, None, "安全 300-500 分 (插值)"))
        segs.append((safe_top, safe_top, 500, "⭐适度最优 500 分"))
        if excess_top:
            segs.append((excess_top, safe_top, None, "过优 500→减分 (插值)"))
            segs.append((0, excess_top, excess_floor, f"极度过剩 {excess_floor} 分"))

    # 填充 score=None 的段位 (插值范围)
    filled_segs = []
    for lo, hi, score, comment in segs:
        if score is None:
            # 在这个范围内找 5 个细分点 (避免 Sheet 1 太长)
            n = 5
            for i in range(n):
                p = lo + (hi - lo) * i / n
                p_next = lo + (hi - lo) * (i + 1) / n
                s = calc_score((p + p_next) / 2, cfg)
                filled_segs.append((p, p_next, s, comment))
        else:
            filled_segs.append((lo, hi, score, comment))
    return filled_segs

# ===================== 4. 创建 Excel =====================
OUTPUT = r"C:/银行经营/PRCP/docs/v2/评分标准_v12.xlsx"
wb = Workbook()
wb.remove(wb.active)

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===== Sheet 1: 0-500 分评分标准 =====
ws1 = wb.create_sheet("0-500分评分标准")
ws1.merge_cells("A1:K1")
ws1["A1"] = "中信银行 7 指标 0-500 分评分规则 v12 (LCR / NSFR / EVE / CET1 / ROE / IBL / LR)"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:K2")
ws1["A2"] = "LCR 18% + NSFR 14% + EVE 13% + CET1 18% + ROE 13% + IBL 12% + LR 12% = 100% | 监管不达标 = 0 分 | 适度最优 = 500 分 | 实测: 中信银行 2025 年末 (ROE 用 2026 H1, LR=7.06%)"
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
    current = cfg["current"]
    direction = cfg["direction"]
    regulation = cfg["regulation"]
    actual_score = calc_score(current, cfg)

    # 生成段位
    segs = generate_segments(cfg)

    all_results[code] = {
        "code": code,
        "name": cfg["name"],
        "current": current,
        "current_text": f"{current*100:.2f}%" if current >= 0.01 else f"{current*100:.4f}%",
        "regulation": regulation,
        "direction": direction,
        "actual_score": actual_score,
        "weight": cfg["weight"],
        "weighted": actual_score * cfg["weight"] / 5,  # 0-500 映射到 0-100
    }
    total_segments += len(segs)

    start_row = row_idx
    seg_count = 0
    for (lo, hi, score, comment) in segs:
        seg_count += 1
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
        ws1.cell(row=row_idx, column=3, value=seg_count)
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
        # 高亮实测位置
        if lo <= current <= hi:
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
ws2["A1"] = "中信银行 7 指标 0-500 分实测得分 v12"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 30

ws2.merge_cells("A2:H2")
ws2["A2"] = "LCR 18% + NSFR 14% + EVE 13% + CET1 18% + ROE 13% + IBL 12% + LR 12% = 100% | 0-500 分制 | 监管不达标 = 0 分"
ws2["A2"].font = Font(name="微软雅黑", size=10, bold=False, color="555555")
ws2["A2"].fill = PatternFill("solid", fgColor="FFF3E0")
ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[2].height = 22

headers2 = ["指标", "红线", "实测值", "档位", "得分(/500)", "权重", "加权(/100)", "说明"]
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
    ws2.cell(row=row_idx, column=5, value=round(r["actual_score"], 2))
    ws2.cell(row=row_idx, column=6, value=f"{r['weight']*100:.0f}%")
    ws2.cell(row=row_idx, column=7, value=round(r["weighted"], 2))
    ws2.cell(row=row_idx, column=8, value=f"{r['name']} 实测 {r['current_text']}")

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
total_weighted = sum(r["weighted"] for r in all_results.values())
total_score_500 = total_weighted * 5  # 反向映射 0-100 → 0-500
ws2.cell(row=row_idx, column=1, value="综合得分")
ws2.merge_cells(f"A{row_idx}:F{row_idx}")
ws2.cell(row=row_idx, column=7, value=f"{round(total_weighted, 2)}/100")
ws2.cell(row=row_idx, column=8, value=f"= {round(total_score_500, 2)}/500")
for c in range(1, 9):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

rating = get_rating(total_weighted)
row_idx += 1
ws2.cell(row=row_idx, column=1, value="综合评级")
ws2.merge_cells(f"A{row_idx}:F{row_idx}")
ws2.cell(row=row_idx, column=7, value=rating)
ws2.cell(row=row_idx, column=8, value=f"满分 100 (500/500)")
for c in range(1, 9):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="FFE082")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="E65100")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

widths2 = [10, 24, 14, 18, 14, 10, 14, 32]
for i, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A5"

# ===== Sheet 3: 评分规则说明 =====
ws3 = wb.create_sheet("评分规则说明")
ws3.merge_cells("A1:D1")
ws3["A1"] = "v12 0-500 分评分规则 + 平滑性约束 + 7 指标说明"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

# 一、0-500 分评分规则
ws3.merge_cells("A3:D3")
ws3["A3"] = "一、0-500 分评分规则 (替代 v11 的 0-100 分 + -500 红线)"
ws3["A3"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A3"].fill = PatternFill("solid", fgColor="FFF3E0")
ws3["A3"].alignment = Alignment(horizontal="left", vertical="center")

tier_rules = [
    ("档位", "分值", "含义", "示例"),
    ("不达标", "0", "触发监管 / 硬约束 彻底淘汰", "LCR<120% / NSFR<100% / EVE>15% / CET1<8.7% / ROE<6% / IBL>33.33% / LR<4%"),
    ("危险", "0-150", "距适度最优 4/5 以上", "LCR 120-128% / CET1 8.7-8.84% / EVE 12-15% / IBL 27-33.33% / LR 4-4.3%"),
    ("预警", "150-300", "距适度最优 2/5-3/5", "LCR 128-140% / CET1 8.84-9% / NSFR 103-105% / EVE 10-12% / LR 4.3-6%"),
    ("安全", "300-500", "完全合规, 满分 500", "LCR 140-150% / CET1 9-10% / NSFR 105-107% / EVE 6-10% / IBL 20-25% / LR 6-8%"),
]
for r, row_data in enumerate(tier_rules, 5):
    for c, val in enumerate(row_data, 1):
        cell = ws3.cell(row=r, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(r == 5))
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if r == 5:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
        elif "不达标" in val:
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
    ("指标", "类型", "红线 (0 分)", "适度最优 (500 分)"),
    ("LCR 流动性覆盖率", "适度最优", "< 120% (本行底线)", "140-150%"),
    ("NSFR 净稳定资金比例", "适度最优", "< 100% (监管)", "105-107%"),
    ("EVE 银行账户利率风险", "越低越好", "> 15% (监管)", "6-8%"),
    ("CET1 核心一级资本充足率", "适度最优", "< 8.7% (7.5+0.5+0.7)", "9-10%"),
    ("ROE 净资产收益率", "越高越好+硬约束", "< 6% (硬约束)", "≥ 12%"),
    ("IBL 同业负债占总负债比", "越低越好", "> 33.33% (监管)", "≤ 20%"),
    ("LR 杠杆率", "适度最优", "< 4% (银保监)", "6-8%"),
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

widths3 = [22, 18, 22, 35]
for i, w in enumerate(widths3, 1):
    ws3.column_dimensions[get_column_letter(i)].width = w

wb.save(OUTPUT)
print(f"已保存: {OUTPUT}")
print(f"总分段数: {total_segments} (7 指标, 每指标约 5-7 段)")

# ===== 5. 打印实测得分 =====
print("\n=== 中信银行 7 指标 0-500 分评分结果 (v12) ===")
print(f"{'指标':<8}{'红线':<24}{'实测值':<10}{'档位':<14}{'得分/500':<10}{'权重':<6}{'加权/100':<8}")
print("-" * 80)
for code in INDICATORS.keys():
    r = all_results[code]
    print(f"{r['code']:<8}{r['regulation'][:22]:<24}{r['current_text']:<10}{tier_label(r['actual_score']):<14}{r['actual_score']:<10.2f}{r['weight']*100:<6.0f}{r['weighted']:<8.2f}")
print("-" * 80)
print(f"综合得分: {round(total_weighted, 2)}/100 = {round(total_score_500, 2)}/500")
print(f"综合评级: {rating}")
