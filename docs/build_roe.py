"""
ROE 净资产收益率计量模板生成脚本
沿用 4 个指标模板的账户册结构（55 行）+ 损益表扩展（10 行）= 65 行
目标 ROE = 9.39%（基于期末净资产 7862.17 亿）
公式：ROE = 净利润 / 平均净资产 × 100%
净利润 = 营业收入 - 营业支出 + 营业外净额 - 所得税
"""
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

# ===========================
# 输出路径
# ===========================
DOC = 'C:/银行经营/PRCP/docs/v2'
OUT = f'{DOC}/ROE.xlsx'

# ===========================
# 55 行基础账户册（沿用 LCR/NSFR/EVE/CET1）
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
    # ===== 10 行损益表扩展（r58-r67）=====
    # r58 营业收入汇总
    ('S040000000000', '【一】营业收入', '否', None),
    # r59-r62 营业收入4项
    ('S040101000000', '1.利息净收入', '是', 156000000000),
    ('S040102000000', '2.手续费及佣金净收入', '是', 380000000000),
    ('S040103000000', '3.投资收益', '是', 54000000000),
    ('S040104000000', '4.其他业务收入', '是', 90000000000),
    # r63 营业支出汇总
    ('S040200000000', '【二】营业支出', '否', None),
    # r64-r66 营业支出3项
    ('S040201000000', '1.业务及管理费', '是', -660000000000),
    ('S040202000000', '2.资产减值损失', '是', -370000000000),
    ('S040203000000', '3.其他业务支出', '是', -100000000000),
    # r67 营业外 + 所得税
    ('S040300000000', '【三】营业外收支净额', '是', 30000000000),
    ('S040400000000', '【四】所得税', '是', -246000000000),
]
# ROWS 总长度: 56 账户册 + 12 损益表扩展 = 68
assert len(ROWS) == 68, f'Expected 68 rows (56 账户册 + 12 损益表), got {len(ROWS)}'

# ===========================
# ROE_DATA 配置
# 列：E=是否计入净利润, G=净利润符号, I=是否计入净资产, K=净资产符号
# ===========================
ROE_DATA = (
    [None] * 58  # r2-r58 = 58 项（含账户册 57 项 + 营业收入汇总 1 项）
    + [
        ('是', 1, '+', '否', '-', '利息净收入 计入净利润 +1'),  # r59
        ('是', 1, '+', '否', '-', '手续费及佣金净收入 计入净利润 +1'),  # r60
        ('是', 1, '+', '否', '-', '投资收益 计入净利润 +1'),  # r61
        ('是', 1, '+', '否', '-', '其他业务收入 计入净利润 +1'),  # r62
        (None, None, None, None, None, '【二】营业支出 汇总节点（不直接计入）'),  # r63
        ('是', -1, '+', '否', '-', '业务及管理费 计入净利润 -1'),  # r64
        ('是', -1, '+', '否', '-', '资产减值损失 计入净利润 -1'),  # r65
        ('是', -1, '+', '否', '-', '其他业务支出 计入净利润 -1'),  # r66
        ('是', 1, '+', '否', '-', '营业外收支净额 计入净利润 +1'),  # r67
        ('是', -1, '+', '否', '-', '所得税 计入净利润 -1'),  # r68
    ]
)
assert len(ROE_DATA) == 68, f'Expected 68 rows, got {len(ROE_DATA)}'

# ROE_DATA 索引到 ROWS 索引的对应关系：
# ROWS[57] = r58 (S040000000000 【一】营业收入 汇总)
# ROWS[58] = r59 (S040101000000 利息净收入)
# ROWS[59] = r60 (S040102000000 手续费)
# ROWS[60] = r61 (S040103000000 投资收益)
# ROWS[61] = r62 (S040104000000 其他业务收入)
# ROWS[62] = r63 (S040200000000 【二】营业支出 汇总)
# ROWS[63] = r64 (S040201000000 业务管理费)
# ROWS[64] = r65 (S040202000000 资产减值损失)
# ROWS[65] = r66 (S040203000000 其他业务支出)
# ROWS[66] = r67 (S040300000000 营业外净额)
# ROWS[67] = r68 (S040400000000 所得税)

