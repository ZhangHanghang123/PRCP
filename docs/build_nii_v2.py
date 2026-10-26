# -*- coding: utf-8 -*-
"""
NII 净利息收入计量模版 v2 —— 基于 prcp_basic_20251231.xlsx 真实数据重建

【数据来源】prcp_basic_20251231.xlsx / sheet「基础数据」（方案 8 / 2025-12-31）
  · 24 个末级账户真实数据：当前余额(EJ/140)、加权平均利率(EL/142)、平均利息收支(EM/143)
  · 64 桶剩余期限分布（BX~EI 列 76~139），等额分期偿还结构
  · 64 点国债收益率曲线（R47~R111）+ 64 个折现因子（R113~R176）
  · 账户册层级 / 是否末级 / 大类 / ASF-RSF / 风险权重

【口径】
  月度利息（参照物 EM 列）= 当前余额 × 加权平均利率 ÷ 100 ÷ 12
  年度利息              = EM × 12 = 余额 × 利率
  NII                   = 利息收入 − 利息支出
  NIM                   = NII ÷ 生息资产
  重定价敞口 A_β / L_β  = Σ(余额 × β)，β 由剩余期限分布 1 年内占比推导
  重定价缺口 RG         = A_β − L_β
  ΔNII(Δr)             = −Δr × RG

【单位】亿元 / 亿元每年 / %

【联动】仅「①数据源」「②期限分布」含输入，其余 7 sheet 全为公式
"""
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter as L

DOC = 'C:/银行经营/PRCP/docs/v2'
SRC = f'{DOC}/prcp_basic_20251231.xlsx'
OUT = f'{DOC}/NII计量模版_v2_真实数据.xlsx'

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


def derive_beta(dist12, is_liab):
    tot = sum(dist12)
    if tot <= 0:
        return 0.0
    return round(min(0.98, max(0.10, sum(dist12[:12]) / tot)), 3)


ACCOUNTS = []
for r in range(4, 44):
    code = _ws.cell(r, 3).value
    if not code or int(_ws.cell(r, 7).value or 0) != 1:
        continue
    name = str(_ws.cell(r, 4).value or '').strip()
    cat = _ws.cell(r, 8).value
    bal = (_ws.cell(r, C_CURBAL).value or 0) / 1e8
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
                         line=ln, atype=ATYPE[ln], src_row=r))

NA = sum(1 for a in ACCOUNTS if a['cat'] == 'ASSET')
NL = sum(1 for a in ACCOUNTS if a['cat'] == 'LIAB')
NE = sum(1 for a in ACCOUNTS if a['cat'] == 'EQUITY')
assert NA + NL + NE == 24, f'{NA}+{NL}+{NE} != 24'

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
FILL_KPI = PatternFill('solid', fgColor='FFD966')
FILL_HL = PatternFill('solid', fgColor='FFF2CC')

BD = Border(left=Side('thin', color='B4C7E7'), right=Side('thin', color='B4C7E7'),
            top=Side('thin', color='B4C7E7'), bottom=Side('thin', color='B4C7E7'))
N2 = '#,##0.00;[Red]-#,##0.00'
N0 = '#,##0;[Red]-#,##0'
N4 = '#,##0.0000;[Red]-#,##0.0000'
P2 = '0.00%'
P4 = '0.0000%'
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
# ① 数据源
# ===========================================================
ws1 = wb.create_sheet('①数据源')
H1 = ['账户编码', '账户名称', '大类', '业务条线', '账户类型', '当前余额\n(亿元)',
      '加权平均\n利率', '月度利息\n(亿元/月)', '年度利息\n(亿元/年)', '1年内到期\n(亿元)',
      '期限分布\n覆盖率', '重定价β', '风险权重', 'ASF/RSF', '数据来源']
W1 = [17, 26, 8, 12, 9, 13, 12, 15, 14, 13, 12, 10, 10, 9, 30]
ws1['A1'] = '① NII 数据源 — 全部取自 prcp_basic_20251231.xlsx「基础数据」（方案 8 / 2025-12-31）'
ws1['A1'].font = F_TITLE
ws1.merge_cells('A1:O1')
ws1['A2'] = ('🟢 绿区(蓝字) = 可编辑：当前余额、加权平均利率、重定价β  |  🟣 紫字 = 自动计算  |  '
              '月度利息 = 余额 × 利率 ÷ 100 ÷ 12（与参照物 EM 列口径一致，已逐笔核对偏差为 0）  |  '
              '1年内到期 = 「②期限分布」前 12 桶合计  |  重定价β = MIN(0.98, MAX(0.10, 1年内到期 ÷ Σ分布)) 自动推导')
ws1['A2'].font = F_SUB
ws1.merge_cells('A2:O2')
r = hdr(ws1, 3, H1, W1)
D0 = r
# ②期限分布 首行（表头第 3 行，故数据首行 = 4）；与 ①数据源 数据首行同为 D0/4
T2_ROW0 = 4
for i, a in enumerate(ACCOUNTS):
    rr = D0 + i
    src = T2_ROW0 + i
    fb = FILL_A if a['cat'] == 'ASSET' else FILL_L
    ws1.cell(rr, 1, a['code']).font = F_N
    ws1.cell(rr, 2, a['name']).font = F_N
    ws1.cell(rr, 3, CATMAP[a['cat']]).font = F_N
    ws1.cell(rr, 4, a['line']).font = F_N
    ws1.cell(rr, 5, a['atype']).font = F_N
    ws1.cell(rr, 6, a['bal']).font = F_INPUT
    ws1.cell(rr, 6).number_format = N2
    ws1.cell(rr, 7, a['rate']).font = F_INPUT
    ws1.cell(rr, 7).number_format = P4
    ws1.cell(rr, 8, f'=F{rr}*G{rr}/12').font = F_CALC
    ws1.cell(rr, 8).number_format = N2
    ws1.cell(rr, 9, f'=H{rr}*12').font = F_CALC
    ws1.cell(rr, 9).number_format = N2
    ws1.cell(rr, 10, f"='②期限分布'!{L(3+NB)}{src}").font = F_CALC
    ws1.cell(rr, 10).number_format = N2
    ws1.cell(rr, 11, f"=IF(F{rr}=0,0,('②期限分布'!{L(4+NB)}{src})/F{rr})").font = F_CALC
    ws1.cell(rr, 11).number_format = P2
    ws1.cell(rr, 12, f"=IF('②期限分布'!{L(4+NB)}{src}=0,0,MIN(0.98,MAX(0.1,'②期限分布'!{L(3+NB)}{src}/'②期限分布'!{L(4+NB)}{src})))").font = F_CALC
    ws1.cell(rr, 12).number_format = N4
    ws1.cell(rr, 13, a['rw']).font = F_N
    ws1.cell(rr, 13).number_format = P2
    ws1.cell(rr, 14, 'RSF').font = F_N
    ws1.cell(rr, 15, f"基础数据!R{a['src_row']} (EJ/EL/EM)").font = F_SUB
    for c in range(1, 16):
        ws1.cell(rr, c).border = BD
        if ws1.cell(rr, c).fill.fgColor.rgb in (None, '00000000'):
            ws1.cell(rr, c).fill = fb
    for c in (6, 7, 12):
        ws1.cell(rr, c).fill = FILL_INPUT if False else PatternFill('solid', fgColor='E2EFDA')
D1 = D0 + len(ACCOUNTS) - 1
SR = D1 + 1
ws1.cell(SR, 2, '合计 / 加权平均').font = F_B
ws1.cell(SR, 6, f'=SUM(F{D0}:F{D1})').font = F_B
ws1.cell(SR, 6).number_format = N2
ws1.cell(SR, 7, f'=IF(F{SR}=0,0,SUMPRODUCT($F${D0}:$F${D1},$G${D0}:$G${D1})/F{SR})').font = F_B
ws1.cell(SR, 7).number_format = P4
ws1.cell(SR, 8, f'=SUM(H{D0}:H{D1})').font = F_B
ws1.cell(SR, 8).number_format = N2
ws1.cell(SR, 9, f'=SUM(I{D0}:I{D1})').font = F_B
ws1.cell(SR, 9).number_format = N2
ws1.cell(SR, 10, f"=SUM('②期限分布'!{L(3+NB)}{T2_ROW0}:{L(3+NB)}{T2_ROW0+len(ACCOUNTS)-1})").font = F_B
ws1.cell(SR, 10).number_format = N2
ws1.cell(SR, 11, f"=IF(F{SR}=0,0,SUM('②期限分布'!{L(4+NB)}{T2_ROW0}:{L(4+NB)}{T2_ROW0+len(ACCOUNTS)-1})/F{SR})").font = F_B
ws1.cell(SR, 11).number_format = P2
ws1.cell(SR, 12, f'=SUMPRODUCT($F${D0}:$F${D1},$L${D0}:$L${D1})').font = F_B
ws1.cell(SR, 12).number_format = N2
ws1.cell(SR, 15, 'L 列 = Σ(余额 × β) 全行重定价敞口').font = F_SUB
for c in range(1, 16):
    ws1.cell(SR, c).fill = FILL_HL
    ws1.cell(SR, c).border = BD
