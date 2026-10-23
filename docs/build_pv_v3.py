"""K 列现值公式 v3 (硬编码折现因子)

问题: v2 中 B113-B176 折现因子公式在 WPS 中未触发计算, K 列返回 0
解决: 直接写入计算好的折现因子数值 (不用公式), K 列 SUMPRODUCT 正常工作
"""

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_PATH = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231.xlsx"

# ===================== 1. 读取 B48-B111 收益率 =====================
wb = load_workbook(EXCEL_PATH, data_only=True)
ws = wb['基础数据']

rates = []  # 64 个收益率 (%)
for r in range(48, 112):
    rates.append(ws.cell(r, 2).value or 0)

# ===================== 2. 计算 64 个折现因子 =====================
# 月度: 1/(1+r)^(m/12) for m=1..60
# 年度: 1/(1+r)^t for t=10,15,20,30
df_monthly = []
for m in range(1, 61):
    r = rates[m-1] / 100
    df_monthly.append(1 / (1 + r) ** (m / 12))

df_annual = []
for t in [10, 15, 20, 30]:
    r = rates[60 + [10, 15, 20, 30].index(t)] / 100
    df_annual.append(1 / (1 + r) ** t)

print("=== 折现因子 (硬编码) ===")
print(f"1M: {df_monthly[0]:.6f}")
print(f"12M: {df_monthly[11]:.6f}")
print(f"60M: {df_monthly[59]:.6f}")
print(f"10Y: {df_annual[0]:.6f}")
print(f"30Y: {df_annual[3]:.6f}")

# ===================== 3. 写入 B113-B176 硬编码数值 =====================
wb2 = load_workbook(EXCEL_PATH)
ws2 = wb2['基础数据']

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# 标题
ws2.cell(112, 2, "折现因子辅助区")
ws2.cell(112, 2).font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
ws2.cell(112, 2).fill = PatternFill("solid", fgColor="C7000B")
ws2.cell(112, 2).alignment = Alignment(horizontal="center", vertical="center")

# 60 月度折现因子
for m in range(1, 61):
    row = 112 + m
    ws2.cell(row, 2, df_monthly[m-1])
    ws2.cell(row, 2).font = Font(name="微软雅黑", size=9, color="555555")
    ws2.cell(row, 2).number_format = "0.000000000"
    ws2.cell(row, 2).border = border
    ws2.cell(row, 1, f"DF {m}M")
    ws2.cell(row, 1).font = Font(name="微软雅黑", size=8, color="888888")

# 4 个年度折现因子
for i, t in enumerate([10, 15, 20, 30]):
    row = 173 + i
    ws2.cell(row, 2, df_annual[i])
    ws2.cell(row, 2).font = Font(name="微软雅黑", size=9, color="555555")
    ws2.cell(row, 2).number_format = "0.000000000"
    ws2.cell(row, 2).border = border
    ws2.cell(row, 1, f"DF {t}Y")
    ws2.cell(row, 1).font = Font(name="微软雅黑", size=8, color="888888")

# ===================== 4. K 列公式 (不变, 引用硬编码的折现因子) =====================
def build_pv_formula(row):
    return ("=SUMPRODUCT($C75:$C134,$B$113:$B$172)"
            "+C135*$B$173+C136*$B$174+C137*$B$175+C138*$B$176")

for r in range(4, 44):
    sid = ws2.cell(r, 3).value
    if not sid or str(sid).strip() == '':
        continue

    formula = build_pv_formula(r)
    ws2.cell(r, 11, formula)

    cell = ws2.cell(r, 11)
    cell.font = Font(name="微软雅黑", size=10, color="0070C0")
    cell.alignment = Alignment(horizontal="right", vertical="center")
    cell.number_format = "#,##0.00"
    cell.border = border

# K3 表头格式
ws2.cell(3, 11).font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
ws2.cell(3, 11).fill = PatternFill("solid", fgColor="C7000B")
ws2.cell(3, 11).alignment = Alignment(horizontal="center", vertical="center")
ws2.cell(3, 11).border = border

ws2.column_dimensions['K'].width = 20

wb2.save(EXCEL_PATH)
print(f"\n已保存: {EXCEL_PATH}")
print(f"K 列公式长度: {len(build_pv_formula(4))} 字符")
print(f"折现因子 B113-B172 (60 月度) + B173-B176 (4 年度) 全部硬编码数值")

# ===================== 5. 验证 =====================
print("\n=== Python 验证 ===")
wb3 = load_workbook(EXCEL_PATH, data_only=True)
ws3 = wb3['基础数据']

for r in [4, 7, 17, 22, 29, 33]:
    sid = ws3.cell(r, 3).value
    if not sid:
        continue
    name = (ws3.cell(r, 4).value or '').strip()[:22]
    cf = [ws3.cell(r, c).value or 0 for c in range(75, 139)]
    monthly_pv = sum(cf[i] * df_monthly[i] for i in range(60))
    annual_pv = sum(cf[60+i] * df_annual[i] for i in range(4))
    total = monthly_pv + annual_pv
    print(f"  R{r} {name:<22} PV = {total/1e8:>14.2f} 亿元")
