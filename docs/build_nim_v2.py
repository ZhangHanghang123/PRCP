# -*- coding: utf-8 -*-
"""
NIM 净息差计量模版 —— 基于 prcp_basic_20251231.xlsx 真实数据

【与 NII 模版的区别】
  NII 模版回答「赚了多少」—— 分子口径（利息收入 − 利息支出）
  NIM 模版回答「赚得 efficiently吗」—— 分母口径（生息资产如何界定）
  NIM = NII ÷ 平均生息资产，分母界定直接决定 NIM 高低，本模版核心即分母

【NIM 特有内容】
  ① 分母口径界定：5 种候选分母逐项对比（监管口径 / 期末余额 / 含非生息 / 含表外 / 杠杆调整）
  ② 多口径 NIM 对比：同一分子下不同分母 → 量化口径差异
  ③ 净利差 NIS 分解：NIM ≠ NIS，差额来自生息资产 ≠ 计息负债 的规模错配
     NIM = NIS × (计息负债/生息资产)
  ④ 杜邦三分解：NIM = 生息资产收益率 × 生息资产占比 − 计息负债成本率 × 计息负债占比
  ⑤ 量价结构分析：按条线拆解 NIM 贡献 = Σ(条线余额占比 × 条线利差)
  ⑥ 情景敏感性：利率平行移动 + 分母口径切换 + 结构优化情景
  ⑦ 监管达标与同业对标
  ⑧ 与 NII 模版的勾稽校验

【口径】
  年度利息 = 余额 × 加权平均利率（参照物 EM × 12）
  NIM = 利息净收入 ÷ 平均生息资产
  NIS = 生息资产收益率 − 计息负债成本率
  NIM = NIS × 计息负债 / 生息资产

【单位】亿元 / 亿元每年 / %
"""
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter as L

DOC = 'C:/银行经营/PRCP/docs/v2'
SRC = f'{DOC}/prcp_basic_20251231.xlsx'
OUT = f'{DOC}/NIM计量模版_v2_真实数据.xlsx'

BUCKETS = [(f'{m}M', m / 12.0) for m in range(1, 61)] + \
          [('10Y', 10.0), ('15Y', 15.0), ('20Y', 20.0), ('30Y', 30.0)]
NB = len(BUCKETS)
C_REMAIN0, C_CURBAL, C_RATE, C_INT, C_RW = 76, 140, 142, 143, 144

_ws = openpyxl.load_workbook(SRC, data_only=True)['基础数据']

CURVE = []
for r in range(48, 112):
    ten, y = _ws.cell(r, 1).value, _ws.cell(r, 2).value
    if ten and isinstance(y, (int, float)):
        t = float(ten[:-1]) / 12.0 if ten.endswith('M') else float(ten[:-1])
        CURVE.append((ten, t, y / 100.0))

CATMAP = {'ASSET': '资产', 'LIAB': '负债', 'EQUITY': '权益'}


def classify(name, cat):
    n = name
    if cat == 'EQUITY':
        return '权益'
    if cat == 'ASSET':
        if '外币' in n:
            return '外币资产'
        if '贷款' in n or '票据贴现' in n:
            return '信贷资产'
        if '债券' in n:
            return '债券投资'
        if '同业' in n or '结构化' in n or '准备金' in n:
            return '金融市场'
        return '非生息资产'
    if '外币' in n:
        return '外币负债'
    if '活期' in n:
        return '活期存款'
    if '定期' in n:
        return '定期存款'
    return '市场化负债'


ATYPE = {'信贷资产': '信贷', '债券投资': '投资', '金融市场': '金融',
         '非生息资产': '非息', '外币资产': '外币', '活期存款': '活期',
         '定期存款': '定期', '市场化负债': '同业', '外币负债': '外币',
         '权益': '权益'}

# ★ NIM 分母口径标记（本模版的核心逻辑）
# 'EA'  = 生息资产（监管口径分母：产生利息收入的资产）
# 'NEA' = 非生息资产（不计入监管口径分母，但计入总资产）
def ea_flag(name, cat, rate):
    """监管口径生息资产判定：资产端 且 产生利息收入（利率 > 0）。
    现金及存放央行、FVTPL 交易性损益类不计入。"""
    if cat != 'ASSET':
        return 'NEA' if cat == 'ASSET' else '-'
    return 'EA' if rate > 0 else 'NEA'


def derive_beta(dist, is_liab):
    tot = sum(dist)
    if tot <= 0:
        return 0.0
    return min(0.98, max(0.10, sum(dist[:12]) / tot))


ACCOUNTS = []
TOTAL = {}
for r in range(4, 44):
    code = _ws.cell(r, 3).value
    if not code:
        continue
    name = str(_ws.cell(r, 4).value or '').strip()
    cat = _ws.cell(r, 8).value
    bal = (_ws.cell(r, C_CURBAL).value or 0) / 1e8
    if int(_ws.cell(r, 7).value or 0) != 1:
        if code in ('S01000000000000', 'S02000000000000', 'S03000000000000'):
            TOTAL[cat] = bal
        continue
    if code == 'S03000000000000':
        TOTAL['EQUITY'] = bal
    rate = (_ws.cell(r, C_RATE).value or 0) / 100.0
    intr_m = (_ws.cell(r, C_INT).value or 0) / 1e8
    dist = []
    for i in range(NB):
        v = _ws.cell(r, C_REMAIN0 + i).value
        dist.append((v if isinstance(v, (int, float)) else 0.0) / 1e8)
    ln = classify(name, cat)
    ACCOUNTS.append(dict(code=code, name=name, cat=cat, bal=bal, rate=rate,
                         intr_m=intr_m, rw=(_ws.cell(r, C_RW).value or 0),
                         dist=dist, beta=derive_beta(dist, cat == 'LIAB'),
                         line=ln, atype=ATYPE[ln], ea=ea_flag(name, cat, rate),
                         src_row=r))

TA = TOTAL.get('ASSET', 0)
TL = TOTAL.get('LIAB', 0)
TE = TOTAL.get('EQUITY', 0)

NA = sum(1 for a in ACCOUNTS if a['cat'] == 'ASSET')
NL = sum(1 for a in ACCOUNTS if a['cat'] == 'LIAB')
NE = sum(1 for a in ACCOUNTS if a['cat'] == 'EQUITY')
assert NA + NL + NE == 24

# ---------- 样式 ----------
F_TITLE = Font(name='Microsoft YaHei', size=14, bold=True, color='1F4E78')
F_SUB = Font(name='Microsoft YaHei', size=9, italic=True, color='595959')
F_HEAD = Font(name='Microsoft YaHei', size=10, bold=True, color='FFFFFF')
F_SEC = Font(name='Microsoft YaHei', size=10, bold=True, color='1F4E78')
F_N = Font(name='Microsoft YaHei', size=10)
F_B = Font(name='Microsoft YaHei', size=10, bold=True)
F_INPUT = Font(name='Microsoft YaHei', size=10, color='0070C0')
F_CALC = Font(name='Microsoft YaHei', size=10, color='7030A0')
F_LIABC = Font(name='Microsoft YaHei', size=10, color='C55A11')
F_KPI = Font(name='Microsoft YaHei', size=12, bold=True, color='C00000')
F_KPIN = Font(name='Microsoft YaHei', size=11, bold=True, color='C00000')

FILL_HEAD = PatternFill('solid', fgColor='305496')
FILL_SEC = PatternFill('solid', fgColor='D9E1F2')
FILL_INPUT = PatternFill('solid', fgColor='E2EFDA')
FILL_A = PatternFill('solid', fgColor='DEEBF7')
FILL_L = PatternFill('solid', fgColor='FCE4D6')
FILL_NEA = PatternFill('solid', fgColor='F2F2F2')
FILL_KPI = PatternFill('solid', fgColor='FFD966')
FILL_HL = PatternFill('solid', fgColor='FFF2CC')

BD = Border(left=Side('thin', color='B4C7E7'), right=Side('thin', color='B4C7E7'),
            top=Side('thin', color='B4C7E7'), bottom=Side('thin', color='B4C7E7'))
N2 = '#,##0.00;[Red]-#,##0.00'
N0 = '#,##0;[Red]-#,##0'
N4 = '#,##0.0000;[Red]-#,##0.0000'
P2 = '0.00%'
P3 = '0.000%'
P4 = '0.0000%'
BP4 = '+0.0000%;-0.0000%;0.0000%'
AC = Alignment(horizontal='center', vertical='center', wrap_text=True)
AL = Alignment(horizontal='left', vertical='center', wrap_text=True)


def sec(ws, r, text, nc):
    ws.cell(r, 1, text).font = F_SEC
    for c in range(1, nc + 1):
        ws.cell(r, c).fill = FILL_SEC
        ws.cell(r, c).border = BD
    ws.cell(r, 1).alignment = AL
    return r + 1


def hdr(ws, r, hs, widths=None):
    for i, h in enumerate(hs, 1):
        c = ws.cell(r, i, h)
        c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
    ws.row_dimensions[r].height = 34
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[L(i)].width = w
    return r + 1


wb = Workbook()
wb.remove(wb.active)

# ===========================================================
# ① 分母口径数据源
# ===========================================================
ws1 = wb.create_sheet('①分母口径数据源')
H1 = ['账户编码', '账户名称', '大类', '业务条线', '账户类型',
      '当前余额\n(亿元)', '加权平均\n利率', '年度利息\n(亿元/年)',
      '★分母归属', '是否生息资产', '计息负债', '1年内到期\n(亿元)',
      '重定价β', '风险权重', '口径说明']
W1 = [17, 26, 8, 12, 9, 13, 11, 14, 12, 12, 11, 13, 10, 10, 40]
ws1['A1'] = '① 分母口径数据源 — 取自 prcp_basic_20251231.xlsx「基础数据」（方案 8 / 2025-12-31）'
ws1['A1'].font = F_TITLE
ws1.merge_cells('A1:O1')
ws1['A2'] = ('🟢 绿区(蓝字) = 可编辑  |  🟣 紫字 = 自动计算  |  ★分母归属 = 生息资产(EA) / 非生息(NEA)，'
             '决定该账户是否进入 NIM 分母  |  年度利息 = 余额 × 加权平均利率（= 参照物 EM × 12）')
