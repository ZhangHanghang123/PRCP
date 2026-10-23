# -*- coding: utf-8 -*-
"""
中信银行 同业负债比 计量模版
============================
沿用 LCR/NSFR/CET1/EVE/ROE/NIM 6 指标的 57 行账户册结构
公式: 同业负债比 = 同业负债 / 总负债
  - 分子 (同业负债): 货币市场同业拆入 + 债券回购 + NCD + 同业存款 + 票据转贴现
  - 分母 (总负债): 24 个负债项目之和
  - 监管红线: ≤ 33.33%
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUTPUT = r"C:/银行经营/PRCP/docs/v2/同业负债比.xlsx"

# ============================================================
# 57 行账户册 (沿用 LCR 模板)
# 格式: (code, name, is_leaf, balance, is_ibl, ibl_factor, ibl_comment)
# is_ibl: 1=同业负债, 0=非同业负债
# ibl_factor: 折算系数 (0 或 1)
# 总负债标记: 所有 24 项负债都是总负债 (用 in_liabilities 区分)
# ============================================================
ACCOUNTS = [
    # S01 资产 (30 项)
    ('S010000000000', '总资产', '否', None, 0, 0, '汇总节点不参与计算'),
    ('S010100000000', '（一）人民币小计', '否', None, 0, 0, '汇总节点'),
    ('S010101000000', '1.境内人民币各项贷款', '否', 8380847647531.74, 0, 0, '汇总节点'),
    ('S010101010000', '1.1.对公一般贷款', '是', 2945272044075.94, 0, 0, '资产项 不参与'),
    ('S010101020000', '1.2.个人贷款', '是', 1828186569200.79, 0, 0, '资产项 不参与'),
    ('S010101030000', '1.3.信用卡贷款', '是', 444525501384.64, 0, 0, '资产项 不参与'),
    ('S010101040000', '1.4.票据贴现', '是', 201340076281.32, 0, 0, '资产项 不参与'),
    ('S010101050000', '1.5.非银贷款', '是', 348478250000, 0, 0, '资产项 不参与'),
    ('S010102000000', '2.人民币非信贷类业务', '否', 2613045206589.05, 0, 0, '汇总节点'),
    ('S010102010000', '2.1.债券投资', '否', 1794400523623.64, 0, 0, '汇总节点'),
    ('S010102010100', '2.1.1金市自营债券', '否', 1184382566128.63, 0, 0, '汇总节点'),
    ('S010102010101', '2.1.1.1AC', '是', 543980069724.63, 0, 0, '资产项'),
    ('S010102010102', '2.1.1.2FVOCI', '是', 640402496404, 0, 0, '资产项'),
    ('S010102010103', '2.1.1.3FVTPL', '是', 50000000000, 0, 0, '资产项'),
    ('S010102010200', '2.1.2司库债券', '否', 610017957495.01, 0, 0, '汇总节点'),
    ('S010102010201', '2.1.2.1AC', '是', 566351367717.5, 0, 0, '资产项'),
    ('S010102010202', '2.1.2.2FVOCI', '是', 43666589777.51, 0, 0, '资产项'),
    ('S010102010203', '2.1.2.3FVTPL', '是', 30000000000, 0, 0, '资产项'),
    ('S010102020000', '2.2.结构化融资', '是', 205172333337.52, 0, 0, '资产项'),
    ('S010102030000', '2.3.同业资产（不含拆放非银）', '是', 248117663093.33, 0, 0, '资产项 同业资产 非同业负债'),
    ('S010102040000', '2.4.存款准备金', '是', 365354686534.56, 0, 0, '资产项'),
    ('S010103000000', '3.人民币非生息资产', '否', 867778998074.61, 0, 0, '汇总节点'),
    ('S010103010000', '3.1.FVTPL类资产', '是', 640262452968.54, 0, 0, '资产项'),
    ('S010103020000', '3.2.其他非生息资产', '否', 227516545106.07, 0, 0, '汇总节点'),
    ('S010103020100', '3.2.1. 其中：现金', '是', 127516545106, 0, 0, '资产项'),
    ('S010103020200', '3.2.2. 其中：其它', '是', 100000000000, 0, 0, '资产项'),
    ('S010200000000', '（二）外币小计（美元）', '否', None, 0, 0, '汇总节点'),
    ('S010201000000', '1.外币贷款', '是', 80000000000, 0, 0, '资产项'),
    ('S010202000000', '2.外币非信贷资产', '否', None, 0, 0, '汇总节点'),
    ('S010202010000', '2.1.外币债券', '是', 35000000000, 0, 0, '资产项'),
    ('S010202020000', '2.2.同业资产', '是', 25000000000, 0, 0, '资产项 同业资产 非同业负债'),
    ('S010203000000', '3.外币非生息资产', '是', 10000000000, 0, 0, '资产项'),
    # S02 负债 (24 项) - 重点: 同业负债
    ('S020000000000', '总负债', '否', None, 0, 0, '汇总节点'),
    ('S020100000000', '（一）人民币小计', '否', None, 0, 0, '汇总节点'),
    ('S020101000000', '1.境内人民币自营存款', '否', None, 0, 0, '汇总节点'),
    ('S020101010000', '1.1.对公存款', '否', 4222682106931.64, 0, 0, '汇总节点'),
    ('S020101010100', '1.1.1对公活期存款', '是', 2486212417437.03, 0, 0, '客户存款 不计入同业负债'),
    ('S020101010200', '1.1.2对公定期存款', '是', 1736469689494.61, 0, 0, '客户存款 不计入同业负债'),
    ('S020101020000', '1.2.零售存款', '否', 2169431482604.05, 0, 0, '汇总节点'),
    ('S020101020100', '1.2.1零售活期存款', '是', 434867199487.65, 0, 0, '客户存款 不计入同业负债'),
    ('S020101020200', '1.2.2零售定期存款', '是', 1734564283116.4, 0, 0, '客户存款 不计入同业负债'),
    ('S020102000000', '2.人民币市场化负债', '否', None, 0, 0, '汇总节点'),
    ('S020102010000', '2.2.1同业负债', '否', None, 0, 0, '汇总节点 (同业负债 5 子项)'),
    ('S020102010100', '2.2.1.1货币市场同业拆入', '是', 32988348999.99, 1, 1, '⭐同业负债: 货币市场同业拆入 100% 计入'),
    ('S020102010200', '2.2.1.2货币市场债券回购', '是', 95875096000, 1, 1, '⭐同业负债: 货币市场债券回购 100% 计入'),
    ('S020102010300', '2.2.1.3同业存单（NCD）', '是', 932237942418.69, 1, 1, '⭐同业负债: 同业存单 NCD 100% 计入'),
    ('S020102010400', '2.2.1.4同业存款', '是', 915605054241.89, 1, 1, '⭐同业负债: 同业存款 100% 计入'),
    ('S020102010500', '2.2.1.5票据转贴现回购', '是', 1000000000, 1, 1, '⭐同业负债: 票据转贴现 100% 计入'),
    ('S020102020000', '2.2.2央行借款', '否', None, 0, 0, '汇总节点 (央行借款 不计入同业负债)'),
    ('S020102020100', '2.2.2.1公开市场回购（买断）', '是', 353887790000, 0, 0, '央行借款 不计入同业负债'),
    ('S020102020200', '2.2.2.2中期借贷便利（MLF）', '是', 160370000000, 0, 0, '央行借款 不计入同业负债'),
    ('S020102020300', '2.2.2.3结构性货币政策工具', '是', 42212093203.19, 0, 0, '央行借款 不计入同业负债'),
    ('S020102020400', '2.2.2.4票据再贴现回购', '是', 1525214781.84, 0, 0, '央行借款 不计入同业负债'),
    ('S020200000000', '（二）外币小计（美元）', '否', None, 0, 0, '汇总节点'),
    ('S020201000000', '1.外币存款', '是', 150000000000, 0, 0, '外币存款 不计入同业负债'),
    ('S020202000000', '2.外币市场化负债', '是', 80000000000, 0, 0, '外币市场化 不计入同业负债'),
    # S03 权益 (1 项)
    ('S030000000000', '所有者权益', '是', 786217000000, 0, 0, '权益项 不计入同业负债'),
    # 2 行空 (与 LCR 模板一致)
    ('', '', '', None, 0, 0, ''),
    ('', '', '', None, 0, 0, ''),
]

# ============================================================
# 创建 Excel
# ============================================================
wb = openpyxl.Workbook()
wb.remove(wb.active)

thin = Side(border_style="thin", color="DDDDDD")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

# ===== Sheet 1: 同业负债比项目明细 =====
ws1 = wb.create_sheet("同业负债比项目明细")

ws1.merge_cells("A1:H1")
ws1["A1"] = "中信银行 同业负债比 计量模版（项目明细）"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:H2")
ws1["A2"] = "公式: 同业负债比 = 同业负债 / 总负债 | 分子: 货币市场同业拆入+债券回购+NCD+同业存款+票据转贴现 | 分母: 24 项负债之和 | 监管红线 ≤ 33.33%"
ws1["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[2].height = 22

# 表头
headers = ["项目序号", "项目名称", "是否末级节点", "当前余额（人民币元）",
           "是否同业负债", "同业负债折算系数", "计入同业负债额", "IBL 规则说明"]
for col, h in enumerate(headers, 1):
    cell = ws1.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws1.row_dimensions[4].height = 32

# 写账户
for i, (code, name, is_leaf, balance, is_ibl, factor, comment) in enumerate(ACCOUNTS, 5):
    # 公式: 计入同业负债额 = IF(E=是, D*F, 0)
    formula = f'=IF(AND(E{i}="是",F{i}=1),D{i}*F{i},0)'

    ws1.cell(row=i, column=1, value=code)
    ws1.cell(row=i, column=2, value=name)
    ws1.cell(row=i, column=3, value=is_leaf)
    if balance is not None:
        ws1.cell(row=i, column=4, value=balance)
    ws1.cell(row=i, column=5, value="是" if is_ibl == 1 else "否")
    if is_ibl == 1:
        ws1.cell(row=i, column=6, value=factor)
    else:
        ws1.cell(row=i, column=6, value="-")
    ws1.cell(row=i, column=7, value=formula)
    ws1.cell(row=i, column=8, value=comment)

    # 格式
    is_ibl_row = is_ibl == 1
    is_liab = code.startswith('S02')
    for c in range(1, 9):
        cell = ws1.cell(row=i, column=c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10)
        if c in [3, 5]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif c == 6:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif c == 7:
            cell.alignment = Alignment(horizontal="right", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left" if c in [2, 8] else "center", vertical="center", wrap_text=(c == 8))
        if c == 4 and isinstance(balance, (int, float)):
            cell.number_format = '#,##0.00'
        if c == 7 and is_ibl_row:
            cell.fill = PatternFill("solid", fgColor="FFE082")
        if c == 5 and is_ibl_row:
            cell.fill = PatternFill("solid", fgColor="C8E6C9")
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="1B5E20")
        # 汇总行
        if is_leaf == '否':
            cell.fill = PatternFill("solid", fgColor="F5F5F5")

# 列宽
widths = [18, 28, 12, 22, 12, 18, 22, 50]
for i, w in enumerate(widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.freeze_panes = "A5"

# ===== Sheet 2: 同业负债比计算 =====
ws2 = wb.create_sheet("同业负债比计算")

ws2.merge_cells("A1:C1")
ws2["A1"] = "中信银行 同业负债比 计算表"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 30

ws2.merge_cells("A2:C2")
ws2["A2"] = "数据基准：中信银行 2025 年末 | 单位：人民币元"
ws2["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="666666")
ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[2].height = 20

# 公式
rows = [
    ("项目", "金额（人民币元）", "占合计", None),
    ("【一、同业负债（分子）】", None, None, "header"),
    ("1. 货币市场同业拆入", "=同业负债比项目明细!D45", None, "normal"),
    ("2. 货币市场债券回购", "=同业负债比项目明细!D46", None, "normal"),
    ("3. 同业存单 (NCD)", "=同业负债比项目明细!D47", None, "normal"),
    ("4. 同业存款", "=同业负债比项目明细!D48", None, "normal"),
    ("5. 票据转贴现回购", "=同业负债比项目明细!D49", None, "normal"),
    ("同业负债合计 (A)", "=SUM(D6:D10)", "100.00%", "subtotal"),
    ("", "", "", "blank"),
    ("【二、总负债（分母）】", None, None, "header"),
    ("1. 对公活期存款", "=同业负债比项目明细!D37", None, "normal"),
    ("2. 对公定期存款", "=同业负债比项目明细!D38", None, "normal"),
    ("3. 零售活期存款", "=同业负债比项目明细!D40", None, "normal"),
    ("4. 零售定期存款", "=同业负债比项目明细!D41", None, "normal"),
    ("5. 同业负债 5 项合计", "=同业负债比项目明细!D45+同业负债比项目明细!D46+同业负债比项目明细!D47+同业负债比项目明细!D48+同业负债比项目明细!D49", None, "normal"),
    ("6. 央行借款 4 项", "=同业负债比项目明细!D50+同业负债比项目明细!D51+同业负债比项目明细!D52+同业负债比项目明细!D53", None, "normal"),
    ("7. 外币存款", "=同业负债比项目明细!D55", None, "normal"),
    ("8. 外币市场化负债", "=同业负债比项目明细!D56", None, "normal"),
    ("总负债合计 (B)", "=SUM(D13:D20)", "100.00%", "subtotal"),
    ("", "", "", "blank"),
    ("【三、同业负债比】", None, None, "header"),
    ("同业负债比 = A / B", "=D11/D22", None, "result"),
    ("", "", "", "blank"),
    ("【四、监管检查】", None, None, "header"),
    ("监管红线", "33.33%", "≤ 33.33%", "regulatory"),
    ("当前值 vs 红线", "=IF(D27<=0.3333,\"✓ 达标\",\"✗ 超标\")", None, "check"),
    ("距红线 (缓冲)", "=(0.3333-D27)*100", "pp", "buffer"),
]

for r, (col_a, col_b, col_c, style) in enumerate(rows, 4):
    cell_a = ws2.cell(row=r, column=1, value=col_a)
    if col_b is not None:
        cell_b = ws2.cell(row=r, column=2, value=col_b)
    if col_c is not None:
        cell_c = ws2.cell(row=r, column=3, value=col_c)

    for c in range(1, 4):
        cell = ws2.cell(row=r, column=c)
        cell.font = Font(name="微软雅黑", size=10)
        cell.border = border

    if style == "header":
        ws2.merge_cells(f"A{r}:C{r}")
        cell_a.font = Font(name="微软雅黑", size=11, bold=True, color="C7000B")
        cell_a.fill = PatternFill("solid", fgColor="FFF3E0")
    elif style == "subtotal":
        cell_a.font = Font(name="微软雅黑", size=11, bold=True)
        cell_a.fill = PatternFill("solid", fgColor="FFE082")
        cell_b.font = Font(name="微软雅黑", size=11, bold=True)
        cell_b.fill = PatternFill("solid", fgColor="FFE082")
        cell_c.fill = PatternFill("solid", fgColor="FFE082")
        cell_b.number_format = '#,##0.00'
    elif style == "result":
        ws2.merge_cells(f"A{r}:A{r}")
        cell_a.font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")
        cell_a.fill = PatternFill("solid", fgColor="C7000B")
        cell_a.alignment = Alignment(horizontal="left", vertical="center")
        cell_b.font = Font(name="微软雅黑", size=14, bold=True, color="C7000B")
        cell_b.fill = PatternFill("solid", fgColor="FFE082")
        cell_b.number_format = '0.0000%'
        cell_b.alignment = Alignment(horizontal="center", vertical="center")
        cell_c.value = "★ 同业负债比 ★"
        cell_c.font = Font(name="微软雅黑", size=12, bold=True, color="C7000B")
        cell_c.fill = PatternFill("solid", fgColor="FFE082")
        ws2.row_dimensions[r].height = 28
    elif style == "regulatory":
        cell_a.font = Font(name="微软雅黑", size=11, bold=True)
        cell_b.font = Font(name="微软雅黑", size=11, bold=True, color="C7000B")
        cell_b.fill = PatternFill("solid", fgColor="FFCDD2")
    elif style == "check":
        cell_b.font = Font(name="微软雅黑", size=11, bold=True)
        cell_b.fill = PatternFill("solid", fgColor="C8E6C9")
    elif style == "buffer":
        cell_b.number_format = '0.00"pp"'
    elif style == "normal":
        if col_b and isinstance(col_b, str) and col_b.startswith("="):
            cell_b.number_format = '#,##0.00'

# 列宽
ws2.column_dimensions["A"].width = 30
ws2.column_dimensions["B"].width = 25
ws2.column_dimensions["C"].width = 18

# ===== Sheet 3: 折算依据 =====
ws3 = wb.create_sheet("折算依据")

ws3.merge_cells("A1:C1")
ws3["A1"] = "同业负债比 折算依据与监管规定"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

# 表头
ws3["A3"] = "序号"
ws3["B3"] = "项目"
ws3["C3"] = "内容/公式"
for c in range(1, 4):
    cell = ws3.cell(row=3, column=c)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border

rules = [
    (1, "指标名称", "同业负债占比 (Interbank Liability Ratio)"),
    (2, "指标代码", "IBL"),
    (3, "计算公式", "同业负债比 = 同业负债合计 / 总负债合计 × 100%"),
    (4, "分子定义", "同业负债 = 货币市场同业拆入 + 货币市场债券回购 + 同业存单 (NCD) + 同业存款 + 票据转贴现回购"),
    (5, "分母定义", "总负债 = 对公存款 + 零售存款 + 同业负债 + 央行借款 + 外币存款 + 外币市场化负债 (24 项)"),
    (6, "数据来源", "中信银行 2025 年末账户册 (ZX_COA 方案)"),
    (7, "监管规定", "银保监会《商业银行风险监管核心指标》同业负债占比 ≤ 33.33%"),
    (8, "折算系数", "同业负债 5 项: 100% 计入 | 央行借款 4 项: 0% (不计) | 客户存款: 0% (不计) | 外币: 0% (不计)"),
    (9, "中信银行实测", "2025 年末 同业负债合计 ≈ 1.98 万亿 / 总负债 ≈ 9.16 万亿 ≈ 21.6% (留有 12pp 缓冲空间)"),
    (10, "考核层级", "本行底线 ≤ 33.33% | 安全 ≤ 25% | 预警 25-30% | 危险 30-33.33% | 红线 > 33.33%"),
    (11, "业务含义", "同业负债占比反映银行对同业资金的依赖程度，过高则流动性风险集中"),
    (12, "调整建议", "保持同业负债占比 ≤ 25% 安全区间, 避免依赖同业资金"),
]

for i, (no, name, content) in enumerate(rules, 4):
    ws3.cell(row=i, column=1, value=no)
    ws3.cell(row=i, column=2, value=name)
    ws3.cell(row=i, column=3, value=content)
    for c in range(1, 4):
        cell = ws3.cell(row=i, column=c)
        cell.font = Font(name="微软雅黑", size=10)
        cell.alignment = Alignment(horizontal="center" if c == 1 else "left", vertical="center", wrap_text=True)
        cell.border = border
        if c == 1:
            cell.fill = PatternFill("solid", fgColor="F5F5F5")

# 列宽
ws3.column_dimensions["A"].width = 8
ws3.column_dimensions["B"].width = 18
ws3.column_dimensions["C"].width = 80

wb.save(OUTPUT)
print(f"已保存：{OUTPUT}")

# 验证计算
import openpyxl as op
wb2 = op.load_workbook(OUTPUT, data_only=False)
ws = wb2["同业负债比项目明细"]

total_ibl = 0
total_liab = 0
print(f"\n=== 同业负债比验证 ===")
print(f"{'项目':<28} {'余额(元)':<22} {'是否同业':<8} {'系数':<6} {'计入同业负债(元)':<22}")
print("-" * 100)
for row in range(5, 65):
    code = ws.cell(row=row, column=1).value
    name = ws.cell(row=row, column=2).value
    is_leaf = ws.cell(row=row, column=3).value
    balance = ws.cell(row=row, column=4).value
    is_ibl = ws.cell(row=row, column=5).value
    factor = ws.cell(row=row, column=6).value

    if is_leaf != "是" or not balance or not name:
        continue
    if not code or not str(code).startswith("S02"):
        continue
    is_ibl_value = 1 if is_ibl == "是" else 0
    factor_value = factor if isinstance(factor, (int, float)) else 0
    contribution = balance * factor_value if is_ibl_value else 0

    if is_ibl_value:
        total_ibl += contribution
    total_liab += balance
    print(f"{name[:24]:<28} {balance:<22,.2f} {is_ibl:<8} {factor_value:<6} {contribution:<22,.2f}")

print("-" * 100)
print(f"同业负债合计: {total_ibl:,.2f} 元 = {total_ibl/1e8:,.2f} 亿元")
print(f"总负债合计: {total_liab:,.2f} 元 = {total_liab/1e8:,.2f} 亿元")
ibl_ratio = total_ibl / total_liab
print(f"同业负债比: {ibl_ratio*100:.4f}%")
print(f"监管红线: 33.33%")
print(f"距红线: {(0.3333 - ibl_ratio)*100:.4f}pp ({'达标' if ibl_ratio <= 0.3333 else '超标'})")
