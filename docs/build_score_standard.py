# -*- coding: utf-8 -*-
"""
6 个银行指标 评分标准生成器
- 6 指标 × 10 段 = 60 个评分区间
- 监管指标 (LCR/NSFR/CET1/EVE) 不达标 → -100 分
- 非监管指标 (ROE/NIM) 按行业水平 + 中信银行实际经营情况打分
- 中信银行 2025 年末数据实测
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUTPUT = r"C:/银行经营/PRCP/docs/v2/评分标准_v6.xlsx"

# ===== 6 个指标定义 =====
# kind: lower=指标值越高越好, upper=指标值越低越好, neutral=非监管业绩指标
INDICATORS = [
    {
        "code": "LCR", "name": "流动性覆盖率", "kind": "lower", "regulatory": 1.00,
        "actual": 1.4729, "unit": "%", "weight": 0.20, "decimal": 2,
        "direction": "高", "direction_text": "≥ 监管值（100%）", "actual_text": "147.29%",
    },
    {
        "code": "NSFR", "name": "净稳定资金比例", "kind": "lower", "regulatory": 1.00,
        "actual": 1.0452, "unit": "%", "weight": 0.15, "decimal": 2,
        "direction": "高", "direction_text": "≥ 监管值（100%）", "actual_text": "104.52%",
    },
    {
        "code": "EVE", "name": "银行账户利率风险(EVE)", "kind": "upper", "regulatory": 0.15,
        "actual": 0.1054, "unit": "%", "weight": 0.15, "decimal": 2,
        "direction": "低", "direction_text": "≤ 监管值（15%）", "actual_text": "10.54%",
    },
    {
        "code": "CET1", "name": "核心一级资本充足率", "kind": "lower", "regulatory": 0.08,
        "actual": 0.0898, "unit": "%", "weight": 0.20, "decimal": 2,
        "direction": "高", "direction_text": "≥ 监管值（8%）", "actual_text": "8.98%",
    },
    {
        "code": "ROE", "name": "净资产收益率(ROAE)", "kind": "neutral", "regulatory": None,
        "actual": 0.0961, "unit": "%", "weight": 0.15, "decimal": 2,
        "direction": "中高", "direction_text": "业绩指标 越高越好", "actual_text": "9.61% (2026 H1)",
    },
    {
        "code": "NIM", "name": "净息差", "kind": "neutral", "regulatory": None,
        "actual": 0.0162, "unit": "%", "weight": 0.15, "decimal": 2,
        "direction": "中", "direction_text": "业绩指标 适度最优", "actual_text": "1.62% (2026 H1)",
    },
]

# ===== 每个指标的 10 段评分区间（关键参数表）=====
# 格式：[下限（含）, 上限（不含）, 得分, 评语]
# lower: 越高越好；upper: 越低越好；neutral: 适度最优
SCORING = {
    # ===== LCR 流动性覆盖率（监管 ≥100%）v4 非均匀分段 =====
    # 设计原则：实测 147.29% 落在第 6 段（145-150%），区间最密 5pp；距实测越远区间越大
    # 1 段: 0-100% (open, -100 监管红线)  2 段: 100-120% (20pp 宽)  3-4 段: 各 10pp
    # 5-6 段: 各 5pp (实测附近最密)  7 段: 10pp  8-9 段: 各 20pp  10 段: 200%+ (open 满分 100)
    "LCR": [
        (0.0,    1.00,  -100, "严重不达标：触发监管处罚"),
        (1.00,   1.20,    50, "勉强达标：缓冲极薄（远，实测 47pp 之外）"),
        (1.20,   1.30,    65, "合规偏低：缓冲不足（远，实测 17pp 之外）"),
        (1.30,   1.40,    75, "合规良好：流动性管理稳健（较远）"),
        (1.40,   1.45,    85, "同业中上：股份制前列（较近，5pp）"),
        (1.45,   1.50,    92, "⭐中信银行实测位置（147.29%）：5pp 最密"),
        (1.50,   1.60,    95, "充裕：流动性储备充足（较近，10pp）"),
        (1.60,   1.80,    97, "过度充裕：可能资金闲置（较远，20pp）"),
        (1.80,   2.00,    99, "冗余严重：收益率受损（远，20pp）"),
        (2.00,   9.99,   100, "满分：最佳水平（open）"),
    ],
    # ===== NSFR 净稳定资金比例（监管 ≥100%）v4 非均匀分段 =====
    # 实测 104.52% 落在第 6 段（104.5-105%），实测附近 0.5pp 最密
    "NSFR": [
        (0.0,    1.00,  -100, "严重不达标：长期资金缺口"),
        (1.00,   1.03,    50, "勉强达标：期限错配严重（远，3pp）"),
        (1.03,   1.035,   68, "合规偏低：稳定资金不足（较远）"),
        (1.035,  1.04,    78, "合规良好：期限匹配（较近）"),
        (1.04,   1.045,   85, "同业中上（较近，0.5pp）"),
        (1.045,  1.05,    90, "⭐中信银行实测位置（104.52%）：0.5pp 最密"),
        (1.05,   1.06,    93, "稳定：负债结构稳健（较近，1pp）"),
        (1.06,   1.08,    96, "过度稳定（较远，2pp）"),
        (1.08,   1.12,    99, "资金冗余（远，4pp）"),
        (1.12,   9.99,   100, "满分：最佳稳定资金结构（open）"),
    ],
    # ===== EVE 银行账户利率风险（监管 ≤15%）v4 非均匀分段 =====
    # 实测 10.54% 落在第 5 段（10.5-11%），实测附近 0.5pp 最密，越低越好所以越低段位越优
    "EVE": [
        (0.15,   9.99,  -100, "严重超标：触发监管上限"),
        (0.13,   0.15,    55, "逼近红线（远，2pp）"),
        (0.12,   0.13,    68, "接近上限（较远，1pp）"),
        (0.11,   0.12,    76, "偏高：久期缺口（较近，1pp）"),
        (0.105,  0.11,    84, "⭐中信银行实测位置（10.54%）：0.5pp 最密"),
        (0.10,   0.105,   88, "可控：久期管理良好（较近，0.5pp）"),
        (0.09,   0.10,    92, "稳健（较近，1pp）"),
        (0.08,   0.09,    95, "低风险：缺口管理优秀（较远，1pp）"),
        (0.06,   0.08,    98, "极低风险（远，2pp）"),
        (0.0,    0.06,   100, "满分：几乎无风险（open，6pp）"),
    ],
    # ===== CET1 核心一级资本充足率（监管 ≥8%）v6 门槛型 =====
    # 用户规则：8% 监管线，超过 8% 全部满分 100
    # 1 段: < 8% → -100（监管不达标）  2-10 段: ≥ 8% → 全部 100
    # 中信 8.98% 落在第 3 段（8.5-9.0%）→ 100
    "CET1": [
        (0.0,    0.08,  -100, "严重不达标：未达 8% 监管底线"),
        (0.08,   0.085,  100, "刚达监管：8% 门槛（0.5pp）"),
        (0.085,  0.09,   100, "⭐中信银行 2025 实测位置（8.98%）：已超 8% 满分"),
        (0.09,   0.095,  100, "达标（0.5pp）"),
        (0.095,  0.10,   100, "达标（0.5pp）"),
        (0.10,   0.105,  100, "达标（0.5pp）"),
        (0.105,  0.11,   100, "达标（0.5pp）"),
        (0.11,   0.12,   100, "达标（1pp）"),
        (0.12,   0.13,   100, "达标（1pp）"),
        (0.13,   9.99,   100, "满分：超过 8% 监管线（open）"),
    ],
    # ===== ROE 净资产收益率 v5 按 2026 H1 中信银行实测分档 =====
    # 中信银行 2026 H1 ROAE 加权 = 9.61%（行业持续下行：10.69% → 9.77% → 9.61%）
    # 段 7 (9.5-10%) ⭐ 中信实测位置
    "ROE": [
        (0.0,    0.03,    25, "极差：盈利模式重大问题（远，3pp open）"),
        (0.03,   0.05,    45, "低于行业（远，2pp）"),
        (0.05,   0.07,    60, "行业中下（较远，2pp）"),
        (0.07,   0.085,   75, "接近均值（较近，1.5pp）"),
        (0.085,  0.09,    85, "接近行业中位（较近，0.5pp）"),
        (0.09,   0.095,   92, "行业中上（较近，0.5pp）"),
        (0.095,  0.10,    95, "⭐中信银行 2026 H1 实测位置（9.61%）：股份制中位偏上"),
        (0.10,   0.11,    98, "优秀：股份制头部（较远，1pp）"),
        (0.11,   0.13,    99, "卓越（远，2pp）"),
        (0.13,   9.99,   100, "满分：顶级水平（open）"),
    ],
    # ===== NIM 净息差 v5 按 2026 H1 中信银行实测分档 =====
    # 中信银行 2026 H1 NIM = 1.62%（行业持续收窄：1.77% → 1.63% → 1.62%）
    # 段 5 (1.6-1.65%) ⭐ 中信实测位置
    # 单峰设计：段 6 (1.65-1.7%) 理论最优 100 分
    "NIM": [
        (0.0,    0.010,   25, "极低：盈利能力严重不足（远，1pp open）"),
        (0.010,  0.013,   45, "低于行业（较远，0.3pp）"),
        (0.013,  0.015,   62, "行业中下（较近，0.2pp）"),
        (0.015,  0.016,   78, "行业中位（较近，0.1pp）"),
        (0.016,  0.0165,  90, "⭐中信银行 2026 H1 实测位置（1.62%）：行业新常态"),
        (0.0165, 0.017,  100, "满分：当前最优水平（0.05pp）"),
        (0.017,  0.018,   95, "偏上：高于行业新常态（0.1pp）"),
        (0.018,  0.019,   82, "偏高：可能含高风险溢价（0.1pp）"),
        (0.019,  0.022,   60, "过高：资产结构异常（0.3pp）"),
        (0.022,  9.99,    45, "异常：需立即核查（open）"),
    ],
}

# ===== 工具函数 =====
def fmt_pct(x: float, decimal: int = 2) -> str:
    """格式化为百分比字符串"""
    return f"{x*100:.{decimal}f}%"

def find_segment(code: str, value: float):
    """根据指标值找对应分段"""
    for i, (lo, hi, score, comment) in enumerate(SCORING[code], 1):
        if lo <= value < hi:
            return i, lo, hi, score, comment
    return 10, None, None, None, None  # 默认第 10 段

# ===== 创建 Excel =====
wb = openpyxl.Workbook()

# ===== Sheet 1: 评分标准 =====
ws1 = wb.active
ws1.title = "评分标准"

# 标题
ws1.merge_cells("A1:J1")
ws1["A1"] = "中信银行 6 大指标 评分标准（10 段制）"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

# 副标题
ws1.merge_cells("A2:J2")
ws1["A2"] = "监管指标：LCR/NSFR/CET1/EVE  不达标直接 -100 分 | 业绩指标：ROE/NIM 按行业水平评分 | 数据基准：中信银行 2025 年末"
ws1["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[2].height = 20

# 表头
headers = ["指标代码", "指标名称", "监管类型", "监管值", "最优方向", "分段", "区间下限", "区间上限", "得分", "评语"]
for col, h in enumerate(headers, 1):
    cell = ws1.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws1.row_dimensions[4].height = 30

thin = Side(border_style="thin", color="DDDDDD")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

row_idx = 5
for ind in INDICATORS:
    code = ind["code"]
    segments = SCORING[code]
    decimal = ind["decimal"]

    # 监管类型文本
    if ind["regulatory"] is not None:
        reg_text = f"监管 {ind['direction_text']}"
        reg_value = fmt_pct(ind["regulatory"], decimal)
    else:
        reg_text = "非监管"
        reg_value = "—"
    direction = "越高越好" if ind["direction"] in ("高", "中高") else ("越低越好" if ind["direction"] == "低" else "适度最优")

    start_row = row_idx
    for seg_idx, (lo, hi, score, comment) in enumerate(segments, 1):
        # 分段颜色（按分数从低到高渐变）
        if score <= 0:
            seg_fill = PatternFill("solid", fgColor="FFCCCC")  # 红：不达标
        elif score < 70:
            seg_fill = PatternFill("solid", fgColor="FFE0B2")  # 橙
        elif score < 85:
            seg_fill = PatternFill("solid", fgColor="FFF9C4")  # 黄
        elif score < 95:
            seg_fill = PatternFill("solid", fgColor="C8E6C9")  # 浅绿
        else:
            seg_fill = PatternFill("solid", fgColor="A5D6A7")  # 绿

        # 写每行
        if seg_idx == 1:
            ws1.cell(row=row_idx, column=1, value=code)
            ws1.cell(row=row_idx, column=2, value=ind["name"])
            ws1.cell(row=row_idx, column=3, value=reg_text)
            ws1.cell(row=row_idx, column=4, value=reg_value)
            ws1.cell(row=row_idx, column=5, value=direction)
        ws1.cell(row=row_idx, column=6, value=seg_idx)
        ws1.cell(row=row_idx, column=7, value=fmt_pct(lo, decimal))
        ws1.cell(row=row_idx, column=8, value=fmt_pct(hi, decimal))
        ws1.cell(row=row_idx, column=9, value=score)
        ws1.cell(row=row_idx, column=10, value=comment)

        for c in range(1, 11):
            cell = ws1.cell(row=row_idx, column=c)
            cell.border = border
            if seg_idx == 1 and c <= 5:
                cell.fill = PatternFill("solid", fgColor="F5F5F5")
            if c == 9:
                cell.fill = seg_fill
                cell.font = Font(name="微软雅黑", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c == 6:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left" if c == 10 else "center", vertical="center", wrap_text=(c == 10))
        row_idx += 1

    # 合并指标代码/名称/监管类型/监管值/方向
    if row_idx - 1 > start_row:
        ws1.merge_cells(f"A{start_row}:A{row_idx-1}")
        ws1.merge_cells(f"B{start_row}:B{row_idx-1}")
        ws1.merge_cells(f"C{start_row}:C{row_idx-1}")
        ws1.merge_cells(f"D{start_row}:D{row_idx-1}")
        ws1.merge_cells(f"E{start_row}:E{row_idx-1}")
        # 设置合并单元格的填充和居中
        for c in [1, 2, 3, 4, 5]:
            cell = ws1.cell(row=start_row, column=c)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.fill = PatternFill("solid", fgColor="F5F5F5")
            cell.font = Font(name="微软雅黑", bold=True)

# 列宽
widths = [10, 22, 18, 12, 12, 8, 12, 12, 10, 40]
for i, w in enumerate(widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w

# 冻结
ws1.freeze_panes = "A5"

# ===== Sheet 2: 中信银行实测得分 =====
ws2 = wb.create_sheet("中信银行得分")

ws2.merge_cells("A1:K1")
ws2["A1"] = "中信银行 6 大指标 2025 年末 实测得分"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 30

ws2.merge_cells("A2:K2")
ws2["A2"] = "得分 = 指标值按所在分段查表 | 加权得分 = 得分 × 权重 | 综合得分 = 6 指标加权平均"
ws2["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[2].height = 20

# 表头
headers2 = ["指标代码", "指标名称", "监管值", "实测值", "达标情况", "所在分段", "得分", "权重", "加权得分", "评语", "排名"]
for col, h in enumerate(headers2, 1):
    cell = ws2.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws2.row_dimensions[4].height = 30

# 写数据
results = []
for ind in INDICATORS:
    code = ind["code"]
    seg_idx, lo, hi, score, comment = find_segment(code, ind["actual"])

    # 达标判断
    if ind["regulatory"] is not None:
        if ind["kind"] == "lower":
            compliant = "✓ 达标" if ind["actual"] >= ind["regulatory"] else "✗ 不达标"
        else:  # upper
            compliant = "✓ 达标" if ind["actual"] <= ind["regulatory"] else "✗ 不达标"
        reg_text = fmt_pct(ind["regulatory"], ind["decimal"])
    else:
        compliant = "— 非监管"
        reg_text = "—"

    results.append({
        "code": code,
        "name": ind["name"],
        "reg_value": reg_text,
        "actual": fmt_pct(ind["actual"], ind["decimal"]),
        "compliant": compliant,
        "seg_idx": seg_idx,
        "score": score,
        "weight": ind["weight"],
        "weighted": round(score * ind["weight"], 2),
        "comment": comment,
    })

# 按得分降序排名
results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)
score_rank = {r["code"]: i+1 for i, r in enumerate(results_sorted)}

row_idx = 5
for r in results:
    # 得分颜色
    if r["score"] <= 0:
        score_fill = PatternFill("solid", fgColor="FFCCCC")
    elif r["score"] < 70:
        score_fill = PatternFill("solid", fgColor="FFE0B2")
    elif r["score"] < 85:
        score_fill = PatternFill("solid", fgColor="FFF9C4")
    elif r["score"] < 95:
        score_fill = PatternFill("solid", fgColor="C8E6C9")
    else:
        score_fill = PatternFill("solid", fgColor="A5D6A7")

    ws2.cell(row=row_idx, column=1, value=r["code"])
    ws2.cell(row=row_idx, column=2, value=r["name"])
    ws2.cell(row=row_idx, column=3, value=r["reg_value"])
    ws2.cell(row=row_idx, column=4, value=r["actual"])
    ws2.cell(row=row_idx, column=5, value=r["compliant"])
    ws2.cell(row=row_idx, column=6, value=f"第 {r['seg_idx']} 段")
    ws2.cell(row=row_idx, column=7, value=r["score"])
    ws2.cell(row=row_idx, column=8, value=f"{r['weight']*100:.0f}%")
    ws2.cell(row=row_idx, column=9, value=r["weighted"])
    ws2.cell(row=row_idx, column=10, value=r["comment"])
    ws2.cell(row=row_idx, column=11, value=f"第 {score_rank[r['code']]} 名")

    for c in range(1, 12):
        cell = ws2.cell(row=row_idx, column=c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10)
        if c in [3, 4, 6, 7, 8, 9, 11]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="center" if c == 5 else "left", vertical="center", wrap_text=(c == 10))
        if c == 7:
            cell.fill = score_fill
            cell.font = Font(name="微软雅黑", size=11, bold=True)
        if c == 5:
            if r["compliant"].startswith("✓"):
                cell.fill = PatternFill("solid", fgColor="C8E6C9")
                cell.font = Font(name="微软雅黑", size=10, bold=True, color="1B5E20")
            elif r["compliant"].startswith("✗"):
                cell.fill = PatternFill("solid", fgColor="FFCDD2")
                cell.font = Font(name="微软雅黑", size=10, bold=True, color="B71C1C")
    ws2.row_dimensions[row_idx].height = 28
    row_idx += 1

# 综合得分行
total_score = sum(r["weighted"] for r in results)
ws2.cell(row=row_idx, column=1, value="综合得分")
ws2.merge_cells(f"A{row_idx}:H{row_idx}")
ws2.cell(row=row_idx, column=9, value=round(total_score, 2))
ws2.merge_cells(f"J{row_idx}:K{row_idx}")
ws2.cell(row=row_idx, column=10, value="6 指标加权平均（中信银行 2025 年末经营情况）")

for c in range(1, 12):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

# 评级行
if total_score >= 90:
    rating = "A+  卓越"
elif total_score >= 85:
    rating = "A   优秀"
elif total_score >= 80:
    rating = "B+  良好"
elif total_score >= 70:
    rating = "B   中等"
elif total_score >= 60:
    rating = "C   及格"
else:
    rating = "D   警示"

row_idx += 1
ws2.cell(row=row_idx, column=1, value="综合评级")
ws2.merge_cells(f"A{row_idx}:H{row_idx}")
ws2.cell(row=row_idx, column=9, value=rating)
ws2.merge_cells(f"J{row_idx}:K{row_idx}")
ws2.cell(row=row_idx, column=10, value=f"综合 {round(total_score, 1)} 分")

for c in range(1, 12):
    cell = ws2.cell(row=row_idx, column=c)
    cell.fill = PatternFill("solid", fgColor="FFE082")
    cell.font = Font(name="微软雅黑", size=12, bold=True, color="E65100")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws2.row_dimensions[row_idx].height = 32

# 列宽
widths2 = [10, 22, 12, 12, 12, 12, 10, 10, 12, 38, 12]
for i, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A5"

# ===== Sheet 3: 评分规则说明 =====
ws3 = wb.create_sheet("评分规则")
ws3.merge_cells("A1:C1")
ws3["A1"] = "评分规则与方法论"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

rules = [
    ("", "", ""),
    ("1. 分段制（10 段）", "每指标分 10 段", "1=最差, 10=最优, 覆盖范围从最差到最优秀"),
    ("2. 监管指标红线", "LCR/NSFR/CET1/EVE 共 4 项", "任一指标不达标 → 该指标直接 -100 分（触发监管处罚）"),
    ("", "", ""),
    ("3. LCR 流动性覆盖率", "监管 ≥ 100%（银保监）", "1 段 <100% (-100) | 2-3 段刚达标 | 4-7 段健康 | 8-10 段过度冗余"),
    ("4. NSFR 净稳定资金比例", "监管 ≥ 100%（银保监）", "1 段 <100% (-100) | 2-3 段刚达标 | 4-7 段合理 | 8-10 段过度稳定"),
    ("5. EVE 银行账户利率风险", "监管 ≤ 15%（IRRBB 利率风险）", "1 段 >15% (-100) | 2-3 段逼近红线 | 4-7 段可控 | 8-10 段极低风险"),
    ("6. CET1 核心一级资本充足率", "监管 ≥ 8.5%", "1 段 <8.5% (-100) | 2-4 段刚达标 | 5-7 段稳健 | 8-10 段过度充足"),
    ("7. ROE 净资产收益率", "无监管值（业绩指标）", "1 段 <5% | 5 段 9-10%（中信银行位置）| 8-10 段 ≥12%"),
    ("8. NIM 净息差", "无监管值（业绩指标）", "1 段 <1.0% | 5 段 1.7-1.8%（中信银行位置）| 8-10 段 ≥2.2%"),
    ("", "", ""),
    ("9. 权重设计", "LCR 20% / CET1 20% / NSFR 15% / EVE 15% / ROE 15% / NIM 15%", "监管资本 + 流动性 合计 70%，业绩指标 30%"),
    ("10. 评级标准", "A+(≥90) / A(85-90) / B+(80-85) / B(70-80) / C(60-70) / D(<60)", "综合得分 = 6 指标加权平均"),
    ("", "", ""),
    ("11. 评级结果（中信银行 2025 年末）", f"综合得分 {round(total_score, 1)} 分", f"评级：{rating}"),
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

ws3.column_dimensions["A"].width = 32
ws3.column_dimensions["B"].width = 28
ws3.column_dimensions["C"].width = 50

wb.save(OUTPUT)
print(f"已保存：{OUTPUT}")

# 打印最终结果
print(f"\n=== 中信银行 6 大指标 评分结果 ===")
print(f"{'指标':<8} {'实测值':<10} {'达标':<8} {'分段':<8} {'得分':<6} {'权重':<6} {'加权':<6} {'评语'}")
print("-" * 100)
for r in results:
    print(f"{r['code']:<8} {r['actual']:<10} {r['compliant']:<8} 第 {r['seg_idx']} 段  {r['score']:<6} {r['weight']*100:.0f}%   {r['weighted']:<6} {r['comment']}")
print("-" * 100)
print(f"综合得分：{round(total_score, 2)}")
print(f"综合评级：{rating}")
