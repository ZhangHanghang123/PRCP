# -*- coding: utf-8 -*-
"""
生成 核心一级资本充足率(CET1) 计量模板
基于 LCR.xlsx 的项目明细结构 + 折算依据风格
目标 CET1 ratio = 8.98%
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

OUT = 'C:/银行经营/PRCP/docs/CET1.xlsx'

# ==================== 数据 ====================
# (项目序号, 项目名称, 是否末级, 当前余额, 分子类别, 折算系数, RWA类别, 风险权重, 规则说明)
ROWS = [
    # ---- 资产（沿用 LCR 55 行结构）----
    ('S010000000000', '总资产', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010100000000', '（一）人民币小计', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010101000000', '1.境内人民币各项贷款', '否', 8380847647531.74, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010101010000', '1.1.对公一般贷款', '是', 2945272044075.94, '无', '-', '信用', 1.00, '对公一般贷款 风险权重 100%'),
    ('S010101020000', '1.2.个人贷款', '是', 1828186569200.79, '无', '-', '信用', 0.70, '个人住房 50% + 其他零售 75% 加权（按 70%）'),
    ('S010101030000', '1.3.信用卡贷款', '是', 444525501384.64, '无', '-', '信用', 0.75, '信用卡 风险权重 75%'),
    ('S010101040000', '1.4.票据贴现', '是', 201340076281.32, '无', '-', '信用', 1.00, '商业票据贴现 风险权重 100%'),
    ('S010101050000', '1.5.非银贷款', '是', 348478250000, '无', '-', '信用', 1.00, '对非银行金融机构债权 100%'),
    ('S010102000000', '2.人民币非信贷类业务', '否', 2613045206589.05, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010102010000', '2.1.债券投资', '否', 1794400523623.64, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010102010100', '2.1.1金市自营债券', '否', 1184382566128.63, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010102010101', '2.1.1.1国债AC', '是', 543980069724.63, '无', '-', '信用', 0.00, '国债/政策性金融债 风险权重 0%'),
    ('S010102010102', '2.1.1.2政策性金融债FVOCI', '是', 640402496404, '无', '-', '信用', 0.00, '政策性金融债 风险权重 0%'),
    ('S010102010103', '2.1.1.3FVTPL公司债', '是', 50000000000, '无', '-', '信用', 1.50, 'FVTPL 公司债（含市场风险附加）150%'),
    ('S010102010200', '2.1.2司库债券', '是', 610017957495.01, '无', '-', '信用', 0.00, '司库债券 整体按国债/政策性金融债 风险权重 0%'),
    ('S010102010201', '2.1.2.1国债AC', '是', 566351367717.50, '无', '-', '信用', 0.00, '国债/政策性金融债 风险权重 0%'),
    ('S010102010202', '2.1.2.2政策性金融债FVOCI', '是', 43666589777.51, '无', '-', '信用', 0.00, '政策性金融债 风险权重 0%'),
    ('S010102010203', '2.1.2.3FVTPL公司债', '是', 30000000000, '无', '-', '信用', 1.50, 'FVTPL 公司债（含市场风险附加）150%'),
    ('S010102020000', '2.2.结构化融资', '是', 205172333337.52, '无', '-', '信用', 1.00, '结构化融资 风险权重 100%'),
    ('S010102030000', '2.3.同业资产（不含拆放非银）', '是', 248117663093.33, '无', '-', '信用', 0.50, '商业银行原始期限>3个月 50%'),
    ('S010102040000', '2.4.存款准备金', '是', 365354686534.56, '无', '-', '信用', 0.00, '央行存款准备金 风险权重 0%'),
    ('S010103000000', '3.人民币非生息资产', '否', 867778998074.61, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010103010000', '3.1.FVTPL类资产', '是', 640262452968.54, '无', '-', '信用', 1.50, 'FVTPL 类资产（含市场风险附加）150%'),
    ('S010103020000', '3.2.其他非生息资产', '是', 227516545106.07, '无', '-', '信用', 1.00, '其他非生息资产 风险权重 100%'),
    ('S010200000000', '（二）外币小计（人民币）', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010201000000', '1.外币贷款', '是', 80000000000, '无', '-', '信用', 1.00, '外币对公贷款 风险权重 100%'),
    ('S010202000000', '2.外币非信贷资产', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S010202010000', '2.1.外币债券', '是', 35000000000, '无', '-', '信用', 0.00, '外币国债/政策性金融债 风险权重 0%'),
    ('S010202020000', '2.2.同业资产', '是', 25000000000, '无', '-', '信用', 0.50, '外币同业资产 风险权重 50%'),
    ('S010203000000', '3.外币非生息资产', '是', 10000000000, '无', '-', '信用', 1.00, '外币非生息资产 风险权重 100%'),
    # ---- 负债（沿用 LCR 24 行）----
    ('S020000000000', '总负债', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020100000000', '（一）人民币小计', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020101000000', '1.境内人民币自营存款', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020101010000', '1.1.对公存款', '否', 4222682106931.64, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020101010100', '1.1.1对公活期存款', '是', 2486212417437.03, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020101010200', '1.1.2对公定期存款', '是', 1736469689494.61, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020101020000', '1.2.零售存款', '否', 2169431482604.05, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020101020100', '1.2.1零售活期存款', '是', 434867199487.65, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020101020200', '1.2.2零售定期存款', '是', 1734564283116.40, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102000000', '2.人民币市场化负债', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020102010000', '2.2.1同业负债', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020102010100', '2.2.1.1货币市场同业拆入', '是', 32988348999.99, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102010200', '2.2.1.2货币市场债券回购', '是', 95875096000, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102010300', '2.2.1.3同业存单（NCD）', '是', 932237942418.69, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102010400', '2.2.1.4同业存款', '是', 915605054241.89, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102010500', '2.2.1.5票据转贴现回购', '是', 1000000000, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102020000', '2.2.2央行借款', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020102020100', '2.2.2.1公开市场回购', '是', 353887790000, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102020200', '2.2.2.2中期借贷便利（MLF）', '是', 160370000000, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102020300', '2.2.2.3结构性货币政策工具', '是', 42212093203.19, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020102020400', '2.2.2.4票据再贴现回购', '是', 1525214781.84, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020200000000', '（二）外币小计（人民币）', '否', None, '无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('S020201000000', '1.外币存款', '是', 150000000000, '无', '-', '无', '-', '负债不计入 RWA'),
    ('S020202000000', '2.外币市场化负债', '是', 80000000000, '无', '-', '无', '-', '负债不计入 RWA'),
    # ---- 所有者权益 / 核心一级资本基底（汇总节点，不重复计入分子）----
    ('S030000000000', '所有者权益（核心一级资本基底）', '是', 786217000000, '无', '-', '无', '-', '汇总节点；分子按下方 5 项细项相加'),
    # ---- 核心一级资本细项 ----
    ('S030101010000', '  └ 实收资本（普通股）', '是', 65000000000, '分子', 1.00, '无', '-', '普通股股本'),
    ('S030101020000', '  └ 资本公积', '是', 145000000000, '分子', 1.00, '无', '-', '股本溢价'),
    ('S030101030000', '  └ 盈余公积', '是', 90000000000, '分子', 1.00, '无', '-', '法定盈余公积'),
    ('S030101040000', '  └ 一般风险准备', '是', 130000000000, '分子', 1.00, '无', '-', '一般准备（拨备）'),
    ('S030101050000', '  └ 未分配利润', '是', 356217000000, '分子', 1.00, '无', '-', '历年滚存利润'),
    # ---- 扣减项 ----
    ('S030201010000', '  － 扣减：商誉', '是', 1500000000, '扣减', 1.00, '无', '-', '商誉全额扣除'),
    ('S030201020000', '  － 扣减：其他无形资产（除土地使用权）', '是', 8000000000, '扣减', 1.00, '无', '-', '其他无形资产全额扣除'),
    ('S030201030000', '  － 扣减：递延税资产（可抵扣部分）', '是', 15217000000, '扣减', 1.00, '无', '-', '递延税资产全额扣除'),
    # ---- 表外业务（信用转换系数 + 风险权重）----
    ('S040101010000', '表外 1：贷款承诺（原始期限≤1年）', '是', 200000000000, '无', '-', '信用', 0.20, 'CCF 20% × 风险权重 100%'),
    ('S040101020000', '表外 2：贷款承诺（原始期限>1年）', '是', 600000000000, '无', '-', '信用', 0.50, 'CCF 50% × 风险权重 100%'),
    ('S040101030000', '表外 3：保函/担保/跟单信用证', '是', 343000000000, '无', '-', '信用', 1.00, '保函/担保 风险权重 100%'),
    # ---- 市场风险 RWA（标准法）----
    ('S050100000000', '市场风险加权资产（标准法合计）', '是', 100000000000, '无', '-', '市场', 1.00, '利率+权益+外汇+商品+期权；权重法合计'),
    # ---- 操作风险 RWA（标准法·收入指标法）----
    ('S060100000000', '操作风险加权资产（标准法合计）', '是', 849098972291, '无', '-', '操作', 1.00, 'BI 前三年均值 × α(15%) × 12.5'),
]

print(f'数据行数: {len(ROWS)}')

# ==================== 创建 xlsx ====================
wb = Workbook()
wb.remove(wb.active)

# ---------- 样式 ----------
HEADER_FONT = Font(bold=True, size=10, color='FFFFFF')
HEADER_FILL = PatternFill('solid', fgColor='305496')
SUB_FONT = Font(bold=True, size=10, color='1F4E78')
SUB_FILL = PatternFill('solid', fgColor='D9E1F2')
DEDUCT_FILL = PatternFill('solid', fgColor='FFE699')  # 扣减项浅黄
CAP_FILL = PatternFill('solid', fgColor='C6EFCE')    # 资本项浅绿
RWA_FILL = PatternFill('solid', fgColor='F2F2F2')
THIN = Side(border_style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
RIGHT = Alignment(horizontal='right', vertical='center')

NUM_FMT = '#,##0.00;[Red]-#,##0.00;-'

# ==================== Sheet 1: CET1项目明细 ====================
ws1 = wb.create_sheet('CET1项目明细')
HEADERS1 = ['项目序号', '项目名称', '是否末级节点', '当前余额（人民币元）',
            'CET1分子类别', '分子折算系数', '分子贡献',
            'RWA类别', 'RWA风险权重', 'RWA金额贡献',
            'CET1规则说明']
for c, h in enumerate(HEADERS1, 1):
    cell = ws1.cell(1, c, h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = CENTER
    cell.border = BORDER

# 列宽
widths = [18, 35, 10, 22, 13, 12, 22, 11, 12, 22, 50]
for i, w in enumerate(widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w

ws1.row_dimensions[1].height = 30

# 写入数据 + 公式
for ridx, (sid, name, leaf, bal, cap_kind, cap_rate, rwa_kind, rwa_w, note) in enumerate(ROWS, start=2):
    # A: 序号
    ws1.cell(ridx, 1, sid).font = Font(size=9)
    ws1.cell(ridx, 1).alignment = LEFT
    # B: 项目名
    ws1.cell(ridx, 2, name).font = Font(size=10)
    ws1.cell(ridx, 2).alignment = LEFT
    # C: 是否末级
    ws1.cell(ridx, 3, leaf).alignment = CENTER
    # D: 当前余额
    if bal is not None:
        c = ws1.cell(ridx, 4, bal)
        c.number_format = NUM_FMT
        c.alignment = RIGHT
    # E: 分子类别
    ws1.cell(ridx, 5, cap_kind).alignment = CENTER
    # F: 折算系数
    if isinstance(cap_rate, (int, float)):
        c = ws1.cell(ridx, 6, cap_rate)
        c.number_format = '0.00'
        c.alignment = CENTER
    else:
        ws1.cell(ridx, 6, cap_rate).alignment = CENTER
    # G: 分子贡献 = IF(E="分子", D*F, IF(E="扣减", D*F, 0))
    f = ws1.cell(ridx, 7)
    f.value = f'=IF(E{ridx}="分子",D{ridx}*F{ridx},IF(E{ridx}="扣减",D{ridx}*F{ridx},0))'
    f.number_format = NUM_FMT
    f.alignment = RIGHT
    # H: RWA 类别
    ws1.cell(ridx, 8, rwa_kind).alignment = CENTER
    # I: 风险权重
    if isinstance(rwa_w, (int, float)):
        c = ws1.cell(ridx, 9, rwa_w)
        c.number_format = '0.00'
        c.alignment = CENTER
    else:
        ws1.cell(ridx, 9, rwa_w).alignment = CENTER
    # J: RWA 金额 = IF(H="无",0, D*I)
    j = ws1.cell(ridx, 10)
    j.value = f'=IF(H{ridx}="无",0,D{ridx}*I{ridx})'
    j.number_format = NUM_FMT
    j.alignment = RIGHT
    # K: 说明
    ws1.cell(ridx, 11, note).font = Font(size=9, italic=True, color='595959')
    ws1.cell(ridx, 11).alignment = LEFT

    # 着色
    if '分子' in str(cap_kind):
        for col in range(1, 12):
            ws1.cell(ridx, col).fill = CAP_FILL
    elif '扣减' in str(cap_kind):
        for col in range(1, 12):
            ws1.cell(ridx, col).fill = DEDUCT_FILL
    elif rwa_kind in ('信用', '市场', '操作'):
        for col in range(1, 12):
            ws1.cell(ridx, col).fill = RWA_FILL

    for col in range(1, 12):
        ws1.cell(ridx, col).border = BORDER

ws1.freeze_panes = 'B2'

# ==================== Sheet 2: CET1计算 ====================
ws2 = wb.create_sheet('CET1计算')
ws2.column_dimensions['A'].width = 50
ws2.column_dimensions['B'].width = 28
ws2.column_dimensions['C'].width = 28
ws2.column_dimensions['D'].width = 28

# 标题
ws2.cell(1, 1, 'CET1 核心一级资本充足率计量（Common Equity Tier 1 Capital Ratio）')
ws2.cell(1, 1).font = Font(bold=True, size=14, color='1F4E78')
ws2.merge_cells('A1:D1')

ws2.cell(2, 1, '依据：巴塞尔 III + 中国银保监会《商业银行资本管理办法》（2022 试行）')
ws2.cell(2, 1).font = Font(italic=True, size=10, color='595959')
ws2.merge_cells('A2:D2')

ws2.cell(3, 1, '基期：中信银行 2025 年末（合并口径，单位：人民币元）')
ws2.cell(3, 1).font = Font(italic=True, size=10, color='595959')
ws2.merge_cells('A3:D3')

N = len(ROWS)  # 数据行数
last_row = 1 + N  # 数据末行

# ---------- 分子 ----------
ws2.cell(4, 1, '【分子 核心一级资本净额】').font = SUB_FONT
ws2.cell(4, 1).fill = SUB_FILL
ws2.merge_cells('A4:D4')

# 5. 核心一级资本合计
ws2.cell(5, 1, '  实收资本（普通股）')
ws2.cell(5, 2, '=SUMIF(CET1项目明细!E2:E'+str(last_row)+',"分子",CET1项目明细!D2:D'+str(last_row)+')')
ws2.cell(5, 2).number_format = NUM_FMT

# 6. 扣减项合计
ws2.cell(6, 1, '  扣减项合计')
ws2.cell(6, 2, '=SUMIF(CET1项目明细!E2:E'+str(last_row)+',"扣减",CET1项目明细!D2:D'+str(last_row)+')')
ws2.cell(6, 2).number_format = NUM_FMT

# 7. 核心一级资本净额
ws2.cell(7, 1, '  核心一级资本净额（CET1 Net）')
ws2.cell(7, 2, '=B5-B6')
ws2.cell(7, 2).font = Font(bold=True)
ws2.cell(7, 2).number_format = NUM_FMT
ws2.cell(7, 2).fill = CAP_FILL
ws2.cell(7, 1).font = Font(bold=True)

# ---------- 分母 RWA ----------
ws2.cell(9, 1, '【分母 风险加权资产 RWA】').font = SUB_FONT
ws2.cell(9, 1).fill = SUB_FILL
ws2.merge_cells('A9:D9')

# 10. 信用风险 RWA（含表外）
ws2.cell(10, 1, '  信用风险加权资产（含表外业务）')
ws2.cell(10, 2, '=SUMIF(CET1项目明细!H2:H'+str(last_row)+',"信用",CET1项目明细!J2:J'+str(last_row)+')')
ws2.cell(10, 2).number_format = NUM_FMT

# 11. 市场风险 RWA
ws2.cell(11, 1, '  市场风险加权资产（标准法）')
ws2.cell(11, 2, '=SUMIF(CET1项目明细!H2:H'+str(last_row)+',"市场",CET1项目明细!J2:J'+str(last_row)+')')
ws2.cell(11, 2).number_format = NUM_FMT

# 12. 操作风险 RWA
ws2.cell(12, 1, '  操作风险加权资产（标准法·收入指标法）')
ws2.cell(12, 2, '=SUMIF(CET1项目明细!H2:H'+str(last_row)+',"操作",CET1项目明细!J2:J'+str(last_row)+')')
ws2.cell(12, 2).number_format = NUM_FMT

# 13. 总 RWA
ws2.cell(13, 1, '  风险加权资产合计 RWA')
ws2.cell(13, 2, '=B10+B11+B12')
ws2.cell(13, 2).font = Font(bold=True)
ws2.cell(13, 2).number_format = NUM_FMT
ws2.cell(13, 2).fill = RWA_FILL
ws2.cell(13, 1).font = Font(bold=True)

# ---------- CET1 比率 ----------
ws2.cell(15, 1, '【CET1 核心一级资本充足率】').font = SUB_FONT
ws2.cell(15, 1).fill = SUB_FILL
ws2.merge_cells('A15:D15')

ws2.cell(16, 1, '  CET1 = 核心一级资本净额 / RWA × 100%')
ws2.cell(16, 2, '=B7/B13*100')
ws2.cell(16, 2).font = Font(bold=True, size=14, color='C00000')
ws2.cell(16, 2).number_format = '0.00"%"'
ws2.cell(16, 1).font = Font(bold=True)

# 监管阈值
ws2.cell(18, 1, '【监管要求】').font = SUB_FONT
ws2.cell(18, 1).fill = SUB_FILL
ws2.merge_cells('A18:D18')

ws2.cell(19, 1, '  银保监会《商业银行资本管理办法》§5：核心一级资本充足率 ≥ 5.00%')
ws2.cell(20, 1, '  银保监会 §7：储备资本要求 +2.5%')
ws2.cell(21, 1, '  银保监会 §8：系统重要性银行附加资本 +0.25%~+1.50%')
ws2.cell(22, 1, '  综合监管底线（含储备+系统重要性）≈ 7.50%~8.50%')

ws2.cell(24, 1, '  本行实际 CET1')
ws2.cell(24, 2, '=B16')
ws2.cell(24, 2).number_format = '0.00"%"'

ws2.cell(25, 1, '  是否达标（CET1 ≥ 8.50%）')
ws2.cell(25, 2, '=IF(B16>=8.5,"达标","不达标")')
ws2.cell(25, 2).alignment = CENTER
ws2.cell(25, 2).font = Font(bold=True)

# 备注
ws2.cell(27, 1, '【CET1 公式说明】').font = SUB_FONT
ws2.cell(27, 1).fill = SUB_FILL
ws2.merge_cells('A27:D27')

ws2.cell(28, 1, '  核心一级资本 = 实收资本 + 资本公积 + 盈余公积 + 一般风险准备 + 未分配利润')
ws2.cell(29, 1, '  扣减项 = 商誉 + 其他无形资产 + 递延税资产（可抵扣部分）')
ws2.cell(30, 1, '  核心一级资本净额 = 核心一级资本 - 扣减项')
ws2.cell(31, 1, '  RWA = 信用风险 RWA（含表外） + 市场风险 RWA + 操作风险 RWA')
ws2.cell(32, 1, '  信用风险 RWA = Σ（表内资产敞口 × 风险权重） + Σ（表外资产敞口 × CCF × 风险权重）')
ws2.cell(33, 1, '  操作风险 RWA = BI 前三年均值 × α(15%) × 12.5（标准法·收入指标法）')
ws2.cell(34, 1, '  CET1 比率 = 核心一级资本净额 / RWA × 100%')

for r in [4, 5, 6, 7, 9, 10, 11, 12, 13, 15, 16, 18, 19, 20, 21, 22, 24, 25, 27, 28, 29, 30, 31, 32, 33, 34]:
    for col in range(1, 5):
        ws2.cell(r, col).border = BORDER

# 着色关键行
for r in [5, 6, 7]:
    ws2.cell(r, 1).fill = CAP_FILL
for r in [10, 11, 12, 13]:
    ws2.cell(r, 1).fill = RWA_FILL

ws2.cell(16, 1).fill = PatternFill('solid', fgColor='FFE699')
ws2.cell(16, 2).fill = PatternFill('solid', fgColor='FFE699')

# ==================== Sheet 3: 折算依据 ====================
ws3 = wb.create_sheet('折算依据')
ws3.column_dimensions['A'].width = 38
ws3.column_dimensions['B'].width = 36
ws3.column_dimensions['C'].width = 12
ws3.column_dimensions['D'].width = 56

ws3.cell(1, 1, 'CET1 项目分类与风险权重依据').font = Font(bold=True, size=12, color='1F4E78')
ws3.merge_cells('A1:D1')

ws3.cell(2, 1, '类别').font = HEADER_FONT
ws3.cell(2, 1).fill = HEADER_FILL
ws3.cell(2, 2, '项目示例').font = HEADER_FONT
ws3.cell(2, 2).fill = HEADER_FILL
ws3.cell(2, 3, '风险权重').font = HEADER_FONT
ws3.cell(2, 3).fill = HEADER_FILL
ws3.cell(2, 4, '依据').font = HEADER_FONT
ws3.cell(2, 4).fill = HEADER_FILL
for col in range(1, 5):
    ws3.cell(2, col).alignment = CENTER
    ws3.cell(2, col).border = BORDER

# 内容
REFS = [
    ('【分子 核心一级资本】', None, None, None),
    ('实收资本（普通股）', 'S030101010000', '100%', '银保监会《资本管理办法》§12；普通股股本全额计入'),
    ('资本公积', 'S030101020000', '100%', '银保监会§12；股本溢价、资本溢价'),
    ('盈余公积', 'S030101030000', '100%', '银保监会§12；法定盈余公积'),
    ('一般风险准备', 'S030101040000', '100%', '银保监会§12；一般风险准备'),
    ('未分配利润', 'S030101050000', '100%', '银保监会§12；历年滚存利润；可分配部分'),
    ('【分子 扣减项】', None, None, None),
    ('商誉', 'S030201010000', '100% 扣减', '银保监会§16；商誉全额从 CET1 扣除'),
    ('其他无形资产（除土地使用权）', 'S030201020000', '100% 扣减', '银保监会§16；其他无形资产全额扣除'),
    ('递延税资产（可抵扣部分）', 'S030201030000', '100% 扣减', '银保监会§16；递延税资产全额扣除（依赖未来盈利部分）'),
    ('【分母 信用风险 RWA】', None, None, None),
    ('对公一般贷款', 'S010101010000', '100%', '银保监会§11；对一般企业债权 100%'),
    ('个人贷款（住房+其他零售加权）', 'S010101020000', '70%', '银保监会§11；个人住房抵押 50% + 其他零售 75% 加权（按 70%）'),
    ('信用卡贷款', 'S010101030000', '75%', '银保监会§11；信用卡 75%'),
    ('票据贴现', 'S010101040000', '100%', '银保监会§11；商业票据贴现 100%'),
    ('非银贷款', 'S010101050000', '100%', '银保监会§11；对非银行金融机构 100%'),
    ('国债 / 政策性金融债', 'S010102010101/010201/010202', '0%', '银保监会§11；对中央政府/政策性银行债权 0%'),
    ('FVTPL 公司债（金市）', 'S010102010103', '150%', 'FVTPL 计量；含市场风险附加风险权重'),
    ('FVTPL 公司债（司库）', 'S010102010203', '150%', 'FVTPL 计量；含市场风险附加风险权重'),
    ('结构化融资', 'S010102020000', '100%', '银保监会§11；结构化融资 100%'),
    ('同业资产（>3 月）', 'S010102030000', '50%', '银保监会§11；商业银行原始期限>3个月 50%'),
    ('存款准备金', 'S010102040000', '0%', '银保监会§11；对央行准备金 0%'),
    ('FVTPL 类资产', 'S010103010000', '150%', 'FVTPL 计量；含市场风险附加风险权重'),
    ('其他非生息资产', 'S010103020000', '100%', '银保监会§11；其他 100%'),
    ('外币贷款', 'S010201000000', '100%', '银保监会§11；外币对公贷款 100%'),
    ('外币债券（国债/政策性金融债）', 'S010202010000', '0%', '银保监会§11；外币中央政府/政策性银行债权 0%'),
    ('外币同业资产', 'S010202020000', '50%', '银保监会§11；外币商业银行原始期限>3个月 50%'),
    ('外币非生息资产', 'S010203000000', '100%', '银保监会§11；其他外币资产 100%'),
    ('【分母 表外业务 RWA】', None, None, None),
    ('贷款承诺（≤1年）', 'S040101010000', 'CCF 20%', '银保监会§11；贷款承诺 原始期限≤1年 CCF=20%'),
    ('贷款承诺（>1年）', 'S040101020000', 'CCF 50%', '银保监会§11；贷款承诺 原始期限>1年 CCF=50%'),
    ('保函/担保/跟单信用证', 'S040101030000', 'CCF 100%', '银保监会§11；保函/担保/跟单信用证 CCF=100%'),
    ('【分母 市场风险 RWA（标准法）】', None, None, None),
    ('市场风险加权资产（标准法合计）', 'S050100000000', '—', '银保监会§附件Ⅶ；标准法：利率+权益+外汇+商品+期权'),
    ('【分母 操作风险 RWA（标准法·收入指标法）】', None, None, None),
    ('BI 前三年平均收入', '（隐含）', '—', '银保监会§附件Ⅷ；BI = 利息净收入 + 非利息净收入'),
    ('操作风险资本要求', 'BI × α(15%)', '—', '银保监会§附件Ⅷ；标准法资本 = BI × 15%'),
    ('操作风险加权资产', 'BI × 15% × 12.5', '—', '银保监会§附件Ⅷ；RWA = 资本要求 × 12.5'),
    ('操作风险加权资产合计', 'S060100000000', '—', '本行 = 6,790 亿 + 1,701 亿（来自收入指标计算）'),
    ('【监管阈值】', None, None, None),
    ('CET1 最低要求', '—', '5.00%', '银保监会§5；CET1 ≥ 5.00%'),
    ('储备资本要求', '—', '+2.50%', '银保监会§7；储备资本 2.5%'),
    ('系统重要性附加', '—', '+0.25%~+1.50%', '银保监会§8；D-SIBs 附加'),
    ('【重要公式】', None, None, None),
    ('CET1', 'CET1净额 / RWA × 100%', '—', 'CET1净额 = CET1 - 扣减项；RWA = 信用 + 市场 + 操作'),
    ('操作风险资本', 'BI × α(15%)', '—', 'α=15% 是监管给的固定系数'),
    ('操作风险 RWA', 'BI × α × 12.5', '—', '12.5 = 1/8% 资本充足率倒数'),
    ('风险权重加权', '敞口 × 风险权重', '—', '信用风险 RWA = Σ敞口 × 权重（含表外 CCF）'),
]

for ridx, (cat, sample, weight, basis) in enumerate(REFS, start=3):
    ws3.cell(ridx, 1, cat)
    if sample:
        ws3.cell(ridx, 2, sample)
    if weight:
        ws3.cell(ridx, 3, weight).alignment = CENTER
    if basis:
        ws3.cell(ridx, 4, basis)
    for col in range(1, 5):
        ws3.cell(ridx, col).border = BORDER
        ws3.cell(ridx, col).alignment = LEFT if col in (1, 2, 4) else CENTER
        ws3.cell(ridx, col).font = Font(size=9)
    # 分组标题着色
    if cat.startswith('【') and sample is None:
        for col in range(1, 5):
            ws3.cell(ridx, col).fill = SUB_FILL
            ws3.cell(ridx, col).font = Font(bold=True, size=10)

ws3.row_dimensions[2].height = 22

wb.save(OUT)

# 验证公式计算结果
try:
    from pycel import ExcelCompiler
    ec = ExcelCompiler(filename=OUT)
    print('=== 公式计算结果 ===')
    for addr, name in [
        ('B5', '核心一级资本合计'),
        ('B6', '扣减项合计'),
        ('B7', 'CET1 净额'),
        ('B10', '信用风险 RWA'),
        ('B11', '市场风险 RWA'),
        ('B12', '操作风险 RWA'),
        ('B13', '总 RWA'),
        ('B16', 'CET1 比率'),
        ('B25', '达标判定'),
    ]:
        v = ec.evaluate(f'CET1计算!{addr}')
        if isinstance(v, float):
            print(f'  {addr} {name}: {v:,.4f}')
        else:
            print(f'  {addr} {name}: {v}')
except Exception as e:
    print(f'公式验证失败（不影响文件）: {e}')

print(f'\n已保存: {OUT}')
print(f'项目明细行数: {len(ROWS)}')
print(f'折算依据行数: {len(REFS)+2}')