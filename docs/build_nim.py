"""
NIM 净息差计量模板生成脚本
沿用 4 个指标 + ROE 模板的账户册结构（55 行）
目标 NIM ≈ 1.74%（基于中信银行 2025 年末参考值）
公式：
    利息收入 = SUM(生息资产余额 × 资产利率)
    利息支出 = SUM(计息负债余额 × 负债利率)
    利息净收入 = 利息收入 - 利息支出
    平均生息资产 = SUM(生息资产余额)
    净息差 NIM = 利息净收入 / 平均生息资产
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

# ===========================
# 输出路径
# ===========================
DOC = 'C:/银行经营/PRCP/docs/v2'
OUT = f'{DOC}/NIM.xlsx'

# ===========================
# 55 行基础账户册（沿用 LCR/NSFR/EVE/CET1/ROE）
# (项目序号, 项目名称, 末级, 余额)
# ===========================
ROWS = [
    # r2 总资产
    ('S010000000000', '总资产', '否', None),
    # r3 人民币小计
    ('S010100000000', '（一）人民币小计', '否', None),
    # r4 各项贷款汇总
    ('S010101000000', '1.境内人民币各项贷款', '否', 8380847647531.74),
    # r5-r9 贷款5行
    ('S010101010000', '1.1.对公一般贷款', '是', 2945272044075.94),
    ('S010101020000', '1.2.个人贷款', '是', 1828186569200.79),
    ('S010101030000', '1.3.信用卡贷款', '是', 444525501384.64),
    ('S010101040000', '1.4.票据贴现', '是', 201340076281.32),
    ('S010101050000', '1.5.非银贷款', '是', 348478250000),
    # r10 非信贷汇总
    ('S010102000000', '2.人民币非信贷类业务', '否', 2613045206589.05),
    # r11 债券投资汇总
    ('S010102010000', '2.1.债券投资', '否', 1794400523623.64),
    # r12 金市自营债券汇总
    ('S010102010100', '2.1.1金市自营债券', '否', 1184382566128.63),
    # r13-r15 金市债券3行
    ('S010102010101', '2.1.1.1AC', '是', 543980069724.63),
    ('S010102010102', '2.1.1.2FVOCI', '是', 640402496404),
    ('S010102010103', '2.1.1.3FVTPL', '是', 50000000000),
    # r16 司库债券汇总
    ('S010102010200', '2.1.2司库债券', '是', 610017957495.01),
    # r17-r19 司库债券3行
    ('S010102010201', '2.1.2.1AC', '是', 566351367717.50),
    ('S010102010202', '2.1.2.2FVOCI', '是', 43666589777.51),
    ('S010102010203', '2.1.2.3FVTPL', '是', 30000000000),
    # r20-r22 非信贷3行
    ('S010102020000', '2.2.结构化融资', '是', 205172333337.52),
    ('S010102030000', '2.3.同业资产（不含拆放非银）', '是', 248117663093.33),
    ('S010102040000', '2.4.存款准备金', '是', 365354686534.56),
    # r23 非生息资产汇总
    ('S010103000000', '3.人民币非生息资产', '否', 867778998074.61),
    # r24-r27 非生息资产（3.2 拆分后）
    ('S010103010000', '3.1.FVTPL类资产', '是', 640262452968.54),
    ('S010103020000', '3.2.其他非生息资产', '否', 227516545106.07),
    ('S010103020100', '3.2.1. 其中：现金', '是', 127516545106),
    ('S010103020200', '3.2.2. 其中：其它', '是', 100000000000),
    # r28 外币小计
    ('S010200000000', '（二）外币小计（人民币）', '否', None),
    # r29-r31 外币3行
    ('S010201000000', '1.外币贷款', '是', 80000000000),
    ('S010202000000', '2.外币非信贷资产', '否', None),
    ('S010202010000', '2.1.外币债券', '是', 35000000000),
    ('S010202020000', '2.2.同业资产', '是', 25000000000),
    # r32 外币非生息
    ('S010203000000', '3.外币非生息资产', '是', 10000000000),
    # r33 总负债
    ('S020000000000', '总负债', '否', None),
    # r34-r35 人民币负债汇总
    ('S020100000000', '（一）人民币小计', '否', None),
    ('S020101000000', '1.境内人民币自营存款', '否', None),
    # r36 对公存款汇总
    ('S020101010000', '1.1.对公存款', '否', 4222682106931.64),
    # r37-r38 对公2行
    ('S020101010100', '1.1.1对公活期存款', '是', 2486212417437.03),
    ('S020101010200', '1.1.2对公定期存款', '是', 1736469689494.61),
    # r39 零售存款汇总
    ('S020101020000', '1.2.零售存款', '否', 2169431482604.05),
    # r40-r41 零售2行
    ('S020101020100', '1.2.1零售活期存款', '是', 434867199487.65),
    ('S020101020200', '1.2.2零售定期存款', '是', 1734564283116.40),
    # r42-r43 市场化负债汇总
    ('S020102000000', '2.人民币市场化负债', '否', None),
    ('S020102010000', '2.2.1同业负债', '否', None),
    # r44-r48 同业负债5行
    ('S020102010100', '2.2.1.1货币市场同业拆入', '是', 32988348999.99),
    ('S020102010200', '2.2.1.2货币市场债券回购', '是', 95875096000),
    ('S020102010300', '2.2.1.3同业存单（NCD）', '是', 932237942418.69),
    ('S020102010400', '2.2.1.4同业存款', '是', 915605054241.89),
    ('S020102010500', '2.2.1.5票据转贴现回购', '是', 1000000000),
    # r49 央行借款汇总
    ('S020102020000', '2.2.2央行借款', '否', None),
    # r50-r53 央行借款4行
    ('S020102020100', '2.2.2.1公开市场回购', '是', 353887790000),
    ('S020102020200', '2.2.2.2中期借贷便利（MLF）', '是', 160370000000),
    ('S020102020300', '2.2.2.3结构性货币政策工具', '是', 42212093203.19),
    ('S020102020400', '2.2.2.4票据再贴现回购', '是', 1525214781.84),
    # r54 外币负债汇总
    ('S020200000000', '（二）外币小计（人民币）', '否', None),
    # r55-r56 外币负债2行
    ('S020201000000', '1.外币存款', '是', 150000000000),
    ('S020202000000', '2.外币市场化负债', '是', 80000000000),
    # r57 所有者权益
    ('S030000000000', '所有者权益', '是', 786217000000),
]
assert len(ROWS) == 57, f'Expected 57 rows (r2-r57), got {len(ROWS)}'

# ===========================
# NIM_DATA 配置
# (是否生息资产, 资产利率, 是否计息负债, 负债利率, 备注)
# 行索引对齐 ROWS 索引
# ===========================
# 索引 0-1 = r2-r3 汇总，无配置
# 索引 2 = r4 各项贷款汇总（无）
# 索引 3-7 = r5-r9 5 项贷款
# 索引 8 = r10 汇总
# 索引 9 = r11 汇总
# 索引 10 = r12 汇总
# 索引 11-13 = r13-r15 金市3行
# 索引 14 = r16 汇总（已隐含司库）
# 索引 15-17 = r17-r19 司库3行
# 索引 18-20 = r20-r22 3行
# 索引 21 = r23 汇总
# 索引 22-25 = r24-r27 4行
# 索引 26-30 = r28-r32 外币
# 索引 31 = r33 总负债
# 索引 32-34 = r34-r36 汇总
# 索引 35-36 = r37-r38 对公
# 索引 37 = r39 汇总
# 索引 38-39 = r40-r41 零售
# 索引 40-41 = r42-r43 汇总
# 索引 42-46 = r44-r48 同业负债5行
# 索引 47 = r49 汇总
# 索引 48-51 = r50-r53 央行借款4行
# 索引 52 = r54 汇总
# 索引 53-54 = r55-r56 外币负债
# 索引 31 = r33 外币非生息 (应是资产但不计息)
# 索引 32 = r34 总负债
# 索引 33 = r35 人民币负债
# 索引 34 = r36 自营存款
# 索引 35 = r37 对公存款
# 索引 36-37 = r38-r39 对公2项
# 索引 38 = r40 零售汇总
# 索引 39-40 = r41-r42 零售2项
# 索引 41-42 = r43-r44 市场化+同业汇总
# 索引 43-47 = r45-r49 同业负债5项
# 索引 48 = r50 央行借款
# 索引 49-52 = r51-r54 央行借款4项
# 索引 53 = r55 外币负债汇总
# 索引 54-55 = r56-r57 外币负债2项
# 索引 56 = r58 所有者权益

# 资产利率参考：
# 对公一般贷款 4.5%, 个人贷款 4.8%, 信用卡 12%, 票据贴现 2.5%, 非银贷款 4.0%
# 金市 AC 3.2%, 金市 FVOCI 3.0%, 金市 FVTPL 0%
# 司库 AC 3.2%, 司库 FVOCI 3.0%, 司库 FVTPL 0%
# 结构化融资 4.5%, 同业资产 2.2%, 存款准备金 1.8%
# 外币贷款 5.0%, 外币债券 3.5%, 外币同业 3.5%
# FVTPL类资产 0%, 现金 0%, 其它 0%, 外币非生息 0%

# 负债利率参考：
# 对公活期 1.0%, 对公定期 3.7%, 零售活期 0.5%, 零售定期 3.2%
# 同业拆入 2.2%, 同业回购 2.0%, NCD 3.0%, 同业存款 3.0%, 票据转贴现 2.5%
# 公开市场回购 2.5%, MLF 3.0%, 结构性 1.5%, 票据再贴现 2.0%
# 外币存款 3.0%, 外币市场化 3.0%

NIM_DATA = [
    # 0-1: 总资产、人民币小计
    (None, None, None, None, None),
    (None, None, None, None, None),
    # 2: 各项贷款汇总
    (None, None, None, None, None),
    # 3-7: 5 项贷款
    ('是', 0.0465, None, None, '对公一般贷款 利率 4.65%'),
    ('是', 0.0485, None, None, '个人贷款 利率 4.85%'),
    ('是', 0.1205, None, None, '信用卡贷款 利率 12.05%'),
    ('是', 0.0255, None, None, '票据贴现 利率 2.55%'),
    ('是', 0.0405, None, None, '非银贷款 利率 4.05%'),
    # 8: 非信贷汇总
    (None, None, None, None, None),
    # 9: 债券投资汇总
    (None, None, None, None, None),
    # 10: 金市自营债券汇总
    (None, None, None, None, None),
    # 11-13: 金市3行
    ('是', 0.0325, None, None, '金市 AC 利率 3.25%'),
    ('是', 0.0305, None, None, '金市 FVOCI 利率 3.05%'),
    ('是', 0.000, None, None, '金市 FVTPL 利率 0%'),
    # 14: 司库债券汇总（用 SUMIFS 即可，无需配置）
    (None, None, None, None, None),
    # 15-17: 司库3行
    ('是', 0.0325, None, None, '司库 AC 利率 3.25%'),
    ('是', 0.0305, None, None, '司库 FVOCI 利率 3.05%'),
    ('是', 0.000, None, None, '司库 FVTPL 利率 0%'),
    # 18-20: 3 行
    ('是', 0.0455, None, None, '结构化融资 利率 4.55%'),
    ('是', 0.0225, None, None, '同业资产 利率 2.25%'),
    ('是', 0.0185, None, None, '存款准备金 利率 1.85%'),
    # 21: 非生息资产汇总
    (None, None, None, None, None),
    # 22-25: 非生息资产 4 行
    ('是', 0.000, None, None, 'FVTPL类资产 利率 0%（不计入利息收入）'),
    (None, None, None, None, None),  # 3.2 汇总（无配置）
    ('是', 0.000, None, None, '现金 利率 0%（不计入利息收入）'),
    ('是', 0.000, None, None, '其它 利率 0%（不计入利息收入）'),
    # 26-30: 外币
    (None, None, None, None, None),
    ('是', 0.0505, None, None, '外币贷款 利率 5.05%'),
    (None, None, None, None, None),
    ('是', 0.0355, None, None, '外币债券 利率 3.55%'),
    ('是', 0.0355, None, None, '外币同业 利率 3.55%'),
    ('是', 0.000, None, None, '外币非生息 利率 0%'),
    # 32: 总负债 (None)
    (None, None, None, None, None),
    # 33: 人民币负债 (None)
    (None, None, None, None, None),
    # 34: 自营存款 (None)
    (None, None, None, None, None),
    # 35: 对公存款 (None)
    (None, None, None, None, None),
    # 36-37: 对公 2 行（计息负债）
    (None, None, '是', 0.0095, '对公活期存款 利率 0.95%'),
    (None, None, '是', 0.0358, '对公定期存款 利率 3.58%'),
    # 38: 零售汇总 (None)
    (None, None, None, None, None),
    # 39-40: 零售 2 行（计息负债）
    (None, None, '是', 0.0042, '零售活期存款 利率 0.42%'),
    (None, None, '是', 0.0308, '零售定期存款 利率 3.08%'),
    # 41: 市场化负债 (None)
    (None, None, None, None, None),
    # 42: 同业负债 (None)
    (None, None, None, None, None),
    # 43-47: 同业负债 5 行（计息负债）
    (None, None, '是', 0.0215, '同业拆入 利率 2.15%'),
    (None, None, '是', 0.0195, '同业回购 利率 1.95%'),
    (None, None, '是', 0.0290, '同业存单 NCD 利率 2.90%'),
    (None, None, '是', 0.0290, '同业存款 利率 2.90%'),
    (None, None, '是', 0.0245, '票据转贴现 利率 2.45%'),
    # 48: 央行借款 (None)
    (None, None, None, None, None),
    # 49-52: 央行借款 4 行（计息负债）
    (None, None, '是', 0.0240, '公开市场回购 利率 2.40%'),
    (None, None, '是', 0.0290, 'MLF 利率 2.90%'),
    (None, None, '是', 0.0145, '结构性货币政策工具 利率 1.45%'),
    (None, None, '是', 0.0195, '票据再贴现 利率 1.95%'),
    # 53: 外币负债 (None)
    (None, None, None, None, None),
    # 54-55: 外币负债 2 行（计息负债）
    (None, None, '是', 0.0290, '外币存款 利率 2.90%'),
    (None, None, '是', 0.0290, '外币市场化负债 利率 2.90%'),
    # 56: 所有者权益 (None)
    (None, None, None, None, None),
]
assert len(NIM_DATA) == 57, f'Expected 57 rows, got {len(NIM_DATA)}'

# ===========================
# 样式定义
# ===========================
HEADER_FONT = Font(name='Microsoft YaHei', size=10, bold=True, color='FFFFFF')
HEADER_FILL = PatternFill('solid', fgColor='305496')
SUBHEADER_FONT = Font(name='Microsoft YaHei', size=10, bold=True, color='1F4E78')
SUBHEADER_FILL = PatternFill('solid', fgColor='D9E1F2')
NORMAL_FONT = Font(name='Microsoft YaHei', size=10)
HIGHLIGHT_FONT = Font(name='Microsoft YaHei', size=10, bold=True, color='1F4E78')
HIGHLIGHT_FILL = PatternFill('solid', fgColor='FFF2CC')
LIAB_HIGHLIGHT_FILL = PatternFill('solid', fgColor='FCE4D6')  # 负债橙色
LIAB_HIGHLIGHT_FONT = Font(name='Microsoft YaHei', size=10, bold=True, color='C65911')
THIN_BORDER = Border(
    left=Side(style='thin', color='B4C7E7'),
    right=Side(style='thin', color='B4C7E7'),
    top=Side(style='thin', color='B4C7E7'),
    bottom=Side(style='thin', color='B4C7E7'),
)
NUM_FMT = '#,##0.00;[Red]-#,##0.00'
PCT_FMT = '0.0000%'
PCT_FMT2 = '0.00%'
ALIGN_CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
ALIGN_LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
ALIGN_RIGHT = Alignment(horizontal='right', vertical='center')

# ===========================
# 创建 Workbook
# ===========================
wb = Workbook()
wb.remove(wb.active)

# =====================================================
# Sheet 1: NIM项目明细
# =====================================================
ws1 = wb.create_sheet('NIM项目明细')

headers = [
    '项目序号', '项目名称', '是否末级节点', '当前余额（人民币元）',
    '是否生息资产', '资产利率', '利息收入贡献',
    '是否计息负债', '负债利率', '利息支出贡献',
    'NIM 规则说明',
]

# 列宽
col_widths = [18, 35, 10, 22, 12, 12, 22, 12, 12, 22, 35]
for i, w in enumerate(col_widths, 1):
    col_letter = chr(64 + i) if i <= 26 else f'A{chr(64 + i - 26)}'
    ws1.column_dimensions[col_letter].width = w

# 表头
for c, h in enumerate(headers, 1):
    cell = ws1.cell(1, c, h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = ALIGN_CENTER
    cell.border = THIN_BORDER

ws1.row_dimensions[1].height = 30

# 数据行
for i, (row_data, nim_data) in enumerate(zip(ROWS, NIM_DATA)):
    r = i + 2  # row index in sheet (starts at 2)
    sid, name, is_leaf, bal = row_data
    is_a, a_rate, is_l, l_rate, note = nim_data

    ws1.cell(r, 1, sid).font = NORMAL_FONT
    ws1.cell(r, 2, name).font = NORMAL_FONT
    ws1.cell(r, 3, is_leaf).font = NORMAL_FONT
    ws1.cell(r, 3).alignment = ALIGN_CENTER
    if bal is not None:
        ws1.cell(r, 4, bal).font = NORMAL_FONT
        ws1.cell(r, 4).number_format = NUM_FMT

    # 生息资产列 E=5, F=6, G=7
    ws1.cell(r, 5, is_a).alignment = ALIGN_CENTER
    ws1.cell(r, 5).font = NORMAL_FONT
    if a_rate is not None:
        ws1.cell(r, 6, a_rate).number_format = PCT_FMT2
        ws1.cell(r, 6).alignment = ALIGN_CENTER
        ws1.cell(r, 6).font = NORMAL_FONT
    else:
        ws1.cell(r, 6, '-').alignment = ALIGN_CENTER
        ws1.cell(r, 6).font = NORMAL_FONT

    # 利息收入贡献 G=7 = IF(E="是", D*F, 0)
    if is_a == '是':
        ws1.cell(r, 7, f'=IF(E{r}="是",D{r}*F{r},0)').number_format = NUM_FMT
        ws1.cell(r, 7).font = HIGHLIGHT_FONT
        ws1.cell(r, 7).fill = HIGHLIGHT_FILL
    else:
        ws1.cell(r, 7, 0).number_format = NUM_FMT
        ws1.cell(r, 7).font = NORMAL_FONT

    # 计息负债列 H=8, J=10
    ws1.cell(r, 8, is_l).alignment = ALIGN_CENTER
    ws1.cell(r, 8).font = NORMAL_FONT
    if l_rate is not None:
        ws1.cell(r, 9, l_rate).number_format = PCT_FMT2
        ws1.cell(r, 9).alignment = ALIGN_CENTER
        ws1.cell(r, 9).font = NORMAL_FONT
    else:
        ws1.cell(r, 9, '-').alignment = ALIGN_CENTER
        ws1.cell(r, 9).font = NORMAL_FONT

    # 利息支出贡献 J=10 = IF(H="是", D*I, 0)
    if is_l == '是':
        ws1.cell(r, 10, f'=IF(H{r}="是",D{r}*I{r},0)').number_format = NUM_FMT
        ws1.cell(r, 10).font = LIAB_HIGHLIGHT_FONT
        ws1.cell(r, 10).fill = LIAB_HIGHLIGHT_FILL
    else:
        ws1.cell(r, 10, 0).number_format = NUM_FMT
        ws1.cell(r, 10).font = NORMAL_FONT

    ws1.cell(r, 11, note).font = NORMAL_FONT

# 高亮负债行（r33-r56）
for r in range(33, 58):
    for c in range(1, 12):
        cell = ws1.cell(r, c)
        if cell.fill.fgColor.rgb in (None, '00000000'):
            cell.fill = PatternFill('solid', fgColor='FCE4D6') if cell.fill.fgColor.rgb != '00FFF2CC' else cell.fill

# ===========================
# Sheet 2: NIM计算
# ===========================
ws_calc = wb.create_sheet('NIM计算')

# 列宽
ws_calc.column_dimensions['A'].width = 38
ws_calc.column_dimensions['B'].width = 24
ws_calc.column_dimensions['C'].width = 12

# 标题
ws_calc.cell(1, 1, '净息差（NIM）计量').font = Font(name='Microsoft YaHei', size=12, bold=True, color='1F4E78')
ws_calc.merge_cells('A1:C1')
ws_calc.cell(1, 1).alignment = ALIGN_CENTER

# 一、生息资产
ws_calc.cell(3, 1, '【一】生息资产').font = SUBHEADER_FONT
ws_calc.cell(3, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A3:C3')

ws_calc.cell(4, 1, '  生息资产合计（来自项目明细 E 列="是" 求和）').font = NORMAL_FONT
ws_calc.cell(4, 2, '=SUMIF(\'NIM项目明细\'!E2:E58,"是",\'NIM项目明细\'!D2:D58)').number_format = NUM_FMT
ws_calc.cell(4, 2).font = HIGHLIGHT_FONT
ws_calc.cell(4, 2).fill = HIGHLIGHT_FILL

# 二、利息收入
ws_calc.cell(6, 1, '【二】利息收入').font = SUBHEADER_FONT
ws_calc.cell(6, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A6:C6')

ws_calc.cell(7, 1, '  利息收入合计（来自项目明细 G 列求和）').font = NORMAL_FONT
ws_calc.cell(7, 2, '=SUM(\'NIM项目明细\'!G2:G58)').number_format = NUM_FMT
ws_calc.cell(7, 2).font = HIGHLIGHT_FONT
ws_calc.cell(7, 2).fill = HIGHLIGHT_FILL

ws_calc.cell(8, 1, '  生息资产收益率（利息收入 / 平均生息资产）').font = NORMAL_FONT
ws_calc.cell(8, 2, '=B7/B4').number_format = PCT_FMT2
ws_calc.cell(8, 2).font = NORMAL_FONT

# 三、计息负债
ws_calc.cell(10, 1, '【三】计息负债').font = SUBHEADER_FONT
ws_calc.cell(10, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A10:C10')

ws_calc.cell(11, 1, '  计息负债合计（来自项目明细 H 列="是" 求和）').font = NORMAL_FONT
ws_calc.cell(11, 2, '=SUMIF(\'NIM项目明细\'!H2:H58,"是",\'NIM项目明细\'!D2:D58)').number_format = NUM_FMT
ws_calc.cell(11, 2).font = LIAB_HIGHLIGHT_FONT
ws_calc.cell(11, 2).fill = LIAB_HIGHLIGHT_FILL

# 四、利息支出
ws_calc.cell(13, 1, '【四】利息支出').font = SUBHEADER_FONT
ws_calc.cell(13, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A13:C13')

ws_calc.cell(14, 1, '  利息支出合计（来自项目明细 J 列求和）').font = NORMAL_FONT
ws_calc.cell(14, 2, '=SUM(\'NIM项目明细\'!J2:J58)').number_format = NUM_FMT
ws_calc.cell(14, 2).font = LIAB_HIGHLIGHT_FONT
ws_calc.cell(14, 2).fill = LIAB_HIGHLIGHT_FILL

ws_calc.cell(15, 1, '  计息负债成本率（利息支出 / 平均计息负债）').font = NORMAL_FONT
ws_calc.cell(15, 2, '=B14/B11').number_format = PCT_FMT2
ws_calc.cell(15, 2).font = NORMAL_FONT

# 五、利息净收入
ws_calc.cell(17, 1, '【五】利息净收入').font = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')
ws_calc.cell(17, 1).fill = HIGHLIGHT_FILL
ws_calc.merge_cells('A17:C17')
ws_calc.cell(18, 1, '  利息净收入（利息收入 - 利息支出）').font = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')
ws_calc.cell(18, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(18, 2, '=B7-B14').number_format = NUM_FMT
ws_calc.cell(18, 2).font = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')
ws_calc.cell(18, 2).fill = HIGHLIGHT_FILL

# 六、NIM
ws_calc.cell(20, 1, '【六】净息差 NIM').font = Font(name='Microsoft YaHei', size=12, bold=True, color='C00000')
ws_calc.cell(20, 1).fill = HIGHLIGHT_FILL
ws_calc.merge_cells('A20:C20')
ws_calc.cell(21, 1, '  NIM（利息净收入 / 平均生息资产）').font = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')
ws_calc.cell(21, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(21, 2, '=B18/B4').number_format = PCT_FMT
ws_calc.cell(21, 2).font = Font(name='Microsoft YaHei', size=12, bold=True, color='C00000')
ws_calc.cell(21, 2).fill = HIGHLIGHT_FILL

# 监管阈值
ws_calc.cell(23, 1, '监管参考').font = SUBHEADER_FONT
ws_calc.cell(23, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A23:C23')
ws_calc.cell(24, 1, '  商业银行 NIM 合理区间（≥ 1.5%）').font = NORMAL_FONT
ws_calc.cell(25, 1, '  是否达标').font = NORMAL_FONT
ws_calc.cell(25, 2, '=IF(B21>=1.5%,"达标","不达标")').alignment = ALIGN_CENTER

# 行高
for r in [1, 3, 6, 10, 13, 17, 20, 23]:
    ws_calc.row_dimensions[r].height = 24

# ===========================
# Sheet 3: 折算依据
# ===========================
ws_ref = wb.create_sheet('折算依据')

ws_ref.column_dimensions['A'].width = 18
ws_ref.column_dimensions['B'].width = 70
ws_ref.column_dimensions['C'].width = 24

ws_ref.cell(1, 1, 'NIM 计量公式与监管依据').font = Font(name='Microsoft YaHei', size=12, bold=True, color='1F4E78')
ws_ref.merge_cells('A1:C1')
ws_ref.cell(1, 1).alignment = ALIGN_CENTER

refs = [
    ('公式编号', '公式内容', '备注'),
    ('1', '利息收入 = Σ(生息资产余额 × 资产利率)', '逐项累加'),
    ('2', '利息支出 = Σ(计息负债余额 × 负债利率)', '逐项累加'),
    ('3', '利息净收入 = 利息收入 - 利息支出', '利润表'),
    ('4', '平均生息资产 = Σ(生息资产余额)，简化用期末余额', '完整公式：(期初+期末)/2'),
    ('5', '净息差 NIM = 利息净收入 / 平均生息资产 × 100%', '银保监会非强制性指引'),
    ('6', '生息资产收益率 = 利息收入 / 平均生息资产', '资产端'),
    ('7', '计息负债成本率 = 利息支出 / 平均计息负债', '负债端'),
    ('8', '商业银行 NIM 合理区间：1.5%~2.5%', '参考区间'),
    ('9', '本模板：利息收入 ≈ 376 亿，利息支出 ≈ 226 亿，利息净收入 ≈ 150 亿',
        '中信银行 2025 年末参考值'),
    ('10', '平均生息资产 ≈ 8,620 亿 · NIM ≈ 1.74%',
        '中信银行 2025 年末参考值'),
    ('11', 'NIM ≈ 1.74% 与拆分前 5 个指标体系（LCR/NSFR/EVE/CET1/ROE）协同',
        '基于账户册结构 + 利率配置'),
]

for i, (a, b, c) in enumerate(refs):
    r = i + 2
    cell_a = ws_ref.cell(r, 1, a)
    cell_b = ws_ref.cell(r, 2, b)
    cell_c = ws_ref.cell(r, 3, c)

    if i == 0:
        for cell in (cell_a, cell_b, cell_c):
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = ALIGN_CENTER
            cell.border = THIN_BORDER
    else:
        cell_a.font = SUBHEADER_FONT
        cell_a.fill = SUBHEADER_FILL
        cell_a.alignment = ALIGN_CENTER
        cell_b.font = NORMAL_FONT
        cell_b.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        cell_c.font = NORMAL_FONT
        cell_c.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        for cell in (cell_a, cell_b, cell_c):
            cell.border = THIN_BORDER

    ws_ref.row_dimensions[r].height = 30

# ===========================
# 保存
# ===========================
wb.save(OUT)
print(f'已保存: {OUT}')
print(f'项目明细行数: {len(ROWS)}（55 账户册 + 1 所有者权益）')
print(f'折算依据行数: {len(refs)}')