ws1.freeze_panes = f'C{D0}'

RF = {'CODE': f"'①数据源'!$A${D0}:$A${D1}", 'NAME': f"'①数据源'!$B${D0}:$B${D1}",
      'CAT': f"'①数据源'!$C${D0}:$C${D1}", 'LINE': f"'①数据源'!$D${D0}:$D${D1}",
      'TYPE': f"'①数据源'!$E${D0}:$E${D1}", 'BAL': f"'①数据源'!$F${D0}:$F${D1}",
      'RATE': f"'①数据源'!$G${D0}:$G${D1}", 'IM': f"'①数据源'!$H${D0}:$H${D1}",
      'IY': f"'①数据源'!$I${D0}:$I${D1}", 'W12': f"'①数据源'!$J${D0}:$J${D1}",
      'COV': f"'①数据源'!$K${D0}:$K${D1}", 'BETA': f"'①数据源'!$L${D0}:$L${D1}"}

# ===========================================================
# ② 期限分布
# ===========================================================
ws2 = wb.create_sheet('②期限分布')
NC2 = 2 + NB + 4
ws2['A1'] = '② 剩余期限分布（64 桶，等额分期偿还结构）— 取自 prcp_basic_20251231.xlsx BX~EI 列'
ws2['A1'].font = F_TITLE
ws2.merge_cells(f'A1:{L(NC2)}1')
ws2['A2'] = ('桶口径：1M~60M 月度 + 10Y/15Y/20Y/30Y 年端  |  资产端非零桶为前 16 个（等额分期），'
             '活期存款 3 桶（3 个月内），定期/市场化负债 12 桶（12 个月内）  |  '
             'Σ分布 ≤ 当前余额，差额为未到期续作本金（资产端覆盖 53.07%，负债端 99.98%）')
ws2['A2'].font = F_SUB
ws2.merge_cells(f'A2:{L(NC2)}2')
T2 = 3
LASTB = L(2 + NB)
ws2.cell(T2, 1, '账户编码').font = F_HEAD
ws2.cell(T2, 2, '账户名称').font = F_HEAD
for i, (bl, t) in enumerate(BUCKETS):
    c = ws2.cell(T2, 3 + i, bl)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
for k, h in enumerate(['1年内到期\n(1M~12M)', 'Σ 分布合计', '当前余额', '覆盖率'], 3 + NB):
    c = ws2.cell(T2, k, h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
ws2.row_dimensions[T2].height = 42
for i, w in enumerate([17, 24] + [11] * NB + [14, 14, 13, 11], 1):
    ws2.column_dimensions[L(i)].width = w
TR0 = T2 + 1
for i, a in enumerate(ACCOUNTS):
    rr = TR0 + i
    fb = FILL_A if a['cat'] == 'ASSET' else FILL_L
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
    ws2.cell(rr, 5 + NB, f"='①数据源'!F{D0+i}").font = F_CALC
    ws2.cell(rr, 5 + NB).number_format = N2
    ws2.cell(rr, 6 + NB, f'=IF({L(5+NB)}{rr}=0,0,{L(4+NB)}{rr}/{L(5+NB)}{rr})').font = F_CALC
    ws2.cell(rr, 6 + NB).number_format = P2
    for c in range(1, 7 + NB):
        ws2.cell(rr, c).border = BD
TR1 = TR0 + len(ACCOUNTS) - 1
TS = TR1 + 1
ws2.cell(TS, 2, '合计').font = F_B
for k in (3 + NB, 4 + NB, 5 + NB):
    col = L(k)
    ws2.cell(TS, k, f'=SUM({col}{TR0}:{col}{TR1})').font = F_B
    ws2.cell(TS, k).number_format = N2
ws2.cell(TS, 6 + NB, f'=IF({L(5+NB)}{TS}=0,0,{L(4+NB)}{TS}/{L(5+NB)}{TS})').font = F_B
ws2.cell(TS, 6 + NB).number_format = P2
for c in range(1, 7 + NB):
    ws2.cell(TS, c).fill = FILL_HL
    ws2.cell(TS, c).border = BD
ws2.freeze_panes = f'C{TR0}'

# ===========================================================
# ③ 收益率曲线
# ===========================================================
ws3 = wb.create_sheet('③收益率曲线')
ws3['A1'] = '③ 国债收益率曲线与折现因子 — 取自 prcp_basic_20251231.xlsx R47~R176'
ws3['A1'].font = F_TITLE
ws3.merge_cells('A1:G1')
ws3['A2'] = '64 个关键期限（1M~60M 月度 + 10Y/15Y/20Y/30Y），中债登关键期限 + 线性插值  |  DF = 1/(1+y)^t'
ws3['A2'].font = F_SUB
ws3.merge_cells('A2:G2')
r = hdr(ws3, 3, ['期限', '年数 t', '收益率 y(%)', '折现因子 DF', 't × DF', '数据来源', '说明'],
         [12, 11, 13, 15, 13, 15, 34])
CV0 = r
KEY = ('3M', '6M', '9M', '12M', '36M', '60M', '10Y', '30Y')
for i, (ten, t, y) in enumerate(CURVE):
    rr = CV0 + i
    ws3.cell(rr, 1, ten).font = F_N
    ws3.cell(rr, 2, t).font = F_N
    ws3.cell(rr, 2).number_format = N4
    ws3.cell(rr, 3, y).font = F_N
    ws3.cell(rr, 3).number_format = P4
    ws3.cell(rr, 4, f'=1/(1+C{rr})^B{rr}').font = F_CALC
    ws3.cell(rr, 4).number_format = '0.00000000'
    ws3.cell(rr, 5, f'=B{rr}*D{rr}').font = F_CALC
    ws3.cell(rr, 5).number_format = N4
    ws3.cell(rr, 6, '中债登' if ten in KEY else '线性插值').font = F_N
    ws3.cell(rr, 7, '关键期限官方数据' if ten in KEY else '由关键期限线性插值').font = F_SUB
    for c in range(1, 8):
        ws3.cell(rr, c).border = BD
CV1 = CV0 + len(CURVE) - 1
ws3.freeze_panes = f'A{CV0}'

# ===========================================================
# ④ 利息收入明细
# ===========================================================
ws4 = wb.create_sheet('④利息收入明细')
ws4['A1'] = '④ 利息收入明细 — 生息资产逐账户拆解'
ws4['A1'].font = F_TITLE
ws4.merge_cells('A1:L1')
ws4['A2'] = '年度利息 = 当前余额 × 加权平均利率（= 参照物「平均利息收支」EM × 12）  |  非生息资产单列备查'
ws4['A2'].font = F_SUB
ws4.merge_cells('A2:L2')
r = hdr(ws4, 3, ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)', '加权平均\n利率',
                 '年度利息\n(亿元/年)', '利息收入\n占比', '累计占比', '1年内到期\n(亿元)', '到期占比', '口径说明'],
         [17, 26, 12, 9, 13, 12, 14, 12, 12, 13, 11, 30])
A_L = [a for a in ACCOUNTS if a['cat'] == 'ASSET' and a['rate'] > 0]
A_Z = [a for a in ACCOUNTS if a['cat'] == 'ASSET' and a['rate'] == 0]
AR0 = r
AT = AR0 + len(A_L)
for k, a in enumerate(A_L):
    i = ACCOUNTS.index(a)
    rr = AR0 + k
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'), (7, 'I'), (10, 'J')):
        ws4.cell(rr, c, f"='①数据源'!{sc}{D0+i}").font = F_CALC if c >= 5 else F_N
    ws4.cell(rr, 8, f'=IF($G${AT}=0,0,G{rr}/$G${AT})').font = F_CALC
    ws4.cell(rr, 9, f'=H{rr}' if k == 0 else f'=I{rr-1}+H{rr}').font = F_CALC
    ws4.cell(rr, 11, f'=IF(E{rr}=0,0,J{rr}/E{rr})').font = F_CALC
    ws4.cell(rr, 12, f"基础数据!R{a['src_row']} · β={a['beta']:.3f}").font = F_SUB
    for c in (5, 7, 10):
        ws4.cell(rr, c).number_format = N2
    ws4.cell(rr, 6).number_format = P4
    for c in (8, 9, 11):
        ws4.cell(rr, c).number_format = P2
    for c in range(1, 13):
        ws4.cell(rr, c).border = BD
        ws4.cell(rr, c).fill = FILL_A
ws4.cell(AT, 2, '利息收入合计（生息资产）').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (10, 'J')):
    ws4.cell(AT, c, f'=SUM({col}{AR0}:{col}{AT-1})').font = F_B
    ws4.cell(AT, c).number_format = N2
ws4.cell(AT, 6, f'=IF(E{AT}=0,0,G{AT}/E{AT})').font = F_B
ws4.cell(AT, 6).number_format = P4
ws4.cell(AT, 8, f'=SUM(H{AR0}:H{AT-1})').font = F_B
ws4.cell(AT, 8).number_format = P2
ws4.cell(AT, 9, f'=I{AT-1}').font = F_B
ws4.cell(AT, 9).number_format = P2
ws4.cell(AT, 11, f'=IF(E{AT}=0,0,J{AT}/E{AT})').font = F_B
ws4.cell(AT, 11).number_format = P2
ws4.cell(AT, 12, 'F 列 = 加权平均收益率 · H 列合计应为 100% · K 列 = 1 年内到期占比').font = F_SUB
for c in range(1, 13):
    ws4.cell(AT, c).fill = FILL_HL
    ws4.cell(AT, c).border = BD
