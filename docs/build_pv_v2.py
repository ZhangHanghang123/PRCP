"""K 列现值公式 v2 (辅助列方案)

问题: 64 项加法公式 (1438 字符) 在某些 Excel/WPS 版本中触发 #VALUE!
解决: 把 64 个折现因子存储在 B113-B176 辅助列, K 列公式简化为:
    = SUMPRODUCT(C75:C134, $B$113:$B$172) + C135*$B$173 + C136*$B$174 + C137*$B$175 + C138*$B$176
"""

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_PATH = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231.xlsx"

# ===================== 1. 加载 Excel =====================
wb = load_workbook(EXCEL_PATH)
ws = wb['基础数据']

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===================== 2. 写入辅助列 (折现因子) =====================
# B113 表头
ws.cell(112, 2, "折现因子辅助区")  # R112
ws.cell(112, 2).font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
ws.cell(112, 2).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(112, 2).alignment = Alignment(horizontal="center", vertical="center")

# 60 月度折现因子: 1/(1 + r_t)^(m/12)
# 折现因子行: B113 (m=1) ~ B172 (m=60)
for m in range(1, 61):
    row = 112 + m  # 113, 114, ..., 172
    rate_row = 47 + m  # 48, 49, ..., 107
    formula = f"=1/(1+$B${rate_row})^({m}/12)"
    ws.cell(row, 2, formula)
    ws.cell(row, 2).font = Font(name="微软雅黑", size=9, color="555555")
    ws.cell(row, 2).number_format = "0.000000000"

# 4 个年度折现因子
# B173 (10Y), B174 (15Y), B175 (20Y), B176 (30Y)
annual_data = [
    (173, 108, 10),  # 10Y
    (174, 109, 15),  # 15Y
    (175, 110, 20),  # 20Y
    (176, 111, 30),  # 30Y
]
for df_row, rate_row, t in annual_data:
    formula = f"=1/(1+$B${rate_row})^{t}"
    ws.cell(df_row, 2, formula)
    ws.cell(df_row, 2).font = Font(name="微软雅黑", size=9, color="555555")
    ws.cell(df_row, 2).number_format = "0.000000000"

# A 列标签
for m in range(1, 61):
    row = 112 + m
    ws.cell(row, 1, f"DF {m}M")
    ws.cell(row, 1).font = Font(name="微软雅黑", size=8, color="888888")
for df_row, _, t in annual_data:
    ws.cell(df_row, 1, f"DF {t}Y")
    ws.cell(df_row, 1).font = Font(name="微软雅黑", size=8, color="888888")

# ===================== 3. K 列公式 (简化版) =====================
# K列 = SUMPRODUCT(C75:C134, 折现因子) + C135*DF_10Y + C136*DF_15Y + C137*DF_20Y + C138*DF_30Y
def build_pv_formula_v2(row):
    """K 列现值公式 (v2 简化版)"""
    formula = (
        f"=SUMPRODUCT($C75:$C134,$B$113:$B$172)"
        f"+C135*$B$173+C136*$B$174+C137*$B$175+C138*$B$176"
    )
    return formula

# 删除旧公式, 写入新公式
for r in range(4, 44):
    sid = ws.cell(r, 3).value
    if not sid or str(sid).strip() == '':
        continue

    formula = build_pv_formula_v2(r)
    ws.cell(r, 11, formula)

    # 格式化
    cell = ws.cell(r, 11)
    cell.font = Font(name="微软雅黑", size=10, color="0070C0")
    cell.alignment = Alignment(horizontal="right", vertical="center")
    cell.number_format = "#,##0.00"
    cell.border = border

# K3 表头格式
ws.cell(3, 11).font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
ws.cell(3, 11).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(3, 11).alignment = Alignment(horizontal="center", vertical="center")
ws.cell(3, 11).border = border

# 列宽
ws.column_dimensions['K'].width = 20

# 保存
wb.save(EXCEL_PATH)

print(f"已保存到: {EXCEL_PATH}")
print(f"K 列公式长度: {len(build_pv_formula_v2(7))} 字符")
print(f"辅助折现因子: B113-B172 (60 月度) + B173-B176 (4 年度)")

# ===================== 4. Python 验证 =====================
print("\n=== Python 验证 (R7, R22, R29, R33) ===")
wb2 = load_workbook(EXCEL_PATH, data_only=True)
ws2 = wb2['基础数据']

# 收益率
rates = [ws2.cell(r, 2).value or 0 for r in range(48, 112)]

# 折现因子
df_monthly = [1/(1 + rates[m-1]/100)**(m/12) for m in range(1, 61)]
df_annual = [1/(1 + rates[60+i]/100)**t for i, t in enumerate([10, 15, 20, 30])]

for r in [4, 7, 22, 29, 33, 38]:
    sid = ws2.cell(r, 3).value
    if not sid:
        continue
    name = (ws2.cell(r, 4).value or '').strip()[:20]
    cf = [ws2.cell(r, c).value or 0 for c in range(75, 139)]
    # 计算 PV
    monthly_pv = sum(cf[i] * df_monthly[i] for i in range(60))
    annual_pv = sum(cf[60+i] * df_annual[i] for i in range(4))
    total = monthly_pv + annual_pv
    print(f"  R{r} {name:<22} PV = {total/1e8:>14.2f} 亿元 (公式应为 {len(build_pv_formula_v2(r))} 字符)")