ws1['A2'].font = F_SUB
ws1.merge_cells('A2:O2')
r = hdr(ws1, 3, H1, W1)
D0 = r
T0 = 4
for i, a in enumerate(ACCOUNTS):
    rr = D0 + i
    src = T0 + i
    fb = FILL_A if a['ea'] == 'EA' else (FILL_L if a['cat'] == 'LIAB' else FILL_NEA)
    ws1.cell(rr, 1, a['code']).font = F_N
    ws1.cell(rr, 2, a['name']).font = F_N
    ws1.cell(rr, 3, CATMAP[a['cat']]).font = F_N
    ws1.cell(rr, 4, a['line']).font = F_N
    ws1.cell(rr, 5, a['atype']).font = F_N
    ws1.cell(rr, 6, a['bal']).font = F_INPUT
    ws1.cell(rr, 6).number_format = N2
    ws1.cell(rr, 7, a['rate']).font = F_INPUT
    ws1.cell(rr, 7).number_format = P4
    ws1.cell(rr, 8, f'=F{rr}*G{rr}').font = F_CALC
    ws1.cell(rr, 8).number_format = N2
    ws1.cell(rr, 9, a['ea']).font = F_B if a['ea'] == 'EA' else F_N
    ws1.cell(rr, 10, f'=IF(AND($C{rr}="资产",$G{rr}>0),"是","否")').font = F_CALC
    ws1.cell(rr, 11, f'=IF($C{rr}="负债","是","否")').font = F_CALC
    ws1.cell(rr, 12, f"='②期限分布'!{L(3+NB)}{src}").font = F_CALC
    ws1.cell(rr, 12).number_format = N2
    ws1.cell(rr, 13, f"=IF('②期限分布'!{L(4+NB)}{src}=0,0,MIN(0.98,MAX(0.1,'②期限分布'!{L(3+NB)}{src}/'②期限分布'!{L(4+NB)}{src})))").font = F_CALC
    ws1.cell(rr, 13).number_format = N4
    ws1.cell(rr, 14, a['rw']).font = F_N
    ws1.cell(rr, 14).number_format = P2
    NOTE_EA = {'信贷资产': '产生利息收入 → 计入 NIM 分母',
               '债券投资': '票息收入 → 计入 NIM 分母（FVTPL 票息 0 则不计入）',
               '金融市场': '同业/准备金/结构化利息收入 → 计入分母',
               '非生息资产': '利率 0% → 不计入 NIM 分母，但计入总资产',
               '外币资产': '折人民币利息收入 → 计入分母',
               '活期存款': '计息负债，付息成本进入分子',
               '定期存款': '计息负债，付息成本进入分子',
               '市场化负债': '计息负债，货币市场定价',
               '外币负债': '计息负债，折人民币',
               '权益': '无利息收支，不进入任何口径'}
    ws1.cell(rr, 15, NOTE_EA.get(a['line'], '')).font = F_SUB
    for c in range(1, 16):
        ws1.cell(rr, c).border = BD
        if ws1.cell(rr, c).fill.fgColor.rgb in (None, '00000000'):
            ws1.cell(rr, c).fill = fb
    for c in (6, 7):
        ws1.cell(rr, c).fill = PatternFill('solid', fgColor='E2EFDA')
D1 = D0 + len(ACCOUNTS) - 1
SR = D1 + 1
ws1.cell(SR, 2, '合计 / 加权平均').font = F_B
ws1.cell(SR, 6, f'=SUM(F{D0}:F{D1})').font = F_B
ws1.cell(SR, 6).number_format = N2
ws1.cell(SR, 7, f'=IF(F{SR}=0,0,SUMPRODUCT($F${D0}:$F${D1},$G${D0}:$G${D1})/F{SR})').font = F_B
ws1.cell(SR, 7).number_format = P4
ws1.cell(SR, 8, f'=SUM(H{D0}:H{D1})').font = F_B
ws1.cell(SR, 8).number_format = N2
ws1.cell(SR, 12, f"=SUM('②期限分布'!{L(3+NB)}{T0}:{L(3+NB)}{T0+len(ACCOUNTS)-1})").font = F_B
ws1.cell(SR, 12).number_format = N2
ws1.cell(SR, 13, f'=SUMPRODUCT($F${D0}:$F${D1},$M${D0}:$M${D1})').font = F_B
ws1.cell(SR, 13).number_format = N2
ws1.cell(SR, 15, 'M 列 = Σ(余额 × β) 全行重定价敞口').font = F_SUB
for c in range(1, 16):
    ws1.cell(SR, c).fill = FILL_HL
    ws1.cell(SR, c).border = BD
ws1.freeze_panes = f'C{D0}'

RF = {'CODE': f"'①分母口径数据源'!$A${D0}:$A${D1}", 'NAME': f"'①分母口径数据源'!$B${D0}:$B${D1}",
      'CAT': f"'①分母口径数据源'!$C${D0}:$C${D1}", 'LINE': f"'①分母口径数据源'!$D${D0}:$D${D1}",
      'TYPE': f"'①分母口径数据源'!$E${D0}:$E${D1}", 'BAL': f"'①分母口径数据源'!$F${D0}:$F${D1}",
      'RATE': f"'①分母口径数据源'!$G${D0}:$G${D1}", 'IY': f"'①分母口径数据源'!$H${D0}:$H${D1}",
      'EA': f"'①分母口径数据源'!$I${D0}:$I${D1}", 'ISEA': f"'①分母口径数据源'!$J${D0}:$J${D1}",
      'ISLB': f"'①分母口径数据源'!$K${D0}:$K${D1}", 'W12': f"'①分母口径数据源'!$L${D0}:$L${D1}",
      'BETA': f"'①分母口径数据源'!$M${D0}:$M${D1}"}

# ===========================================================
# ② 期限分布
# ===========================================================
ws2 = wb.create_sheet('②期限分布')
NC2 = 2 + NB + 3
ws2['A1'] = '② 剩余期限分布（64 桶，等额分期偿还结构）— 取自 prcp_basic_20251231.xlsx BX~EI 列'
ws2['A1'].font = F_TITLE
ws2.merge_cells(f'A1:{L(NC2)}1')
ws2['A2'] = ('用于 NIM 的「有效计息资产」重定价分析  |  资产端 16 桶（1M~16M 等额）· 活期存款 3 桶 · 定期/市场化负债 12 桶  |  '
             'Σ分布 ≤ 当前余额，差额为未到期续作本金')
ws2['A2'].font = F_SUB
ws2.merge_cells(f'A2:{L(NC2)}2')
T2 = 3
LASTB = L(2 + NB)
ws2.cell(T2, 1, '账户编码').font = F_HEAD
ws2.cell(T2, 2, '账户名称').font = F_HEAD
for i, (bl, t) in enumerate(BUCKETS):
    c = ws2.cell(T2, 3 + i, bl)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
for k, h in enumerate(['1年内到期\n(1M~12M)', 'Σ 分布合计', '覆盖率'], 3 + NB):
    c = ws2.cell(T2, k, h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
ws2.row_dimensions[T2].height = 42
for i, w in enumerate([17, 24] + [11] * NB + [14, 14, 11], 1):
    ws2.column_dimensions[L(i)].width = w
TR0 = T2 + 1
for i, a in enumerate(ACCOUNTS):
    rr = TR0 + i
    fb = FILL_A if a['ea'] == 'EA' else (FILL_L if a['cat'] == 'LIAB' else FILL_NEA)
    ws2.cell(rr, 1, a['code']).font = F_N
    ws2.cell(rr, 2, a['name']).font = F_N
    for j, v in enumerate(a['dist']):
        c = ws2.cell(rr, 3 + j, v if v else None)
        c.font, c.border = F_INPUT, BD
        c.fill = FILL_INPUT if v else fb
        c.number_format = N0
    ws2.cell(rr, 3 + NB, f'=SUM(C{rr}:N{rr})').font = F_CALC
    ws2.cell(rr, 3 + NB).number_format = N2
    ws2.cell(rr, 4 + NB, f'=SUM(C{rr}:{LASTB}{rr})').font = F_CALC
    ws2.cell(rr, 4 + NB).number_format = N2
    ws2.cell(rr, 5 + NB, f'=IF(F{D0+i}=0,0,{L(4+NB)}{rr}/F{D0+i})').font = F_CALC
    ws2.cell(rr, 5 + NB).number_format = P2
    for c in range(1, 6 + NB):
        ws2.cell(rr, c).border = BD
TR1 = TR0 + len(ACCOUNTS) - 1
TS = TR1 + 1
ws2.cell(TS, 2, '合计').font = F_B
for k in (3 + NB, 4 + NB):
    col = L(k)
    ws2.cell(TS, k, f'=SUM({col}{TR0}:{col}{TR1})').font = F_B
    ws2.cell(TS, k).number_format = N2
for c in range(1, 6 + NB):
    ws2.cell(TS, c).fill = FILL_HL
    ws2.cell(TS, c).border = BD
ws2.freeze_panes = f'C{TR0}'

# ===========================================================
# ③ 生息资产逐账户界定（NIM 分母明细）
# ===========================================================
ws3 = wb.create_sheet('③生息资产界定')
ws3['A1'] = '③ 生息资产界定表 — 决定 NIM 分母的每一个账户'
ws3['A1'].font = F_TITLE
ws3.merge_cells('A1:L1')
ws3['A2'] = ('判定规则：资产端 且 加权平均利率 > 0 → 生息资产(EA) 计入分母；利率 = 0 → 非生息(NEA) 不计入分母  |  '
             '负债端与权益不进分母，仅提供分子')
ws3['A2'].font = F_SUB
ws3.merge_cells('A2:L2')
H3 = ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)',
      '加权平均\n利率', '年度利息\n(亿元/年)', '★分母归属', '计入分母\n余额(亿元)',
      '不计入分母\n余额(亿元)', '余额占比', '判定依据']