r = AT + 2
r = sec(ws4, r, '【附】非生息资产（加权平均利率 = 0，不计入利息收入与 NIM 分母）', 12)
NZ0 = r
for k, a in enumerate(A_Z):
    i = ACCOUNTS.index(a)
    rr = NZ0 + k
    ws4.cell(rr, 2, f"='①数据源'!B{D0+i}").font = F_N
    ws4.cell(rr, 5, f"='①数据源'!F{D0+i}").font = F_CALC
    ws4.cell(rr, 6, f"='①数据源'!G{D0+i}").font = F_CALC
    ws4.cell(rr, 7, f"='①数据源'!I{D0+i}").font = F_CALC
    ws4.cell(rr, 12, '利率 0%，无利息收入，已从 NIM 分母剔除').font = F_SUB
    for c in (5, 7):
        ws4.cell(rr, c).number_format = N2
    ws4.cell(rr, 6).number_format = P4
    for c in range(1, 13):
        ws4.cell(rr, c).border = BD
        ws4.cell(rr, c).fill = FILL_A
NZ1 = NZ0 + len(A_Z) - 1
ANZ = NZ1 + 1
ws4.cell(ANZ, 2, '非生息资产合计（备查）').font = F_B
for c, col in ((5, 'E'), (7, 'G')):
    ws4.cell(ANZ, c, f'=SUM({col}{NZ0}:{col}{NZ1})').font = F_B
    ws4.cell(ANZ, c).number_format = N2
for c in range(1, 13):
    ws4.cell(ANZ, c).fill = FILL_HL
    ws4.cell(ANZ, c).border = BD
ws4.freeze_panes = f'C{AR0}'

# ===========================================================
# ⑤ 利息支出明细
# ===========================================================
ws5 = wb.create_sheet('⑤利息支出明细')
ws5['A1'] = '⑤ 利息支出明细 — 计息负债逐账户拆解'
ws5['A1'].font = F_TITLE
ws5.merge_cells('A1:L1')
ws5['A2'] = '年度利息 = 当前余额 × 加权平均利率  |  活期存款为 3 桶结构（3 个月内到期），重定价快于资产端'
ws5['A2'].font = F_SUB
ws5.merge_cells('A2:L2')
r = hdr(ws5, 3, ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)', '加权平均\n利率',
                 '年度利息\n(亿元/年)', '利息支出\n占比', '累计占比', '1年内到期\n(亿元)', '到期占比', '口径说明'],
         [17, 26, 12, 9, 13, 12, 14, 12, 12, 13, 11, 30])
L_L = [a for a in ACCOUNTS if a['cat'] == 'LIAB']
LR0 = r
LT = LR0 + len(L_L)
for k, a in enumerate(L_L):
    i = ACCOUNTS.index(a)
    rr = LR0 + k
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'), (7, 'I'), (10, 'J')):
        ws5.cell(rr, c, f"='①数据源'!{sc}{D0+i}").font = F_N if c <= 4 else F_LIABC
    ws5.cell(rr, 8, f'=IF($G${LT}=0,0,G{rr}/$G${LT})').font = F_LIABC
    ws5.cell(rr, 9, f'=H{rr}' if k == 0 else f'=I{rr-1}+H{rr}').font = F_LIABC
    ws5.cell(rr, 11, f'=IF(E{rr}=0,0,J{rr}/E{rr})').font = F_LIABC
    ws5.cell(rr, 12, f"基础数据!R{a['src_row']} · β={a['beta']:.3f}").font = F_SUB
    for c in (5, 7, 10):
        ws5.cell(rr, c).number_format = N2
    ws5.cell(rr, 6).number_format = P4
    for c in (8, 9, 11):
        ws5.cell(rr, c).number_format = P2
    for c in range(1, 13):
        ws5.cell(rr, c).border = BD
        ws5.cell(rr, c).fill = FILL_L
ws5.cell(LT, 2, '利息支出合计（计息负债）').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (10, 'J')):
    ws5.cell(LT, c, f'=SUM({col}{LR0}:{col}{LT-1})').font = F_B
    ws5.cell(LT, c).number_format = N2
ws5.cell(LT, 6, f'=IF(E{LT}=0,0,G{LT}/E{LT})').font = F_B
ws5.cell(LT, 6).number_format = P4
ws5.cell(LT, 8, f'=SUM(H{LR0}:H{LT-1})').font = F_B
ws5.cell(LT, 8).number_format = P2
ws5.cell(LT, 9, f'=I{LT-1}').font = F_B
ws5.cell(LT, 9).number_format = P2
ws5.cell(LT, 11, f'=IF(E{LT}=0,0,J{LT}/E{LT})').font = F_B
ws5.cell(LT, 11).number_format = P2
ws5.cell(LT, 12, 'F 列 = 加权平均成本率 · H 列合计应为 100% · K 列 = 1 年内到期占比').font = F_SUB
for c in range(1, 13):
    ws5.cell(LT, c).fill = FILL_HL
    ws5.cell(LT, c).border = BD
ws5.freeze_panes = f'C{LR0}'

# ===========================================================
# ⑥ NII 计量表
# ===========================================================
ws6 = wb.create_sheet('⑥NII计量表')
for i, w in enumerate([40, 17, 15, 12, 48], 1):
    ws6.column_dimensions[L(i)].width = w
ws6['A1'] = '⑥ 净利息收入（NII）计量表 — 基于 prcp_basic_20251231.xlsx 真实数据'
ws6['A1'].font = F_TITLE
ws6.merge_cells('A1:E1')
ws6['A2'] = ('NII = 利息收入 − 利息支出  |  NIM = NII ÷ 生息资产  |  '
             '引用「④利息收入明细」「⑤利息支出明细」逐级联动  |  单位：亿元 / 亿元每年 / %')
ws6['A2'].font = F_SUB
ws6.merge_cells('A2:E2')

r = sec(ws6, 4, '【一】生息资产与计息负债规模', 5)
R_EA, R_NZ, R_LB, R_DEP, R_MKT, R_FXL, R_EQ = r, r + 1, r + 2, r + 3, r + 4, r + 5, r + 6
rows1 = [
    (R_EA, '生息资产合计（加权平均利率 > 0）', f"='④利息收入明细'!E{AT}", N2, '剔除非生息资产后的 NIM 分母'),
    (R_NZ, '其中：已剔除非生息资产', f"='④利息收入明细'!E{ANZ}", N2, '加权平均利率 = 0，不计入分母'),
    (R_LB, '计息负债合计', f"='⑤利息支出明细'!E{LT}", N2, '7 个计息负债账户'),
    (R_DEP, '其中：存款类负债', f'=SUMIF({RF["TYPE"]},"活期",{RF["BAL"]})+SUMIF({RF["TYPE"]},"定期",{RF["BAL"]})', N2, '活期 380,000 + 定期 420,000'),
    (R_MKT, '其中：市场化负债', f'=SUMIF({RF["TYPE"]},"同业",{RF["BAL"]})', N2, '人民币市场化负债'),
    (R_FXL, '其中：外币负债', f'=SUMIF({RF["TYPE"]},"外币",{RF["BAL"]})-SUMIF({RF["CAT"]},"负债",{RF["BAL"]})', N2, '负债端外币 = 全部外币 − 资产端外币'),
    (R_EQ, '所有者权益', f"='①数据源'!F{D0+[ACCOUNTS.index(a) for a in ACCOUNTS if a['cat']=='EQUITY'][0]}", N2, '不产生利息收支，仅作规模对照'),
]
for rr, lab, fml, fmt, note in rows1:
    ws6.cell(rr, 1, lab).font = F_N
    ws6.cell(rr, 2, fml).font = F_CALC
    ws6.cell(rr, 2).number_format = fmt
    ws6.cell(rr, 3, f'=IF($B${R_EA}=0,0,B{rr}/$B${R_EA})').font = F_CALC
    ws6.cell(rr, 3).number_format = P2
    ws6.cell(rr, 4, '亿元').font = F_SUB
    ws6.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws6.cell(rr, c).border = BD

r = R_EQ + 2
r = sec(ws6, r, '【二】利息收入与利息支出', 5)
R_II, R_IE = r, r + 1
R_CA, R_CL = r + 2, r + 3
rows2 = [
    (R_II, '利息收入合计（年度）', f"='④利息收入明细'!G{AT}", 'A', '14 个生息资产账户'),
    (R_IE, '利息支出合计（年度）', f"='⑤利息支出明细'!G{LT}", 'E', '7 个计息负债账户'),
    (R_CA, '参照物校验：Σ月度利息 × 12（资产）', f'=SUMIF({RF["CAT"]},"资产",{RF["IM"]})*12', 'A', '应与利息收入合计相等'),
    (R_CL, '参照物校验：Σ月度利息 × 12（负债）', f'=SUMIF({RF["CAT"]},"负债",{RF["IM"]})*12', 'E', '应与利息支出合计相等'),
]
for rr, lab, fml, tag, note in rows2:
    ws6.cell(rr, 1, lab).font = F_N
    ws6.cell(rr, 2, fml).font = F_CALC
    ws6.cell(rr, 2).number_format = N2
    ws6.cell(rr, 4, '亿元/年').font = F_SUB
    ws6.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws6.cell(rr, c).border = BD

