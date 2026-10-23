"""K 列现值 v4 (直接写入计算后的数值)

问题: v2/v3 公式在 WPS 中 SUMPRODUCT 数组无法正确计算
解决: 用 Python 直接计算所有 38 个账户的 PV, 直接写入 K 列数值
同时保留 B113-B176 折现因子 (硬编码), 方便用户回溯
"""

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

EXCEL_PATH = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v4.xlsx"

# ===================== 1. 加载 Excel =====================
wb = load_workbook(EXCEL_PATH)
ws = wb['基础数据']

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===================== 2. 读取 B113-B176 折现因子 =====================
df_monthly = [ws.cell(112 + m, 2).value or 0 for m in range(1, 61)]
df_annual = [ws.cell(173 + i, 2).value or 0 for i in range(4)]

# 重新计算 (确保 B113-B176 是 float 数值)
rates = [ws.cell(r, 2).value or 0 for r in range(48, 112)]
df_monthly = [1 / (1 + rates[m-1] / 100) ** (m / 12) for m in range(1, 61)]
df_annual = [1 / (1 + rates[60 + i] / 100) ** t for i, t in enumerate([10, 15, 20, 30])]

print("=== 折现因子 (重新计算并写入) ===")
print(f"1M: {df_monthly[0]:.6f}")
print(f"12M: {df_monthly[11]:.6f}")
print(f"60M: {df_monthly[59]:.6f}")
print(f"10Y: {df_annual[0]:.6f}")
print(f"30Y: {df_annual[3]:.6f}")

# 写硬编码折现因子 (确保 B113-B176 是 float 不是公式)
ws.cell(112, 2, "折现因子辅助区")
ws.cell(112, 2).font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
ws.cell(112, 2).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(112, 2).alignment = Alignment(horizontal="center", vertical="center")

for m in range(1, 61):
    row = 112 + m
    ws.cell(row, 2, df_monthly[m-1])
    ws.cell(row, 2).font = Font(name="微软雅黑", size=9, color="555555")
    ws.cell(row, 2).number_format = "0.000000000"
    ws.cell(row, 2).border = border
    ws.cell(row, 1, f"DF {m}M")
    ws.cell(row, 1).font = Font(name="微软雅黑", size=8, color="888888")

for i, t in enumerate([10, 15, 20, 30]):
    row = 173 + i
    ws.cell(row, 2, df_annual[i])
    ws.cell(row, 2).font = Font(name="微软雅黑", size=9, color="555555")
    ws.cell(row, 2).number_format = "0.000000000"
    ws.cell(row, 2).border = border
    ws.cell(row, 1, f"DF {t}Y")
    ws.cell(row, 1).font = Font(name="微软雅黑", size=8, color="888888")

# ===================== 3. K 列直接写入 PV 数值 (不用公式) =====================
print("\n=== K 列写入 PV 数值 (R4-R43) ===")
for r in range(4, 44):
    sid = ws.cell(r, 3).value
    if not sid or str(sid).strip() == '':
        continue

    name = (ws.cell(r, 4).value or '').strip()[:22]
    cf = [ws.cell(r, c).value or 0 for c in range(75, 139)]

    # 计算 PV
    monthly_pv = sum(cf[i] * df_monthly[i] for i in range(60))
    annual_pv = sum(cf[60 + i] * df_annual[i] for i in range(4))
    total_pv = monthly_pv + annual_pv

    # 写入 K 列 (数值, 不是公式)
    ws.cell(r, 11, total_pv)
    cell = ws.cell(r, 11)
    cell.font = Font(name="微软雅黑", size=10, color="0070C0", bold=True)
    cell.alignment = Alignment(horizontal="right", vertical="center")
    cell.number_format = "#,##0.00"
    cell.border = border

    print(f"  R{r} {name:<22} PV = {total_pv/1e8:>14.2f} 亿元")

# K3 表头
ws.cell(3, 11).font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
ws.cell(3, 11).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(3, 11).alignment = Alignment(horizontal="center", vertical="center")
ws.cell(3, 11).border = border

ws.column_dimensions['K'].width = 20

# ===================== 4. L 列写公式 (可追溯) =====================
# L 列写公式, 用户可以审计
# L3 表头
ws.cell(3, 12, "PV 公式(可审计)")
ws.cell(3, 12).font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
ws.cell(3, 12).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(3, 12).alignment = Alignment(horizontal="center", vertical="center")
ws.cell(3, 12).border = border

# L 列公式 (简化, 不带 SUMPRODUCT)
for r in range(4, 44):
    sid = ws.cell(r, 3).value
    if not sid or str(sid).strip() == '':
        continue

    # 简化公式: C75*B113 + C76*B114 + ... (每项是 Cxx*Bxx)
    parts = []
    for m in range(1, 61):
        parts.append(f"C{74+m}*B{112+m}")
    for i, t in enumerate([10, 15, 20, 30]):
        parts.append(f"C{135+i}*B{173+i}")

    formula = "=" + "+".join(parts)
    ws.cell(r, 12, formula)
    cell = ws.cell(r, 12)
    cell.font = Font(name="微软雅黑", size=9, color="888888")
    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)
    cell.number_format = "0"
    cell.border = border

ws.column_dimensions['L'].width = 80

# ===================== 5. 保存 =====================
wb.save(EXCEL_PATH)
print(f"\n已保存: {EXCEL_PATH}")
print("K 列: 直接写入 PV 数值 (无公式, 立即可见)")
print("L 列: 60+4 项乘法公式 (可审计)")