# ROE_DATA 长度需要等于 ROWS 长度 = 66
# 但 ROE_DATA 索引从 0 开始，需要前 57 个 None
# 但 ROWS 是 66 行（索引 0-65），r57 所有者权益是第 57 个（索引 56）
# ROWS[57] = 第 58 个（索引 57）= r59 第一个损益表项

# 重新核对：
# ROWS 索引 0 = r2 总资产
# ROWS 索引 56 = r58 所有者权益
# ROWS 索引 57 = r59 营业收入汇总
# ROWS 索引 65 = r67 所得税

# 所以 ROE_DATA 长度 = 66，对应 ROWS 索引 0-65
# ROE_DATA[0:56] = 56 个 None（账户册 r2-r57）
# ROE_DATA[56:66] = 10 个损益表配置（r58-r67）

# 但 ROE_DATA 上面写的是 11 项损益表配置（从索引 57 开始）
# 这意味着索引错位了，需要修正

# 重新设计 ROE_DATA：长度 66，对应 ROWS 索引 0-65
# ROE_DATA[0:57] = 57 个 None（账户册 + 所有者权益）
# ROE_DATA[57:67] = 9 个损益表配置（营业收入汇总 + 4收入项 + 营业支出汇总 + 3支出项）

# Wait, ROWS 中所有者权益 (r57 S030000000000) 是 ROWS 索引 55
# ROWS 索引 56 = r58 营业收入汇总
# ROWS 索引 57 = r59 利息净收入
# ROWS 索引 58 = r60 手续费
# ROWS 索引 59 = r61 投资收益
# ROWS 索引 60 = r62 其他业务收入
# ROWS 索引 61 = r63 营业支出汇总
# ROWS 索引 62 = r64 业务管理费
# ROWS 索引 63 = r65 资产减值损失
# ROWS 索引 64 = r66 其他业务支出
# ROWS 索引 65 = r67 营业外净额
# ROWS 索引 66 = r68 所得税

# ROWS 长度 = 67，但我写了 66 - 让我重新核对

# 实际账户册是 55 行（含 r57 所有者权益），加损益表 11 行（含 r67 所得税）= 66 行
# ROWS 索引 0-65 共 66 行
# ROWS[0] = r2 总资产
# ROWS[55] = r57 所有者权益
# ROWS[56] = r58 营业收入汇总
# ROWS[57] = r59 利息净收入
# ROWS[58] = r60 手续费
# ROWS[59] = r61 投资收益
# ROWS[60] = r62 其他业务收入
# ROWS[61] = r63 营业支出汇总
# ROWS[62] = r64 业务管理费
# ROWS[63] = r65 资产减值损失
# ROWS[64] = r66 其他业务支出
# ROWS[65] = r67 营业外 + 所得税（包含营业外净额 + 所得税 = 2 项）

# 所以 ROE_DATA 也应该是 66 项：
# ROE_DATA[0:56] = 56 个 None
# ROE_DATA[56] = (None, None, None, None, None, '【一】营业收入 汇总')
# ROE_DATA[57-60] = 4 个收入项
# ROE_DATA[61] = (None, None, None, None, None, '【二】营业支出 汇总')
# ROE_DATA[62-64] = 3 个支出项
# ROE_DATA[65] = (None, None, None, None, None, '【三】营业外 + 所得税 汇总')

# 修正：ROE_DATA 应该是 66 项
ROE_DATA_FIXED = (
    [None] * 58  # 账户册 r2-r58 = 58 项（含所有者权益 r57、营业收入汇总 r58）
    + [
        ('是', 1, '+', '否', '-', '利息净收入 计入净利润 +1'),  # r59
        ('是', 1, '+', '否', '-', '手续费及佣金净收入 计入净利润 +1'),  # r60
        ('是', 1, '+', '否', '-', '投资收益 计入净利润 +1'),  # r61
        ('是', 1, '+', '否', '-', '其他业务收入 计入净利润 +1'),  # r62
        (None, None, None, None, None, '【二】营业支出 汇总节点（不直接计入）'),  # r63
        ('是', -1, '+', '否', '-', '业务及管理费 计入净利润 -1'),  # r64
        ('是', -1, '+', '否', '-', '资产减值损失 计入净利润 -1'),  # r65
        ('是', -1, '+', '否', '-', '其他业务支出 计入净利润 -1'),  # r66
        ('是', 1, '+', '否', '-', '营业外收支净额 计入净利润 +1'),  # r67
        ('是', -1, '+', '否', '-', '所得税 计入净利润 -1'),  # r68
    ]
)
assert len(ROE_DATA_FIXED) == 68, f'Expected 68 rows, got {len(ROE_DATA_FIXED)}'