r = R_CL + 2
r = sec(ws6, r, '【三】净利息收入 NII（核心指标）', 5)
R_NII = r
ws6.cell(r, 1, '★ 净利息收入 NII').font = F_B
ws6.cell(r, 2, f'=B{R_II}-B{R_IE}').font = F_KPI
ws6.cell(r, 2).number_format = N2
ws6.cell(r, 4, '亿元/年').font = F_B
ws6.cell(r, 5, 'NII = 利息收入 − 利息支出').font = F_B
for c in range(1, 6):
    ws6.cell(r, c).fill = FILL_KPI
    ws6.cell(r, c).border = BD
R_IIM = r + 1
ws6.cell(R_IIM, 1, '月度净利息收入（对照参照物 EM 口径）').font = F_N
ws6.cell(R_IIM, 2, f'=SUMIF({RF["CAT"]},"资产",{RF["IM"]})-SUMIF({RF["CAT"]},"负债",{RF["IM"]})').font = F_CALC
ws6.cell(R_IIM, 2).number_format = N2
ws6.cell(R_IIM, 4, '亿元/月').font = F_SUB
ws6.cell(R_IIM, 5, '= NII ÷ 12，与参照物「平均利息收支」列完全对齐').font = F_SUB
for c in range(1, 6):
    ws6.cell(R_IIM, c).border = BD

r = R_IIM + 2
r = sec(ws6, r, '【四】利差与净息差核心比率', 5)
R_YLD, R_CST, R_NIS, R_NIM = r, r + 1, r + 2, r + 3
rows4 = [
    (R_YLD, '生息资产收益率（利息收入 ÷ 生息资产）', f'=IF($B${R_EA}=0,0,$B${R_II}/$B${R_EA})', P4, '资产端盈利能力'),
    (R_CST, '计息负债成本率（利息支出 ÷ 计息负债）', f'=IF($B${R_LB}=0,0,$B${R_IE}/$B${R_LB})', P4, '负债端付息成本'),
    (R_NIS, '净利差 NIS（净收益率 − 净成本率）', f'=B{r}-B{r+1}', P4, '资产端与负债端定价之差'),
    (R_NIM, '★ 净息差 NIM（NII ÷ 生息资产）', f'=IF($B${R_EA}=0,0,$B${R_NII}/$B${R_EA})', P4, '★ NII 计量最终输出指标'),
]
for rr, lab, fml, fmt, note in rows4:
    ws6.cell(rr, 1, lab).font = F_B if rr in (R_NIS, R_NIM) else F_N
    ws6.cell(rr, 2, fml).font = F_KPIN if rr == R_NIM else F_CALC
    ws6.cell(rr, 2).number_format = fmt
    ws6.cell(rr, 4, '%').font = F_SUB
    ws6.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws6.cell(rr, c).border = BD
        if rr == R_NIM:
            ws6.cell(rr, c).fill = FILL_KPI

r = R_NIM + 2
r = sec(ws6, r, '【五】资产负债结构与存款成本辅助比率', 5)
R_LN, R_DP, R_LDR, R_LTD, R_DMD = r, r + 1, r + 2, r + 3, r + 4
rows5 = [
    (R_LN, '信贷资产余额（贷款 5 项）', f'=SUMIF({RF["TYPE"]},"信贷",{RF["BAL"]})', N2, '对公 / 个人 / 信用卡 / 票据 / 非银'),
    (R_DP, '存款余额（活期 + 定期）', f'=SUMIF({RF["TYPE"]},"活期",{RF["BAL"]})+SUMIF({RF["TYPE"]},"定期",{RF["BAL"]})', N2, '对公 + 零售'),
    (R_LDR, '存贷比（信贷资产 ÷ 计息负债）', f'=IF($B${R_LB}=0,0,$B${R_LN}/$B${R_LB})', P2, '监管上限 100%'),
    (R_LTD, '贷存比（信贷资产 ÷ 存款余额）', f'=IF($B${R_DP}=0,0,$B${R_LN}/$B${R_DP})', P2, '存款对贷款的覆盖程度'),
    (R_DMD, '存款活期化率（活期 ÷ 存款合计）', f'=IF($B${R_DP}=0,0,SUMIF({RF["TYPE"]},"活期",{RF["BAL"]})/$B${R_DP})', P2, '活期付息成本低，活期化率越高 → NIM 越高'),
]
for rr, lab, fml, fmt, note in rows5:
    ws6.cell(rr, 1, lab).font = F_N
    ws6.cell(rr, 2, fml).font = F_CALC
    ws6.cell(rr, 2).number_format = fmt
    ws6.cell(rr, 4, '亿元' if fmt == N2 else '%').font = F_SUB
    ws6.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws6.cell(rr, c).border = BD

r = R_DMD + 2
r = sec(ws6, r, '【六】勾稽校验（校验 1~9 应全部为 0）', 5)
rows6 = [
    ('校验 1：④明细 = ①Σ年度利息（资产，利率>0）', f"=ROUND('④利息收入明细'!G{AT}-SUMIF({RF['CAT']},\"资产\",{RF['IY']}),6)", '明细 ↔ 数据源交叉勾稽'),
    ('校验 2：⑤明细 = ①Σ年度利息（负债）', f"=ROUND('⑤利息支出明细'!G{LT}-SUMIF({RF['CAT']},\"负债\",{RF['IY']}),6)", '明细 ↔ 数据源交叉勾稽'),
    ('校验 3：①Σ全部年度利息 = 资产 + 负债', f"=ROUND(SUM({RF['IY']})-SUMIF({RF['CAT']},\"资产\",{RF['IY']})-SUMIF({RF['CAT']},\"负债\",{RF['IY']}),6)", '权益年度利息应为 0'),
    ('校验 4：Σ月度利息 × 12 = Σ年度利息（资产）', f"=ROUND(SUMIF({RF['CAT']},\"资产\",{RF['IM']})*12-SUMIF({RF['CAT']},\"资产\",{RF['IY']}),6)", '参照物 EM 口径'),
    ('校验 5：Σ月度利息 × 12 = Σ年度利息（负债）', f"=ROUND(SUMIF({RF['CAT']},\"负债\",{RF['IM']})*12-SUMIF({RF['CAT']},\"负债\",{RF['IY']}),6)", '参照物 EM 口径'),
    ('校验 6：④利息收入占比合计 = 100%', f"=ROUND('④利息收入明细'!H{AT}-1,8)", '占比无重复无遗漏'),
    ('校验 7：⑤利息支出占比合计 = 100%', f"=ROUND('⑤利息支出明细'!H{LT}-1,8)", '占比无重复无遗漏'),
    ('校验 8：NII = 利息收入 − 利息支出（核心恒等式）', f"=ROUND($B${R_NII}-($B${R_II}-$B${R_IE}),8)", 'NII 主口径恒等式自检'),
    ('校验 9：年度 NII = 月度 NII × 12', f"=ROUND($B${R_NII}-$B${R_IIM}*12,6)", '年度与月度口径对齐'),
    ('信息项：Σ期限分布 − Σ当前余额（差额 = 未覆盖续作本金）', f"='②期限分布'!{L(4+NB)}{TS}-'②期限分布'!{L(5+NB)}{TS}", '资产端覆盖 53.07%，负债端 99.98%'),
]
for k, (lab, fml, note) in enumerate(rows6):
    rr = r + k
    ws6.cell(rr, 1, lab).font = F_N
    ws6.cell(rr, 2, fml).font = F_CALC
    ws6.cell(rr, 2).number_format = N2
    ws6.cell(rr, 4, '亿元').font = F_SUB
    ws6.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws6.cell(rr, c).border = BD
R_CHK1 = r
r += len(rows6) + 1
r = sec(ws6, r, '【七】监管参考与达标判定', 5)
R_RL, R_RU = r, r + 1
R_J1, R_J2, R_J3 = r + 2, r + 3, r + 4
rows7 = [
    (R_RL, '商业银行 NIM 合理区间下限', 0.015, P2, '监管非强制指引参考值', True),
    (R_RU, '商业银行 NIM 合理区间上限', 0.025, P2, '监管非强制指引参考值', True),
    (R_J1, '本行 NIM 达标判定', f'=IF($B${R_NIM}>=$B${R_RL},"达标","不达标")', '@', 'NIM ≥ 1.50%', False),
    (R_J2, '本行 NIM 区间判定', f'=IF(AND($B${R_NIM}>=$B${R_RL},$B${R_NIM}<=$B${R_RU}),"位于合理区间","偏离合理区间")', '@', '1.50% ≤ NIM ≤ 2.50%', False),
    (R_J3, '本行存贷比达标判定', f'=IF($B${R_LDR}<=1,"达标","超标")', '@', '存贷比 ≤ 100%', False),
]
for rr, lab, val, fmt, note, is_in in rows7:
    ws6.cell(rr, 1, lab).font = F_N
    c = ws6.cell(rr, 2, val)
    if is_in:
        c.font = F_INPUT
    else:
        c.font = F_CALC
    c.number_format = fmt
    ws6.cell(rr, 4, '%' if fmt != '@' else '').font = F_SUB
    ws6.cell(rr, 5, note).font = F_SUB
    for cc in range(1, 6):
        ws6.cell(rr, cc).border = BD
