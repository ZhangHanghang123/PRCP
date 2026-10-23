"""K 列现值 v6: 优化折现因子辅助区布局

v5: 折现因子在 B113-B176 (公式), K 列是数值
v6: 增加月度/年度分块标题, 颜色标记
"""

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_PATH = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v4.xlsx"

# ===================== 1. 加载 =====================
wb = load_workbook(EXCEL_PATH)
ws = wb['基础数据']

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===================== 2. 重新整理辅助区 =====================
# 布局:
# R112: 表头 (A: 名称, B: 公式, C: 引用)
# R113: 月度分块标题 (合并)
# R114-R173: 60 月度折现因子
# R174: 年度分块标题 (合并)
# R175-R178: 4 年度折现因子

# Unmerge 之前可能合并的单元格
to_unmerge = []
for merged_range in list(ws.merged_cells.ranges):
    if merged_range.min_row >= 112 and merged_range.min_row <= 182:
        to_unmerge.append(str(merged_range))
for mr in to_unmerge:
    ws.unmerge_cells(mr)

# 清空旧的辅助区
for r in range(112, 183):
    for c in range(1, 6):
        cell = ws.cell(r, c)
        cell.value = None
        cell.fill = PatternFill(fill_type=None)
        cell.border = Border()
        cell.font = Font()

# 辅助区标题 (B112)
ws.cell(112, 1, "DF 名称")
ws.cell(112, 2, "折现因子公式")
ws.cell(112, 3, "引用收益率")
for c in range(1, 4):
    cell = ws.cell(112, c)
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border
ws.row_dimensions[112].height = 24

# 月度分块标题 (R113)
ws.cell(113, 1, "─── 月度折现因子 (m=1~60) ───")
ws.merge_cells("A113:C113")
ws.cell(113, 1).font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
ws.cell(113, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(113, 1).alignment = Alignment(horizontal="center", vertical="center")
ws.cell(113, 1).border = border

# 月度折现因子 (R114-R173, m=1..60)
for m in range(1, 61):
    row = 113 + m  # 114, 115, ..., 173
    rate_row = 47 + m  # B48, B49, ..., B107
    ws.cell(row, 1, f"DF {m}M")
    ws.cell(row, 2, f"=1/(1+$B${rate_row})^({m}/12)")
    ws.cell(row, 3, f"$B${rate_row}")
    for c in range(1, 4):
        cell = ws.cell(row, c)
        cell.font = Font(name="微软雅黑", size=9, color="555555")
        cell.alignment = Alignment(horizontal="center" if c in [1, 3] else "left", vertical="center")
        cell.border = border
        if c == 2:
            cell.number_format = "0.000000000"

# 年度分块标题 (R174)
ws.cell(174, 1, "─── 年度折现因子 (t=10/15/20/30) ───")
ws.merge_cells("A174:C174")
ws.cell(174, 1).font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
ws.cell(174, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(174, 1).alignment = Alignment(horizontal="center", vertical="center")
ws.cell(174, 1).border = border

# 年度折现因子 (R175-R178, t=10,15,20,30)
for i, (rate_row, t) in enumerate([(108, 10), (109, 15), (110, 20), (111, 30)]):
    row = 175 + i  # 175, 176, 177, 178
    ws.cell(row, 1, f"DF {t}Y")
    ws.cell(row, 2, f"=1/(1+$B${rate_row})^{t}")
    ws.cell(row, 3, f"$B${rate_row}")
    for c in range(1, 4):
        cell = ws.cell(row, c)
        cell.font = Font(name="微软雅黑", size=9, color="555555")
        cell.alignment = Alignment(horizontal="center" if c in [1, 3] else "left", vertical="center")
        cell.border = border
        if c == 2:
            cell.number_format = "0.000000000"

# 公式说明 (R180-R181)
ws.cell(180, 1, "通用公式: DF_t = 1 / (1 + r_t)^t")
ws.merge_cells("A180:C180")
ws.cell(180, 1).font = Font(name="微软雅黑", size=10, bold=True, color="0070C0")
ws.cell(180, 1).alignment = Alignment(horizontal="left", vertical="center")
ws.cell(180, 1).border = border

ws.cell(181, 1, "其中: r_t = 国债收益率 (B48-B111), t = 期限 (月=1~60, 年=10/15/20/30)")
ws.merge_cells("A181:C181")
ws.cell(181, 1).font = Font(name="微软雅黑", size=9, italic=True, color="555555")
ws.cell(181, 1).alignment = Alignment(horizontal="left", vertical="center")
ws.cell(181, 1).border = border

ws.cell(182, 1, "提示: WPS 打开后请按 Ctrl+Alt+F9 强制重算")
ws.merge_cells("A182:C182")
ws.cell(182, 1).font = Font(name="微软雅黑", size=9, bold=True, color="C7000B")
ws.cell(182, 1).alignment = Alignment(horizontal="left", vertical="center")
ws.cell(182, 1).border = border

# 列宽
ws.column_dimensions['A'].width = 16
ws.column_dimensions['B'].width = 28
ws.column_dimensions['C'].width = 14

# ===================== 3. K 列公式 (引用 B114-B178) =====================
# v5: 折现因子在 B113-B176, K 引用 B113-B172, B173-B176
# v6: 折现因子在 B114-B178 (R113 是分块标题, R174 是分块标题)
#       K 引用 B114-B173 (月度), B175-B178 (年度)
for r in range(4, 44):
    sid = ws.cell(r, 3).value
    if not sid or str(sid).strip() == '':
        continue
    formula = ("=SUMPRODUCT($C75:$C134,$B$114:$B$173)"
               "+C135*$B$175+C136*$B$176+C137*$B$177+C138*$B$178")
    ws.cell(r, 12, formula)  # L 列写公式 (审计用)
print("L 列公式更新: 引用 B114-B178")

# ===================== 4. 保存 =====================
wb.save(EXCEL_PATH)
print(f"已保存: {EXCEL_PATH}")

# 验证
print("\n=== 验证辅助区结构 ===")
wb2 = load_workbook(EXCEL_PATH, data_only=False)
ws2 = wb2['基础数据']
print(f"R112 表头: {ws2.cell(112, 1).value} | {ws2.cell(112, 2).value} | {ws2.cell(112, 3).value}")
print(f"R113 月度分块: {ws2.cell(113, 1).value}")
print(f"R114 DF 1M: {ws2.cell(114, 1).value} | {ws2.cell(114, 2).value} | {ws2.cell(114, 3).value}")
print(f"R173 DF 60M: {ws2.cell(173, 1).value} | {ws2.cell(173, 2).value} | {ws2.cell(173, 3).value}")
print(f"R174 年度分块: {ws2.cell(174, 1).value}")
print(f"R175 DF 10Y: {ws2.cell(175, 1).value} | {ws2.cell(175, 2).value} | {ws2.cell(175, 3).value}")
print(f"R178 DF 30Y: {ws2.cell(178, 1).value} | {ws2.cell(178, 2).value} | {ws2.cell(178, 3).value}")
print(f"R180 公式: {ws2.cell(180, 1).value}")