W3 = [17, 26, 12, 9, 13, 11, 14, 11, 14, 14, 11, 34]
r = hdr(ws3, 3, H3, W3)
AL_R0 = r
AL_R1 = AL_R0 + NA - 1
AT_ALL = AL_R1 + 1
for i, a in enumerate([x for x in ACCOUNTS if x['cat'] == 'ASSET']):
    rr = AL_R0 + i
    j = ACCOUNTS.index(a)
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'), (7, 'H'), (8, 'I')):
        ws3.cell(rr, c, f"='①分母口径数据源'!{sc}{D0+j}").font = F_N if c <= 4 else F_CALC
    ws3.cell(rr, 9, f'=IF($H{rr}="EA",$E{rr},0)').font = F_CALC
    ws3.cell(rr, 10, f'=IF($H{rr}="NEA",$E{rr},0)').font = F_CALC
    ws3.cell(rr, 11, f'=IF(SUM($E${AL_R0}:$E${AT_ALL-1})=0,0,$E{rr}/SUM($E${AL_R0}:$E${AT_ALL-1}))').font = F_CALC
    ws3.cell(rr, 12, f'=IF($H{rr}="EA","计入分母：产生利息收入","不计入：利率 0%，无利息收入")').font = F_SUB
    for c in (5, 7, 9, 10):
        ws3.cell(rr, c).number_format = N2
    ws3.cell(rr, 6).number_format = P4
    ws3.cell(rr, 11).number_format = P2
    for c in range(1, 13):
        ws3.cell(rr, c).border = BD
        ws3.cell(rr, c).fill = FILL_A if a['ea'] == 'EA' else FILL_NEA
ws3.cell(AT_ALL, 2, '资产端合计').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (9, 'I'), (10, 'J')):
    ws3.cell(AT_ALL, c, f'=SUM({col}{AL_R0}:{col}{AT_ALL-1})').font = F_B
    ws3.cell(AT_ALL, c).number_format = N2
ws3.cell(AT_ALL, 11, f'=SUM(K{AL_R0}:K{AT_ALL-1})').font = F_B
ws3.cell(AT_ALL, 11).number_format = P2
ws3.cell(AT_ALL, 12, 'I 列 = 生息资产（NIM 分母），J 列 = 非生息资产').font = F_SUB
for c in range(1, 13):
    ws3.cell(AT_ALL, c).fill = FILL_HL
    ws3.cell(AT_ALL, c).border = BD
# 生息资产小计行
EA_T = AT_ALL + 1
ws3.cell(EA_T, 2, '★ 生息资产合计（NIM 分母）').font = F_B
ws3.cell(EA_T, 5, f'=I{AT_ALL}').font = F_KPI
ws3.cell(EA_T, 5).number_format = N2
ws3.cell(EA_T, 7, f'=SUMIF($H${AL_R0}:$H${AL_R1},"EA",$G${AL_R0}:$G${AL_R1})').font = F_KPI
ws3.cell(EA_T, 7).number_format = N2
ws3.cell(EA_T, 6, f'=IF(E{EA_T}=0,0,G{EA_T}/E{EA_T})').font = F_KPIN
ws3.cell(EA_T, 6).number_format = P4
ws3.cell(EA_T, 12, 'F 列 = 生息资产加权平均收益率 ★ NIM 分子/分母').font = F_B
for c in range(1, 13):
    ws3.cell(EA_T, c).fill = FILL_KPI
    ws3.cell(EA_T, c).border = BD
NEA_T = EA_T + 1
ws3.cell(NEA_T, 2, '非生息资产合计（不计入分母）').font = F_B
ws3.cell(NEA_T, 5, f'=J{AT_ALL}').font = F_CALC
ws3.cell(NEA_T, 5).number_format = N2
ws3.cell(NEA_T, 12, '现金 / 其它非生息资产').font = F_SUB
for c in range(1, 13):
    ws3.cell(NEA_T, c).border = BD
r = NEA_T + 2
r = sec(ws3, r, '【校验】与参照物总量核对', 12)
ws3.cell(r, 2, '参照物总资产（基础数据 EJ 列 R4）').font = F_N
ws3.cell(r, 5, TA).font = F_INPUT
ws3.cell(r, 5).number_format = N2
ws3.cell(r, 12, '参照物总资产（基础数据 R4 EJ 列）').font = F_SUB
R_TA_REF = r
for c in range(1, 13):
    ws3.cell(r, c).border = BD
r += 1
ws3.cell(r, 2, '校验：资产端合计 − 参照物总资产（应为 0）').font = F_B
ws3.cell(r, 5, f'=ROUND(E{AT_ALL}-E{R_TA_REF},6)').font = F_B
ws3.cell(r, 5).number_format = N2
ws3.cell(r, 12, '末级账户余额加总应等于总资产').font = F_SUB
for c in range(1, 13):
    ws3.cell(r, c).border = BD
ws3.freeze_panes = f'C{AL_R0}'

# ===========================================================
# ④ 计息负债明细
# ===========================================================
ws4 = wb.create_sheet('④计息负债明细')
ws4['A1'] = '④ 计息负债明细 — NIM 分子的负债端构成'
ws4['A1'].font = F_TITLE
ws4.merge_cells('A1:L1')
ws4['A2'] = '计息负债全部计入 NIM 分子（利息支出）；活期存款 3 桶结构，1 年内 100% 到期，成本刚性'
ws4['A2'].font = F_SUB
ws4.merge_cells('A2:L2')
H4 = ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)',
      '加权平均\n利率', '年度利息\n(亿元/年)', '利息支出\n占比', '累计占比',
      '1年内到期\n(亿元)', '到期占比', '结构说明']
r = hdr(ws4, 3, H4, [17, 26, 12, 9, 13, 11, 14, 12, 12, 13, 11, 32])
LL_R0 = r
LL_T = LL_R0 + NL
LNOTE = {'活期存款': '3 桶（1M~3M），1 年内 100% 到期，成本几乎不随政策利率变动',
         '定期存款': '12 桶（1M~12M），到期续作时重定价',
         '市场化负债': '12 桶货币市场工具，SHIBOR/DR 联动，β 接近 1',
         '外币负债': '折人民币，受境内外利差与汇率影响'}
for k, a in enumerate([x for x in ACCOUNTS if x['cat'] == 'LIAB']):
    j = ACCOUNTS.index(a)
    rr = LL_R0 + k
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'), (7, 'H'), (10, 'L')):
        ws4.cell(rr, c, f"='①分母口径数据源'!{sc}{D0+j}").font = F_N if c <= 4 else F_LIABC
    ws4.cell(rr, 8, f'=IF($G${LL_T}=0,0,G{rr}/$G${LL_T})').font = F_LIABC
    ws4.cell(rr, 9, f'=H{rr}' if k == 0 else f'=I{rr-1}+H{rr}').font = F_LIABC
    ws4.cell(rr, 11, f'=IF(E{rr}=0,0,J{rr}/E{rr})').font = F_LIABC
    ws4.cell(rr, 12, LNOTE.get(a['line'], '')).font = F_SUB
    for c in (5, 7, 10):
        ws4.cell(rr, c).number_format = N2
    ws4.cell(rr, 6).number_format = P4
    for c in (8, 9, 11):
        ws4.cell(rr, c).number_format = P2
    for c in range(1, 13):
        ws4.cell(rr, c).border = BD
        ws4.cell(rr, c).fill = FILL_L
ws4.cell(LL_T, 2, '计息负债合计').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (10, 'J')):
    ws4.cell(LL_T, c, f'=SUM({col}{LL_R0}:{col}{LL_T-1})').font = F_B
    ws4.cell(LL_T, c).number_format = N2
ws4.cell(LL_T, 6, f'=IF(E{LL_T}=0,0,G{LL_T}/E{LL_T})').font = F_B
ws4.cell(LL_T, 6).number_format = P4
ws4.cell(LL_T, 8, f'=SUM(H{LL_R0}:H{LL_T-1})').font = F_B
ws4.cell(LL_T, 8).number_format = P2
ws4.cell(LL_T, 9, f'=I{LL_T-1}').font = F_B
ws4.cell(LL_T, 9).number_format = P2
ws4.cell(LL_T, 11, f'=IF(E{LL_T}=0,0,J{LL_T}/E{LL_T})').font = F_B
ws4.cell(LL_T, 11).number_format = P2
ws4.cell(LL_T, 12, 'F 列 = 计息负债加权平均成本率').font = F_SUB
for c in range(1, 13):
    ws4.cell(LL_T, c).fill = FILL_HL
    ws4.cell(LL_T, c).border = BD
# 负债类型分组小计
r = LL_T + 2
r = sec(ws4, r, '【附】按账户类型分组小计', 12)
GRP = [('活期存款', '活期存款'), ('定期存款', '定期存款'),
       ('市场化负债', '市场化负债'), ('外币负债', '外币负债')]
GRP0 = r
for gname, gkey in GRP:
    ws4.cell(r, 2, gname).font = F_N
    ws4.cell(r, 5, f'=SUMIF({RF["LINE"]},"{gkey}",{RF["BAL"]})').font = F_LIABC
    ws4.cell(r, 6, f'=IF(E{r}=0,0,SUMIF({RF["LINE"]},"{gkey}",{RF["IY"]})/E{r})').font = F_LIABC
    ws4.cell(r, 7, f'=SUMIF({RF["LINE"]},"{gkey}",{RF["IY"]})').font = F_LIABC
    ws4.cell(r, 5).number_format = N2
    ws4.cell(r, 6).number_format = P4
    ws4.cell(r, 7).number_format = N2
    ws4.cell(r, 12, LNOTE.get(gkey, '')).font = F_SUB
    for c in range(1, 13):
        ws4.cell(r, c).border = BD
        ws4.cell(r, c).fill = FILL_L
    r += 1
R_DEMD = GRP0
R_TERM = GRP0 + 1
ws4.cell(r, 2, '存款活期化率（活期 ÷ 存款合计）').font = F_B
ws4.cell(r, 5, f'=IF((E{R_DEMD}+E{R_TERM})=0,0,E{R_DEMD}/(E{R_DEMD}+E{R_TERM}))').font = F_KPIN
ws4.cell(r, 5).number_format = P2
ws4.cell(r, 12, '活期付息成本最低，活期化率是 NIM 的关键结构变量').font = F_B
for c in range(1, 13):
    ws4.cell(r, c).fill = FILL_KPI
    ws4.cell(r, c).border = BD
R_DMR = r
ws4.freeze_panes = f'C{LL_R0}'

# ===========================================================
# ⑤ NIM 计量表（核心）
# ===========================================================
ws5 = wb.create_sheet('⑤NIM计量表')
for i, w in enumerate([44, 17, 14, 12, 50], 1):
    ws5.column_dimensions[L(i)].width = w
ws5['A1'] = '⑤ 净息差（NIM）计量表 — 基于 prcp_basic_20251231.xlsx 真实数据'
ws5['A1'].font = F_TITLE
ws5.merge_cells('A1:E1')
ws5['A2'] = ('NIM = 利息净收入 ÷ 平均生息资产  |  NIS = 生息资产收益率 − 计息负债成本率  |  '
             '本表核心是「分母界定」，分子与「NII计量模版」完全一致  |  单位：亿元 / 亿元每年 / %')