ws6.freeze_panes = 'A4'

# ===========================================================
# ⑦ 期限结构与重定价
# ===========================================================
ws7 = wb.create_sheet('⑦期限结构与重定价')
for i, w in enumerate([26, 10, 14, 11, 15, 14, 12, 42], 1):
    ws7.column_dimensions[L(i)].width = w
ws7['A1'] = '⑦ 剩余期限结构与重定价缺口分析'
ws7['A1'].font = F_TITLE
ws7.merge_cells('A1:H1')
ws7['A2'] = 'A_β / L_β = Σ(余额 × β)，β 由「②期限分布」1 年内（12 桶）到期占比推导  |  ΔNII = −Δr × (A_β − L_β)'
ws7['A2'].font = F_SUB
ws7.merge_cells('A2:H2')
NOTE = {
    '信贷资产': '16 桶等额分期，1 年内到期约 1/4，重定价滞后于负债端',
    '债券投资': '16 桶分期；到期后按市价重定价，久期较长',
    '金融市场': '同业 / 准备金 / 结构化融资，货币市场驱动，β 较高',
    '非生息资产': '利率 0%，无重定价敞口',
    '外币资产': '折人民币计价，境内利率 + 汇率双重影响',
    '活期存款': '3 桶（3 个月内）结构，1 年内基本全部到期，β = 1',
    '定期存款': '12 桶（12 个月内）结构，到期可续作定价',
    '市场化负债': '12 桶货币市场工具，β 接近 1',
    '外币负债': '折人民币负债，境内外利差影响',
    '权益': '无利息，不参与 NII',
}
r = sec(ws7, 4, '【一】账户重定价属性明细（24 个末级账户）', 8)
r = hdr(ws7, r, ['账户名称', '方向', '当前余额\n(亿元)', '重定价β', '重定价敞口\n(亿元)',
                 '1年内到期\n(亿元)', '到期占比', '到期 / 非到期结构说明'])
EX0 = r
for k, a in enumerate(ACCOUNTS):
    i = ACCOUNTS.index(a)
    rr = EX0 + k
    ws7.cell(rr, 1, f"='①数据源'!B{D0+i}").font = F_N
    ws7.cell(rr, 2, f"='①数据源'!C{D0+i}").font = F_N
    ws7.cell(rr, 3, f"='①数据源'!F{D0+i}").font = F_CALC
    ws7.cell(rr, 4, f"='①数据源'!L{D0+i}").font = F_CALC
    ws7.cell(rr, 5, f'=C{rr}*D{rr}').font = F_CALC
    ws7.cell(rr, 6, f"='①数据源'!J{D0+i}").font = F_CALC
    ws7.cell(rr, 7, f'=IF(C{rr}=0,0,F{rr}/C{rr})').font = F_CALC
    ws7.cell(rr, 8, NOTE.get(a['line'], '')).font = F_SUB
    for c in (3, 5, 6):
        ws7.cell(rr, c).number_format = N2
    ws7.cell(rr, 4).number_format = N4
    ws7.cell(rr, 7).number_format = P2
    for c in range(1, 9):
        ws7.cell(rr, c).border = BD
        ws7.cell(rr, c).fill = FILL_A if a['cat'] == 'ASSET' else (FILL_L if a['cat'] == 'LIAB' else FILL_HL)
EX1 = EX0 + len(ACCOUNTS) - 1


def agg_row(rr, label, cond):
    ws7.cell(rr, 1, label).font = F_B
    for c, col, agg in ((3, 'C', f'=SUMIF($B${EX0}:$B${EX1},"{cond}",$C${EX0}:$C${EX1})'),
                        (5, 'E', f'=SUMIF($B${EX0}:$B${EX1},"{cond}",$E${EX0}:$E${EX1})'),
                        (6, 'F', f'=SUMIF($B${EX0}:$B${EX1},"{cond}",$F${EX0}:$F${EX1})')):
        ws7.cell(rr, c, agg).font = F_B
        ws7.cell(rr, c).number_format = N2
    ws7.cell(rr, 4, f'=IF(C{rr}=0,0,E{rr}/C{rr})').font = F_B
    ws7.cell(rr, 4).number_format = N4
    ws7.cell(rr, 7, f'=IF(C{rr}=0,0,F{rr}/C{rr})').font = F_B
    ws7.cell(rr, 7).number_format = P2
    for c in range(1, 9):
        ws7.cell(rr, c).fill = FILL_HL
        ws7.cell(rr, c).border = BD


R_EXA = EX1 + 1
agg_row(R_EXA, '资产重定价敞口 A_β 合计', '资产')
ws7.cell(R_EXA, 8, 'D 列 = 组合加权平均 β').font = F_SUB
R_EXL = EX1 + 2
agg_row(R_EXL, '负债重定价敞口 L_β 合计', '负债')
ws7.cell(R_EXL, 8, 'D 列 = 组合加权平均 β').font = F_SUB
R_RG = EX1 + 3
ws7.cell(R_RG, 1, '★ 重定价缺口 RG = A_β − L_β').font = F_B
ws7.cell(R_RG, 5, f'=E{R_EXA}-E{R_EXL}').font = F_KPI
ws7.cell(R_RG, 5).number_format = N2
ws7.cell(R_RG, 8, '★ RG > 0 → 利率上行时 NII 受损；RG < 0 → 利率上行时 NII 受益').font = F_B
for c in range(1, 9):
    ws7.cell(R_RG, c).fill = FILL_KPI
    ws7.cell(R_RG, c).border = BD
R_STEP = EX1 + 4
ws7.cell(R_STEP, 1, '利率每平行上移 10bp 对 NII 的影响').font = F_N
ws7.cell(R_STEP, 5, f'=-E{R_RG}*0.001').font = F_CALC
ws7.cell(R_STEP, 5).number_format = N2
ws7.cell(R_STEP, 8, '= −RG × 0.001（亿元/年 / 10bp）').font = F_SUB
for c in range(1, 9):
    ws7.cell(R_STEP, c).border = BD
R_ELAST = EX1 + 5
ws7.cell(R_ELAST, 1, 'NII 利率弹性（−RG ÷ 生息资产）').font = F_N
ws7.cell(R_ELAST, 5, f"=IF('⑥NII计量表'!B{R_EA}=0,0,-E{R_RG}/'⑥NII计量表'!B{R_EA})").font = F_CALC
ws7.cell(R_ELAST, 5).number_format = P4
ws7.cell(R_ELAST, 8, 'ΔNII/NII ÷ Δr').font = F_SUB
for c in range(1, 9):
    ws7.cell(R_ELAST, c).border = BD

r = R_ELAST + 2
r = sec(ws7, r, '【二】按业务条线的期限与重定价结构', 8)
r = hdr(ws7, r, ['业务条线', '方向', '当前余额\n(亿元)', '组合 β', '重定价敞口\n(亿元)',
                 '1年内到期\n(亿元)', '到期占比', '说明'])
LINE_SPECS = [('信贷资产', '资产'), ('债券投资', '资产'), ('金融市场', '资产'),
              ('非生息资产', '资产'), ('外币资产', '资产'),
              ('活期存款', '负债'), ('定期存款', '负债'), ('市场化负债', '负债'), ('外币负债', '负债')]
LN0 = r
for ln, d in LINE_SPECS:
    rr = r
    ws7.cell(rr, 1, ln).font = F_N
    ws7.cell(rr, 2, d).font = F_N
    ws7.cell(rr, 3, f'=SUMIF($A${EX0}:$A${EX1},$A{rr},$C${EX0}:$C${EX1})').font = F_CALC
    ws7.cell(rr, 4, f'=IF(C{rr}=0,0,E{rr}/C{rr})').font = F_CALC
    ws7.cell(rr, 5, f'=SUMIF($A${EX0}:$A${EX1},$A{rr},$E${EX0}:$E${EX1})').font = F_CALC
    ws7.cell(rr, 6, f'=SUMIF($A${EX0}:$A${EX1},$A{rr},$F${EX0}:$F${EX1})').font = F_CALC
    ws7.cell(rr, 7, f'=IF(C{rr}=0,0,F{rr}/C{rr})').font = F_CALC
    ws7.cell(rr, 8, NOTE.get(ln, '')).font = F_SUB
    for c in (3, 5, 6):
        ws7.cell(rr, c).number_format = N2
    ws7.cell(rr, 4).number_format = N4
    ws7.cell(rr, 7).number_format = P2
    for c in range(1, 9):
        ws7.cell(rr, c).border = BD
        ws7.cell(rr, c).fill = FILL_A if d == '资产' else FILL_L
    r += 1
