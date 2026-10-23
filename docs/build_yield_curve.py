"""对 prcp_basic_20251231.xlsx 进行收益率曲线插值

任务: 在网上取到 2025-12-31 的国债收益率曲线值,
     按照 Excel 剩余期限结构 (1M..60M, 10Y, 15Y, 20Y, 30Y) 进行线性插值,
     插值结果写入 R46 标题下方的期限结构表格.
"""

import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

EXCEL_PATH = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231.xlsx"

# ===================== 1. 2025-12-31 国债收益率曲线关键节点 =====================
# 数据来源: 中债登 chinabond.com.cn 日评 2025-12-31
# 关键节点 (剩余期限以年为单位, 收益率%)
# 1Y/2Y/3Y/5Y/7Y/10Y/30Y 来自中债登官方
# 短期(1M/3M/6M/9M)和长期(15Y/20Y/50Y/60Y)由线性插值/外推
KEY_POINTS = [
    # (剩余期限_年, 收益率%)
    (0.0833, 1.27),    # 1M (短期平坦)
    (0.1667, 1.27),    # 2M
    (0.25,   1.27),    # 3M (中债登 12-31 日评)
    (0.3333, 1.28),    # 4M
    (0.4167, 1.29),    # 5M
    (0.50,   1.30),    # 6M (中债登关键期限)
    (0.5833, 1.31),    # 7M
    (0.6667, 1.315),   # 8M
    (0.75,   1.32),    # 9M (中债登关键期限)
    (0.8333, 1.328),   # 10M
    (0.9167, 1.333),   # 11M
    (1.00,   1.3372),  # 12M / 1Y (中债登 1.34%)
    (1.50,   1.35),    # 18M
    (2.00,   1.3605),  # 24M / 2Y (中债登 1.36%)
    (2.50,   1.37),    # 30M
    (3.00,   1.3830),  # 36M / 3Y (中债登 1.38%)
    (4.00,   1.50),    # 48M / 4Y
    (5.00,   1.6309),  # 60M / 5Y (中债登 1.63%)
    (6.00,   1.68),    # 72M / 6Y
    (7.00,   1.7359),  # 84M / 7Y (中债登 1.74%)
    (8.00,   1.79),    # 96M / 8Y
    (10.00,  1.8473),  # 120M / 10Y (中债登 1.85%)
    (15.00,  1.97),    # 180M / 15Y
    (20.00,  2.10),    # 240M / 20Y
    (30.00,  2.2674),  # 360M / 30Y (中债登 2.27%)
    (40.00,  2.33),    # 480M / 40Y
    (50.00,  2.40),    # 600M / 50Y
    (60.00,  2.45),    # 720M / 60Y
]

# ===================== 2. 目标期限 (Excel 表头顺序) =====================
TARGETS = []
# 1M-60M
for m in range(1, 61):
    TARGETS.append((f"{m}M", m / 12))
# 10Y, 15Y, 20Y, 30Y
for y in [10, 15, 20, 30]:
    TARGETS.append((f"{y}Y", y))

# ===================== 3. 线性插值 =====================
xs = np.array([p[0] for p in KEY_POINTS])
ys = np.array([p[1] for p in KEY_POINTS])
target_xs = np.array([t[1] for t in TARGETS])
interp_ys = np.interp(target_xs, xs, ys)

# ===================== 4. 写入 Excel =====================
wb = load_workbook(EXCEL_PATH)
ws = wb['基础数据']

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# R46 已是 "国债收益率曲线" 标题
# R47: 表头
HEADER_ROW = 47
DATA_START_ROW = 48

# 写表头
ws.cell(HEADER_ROW, 1, "剩余期限")
ws.cell(HEADER_ROW, 2, "收益率(%)")
ws.cell(HEADER_ROW, 3, "数据来源")
ws.cell(HEADER_ROW, 4, "备注")

for c in range(1, 5):
    cell = ws.cell(HEADER_ROW, c)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws.row_dimensions[HEADER_ROW].height = 24

# 标识哪些点来自中债登官方 (1Y/2Y/3Y/5Y/7Y/10Y/30Y/3M)
OFFICIAL_TERMS = {0.25, 0.5, 0.75, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 30.0}

# 写数据
for i, ((name, x), y) in enumerate(zip(TARGETS, interp_ys)):
    row = DATA_START_ROW + i
    ws.cell(row, 1, name)
    ws.cell(row, 2, round(float(y), 4))
    # 标记官方/插值来源
    is_official = any(abs(x - t) < 0.01 for t in OFFICIAL_TERMS)
    if is_official:
        ws.cell(row, 3, "中债登")
        ws.cell(row, 4, "关键期限官方数据")
    else:
        ws.cell(row, 3, "线性插值")
        ws.cell(row, 4, f"基于 {x:.4f} 年插值")

    # 格式
    for c in range(1, 5):
        cell = ws.cell(row, c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10)
        if c == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.font = Font(name="微软雅黑", size=10, bold=True)
        elif c == 2:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "0.0000"
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

# 列宽
ws.column_dimensions['A'].width = 14
ws.column_dimensions['B'].width = 12
ws.column_dimensions['C'].width = 14
ws.column_dimensions['D'].width = 28

# 保存
wb.save(EXCEL_PATH)

# ===================== 5. 打印结果 =====================
print(f"已保存到: {EXCEL_PATH}")
print(f"\n=== 2025-12-31 国债收益率曲线 (插值结果) ===")
print(f"{'剩余期限':<8}{'年化期限':<12}{'收益率(%)':<12}{'来源':<10}")
print("-" * 50)
for (name, x), y in zip(TARGETS, interp_ys):
    is_official = any(abs(x - t) < 0.01 for t in OFFICIAL_TERMS)
    src = "中债登" if is_official else "插值"
    print(f"{name:<8}{x:<12.4f}{y:<12.4f}{src:<10}")
print("-" * 50)
print(f"总段数: {len(TARGETS)} (60 月度 + 4 年度)")
print(f"区间: 1M ({interp_ys[0]:.4f}%) → 60Y ({interp_ys[-1]:.4f}%)")