ws5['A2'].font = F_SUB
ws5.merge_cells('A2:E2')

r = sec(ws5, 4, '【一】NIM 分母口径界定（本模版核心）', 5)
R_EA, R_NEA, R_TA = r, r + 1, r + 2
rows1 = [
    (R_EA, '★ 生息资产（NIM 分母，利率 > 0）', f"='③生息资产界定'!E{EA_T}", N2, '16 个资产账户中利率 > 0 的部分'),
    (R_NEA, '非生息资产（不计入分母）', f"='③生息资产界定'!E{NEA_T}", N2, '现金 / 其它非生息资产，利率 0%'),
    (R_TA, '资产端合计（= 参照物总资产）', f"='③生息资产界定'!E{AT_ALL}", N2, '生息 + 非生息'),
]
for rr, lab, fml, fmt, note in rows1:
    ws5.cell(rr, 1, lab).font = F_B if rr == R_EA else F_N
    ws5.cell(rr, 2, fml).font = F_KPIN if rr == R_EA else F_CALC
    ws5.cell(rr, 2).number_format = fmt
    ws5.cell(rr, 3, f'=IF($B${R_TA}=0,0,B{rr}/$B${R_TA})').font = F_CALC
    ws5.cell(rr, 3).number_format = P2
    ws5.cell(rr, 4, '亿元').font = F_SUB
    ws5.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws5.cell(rr, c).border = BD
        if rr == R_EA:
            ws5.cell(rr, c).fill = FILL_KPI
R_EQ = R_TA + 1
ws5.cell(R_EQ, 1, '所有者权益（不进入分母）').font = F_N
ws5.cell(R_EQ, 2, TE).font = F_INPUT
ws5.cell(R_EQ, 2).number_format = N2
ws5.cell(R_EQ, 4, '亿元').font = F_SUB
ws5.cell(R_EQ, 5, '参照物 10 万亿；NIM 分母不含权益').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_EQ, c).border = BD
R_TL = R_EQ + 1
ws5.cell(R_TL, 1, '计息负债（进入分子，不进入分母）').font = F_N
ws5.cell(R_TL, 2, f"='④计息负债明细'!E{LL_T}").font = F_CALC
ws5.cell(R_TL, 2).number_format = N2
ws5.cell(R_TL, 4, '亿元').font = F_SUB
ws5.cell(R_TL, 5, 'NIM = NII ÷ 生息资产，负债只影响分子').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_TL, c).border = BD

r = R_TL + 2
r = sec(ws5, r, '【二】分子：利息收入与利息支出', 5)
R_II, R_IE = r, r + 1
ws5.cell(R_II, 1, '利息收入合计（生息资产）').font = F_N
ws5.cell(R_II, 2, f"='③生息资产界定'!G{EA_T}").font = F_CALC
ws5.cell(R_II, 2).number_format = N2
ws5.cell(R_II, 4, '亿元/年').font = F_SUB
ws5.cell(R_II, 5, 'Σ 生息资产 余额 × 加权平均利率').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_II, c).border = BD
ws5.cell(R_IE, 1, '利息支出合计（计息负债）').font = F_N
ws5.cell(R_IE, 2, f"='④计息负债明细'!G{LL_T}").font = F_CALC
ws5.cell(R_IE, 2).number_format = N2
ws5.cell(R_IE, 4, '亿元/年').font = F_SUB
ws5.cell(R_IE, 5, 'Σ 计息负债 余额 × 加权平均利率').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_IE, c).border = BD

r = R_IE + 2
r = sec(ws5, r, '【三】★ 核心指标：NIM 与 NIS', 5)
R_NII, R_NIM, R_YLD, R_CST, R_NIS = r, r + 1, r + 2, r + 3, r + 4
ws5.cell(R_NII, 1, '利息净收入 NII（= 与 NII计量模版一致）').font = F_N
ws5.cell(R_NII, 2, f'=B{R_II}-B{R_IE}').font = F_CALC
ws5.cell(R_NII, 2).number_format = N2
ws5.cell(R_NII, 4, '亿元/年').font = F_SUB
ws5.cell(R_NII, 5, '校验点：应与 NII计量模版!⑥NII 完全一致').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_NII, c).border = BD
ws5.cell(R_NIM, 1, '★ 净息差 NIM（NII ÷ 生息资产）').font = F_B
ws5.cell(R_NIM, 2, f'=IF($B${R_EA}=0,0,$B${R_NII}/$B${R_EA})').font = F_KPI
ws5.cell(R_NIM, 2).number_format = P4
ws5.cell(R_NIM, 4, '%').font = F_B
ws5.cell(R_NIM, 5, '★ NIM 计量最终输出指标（监管口径分母）').font = F_B
for c in range(1, 6):
    ws5.cell(R_NIM, c).fill = FILL_KPI
    ws5.cell(R_NIM, c).border = BD
ws5.cell(R_YLD, 1, '生息资产收益率（利息收入 ÷ 生息资产）').font = F_N
ws5.cell(R_YLD, 2, f'=IF($B${R_EA}=0,0,$B${R_II}/$B${R_EA})').font = F_CALC
ws5.cell(R_YLD, 2).number_format = P4
ws5.cell(R_YLD, 4, '%').font = F_SUB
ws5.cell(R_YLD, 5, '资产端盈利能力').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_YLD, c).border = BD
ws5.cell(R_CST, 1, '计息负债成本率（利息支出 ÷ 计息负债）').font = F_N
ws5.cell(R_CST, 2, f'=IF($B${R_TL}=0,0,$B${R_IE}/$B${R_TL})').font = F_CALC
ws5.cell(R_CST, 2).number_format = P4
ws5.cell(R_CST, 4, '%').font = F_SUB
ws5.cell(R_CST, 5, '负债端付息成本').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_CST, c).border = BD
ws5.cell(R_NIS, 1, '★ 净利差 NIS（净收益率 − 净成本率）').font = F_B
ws5.cell(R_NIS, 2, f'=B{R_YLD}-B{R_CST}').font = F_KPIN
ws5.cell(R_NIS, 2).number_format = P4
ws5.cell(R_NIS, 4, '%').font = F_B
ws5.cell(R_NIS, 5, '★ 资产端与负债端的定价之差').font = F_B
for c in range(1, 6):
    ws5.cell(R_NIS, c).fill = FILL_KPI
    ws5.cell(R_NIS, c).border = BD

r = R_NIS + 2
r = sec(ws5, r, '【四】★ NIM ≠ NIS：分母错配的量化拆解（常见误区澄清）', 5)
R_MM, R_ADJ, R_ADJC = r, r + 1, r + 2
rows4 = [
    (R_MM, '生息资产 ÷ 计息负债（规模比）', f'=IF($B${R_TL}=0,0,$B${R_EA}/$B${R_TL})', N4, '生息资产规模是计息负债的多少倍'),
    (R_ADJ, '负债支持率 k = 计息负债 ÷ 生息资产', f'=IF($B${R_EA}=0,0,$B${R_TL}/$B${R_EA})', P4, '★ 恒小于 100%，因非生息资产不由负债全额融资'),
    (R_ADJC, '★ 校验：收益率 − 成本率 × k − NIM（应为 0）', f'=ROUND($B${R_YLD}-$B${R_CST}*$B${R_ADJ}-$B${R_NIM},10)', N4,
     '★ 正确关系：NIM = 生息资产收益率 − 计息负债成本率 × k（加权差，非相乘）'),
]
for rr, lab, fml, fmt, note in rows4:
    ws5.cell(rr, 1, lab).font = F_B if rr == R_ADJC else F_N
    ws5.cell(rr, 2, fml).font = F_CALC
    ws5.cell(rr, 2).number_format = fmt
    ws5.cell(rr, 4, '倍' if fmt == N4 else '%').font = F_SUB
    ws5.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws5.cell(rr, c).border = BD
R_GAPNIM = R_ADJC + 1
ws5.cell(R_GAPNIM, 1, 'NIS − NIM（利差与息差的差额）').font = F_B
ws5.cell(R_GAPNIM, 2, f'=$B${R_NIS}-$B${R_NIM}').font = F_KPIN
ws5.cell(R_GAPNIM, 2).number_format = P4
ws5.cell(R_GAPNIM, 4, '个百分点').font = F_SUB
ws5.cell(R_GAPNIM, 5, '⚠ NIM 通常 > NIS：分子中利息支出按计息负债计，分母用生息资产，两者口径不一致').font = F_B
R_MISCON = R_GAPNIM + 1
ws5.cell(R_MISCON, 1, '⚠ 常见误区：NIS × k（错误做法，非 NIM）').font = F_N
ws5.cell(R_MISCON, 2, f'=$B${R_NIS}*$B${R_ADJ}').font = F_CALC
ws5.cell(R_MISCON, 2).number_format = P4
ws5.cell(R_MISCON, 4, '%').font = F_SUB
ws5.cell(R_MISCON, 5, '净利差×负债率 ≠ 净息差；两处分母不同，必须用「收益率 − 成本率×k」').font = F_SUB
R_MISERR = R_MISCON + 1
ws5.cell(R_MISERR, 1, '误区造成的偏差（NIS × k − NIM）').font = F_N
ws5.cell(R_MISERR, 2, f'=$B${R_MISCON}-$B${R_NIM}').font = F_CALC
ws5.cell(R_MISERR, 2).number_format = BP4
ws5.cell(R_MISERR, 4, '个百分点').font = F_SUB
ws5.cell(R_MISERR, 5, '本例偏差约 −0.26pp，若误用会严重低估 NIM').font = F_SUB
for _rr in (R_MISCON, R_MISERR):
    for c in range(1, 6):
        ws5.cell(_rr, c).border = BD
for c in range(1, 6):
    ws5.cell(R_GAPNIM, c).fill = FILL_HL
    ws5.cell(R_GAPNIM, c).border = BD