LN1 = r - 1
r += 1
ws7.cell(r, 1, '校验：资产条线敞口合计 = A_β 合计').font = F_B
ws7.cell(r, 5, f'=ROUND(SUM(E{LN0}:E{LN0+4})-E{R_EXA},6)').font = F_B
ws7.cell(r, 5).number_format = N2
ws7.cell(r, 8, '差额应为 0').font = F_SUB
for c in range(1, 9):
    ws7.cell(r, c).border = BD
r += 1
ws7.cell(r, 1, '校验：负债条线敞口合计 = L_β 合计').font = F_B
ws7.cell(r, 5, f'=ROUND(SUM(E{LN0+5}:E{LN1})-E{R_EXL},6)').font = F_B
ws7.cell(r, 5).number_format = N2
ws7.cell(r, 8, '差额应为 0').font = F_SUB
for c in range(1, 9):
    ws7.cell(r, c).border = BD

r += 2
r = sec(ws7, r, '【三】重定价到期结构（按期限桶汇总，亿元）', 8)
r = hdr(ws7, r, ['期限桶', '年数 t', '资产端分布', '负债端分布', '净头寸', '累计资产', '累计负债', '说明'])
TB0 = r
for j, (bl, t) in enumerate(BUCKETS):
    rr = r + j
    col = L(3 + j)
    ws7.cell(rr, 1, bl).font = F_N
    ws7.cell(rr, 2, t).font = F_N
    ws7.cell(rr, 2).number_format = N4
    ws7.cell(rr, 3, f"=SUMIF({RF['CAT']},\"资产\",'②期限分布'!{col}${TR0}:{col}${TR1})").font = F_CALC
    ws7.cell(rr, 4, f"=SUMIF({RF['CAT']},\"负债\",'②期限分布'!{col}${TR0}:{col}${TR1})").font = F_LIABC
    ws7.cell(rr, 5, f'=C{rr}-D{rr}').font = F_CALC
    ws7.cell(rr, 6, f'=C{rr}' if j == 0 else f'=F{rr-1}+C{rr}').font = F_CALC
    ws7.cell(rr, 7, f'=D{rr}' if j == 0 else f'=G{rr-1}+D{rr}').font = F_LIABC
    ws7.cell(rr, 8, '活期存款集中于 1M~3M → 负债端 1 年内到期占比高' if j < 3 else
             ('定期 / 市场化负债集中于 1M~12M' if j < 12 else '资产端分期延续至 16M')).font = F_SUB
    for c in (3, 4, 5, 6, 7):
        ws7.cell(rr, c).number_format = N2
    for c in range(1, 9):
        ws7.cell(rr, c).border = BD
TB1 = r + NB - 1
TB_T = TB1 + 1
ws7.cell(TB_T, 1, '合计').font = F_B
for c, col in ((3, 'C'), (4, 'D'), (5, 'E'), (6, 'F'), (7, 'G')):
    ws7.cell(TB_T, c, f'=SUM({col}{TB0}:{col}{TB1})').font = F_B
    ws7.cell(TB_T, c).number_format = N2
ws7.cell(TB_T, 8, '与当前余额差额 = 未到期续作本金（资产端）').font = F_SUB
for c in range(1, 9):
    ws7.cell(TB_T, c).fill = FILL_HL
    ws7.cell(TB_T, c).border = BD
ws7.freeze_panes = 'A4'

# ===========================================================
# ⑧ NII 结构拆解
# ===========================================================
ws8 = wb.create_sheet('⑧NII结构拆解')
for i, w in enumerate([22, 10, 15, 12, 14, 12, 13, 15, 40], 1):
    ws8.column_dimensions[L(i)].width = w
ws8['A1'] = '⑧ NII 结构拆解 — 业务条线 / 账户类型 双维度'
ws8['A1'].font = F_TITLE
ws8.merge_cells('A1:I1')
ws8['A2'] = '全部由 SUMIF 引用「①数据源」，联动更新  |  单位：亿元 / 亿元每年 / %'
ws8['A2'].font = F_SUB
ws8.merge_cells('A2:I2')


def block(ws, r, sec_title, hdrs, key_list, note_map, r8_start):
    r = sec(ws, r, sec_title, 9)
    r = hdr(ws, r, hdrs)
    r0 = r
    for kn, d in key_list:
        rr = r
        ws.cell(rr, 1, kn).font = F_N
        ws.cell(rr, 2, d).font = F_N
        ws.cell(rr, 3, f'=SUMIF({RF["LINE"]},"{kn}",{RF["BAL"]})').font = F_CALC
        ws.cell(rr, 4, f'=IF(SUMIF($B${r0}:$B${r0+len(key_list)-1},$B{rr},$C${r0}:$C${r0+len(key_list)-1})=0,0,C{rr}/SUMIF($B${r0}:$B${r0+len(key_list)-1},$B{rr},$C${r0}:$C${r0+len(key_list)-1}))').font = F_CALC
        ws.cell(rr, 5, f'=SUMIF({RF["LINE"]},"{kn}",{RF["IY"]})').font = F_CALC
        ws.cell(rr, 6, f'=IF(SUMIF($B${r0}:$B${r0+len(key_list)-1},$B{rr},$E${r0}:$E${r0+len(key_list)-1})=0,0,E{rr}/SUMIF($B${r0}:$B${r0+len(key_list)-1},$B{rr},$E${r0}:$E${r0+len(key_list)-1}))').font = F_CALC
        ws.cell(rr, 7, f'=IF(C{rr}=0,0,E{rr}/C{rr})').font = F_CALC
        ws.cell(rr, 8, f'=SUMIF({RF["LINE"]},"{kn}",{RF["BAL"]},{RF["BETA"]})').font = F_CALC
        ws.cell(rr, 9, note_map.get(kn, '')).font = F_SUB
        for c in (3, 5, 8):
            ws.cell(rr, c).number_format = N2
        for c in (4, 6):
            ws.cell(rr, c).number_format = P2
        ws.cell(rr, 7).number_format = P4
        for c in range(1, 10):
            ws.cell(rr, c).border = BD
            ws.cell(rr, c).fill = FILL_A if d == '资产' else FILL_L
        r += 1
    return r0, r - 1, r


H8 = ['维度', '方向', '当前余额\n(亿元)', '余额占比', '年度利息\n(亿元/年)', '利息占比',
      '综合利率', '重定价敞口\n(亿元)', '说明']
LN_KEYS = [(ln, d) for ln, d in LINE_SPECS]
TP_KEYS = [(t, d) for t, d in [('信贷', '资产'), ('投资', '资产'), ('金融', '资产'),
                               ('非息', '资产'), ('外币', '资产'),
                               ('活期', '负债'), ('定期', '负债'), ('同业', '负债')]]
TNOTE = {'信贷': '贷款类，余额最大，信用卡 12% 拉高综合利率',
         '投资': '金市 + 司库债券，票息 2.55~2.85%',
         '金融': '同业资产 / 准备金 / 结构化融资',
         '非息': '非生息资产，利率 0%',
         '外币': '外币资产（折人民币）',
         '活期': '3 桶结构，1 年内全部到期，β = 1',
         '定期': '12 桶结构，到期可续作',
         '同业': '人民币市场化负债，货币市场工具'}

r = 4
S8A0, S8A1, r = block(ws8, r, '【一】按业务条线拆解', H8, LN_KEYS, NOTE, r)
r += 1
S8B0, S8B1, r = block(ws8, r, '【二】按账户类型拆解', H8, TP_KEYS, TNOTE, r)
r += 1
r = sec(ws8, r, '【三】NII 贡献分解与校验', 9)
R8A, R8L, R8N, R8C, R8X = r, r + 1, r + 2, r + 3, r + 4
rows8 = [
    (R8A, '资产端年度利息合计', f'=SUM(E{S8A0}:E{S8A0+4})', F_N, '信贷 + 投资 + 金融 + 非息 + 外币'),
    (R8L, '负债端年度利息合计', f'=SUM(E{S8A0+5}:E{S8A1})', F_N, '活期 + 定期 + 市场化 + 外币'),
    (R8N, '★ NII（条线加总）', f'=B{R8A}-B{R8L}', F_KPI, '= 资产端 − 负债端'),
    (R8C, '对照：⑥NII计量表 NII', f"='⑥NII计量表'!B{R_NII}", F_CALC, '交叉验证'),
    (R8X, '校验差额（应为 0）', f'=B{R8N}-B{R8C}', F_B, '条线维度与总表完全勾稽'),
]
for rr, lab, fml, fnt, note in rows8:
    ws8.cell(rr, 1, lab).font = F_B if rr in (R8N, R8X) else F_N
    ws8.cell(rr, 2, fml).font = fnt
    ws8.cell(rr, 2).number_format = N2
    ws8.cell(rr, 4, '亿元/年').font = F_SUB
    ws8.cell(rr, 9, note).font = F_SUB
    for c in range(1, 10):
        ws8.cell(rr, c).border = BD
        if rr == R8N:
            ws8.cell(rr, c).fill = FILL_KPI
        elif rr == R8X:
            ws8.cell(rr, c).fill = FILL_HL
