"""为 prcp_basic_20251231.xlsx 添加 K 列现值公式

公式: K列(现值) = Σ_{t=1M..60M, 10Y, 15Y, 20Y, 30Y} CF_t / (1 + r_t)^t
- CF_t: 剩余·t 列 (C75-C138) 的现金流金额
- r_t:  R48-R111 表格中的国债收益率
- t:    期限 (月: t/12, 年: t)

Excel 公式策略:
- 60 个月度期限用 SUMPRODUCT 数组公式
- 4 个年度期限用单项除法 (因为 t 整数)
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

# ===================== 2. 设计 K 列公式 =====================
# 剩余·1M 在 C75, 剩余·60M 在 C134
# 剩余·10Y 在 C135, 剩余·15Y 在 C136, 剩余·20Y 在 C137, 剩余·30Y 在 C138
# 收益率: B48 (1M) ~ B107 (60M), B108 (10Y), B109 (15Y), B110 (20Y), B111 (30Y)

def build_pv_formula(row):
    """
    为指定行生成 K 列现值公式 (展开式, 避免 ROW 数组)

    60 月度: SUM(C75/(1+$B$48)^(1/12), C76/(1+$B$49)^(2/12), ..., C134/(1+$B$107)^(60/12))
    4 年度:  C135/(1+$B$108)^10 + C136/(1+$B$109)^15 + C137/(1+$B$110)^20 + C138/(1+$B$111)^30
    """
    parts = []
    # 60 月度期限 (1M-60M)
    # 现金流列: C75 (1M) ~ C134 (60M)
    # 收益率行: B48 (1M) ~ B107 (60M)
    for m in range(1, 61):
        cf_col = 74 + m  # 75, 76, ..., 134
        rate_row = 47 + m  # 48, 49, ..., 107
        # 折现因子: (1 + rate)^(m/12)
        parts.append(f"C{cf_col}/(1+$B${rate_row})^({m}/12)")

    # 4 个年度 (10Y, 15Y, 20Y, 30Y)
    # 现金流列: C135 (10Y) ~ C138 (30Y)
    # 收益率行: B108 (10Y) ~ B111 (30Y)
    annual_data = [
        (135, 108, 10),  # 10Y
        (136, 109, 15),  # 15Y
        (137, 110, 20),  # 20Y
        (138, 111, 30),  # 30Y
    ]
    for cf_col, rate_row, t in annual_data:
        parts.append(f"C{cf_col}/(1+$B${rate_row})^({t})")

    return "=" + "+".join(parts)

# ===================== 3. 对 R4-R43 每一行写入 K 列公式 =====================
# 跳过空行 (R28, R42 等)
processed = 0
for r in range(4, 44):  # R4-R43
    is_leaf = ws.cell(r, 7).value  # G 列 是否末级
    # 检查是否数据行 (有账户编码)
    sid = ws.cell(r, 3).value
    if not sid or str(sid).strip() == '':
        # 空行, 跳过
        continue

    formula = build_pv_formula(r)
    ws.cell(r, 11, formula)

    # 格式化
    cell = ws.cell(r, 11)
    cell.font = Font(name="微软雅黑", size=10, color="0070C0")
    cell.alignment = Alignment(horizontal="right", vertical="center")
    cell.number_format = "#,##0.00"
    cell.border = border

    processed += 1

# 设置 K 列宽度
ws.column_dimensions['K'].width = 20

# K3 表头加格式
ws.cell(3, 11).font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
ws.cell(3, 11).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(3, 11).alignment = Alignment(horizontal="center", vertical="center")
ws.cell(3, 11).border = border

# 保存
wb.save(EXCEL_PATH)

print(f"已为 {processed} 个账户行写入 K 列现值公式")
print(f"保存到: {EXCEL_PATH}")

# ===================== 4. 打印公式样例 =====================
print("\n=== K 列公式样例 ===")
sample_formula = build_pv_formula(7)
print(f"R7 公式长度: {len(sample_formula)} 字符")
print(f"R7 公式样例: {sample_formula[:300]}...")

# ===================== 5. 验证 (用 pycel 评估) =====================
print("\n=== 公式验证 (pycel 评估 R7) ===")
try:
    from pycel import ExcelCompiler
    ec = ExcelCompiler(filename=EXCEL_PATH)
    # R7: 1.1.对公一般贷款
    pv_r7 = ec.evaluate("基础数据!K7")
    if pv_r7 is not None:
        print(f"R7 (1.1对公一般贷款) PV: {pv_r7/1e8:.2f} 亿元")

    # R20: 3.1.FVTPL类资产
    pv_r20 = ec.evaluate("基础数据!K20")
    if pv_r20 is not None:
        print(f"R20 (3.1FVTPL类资产) PV: {pv_r20/1e8:.2f} 亿元")

    # R33: 1.1.1对公活期存款
    pv_r33 = ec.evaluate("基础数据!K33")
    if pv_r33 is not None:
        print(f"R33 (1.1.1对公活期存款) PV: {pv_r33/1e8:.2f} 亿元")

    # 总负债 R29
    pv_r29 = ec.evaluate("基础数据!K29")
    if pv_r29 is not None:
        print(f"R29 (总负债) PV: {pv_r29/1e8:.2f} 亿元")
except Exception as e:
    print(f"pycel 验证失败: {e}")