r = R_MISERR + 2
r = sec(ws5, r, '【五】多口径 NIM 对比（分母界定如何影响结果）', 5)
R_M0 = r
rows5 = [
    ('口径 1（★监管口径）：NII ÷ 生息资产', f'=$B${R_NIM}', N4, '本行采用口径，剔除利率 0 的非生息资产'),
    ('口径 2：NII ÷ 资产端合计（含非生息）', f'=IF($B${R_TA}=0,0,$B${R_NII}/$B${R_TA})', P4, '分母含非生息，NIM 被系统性低估'),
    ('口径 3：NII ÷ 计息负债', f'=IF($B${R_TL}=0,0,$B${R_NII}/$B${R_TL})', P4, '分子分母口径不匹配，非监管定义，仅作对照'),
    ('口径 4：NII ÷ 总资产（含权益）', f'=IF(($B${R_TA}+$B${R_EQ})=0,0,$B${R_NII}/($B${R_TA}+$B${R_EQ}))', P4, '分母含权益，杠杆调整后口径'),
    ('口径 5：NII ÷ 风险加权资产（RWA 近似）', f'=IF(SUMIF({RF["CAT"]},"资产",{RF["BAL"]})=0,0,$B${R_NII}/SUMIF({RF["CAT"]},"资产",{RF["BAL"]}))', P4, '无表外资产，RWA 口径近似等于资产端合计'),
]
for k, (lab, fml, fmt, note) in enumerate(rows5):
    rr = R_M0 + k
    ws5.cell(rr, 1, lab).font = F_B if k == 0 else F_N
    ws5.cell(rr, 2, fml).font = F_KPIN if k == 0 else F_CALC
    ws5.cell(rr, 2).number_format = fmt
    ws5.cell(rr, 3, f'=B{rr}-$B${R_M0}').font = F_CALC
    ws5.cell(rr, 3).number_format = BP4
    ws5.cell(rr, 4, '%' if fmt == P4 else '').font = F_SUB
    ws5.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws5.cell(rr, c).border = BD
        if k == 0:
            ws5.cell(rr, c).fill = FILL_KPI
R_M4 = R_M0 + 4
ws5.cell(R_M4 + 1, 1, '口径敏感度：口径 1 与口径 2 差异').font = F_B
ws5.cell(R_M4 + 1, 2, f'=$B${R_M0}-$B${R_M0+1}').font = F_KPIN
ws5.cell(R_M4 + 1, 2).number_format = P4
ws5.cell(R_M4 + 1, 5, '仅因分母是否含非生息资产，NIM 可差 ' + '多个百分点').font = F_SUB
for c in range(1, 6):
    ws5.cell(R_M4 + 1, c).fill = FILL_HL
    ws5.cell(R_M4 + 1, c).border = BD

r = R_M4 + 3
r = sec(ws5, r, '【六】杜邦三分解：NIM 的三个驱动因子', 5)
R_D0 = r
rows6 = [
    ('资产效率 = 生息资产 ÷ 资产端合计', f'=IF($B${R_TA}=0,0,$B${R_EA}/$B${R_TA})', P2, '非生息资产占比的倒数，越大越好'),
    ('负债支持率 k = 计息负债 ÷ 生息资产', f'=$B${R_ADJ}', P4, '与【四】同源，两处分母不同'),
    ('资产端贡献 = 生息资产收益率', f'=$B${R_YLD}', P4, '每元生息资产产生的利息收入'),
    ('负债端贡献 = 成本率 × k', f'=$B${R_CST}*$B${R_D0+1}', P4, '每元生息资产承担的利息支出（已按 k 折算）'),
    ('★ NIM 复核 = 资产端 − 负债端', f'=$B${R_D0+2}-$B${R_D0+3}', P4, '★ 应等于 NIM'),
    ('校验：复核值 − NIM（应为 0）', f'=ROUND($B${R_D0+4}-$B${R_NIM},10)', N4, '分解恒等式自检'),
    ('（附）总资产口径净息差 = NIM × 资产效率', f'=$B${R_NIM}*$B${R_D0}', P4, '分母换成资产端合计，即口径 2 的 NIM'),
]
for k, (lab, fml, fmt, note) in enumerate(rows6):
    rr = R_D0 + k
    ws5.cell(rr, 1, lab).font = F_B if k in (4, 5) else F_N
    ws5.cell(rr, 2, fml).font = F_CALC
    ws5.cell(rr, 2).number_format = fmt
    ws5.cell(rr, 4, '%' if fmt == P4 else '').font = F_SUB
    ws5.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws5.cell(rr, c).border = BD
        if k == 4:
            ws5.cell(rr, c).fill = FILL_KPI

r = R_D0 + len(rows6) + 1
r = sec(ws5, r, '【七】结构比率', 5)
R_S0 = r
rows7 = [
    ('信贷资产 ÷ 生息资产', f'=SUMIF({RF["TYPE"]},"信贷",{RF["BAL"]})/$B${R_EA}', P2, '信贷占比越高，收益率越高'),
    ('存款 ÷ 计息负债', f'=(SUMIF({RF["TYPE"]},"活期",{RF["BAL"]})+SUMIF({RF["TYPE"]},"定期",{RF["BAL"]}))/$B${R_TL}', P2, '存款占比越高，成本越低'),
    ('存款活期化率（活期 ÷ 存款）', f"='④计息负债明细'!E{R_DMR}", P2, '活期成本 0.20%，定期 1.85~1.95%'),
    ('市场化负债占比', f'=SUMIF({RF["TYPE"]},"同业",{RF["BAL"]})/$B${R_TL}', P2, '市场化负债成本 2.50%，高于存款'),
    ('权益乘数（资产端合计 ÷ 权益）', f'=IF($B${R_EQ}=0,0,$B${R_TA}/$B${R_EQ})', N4, '杠杆倍数；权益乘数 × ROE = ROA × 杠杆'),
    ('权益 / 资产端合计（杠杆调整后分母）', f'=IF($B${R_TA}=0,0,$B${R_EQ}/$B${R_TA})', P2, '≈ 9.26%，故含权益口径 NIM 最低'),
]
for k, (lab, fml, fmt, note) in enumerate(rows7):
    rr = R_S0 + k
    ws5.cell(rr, 1, lab).font = F_N
    ws5.cell(rr, 2, fml).font = F_CALC
    ws5.cell(rr, 2).number_format = fmt
    ws5.cell(rr, 4, '倍' if fmt == N4 else '%').font = F_SUB
    ws5.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws5.cell(rr, c).border = BD

r = R_S0 + len(rows7) + 1
r = sec(ws5, r, '【八】勾稽校验（校验 1~9 应全部为 0）', 5)
rows8 = [
    ('校验 1：③生息资产明细 = ①Σ生息资产', f"=ROUND('③生息资产界定'!E{EA_T}-SUMIF({RF['EA']},\"EA\",{RF['BAL']}),6)", '明细 ↔ 数据源'),
    ('校验 2：④计息负债明细 = ①Σ计息负债', f"=ROUND('④计息负债明细'!E{LL_T}-SUMIF({RF['ISLB']},\"是\",{RF['BAL']}),6)", '明细 ↔ 数据源'),
    ('校验 3：生息 + 非生息 = 资产端合计', f'=ROUND($B${R_EA}+$B${R_NEA}-$B${R_TA},6)', '分母完整性'),
    ('校验 4：收益率 − 成本率 × k = NIM', f'=ROUND($B${R_YLD}-$B${R_CST}*$B${R_ADJ}-$B${R_NIM},10)', '★ NIM = 收益率 − 成本率 × 负债率'),
    ('校验 5：分解复核 = NIM', f'=ROUND($B${R_D0+4}-$B${R_NIM},10)', 'NIM = 资产端 − 负债端贡献'),
    ('校验 6：利息收入占比合计 = 100%（负债端）', f"=ROUND('④计息负债明细'!H{LL_T}-1,8)", '占比无重复无遗漏'),
    ('校验 7：①Σ年度利息 = 资产 + 负债', f'=ROUND(SUM({RF["IY"]})-SUMIF({RF["CAT"]},"资产",{RF["IY"]})-SUMIF({RF["CAT"]},"负债",{RF["IY"]}),6)', '权益年度利息为 0'),
    ('校验 8：NIM × 生息资产 = NII（还原分子）', f'=ROUND($B${R_NIM}*$B${R_EA}-$B${R_NII},6)', 'NIM 反算 NII'),
    ('校验 9：NIM 反算 NIS（NIS 应还原）', f'=ROUND(($B${R_NIM}+$B${R_CST}*$B${R_ADJ})-$B${R_YLD},10)', '由 NIM + 成本率×k 反推收益率'),
]
for k, (lab, fml, note) in enumerate(rows8):
    rr = r + k
    ws5.cell(rr, 1, lab).font = F_N
    ws5.cell(rr, 2, fml).font = F_CALC
    ws5.cell(rr, 2).number_format = N2 if k != 8 else N2
    ws5.cell(rr, 4, '亿元').font = F_SUB
    ws5.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws5.cell(rr, c).border = BD
R_CHK0 = r

r += len(rows8) + 1
r = sec(ws5, r, '【九】监管参考与达标判定', 5)
R_RL, R_RU = r, r + 1
R_J1, R_J2, R_J3, R_J4 = r + 2, r + 3, r + 4, r + 5
rows9 = [
    (R_RL, '商业银行 NIM 合理区间下限', 0.015, P2, '监管非强制指引参考值', True),
    (R_RU, '商业银行 NIM 合理区间上限', 0.025, P2, '监管非强制指引参考值', True),
    (R_J1, '本行 NIM 达标判定', f'=IF($B${R_NIM}>=$B${R_RL},"达标","不达标")', '@', 'NIM ≥ 1.50%', False),
    (R_J2, '本行 NIM 区间判定', f'=IF(AND($B${R_NIM}>=$B${R_RL},$B${R_NIM}<=$B${R_RU}),"位于合理区间","偏离合理区间")', '@', '1.50% ≤ NIM ≤ 2.50%', False),
    (R_J3, '与下限差值', f'=$B${R_NIM}-$B${R_RL}', BP4, '高于下限的百分点', False),
    (R_J4, '与上限差值', f'=$B${R_NIM}-$B${R_RU}', BP4, '高于/低于上限的百分点', False),
]
for rr, lab, val, fmt, note, is_in in rows9:
    ws5.cell(rr, 1, lab).font = F_N
    c = ws5.cell(rr, 2, val)
    c.font = F_INPUT if is_in else F_CALC
    c.number_format = fmt
    ws5.cell(rr, 4, '%' if fmt in (P2,) else '').font = F_SUB
    ws5.cell(rr, 5, note).font = F_SUB
    for cc in range(1, 6):
        ws5.cell(rr, cc).border = BD
ws5.freeze_panes = 'A4'