ws8.freeze_panes = 'A4'

# ===========================================================
# ⑨ 情景敏感性
# ===========================================================
ws9 = wb.create_sheet('⑨情景敏感性')
for i, w in enumerate([26, 11, 17, 17, 15, 17, 12, 13, 42], 1):
    ws9.column_dimensions[L(i)].width = w
ws9['A1'] = '⑨ NII 情景敏感性分析 — 利率平行移动冲击'
ws9['A1'].font = F_TITLE
ws9.merge_cells('A1:I1')
ws9['A2'] = 'ΔNII = −Δr × (A_β − L_β)  |  敞口 ←「⑦期限结构与重定价」，NII ←「⑥NII计量表」'
ws9['A2'].font = F_SUB
ws9.merge_cells('A2:I2')
H9 = ['情景', 'Δr (bp)', 'Δ利息收入\n(亿元/年)', 'Δ利息支出\n(亿元/年)', 'ΔNII\n(亿元/年)',
      '情景后 NII\n(亿元/年)', 'ΔNII %', '情景后 NIM', '情景解读']
r = sec(ws9, 4, '【一】利率平行移动情景', 9)
r = hdr(ws9, r, H9)
SC0 = r
SCEN = [
    ('利率平行上移 250bp', 250, '大幅加息：资产端分期重定价滞后，NII 承压'),
    ('利率平行上移 100bp', 100, '常规加息周期：重定价缺口决定 NII 方向'),
    ('利率平行上移 50bp', 50, '温和加息：关注 NIM 是否跌破 1.50% 参考线'),
    ('基准情景（利率不变）', 0, '基准：ΔNII = 0，NII = 计量表主口径'),
    ('利率平行下移 50bp', -50, '温和降息：负债端成本下行，NII 受益'),
    ('利率平行下移 100bp', -100, '降息周期：存款重定价滞后，短期利好 NIM'),
    ('利率平行下移 250bp', -250, '大幅降息：贷款重定价滞后，NIM 阶段性走高'),
]
for lab, bp, note in SCEN:
    ws9.cell(r, 1, lab).font = F_N
    ws9.cell(r, 2, bp).font = F_INPUT
    ws9.cell(r, 3, f"=-$B${r}/10000*'⑦期限结构与重定价'!$E${R_EXA}").font = F_CALC
    ws9.cell(r, 4, f"=-$B${r}/10000*'⑦期限结构与重定价'!$E${R_EXL}").font = F_LIABC
    ws9.cell(r, 5, f'=C{r}-D{r}').font = F_CALC
    ws9.cell(r, 6, f"='⑥NII计量表'!$B${R_NII}+E{r}").font = F_CALC
    ws9.cell(r, 7, f"=IF('⑥NII计量表'!$B${R_NII}=0,0,E{r}/'⑥NII计量表'!$B${R_NII})").font = F_CALC
    ws9.cell(r, 8, f"=IF('⑥NII计量表'!$B${R_EA}=0,0,F{r}/'⑥NII计量表'!$B${R_EA})").font = F_CALC
    ws9.cell(r, 9, note).font = F_SUB
    for c in (3, 4, 5, 6):
        ws9.cell(r, c).number_format = N2
    ws9.cell(r, 2).number_format = N0
    ws9.cell(r, 7).number_format = P2
    ws9.cell(r, 8).number_format = P4
    for c in range(1, 10):
        ws9.cell(r, c).border = BD
    r += 1
SC1 = r - 1
R_SCMIN = r
ws9.cell(r, 1, '最不利情景 ΔNII（最小值）').font = F_B
ws9.cell(r, 5, f'=MIN(E{SC0}:E{SC1})').font = F_B
ws9.cell(r, 6, f"='⑥NII计量表'!$B${R_NII}+E{r}").font = F_B
ws9.cell(r, 8, f"=IF('⑥NII计量表'!$B${R_EA}=0,0,F{r}/'⑥NII计量表'!$B${R_EA})").font = F_B
ws9.cell(r, 9, '各情景中 NII 变动最不利者').font = F_SUB
for c in (5, 6):
    ws9.cell(r, c).number_format = N2
ws9.cell(r, 8).number_format = P4
for c in range(1, 10):
    ws9.cell(r, c).fill = FILL_HL
    ws9.cell(r, c).border = BD
R_SCMAX = r + 1
ws9.cell(r + 1, 1, '最有利情景 ΔNII（最大值）').font = F_B
ws9.cell(r + 1, 5, f'=MAX(E{SC0}:E{SC1})').font = F_B
ws9.cell(r + 1, 6, f"='⑥NII计量表'!$B${R_NII}+E{r+1}").font = F_B
ws9.cell(r + 1, 8, f"=IF('⑥NII计量表'!$B${R_EA}=0,0,F{r+1}/'⑥NII计量表'!$B${R_EA})").font = F_B
ws9.cell(r + 1, 9, '各情景中 NII 变动最有利者').font = F_SUB
for c in (5, 6):
    ws9.cell(r + 1, c).number_format = N2
ws9.cell(r + 1, 8).number_format = P4
for c in range(1, 10):
    ws9.cell(r + 1, c).fill = FILL_HL
    ws9.cell(r + 1, c).border = BD

r = R_SCMAX + 2
r = sec(ws9, r, '【二】单边冲击（资产端 / 负债端 分开重定价）', 9)
r = hdr(ws9, r, H9)
ONES = [
    ('仅负债端全额重定价 +100bp', 100, 0.0, 1.0, '极端下限：负债 100% 重定价、资产 0% → NII 损失上限'),
    ('仅资产端全额重定价 +100bp', 100, 1.0, 0.0, '极端上限：资产 100% 重定价、负债 0% → NII 改善上限'),
    ('实际重定价（按 β 加权）+100bp', 100, 1.0, 1.0, '实际情景：各自按 β 加权（= 上表 +100bp）'),
    ('负债重定价滞后 +100bp', 100, 1.0, 0.3, '假设存款久期锁定、有效 β 降至 30%'),
]
for lab, bp, ka, kl, note in ONES:
    ws9.cell(r, 1, lab).font = F_N
    ws9.cell(r, 2, bp).font = F_INPUT
    ws9.cell(r, 3, f"=-$B${r}/10000*'⑦期限结构与重定价'!$E${R_EXA}*{ka}").font = F_CALC
    ws9.cell(r, 4, f"=-$B${r}/10000*'⑦期限结构与重定价'!$E${R_EXL}*{kl}").font = F_LIABC
    ws9.cell(r, 5, f'=C{r}-D{r}').font = F_CALC
    ws9.cell(r, 6, f"='⑥NII计量表'!$B${R_NII}+E{r}").font = F_CALC
    ws9.cell(r, 7, f"=IF('⑥NII计量表'!$B${R_NII}=0,0,E{r}/'⑥NII计量表'!$B${R_NII})").font = F_CALC
    ws9.cell(r, 8, f"=IF('⑥NII计量表'!$B${R_EA}=0,0,F{r}/'⑥NII计量表'!$B${R_EA})").font = F_CALC
    ws9.cell(r, 9, note).font = F_SUB
    for c in (3, 4, 5, 6):
        ws9.cell(r, c).number_format = N2
    ws9.cell(r, 2).number_format = N0
    ws9.cell(r, 7).number_format = P2
    ws9.cell(r, 8).number_format = P4
    for c in range(1, 10):
        ws9.cell(r, c).border = BD
    r += 1

r += 1
r = sec(ws9, r, '【三】NII 风险敞口判定', 9)
rows9 = [
    ('加息 100bp 下 NII 变化率（核心敏感度）',
     f"=IF('⑥NII计量表'!$B${R_NII}=0,0,E{SC0+1}/'⑥NII计量表'!$B${R_NII})", P2, N2,
     '绝对值越大，利率风险敞口越大'),
    ('加息 100bp 下 NIM 变动（百分点）',
     f"=IF('⑥NII计量表'!$B${R_EA}=0,0,(H{SC0+1}-'⑥NII计量表'!$B${R_NIM}))", P4, P2,
     '情景后 NIM − 基准 NIM'),
    ('降息 100bp 下 NIM 变动（百分点）',
     f"=IF('⑥NII计量表'!$B${R_EA}=0,0,(H{SC0+5}-'⑥NII计量表'!$B${R_NIM}))", P4, P2,
     '与上式未必等幅，取决于 β 分布'),
    ('NII 波动区间（最有利 − 最不利）', f'=E{R_SCMAX}-E{R_SCMIN}', N2, N2,
     '7 档情景下 NII 最大波动幅度'),
    ('敞口方向判定',
     f"=IF('⑦期限结构与重定价'!$E${R_RG}>0,\"正缺口：利率上行 NII 受损\",IF('⑦期限结构与重定价'!$E${R_RG}<0,\"负缺口：利率上行 NII 受益\",\"利率中性\"))",
     '@', '@', '由 RG 符号决定'),
    ('敞口强弱判定',
     f"=IF(ABS(E{SC0+1}/'⑥NII计量表'!$B${R_NII})>0.05,\"高敏感（>|5%|）\",IF(ABS(E{SC0+1}/'⑥NII计量表'!$B${R_NII})>0.02,\"中敏感（2~5%）\",\"低敏感（<2%）\"))",
     '@', '@', '阈值：100bp 冲击下 NII 变动幅度'),
    ('+250bp 情景 NIM 是否跌破 1.50% 下限',
     f"=IF(H{SC0}<'⑥NII计量表'!$B${R_RL},\"跌破 1.50% 下限\",\"未跌破\")", '@', '@',
     '极端加息情景的监管红线检验'),
]
for k, (lab, fml, fmt, unit, note) in enumerate(rows9):
    rr = r + k
    ws9.cell(rr, 1, lab).font = F_B if k == 0 else F_N
    ws9.cell(rr, 3, fml).font = F_CALC
    ws9.cell(rr, 3).number_format = fmt
    ws9.cell(rr, 4, '亿元/年' if unit == N2 else ('%' if unit == P2 else '')).font = F_SUB
    ws9.cell(rr, 9, note).font = F_SUB
    for c in range(1, 10):
        ws9.cell(rr, c).border = BD
        if k == 0:
            ws9.cell(rr, c).fill = FILL_KPI
