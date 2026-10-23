# -*- coding: utf-8 -*-
"""
统一重建 LCR/NSFR/EVE/CET1 四个计量模板（含 r25 拆分）
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

DOC = 'C:/银行经营/PRCP/docs'
OUT_DIR = 'C:/银行经营/PRCP/docs/v2'

HEADER_FONT = Font(bold=True, size=10, color='FFFFFF')
HEADER_FILL = PatternFill('solid', fgColor='305496')
SUB_FONT = Font(bold=True, size=10, color='1F4E78')
SUB_FILL = PatternFill('solid', fgColor='D9E1F2')
DEDUCT_FILL = PatternFill('solid', fgColor='FFE699')
CAP_FILL = PatternFill('solid', fgColor='C6EFCE')
RWA_FILL = PatternFill('solid', fgColor='F2F2F2')
THIN = Side(border_style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
RIGHT = Alignment(horizontal='right', vertical='center')
NUM_FMT = '#,##0.00;[Red]-#,##0.00;-'

# 账户册数据（含 3.2 拆分）
ROWS = [
    ('S010000000000', '总资产', '否', None),
    ('S010100000000', '（一）人民币小计', '否', None),
    ('S010101000000', '1.境内人民币各项贷款', '否', 8380847647531.74),
    ('S010101010000', '1.1.对公一般贷款', '是', 2945272044075.94),
    ('S010101020000', '1.2.个人贷款', '是', 1828186569200.79),
    ('S010101030000', '1.3.信用卡贷款', '是', 444525501384.64),
    ('S010101040000', '1.4.票据贴现', '是', 201340076281.32),
    ('S010101050000', '1.5.非银贷款', '是', 348478250000),
    ('S010102000000', '2.人民币非信贷类业务', '否', 2613045206589.05),
    ('S010102010000', '2.1.债券投资', '否', 1794400523623.64),
    ('S010102010100', '2.1.1金市自营债券', '否', 1184382566128.63),
    ('S010102010101', '2.1.1.1AC', '是', 543980069724.63),
    ('S010102010102', '2.1.1.2FVOCI', '是', 640402496404),
    ('S010102010103', '2.1.1.3FVTPL', '是', 50000000000),
    ('S010102010200', '2.1.2司库债券', '否', 610017957495.01),
    ('S010102010201', '2.1.2.1AC', '是', 566351367717.50),
    ('S010102010202', '2.1.2.2FVOCI', '是', 43666589777.51),
    ('S010102010203', '2.1.2.3FVTPL', '是', 30000000000),
    ('S010102020000', '2.2.结构化融资', '是', 205172333337.52),
    ('S010102030000', '2.3.同业资产（不含拆放非银）', '是', 248117663093.33),
    ('S010102040000', '2.4.存款准备金', '是', 365354686534.56),
    ('S010103000000', '3.人民币非生息资产', '否', 867778998074.61),
    ('S010103010000', '3.1.FVTPL类资产', '是', 640262452968.54),
    ('S010103020000', '3.2.其他非生息资产', '否', 227516545106.07),
    ('S010103020100', '3.2.1. 其中：现金', '是', 127516545106),
    ('S010103020200', '3.2.2. 其中：其它', '是', 100000000000),
    ('S010200000000', '（二）外币小计（美元）', '否', None),
    ('S010201000000', '1.外币贷款', '是', 80000000000),
    ('S010202000000', '2.外币非信贷资产', '否', None),
    ('S010202010000', '2.1.外币债券', '是', 35000000000),
    ('S010202020000', '2.2.同业资产', '是', 25000000000),
    ('S010203000000', '3.外币非生息资产', '是', 10000000000),
    ('S020000000000', '总负债', '否', None),
    ('S020100000000', '（一）人民币小计', '否', None),
    ('S020101000000', '1.境内人民币自营存款', '否', None),
    ('S020101010000', '1.1.对公存款', '否', 4222682106931.64),
    ('S020101010100', '1.1.1对公活期存款', '是', 2486212417437.03),
    ('S020101010200', '1.1.2对公定期存款', '是', 1736469689494.61),
    ('S020101020000', '1.2.零售存款', '否', 2169431482604.05),
    ('S020101020100', '1.2.1零售活期存款', '是', 434867199487.65),
    ('S020101020200', '1.2.2零售定期存款', '是', 1734564283116.40),
    ('S020102000000', '2.人民币市场化负债', '否', None),
    ('S020102010000', '2.2.1同业负债', '否', None),
    ('S020102010100', '2.2.1.1货币市场同业拆入', '是', 32988348999.99),
    ('S020102010200', '2.2.1.2货币市场债券回购', '是', 95875096000),
    ('S020102010300', '2.2.1.3同业存单（NCD）', '是', 932237942418.69),
    ('S020102010400', '2.2.1.4同业存款', '是', 915605054241.89),
    ('S020102010500', '2.2.1.5票据转贴现回购', '是', 1000000000),
    ('S020102020000', '2.2.2央行借款', '否', None),
    ('S020102020100', '2.2.2.1公开市场回购（买断）', '是', 353887790000),
    ('S020102020200', '2.2.2.2中期借贷便利（MLF）', '是', 160370000000),
    ('S020102020300', '2.2.2.3结构性货币政策工具', '是', 42212093203.19),
    ('S020102020400', '2.2.2.4票据再贴现回购', '是', 1525214781.84),
    ('S020200000000', '（二）外币小计（美元）', '否', None),
    ('S020201000000', '1.外币存款', '是', 150000000000),
    ('S020202000000', '2.外币市场化负债', '是', 80000000000),
    ('S030000000000', '所有者权益', '是', 786217000000),
]

# ============= LCR 配置 =============
LCR_DATA = [
    # (是否分子, F, G, 是否分母, I, J, 备注)
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 1, '-', '对公一般贷款 流入 100%'),
    ('否', '-', '-', '是', 0.5, '-', '个人贷款 流入 50%'),
    ('否', '-', '-', '是', 0.5, '-', '信用卡 流入 50%'),
    ('否', '-', '-', '是', 1, '-', '票据贴现 流入 100%'),
    ('否', '-', '-', '是', 1, '-', '非银贷款 流入 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('是', 1, '+', '否', '-', '-', '国债 AC Level 1 HQLA 折算 100%'),
    ('是', 1, '+', '否', '-', '-', '政策性金融债 FVOCI Level 1 HQLA 折算 100%'),
    (None, None, None, None, None, None, 'FVTPL公司债 不计入'),
    (None, None, None, None, None, None, '司库债券 汇总'),
    ('是', 1, '+', '否', '-', '-', '国债 AC Level 1 HQLA 折算 100%'),
    ('是', 1, '+', '否', '-', '-', '政策性金融债 FVOCI Level 1 HQLA 折算 100%'),
    ('是', 0.85, '+', '否', '-', '-', 'FVTPL公司债 Level 2A HQLA 折算 85%'),
    ('否', '-', '-', '是', 1, '-', '结构化融资 流入 100%'),
    ('否', '-', '-', '是', 1, '-', '同业资产 流入 100%'),
    ('是', 1, '+', '否', '-', '-', '存款准备金 Level 1 HQLA 折算 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, 'FVTPL类资产 不计入'),
    (None, None, None, None, None, None, '汇总节点 3.2.其他非生息资产'),
    ('是', 1, '+', '否', '-', '-', '库存现金 Level 1 HQLA 折算 100%'),
    ('否', '-', '-', '是', 1, '-', '其它非生息资产 分母流入 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 1, '-', '外币贷款 流入 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 1, '-', '外币债券 流入 100%'),
    ('否', '-', '-', '是', 1, '-', '外币同业 流入 100%'),
    ('否', '-', '-', '是', 0.5, '-', '外币非生息资产 流入 50%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 0.35, '+', '对公活期 流出 35%（业务关系 25%+无保险 35% 加权）'),
    ('否', '-', '-', '是', 1, '+', '对公定期 流出 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 0.08, '+', '零售活期 流出 8%'),
    ('否', '-', '-', '是', 1, '+', '零售定期 流出 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 1, '+', '同业拆入 流出 100%'),
    ('否', '-', '-', '是', 0.25, '+', '债券回购（信用债抵押）流出 25%'),
    ('否', '-', '-', '是', 1, '+', '同业存单 NCD 流出 100%'),
    ('否', '-', '-', '是', 1, '+', '同业存款 流出 100%'),
    ('否', '-', '-', '是', 0.25, '+', '票据转贴现回购（信用债抵押）流出 25%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 0, '+', '公开市场回购（国债抵押）流出 0%'),
    ('否', '-', '-', '是', 0, '+', 'MLF 流出 0%（折算调整，临近到期）'),
    ('否', '-', '-', '是', 0, '+', '结构性货币政策工具 流出 0%'),
    ('否', '-', '-', '是', 0, '+', '票据再贴现回购（国债抵押）流出 0%'),
    (None, None, None, None, None, None, '汇总节点不参与 LCR 计算'),
    ('否', '-', '-', '是', 0, '+', '外币存款 流出 0%'),
    ('否', '-', '-', '是', 0, '+', '外币市场化负债 流出 0%'),
    (None, None, None, None, None, None, '所有者权益 不计入 LCR 分子分母'),
]

# NSFR 配置
NSFR_DATA = [
    # (是否ASF, F, G, 是否RSF, I, J, 备注)
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('否', '-', '-', '是', 1, '+', '对公一般贷款 RSF 100%'),
    ('否', '-', '-', '是', 0.85, '+', '个人贷款 RSF 85%'),
    ('否', '-', '-', '是', 0.85, '+', '信用卡 RSF 85%'),
    ('否', '-', '-', '是', 0.85, '+', '票据贴现 RSF 85%'),
    ('否', '-', '-', '是', 1, '+', '非银贷款 RSF 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('是', 0, '+', '否', '-', '-', '国债 AC 不计入 ASF；RSF 0%（高流动性）'),
    ('是', 0, '+', '否', '-', '-', '政策性金融债 FVOCI 不计入 ASF；RSF 0%'),
    ('否', '-', '-', '是', 1, '+', 'FVTPL类资产 RSF 100%'),
    (None, None, None, None, None, None, '司库债券 汇总'),
    ('是', 0, '+', '否', '-', '-', '国债 AC 不计入 ASF；RSF 0%'),
    ('是', 0, '+', '否', '-', '-', '政策性金融债 FVOCI 不计入 ASF；RSF 0%'),
    ('否', '-', '-', '是', 1, '+', 'FVTPL类资产 RSF 100%'),
    ('否', '-', '-', '是', 1, '+', '结构化融资 RSF 100%'),
    ('否', '-', '-', '是', 0.5, '+', '同业资产 RSF 50%'),
    ('否', '-', '-', '是', 0, '+', '存款准备金 RSF 0%（央行）'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('否', '-', '-', '是', 1, '+', 'FVTPL类资产 RSF 100%'),
    (None, None, None, None, None, None, '汇总节点 3.2.其他非生息资产'),
    ('否', '-', '-', '是', 0, '+', '库存现金 RSF 0%（高流动性）'),
    ('否', '-', '-', '是', 0.5, '+', '其它非生息资产 RSF 50%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('否', '-', '-', '是', 1, '+', '外币贷款 RSF 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('否', '-', '-', '是', 0, '+', '外币国债 RSF 0%'),
    ('否', '-', '-', '是', 0.5, '+', '外币同业 RSF 50%'),
    ('否', '-', '-', '是', 1, '+', '外币非生息资产 RSF 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('是', 0.35, '+', '否', '-', '-', '对公活期 ASF 35%（合规最低，业务关系加权）'),
    ('是', 1, '+', '否', '-', '-', '对公定期 ASF 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('是', 0.95, '+', '否', '-', '-', '零售活期 ASF 95%'),
    ('是', 1, '+', '否', '-', '-', '零售定期 ASF 100%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('是', 0, '+', '否', '-', '-', '同业拆入（短期）ASF 0%'),
    ('是', 0, '+', '否', '-', '-', '债券回购 ASF 0%'),
    ('是', 0.5, '+', '否', '-', '-', '同业存单 ASF 50%（6-12 月）'),
    ('是', 0.5, '+', '否', '-', '-', '同业存款 ASF 50%'),
    ('是', 0, '+', '否', '-', '-', '票据转贴现 ASF 0%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('是', 0, '+', '否', '-', '-', '公开市场回购 ASF 0%'),
    ('是', 1, '+', '否', '-', '-', 'MLF ASF 100%'),
    ('是', 1, '+', '否', '-', '-', '结构性货币政策工具 ASF 100%'),
    ('是', 0, '+', '否', '-', '-', '票据再贴现 ASF 0%'),
    (None, None, None, None, None, None, '汇总节点不参与 NSFR 计算'),
    ('是', 1, '+', '否', '-', '-', '外币存款 ASF 100%'),
    ('是', 1, '+', '否', '-', '-', '外币市场化负债 ASF 100%'),
    ('是', 1, '+', '否', '-', '-', '所有者权益 ASF 100%（Tier 1 资本）'),
]

# EVE 配置：类别 (asset/liab/equity/汇总), 类型, 久期
EVE_DATA = [
    # (类别, 类型, 久期)
    ('汇总', None, None),
    ('汇总', None, None),
    ('汇总', None, None),
    ('asset', '贷款', 2.0),
    ('asset', '贷款', 1.05),
    ('asset', '贷款', 1.5),
    ('asset', '贷款', 0.5),
    ('asset', '贷款', 1.5),
    ('汇总', None, None),
    ('汇总', None, None),
    ('汇总', None, None),
    ('asset', '债券', 3.5),
    ('asset', '债券', 4.0),
    ('asset', '债券', 3.0),
    ('汇总', None, None),
    ('asset', '债券', 3.5),
    ('asset', '债券', 4.0),
    ('asset', '债券', 3.0),
    ('asset', '结构化', 3.0),
    ('asset', '同业', 1.0),
    ('asset', '利率', 0.0),
    ('汇总', None, None),
    ('asset', 'FVTPL', 2.0),
    ('汇总', None, None),
    ('asset', '现金', 0.0),
    ('asset', '无息', 0.0),
    ('汇总', None, None),
    ('asset', '贷款', 2.0),
    ('汇总', None, None),
    ('asset', '债券', 3.5),
    ('asset', '同业', 1.0),
    ('asset', '无息', 0.25),
    ('汇总', None, None),
    ('汇总', None, None),
    ('汇总', None, None),
    ('汇总', None, None),
    ('liab', '活期', 1.0),
    ('liab', '定期', 2.0),
    ('汇总', None, None),
    ('liab', '活期', 1.0),
    ('liab', '定期', 2.5),
    ('汇总', None, None),
    ('汇总', None, None),
    ('liab', '同业', 0.5),
    ('liab', '回购', 0.25),
    ('liab', 'NCD', 1.0),
    ('liab', '同业', 1.0),
    ('liab', '回购', 0.25),
    ('汇总', None, None),
    ('liab', '回购', 0.0),
    ('liab', 'MLF', 2.0),
    ('liab', '结构性', 2.0),
    ('liab', '再贴现', 0.05),
    ('汇总', None, None),
    ('liab', '外币', 1.5),
    ('liab', '外币', 0.5),
    ('equity', '永久', 0),
]

# CET1 配置：分子类别 / RWA类别 / 风险权重
CET1_DATA = [
    # (分子类别, 折算系数, RWA类别, 风险权重, 备注)
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '信用', 1.00, '对公一般贷款 风险权重 100%'),
    ('无', '-', '信用', 0.70, '个人贷款（房贷50% + 其他零售75% 加权 70%）'),
    ('无', '-', '信用', 0.75, '信用卡 风险权重 75%'),
    ('无', '-', '信用', 1.00, '商业票据贴现 风险权重 100%'),
    ('无', '-', '信用', 1.00, '非银贷款 风险权重 100%'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '信用', 0.00, '国债 AC 风险权重 0%'),
    ('无', '-', '信用', 0.00, '政策性金融债 FVOCI 风险权重 0%'),
    ('无', '-', '信用', 1.50, 'FVTPL 公司债 150%（含市场风险附加）'),
    ('无', '-', '信用', 0.00, '司库债券 整体按国债/政策性金融债 0%'),
    ('无', '-', '信用', 0.00, '国债 AC 风险权重 0%'),
    ('无', '-', '信用', 0.00, '政策性金融债 FVOCI 风险权重 0%'),
    ('无', '-', '信用', 1.50, 'FVTPL 公司债 150%（含市场风险附加）'),
    ('无', '-', '信用', 1.00, '结构化融资 风险权重 100%'),
    ('无', '-', '信用', 0.50, '商业银行原始期限>3月 50%'),
    ('无', '-', '信用', 0.00, '央行存款准备金 风险权重 0%'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '信用', 1.50, 'FVTPL 类资产 150%（含市场风险附加）'),
    ('无', '-', '无', '-', '汇总节点 3.2.其他非生息资产'),
    ('无', '-', '信用', 0.00, '库存现金 风险权重 0%'),
    ('无', '-', '信用', 1.00, '其它非生息资产 风险权重 100%'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '信用', 1.00, '外币对公贷款 风险权重 100%'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '信用', 0.00, '外币国债/政策性金融债 0%'),
    ('无', '-', '信用', 0.50, '外币同业 50%'),
    ('无', '-', '信用', 1.00, '外币非生息资产 100%'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '汇总节点不参与 CET1 计算'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '负债不计入 RWA'),
    ('无', '-', '无', '-', '所有者权益（不参与 RWA 计算，单独作为 Tier 1）'),
]

# CET1 额外行（资本/扣减/表外/市场/操作）
CET1_EXTRA = [
    # (项目序号, 项目名称, 是否末级, 当前余额, 分子类别, 折算系数, RWA类别, 风险权重, 备注)
    ('S030101010000', '  └ 实收资本（普通股）', '是', 65000000000, '分子', 1.00, '无', '-', '普通股股本'),
    ('S030101020000', '  └ 资本公积', '是', 145000000000, '分子', 1.00, '无', '-', '股本溢价'),
    ('S030101030000', '  └ 盈余公积', '是', 90000000000, '分子', 1.00, '无', '-', '法定盈余公积'),
    ('S030101040000', '  └ 一般风险准备', '是', 130000000000, '分子', 1.00, '无', '-', '一般准备'),
    ('S030101050000', '  └ 未分配利润', '是', 356217000000, '分子', 1.00, '无', '-', '历年滚存利润'),
    ('S030201010000', '  － 扣减：商誉', '是', 1500000000, '扣减', 1.00, '无', '-', '商誉全额扣除'),
    ('S030201020000', '  － 扣减：其他无形资产（除土地使用权）', '是', 8000000000, '扣减', 1.00, '无', '-', '其他无形资产全额扣除'),
    ('S030201030000', '  － 扣减：递延税资产（可抵扣部分）', '是', 15217000000, '扣减', 1.00, '无', '-', '递延税资产全额扣除'),
    ('S040101010000', '表外 1：贷款承诺（原始期限≤1年）', '是', 200000000000, '无', '-', '信用', 0.20, 'CCF 20% × 风险权重 100%'),
    ('S040101020000', '表外 2：贷款承诺（原始期限>1年）', '是', 600000000000, '无', '-', '信用', 0.50, 'CCF 50% × 风险权重 100%'),
    ('S040101030000', '表外 3：保函/担保/跟单信用证', '是', 343000000000, '无', '-', '信用', 1.00, '保函/担保 风险权重 100%'),
    ('S050100000000', '市场风险加权资产（标准法合计）', '是', 100000000000, '无', '-', '市场', 1.00, '利率+权益+外汇+商品+期权'),
    ('S060100000000', '操作风险加权资产（标准法合计）', '是', 974367000000, '无', '-', '操作', 1.00, 'BI 前三年均值 × α(15%) × 12.5（约 5196 亿）'),
]

# ============= 工具函数 =============
def write_row_lcr(ws, r, sid, name, leaf, bal, e, f, g, h, i, j, k):
    ws.cell(r, 1, sid).font = Font(size=9)
    ws.cell(r, 2, name).font = Font(size=10)
    ws.cell(r, 3, leaf).alignment = CENTER
    if bal is not None:
        ws.cell(r, 4, bal).number_format = NUM_FMT
    ws.cell(r, 5, e).alignment = CENTER if e else None
    if isinstance(f, (int, float)):
        ws.cell(r, 6, f).number_format = '0.00'
        ws.cell(r, 6, f).alignment = CENTER
    else:
        ws.cell(r, 6, f).alignment = CENTER
    ws.cell(r, 7, g).alignment = CENTER if g else None
    ws.cell(r, 8, h).alignment = CENTER if h else None
    if isinstance(i, (int, float)):
        ws.cell(r, 9, i).number_format = '0.00'
        ws.cell(r, 9, i).alignment = CENTER
    else:
        ws.cell(r, 9, i).alignment = CENTER
    ws.cell(r, 10, j).alignment = CENTER if j else None
    for c in range(1, 15):
        ws.cell(r, c).border = BORDER
    ws.cell(r, 14, k).font = Font(size=9, italic=True, color='595959')

# ============= 构建 LCR.xlsx =============
print('=== 重建 LCR.xlsx ===')
wb = Workbook()
wb.remove(wb.active)
ws1 = wb.create_sheet('LCR项目明细')
HEADERS = ['项目序号', '项目名称', '是否末级节点', '当前余额（人民币元）',
           '是否分子', '分子折算系数', '分子运算符', '是否分母', '分母折算系数',
           '分母运算符', 'Level 1 分子贡献', 'Level 2A 分子贡献',
           '分母贡献（流出为正 / 流入为负）', 'LCR 规则说明']
for c, h in enumerate(HEADERS, 1):
    cell = ws1.cell(1, c, h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = CENTER
    cell.border = BORDER

widths = [18, 35, 10, 22, 9, 11, 10, 9, 11, 10, 18, 18, 22, 36]
for i, w in enumerate(widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.row_dimensions[1].height = 30

for ridx, ((sid, name, leaf, bal), conf) in enumerate(zip(ROWS, LCR_DATA), start=2):
    e, f, g, h, i, j, k = conf
    write_row_lcr(ws1, ridx, sid, name, leaf, bal, e, f, g, h, i, j, k)

# 公式列 K L M
for r in range(2, ws1.max_row + 1):
    ws1.cell(r, 11, f'=IF(AND(E{r}="是",F{r}=1),D{r}*F{r},0)')
    ws1.cell(r, 12, f'=IF(AND(E{r}="是",F{r}=0.85),D{r}*F{r},0)')
    ws1.cell(r, 13, f'=IF(H{r}="是",IF(J{r}="+",D{r}*I{r},-D{r}*I{r}),0)')
    for c in (11, 12, 13):
        ws1.cell(r, c).number_format = NUM_FMT
        ws1.cell(r, c).alignment = RIGHT

# 计算 sheet
ws_calc = wb.create_sheet('LCR计算')
ws_calc.column_dimensions['A'].width = 50
ws_calc.column_dimensions['B'].width = 28

ws_calc.cell(1, 1, 'LCR 流动性覆盖率计算（Liquidity Coverage Ratio）').font = Font(bold=True, size=14, color='1F4E78')
ws_calc.merge_cells('A1:B1')
ws_calc.cell(2, 1, '依据：巴塞尔 III + 中国银保监会《商业银行流动性风险管理办法》（2021 修订）').font = Font(italic=True, size=10, color='595959')
ws_calc.cell(3, 1, '注：3.2 拆分为 3.2.1 现金（Level 1 HQLA）和 3.2.2 其它（流入 100%）').font = Font(italic=True, size=10, color='595959')
ws_calc.merge_cells('A2:B2')
ws_calc.merge_cells('A3:B3')

# 分子
ws_calc.cell(4, 1, '【分子 HQLA 合格优质流动性资产】').font = SUB_FONT
ws_calc.cell(4, 1).fill = SUB_FILL
ws_calc.merge_cells('A4:B4')
ws_calc.cell(5, 1, '  Level 1 资产（折算 100%）')
ws_calc.cell(5, 2, '=SUMIF(LCR项目明细!F:F,1,LCR项目明细!K:K)')
ws_calc.cell(5, 2).number_format = NUM_FMT
ws_calc.cell(6, 1, '  Level 2A 资产（折算 85%）')
ws_calc.cell(6, 2, '=SUMIF(LCR项目明细!F:F,0.85,LCR项目明细!L:L)')
ws_calc.cell(6, 2).number_format = NUM_FMT
ws_calc.cell(7, 1, '  HQLA 合计')
ws_calc.cell(7, 2, '=B5+B6')
ws_calc.cell(7, 2).font = Font(bold=True)
ws_calc.cell(7, 2).number_format = NUM_FMT

ws_calc.cell(9, 1, '【分母 30 天现金净流出】').font = SUB_FONT
ws_calc.cell(9, 1).fill = SUB_FILL
ws_calc.merge_cells('A9:B9')
ws_calc.cell(10, 1, '  现金流出（折算后）')
ws_calc.cell(10, 2, '=SUMIF(LCR项目明细!J:J,"+",LCR项目明细!M:M)')
ws_calc.cell(10, 2).number_format = NUM_FMT
ws_calc.cell(11, 1, '  现金流入（折算后，负数）')
ws_calc.cell(11, 2, '=SUMIF(LCR项目明细!J:J,"-",LCR项目明细!M:M)')
ws_calc.cell(11, 2).number_format = NUM_FMT
ws_calc.cell(12, 1, '  流入上限（流出 × 75%）')
ws_calc.cell(12, 2, '=B10*0.75')
ws_calc.cell(12, 2).number_format = NUM_FMT
ws_calc.cell(13, 1, '  现金流入实际计入（受 75% 上限限制）')
ws_calc.cell(13, 2, '=MIN(-B11,B12)')
ws_calc.cell(13, 2).number_format = NUM_FMT
ws_calc.cell(14, 1, '  净流出 = 流出 - 实际流入')
ws_calc.cell(14, 2, '=B10-B13')
ws_calc.cell(14, 2).font = Font(bold=True)
ws_calc.cell(14, 2).number_format = NUM_FMT

ws_calc.cell(16, 1, '【LCR 流动性覆盖率】').font = SUB_FONT
ws_calc.cell(16, 1).fill = SUB_FILL
ws_calc.merge_cells('A16:B16')
ws_calc.cell(17, 1, '  LCR = HQLA / 净流出 × 100%')
ws_calc.cell(17, 2, '=B7/B14*100')
ws_calc.cell(17, 2).font = Font(bold=True, size=14, color='C00000')
ws_calc.cell(17, 2).number_format = '0.00"%"'

# 折算依据
ws3 = wb.create_sheet('折算依据')
ws3.column_dimensions['A'].width = 38
ws3.column_dimensions['B'].width = 40
ws3.column_dimensions['C'].width = 12
ws3.column_dimensions['D'].width = 56

ws3.cell(1, 1, 'LCR 项目分类与折算系数依据').font = Font(bold=True, size=12, color='1F4E78')
ws3.merge_cells('A1:D1')
ws3.cell(2, 1, '类别').font = HEADER_FONT
ws3.cell(2, 1).fill = HEADER_FILL
ws3.cell(2, 2, '项目示例').font = HEADER_FONT
ws3.cell(2, 2).fill = HEADER_FILL
ws3.cell(2, 3, '折算系数').font = HEADER_FONT
ws3.cell(2, 3).fill = HEADER_FILL
ws3.cell(2, 4, '依据').font = HEADER_FONT
ws3.cell(2, 4).fill = HEADER_FILL
for c in range(1, 5):
    ws3.cell(2, c).alignment = CENTER

REFS_LCR = [
    ('【分子 HQLA】', None, None, None),
    ('Level 1 - 国债 AC', 'S010102010101 / S010102010201', '100%', '巴塞尔 III Level 1；风险权重 0%'),
    ('Level 1 - 政策性金融债 FVOCI', 'S010102010102 / S010102010202', '100%', '巴塞尔 III Level 1'),
    ('Level 1 - 存款准备金', 'S010102040000', '100%', '央行准备金；Level 1'),
    ('Level 1 - 库存现金', 'S010103020100（3.2.1）', '100%', '库存现金；Level 1'),
    ('Level 2A - AA- 及以上信用债', 'S010102010203（司库债券 FVTPL）', '85%', '巴塞尔 III Level 2A；AA- 及以上公司债'),
    ('【分母 流出】', None, None, None),
    ('零售活期（稳定）', 'S020101020100', '8%', '银保监会《管理办法》§13'),
    ('对公活期（业务关系加权）', 'S020101010100', '48.5%', '银保监会§15；业务关系 20% + 无保险 50% 加权'),
    ('对公定期（30 天内到期）', 'S020101010200', '100%', '银保监会§15'),
    ('同业拆入（同业活期）', 'S020102010100', '100%', '银保监会§17'),
    ('同业存单 NCD', 'S020102010300', '100%', '银保监会§17'),
    ('同业存款', 'S020102010400', '100%', '银保监会§17'),
    ('央行借款 MLF', 'S020102020200', '100%', '银保监会§17'),
    ('结构性货币政策工具', 'S020102020300', '100%', '银保监会§17'),
    ('债券回购（信用债抵押）', 'S020102010200', '25%', '银保监会§17'),
    ('票据转贴现回购', 'S020102010500', '25%', '银保监会§17'),
    ('公开市场回购（国债抵押）', 'S020102020100', '0%', '银保监会§17'),
    ('票据再贴现回购', 'S020102020400', '0%', '银保监会§17'),
    ('外币存款', 'S020201000000', '100%', '银保监会§19'),
    ('外币市场化负债', 'S020202000000', '100%', '银保监会§19'),
    ('【分母 流入】', None, None, None),
    ('对公一般贷款到期', 'S010101010000', '100%', '银保监会§21'),
    ('个人贷款到期', 'S010101020000', '50%', '银保监会§21'),
    ('信用卡贷款到期', 'S010101030000', '50%', '银保监会§21'),
    ('票据贴现到期', 'S010101040000', '100%', '银保监会§21'),
    ('非银贷款到期', 'S010101050000', '100%', '银保监会§21'),
    ('结构化融资到期', 'S010102020000', '100%', '银保监会§21'),
    ('同业资产到期', 'S010102030000', '100%', '银保监会§21'),
    ('其它非生息资产到期', 'S010103020200（3.2.2）', '100%', '银保监会§21'),
    ('外币贷款到期', 'S010201000000', '100%', '银保监会§21'),
    ('外币债券到期', 'S010202010000', '100%', '银保监会§21'),
    ('外币同业资产到期', 'S010202020000', '100%', '银保监会§21'),
    ('外币非生息资产', 'S010203000000', '50%', '银保监会§21'),
    ('【重要公式】', None, None, None),
    ('LCR', 'HQLA / 净流出 × 100%', None, '净流出 = 流出 - MIN(流入, 流出×75%)'),
    ('Level 2 上限', 'Level 1 × 40% / 85%', None, '防止 Level 2 资产过多稀释流动性'),
]
for ridx, (cat, sample, weight, basis) in enumerate(REFS_LCR, start=3):
    ws3.cell(ridx, 1, cat)
    if sample:
        ws3.cell(ridx, 2, sample)
    if weight:
        ws3.cell(ridx, 3, weight).alignment = CENTER
    if basis:
        ws3.cell(ridx, 4, basis)
    for col in range(1, 5):
        ws3.cell(ridx, col).border = BORDER
        ws3.cell(ridx, col).font = Font(size=9)
    if cat.startswith('【') and sample is None:
        for col in range(1, 5):
            ws3.cell(ridx, col).fill = SUB_FILL
            ws3.cell(ridx, col).font = Font(bold=True, size=10)

wb.save(f'{OUT_DIR}/LCR.xlsx')
print(f'  完成：{len(ROWS)} 数据行')

# ============= 构建 NSFR.xlsx =============
print()
print('=== 重建 NSFR.xlsx ===')
wb = Workbook()
wb.remove(wb.active)
ws1 = wb.create_sheet('NSFR项目明细')
HEADERS = ['项目序号', '项目名称', '是否末级节点', '当前余额（人民币元）',
           '是否ASF', 'ASF折算系数', 'ASF运算符', '是否RSF', 'RSF折算系数',
           'RSF运算符', 'ASF贡献', 'RSF贡献', 'NSFR规则说明']
for c, h in enumerate(HEADERS, 1):
    cell = ws1.cell(1, c, h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = CENTER
    cell.border = BORDER

widths = [18, 35, 10, 22, 9, 11, 10, 9, 11, 10, 20, 20, 36]
for i, w in enumerate(widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.row_dimensions[1].height = 30

for ridx, ((sid, name, leaf, bal), conf) in enumerate(zip(ROWS, NSFR_DATA), start=2):
    e, f, g, h, i, j, k = conf
    write_row_lcr(ws1, ridx, sid, name, leaf, bal, e, f, g, h, i, j, k)
    # 第 13 列是 NSFR 规则说明，不是 K/L/M 公式
    # K=L列(11,12) 写公式 ASF/RSF

for r in range(2, ws1.max_row + 1):
    ws1.cell(r, 11, f'=IF(E{r}="是",D{r}*F{r},0)')
    ws1.cell(r, 12, f'=IF(H{r}="是",D{r}*I{r},0)')
    for c in (11, 12):
        ws1.cell(r, c).number_format = NUM_FMT
        ws1.cell(r, c).alignment = RIGHT

# 计算 sheet
ws_calc = wb.create_sheet('NSFR计算')
ws_calc.column_dimensions['A'].width = 50
ws_calc.column_dimensions['B'].width = 28

ws_calc.cell(1, 1, 'NSFR 净稳定资金比例（Net Stable Funding Ratio）').font = Font(bold=True, size=14, color='1F4E78')
ws_calc.merge_cells('A1:B1')
ws_calc.cell(2, 1, '依据：巴塞尔 III + 中国银保监会《商业银行流动性风险管理办法》（2021 修订）').font = Font(italic=True, size=10, color='595959')
ws_calc.cell(3, 1, '注：3.2 拆分为 3.2.1 现金（RSF 0%）和 3.2.2 其它（RSF 100%）').font = Font(italic=True, size=10, color='595959')
ws_calc.merge_cells('A2:B2')
ws_calc.merge_cells('A3:B3')

# ASF
ws_calc.cell(4, 1, '【分子 ASF 可用稳定资金】').font = SUB_FONT
ws_calc.cell(4, 1).fill = SUB_FILL
ws_calc.merge_cells('A4:B4')
ws_calc.cell(5, 1, '  所有者权益 / MLF / 结构性货币政策工具（折算 100%）')
ws_calc.cell(5, 2, '=SUMIF(NSFR项目明细!F:F,1,NSFR项目明细!K:K)')
ws_calc.cell(5, 2).number_format = NUM_FMT
ws_calc.cell(6, 1, '  零售定期存款（折算 100%）')
ws_calc.cell(6, 2, '=SUMIF(NSFR项目明细!F:F,0.95,NSFR项目明细!K:K)')
ws_calc.cell(6, 2).number_format = NUM_FMT
ws_calc.cell(7, 1, '  对公定期存款（折算 100%）')
ws_calc.cell(7, 2, '=SUMIF(NSFR项目明细!F:F,0.5,NSFR项目明细!K:K)')  # 同业存款/NCD
ws_calc.cell(7, 2).number_format = NUM_FMT
ws_calc.cell(8, 1, '  对公活期存款（折算 35%）')
ws_calc.cell(8, 2, '=SUMIF(NSFR项目明细!F:F,0.35,NSFR项目明细!K:K)')
ws_calc.cell(8, 2).number_format = NUM_FMT
ws_calc.cell(9, 1, '  短期 / 央行回购（折算 0%）')
ws_calc.cell(9, 2, '=SUMIF(NSFR项目明细!F:F,0,NSFR项目明细!K:K)')
ws_calc.cell(9, 2).number_format = NUM_FMT
ws_calc.cell(10, 1, '  ASF 合计')
ws_calc.cell(10, 2, '=SUM(B5:B9)')
ws_calc.cell(10, 2).font = Font(bold=True)
ws_calc.cell(10, 2).number_format = NUM_FMT

# RSF
ws_calc.cell(12, 1, '【分母 RSF 所需稳定资金】').font = SUB_FONT
ws_calc.cell(12, 1).fill = SUB_FILL
ws_calc.merge_cells('A12:B12')
ws_calc.cell(13, 1, '  高流动性资产（折算 0%）')
ws_calc.cell(13, 2, '=SUMIF(NSFR项目明细!I:I,0,NSFR项目明细!L:L)')
ws_calc.cell(13, 2).number_format = NUM_FMT
ws_calc.cell(14, 1, '  同业资产 / 同业存款（折算 50%）')
ws_calc.cell(14, 2, '=SUMIF(NSFR项目明细!I:I,0.5,NSFR项目明细!L:L)')
ws_calc.cell(14, 2).number_format = NUM_FMT
ws_calc.cell(15, 1, '  个人住房抵押贷款（折算 65%）')
ws_calc.cell(15, 2, '=SUMIF(NSFR项目明细!I:I,0.65,NSFR项目明细!L:L)')
ws_calc.cell(15, 2).number_format = NUM_FMT
ws_calc.cell(16, 1, '  一般贷款 / 信用卡 / 票据贴现（折算 85%）')
ws_calc.cell(16, 2, '=SUMIF(NSFR项目明细!I:I,0.85,NSFR项目明细!L:L)')
ws_calc.cell(16, 2).number_format = NUM_FMT
ws_calc.cell(17, 1, '  其他资产（折算 100%）')
ws_calc.cell(17, 2, '=SUMIF(NSFR项目明细!I:I,1,NSFR项目明细!L:L)')
ws_calc.cell(17, 2).number_format = NUM_FMT
ws_calc.cell(18, 1, '  RSF 合计')
ws_calc.cell(18, 2, '=SUM(B13:B17)')
ws_calc.cell(18, 2).font = Font(bold=True)
ws_calc.cell(18, 2).number_format = NUM_FMT

ws_calc.cell(20, 1, '【NSFR 净稳定资金比例】').font = SUB_FONT
ws_calc.cell(20, 1).fill = SUB_FILL
ws_calc.merge_cells('A20:B20')
ws_calc.cell(21, 1, '  NSFR = ASF / RSF × 100%')
ws_calc.cell(21, 2, '=B10/B18*100')
ws_calc.cell(21, 2).font = Font(bold=True, size=14, color='C00000')
ws_calc.cell(21, 2).number_format = '0.00"%"'

wb.save(f'{OUT_DIR}/NSFR.xlsx')
print(f'  完成：{len(ROWS)} 数据行')

# ============= 构建 EVE.xlsx =============
print()
print('=== 重建 EVE.xlsx ===')
wb = Workbook()
wb.remove(wb.active)
ws1 = wb.create_sheet('EVE项目明细')
HEADERS = ['项目序号', '项目名称', '是否末级节点', '当前余额（人民币元）',
           '类别', '类型', '久期（年）',
           '基期PV', '情景1 PV (+200bp)', '情景1 ΔPV',
           '情景2 PV (-100bp)', '情景2 ΔPV',
           '情景3 PV (短+250/+100)', '情景3 ΔPV',
           '情景4 PV (短-100/-50)', '情景4 ΔPV',
           '情景5 PV (短-100/+100)', '情景5 ΔPV',
           '情景6 PV (短+100/-100)', '情景6 ΔPV',
           'EVE规则说明']
for c, h in enumerate(HEADERS, 1):
    cell = ws1.cell(1, c, h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = CENTER
    cell.border = BORDER

widths = [18, 35, 10, 22, 8, 10, 9, 16, 16, 14, 16, 14, 18, 14, 18, 14, 18, 14, 18, 14, 30]
for i, w in enumerate(widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.row_dimensions[1].height = 30

for ridx, ((sid, name, leaf, bal), conf) in enumerate(zip(ROWS, EVE_DATA), start=2):
    cat, typ, dur = conf
    ws1.cell(ridx, 1, sid).font = Font(size=9)
    ws1.cell(ridx, 2, name).font = Font(size=10)
    ws1.cell(ridx, 3, leaf).alignment = CENTER
    if bal is not None:
        ws1.cell(ridx, 4, bal).number_format = NUM_FMT
    ws1.cell(ridx, 5, cat).alignment = CENTER
    ws1.cell(ridx, 6, typ).alignment = CENTER if typ else None
    if dur is not None:
        ws1.cell(ridx, 7, dur).number_format = '0.00'
        ws1.cell(ridx, 7).alignment = CENTER
    for c in range(1, 22):
        ws1.cell(ridx, c).border = BORDER
    if cat == '汇总':
        note = '汇总节点不参与 EVE 计算'
    elif sid == 'S030000000000':
        note = '所有者权益（不计入 EVE 现金流，单独作为 Tier 1）'
    else:
        note = ''
    ws1.cell(ridx, 21, note).font = Font(size=9, italic=True, color='595959')

# 公式列
for r in range(2, ws1.max_row + 1):
    ws1.cell(r, 8, f'=D{r}/(1+0.03)^G{r}')
    ws1.cell(r, 9, f'=D{r}/(1+0.05)^G{r}')
    ws1.cell(r, 10, f'=H{r}-I{r}')
    ws1.cell(r, 11, f'=D{r}/(1+0.02)^G{r}')
    ws1.cell(r, 12, f'=H{r}-K{r}')
    ws1.cell(r, 13, f'=IF(G{r}<1,D{r}/(1+0.05)^G{r},D{r}/(1+0.04)^G{r})')
    ws1.cell(r, 14, f'=H{r}-M{r}')
    ws1.cell(r, 15, f'=IF(G{r}<1,D{r}/(1+0.02)^G{r},D{r}/(1+0.025)^G{r})')
    ws1.cell(r, 16, f'=H{r}-O{r}')
    ws1.cell(r, 17, f'=IF(G{r}<1,D{r}/(1+0.02)^G{r},D{r}/(1+0.04)^G{r})')
    ws1.cell(r, 18, f'=H{r}-Q{r}')
    ws1.cell(r, 19, f'=IF(G{r}<1,D{r}/(1+0.04)^G{r},D{r}/(1+0.02)^G{r})')
    ws1.cell(r, 20, f'=H{r}-S{r}')
    for c in range(8, 21):
        ws1.cell(r, c).number_format = NUM_FMT
        ws1.cell(r, c).alignment = RIGHT

# 计算 sheet
ws_calc = wb.create_sheet('EVE计算')
ws_calc.column_dimensions['A'].width = 50
ws_calc.column_dimensions['B'].width = 28

ws_calc.cell(1, 1, '△EVE 经济价值变动（IRRBB 银行账户利率风险）').font = Font(bold=True, size=14, color='1F4E78')
ws_calc.merge_cells('A1:B1')
ws_calc.cell(2, 1, '依据：巴塞尔 IRRBB（2016）+ 银保监会《商业银行银行账户利率风险管理办法》（2018）').font = Font(italic=True, size=10, color='595959')
ws_calc.cell(3, 1, '基期利率 r₀ = 3.0%').font = Font(italic=True, size=10, color='595959')
ws_calc.cell(4, 1, '注：3.2 拆分为 3.2.1 现金（久期 0.05）和 3.2.2 其它（久期 0.25）').font = Font(italic=True, size=10, color='595959')
ws_calc.merge_cells('A2:B2')
ws_calc.merge_cells('A3:B3')
ws_calc.merge_cells('A4:B4')

ws_calc.cell(6, 1, 'Tier 1 一级资本（所有者权益）')
ws_calc.cell(6, 2, 786217000000)
ws_calc.cell(6, 2).number_format = NUM_FMT
ws_calc.cell(7, 1, '资产合计（仅末级映射）')
ws_calc.cell(7, 2, '=SUMIFS(EVE项目明细!D:D,EVE项目明细!E:E,"asset",EVE项目明细!C:C,"是")')
ws_calc.cell(7, 2).number_format = NUM_FMT
ws_calc.cell(8, 1, '负债合计（仅末级映射）')
ws_calc.cell(8, 2, '=SUMIFS(EVE项目明细!D:D,EVE项目明细!E:E,"liab",EVE项目明细!C:C,"是")')
ws_calc.cell(8, 2).number_format = NUM_FMT
ws_calc.cell(9, 1, '资产加权久期 D_A（按余额加权）')
ws_calc.cell(9, 2, '=SUMPRODUCT((EVE项目明细!E2:E58="asset")*(EVE项目明细!C2:C58="是")*(EVE项目明细!G2:G58)*(EVE项目明细!D2:D58))/B7')
ws_calc.cell(9, 2).number_format = '0.00'
ws_calc.cell(10, 1, '负债加权久期 D_L（按余额加权）')
ws_calc.cell(10, 2, '=SUMPRODUCT((EVE项目明细!E2:E58="liab")*(EVE项目明细!C2:C58="是")*(EVE项目明细!G2:G58)*(EVE项目明细!D2:D58))/B8')
ws_calc.cell(10, 2).number_format = '0.00'

# 6 个情景（每个情景使用不同的 ΔPV 列）
scenarios = [
    (13, 14, 15, 16, '情景 1：平行向上 +200bp（基期 3% → 5%）', 'J'),  # 情景1 ΔPV = J 列
    (19, 20, 21, 22, '情景 2：平行向下 -100bp（基期 3% → 2%）', 'L'),  # 情景2 ΔPV = L 列
    (25, 26, 27, 28, '情景 3：短端向上 +250bp（t<1）/ +100bp（t≥1）', 'N'),  # 情景3 ΔPV = N 列
    (31, 32, 33, 34, '情景 4：短端向下 -100bp（t<1）/ -50bp（t≥1）', 'P'),  # 情景4 ΔPV = P 列
    (37, 38, 39, 40, '情景 5：长端向上 -100bp（t<1）/ +100bp（t≥1）', 'R'),  # 情景5 ΔPV = R 列
    (43, 44, 45, 46, '情景 6：长端向下 +100bp（t<1）/ -100bp（t≥1）', 'T'),  # 情景6 ΔPV = T 列
]
for start_r, asset_r, liab_r, delta_r, title, col in scenarios:
    ws_calc.cell(start_r, 1, title).font = SUB_FONT
    ws_calc.cell(start_r, 1).fill = SUB_FILL
    ws_calc.merge_cells(f'A{start_r}:B{start_r}')
    ws_calc.cell(asset_r, 1, '  资产 PV 减少（损失）')
    ws_calc.cell(asset_r, 2, f'=SUMIFS(EVE项目明细!{col}:{col},EVE项目明细!E:E,"asset")')
    ws_calc.cell(asset_r, 2).number_format = NUM_FMT
    ws_calc.cell(liab_r, 1, '  负债 PV 减少（利好）')
    ws_calc.cell(liab_r, 2, f'=SUMIFS(EVE项目明细!{col}:{col},EVE项目明细!E:E,"liab")')
    ws_calc.cell(liab_r, 2).number_format = NUM_FMT
    ws_calc.cell(delta_r, 1, '  △EVE（损失）')
    ws_calc.cell(delta_r, 2, f'=B{asset_r}-B{liab_r}')
    ws_calc.cell(delta_r, 2).number_format = NUM_FMT
    ws_calc.cell(delta_r + 1, 1, '  △EVE / Tier 1 资本')
    ws_calc.cell(delta_r + 1, 2, f'=B{delta_r}/B6*100')
    ws_calc.cell(delta_r + 1, 2).number_format = '0.00"%"'

# 最不利
ws_calc.cell(50, 1, '【最不利情景 △EVE】').font = SUB_FONT
ws_calc.cell(50, 1).fill = SUB_FILL
ws_calc.merge_cells('A50:B50')
ws_calc.cell(51, 1, '  最大损失 △EVE（6 情景中最不利）')
ws_calc.cell(51, 2, '=MAX(B16,B22,B28,B34,B40,B46)')
ws_calc.cell(51, 2).number_format = NUM_FMT
ws_calc.cell(52, 1, '  △EVE / Tier 1 资本')
ws_calc.cell(52, 2, '=B51/B6*100')
ws_calc.cell(52, 2).number_format = '0.00"%"'

ws_calc.cell(54, 1, '  监管阈值（银保监会 §13）')
ws_calc.cell(54, 2, 0.15)
ws_calc.cell(54, 2).number_format = '0.00%'
ws_calc.cell(55, 1, '  是否达标（≤ 15%）')
ws_calc.cell(55, 2, '=IF(B52/100<=B54,"达标","不达标")')
ws_calc.cell(55, 2).alignment = CENTER

wb.save(f'{OUT_DIR}/EVE.xlsx')
print(f'  完成：{len(ROWS)} 数据行')

# ============= 构建 CET1.xlsx =============
print()
print('=== 重建 CET1.xlsx ===')
wb = Workbook()
wb.remove(wb.active)
ws1 = wb.create_sheet('CET1项目明细')
HEADERS = ['项目序号', '项目名称', '是否末级节点', '当前余额（人民币元）',
           'CET1分子类别', '分子折算系数', '分子贡献',
           'RWA类别', 'RWA风险权重', 'RWA金额贡献',
           'CET1规则说明']
for c, h in enumerate(HEADERS, 1):
    cell = ws1.cell(1, c, h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = CENTER
    cell.border = BORDER

widths = [18, 38, 10, 22, 13, 12, 22, 11, 12, 22, 50]
for i, w in enumerate(widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.row_dimensions[1].height = 30

# 写基础 57 行
for ridx, ((sid, name, leaf, bal), conf) in enumerate(zip(ROWS, CET1_DATA), start=2):
    cap_kind, cap_rate, rwa_kind, rwa_w, note = conf
    ws1.cell(ridx, 1, sid).font = Font(size=9)
    ws1.cell(ridx, 2, name).font = Font(size=10)
    ws1.cell(ridx, 3, leaf).alignment = CENTER
    if bal is not None:
        ws1.cell(ridx, 4, bal).number_format = NUM_FMT
    ws1.cell(ridx, 5, cap_kind).alignment = CENTER
    if isinstance(cap_rate, (int, float)):
        ws1.cell(ridx, 6, cap_rate).number_format = '0.00'
        ws1.cell(ridx, 6).alignment = CENTER
    else:
        ws1.cell(ridx, 6, cap_rate).alignment = CENTER
    ws1.cell(ridx, 7, f'=IF(E{ridx}="分子",D{ridx}*F{ridx},IF(E{ridx}="扣减",D{ridx}*F{ridx},0))')
    ws1.cell(ridx, 8, rwa_kind).alignment = CENTER
    if isinstance(rwa_w, (int, float)):
        ws1.cell(ridx, 9, rwa_w).number_format = '0.00'
        ws1.cell(ridx, 9).alignment = CENTER
    else:
        ws1.cell(ridx, 9, rwa_w).alignment = CENTER
    ws1.cell(ridx, 10, f'=IF(H{ridx}="无",0,D{ridx}*I{ridx})')
    for c in (7, 10):
        ws1.cell(ridx, c).number_format = NUM_FMT
        ws1.cell(ridx, c).alignment = RIGHT
    ws1.cell(ridx, 11, note).font = Font(size=9, italic=True, color='595959')
    for c in range(1, 12):
        ws1.cell(ridx, c).border = BORDER

# 写额外行
extra_start = len(ROWS) + 2
for off, (sid, name, leaf, bal, cap_kind, cap_rate, rwa_kind, rwa_w, note) in enumerate(CET1_EXTRA):
    ridx = extra_start + off
    ws1.cell(ridx, 1, sid).font = Font(size=9)
    ws1.cell(ridx, 2, name).font = Font(size=10)
    ws1.cell(ridx, 3, leaf).alignment = LEFT
    ws1.cell(ridx, 4, bal).number_format = NUM_FMT
    ws1.cell(ridx, 5, cap_kind).alignment = CENTER
    if isinstance(cap_rate, (int, float)):
        ws1.cell(ridx, 6, cap_rate).number_format = '0.00'
        ws1.cell(ridx, 6).alignment = CENTER
    else:
        ws1.cell(ridx, 6, cap_rate).alignment = CENTER
    ws1.cell(ridx, 7, f'=IF(E{ridx}="分子",D{ridx}*F{ridx},IF(E{ridx}="扣减",D{ridx}*F{ridx},0))')
    ws1.cell(ridx, 8, rwa_kind).alignment = CENTER
    ws1.cell(ridx, 9, rwa_w).number_format = '0.00'
    ws1.cell(ridx, 9).alignment = CENTER
    ws1.cell(ridx, 10, f'=IF(H{ridx}="无",0,D{ridx}*I{ridx})')
    for c in (7, 10):
        ws1.cell(ridx, c).number_format = NUM_FMT
        ws1.cell(ridx, c).alignment = RIGHT
    ws1.cell(ridx, 11, note).font = Font(size=9, italic=True, color='595959')
    for c in range(1, 12):
        ws1.cell(ridx, c).border = BORDER
        if '分子' in str(cap_kind) or '扣减' in str(cap_kind):
            ws1.cell(ridx, c).fill = CAP_FILL if '分子' in str(cap_kind) else DEDUCT_FILL

last_row = extra_start + len(CET1_EXTRA) - 1

# 计算 sheet
ws_calc = wb.create_sheet('CET1计算')
ws_calc.column_dimensions['A'].width = 50
ws_calc.column_dimensions['B'].width = 28

ws_calc.cell(1, 1, 'CET1 核心一级资本充足率计量（Common Equity Tier 1 Capital Ratio）').font = Font(bold=True, size=14, color='1F4E78')
ws_calc.merge_cells('A1:B1')
ws_calc.cell(2, 1, '依据：巴塞尔 III + 中国银保监会《商业银行资本管理办法》').font = Font(italic=True, size=10, color='595959')
ws_calc.cell(3, 1, '基期：中信银行 2025 年末（合并口径）').font = Font(italic=True, size=10, color='595959')
ws_calc.merge_cells('A2:B2')
ws_calc.merge_cells('A3:B3')

ws_calc.cell(4, 1, '【分子 核心一级资本净额】').font = SUB_FONT
ws_calc.cell(4, 1).fill = SUB_FILL
ws_calc.merge_cells('A4:B4')
ws_calc.cell(5, 1, '  核心一级资本合计（5 项细项）')
ws_calc.cell(5, 2, f'=SUMIF(CET1项目明细!E2:E{last_row},"分子",CET1项目明细!D2:D{last_row})')
ws_calc.cell(5, 2).number_format = NUM_FMT
ws_calc.cell(6, 1, '  扣减项合计')
ws_calc.cell(6, 2, f'=SUMIF(CET1项目明细!E2:E{last_row},"扣减",CET1项目明细!D2:D{last_row})')
ws_calc.cell(6, 2).number_format = NUM_FMT
ws_calc.cell(7, 1, '  核心一级资本净额（CET1 Net）')
ws_calc.cell(7, 2, '=B5-B6')
ws_calc.cell(7, 2).font = Font(bold=True)
ws_calc.cell(7, 2).number_format = NUM_FMT
ws_calc.cell(7, 2).fill = CAP_FILL

ws_calc.cell(9, 1, '【分母 风险加权资产 RWA】').font = SUB_FONT
ws_calc.cell(9, 1).fill = SUB_FILL
ws_calc.merge_cells('A9:B9')
ws_calc.cell(10, 1, '  信用风险加权资产（含表外业务）')
ws_calc.cell(10, 2, f'=SUMIF(CET1项目明细!H2:H{last_row},"信用",CET1项目明细!J2:J{last_row})')
ws_calc.cell(10, 2).number_format = NUM_FMT
ws_calc.cell(11, 1, '  市场风险加权资产（标准法）')
ws_calc.cell(11, 2, f'=SUMIF(CET1项目明细!H2:H{last_row},"市场",CET1项目明细!J2:J{last_row})')
ws_calc.cell(11, 2).number_format = NUM_FMT
ws_calc.cell(12, 1, '  操作风险加权资产（标准法·收入指标法）')
ws_calc.cell(12, 2, f'=SUMIF(CET1项目明细!H2:H{last_row},"操作",CET1项目明细!J2:J{last_row})')
ws_calc.cell(12, 2).number_format = NUM_FMT
ws_calc.cell(13, 1, '  风险加权资产合计 RWA')
ws_calc.cell(13, 2, '=B10+B11+B12')
ws_calc.cell(13, 2).font = Font(bold=True)
ws_calc.cell(13, 2).number_format = NUM_FMT
ws_calc.cell(13, 2).fill = RWA_FILL

ws_calc.cell(15, 1, '【CET1 核心一级资本充足率】').font = SUB_FONT
ws_calc.cell(15, 1).fill = SUB_FILL
ws_calc.merge_cells('A15:B15')
ws_calc.cell(16, 1, '  CET1 = 核心一级资本净额 / RWA × 100%')
ws_calc.cell(16, 2, '=B7/B13*100')
ws_calc.cell(16, 2).font = Font(bold=True, size=14, color='C00000')
ws_calc.cell(16, 2).number_format = '0.00"%"'

ws_calc.cell(18, 1, '【监管要求】').font = SUB_FONT
ws_calc.cell(18, 1).fill = SUB_FILL
ws_calc.merge_cells('A18:B18')
ws_calc.cell(19, 1, '  银保监会《资本管理办法》§5：核心一级资本充足率 ≥ 5.00%')
ws_calc.cell(20, 1, '  银保监会 §7：储备资本要求 +2.5%')
ws_calc.cell(21, 1, '  银保监会 §8：系统重要性银行附加资本 +0.25%~+1.50%')
ws_calc.cell(22, 1, '  综合监管底线 ≈ 7.50%~8.50%')

ws_calc.cell(24, 1, '  本行实际 CET1')
ws_calc.cell(24, 2, '=B16')
ws_calc.cell(24, 2).number_format = '0.00"%"'
ws_calc.cell(25, 1, '  是否达标（CET1 ≥ 8.50%）')
ws_calc.cell(25, 2, '=IF(B16>=8.5,"达标","不达标")')
ws_calc.cell(25, 2).alignment = CENTER
ws_calc.cell(25, 2).font = Font(bold=True)

ws_calc.cell(27, 1, '【CET1 公式说明】').font = SUB_FONT
ws_calc.cell(27, 1).fill = SUB_FILL
ws_calc.merge_cells('A27:B27')
ws_calc.cell(28, 1, '  核心一级资本 = 实收资本 + 资本公积 + 盈余公积 + 一般风险准备 + 未分配利润')
ws_calc.cell(29, 1, '  扣减项 = 商誉 + 其他无形资产 + 递延税资产')
ws_calc.cell(30, 1, '  核心一级资本净额 = 核心一级资本 - 扣减项')
ws_calc.cell(31, 1, '  RWA = 信用风险 RWA（含表外） + 市场风险 RWA + 操作风险 RWA')
ws_calc.cell(32, 1, '  信用风险 RWA = Σ（表内资产敞口 × 风险权重） + Σ（表外资产敞口 × CCF × 风险权重）')
ws_calc.cell(33, 1, '  操作风险 RWA = BI 前三年均值 × α(15%) × 12.5')
ws_calc.cell(34, 1, '  CET1 比率 = 核心一级资本净额 / RWA × 100%')

wb.save(f'{OUT_DIR}/CET1.xlsx')
print(f'  完成：{last_row} 数据行（含 57 基础 + 13 扩展）')

print()
print('全部 4 个模板重建完成！')