# ===========================================================
# ⑥ NIM 驱动因素分解
# ===========================================================
ws6 = wb.create_sheet('⑥NIM驱动分解')
for i, w in enumerate([20, 10, 15, 13, 15, 13, 15, 44], 1):
    ws6.column_dimensions[L(i)].width = w
ws6['A1'] = '⑥ NIM 驱动因素分解 — 量、价、结构三维'
ws6['A1'].font = F_TITLE
ws6.merge_cells('A1:H1')
ws6['A2'] = ('ΔNIM ≈ Σ(条线余额占比 × 条线利差)  |  '
             '量（规模摊薄）/ 价（利率变动）/ 结构（活期化、信贷占比）三条路径  |  全部引用 ① 与 NIM计量表')
ws6['A2'].font = F_SUB
ws6.merge_cells('A2:H2')

r = sec(ws6, 4, '【一】按业务条线的 NIM 贡献分解（资产端）', 8)
H6 = ['业务条线', '方向', '余额\n(亿元)', '余额占比', '综合利率',
      '利息金额\n(亿元/年)', '利息占比', '说明']
r = hdr(ws6, r, H6)
LN_KEYS = [('信贷资产', '资产'), ('债券投资', '资产'), ('金融市场', '资产'),
           ('非生息资产', '资产'), ('外币资产', '资产'),
           ('活期存款', '负债'), ('定期存款', '负债'), ('市场化负债', '负债'), ('外币负债', '负债')]
LNOTE6 = {'信贷资产': '余额 55 万亿，综合 4.63%，是 NIM 的最大贡献项',
          '债券投资': '余额 25 万亿，综合 2.67%，低收益压低整体收益率',
          '金融市场': '同业/准备金/结构化，综合 2.34%',
          '非生息资产': '利率 0%，拉低「资产端合计口径」收益率',
          '外币资产': '折人民币，综合 3.80%',
          '活期存款': '余额 38 万亿，成本 0.20%，NIM 的最大正向贡献',
          '定期存款': '余额 42 万亿，成本 1.88%',
          '市场化负债': '余额 12 万亿，成本 2.50%，成本最高',
          '外币负债': '余额 6 万亿，成本 2.60%'}
S6_0 = r
for ln, d in LN_KEYS:
    rr = r
    ws6.cell(rr, 1, ln).font = F_N
    ws6.cell(rr, 2, d).font = F_N
    ws6.cell(rr, 3, f'=SUMIF({RF["LINE"]},"{ln}",{RF["BAL"]})').font = F_CALC
    ws6.cell(rr, 4, f'=IF(SUMIF($B${S6_0}:$B${S6_0+8},$B{rr},$C${S6_0}:$C${S6_0+8})=0,0,C{rr}/SUMIF($B${S6_0}:$B${S6_0+8},$B{rr},$C${S6_0}:$C${S6_0+8}))').font = F_CALC
    ws6.cell(rr, 5, f'=IF(C{rr}=0,0,SUMIF({RF["LINE"]},"{ln}",{RF["IY"]})/C{rr})').font = F_CALC
    ws6.cell(rr, 6, f'=SUMIF({RF["LINE"]},"{ln}",{RF["IY"]})').font = F_CALC
    ws6.cell(rr, 7, f'=IF(SUMIF($B${S6_0}:$B${S6_0+8},$B{rr},$F${S6_0}:$F${S6_0+8})=0,0,F{rr}/SUMIF($B${S6_0}:$B${S6_0+8},$B{rr},$F${S6_0}:$F${S6_0+8}))').font = F_CALC
    ws6.cell(rr, 8, LNOTE6.get(ln, '')).font = F_SUB
    for c in (3, 6):
        ws6.cell(rr, c).number_format = N2
    for c in (4, 7):
        ws6.cell(rr, c).number_format = P2
    ws6.cell(rr, 5).number_format = P4
    for c in range(1, 9):
        ws6.cell(rr, c).border = BD
        ws6.cell(rr, c).fill = FILL_A if d == '资产' else FILL_L
S6_1 = r + len(LN_KEYS) - 1
r = S6_1 + 2
r = sec(ws6, r, '【二】NIM 三因子拆解：量 / 价 / 结构', 8)
H62 = ['驱动因子', '维度', '当前值', '基准', '变动量', '对 NIM 影响\n(百分点)', '敏感度', '说明']
r = hdr(ws6, r, H62)
D6_0 = r
rows62 = [
    ('资产收益率', '价', f"='⑤NIM计量表'!B{R_YLD}", f"='⑤NIM计量表'!B{R_YLD}", N4,
     '加息 25bp 全额传导', '生息资产收益率是 NIM 的第一驱动'),
    ('计息负债成本率', '价', f"='⑤NIM计量表'!B{R_CST}", f"='⑤NIM计量表'!B{R_CST}", N4,
     '加息 25bp 全额传导', '成本率上升直接压低 NIM'),
    ('规模调整系数', '结构', f"='⑤NIM计量表'!B{R_ADJ}", f"='⑤NIM计量表'!B{R_ADJ}", P4,
     '非生息资产占比', '非生息越多，系数越低，NIM 被摊薄'),
    ('存款活期化率', '结构', f"='④计息负债明细'!E{R_DMR}", f"='④计息负债明细'!E{R_DMR}", P2,
     '活期化率 +5pp', '活期 0.20% vs 定期 1.88%，5pp 相当于成本降 8.4bp'),
    ('信贷资产占比', '结构', f"='⑤NIM计量表'!B{R_S0}", f"='⑤NIM计量表'!B{R_S0}", P2,
     '信贷占比 +5pp', '信贷 4.63% vs 债券 2.67%，5pp 相当于收益率升 9.8bp'),
    ('生息资产规模', '量', f"='⑤NIM计量表'!B{R_EA}", f"='⑤NIM计量表'!B{R_EA}", N2,
     '规模变动', 'NIM 是比率，规模扩张对 NIM 中性（分子分母同增）'),
]
for lab, dim, cur, base, fmt, sens, note in rows62:
    rr = r
    ws6.cell(rr, 1, lab).font = F_N
    ws6.cell(rr, 2, dim).font = F_N
    ws6.cell(rr, 3, cur).font = F_CALC
    ws6.cell(rr, 4, base).font = F_CALC
    ws6.cell(rr, 5, '—').font = F_SUB
    ws6.cell(rr, 6, '—').font = F_SUB
    ws6.cell(rr, 7, sens).font = F_SUB
    ws6.cell(rr, 8, note).font = F_SUB
    for c in (3, 4):
        ws6.cell(rr, c).number_format = fmt
    for c in range(1, 9):
        ws6.cell(rr, c).border = BD
r += len(rows62) + 1

r = sec(ws6, r, '【三】结构优化情景（测算 NIM 提升空间）', 8)
ws6.cell(r, 1, '假设与口径：① 分子按调整后余额 × 利率重算；② 分母为调整后的生息资产；③ 不考虑规模总量变化').font = F_SUB
ws6.merge_cells(f'A{r}:H{r}')
r += 1
ws6.cell(r, 1, '参数：非生息资产转生息的收益率').font = F_B
ws6.cell(r, 3, 0.02).font = F_INPUT
ws6.cell(r, 3).number_format = P2
ws6.cell(r, 8, '可编辑；默认 2.00%（参考同业活期水平）').font = F_SUB
for c in range(1, 9):
    ws6.cell(r, c).border = BD
R_NEA_RATE = r
r += 2
H63 = ['优化情景', '维度', '调整幅度', '新 NIM', 'ΔNIM\n(百分点)', '可行性', '生效分母\n(亿元)', '说明']
r = hdr(ws6, r, H63)
O6_0 = r

EA_ = f"'⑤NIM计量表'!$B${R_EA}"
TA_ = f"'⑤NIM计量表'!$B${R_TA}"
TL_ = f"'⑤NIM计量表'!$B${R_TL}"
NIM_ = f"'⑤NIM计量表'!$B${R_NIM}"
II_ = f"'⑤NIM计量表'!$B${R_II}"
IE_ = f"'⑤NIM计量表'!$B${R_IE}"
# 分类型余额与综合利率（全部由数据源 SUMIF 实时计算，不硬编码利率）
DEM_ = f'SUMIF({RF["TYPE"]},"活期",{RF["BAL"]})'
TRM_ = f'SUMIF({RF["TYPE"]},"定期",{RF["BAL"]})'
CRD_ = f'SUMIF({RF["TYPE"]},"信贷",{RF["BAL"]})'
INV_ = f'SUMIF({RF["TYPE"]},"投资",{RF["BAL"]})'
MKT_ = f'SUMIF({RF["TYPE"]},"同业",{RF["BAL"]})'
# 各类型年度利息（余额 × 利率，已在数据源 H 列）
II_DEM = f'SUMIF({RF["TYPE"]},"活期",{RF["IY"]})'
II_TRM = f'SUMIF({RF["TYPE"]},"定期",{RF["IY"]})'
II_CRD = f'SUMIF({RF["TYPE"]},"信贷",{RF["IY"]})'
II_INV = f'SUMIF({RF["TYPE"]},"投资",{RF["IY"]})'
IE_MKT = f'SUMIF({RF["TYPE"]},"同业",{RF["IY"]})'
DEM_R = f'({II_DEM}/{DEM_})'
TRM_R = f'({II_TRM}/{TRM_})'
CRD_R = f'({II_CRD}/{CRD_})'
INV_R = f'({II_INV}/{INV_})'
MKT_R = f'({IE_MKT}/{MKT_})'