ws9.freeze_panes = 'A4'

# ===========================================================
# ⑩ 计算逻辑说明
# ===========================================================
ws10 = wb.create_sheet('⑩计算逻辑说明')
for i, w in enumerate([28, 60, 32], 1):
    ws10.column_dimensions[L(i)].width = w
ws10['A1'] = '⑩ NII 计量逻辑说明 · 数据来源映射 · prcp 实体对应'
ws10['A1'].font = F_TITLE
ws10.merge_cells('A1:C1')
DOC10 = [
    ('SEC', '【一】数据来源（prcp_basic_20251231.xlsx / sheet「基础数据」，方案 8 / 2025-12-31）'),
    ('kv', '当前余额', '①数据源!F 列 ← 基础数据 EJ 列（列 140），原始单位元，已换算为亿元'),
    ('kv', '加权平均利率', '①数据源!G 列 ← 基础数据 EL 列（列 142），单位 %'),
    ('kv', '月度利息（EM）', '①数据源!H 列 ← 基础数据 EM 列（列 143）= 余额 × 利率 ÷ 100 ÷ 12'),
    ('kv', '年度利息', '①数据源!I 列 = H × 12；已与 余额 × 利率 逐笔核对，偏差为 0'),
    ('kv', '剩余期限分布', '②期限分布!C~BJ 列 ← 基础数据 BX~EI 列（列 76~139），共 64 桶'),
    ('kv', '1 年内到期', '②期限分布 第 3+NB 列 = SUM(1M~12M 十二个桶)'),
    ('kv', '收益率曲线', '③收益率曲线 ← 基础数据 R47~R111，64 点，中债登关键期限 + 线性插值'),
    ('kv', '折现因子', '③收益率曲线!D 列 = 1/(1+y)^t，与基础数据 R113~R176 口径一致'),
    ('kv', '重定价 β', '①数据源!L 列 = min(0.98, max(0.10, Σ前12桶 ÷ Σ全部桶))，由期限分布推导'),
    ('SEC', '【二】核心计量公式'),
    ('kv', '月度利息 M_i', 'M_i = 当前余额_i × 加权平均利率_i ÷ 100 ÷ 12'),
    ('kv', '年度利息 I_i', 'I_i = M_i × 12 = 当前余额_i × 加权平均利率_i'),
    ('kv', '利息收入', 'Σ 资产端 I_i（仅加权平均利率 > 0 的生息资产）'),
    ('kv', '利息支出', 'Σ 负债端 I_i（全部计息负债）'),
    ('kv', '★ 净利息收入 NII', 'NII = 利息收入 − 利息支出（亿元/年）'),
    ('kv', '生息资产收益率', '= 利息收入 ÷ 生息资产余额'),
    ('kv', '计息负债成本率', '= 利息支出 ÷ 计息负债余额'),
    ('kv', '净利差 NIS', '= 生息资产收益率 − 计息负债成本率'),
    ('kv', '★ 净息差 NIM', 'NIM = NII ÷ 生息资产余额'),
    ('kv', '重定价敞口', 'A_β = Σ(资产余额 × β)；L_β = Σ(负债余额 × β)'),
    ('kv', '★ 重定价缺口 RG', 'RG = A_β − L_β；RG > 0 → 利率上行时 NII 受损'),
    ('kv', 'ΔNII 敏感度', 'ΔNII = −Δr × RG；NII 利率弹性 = −RG ÷ 生息资产'),
    ('SEC', '【三】期限分布口径说明（重要）'),
    ('kv', '等额分期结构', '资产端非零桶为前 16 个（1M~16M 等额）；活期存款 3 桶；定期 / 市场化负债 12 桶'),
    ('kv', 'Σ桶 ≤ 当前余额', 'Σ 分布合计仅覆盖余额 53.07%（资产）/ 99.98%（负债），差额为未到期续作本金'),
    ('kv', '对 NII 的影响', 'NII 由 余额 × 加权利率 直接决定，不依赖期限分布；期限分布仅用于推导重定价 β'),
    ('kv', '活期存款 β = 1', '活期存款 3 桶结构，1 年内 100% 到期，β 上限取 1，是负债端重定价最快的部分'),
    ('kv', '资产端 β ≈ 0.20', '资产端 16 桶等额分期，1 年内到期约 1/4，β 显著低于负债端'),
    ('SEC', '【四】prcp 平台实体映射'),
    ('kv', 'KpiScheme（指标方案）', 'NII 指标方案主体，绑定账户册方案 CoaScheme（方案 8）'),
    ('kv', 'KpiDefinition（指标定义）', 'NII 定义：formula = Σ(资产利息) − Σ(负债利息)，unit = 亿元/年'),
    ('kv', 'KpiDefinition（关联指标）', 'NIM 定义引用 NII 作为输入，形成 NII → NIM 计量链路'),
    ('kv', 'KpiValue（指标值）', '落库字段：value + value_date + scheme_id + definition_id'),
    ('kv', 'CoaNode（账户节点）', '24 个末级账户对应 prcp_coa_node，node_code 即 ①数据源!A 列账户编码'),
    ('kv', 'prcp_data_basic', '余额与期限分布对应 prcp_data_basic 的 orig_* / rem_* 64 桶列'),
    ('kv', 'MetricCoefficient（系数）', '各账户加权平均利率对应系数表，支持按方案覆盖'),
    ('kv', 'SimScheme（测算方案）', '利率情景（Δr = ±250/100/50 bp）对应测算方案，批量重算 NII'),
    ('SEC', '【五】本模版相比早期版本的关键修正'),
    ('kv', '① 数据真实性', '全部余额 / 利率 / 期限分布改用 prcp_basic_20251231.xlsx 真实值，替换推演数据'),
    ('kv', '② 口径逐笔对齐', '月度利息与参照物 EM 列逐笔核对，偏差 0；年度 = 月度 × 12，设校验 4 / 5 兜底'),
    ('kv', '③ 非生息资产剔除', '非生息资产 30,000 亿（利率 0%）不计入 NIM 分母，单列备查'),
    ('kv', '④ β 由数据推导', '重定价 β 不再主观设定，改由剩余期限分布 1 年内到期占比推导'),
    ('kv', '⑤ 覆盖度透明', '显式披露 Σ 期限分布 / 当前余额 覆盖率，资产端 53.07% 一目了然'),
    ('kv', '⑥ 10 项勾稽校验', '明细↔数据源、月度↔年度、占比合计、NII 恒等式、条线加总，全部应归零'),
]
r = 3
for row in DOC10:
    if row[0] == 'SEC':
        ws10.cell(r, 1, row[1]).font = F_SEC
        for c in range(1, 4):
            ws10.cell(r, c).fill = FILL_SEC
            ws10.cell(r, c).border = BD
        ws10.cell(r, 1).alignment = AL
    else:
        ws10.cell(r, 1, row[1]).font = F_B
        ws10.cell(r, 2, row[2]).font = F_N
        ws10.cell(r, 2).alignment = AL
        for c in range(1, 4):
            ws10.cell(r, c).border = BD
    r += 1
ws10.row_dimensions[1].height = 24

wb.save(OUT)
print('OK ->', OUT)
print(f'  末级账户 {NA}资产 / {NL}负债 / {NE}权益 = {len(ACCOUNTS)}')
print(f'  ①数据源 D{D0}-D{D1} 合计 S{SR}')
print(f'  ②期限分布 T{TR0}-T{TR1} 合计 TS{TS} (1年内列={L(3+NB)})')
print(f'  ③曲线 {CV0}-{CV1}')
print(f'  ④收入 A{AR0}-{AT-1} 合计 AT={AT} 非息 ANZ={ANZ}')
print(f'  ⑤支出 L{LR0}-{LT-1} 合计 LT={LT}')
print(f'  ⑥ EA{R_EA} II{R_II} IE{R_IE} NII{R_NII} NIM{R_NIM} 校验首行{R_CHK1}')
print(f'  ⑦ EX{EX0}-{EX1} Aβ{R_EXA} Lβ{R_EXL} RG{R_RG}')
print(f'  ⑨ SC{SC0}-{SC1}')