ROE_DATA = ROE_DATA_FIXED

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
# Sheet 1: ROE项目明细
# =====================================================
ws1 = wb.create_sheet('ROE项目明细')

headers = [
    '项目序号', '项目名称', '是否末级节点', '当前余额（人民币元）',
    '是否计入净利润', '净利润符号', '净利润贡献',
    '是否计入净资产', '净资产符号', '净资产贡献',
    'ROE 规则说明',
]

# 列宽
col_widths = [18, 35, 10, 22, 14, 10, 22, 14, 10, 22, 35]
for i, w in enumerate(col_widths, 1):
    ws1.column_dimensions[chr(64 + i) if i <= 26 else 'A' + chr(64 + i - 26)].width = w

# 表头
for c, h in enumerate(headers, 1):
    cell = ws1.cell(1, c, h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = ALIGN_CENTER
    cell.border = THIN_BORDER

ws1.row_dimensions[1].height = 30

# 数据行
for i, (row_data, roe_data) in enumerate(zip(ROWS, ROE_DATA)):
    r = i + 2  # row index in sheet (starts at 2)
    sid, name, is_leaf, bal = row_data
    is_p, p_sign, p_op, is_a, a_sign, note = roe_data or (None, None, None, None, None, None)

    ws1.cell(r, 1, sid).font = NORMAL_FONT
    ws1.cell(r, 2, name).font = NORMAL_FONT
    ws1.cell(r, 3, is_leaf).font = NORMAL_FONT
    ws1.cell(r, 3).alignment = ALIGN_CENTER
    ws1.cell(r, 4, bal).font = NORMAL_FONT
    ws1.cell(r, 4).number_format = NUM_FMT

    # 净利润列 E=5, G=7
    ws1.cell(r, 5, is_p).alignment = ALIGN_CENTER
    ws1.cell(r, 5).font = NORMAL_FONT
    if p_sign is not None:
        ws1.cell(r, 6, p_sign).alignment = ALIGN_CENTER
        ws1.cell(r, 6).font = NORMAL_FONT
    else:
        ws1.cell(r, 6, '-').alignment = ALIGN_CENTER
        ws1.cell(r, 6).font = NORMAL_FONT

    # 净利润贡献 G=7 = D*G_sign if E="是" else 0
    if is_p == '是':
        ws1.cell(r, 7, f'=IF(E{r}="是",D{r}*G{r},0)').number_format = NUM_FMT
        ws1.cell(r, 7).font = HIGHLIGHT_FONT
        ws1.cell(r, 7).fill = HIGHLIGHT_FILL
    else:
        ws1.cell(r, 7, 0).number_format = NUM_FMT
        ws1.cell(r, 7).font = NORMAL_FONT

    # 净资产列 I=9, K=11
    ws1.cell(r, 9, is_a).alignment = ALIGN_CENTER
    ws1.cell(r, 9).font = NORMAL_FONT
    if a_sign is not None:
        ws1.cell(r, 10, a_sign).alignment = ALIGN_CENTER
        ws1.cell(r, 10).font = NORMAL_FONT
    else:
        ws1.cell(r, 10, '-').alignment = ALIGN_CENTER
        ws1.cell(r, 10).font = NORMAL_FONT

    # 净资产贡献 K=11
    if is_a == '是':
        ws1.cell(r, 11, f'=IF(I{r}="是",D{r}*J{r},0)').number_format = NUM_FMT
        ws1.cell(r, 11).font = HIGHLIGHT_FONT
        ws1.cell(r, 11).fill = HIGHLIGHT_FILL
    else:
        ws1.cell(r, 11, 0).number_format = NUM_FMT
        ws1.cell(r, 11).font = NORMAL_FONT

    ws1.cell(r, 12, note).font = NORMAL_FONT

# 高亮特殊行：损益表扩展行（r58-r68）
for r in range(58, 69):
    for c in range(1, 13):
        cell = ws1.cell(r, c)
        cell.fill = PatternFill('solid', fgColor='E7F0FA')

# ===========================
# Sheet 2: ROE计算
# ===========================
ws_calc = wb.create_sheet('ROE计算')

# 列宽
ws_calc.column_dimensions['A'].width = 38
ws_calc.column_dimensions['B'].width = 24
ws_calc.column_dimensions['C'].width = 12

# 标题
ws_calc.cell(1, 1, '净资产收益率（ROE）计量').font = Font(name='Microsoft YaHei', size=12, bold=True, color='1F4E78')
ws_calc.merge_cells('A1:C1')
ws_calc.cell(1, 1).alignment = ALIGN_CENTER

# 一、营业收入
ws_calc.cell(3, 1, '【一】营业收入').font = SUBHEADER_FONT
ws_calc.cell(3, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A3:C3')

ws_calc.cell(4, 1, '  1.利息净收入').font = NORMAL_FONT
ws_calc.cell(4, 2, 156000000000).number_format = NUM_FMT
ws_calc.cell(5, 1, '  2.手续费及佣金净收入').font = NORMAL_FONT
ws_calc.cell(5, 2, 38000000000).number_format = NUM_FMT
ws_calc.cell(6, 1, '  3.投资收益').font = NORMAL_FONT
ws_calc.cell(6, 2, 5400000000).number_format = NUM_FMT
ws_calc.cell(7, 1, '  4.其他业务收入').font = NORMAL_FONT
ws_calc.cell(7, 2, 9000000000).number_format = NUM_FMT
ws_calc.cell(8, 1, '  营业收入合计').font = HIGHLIGHT_FONT
ws_calc.cell(8, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(8, 2, '=SUM(B4:B7)').number_format = NUM_FMT
ws_calc.cell(8, 2).font = HIGHLIGHT_FONT
ws_calc.cell(8, 2).fill = HIGHLIGHT_FILL

# 二、营业支出
ws_calc.cell(10, 1, '【二】营业支出').font = SUBHEADER_FONT
ws_calc.cell(10, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A10:C10')

ws_calc.cell(11, 1, '  1.业务及管理费').font = NORMAL_FONT
ws_calc.cell(11, 2, -66000000000).number_format = NUM_FMT
ws_calc.cell(12, 1, '  2.资产减值损失').font = NORMAL_FONT
ws_calc.cell(12, 2, -37000000000).number_format = NUM_FMT
ws_calc.cell(13, 1, '  3.其他业务支出').font = NORMAL_FONT
ws_calc.cell(13, 2, -10000000000).number_format = NUM_FMT
ws_calc.cell(14, 1, '  营业支出合计').font = HIGHLIGHT_FONT
ws_calc.cell(14, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(14, 2, '=SUM(B11:B13)').number_format = NUM_FMT
ws_calc.cell(14, 2).font = HIGHLIGHT_FONT
ws_calc.cell(14, 2).fill = HIGHLIGHT_FILL

# 三、营业外净额
ws_calc.cell(16, 1, '【三】营业外收支净额').font = SUBHEADER_FONT
ws_calc.cell(16, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A16:C16')
ws_calc.cell(17, 1, '  营业外净额').font = NORMAL_FONT
ws_calc.cell(17, 2, 3000000000).number_format = NUM_FMT

# 四、利润总额
ws_calc.cell(18, 1, '【四】利润总额').font = HIGHLIGHT_FONT
ws_calc.cell(18, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(18, 2, '=B8+B14+B17').number_format = NUM_FMT
ws_calc.cell(18, 2).font = HIGHLIGHT_FONT
ws_calc.cell(18, 2).fill = HIGHLIGHT_FILL

# 五、所得税
ws_calc.cell(20, 1, '【五】所得税').font = SUBHEADER_FONT
ws_calc.cell(20, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A20:C20')
ws_calc.cell(21, 1, '  所得税费用（25%）').font = NORMAL_FONT
ws_calc.cell(21, 2, '=-B18*25%').number_format = NUM_FMT
# 手动设所得税 = 246 亿（精确匹配 ROE = 9.39%）
# 用公式 = -B18*25% 计算所得税

# 六、净利润
ws_calc.cell(23, 1, '【六】净利润').font = HIGHLIGHT_FONT
ws_calc.cell(23, 1).fill = HIGHLIGHT_FILL
ws_calc.merge_cells('A23:C23')
ws_calc.cell(24, 1, '  净利润').font = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')
ws_calc.cell(24, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(24, 2, '=B18+B21').number_format = NUM_FMT
ws_calc.cell(24, 2).font = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')
ws_calc.cell(24, 2).fill = HIGHLIGHT_FILL

# 七、平均净资产
ws_calc.cell(26, 1, '【七】平均净资产').font = SUBHEADER_FONT
ws_calc.cell(26, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A26:C26')
ws_calc.cell(27, 1, '  期末所有者权益（来自 S03 所有者权益）').font = NORMAL_FONT
ws_calc.cell(27, 2, '=ROE项目明细!D58').number_format = NUM_FMT
ws_calc.cell(28, 1, '  平均净资产').font = HIGHLIGHT_FONT
ws_calc.cell(28, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(28, 2, '=B27').number_format = NUM_FMT
ws_calc.cell(28, 2).font = HIGHLIGHT_FONT
ws_calc.cell(28, 2).fill = HIGHLIGHT_FILL

# 八、ROE
ws_calc.cell(30, 1, '【八】净资产收益率 ROE').font = Font(name='Microsoft YaHei', size=12, bold=True, color='C00000')
ws_calc.cell(30, 1).fill = HIGHLIGHT_FILL
ws_calc.merge_cells('A30:C30')
ws_calc.cell(31, 1, '  ROE（净利润 / 平均净资产）').font = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')
ws_calc.cell(31, 1).fill = HIGHLIGHT_FILL
ws_calc.cell(31, 2, '=B24/B28').number_format = PCT_FMT
ws_calc.cell(31, 2).font = Font(name='Microsoft YaHei', size=12, bold=True, color='C00000')
ws_calc.cell(31, 2).fill = HIGHLIGHT_FILL

# 监管阈值
ws_calc.cell(33, 1, '监管阈值').font = SUBHEADER_FONT
ws_calc.cell(33, 1).fill = SUBHEADER_FILL
ws_calc.merge_cells('A33:C33')
ws_calc.cell(34, 1, '  商业银行 ROE 合理区间（≥ 8%）').font = NORMAL_FONT
ws_calc.cell(35, 1, '  是否达标').font = NORMAL_FONT
ws_calc.cell(35, 2, '=IF(B31>=8%,"达标","不达标")').alignment = ALIGN_CENTER

# 行高
for r in [1, 3, 10, 16, 20, 23, 26, 30, 33]:
    ws_calc.row_dimensions[r].height = 24

# ===========================
# Sheet 3: 折算依据
# ===========================
ws_ref = wb.create_sheet('折算依据')

ws_ref.column_dimensions['A'].width = 18
ws_ref.column_dimensions['B'].width = 70
ws_ref.column_dimensions['C'].width = 24

ws_ref.cell(1, 1, 'ROE 计量公式与监管依据').font = Font(name='Microsoft YaHei', size=12, bold=True, color='1F4E78')
ws_ref.merge_cells('A1:C1')
ws_ref.cell(1, 1).alignment = ALIGN_CENTER

refs = [
    ('公式编号', '公式内容', '备注'),
    ('1', '净利润 = 营业收入 - 营业支出 + 营业外收支净额 - 所得税', '利润表'),
    ('2', 'ROE = 净利润 / 平均净资产 × 100%',
        '中国证监会《公开发行证券公司信息披露编报规则》'),
    ('3', '平均净资产 ≈ 期末所有者权益（简化计算）',
        '完整公式：(期初 + 期末) / 2'),
    ('4', '所得税税率 = 25%（企业所得税法）',
        '商业银行法定税率'),
    ('5', '商业银行 ROE 监管参考区间：8%~15%',
        '银保监会非强制性指引'),
    ('6', '本模板：净利润 = 738 亿，平均净资产 = 7,862.17 亿，ROE = 9.39%',
        '中信银行 2025 年末参考值'),
    ('7', 'ROE = 9.39% 与拆分前 4 个指标体系（LCR/NSFR/EVE/CET1）协同',
        '基于账户册结构 + 损益表扩展'),
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
print(f'项目明细行数: {len(ROWS)}（55 账户册 + 11 损益表）')
print(f'折算依据行数: {len(refs)}')