rows63 = [
    ('活期化率 −10pp：10% 定期余额转入活期', '结构', '−10pp',
     # 利息支出 = 原支出 − 定期利息 × 10% + 活期利息 × 10%（等额互换，存款总额不变）
     f'=({II_}-{IE_}+{II_TRM}*0.1-{II_DEM}*0.1)/{EA_}',
     '中', f'={EA_}',
     '新利息支出 = 原支出 − 定期利息×10% + 活期利息×10%'),
    ('活期化率 +10pp：10% 活期余额转入定期', '结构', '+10pp',
     f'=({II_}-{IE_}-{II_TRM}*0.1+{II_DEM}*0.1)/{EA_}',
     '低', f'={EA_}',
     '新利息支出 = 原支出 + 定期利息×10% − 活期利息×10%'),
    ('信贷占比 +5pp：债券置换为信贷', '结构', '+5pp',
     f'=({II_}+{EA_}*0.05*({CRD_R}-{INV_R})-{IE_})/{EA_}',
     '中低', f'={EA_}',
     '新利息收入 = 原收入 + 生息资产×5pp×(信贷利率 − 债券利率)'),
    ('计息负债成本 −10bp', '价', '−10bp',
     f'=({II_}-({IE_}-{TL_}*0.001))/{EA_}',
     '高', f'={EA_}',
     '★ 新利息支出 = 原支出 − 计息负债×10bp；最直接可控的 NIM 提升手段'),
    ('市场化负债成本 −10bp', '价', '−10bp',
     f'=({II_}-({IE_}-{IE_MKT}+{MKT_}*0.001))/{EA_}',
     '高', f'={EA_}',
     '仅下调同业/市场化负债成本 10bp，其余负债成本不变'),
    ('生息资产收益率 +10bp', '价', '+10bp',
     f'=({II_}+{EA_}*0.001-{IE_})/{EA_}',
     '中低', f'={EA_}',
     '新利息收入 = 原收入 + 生息资产×10bp；受客户议价与投放能力约束'),
    ('非生息资产 −50%：按 2% 转为生息', '结构', '−50%',
     f'=({II_}+({TA_}-{EA_})*$C${R_NEA_RATE}*0.5-{IE_})/({EA_}+({TA_}-{EA_})*0.5)',
     '中', f'={EA_}+({TA_}-{EA_})*0.5',
     '非生息资产的一半转为生息，收益率取左侧可编辑参数；分母同步扩大'),
]
for lab, dim, amt, nn, feas, dn, note in rows63:
    rr = r
    ws6.cell(rr, 1, lab).font = F_N
    ws6.cell(rr, 2, dim).font = F_N
    ws6.cell(rr, 3, amt).font = F_SUB
    ws6.cell(rr, 4, nn).font = F_CALC
    ws6.cell(rr, 4).number_format = P4
    ws6.cell(rr, 5, f'=D{rr}-{NIM_}').font = F_CALC
    ws6.cell(rr, 5).number_format = BP4
    ws6.cell(rr, 6, feas).font = F_N
    ws6.cell(rr, 7, dn).font = F_CALC
    ws6.cell(rr, 7).number_format = N2
    ws6.cell(rr, 8, note).font = F_SUB
    for c in range(1, 9):
        ws6.cell(rr, c).border = BD
    r += 1
O6_1 = r - 1
r += 1
r = sec(ws6, r, '【四】NIM 提升路径汇总', 8)
ws6.cell(r, 1, '★ 最大 ΔNIM 情景').font = F_B
ws6.cell(r, 2, f'=INDEX($A${O6_0}:$A${O6_1},MATCH(MAX($E${O6_0}:$E${O6_1}),$E${O6_0}:$E${O6_1},0))').font = F_KPIN
ws6.cell(r, 5, f'=MAX($E${O6_0}:$E${O6_1})').font = F_KPIN
ws6.cell(r, 5).number_format = BP4
ws6.cell(r, 6, f'=INDEX($F${O6_0}:$F${O6_1},MATCH(MAX($E${O6_0}:$E${O6_1}),$E${O6_0}:$E${O6_1},0))').font = F_KPIN
ws6.cell(r, 8, '6 类优化情景中 ΔNIM 最大者（自动排序）').font = F_SUB
for c in range(1, 9):
    ws6.cell(r, c).fill = FILL_KPI
    ws6.cell(r, c).border = BD
r += 1
ws6.cell(r, 1, '最优情景下的新 NIM').font = F_N
ws6.cell(r, 4, f'=MAX($D${O6_0}:$D${O6_1})').font = F_CALC
ws6.cell(r, 4).number_format = P4
ws6.cell(r, 8, '可达到的最高 NIM 水平').font = F_SUB
for c in range(1, 9):
    ws6.cell(r, c).border = BD
r += 1
ws6.cell(r, 1, '基准 NIM（对照）').font = F_N
ws6.cell(r, 4, f'={NIM_}').font = F_CALC
ws6.cell(r, 4).number_format = P4
ws6.cell(r, 8, '与上一行之差即优化空间').font = F_SUB
for c in range(1, 9):
    ws6.cell(r, c).border = BD
ws6.freeze_panes = 'A4'

# ===========================================================
# ⑦ 情景敏感性
# ===========================================================
ws7 = wb.create_sheet('⑦情景敏感性')
for i, w in enumerate([26, 12, 16, 16, 15, 16, 13, 13, 42], 1):
    ws7.column_dimensions[L(i)].width = w
ws7['A1'] = '⑦ NIM 情景敏感性分析'
ws7['A1'].font = F_TITLE
ws7.merge_cells('A1:I1')
ws7['A2'] = 'ΔNIM = Δ分子 ÷ 分母 − 原 NIM  |  分子变动引用「①分母口径数据源」的 β 加权敞口  |  分母保持不变（规模中性）'
ws7['A2'].font = F_SUB
ws7.merge_cells('A2:I2')
H7 = ['情景', 'Δr (bp)', 'Δ利息收入\n(亿元/年)', 'Δ利息支出\n(亿元/年)', 'ΔNII\n(亿元/年)',
      '情景后 NII\n(亿元/年)', '情景后 NIM', 'ΔNIM', '情景解读']
r = sec(ws7, 4, '【一】利率平行移动情景', 9)
r = hdr(ws7, r, H7)
SC0 = r
A_BETA_CELL = f'SUMPRODUCT(({RF["EA"]}="EA")*{RF["BAL"]}*{RF["BETA"]})'
L_BETA_CELL = f'SUMPRODUCT(({RF["ISLB"]}="是")*{RF["BAL"]}*{RF["BETA"]})'
SCEN = [
    ('利率平行上移 250bp', 250, '大幅加息：负债端 β≈0.98 成本上升快于资产端 β≈0.53'),
    ('利率平行上移 100bp', 100, '常规加息：负规模调整，NIM 承压'),
    ('利率平行上移 50bp', 50, '温和加息'),
    ('基准情景（利率不变）', 0, '基准：ΔNIM = 0'),
    ('利率平行下移 50bp', -50, '温和降息：成本端受益更快'),
    ('利率平行下移 100bp', -100, '降息周期：NIM 走阔'),
    ('利率平行下移 250bp', -250, '大幅降息：NIM 显著走阔'),
]
for lab, bp, note in SCEN:
    ws7.cell(r, 1, lab).font = F_N
    ws7.cell(r, 2, bp).font = F_INPUT
    ws7.cell(r, 3, f'=-$B${r}/10000*{A_BETA_CELL}').font = F_CALC
    ws7.cell(r, 4, f'=-$B${r}/10000*{L_BETA_CELL}').font = F_LIABC
    ws7.cell(r, 5, f'=C{r}-D{r}').font = F_CALC
    ws7.cell(r, 6, f"='⑤NIM计量表'!$B${R_NII}+E{r}").font = F_CALC
    ws7.cell(r, 7, f"=IF('⑤NIM计量表'!$B${R_EA}=0,0,F{r}/'⑤NIM计量表'!$B${R_EA})").font = F_CALC
    ws7.cell(r, 8, f"=G{r}-'⑤NIM计量表'!$B${R_NIM}").font = F_CALC
    ws7.cell(r, 9, note).font = F_SUB
    for c in (3, 4, 5, 6):
        ws7.cell(r, c).number_format = N2
    ws7.cell(r, 2).number_format = N0
    ws7.cell(r, 7).number_format = P4
    ws7.cell(r, 8).number_format = BP4
    for c in range(1, 10):
        ws7.cell(r, c).border = BD
    r += 1
SC1 = r - 1
R_SCMIN = r
ws7.cell(r, 1, '最不利情景 ΔNIM（最小值）').font = F_B
ws7.cell(r, 8, f'=MIN(H{SC0}:H{SC1})').font = F_B
ws7.cell(r, 8).number_format = BP4
ws7.cell(r, 9, 'NIM 变动最不利者').font = F_SUB
for c in range(1, 10):
    ws7.cell(r, c).fill = FILL_HL
    ws7.cell(r, c).border = BD
R_SCMAX = r + 1
ws7.cell(r + 1, 1, '最有利情景 ΔNIM（最大值）').font = F_B
ws7.cell(r + 1, 8, f'=MAX(H{SC0}:H{SC1})').font = F_B
ws7.cell(r + 1, 8).number_format = BP4
ws7.cell(r + 1, 9, 'NIM 变动最有利者').font = F_SUB
for c in range(1, 10):
    ws7.cell(r + 1, c).fill = FILL_HL
    ws7.cell(r + 1, c).border = BD

r = R_SCMAX + 2
r = sec(ws7, r, '【二】分母口径切换情景（NIM 对分母界定有多敏感）', 9)
r = hdr(ws7, r, ['分母口径', '分母余额\n(亿元)', '分子 NII\n(亿元/年)', 'NIM', '与监管口径差\n(百分点)',
                 '排序', '占资产端比', '—', '说明'])
DN0 = r
dns = [
    ('口径1 生息资产（★监管）', f"='⑤NIM计量表'!B{R_EA}", '监管采用；剔除利率 0 的非生息资产'),
    ('口径2 资产端合计', f"='⑤NIM计量表'!B{R_TA}", '含非生息，分母变大 NIM 变小'),
    ('口径3 总资产（+权益）', f"='⑤NIM计量表'!B{R_TA}+'⑤NIM计量表'!B{R_EQ}", '杠杆调整后分母，NIM 最低'),
    ('口径4 风险加权资产近似', f'=SUMIF({RF["CAT"]},"资产",{RF["BAL"]})', '近似口径'),
]
for name, dn, note in dns:
    rr = r
    ws7.cell(rr, 1, name).font = F_B if '监管' in name else F_N
    ws7.cell(rr, 2, dn).font = F_CALC
    ws7.cell(rr, 3, f"='⑤NIM计量表'!B{R_NII}").font = F_CALC
    ws7.cell(rr, 4, f'=IF(B{rr}=0,0,C{rr}/B{rr})').font = F_CALC
    ws7.cell(rr, 5, f"=D{rr}-'⑤NIM计量表'!$B${R_NIM}").font = F_CALC
    ws7.cell(rr, 6, f'=RANK(D{rr},$D${DN0}:$D${DN0+3})').font = F_CALC
    ws7.cell(rr, 7, f"=IF('⑤NIM计量表'!B{R_TA}=0,0,B{rr}/'⑤NIM计量表'!B{R_TA})").font = F_CALC
    ws7.cell(rr, 9, note).font = F_SUB
    ws7.cell(rr, 2).number_format = N2
    ws7.cell(rr, 3).number_format = N2
    ws7.cell(rr, 4).number_format = P4
    ws7.cell(rr, 5).number_format = BP4
    ws7.cell(rr, 7).number_format = P2
    for c in range(1, 10):
        ws7.cell(rr, c).border = BD
        if '监管' in name:
            ws7.cell(rr, c).fill = FILL_KPI
    r += 1
