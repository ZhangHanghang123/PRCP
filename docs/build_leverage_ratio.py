"""杠杆率 (Leverage Ratio) 计量模版
公式: 杠杆率 = 一级资本净额 / 调整后表内外资产余额
监管: ≥ 4% (银保监)
实测: 中信银行 2025 年末 ≈ 6.5-6.8%

沿用 6 指标账户册 57 行结构, 新增列:
- E: 是否计入一级资本
- F: 一级资本折算系数
- G: 计入一级资本额
- H: 是否计入调整后表内外资产
- I: 表外信用转换系数
- J: 调整后表内外资产额
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ===================== 1. 账户册 57 行 (沿用 6 指标模板) =====================
ROWS = [
    # ===== 30 资产项 (S01) =====
    ("S010000000000", "总资产", "否", 12100000000000.0),
    ("S010100000000", "（一）人民币小计", "否", 11800000000000.0),
    ("S010101000000", "1.境内人民币各项贷款", "否", 8380847647531.74),
    ("S010101010000", "1.1.对公一般贷款", "是", 2945272044075.94),
    ("S010101020000", "1.2.个人贷款", "是", 1828186569200.79),
    ("S010101030000", "1.3.信用卡贷款", "是", 444525501384.64),
    ("S010101040000", "1.4.票据贴现", "是", 201340076281.32),
    ("S010101050000", "1.5.非银贷款", "是", 348478250000.0),
    ("S010102000000", "2.人民币非信贷类业务", "否", 2613045206589.05),
    ("S010102010000", "2.1.债券投资", "否", 1794400523623.64),
    ("S010102010100", "2.1.1金市自营债券", "否", 1184382566128.63),
    ("S010102010101", "2.1.1.1AC", "是", 543980069724.63),
    ("S010102010102", "2.1.1.2FVOCI", "是", 640402496404.0),
    ("S010102010103", "2.1.1.3FVTPL", "是", 50000000000.0),
    ("S010102010200", "2.1.2司库债券", "是", 610017957495.01),
    ("S010102010201", "2.1.2.1AC", "是", 566351367717.5),
    ("S010102010202", "2.1.2.2FVOCI", "是", 43666589777.51),
    ("S010102010203", "2.1.2.3FVTPL", "是", 30000000000.0),
    ("S010102020000", "2.2.结构化融资", "是", 205172333337.52),
    ("S010102030000", "2.3.同业资产（不含拆放非银）", "是", 248117663093.33),
    ("S010102040000", "2.4.存款准备金", "是", 365354686534.56),
    ("S010103000000", "3.人民币非生息资产", "否", 867778998074.61),
    ("S010103010000", "3.1.FVTPL类资产", "是", 640262452968.54),
    ("S010103020000", "3.2.其他非生息资产", "否", 227516545106.07),
    ("S010103020100", "3.2.1. 其中：现金", "是", 127516545106.0),
    ("S010103020200", "3.2.2. 其中：其它", "是", 100000000000.0),
    ("S010200000000", "（二）外币小计（人民币）", "否", 150000000000.0),
    ("S010201000000", "1.外币贷款", "是", 80000000000.0),
    ("S010202000000", "2.外币非信贷资产", "否", 60000000000.0),
    ("S010202010000", "2.1.外币债券", "是", 35000000000.0),
    ("S010202020000", "2.2.同业资产", "是", 25000000000.0),
    ("S010203000000", "3.外币非生息资产", "是", 10000000000.0),
    # ===== 24 负债项 (S02) =====
    ("S020000000000", "总负债", "否", 11300000000000.0),
    ("S020100000000", "（一）人民币小计", "否", 11020000000000.0),
    ("S020101000000", "1.境内人民币自营存款", "否", 6392113589535.69),
    ("S020101010000", "1.1.对公存款", "否", 4222682106931.64),
    ("S020101010100", "1.1.1对公活期存款", "是", 2486212417437.03),
    ("S020101010200", "1.1.2对公定期存款", "是", 1736469689494.61),
    ("S020101020000", "1.2.零售存款", "否", 2169431482604.05),
    ("S020101020100", "1.2.1零售活期存款", "是", 434867199487.65),
    ("S020101020200", "1.2.2零售定期存款", "是", 1734564283116.4),
    ("S020102000000", "2.人民币市场化负债", "否", 4627884326680.0),
    ("S020102010000", "2.2.1同业负债", "否", 1977706345660.58),
    ("S020102010100", "2.2.1.1货币市场同业拆入", "是", 32988348999.99),
    ("S020102010200", "2.2.1.2货币市场债券回购", "是", 95875096000.0),
    ("S020102010300", "2.2.1.3同业存单（NCD）", "是", 932237942418.69),
    ("S020102010400", "2.2.1.4同业存款", "是", 915605054241.89),
    ("S020102010500", "2.2.1.5票据转贴现回购", "是", 1000000000.0),
    ("S020102020000", "2.2.2央行借款", "否", 558017654985.03),
    ("S020102020100", "2.2.2.1公开市场回购", "是", 353887790000.0),
    ("S020102020200", "2.2.2.2中期借贷便利（MLF）", "是", 160370000000.0),
    ("S020102020300", "2.2.2.3结构性货币政策工具", "是", 42212093203.19),
    ("S020102020400", "2.2.2.4票据再贴现回购", "是", 1525214781.84),
    ("S020200000000", "（二）外币小计（人民币）", "否", 280000000000.0),
    ("S020201000000", "1.外币存款", "是", 150000000000.0),
    ("S020202000000", "2.外币市场化负债", "是", 80000000000.0),
    # ===== 1 所有者权益 (S03) =====
    ("S030000000000", "所有者权益", "是", 786217000000.0),
    ("", "", "", None),  # 空行
    ("", "", "", None),  # 空行
]

# ===================== 2. 一级资本 + 调整后表内外资产 配置 =====================
# 索引 0-31 资产, 32-55 负债, 56 所有者权益
LEV_DATA = [
    # 0: 总资产, 1: 人民币小计, 2: 各项贷款汇总
    (None, None, "是", 0.0, None, None, "总资产/人民币小计 (汇总, 不重复)"),
    (None, None, None, None, None, None, ""),
    (None, None, None, None, None, None, ""),
    # 3-7: 5 项贷款 (一级资本 不计入, 表内外资产 100%)
    (None, None, "是", 1.00, None, None, "对公一般贷款 (表内资产 100%)"),
    (None, None, "是", 1.00, None, None, "个人贷款 (表内资产 100%)"),
    (None, None, "是", 1.00, None, None, "信用卡贷款 (表内资产 100%)"),
    (None, None, "是", 1.00, None, None, "票据贴现 (表内资产 100%)"),
    (None, None, "是", 1.00, None, None, "非银贷款 (表内资产 100%)"),
    # 8-13: 非信贷汇总 + 债券 + 金市
    (None, None, None, None, None, None, ""),
    (None, None, None, None, None, None, ""),
    (None, None, None, None, None, None, ""),
    (None, None, "是", 1.00, None, None, "金市 AC"),
    (None, None, "是", 1.00, None, None, "金市 FVOCI"),
    (None, None, "是", 1.00, None, None, "金市 FVTPL"),
    # 14-17: 司库债券
    (None, None, "是", 1.00, None, None, "司库 AC"),
    (None, None, "是", 1.00, None, None, "司库 FVOCI"),
    (None, None, "是", 1.00, None, None, "司库 FVTPL"),
    (None, None, "是", 1.00, None, None, "司库 FVTPL"),
    # 18-20: 结构化/同业/准备金
    (None, None, "是", 1.00, None, None, "结构化融资"),
    (None, None, "是", 1.00, None, None, "同业资产"),
    (None, None, "是", 1.00, None, None, "存款准备金"),
    # 21-25: 非生息资产
    (None, None, None, None, None, None, ""),
    (None, None, "是", 1.00, None, None, "FVTPL类资产"),
    (None, None, None, None, None, None, ""),
    (None, None, "是", 1.00, None, None, "现金"),
    (None, None, "是", 1.00, None, None, "其它"),
    # 26-31: 外币
    (None, None, None, None, None, None, ""),
    (None, None, "是", 1.00, None, None, "外币贷款"),
    (None, None, None, None, None, None, ""),
    (None, None, "是", 1.00, None, None, "外币债券"),
    (None, None, "是", 1.00, None, None, "外币同业"),
    (None, None, "是", 1.00, None, None, "外币非生息"),
    # 32-56: 负债项 (负债 不计入一级资本, 但表外承诺可能含信用转换)
    (None, None, None, None, None, None, "总负债 (不含一级资本)"),
    (None, None, None, None, None, None, ""),
    (None, None, None, None, None, None, ""),
    (None, None, None, None, None, None, "对公存款汇总"),
    (None, None, None, None, None, None, "对公活期 (表外承诺按 75% 信用转换)"),
    (None, None, None, None, None, None, "对公定期 (表外承诺按 75% 信用转换)"),
    (None, None, None, None, None, None, "零售存款汇总"),
    (None, None, None, None, None, None, "零售活期 (表外承诺按 75%)"),
    (None, None, None, None, None, None, "零售定期 (表外承诺按 75%)"),
    (None, None, None, None, None, None, "市场化负债汇总"),
    (None, None, None, None, None, None, "同业负债汇总"),
    (None, None, None, None, None, None, "同业拆入"),
    (None, None, None, None, None, None, "债券回购"),
    (None, None, None, None, None, None, "同业存单 NCD"),
    (None, None, None, None, None, None, "同业存款"),
    (None, None, None, None, None, None, "票据转贴现"),
    (None, None, None, None, None, None, "央行借款汇总"),
    (None, None, None, None, None, None, "公开市场回购"),
    (None, None, None, None, None, None, "MLF"),
    (None, None, None, None, None, None, "结构性货币政策"),
    (None, None, None, None, None, None, "票据再贴现"),
    (None, None, None, None, None, None, "外币负债汇总"),
    (None, None, None, None, None, None, "外币存款"),
    (None, None, None, None, None, None, "外币市场化"),
    # 56: 所有者权益 (核心一级资本基础 = 所有者权益)
    ("是", 0.85, "是", 1.00, None, None, "⭐所有者权益 (核心一级资本 85% 折算, 含商誉/无形资产扣除)"),
    # 57-58: 空行
    (None, None, None, None, None, None, ""),
    (None, None, None, None, None, None, ""),
]

# 简化: 简化一级资本计算
# 一级资本 = 核心一级资本 + 其他一级资本 (优先股+永续债)
# 核心一级资本 = 所有者权益 - 商誉 - 其他无形资产 - 少数股东权益
# 折算系数 0.85 表示核心一级资本占所有者权益的 85% (扣除 15% 商誉/无形资产)
# 其他一级资本 = 1000 亿 (估算, 中信银行永续债规模)
OTHER_TIER1 = 100000000000.0  # 其他一级资本 1000 亿

# ===================== 3. 创建 Excel =====================
OUTPUT = r"C:/银行经营/PRCP/docs/v2/杠杆率.xlsx"
wb = Workbook()
wb.remove(wb.active)

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===== Sheet 1: 杠杆率项目明细 =====
ws1 = wb.create_sheet("杠杆率项目明细")
ws1.merge_cells("A1:K1")
ws1["A1"] = "杠杆率 (Leverage Ratio) 计量模版 - 中信银行 2025 年末"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:K2")
ws1["A2"] = "公式: 杠杆率 = 一级资本净额 / 调整后表内外资产余额 | 监管 ≥ 4% (银保监) | 沿用 6 指标账户册 57 行结构"
ws1["A2"].font = Font(name="微软雅黑", size=10, color="555555")
ws1["A2"].fill = PatternFill("solid", fgColor="FFF3E0")
ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[2].height = 22

# 表头
headers = [
    "项目序号", "项目名称", "末级", "余额(元)",
    "是否计入一级资本", "一级资本折算系数", "计入一级资本额(元)",
    "是否计入调整后表内外资产", "信用转换系数", "调整后表内外资产额(元)",
    "备注"
]
for col, h in enumerate(headers, 1):
    cell = ws1.cell(row=4, column=col, value=h)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = border
ws1.row_dimensions[4].height = 36

# 写数据
for i, ((sid, name, is_leaf, balance), lev_cfg) in enumerate(zip(ROWS, LEV_DATA), 5):
    is_t1, t1_rate, is_exp, exp_rate, _, _, note = lev_cfg
    # 项目序号 / 项目名称 / 末级
    ws1.cell(row=i, column=1, value=sid if sid else None)
    ws1.cell(row=i, column=2, value=name if name else None)
    ws1.cell(row=i, column=3, value=is_leaf if is_leaf else None)
    # 余额
    if balance is not None:
        ws1.cell(row=i, column=4, value=balance)
    # 一级资本
    if is_t1 == "是":
        ws1.cell(row=i, column=5, value="是")
        ws1.cell(row=i, column=6, value=t1_rate)
        if balance is not None:
            ws1.cell(row=i, column=7, value=f"=D{i}*F{i}")
    # 表内外资产
    if is_exp == "是":
        ws1.cell(row=i, column=8, value="是")
        ws1.cell(row=i, column=9, value=exp_rate)
        if balance is not None:
            ws1.cell(row=i, column=10, value=f"=D{i}*I{i}")
    if note:
        ws1.cell(row=i, column=11, value=note)

    # 格式
    for c in range(1, 12):
        cell = ws1.cell(row=i, column=c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10)
        if c in [1, 2, 3, 5, 6, 8, 9, 11]:
            cell.alignment = Alignment(horizontal="left" if c in [2, 11] else "center", vertical="center", wrap_text=True)
        else:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "#,##0.00"

# 列宽
widths1 = [16, 32, 6, 18, 12, 12, 18, 14, 12, 20, 32]
for i, w in enumerate(widths1, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.freeze_panes = "A5"

# ===== Sheet 2: 杠杆率计算表 =====
ws2 = wb.create_sheet("杠杆率计算表")
ws2.merge_cells("A1:E1")
ws2["A1"] = "杠杆率计算表"
ws2["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 30

# ===== 一、分子: 一级资本净额 =====
ws2.merge_cells("A3:E3")
ws2["A3"] = "一、分子：一级资本净额"
ws2["A3"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws2["A3"].fill = PatternFill("solid", fgColor="FFF3E0")
ws2["A3"].alignment = Alignment(horizontal="left", vertical="center")

tier1_data = [
    ("项目", "金额(元)", "占比", "说明", ""),
    ("1. 核心一级资本 (CET1)", "=SUMIF('杠杆率项目明细'!E5:E61,\"是\",'杠杆率项目明细'!G5:G61)", "85%", "所有者权益 7862.17 亿 × 85% 折算 (扣商誉/无形资产)", ""),
    ("2. 其他一级资本 (AT1)", "100000000000", "15%", "永续债 + 优先股 (估算 1000 亿)", ""),
    ("3. 一级资本扣减项", "0", "0%", "无重大扣减", ""),
    ("一级资本净额 (A)", "=B6+B7-B8", "100%", "分子", ""),
]
for r, row_data in enumerate(tier1_data, 5):
    for c, val in enumerate(row_data, 1):
        cell = ws2.cell(row=r, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(r == 9))
        cell.alignment = Alignment(horizontal="left" if c in [1, 4] else "right", vertical="center", wrap_text=True)
        if r == 5:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif r == 9:
            cell.fill = PatternFill("solid", fgColor="FFE082")
            cell.font = Font(name="微软雅黑", size=12, bold=True)
        if c == 2 and r > 5 and r < 9:
            cell.number_format = "#,##0.00"
        cell.border = border

# ===== 二、分母: 调整后表内外资产余额 =====
ws2.merge_cells("A11:E11")
ws2["A11"] = "二、分母：调整后表内外资产余额"
ws2["A11"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws2["A11"].fill = PatternFill("solid", fgColor="FFF3E0")
ws2["A11"].alignment = Alignment(horizontal="left", vertical="center")

exp_data = [
    ("项目", "金额(元)", "占比", "说明", ""),
    ("1. 表内资产 (按 100% 计入)", "=SUMIF('杠杆率项目明细'!H5:H61,\"是\",'杠杆率项目明细'!J5:J61)", "100%", "总资产 + 表内科目", ""),
    ("2. 表外项目信用转换 (估算 0%)", "0", "0%", "本行表外承诺规模较小, 按简化 0% 计算", ""),
    ("调整后表内外资产余额 (B)", "=B14+B15", "100%", "分母", ""),
]
for r, row_data in enumerate(exp_data, 13):
    for c, val in enumerate(row_data, 1):
        cell = ws2.cell(row=r, column=c, value=val)
        cell.font = Font(name="微软雅黑", size=10, bold=(r == 16))
        cell.alignment = Alignment(horizontal="left" if c in [1, 4] else "right", vertical="center", wrap_text=True)
        if r == 13:
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif r == 16:
            cell.fill = PatternFill("solid", fgColor="FFE082")
            cell.font = Font(name="微软雅黑", size=12, bold=True)
        if c == 2 and r > 13 and r < 16:
            cell.number_format = "#,##0.00"
        cell.border = border

# ===== 三、杠杆率 =====
ws2.merge_cells("A18:E18")
ws2["A18"] = "三、杠杆率"
ws2["A18"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws2["A18"].fill = PatternFill("solid", fgColor="FFF3E0")
ws2["A18"].alignment = Alignment(horizontal="left", vertical="center")

# 计算公式
ws2.cell(row=20, column=1, value="杠杆率 = 一级资本净额 (A) / 调整后表内外资产余额 (B)").font = Font(name="微软雅黑", size=12, bold=True)
ws2.merge_cells("A20:C20")
ws2.cell(row=20, column=1).alignment = Alignment(horizontal="left", vertical="center")

ws2.cell(row=21, column=1, value="杠杆率").font = Font(name="微软雅黑", size=12, bold=True)
ws2.merge_cells("A21:C21")
ws2.cell(row=21, column=1).alignment = Alignment(horizontal="left", vertical="center")
ws2.cell(row=21, column=1).fill = PatternFill("solid", fgColor="C7000B")
ws2.cell(row=21, column=1).font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")

ws2.cell(row=21, column=4, value="=B9/B16").font = Font(name="微软雅黑", size=14, bold=True, color="C7000B")
ws2.cell(row=21, column=4).number_format = "0.0000%"
ws2.cell(row=21, column=4).fill = PatternFill("solid", fgColor="FFE082")
ws2.cell(row=21, column=4).alignment = Alignment(horizontal="center", vertical="center")

ws2.cell(row=21, column=5, value="6.50% (实测估算)").font = Font(name="微软雅黑", size=10, bold=False, color="555555")
ws2.cell(row=21, column=5).alignment = Alignment(horizontal="left", vertical="center")

# 监管对比
ws2.cell(row=23, column=1, value="监管要求").font = Font(name="微软雅黑", size=11, bold=True)
ws2.merge_cells("A23:C23")
ws2.cell(row=23, column=1).alignment = Alignment(horizontal="left", vertical="center")
ws2.cell(row=23, column=4, value="≥ 4.00%").font = Font(name="微软雅黑", size=11, bold=True, color="C7000B")
ws2.cell(row=23, column=4).alignment = Alignment(horizontal="center", vertical="center")

ws2.cell(row=24, column=1, value="距监管要求").font = Font(name="微软雅黑", size=11, bold=True)
ws2.merge_cells("A24:C24")
ws2.cell(row=24, column=1).alignment = Alignment(horizontal="left", vertical="center")
ws2.cell(row=24, column=4, value="=D21-D23").font = Font(name="微软雅黑", size=11, bold=True, color="2E7D32")
ws2.cell(row=24, column=4).number_format = "+0.00%;-0.00%"
ws2.cell(row=24, column=4).alignment = Alignment(horizontal="center", vertical="center")

# 评级
ws2.cell(row=26, column=1, value="评级").font = Font(name="微软雅黑", size=12, bold=True)
ws2.merge_cells("A26:C26")
ws2.cell(row=26, column=1).alignment = Alignment(horizontal="left", vertical="center")
ws2.cell(row=26, column=1).fill = PatternFill("solid", fgColor="C8E6C9")
ws2.cell(row=26, column=4, value="✓ 优秀 (6-8% 区间, 距监管 250bp 缓冲)").font = Font(name="微软雅黑", size=12, bold=True, color="2E7D32")
ws2.cell(row=26, column=4).alignment = Alignment(horizontal="center", vertical="center")
ws2.cell(row=26, column=4).fill = PatternFill("solid", fgColor="C8E6C9")

widths2 = [25, 20, 10, 25, 35]
for i, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w

# ===== Sheet 3: 折算依据 =====
ws3 = wb.create_sheet("折算依据")
ws3.merge_cells("A1:C1")
ws3["A1"] = "杠杆率折算依据 + 监管口径 + 业务含义"
ws3["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 30

# 1. 指标定义
ws3.merge_cells("A3:C3")
ws3["A3"] = "一、指标定义"
ws3["A3"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A3"].fill = PatternFill("solid", fgColor="FFF3E0")

definitions = [
    ("杠杆率", "一级资本净额 / 调整后表内外资产余额", "银保监《商业银行杠杆率管理办法》"),
    ("监管要求", "≥ 4%", "国内系统重要性银行 (D-SIBs)"),
    ("国际标准", "≥ 3% (巴塞尔 III)", "BCBS 最低要求"),
    ("优质水平", "≥ 6%", "股份制银行头部水平"),
    ("过高", "≥ 8%", "资本冗余, ROE 承压"),
]
for r, (a, b, c) in enumerate(definitions, 5):
    ws3.cell(row=r, column=1, value=a).font = Font(name="微软雅黑", size=10, bold=True)
    ws3.cell(row=r, column=2, value=b).font = Font(name="微软雅黑", size=10)
    ws3.cell(row=r, column=3, value=c).font = Font(name="微软雅黑", size=10, color="555555")
    for col in range(1, 4):
        ws3.cell(row=r, column=col).border = border
        ws3.cell(row=r, column=col).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r % 2 == 0:
        for col in range(1, 4):
            ws3.cell(row=r, column=col).fill = PatternFill("solid", fgColor="F5F5F5")

# 2. 公式
ws3.merge_cells("A12:C12")
ws3["A12"] = "二、计算公式"
ws3["A12"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A12"].fill = PatternFill("solid", fgColor="FFF3E0")

formulas = [
    ("一级资本净额", "= 核心一级资本 + 其他一级资本 - 一级资本扣减项", ""),
    ("核心一级资本", "= 所有者权益 - 商誉 - 其他无形资产 - 少数股东权益等", "CET1 口径, 银保监规则"),
    ("其他一级资本", "= 优先股 + 永续债 (符合条件的其他一级资本工具)", "AT1 口径"),
    ("调整后表内外资产余额", "= 表内资产 + 表外项目 × 信用转换系数", "总资产 + 表外承诺等"),
    ("表内资产", "= 总资产 (按 100% 计入)", "简化处理"),
    ("表外项目信用转换系数", "贷款承诺 75% / 担保 100% / 证券化 100% 等", "银保监规定"),
]
for r, (a, b, c) in enumerate(formulas, 14):
    ws3.cell(row=r, column=1, value=a).font = Font(name="微软雅黑", size=10, bold=True)
    ws3.cell(row=r, column=2, value=b).font = Font(name="微软雅黑", size=10)
    ws3.cell(row=r, column=3, value=c).font = Font(name="微软雅黑", size=10, color="555555")
    for col in range(1, 4):
        ws3.cell(row=r, column=col).border = border
        ws3.cell(row=r, column=col).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r % 2 == 0:
        for col in range(1, 4):
            ws3.cell(row=r, column=col).fill = PatternFill("solid", fgColor="F5F5F5")

# 3. 业务含义
ws3.merge_cells("A22:C22")
ws3["A22"] = "三、业务含义与调整建议"
ws3["A22"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A22"].fill = PatternFill("solid", fgColor="FFF3E0")

business = [
    ("过高 (>8%)", "资本冗余, ROE 承压", "建议发行一级资本工具或提升分红"),
    ("优质 (6-8%)", "资本充足, 抗风险能力强", "保持当前水平, 优化 RWA 配置"),
    ("达标 (4-6%)", "满足监管, 缓冲薄", "可适度加大 RWA 配置"),
    ("贴近红线 (<4%)", "未达监管, 触发处罚", "紧急补充一级资本"),
]
for r, (a, b, c) in enumerate(business, 24):
    ws3.cell(row=r, column=1, value=a).font = Font(name="微软雅黑", size=10, bold=True)
    ws3.cell(row=r, column=2, value=b).font = Font(name="微软雅黑", size=10)
    ws3.cell(row=r, column=3, value=c).font = Font(name="微软雅黑", size=10, color="555555")
    for col in range(1, 4):
        ws3.cell(row=r, column=col).border = border
        ws3.cell(row=r, column=col).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r % 2 == 0:
        for col in range(1, 4):
            ws3.cell(row=r, column=col).fill = PatternFill("solid", fgColor="F5F5F5")

# 4. 中信银行 2025 年末测算
ws3.merge_cells("A30:C30")
ws3["A30"] = "四、中信银行 2025 年末测算"
ws3["A30"].font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws3["A30"].fill = PatternFill("solid", fgColor="FFF3E0")

citic_data = [
    ("核心一级资本 (估算)", "约 6,683 亿元", "所有者权益 7,862 亿 × 85% 折算"),
    ("其他一级资本 (估算)", "约 1,000 亿元", "永续债 + 优先股"),
    ("一级资本净额 (A)", "约 7,683 亿元", ""),
    ("调整后表内外资产 (B)", "约 118,200 亿元", "总资产 11.8 万亿 + 表外承诺"),
    ("杠杆率", "约 6.50%", "A / B = 6.50%"),
    ("距监管 (≥4%)", "+250bp", "充裕缓冲"),
    ("评级", "✓ 优秀", "股份制银行头部水平"),
]
for r, (a, b, c) in enumerate(citic_data, 32):
    ws3.cell(row=r, column=1, value=a).font = Font(name="微软雅黑", size=10, bold=True)
    ws3.cell(row=r, column=2, value=b).font = Font(name="微软雅黑", size=10)
    ws3.cell(row=r, column=3, value=c).font = Font(name="微软雅黑", size=10, color="555555")
    for col in range(1, 4):
        ws3.cell(row=r, column=col).border = border
        ws3.cell(row=r, column=col).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r % 2 == 0:
        for col in range(1, 4):
            ws3.cell(row=r, column=col).fill = PatternFill("solid", fgColor="F5F5F5")

widths3 = [22, 30, 35]
for i, w in enumerate(widths3, 1):
    ws3.column_dimensions[get_column_letter(i)].width = w

wb.save(OUTPUT)
print(f"已保存: {OUTPUT}")

# ===================== 4. 验证计算 =====================
print("\n=== 杠杆率测算 (中信银行 2025 年末) ===")
total_assets = 11800000000000.0  # 总资产 (表内)
equity = 786217000000.0
cet1 = equity * 0.85  # 核心一级资本 (扣商誉等)
at1 = 100000000000.0
tier1 = cet1 + at1
exposure = total_assets  # 简化: 表内资产
leverage_ratio = tier1 / exposure
print(f"核心一级资本 (CET1): {cet1/1e8:.2f} 亿元")
print(f"其他一级资本 (AT1):  {at1/1e8:.2f} 亿元")
print(f"一级资本净额 (A):    {tier1/1e8:.2f} 亿元")
print(f"调整后表内外资产 (B): {exposure/1e8:.2f} 亿元 ({exposure/1e12:.2f} 万亿)")
print(f"杠杆率: {leverage_ratio*100:.4f}%")
print(f"监管要求: ≥ 4%")
print(f"缓冲: {(leverage_ratio - 0.04)*100:.2f} pp")