DN1 = r - 1
r = DN1 + 2
r = sec(ws7, r, '【三】NIM 风险敞口判定', 9)
rows7 = [
    ('加息 100bp 下 ΔNIM（核心敏感度）', f"=H{SC0+1}", BP4, '绝对值越大，NIM 对利率越敏感'),
    ('加息 250bp 下 ΔNIM', f"=H{SC0}", BP4, '极端加息情景'),
    ('降息 100bp 下 ΔNIM', f"=H{SC0+5}", BP4, '降息情景'),
    ('分母口径敏感度（口径1 − 口径3）', f"=E{DN0}-E{DN0+2}", BP4, '仅口径差异导致的 NIM 变化'),
    ('NIM 敏感度判定', f'=IF(ABS(H{SC0+1})>0.005,"高敏感（|Δ|>50bp）",IF(ABS(H{SC0+1})>0.002,"中敏感（20~50bp）","低敏感（<20bp）"))', '@', '100bp 冲击下 NIM 变动'),
    ('加息 250bp 是否跌破 1.50% 下限', f"=IF(G{SC0}<'⑤NIM计量表'!B{R_RL},\"跌破\",\"未跌破\")", '@', '监管红线检验'),
]
for k, (lab, fml, fmt, note) in enumerate(rows7):
    rr = r + k
    ws7.cell(rr, 1, lab).font = F_B if k == 0 else F_N
    ws7.cell(rr, 2, fml).font = F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 9, note).font = F_SUB
    for c in range(1, 10):
        ws7.cell(rr, c).border = BD
        if k == 0:
            ws7.cell(rr, c).fill = FILL_KPI
ws7.freeze_panes = 'A4'

# ===========================================================
# ⑧ 计算逻辑说明
# ===========================================================
ws8 = wb.create_sheet('⑧计算逻辑说明')
for i, w in enumerate([30, 62, 32], 1):
    ws8.column_dimensions[L(i)].width = w
ws8['A1'] = '⑧ NIM 计量逻辑说明 · 与 NII 模版的分工 · prcp 实体映射'
ws8['A1'].font = F_TITLE
ws8.merge_cells('A1:C1')
DOC8 = [
    ('SEC', '【一】NIM 与 NII 模版的分工'),
    ('kv', 'NII 模版回答', '「一年赚了多少利息净收入」—— 关注分子口径与规模，单位亿元/年'),
    ('kv', 'NIM 模版回答', '「每元生息资产赚多少」—— 关注分母口径与效率，单位 %'),
    ('kv', '关系式', 'NIM = NII ÷ 平均生息资产；分子完全相同，差异全在分母界定'),
    ('kv', '共用数据', '两者同源于 prcp_basic_20251231.xlsx，24 个末级账户、余额、加权平均利率完全一致'),
    ('kv', '交叉校验', '⑤NIM计量表 的 NII 应等于 NII计量模版 的 NII（校验点，见【五】）'),
    ('SEC', '【二】数据来源（prcp_basic_20251231.xlsx /「基础数据」）'),
    ('kv', '当前余额', '①分母口径数据源!F 列 ← EJ 列（列 140），原始单位元，已换算亿元'),
    ('kv', '加权平均利率', '①分母口径数据源!G 列 ← EL 列（列 142），已 /100 存为小数'),
    ('kv', '年度利息', '①分母口径数据源!H 列 = F × G，等价于参照物 EM 列 × 12'),
    ('kv', '剩余期限分布', '②期限分布!C~BJ 列 ← BX~EI 列（列 76~139），64 桶'),
    ('kv', '1 年内到期', '②期限分布 第 3+NB 列 = SUM(1M~12M 十二个桶)'),
    ('kv', '风险权重', '①分母口径数据源!N 列 ← EN 列（列 144），RWA 近似口径用'),
    ('kv', '总资产 / 总负债 / 权益', '参照物 R4 / R29 / R43 的 EJ 列：108 万亿 / 98 万亿 / 10 万亿'),
    ('SEC', '【三】★ 核心：NIM 分母界定'),
    ('kv', '生息资产判定', '资产端 且 加权平均利率 > 0 → 生息资产(EA)，计入 NIM 分母'),
    ('kv', '非生息判定', '资产端 且 利率 = 0 → 非生息(NEA)，不计入分母，但计入总资产'),
    ('kv', '本行分母构成', '生息资产 105 万亿 + 非生息资产 3 万亿 = 总资产 108 万亿'),
    ('kv', '★ NIM ≠ NIS', 'NIM = NIS × (计息负债 ÷ 生息资产)；本行系数 93.33%'),
    ('kv', '规模错配拖累', '非生息资产不为负债融资，故分母 > 分子对应规模，NIS > NIM'),
    ('kv', '多口径对比', '5 种候选分母并列，量化口径差异（NIM 可相差多个百分点）'),
    ('SEC', '【四】核心计量公式'),
    ('kv', '年度利息', 'I_i = 当前余额_i × 加权平均利率_i'),
    ('kv', '利息收入', 'Σ 生息资产 I_i'),
    ('kv', '利息支出', 'Σ 计息负债 I_i'),
    ('kv', '★ 净息差 NIM', 'NIM = (利息收入 − 利息支出) ÷ 生息资产余额'),
    ('kv', '生息资产收益率', '= 利息收入 ÷ 生息资产余额'),
    ('kv', '计息负债成本率', '= 利息支出 ÷ 计息负债余额'),
    ('kv', '★ 净利差 NIS', 'NIS = 生息资产收益率 − 计息负债成本率'),
    ('kv', '★ 规模调整系数', 'k = 计息负债 ÷ 生息资产；NIM = NIS × k'),
    ('kv', '杜邦三分解', 'NIM = 收益率 × 资产效率 − 成本率 × (负债 ÷ 资产端合计)'),
    ('kv', '重定价 β', '= MIN(0.98, MAX(0.10, 1年内到期 ÷ Σ分布))'),
    ('kv', 'ΔNII 敏感度', 'ΔNII = −Δr × (A_β − L_β)；ΔNIM = ΔNII ÷ 生息资产'),
    ('SEC', '【五】与 NII 计量模版的分工对照'),
    ('kv', '①~② 数据源', 'NII 模版与 NIM 模版同源，均直接取自 prcp_basic_20251231.xlsx'),
    ('kv', '③④⑤⑥ 对应', 'NII 模版「④利息收入明细」≈ NIM 模版「③生息资产界定」的生息资产部分'),
    ('kv', 'NIM 模版独有', '⑤NIM计量表【四】NIS 分解、【五】多口径 NIM、【六】杜邦三分解'),
    ('kv', '⑥NII驱动分解 独有', '量 / 价 / 结构三因子 + 6 类结构优化情景的 NIM 提升空间'),
    ('kv', '⑦情景敏感性 差异', 'NII 模版看 ΔNII（亿元），NIM 模版看 ΔNIM（百分点）'),
    ('kv', '交叉校验点', '两者 NII 应完全相等；分母口径是 NIM 独有的分析维度'),
    ('SEC', '【六】prcp 平台实体映射'),
    ('kv', 'KpiScheme（指标方案）', 'NIM 指标方案主体，绑定账户册方案 CoaScheme（方案 8）'),
    ('kv', 'KpiDefinition（指标定义）', 'NIM 定义：formula = NII ÷ 生息资产，unit = %'),
    ('kv', 'KpiDefinition（关联）', 'NIM 定义引用 NII（KpiDefinition of NII）作为分子'),
    ('kv', 'MetricCoefficient（系数）', '各账户加权平均利率、生息资产标志 → 系数表配置项'),
    ('kv', 'KpiValue（指标值）', '落库：value + value_date + scheme_id + definition_id'),
    ('kv', 'CoaNode（账户节点）', '24 个末级账户对应 prcp_coa_node，node_code 即 ①!A 列编码'),
    ('kv', 'prcp_data_basic', '余额与期限分布对应 rem_* 64 桶列；风险权重对应 rw 列'),
    ('kv', 'SimScheme（测算方案）', '利率情景与结构优化情景对应测算方案，批量重算 NIM'),
]
r = 3
for row in DOC8:
    if row[0] == 'SEC':
        ws8.cell(r, 1, row[1]).font = F_SEC
        for c in range(1, 4):
            ws8.cell(r, c).fill = FILL_SEC
            ws8.cell(r, c).border = BD
        ws8.cell(r, 1).alignment = AL
    else:
        ws8.cell(r, 1, row[1]).font = F_B
        ws8.cell(r, 2, row[2]).font = F_N
        ws8.cell(r, 2).alignment = AL
        for c in range(1, 4):
            ws8.cell(r, c).border = BD
    r += 1
ws8.row_dimensions[1].height = 24

wb.save(OUT)
print('OK ->', OUT)
print(f'  末级账户 {NA}资产 / {NL}负债 / {NE}权益 = {len(ACCOUNTS)}')
print(f'  ①分母口径数据源 D{D0}-D{D1} 合计 S{SR}')
print(f'  ②期限分布 T{TR0}-T{TR1} 合计 TS{TS}')
print(f'  ③生息资产界定 {AL_R0}-{AL_R1} 资产合计{AT_ALL} 生息{EA_T} 非息{NEA_T}')
print(f'  ④计息负债明细 {LL_R0}-{LL_T-1} 合计{LL_T} 活期化{R_DMR}')
print(f'  ⑤NIM计量表 EA{R_EA} NEA{R_NEA} TA{R_TA} EQ{R_EQ} TL{R_TL}')
print(f'     NII{R_NII} NIM{R_NIM} YLD{R_YLD} CST{R_CST} NIS{R_NIS} ADJ{R_ADJ} 校验{R_CHK0}')
print(f'  ⑥驱动分解 {S6_0}-{S6_1} 优化情景{O6_0}-{O6_1}')
print(f'  ⑦情景 SC{SC0}-{SC1} 分母切换{DN0}-{DN1}')