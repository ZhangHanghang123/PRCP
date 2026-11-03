# -*- coding: utf-8 -*-
"""
NII 净利息收入计量模版 v3 —— 基于 prcp_basic_20251231.xlsx 真实数据

【相对 v2 的两点改造】
  ① 业务不考虑重定价
     · 删除「重定价β」列、A_β / L_β / 重定价缺口 RG
     · 删除「⑦期限结构与重定价」整张分析表
     · 情景分析改为「利率等幅平移 + 单边冲击 + 结构情景」，不涉及重定价时点与幅度
     · 期限结构分析降级为「静态加权平均剩余期限（WAL/MAL）」，属期限结构披露，非重定价缺口
  ② 数据模拟填充：剩余期限余额合计 = 当前余额
     · 「②期限分布观测」保留参照物原始 64 桶（绿色输入）+ 观测Σ + 覆盖率 + 填充缺口
     · 「③期限分布填充」每桶 = 观测桶 × 填充系数 k，k = 当前余额 ÷ 观测Σ（公式驱动）
     · 填充后 Σ 精确等于当前余额，校验差列逐账户为 0
     · 所有者权益无偿还计划，不纳入期限分布范围（23 个资产/负债账户全覆盖）

【核心口径】
  年度利息 = 当前余额 × 加权平均利率（= 参照物 EM × 12）
  NII      = 利息收入 − 利息支出
  NIM      = NII ÷ 生息资产（供与 NIM 模版勾稽）
  WAL      = Σ(剩余期限桶金额 × 桶年数) ÷ Σ桶金额（静态期限结构）

【单位】亿元 / 亿元每年 / %
"""
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter as L

DOC = 'C:/银行经营/PRCP/docs/v2'
SRC = f'{DOC}/prcp_basic_20251231.xlsx'
OUT = f'{DOC}/NII计量模版_v3_模拟填充.xlsx'

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
                         dist=dist, line=ln, atype=ATYPE[ln], src_row=r))

DIST_ACCOUNTS = [a for a in ACCOUNTS if a['cat'] != 'EQUITY']
NA = sum(1 for a in ACCOUNTS if a['cat'] == 'ASSET')
NL = sum(1 for a in ACCOUNTS if a['cat'] == 'LIAB')
NE = sum(1 for a in ACCOUNTS if a['cat'] == 'EQUITY')
assert NA + NL + NE == 24 and len(DIST_ACCOUNTS) == 23

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
FILL_A = PatternFill('solid', fgColor='DEEBF7')
FILL_L = PatternFill('solid', fgColor='FCE4D6')
FILL_NEA = PatternFill('solid', fgColor='F2F2F2')
FILL_KPI = PatternFill('solid', fgColor='FFD966')
FILL_HL = PatternFill('solid', fgColor='FFF2CC')
FILL_FILL = PatternFill('solid', fgColor='EDE1F5')
FILL_IN = PatternFill('solid', fgColor='E2EFDA')

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
# ① 数据源
# ===========================================================
ws1 = wb.create_sheet('①数据源')
H1 = ['账户编码', '账户名称', '大类', '业务条线', '账户类型',
      '当前余额\n(亿元)', '加权平均\n利率', '月度利息\n(亿元/月)',
      '年度利息\n(亿元/年)', '1年内到期\n(亿元)', '期限分布\n覆盖率', '风险权重', '备注']
W1 = [17, 26, 8, 12, 10, 13, 11, 13, 14, 13, 12, 10, 36]
ws1['A1'] = '① NII 数据源 — 取自 prcp_basic_20251231.xlsx「基础数据」（方案 8 / 2025-12-31）'
ws1['A1'].font = F_TITLE
ws1.merge_cells('A1:M1')
ws1['A2'] = ('🟢 绿区(蓝字) = 可编辑：当前余额、加权平均利率  |  🟣 紫字 = 自动计算  |  '
              '★ 不含重定价β（业务不建模重定价）  |  年度利息 = 余额 × 加权平均利率（= 参照物 EM × 12）  |  '
              '「1年内到期」「期限分布覆盖率」引用「③期限分布填充」')
ws1['A2'].font = F_SUB
ws1.merge_cells('A2:M2')
r = hdr(ws1, 3, H1, W1)
D0 = r
for i, a in enumerate(ACCOUNTS):
    rr = D0 + i
    is_a = a['cat'] == 'ASSET'
    fb = FILL_A if is_a else (FILL_L if a['cat'] == 'LIAB' else FILL_NEA)
    ws1.cell(rr, 1, a['code']).font = F_N
    ws1.cell(rr, 2, a['name']).font = F_N
    ws1.cell(rr, 3, CATMAP[a['cat']]).font = F_N
    ws1.cell(rr, 4, a['line']).font = F_N
    ws1.cell(rr, 5, a['atype']).font = F_N
    ws1.cell(rr, 6, a['bal']).font = F_INPUT
    ws1.cell(rr, 6).number_format = N2
    ws1.cell(rr, 7, a['rate']).font = F_INPUT
    ws1.cell(rr, 7).number_format = P2
    ws1.cell(rr, 8, f'=F{rr}*G{rr}/12').font = F_CALC
    ws1.cell(rr, 8).number_format = N2
    if a['cat'] == 'EQUITY':
        ws1.cell(rr, 10, '不适用').font = F_SUB
        ws1.cell(rr, 11, '不适用').font = F_SUB
    else:
        ws1.cell(rr, 9, f'=H{rr}*12').font = F_CALC
        ws1.cell(rr, 9).number_format = N2
        ws1.cell(rr, 10, f"=SUM('③期限分布填充'!C{4+i}:N{4+i})").font = F_CALC
        ws1.cell(rr, 10).number_format = N2
        ws1.cell(rr, 11, f"=IF(F{rr}=0,0,'③期限分布填充'!BQ{4+i}/F{rr})").font = F_CALC
        ws1.cell(rr, 11).number_format = P2
    ws1.cell(rr, 12, a['rw']).font = F_N
    ws1.cell(rr, 12).number_format = P2
    NOTE = {'信贷资产': '产生利息收入 → 计入生息资产与 NIM 分母',
            '债券投资': '票息收入 → 计入生息资产',
            '金融市场': '同业/准备金/结构化 → 计入生息资产',
            '非生息资产': '利率 0% → 不计入 NIM 分母（计入总资产）',
            '外币资产': '折人民币计价 → 计入生息资产',
            '活期存款': '计息负债 · 剩余期限 3 桶（1M~3M）',
            '定期存款': '计息负债 · 剩余期限 12 桶（1M~12M）',
            '市场化负债': '计息负债 · 剩余期限 12 桶',
            '外币负债': '计息负债 · 折人民币',
            '权益': '无偿还计划，不纳入期限分布范围'}
    ws1.cell(rr, 13, f"基础数据!R{a['src_row']} (EJ/EL/EM) · {NOTE.get(a['line'],'')}").font = F_SUB
    for c in range(1, 14):
        ws1.cell(rr, c).border = BD
        if ws1.cell(rr, c).fill.fgColor.rgb in (None, '00000000'):
            ws1.cell(rr, c).fill = fb
    for c in (6, 7):
        ws1.cell(rr, c).fill = FILL_IN
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
ws1.cell(SR, 13, 'H 列 = 月度利息合计；I 列 = 年度利息合计（权益为 0）').font = F_SUB
for c in range(1, 14):
    ws1.cell(SR, c).fill = FILL_HL
    ws1.cell(SR, c).border = BD
ws1.freeze_panes = f'C{D0}'

RF = {'CODE': f"'①数据源'!$A${D0}:$A${D1}", 'NAME': f"'①数据源'!$B${D0}:$B${D1}",
      'CAT': f"'①数据源'!$C${D0}:$C${D1}", 'LINE': f"'①数据源'!$D${D0}:$D${D1}",
      'TYPE': f"'①数据源'!$E${D0}:$E${D1}", 'BAL': f"'①数据源'!$F${D0}:$F${D1}",
      'RATE': f"'①数据源'!$G${D0}:$G${D1}", 'IM12': f"'①数据源'!$H${D0}:$H${D1}",
      'IY': f"'①数据源'!$I${D0}:$I${D1}",
      'W12': f"'①数据源'!$J${D0}:$J${D1}", 'COV': f"'①数据源'!$K${D0}:$K${D1}"}

# ===========================================================
# ② 期限分布观测
# ===========================================================
ws2 = wb.create_sheet('②期限分布观测')
NC2 = 2 + NB + 4
ws2['A1'] = '② 剩余期限分布 · 观测值（参照物原始数据，绿色输入区）'
ws2['A1'].font = F_TITLE
ws2.merge_cells(f'A1:{L(NC2)}1')
ws2['A2'] = ('直接取自 prcp_basic_20251231.xlsx BX~EI 列（列 76~139）  |  '
             '资产端为 16 桶（1M~12M 等额 + 10Y/15Y/20Y/30Y 长尾），负债端为 3 或 12 桶  |  '
             '观测合计通常 < 当前余额，差额即「模拟填充缺口」，见 BR 列')
ws2['A2'].font = F_SUB
ws2.merge_cells(f'A2:{L(NC2)}2')
T2 = 3
LASTB = L(2 + NB)
ws2.cell(T2, 1, '账户编码').font = F_HEAD
ws2.cell(T2, 2, '账户名称').font = F_HEAD
for i, (bl, t) in enumerate(BUCKETS):
    c = ws2.cell(T2, 3 + i, bl)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
for k, h in enumerate(['观测Σ\n(亿元)', '当前余额\n(亿元)', '观测覆盖率', '填充缺口\n(亿元)'], 3 + NB):
    c = ws2.cell(T2, k, h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
ws2.row_dimensions[T2].height = 40
for i, w in enumerate([17, 26] + [11] * NB + [14, 14, 13, 14], 1):
    ws2.column_dimensions[L(i)].width = w
TR0 = T2 + 1
for i, a in enumerate(DIST_ACCOUNTS):
    rr = TR0 + i
    fb = FILL_A if a['cat'] == 'ASSET' else FILL_L
    ws2.cell(rr, 1, a['code']).font = F_N
    ws2.cell(rr, 2, a['name']).font = F_N
    for j, v in enumerate(a['dist']):
        c = ws2.cell(rr, 3 + j, v if v else None)
        c.font, c.border = F_INPUT, BD
        c.fill = FILL_IN if v else fb
        c.number_format = N0
    ws2.cell(rr, 3 + NB, f'=SUM(C{rr}:{LASTB}{rr})').font = F_CALC
    ws2.cell(rr, 3 + NB).number_format = N2
    ws2.cell(rr, 4 + NB, f"='①数据源'!F{D0+i}").font = F_CALC
    ws2.cell(rr, 4 + NB).number_format = N2
    ws2.cell(rr, 5 + NB, f'=IF({L(4+NB)}{rr}=0,0,{L(3+NB)}{rr}/{L(4+NB)}{rr})').font = F_CALC
    ws2.cell(rr, 5 + NB).number_format = P2
    ws2.cell(rr, 6 + NB, f'={L(4+NB)}{rr}-{L(3+NB)}{rr}').font = F_CALC
    ws2.cell(rr, 6 + NB).number_format = N2
    for c in range(1, 7 + NB):
        ws2.cell(rr, c).border = BD
TR1 = TR0 + len(DIST_ACCOUNTS) - 1
TS = TR1 + 1
ws2.cell(TS, 2, '合计').font = F_B
for k in (3 + NB, 4 + NB, 6 + NB):
    col = L(k)
    ws2.cell(TS, k, f'=SUM({col}{TR0}:{col}{TR1})').font = F_B
    ws2.cell(TS, k).number_format = N2
ws2.cell(TS, 5 + NB, f'=IF({L(4+NB)}{TS}=0,0,{L(3+NB)}{TS}/{L(4+NB)}{TS})').font = F_B
ws2.cell(TS, 5 + NB).number_format = P2
ws2.cell(TS, 6 + NB + 1, '← BR 列为待模拟填充的缺口总额').font = F_SUB
for c in range(1, 7 + NB):
    ws2.cell(TS, c).fill = FILL_HL
    ws2.cell(TS, c).border = BD
ws2.freeze_panes = f'C{TR0}'

# ===========================================================
# ③ 期限分布填充
# ===========================================================
ws3 = wb.create_sheet('③期限分布填充')
ws3['A1'] = '③ 剩余期限分布 · 模拟填充后（Σ 精确等于当前余额）'
ws3['A1'].font = F_TITLE
ws3.merge_cells(f'A1:{L(NC2)}1')
ws3['A2'] = ('填充规则：每桶 = ②观测桶 × 填充系数 k，k = 当前余额 ÷ 观测Σ（等比放大，保持原始期限形态）  |  '
             '紫区 = 模拟填充结果  |  BR 列校验差应全为 0  |  所有者权益无偿还计划，不纳入本表')
ws3['A2'].font = F_SUB
ws3.merge_cells(f'A2:{L(NC2)}2')
ws3.cell(T2, 1, '账户编码').font = F_HEAD
ws3.cell(T2, 2, '账户名称').font = F_HEAD
for i, (bl, t) in enumerate(BUCKETS):
    c = ws3.cell(T2, 3 + i, bl)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
for k, h in enumerate(['填充系数 k', '填充后Σ\n(亿元)', '当前余额\n(亿元)', '校验差\n(应为 0)'], 3 + NB):
    c = ws3.cell(T2, k, h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
ws3.row_dimensions[T2].height = 40
for i, w in enumerate([17, 26] + [11] * NB + [13, 14, 14, 13], 1):
    ws3.column_dimensions[L(i)].width = w
FL0 = T2 + 1
for i, a in enumerate(DIST_ACCOUNTS):
    rr = FL0 + i
    obs = TR0 + i
    ws3.cell(rr, 1, f"='②期限分布观测'!A{obs}").font = F_N
    ws3.cell(rr, 2, f"='②期限分布观测'!B{obs}").font = F_N
    for j in range(NB):
        col = L(3 + j)
        ws3.cell(rr, 3 + j,
                 f"=IF('②期限分布观测'!{col}{obs}=0,0,'②期限分布观测'!{col}{obs}*$BO{rr})").font = F_CALC
        ws3.cell(rr, 3 + j).number_format = N0
    ws3.cell(rr, 3 + NB,
             f"=IF('②期限分布观测'!{L(3+NB)}{obs}=0,0,'②期限分布观测'!{L(4+NB)}{obs}/'②期限分布观测'!{L(3+NB)}{obs})").font = F_CALC
    ws3.cell(rr, 3 + NB).number_format = N4
    ws3.cell(rr, 4 + NB, f'=SUM(C{rr}:{LASTB}{rr})').font = F_CALC
    ws3.cell(rr, 4 + NB).number_format = N2
    ws3.cell(rr, 5 + NB, f"='①数据源'!F{D0+i}").font = F_CALC
    ws3.cell(rr, 5 + NB).number_format = N2
    ws3.cell(rr, 6 + NB, f'={L(4+NB)}{rr}-{L(5+NB)}{rr}').font = F_CALC
    ws3.cell(rr, 6 + NB).number_format = N2
    for c in range(1, 7 + NB):
        ws3.cell(rr, c).border = BD
        ws3.cell(rr, c).fill = FILL_FILL
FL1 = FL0 + len(DIST_ACCOUNTS) - 1
FS = FL1 + 1
ws3.cell(FS, 2, '合计').font = F_B
for k in (3 + NB, 4 + NB, 5 + NB, 6 + NB):
    col = L(k)
    ws3.cell(FS, k, f'=SUM({col}{FL0}:{col}{FL1})').font = F_B
    ws3.cell(FS, k).number_format = N2
ws3.cell(FS, 6 + NB + 1, '← 校验差合计应为 0：Σ 剩余期限余额 = Σ 当前余额').font = F_SUB
for c in range(1, 7 + NB):
    ws3.cell(FS, c).fill = FILL_HL
    ws3.cell(FS, c).border = BD
TROW = FS + 1
ws3.cell(TROW, 2, '年数 t（辅助行）').font = F_SUB
for j, (bl, t) in enumerate(BUCKETS):
    c = ws3.cell(TROW, 3 + j, t)
    c.font, c.border, c.number_format = F_SUB, BD, N4
for c in range(1, 4 + NB):
    ws3.cell(TROW, c).border = BD

# 资产端 / 负债端 各桶金额合计（辅助行，供 WAL / MAL 引用，避免跨表三参数 SUMPRODUCT）
A_SUM_ROW = TROW + 1
L_SUM_ROW = TROW + 2
for tag, rr in (('资产端各桶合计', A_SUM_ROW), ('负债端各桶合计', L_SUM_ROW)):
    ws3.cell(rr, 2, tag + '（辅助行）').font = F_SUB
    for j in range(NB):
        col = L(3 + j)
        ws3.cell(rr, 3 + j,
                 f"=SUMPRODUCT(('①数据源'!$C${D0}:$C${D0+len(DIST_ACCOUNTS)-1}=\"{'资产' if rr == A_SUM_ROW else '负债'}\")"
                 f"*'③期限分布填充'!{col}${FL0}:{col}${FL1})").font = F_CALC
        ws3.cell(rr, 3 + j).number_format = N0
    for c in range(1, 4 + NB):
        ws3.cell(rr, c).border = BD
    ws3.cell(rr, 3 + NB, '← 供 WAL / MAL 计算').font = F_SUB

# 加权年数合计行（各桶金额 × 年数）
T_A_ROW = TROW + 3
T_L_ROW = TROW + 4
for tag, src_row, rr in (('资产端 Σ(金额×年数)', A_SUM_ROW, T_A_ROW),
                         ('负债端 Σ(金额×年数)', L_SUM_ROW, T_L_ROW)):
    ws3.cell(rr, 2, tag).font = F_SUB
    for j in range(NB):
        col = L(3 + j)
        ws3.cell(rr, 3 + j, f"={col}{src_row}*{col}{TROW}").font = F_CALC
        ws3.cell(rr, 3 + j).number_format = N0
    for c in range(1, 4 + NB):
        ws3.cell(rr, c).border = BD
    ws3.cell(rr, 3 + NB, '← 供 WAL / MAL 计算').font = F_SUB
ws3.freeze_panes = f'C{FL0}'

# ===========================================================
# ④ 利率曲线（参考）
# ===========================================================
ws4 = wb.create_sheet('④利率曲线')
ws4['A1'] = '④ 国债收益率曲线与折现因子（参考）— 取自 prcp_basic_20251231.xlsx R47~R176'
ws4['A1'].font = F_TITLE
ws4.merge_cells('A1:G1')
ws4['A2'] = ('64 个关键期限（1M~60M + 10Y/15Y/20Y/30Y）  |  '
              '★ 本模版 NII 计量不直接使用（业务不建模折现/重定价），供与久期、EVE 模版衔接时取用')
ws4['A2'].font = F_SUB
ws4.merge_cells('A2:G2')
r = hdr(ws4, 3, ['期限', '年数 t', '收益率 y(%)', '折现因子 DF', 't × DF', '数据来源', '说明'],
         [12, 11, 13, 15, 13, 15, 34])
CV0 = r
KEY = ('3M', '6M', '9M', '12M', '36M', '60M', '10Y', '30Y')
for i, (ten, t, y) in enumerate(CURVE):
    rr = CV0 + i
    ws4.cell(rr, 1, ten).font = F_N
    ws4.cell(rr, 2, t).font = F_N
    ws4.cell(rr, 2).number_format = N4
    ws4.cell(rr, 3, y).font = F_N
    ws4.cell(rr, 3).number_format = P4
    ws4.cell(rr, 4, f'=1/(1+C{rr})^B{rr}').font = F_CALC
    ws4.cell(rr, 4).number_format = '0.00000000'
    ws4.cell(rr, 5, f'=B{rr}*D{rr}').font = F_CALC
    ws4.cell(rr, 5).number_format = N4
    ws4.cell(rr, 6, '中债登' if ten in KEY else '线性插值').font = F_N
    ws4.cell(rr, 7, '关键期限官方数据' if ten in KEY else '由关键期限线性插值').font = F_SUB
    for c in range(1, 8):
        ws4.cell(rr, c).border = BD
CV1 = CV0 + len(CURVE) - 1
ws4.freeze_panes = f'A{CV0}'

# ===========================================================
# ⑤ 利息收入明细
# ===========================================================
ws5 = wb.create_sheet('⑤利息收入明细')
ws5['A1'] = '⑤ 利息收入明细 — 生息资产逐账户拆解'
ws5['A1'].font = F_TITLE
ws5.merge_cells('A1:L1')
ws5['A2'] = ('年度利息 = 当前余额 × 加权平均利率（= 参照物「平均利息收支」EM × 12）  |  '
              '非生息资产（利率 0%）单列备查，不计入 NIM 分母')
ws5['A2'].font = F_SUB
ws5.merge_cells('A2:L2')
r = hdr(ws5, 3, ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)',
                 '加权平均\n利率', '年度利息\n(亿元/年)', '利息收入\n占比', '累计占比',
                 '1年内到期\n(亿元)', '期限覆盖率', '口径说明'],
         [17, 26, 12, 9, 13, 11, 14, 12, 12, 13, 12, 32])
A_LIST = [a for a in ACCOUNTS if a['cat'] == 'ASSET' and a['rate'] > 0]
A_ZERO = [a for a in ACCOUNTS if a['cat'] == 'ASSET' and a['rate'] == 0]
AR0 = r
AT = AR0 + len(A_LIST)
for k, a in enumerate(A_LIST):
    i = ACCOUNTS.index(a)
    rr = AR0 + k
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'), (7, 'I'), (10, 'J'), (11, 'K')):
        ws5.cell(rr, c, f"='①数据源'!{sc}{D0+i}").font = F_N if c <= 4 else F_CALC
    ws5.cell(rr, 8, f'=IF($G${AT}=0,0,G{rr}/$G${AT})').font = F_CALC
    ws5.cell(rr, 9, f'=H{rr}' if k == 0 else f'=I{rr-1}+H{rr}').font = F_CALC
    ws5.cell(rr, 12, f"基础数据!R{a['src_row']}").font = F_SUB
    for c in (5, 7, 10):
        ws5.cell(rr, c).number_format = N2
    for c in (6, 8, 9, 11):
        ws5.cell(rr, c).number_format = P2
    for c in range(1, 13):
        ws5.cell(rr, c).border = BD
        ws5.cell(rr, c).fill = FILL_A
ws5.cell(AT, 2, '利息收入合计（生息资产）').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (10, 'J')):
    ws5.cell(AT, c, f'=SUM({col}{AR0}:{col}{AT-1})').font = F_B
    ws5.cell(AT, c).number_format = N2
ws5.cell(AT, 6, f'=IF(E{AT}=0,0,G{AT}/E{AT})').font = F_B
ws5.cell(AT, 6).number_format = P4
ws5.cell(AT, 8, f'=SUM(H{AR0}:H{AT-1})').font = F_B
ws5.cell(AT, 8).number_format = P2
ws5.cell(AT, 9, f'=I{AT-1}').font = F_B
ws5.cell(AT, 9).number_format = P2
ws5.cell(AT, 12, 'F 列 = 加权平均收益率 · H 列合计应为 100%').font = F_SUB
for c in range(1, 13):
    ws5.cell(AT, c).fill = FILL_HL
    ws5.cell(AT, c).border = BD
r = AT + 2
r = sec(ws5, r, '【附】非生息资产（利率 = 0，不计入利息收入与 NIM 分母）', 12)
NZ0 = r
for k, a in enumerate(A_ZERO):
    i = ACCOUNTS.index(a)
    rr = NZ0 + k
    ws5.cell(rr, 2, f"='①数据源'!B{D0+i}").font = F_N
    ws5.cell(rr, 5, f"='①数据源'!F{D0+i}").font = F_CALC
    ws5.cell(rr, 6, f"='①数据源'!G{D0+i}").font = F_CALC
    ws5.cell(rr, 7, f"='①数据源'!I{D0+i}").font = F_CALC
    ws5.cell(rr, 12, '利率 0%，无利息收入，已从 NIM 分母剔除').font = F_SUB
    for c in (5, 7):
        ws5.cell(rr, c).number_format = N2
    ws5.cell(rr, 6).number_format = P2
    for c in range(1, 13):
        ws5.cell(rr, c).border = BD
        ws5.cell(rr, c).fill = FILL_A
NZ1 = NZ0 + len(A_ZERO) - 1
ANZ = NZ1 + 1
ws5.cell(ANZ, 2, '非生息资产合计（备查）').font = F_B
for c, col in ((5, 'E'), (7, 'G')):
    ws5.cell(ANZ, c, f'=SUM({col}{NZ0}:{col}{NZ1})').font = F_B
    ws5.cell(ANZ, c).number_format = N2
for c in range(1, 13):
    ws5.cell(ANZ, c).fill = FILL_HL
    ws5.cell(ANZ, c).border = BD
ws5.freeze_panes = f'C{AR0}'

# ===========================================================
# ⑥ 利息支出明细
# ===========================================================
ws6 = wb.create_sheet('⑥利息支出明细')
ws6['A1'] = '⑥ 利息支出明细 — 计息负债逐账户拆解'
ws6['A1'].font = F_TITLE
ws6.merge_cells('A1:L1')
ws6['A2'] = '年度利息 = 当前余额 × 加权平均利率  |  全部计息负债进入 NII 分子（利息支出）'
ws6['A2'].font = F_SUB
ws6.merge_cells('A2:L2')
r = hdr(ws6, 3, ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)',
                 '加权平均\n利率', '年度利息\n(亿元/年)', '利息支出\n占比', '累计占比',
                 '1年内到期\n(亿元)', '期限覆盖率', '结构说明'],
         [17, 26, 12, 9, 13, 11, 14, 12, 12, 13, 12, 34])
L_LIST = [a for a in ACCOUNTS if a['cat'] == 'LIAB']
LR0 = r
LT = LR0 + len(L_LIST)
LNOTE = {'活期存款': '剩余期限 3 桶（1M~3M），1 年内 100% 到期',
         '定期存款': '剩余期限 12 桶（1M~12M），到期续作时重定价',
         '市场化负债': '剩余期限 12 桶，货币市场工具',
         '外币负债': '折人民币，受境内外利差与汇率影响'}
for k, a in enumerate(L_LIST):
    i = ACCOUNTS.index(a)
    rr = LR0 + k
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'), (7, 'I'), (10, 'J'), (11, 'K')):
        ws6.cell(rr, c, f"='①数据源'!{sc}{D0+i}").font = F_N if c <= 4 else F_LIABC
    ws6.cell(rr, 8, f'=IF($G${LT}=0,0,G{rr}/$G${LT})').font = F_LIABC
    ws6.cell(rr, 9, f'=H{rr}' if k == 0 else f'=I{rr-1}+H{rr}').font = F_LIABC
    ws6.cell(rr, 12, LNOTE.get(a['line'], '')).font = F_SUB
    for c in (5, 7, 10):
        ws6.cell(rr, c).number_format = N2
    for c in (6, 8, 9, 11):
        ws6.cell(rr, c).number_format = P2
    for c in range(1, 13):
        ws6.cell(rr, c).border = BD
        ws6.cell(rr, c).fill = FILL_L
ws6.cell(LT, 2, '利息支出合计（计息负债）').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (10, 'J')):
    ws6.cell(LT, c, f'=SUM({col}{LR0}:{col}{LT-1})').font = F_B
    ws6.cell(LT, c).number_format = N2
ws6.cell(LT, 6, f'=IF(E{LT}=0,0,G{LT}/E{LT})').font = F_B
ws6.cell(LT, 6).number_format = P4
ws6.cell(LT, 8, f'=SUM(H{LR0}:H{LT-1})').font = F_B
ws6.cell(LT, 8).number_format = P2
ws6.cell(LT, 9, f'=I{LT-1}').font = F_B
ws6.cell(LT, 9).number_format = P2
ws6.cell(LT, 12, 'F 列 = 加权平均成本率 · H 列合计应为 100%').font = F_SUB
for c in range(1, 13):
    ws6.cell(LT, c).fill = FILL_HL
    ws6.cell(LT, c).border = BD
r = LT + 2
r = sec(ws6, r, '【附】按账户类型分组小计', 12)
GRP = ['活期存款', '定期存款', '市场化负债', '外币负债']
GRP0 = r
for gkey in GRP:
    ws6.cell(r, 2, gkey).font = F_N
    ws6.cell(r, 5, f'=SUMIF({RF["LINE"]},"{gkey}",{RF["BAL"]})').font = F_LIABC
    ws6.cell(r, 6, f'=IF(E{r}=0,0,SUMIF({RF["LINE"]},"{gkey}",{RF["IY"]})/E{r})').font = F_LIABC
    ws6.cell(r, 7, f'=SUMIF({RF["LINE"]},"{gkey}",{RF["IY"]})').font = F_LIABC
    ws6.cell(r, 5).number_format = N2
    ws6.cell(r, 6).number_format = P4
    ws6.cell(r, 7).number_format = N2
    ws6.cell(r, 12, LNOTE.get(gkey, '')).font = F_SUB
    for c in range(1, 13):
        ws6.cell(r, c).border = BD
        ws6.cell(r, c).fill = FILL_L
    r += 1
R_DMR = r
ws6.cell(r, 2, '存款活期化率（活期 ÷ 存款合计）').font = F_B
ws6.cell(r, 5, f'=IF((E{GRP0}+E{GRP0+1})=0,0,E{GRP0}/(E{GRP0}+E{GRP0+1}))').font = F_KPIN
ws6.cell(r, 5).number_format = P2
ws6.cell(r, 12, '活期付息成本最低，活期化率是 NIM 的关键结构变量').font = F_B
for c in range(1, 13):
    ws6.cell(r, c).fill = FILL_KPI
    ws6.cell(r, c).border = BD
ws6.freeze_panes = f'C{LR0}'

# ===========================================================
# ⑦ NII 计量表
# ===========================================================
ws7 = wb.create_sheet('⑦NII计量表')
for i, w in enumerate([42, 17, 14, 12, 50], 1):
    ws7.column_dimensions[L(i)].width = w
ws7['A1'] = '⑦ 净利息收入（NII）计量表 — 基于 prcp_basic_20251231.xlsx 真实数据'
ws7['A1'].font = F_TITLE
ws7.merge_cells('A1:E1')
ws7['A2'] = ('NII = 利息收入 − 利息支出  |  NIM = NII ÷ 生息资产（供与 NIM 模版勾稽）  |  '
             '★ 不含重定价β / 重定价缺口（业务不建模重定价）  |  单位：亿元 / 亿元每年 / %')
ws7['A2'].font = F_SUB
ws7.merge_cells('A2:E2')

r = sec(ws7, 4, '【一】规模：生息资产与计息负债', 5)
R_EA, R_NEA, R_TA, R_EQ, R_TL = r, r + 1, r + 2, r + 3, r + 4
EQ_ROW = D0 + [ACCOUNTS.index(a) for a in ACCOUNTS if a['cat'] == 'EQUITY'][0]
rows1 = [
    (R_EA, '★ 生息资产（利率 > 0，NIM 分母）', f"='⑤利息收入明细'!E{AT}", N2, '剔除非生息资产后的生息资产口径'),
    (R_NEA, '非生息资产（利率 = 0，不计入分母）', f"='⑤利息收入明细'!E{ANZ}", N2, '现金 / 其它非生息资产'),
    (R_TA, '资产端合计（= 参照物总资产）', f"='⑤利息收入明细'!E{AT}+'⑤利息收入明细'!E{ANZ}", N2, '生息 + 非生息'),
    (R_EQ, '所有者权益（不进入分母）', f"='①数据源'!F{EQ_ROW}", N2, '无偿还计划，不纳入期限分布'),
    (R_TL, '计息负债（进入分子，不进入分母）', f"='⑥利息支出明细'!E{LT}", N2, 'NIM = NII ÷ 生息资产，负债只影响分子'),
]
for rr, lab, fml, fmt, note in rows1:
    ws7.cell(rr, 1, lab).font = F_B if rr == R_EA else F_N
    ws7.cell(rr, 2, fml).font = F_KPIN if rr == R_EA else F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 3, f'=IF($B${R_TA}=0,0,B{rr}/$B${R_TA})').font = F_CALC
    ws7.cell(rr, 3).number_format = P2
    ws7.cell(rr, 4, '亿元').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD
        if rr == R_EA:
            ws7.cell(rr, c).fill = FILL_KPI

r = R_TL + 2
r = sec(ws7, r, '【二】分子：利息收入与利息支出', 5)
R_II, R_IE, R_CA, R_CL = r, r + 1, r + 2, r + 3
rows2 = [
    (R_II, '利息收入合计（生息资产）', f"='⑤利息收入明细'!G{AT}", N2, 'Σ 生息资产 余额 × 加权平均利率'),
    (R_IE, '利息支出合计（计息负债）', f"='⑥利息支出明细'!G{LT}", N2, 'Σ 计息负债 余额 × 加权平均利率'),
    (R_CA, '参照物校验：Σ月度利息 × 12（资产）', f'=SUMIF({RF["CAT"]},"资产",{RF["IY"]})*12', N2, '参照物 EM 列口径，应与利息收入相等'),
    (R_CL, '参照物校验：Σ月度利息 × 12（负债）', f'=SUMIF({RF["CAT"]},"负债",{RF["IY"]})*12', N2, '应与利息支出相等'),
]
for rr, lab, fml, fmt, note in rows2:
    ws7.cell(rr, 1, lab).font = F_N
    ws7.cell(rr, 2, fml).font = F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, '亿元/年').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD

r = R_CL + 2
r = sec(ws7, r, '【三】★ 核心指标：NII 与 NIM', 5)
R_NII, R_NIM, R_YLD, R_CST, R_NIS, R_K = r, r + 1, r + 2, r + 3, r + 4, r + 5
rows3 = [
    (R_NII, '★ 净利息收入 NII（= 利息收入 − 利息支出）', f'=B{R_II}-B{R_IE}', F_KPI, N2, '亿元/年', '★ 本模版核心输出指标'),
    (R_NIM, '净息差 NIM（NII ÷ 生息资产）', f'=IF($B${R_EA}=0,0,$B${R_NII}/$B${R_EA})', F_KPIN, P4, '%', '供与 NIM计量模版 勾稽'),
    (R_YLD, '生息资产收益率（利息收入 ÷ 生息资产）', f'=IF($B${R_EA}=0,0,$B${R_II}/$B${R_EA})', F_CALC, P4, '%', '资产端盈利能力'),
    (R_CST, '计息负债成本率（利息支出 ÷ 计息负债）', f'=IF($B${R_TL}=0,0,$B${R_IE}/$B${R_TL})', F_CALC, P4, '%', '负债端付息成本'),
    (R_NIS, '净利差 NIS（净收益率 − 净成本率）', f'=B{R_YLD}-B{R_CST}', F_CALC, P4, '%', '★ NIM = 收益率 − 成本率 × k'),
    (R_K, '负债支持率 k（计息负债 ÷ 生息资产）', f'=IF($B${R_EA}=0,0,$B${R_TL}/$B${R_EA})', F_CALC, P4, '%', '用于 NIM 与 NIS 的关系换算，不涉及重定价'),
]
for rr, lab, fml, fnt, fmt, unit, note in rows3:
    ws7.cell(rr, 1, lab).font = F_B if rr in (R_NII, R_NIM) else F_N
    ws7.cell(rr, 2, fml).font = fnt
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, unit).font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD
        if rr == R_NII:
            ws7.cell(rr, c).fill = FILL_KPI

r = R_K + 2
r = sec(ws7, r, '【四】★ 静态期限结构（披露口径，非重定价分析）', 5)
R_WALA, R_WALL, R_GAP = r, r + 1, r + 2
rows4 = [
    (R_WALA, '资产端加权平均剩余期限 WAL',
     f"=IF(SUM('③期限分布填充'!C{A_SUM_ROW}:{LASTB}{A_SUM_ROW})=0,0,"
     f"SUM('③期限分布填充'!C{T_A_ROW}:{LASTB}{T_A_ROW})/SUM('③期限分布填充'!C{A_SUM_ROW}:{LASTB}{A_SUM_ROW}))", N4, '年',
     '★ Σ(各桶金额 × 桶年数) ÷ Σ桶金额；静态期限结构披露，非重定价缺口'),
    (R_WALL, '负债端加权平均剩余期限 MAL',
     f"=IF(SUM('③期限分布填充'!C{L_SUM_ROW}:{LASTB}{L_SUM_ROW})=0,0,"
     f"SUM('③期限分布填充'!C{T_L_ROW}:{LASTB}{T_L_ROW})/SUM('③期限分布填充'!C{L_SUM_ROW}:{LASTB}{L_SUM_ROW}))", N4, '年', '同上口径，负债端'),
    (R_GAP, '期限结构错配 WAL − MAL', f'=B{R_WALA}-B{R_WALL}', N4, '年',
     '正 = 资产久于负债；仅为期限结构描述，不构成重定价缺口'),
]
for rr, lab, fml, fmt, unit, note in rows4:
    ws7.cell(rr, 1, lab).font = F_B if rr == R_GAP else F_N
    ws7.cell(rr, 2, fml).font = F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, unit).font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD

r = R_GAP + 2
r = sec(ws7, r, '【五】结构比率', 5)
R_S0 = r
rows5 = [
    ('信贷资产 ÷ 生息资产', f'=SUMIF({RF["TYPE"]},"信贷",{RF["BAL"]})/$B${R_EA}', P2, '信贷占比越高，收益率越高'),
    ('存款 ÷ 计息负债', f'=(SUMIF({RF["TYPE"]},"活期",{RF["BAL"]})+SUMIF({RF["TYPE"]},"定期",{RF["BAL"]}))/$B${R_TL}', P2, '存款占比越高，成本越低'),
    ('存款活期化率（活期 ÷ 存款）', f"='⑥利息支出明细'!E{R_DMR}", P2, '活期 0.20% vs 定期 1.85~1.95%'),
    ('市场化负债占比', f'=SUMIF({RF["TYPE"]},"同业",{RF["BAL"]})/$B${R_TL}', P2, '市场化负债成本 2.50%，高于存款'),
    ('1 年内到期 ÷ 生息资产', f'=SUMIF({RF["CAT"]},"资产",{RF["W12"]})/$B${R_EA}', P2, '按模拟填充后期限分布计算'),
    ('1 年内到期 ÷ 计息负债', f'=SUMIF({RF["CAT"]},"负债",{RF["W12"]})/$B${R_TL}', P2, '同上，负债端'),
]
for k, (lab, fml, fmt, note) in enumerate(rows5):
    rr = R_S0 + k
    ws7.cell(rr, 1, lab).font = F_N
    ws7.cell(rr, 2, fml).font = F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, '%').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD

r = R_S0 + len(rows5) + 1
r = sec(ws7, r, '【六】勾稽校验（校验 1~11 应全部为 0）', 5)
rows6 = [
    ('校验 1：⑤明细 = ①Σ年度利息（资产，利率>0）', f"=ROUND('⑤利息收入明细'!G{AT}-SUMIF({RF['CAT']},\"资产\",{RF['IY']}),6)", '明细 ↔ 数据源'),
    ('校验 2：⑥明细 = ①Σ年度利息（负债）', f"=ROUND('⑥利息支出明细'!G{LT}-SUMIF({RF['CAT']},\"负债\",{RF['IY']}),6)", '明细 ↔ 数据源'),
    ('校验 3：①Σ全部年度利息 = 资产 + 负债', f'=ROUND(SUM({RF["IY"]})-SUMIF({RF["CAT"]},"资产",{RF["IY"]})-SUMIF({RF["CAT"]},"负债",{RF["IY"]}),6)', '权益年度利息为 0'),
    ('校验 4：Σ月度利息 × 12 = Σ年度利息（资产）',
     f'=ROUND(SUMIF({RF["CAT"]},"资产",{RF["IM12"]})*12-SUMIF({RF["CAT"]},"资产",{RF["IY"]}),6)', '参照物 EM 口径一致'),
    ('校验 6：Σ月度利息 × 12 = Σ年度利息（负债）',
     f'=ROUND(SUMIF({RF["CAT"]},"负债",{RF["IM12"]})*12-SUMIF({RF["CAT"]},"负债",{RF["IY"]}),6)', '参照物 EM 口径一致'),
    ('校验 6：NII = 利息收入 − 利息支出', f'=ROUND($B${R_NII}-($B${R_II}-$B${R_IE}),8)', 'NII 主口径恒等式'),
    ('校验 7：⑤利息收入占比合计 = 100%', f"=ROUND('⑤利息收入明细'!H{AT}-1,8)", '占比无重复无遗漏'),
    ('校验 8：⑥利息支出占比合计 = 100%', f"=ROUND('⑥利息支出明细'!H{LT}-1,8)", '占比无重复无遗漏'),
    ('校验 9：NIM × 生息资产 = NII（还原分子）', f'=ROUND($B${R_NIM}*$B${R_EA}-$B${R_NII},6)', 'NIM 反算 NII'),
    ('校验 10：NIM 反算 NIS（NIS 应还原）', f'=ROUND(($B${R_NIM}+$B${R_CST}*$B${R_K})-$B${R_YLD},10)', 'NIM = 收益率 − 成本率 × k'),
    ('校验 11：★ 剩余期限分布 Σ桶 = 当前余额（模拟填充后）',
     f"=ROUND('③期限分布填充'!BR{FS},6)", '23 个资产/负债账户全部平准'),
]
for k, (lab, fml, note) in enumerate(rows6):
    rr = r + k
    ws7.cell(rr, 1, lab).font = F_B if k == 10 else F_N
    ws7.cell(rr, 2, fml).font = F_CALC
    ws7.cell(rr, 2).number_format = N2
    ws7.cell(rr, 4, '亿元').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD
        if k == 10:
            ws7.cell(rr, c).fill = FILL_KPI
R_CHK0 = r

r += len(rows6) + 1
r = sec(ws7, r, '【七】监管参考与达标判定', 5)
R_RL, R_RU, R_J1, R_J2 = r, r + 1, r + 2, r + 3
rows7 = [
    (R_RL, '商业银行 NIM 合理区间下限', 0.015, P2, '监管非强制指引参考值', True),
    (R_RU, '商业银行 NIM 合理区间上限', 0.025, P2, '监管非强制指引参考值', True),
    (R_J1, '本行 NIM 达标判定', f'=IF($B${R_NIM}>=$B${R_RL},"达标","不达标")', '@', 'NIM ≥ 1.50%', False),
    (R_J2, '本行 NIM 区间判定', f'=IF(AND($B${R_NIM}>=$B${R_RL},$B${R_NIM}<=$B${R_RU}),"位于合理区间","偏离合理区间")', '@', '1.50% ≤ NIM ≤ 2.50%', False),
]
for rr, lab, val, fmt, note, is_in in rows7:
    ws7.cell(rr, 1, lab).font = F_N
    c = ws7.cell(rr, 2, val)
    c.font = F_INPUT if is_in else F_CALC
    c.number_format = fmt
    ws7.cell(rr, 4, '%' if fmt != '@' else '').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for cc in range(1, 6):
        ws7.cell(rr, cc).border = BD
ws7.freeze_panes = 'A4'

# ===========================================================
# ⑧ NII 结构拆解
# ===========================================================
ws8 = wb.create_sheet('⑧NII结构拆解')
for i, w in enumerate([22, 10, 15, 12, 14, 12, 13, 14, 40], 1):
    ws8.column_dimensions[L(i)].width = w
ws8['A1'] = '⑧ NII 结构拆解 — 业务条线 / 账户类型 / 期限分布 三维'
ws8['A1'].font = F_TITLE
ws8.merge_cells('A1:I1')
ws8['A2'] = '全部由 SUMIF 引用「①数据源」，联动更新  |  期限维度引用「③期限分布填充」  |  单位：亿元 / 亿元每年 / %'
ws8['A2'].font = F_SUB
ws8.merge_cells('A2:I2')

H8 = ['维度', '方向', '当前余额\n(亿元)', '余额占比', '年度利息\n(亿元/年)', '利息占比',
      '综合利率', '1年内到期\n(亿元)', '说明']
LN_KEYS = [('信贷资产', '资产'), ('债券投资', '资产'), ('金融市场', '资产'),
           ('非生息资产', '资产'), ('外币资产', '资产'),
           ('活期存款', '负债'), ('定期存款', '负债'), ('市场化负债', '负债'), ('外币负债', '负债')]
NOTE8 = {'信贷资产': '余额 55 万亿，综合 4.63%，NII 的最大贡献项',
         '债券投资': '余额 25 万亿，综合 2.67%，低收益压低整体收益率',
         '金融市场': '同业 / 准备金 / 结构化融资，综合 2.34%',
         '非生息资产': '利率 0%，拉低「资产端合计口径」收益率',
         '外币资产': '折人民币，综合 3.80%',
         '活期存款': '余额 38 万亿，成本 0.20%，NII 的最大正向贡献',
         '定期存款': '余额 42 万亿，成本 1.88%',
         '市场化负债': '余额 12 万亿，成本 2.50%，成本最高',
         '外币负债': '余额 6 万亿，成本 2.60%'}

r = 4
r = sec(ws8, r, '【一】按业务条线拆解', 9)
r = hdr(ws8, r, H8)
S8A0 = r
for ln, d in LN_KEYS:
    rr = r
    ws8.cell(rr, 1, ln).font = F_N
    ws8.cell(rr, 2, d).font = F_N
    ws8.cell(rr, 3, f'=SUMIF({RF["LINE"]},"{ln}",{RF["BAL"]})').font = F_CALC
    ws8.cell(rr, 4, f'=IF(SUMIF($B${S8A0}:$B${S8A0+8},$B{rr},$C${S8A0}:$C${S8A0+8})=0,0,C{rr}/SUMIF($B${S8A0}:$B${S8A0+8},$B{rr},$C${S8A0}:$C${S8A0+8}))').font = F_CALC
    ws8.cell(rr, 5, f'=SUMIF({RF["LINE"]},"{ln}",{RF["IY"]})').font = F_CALC
    ws8.cell(rr, 6, f'=IF(SUMIF($B${S8A0}:$B${S8A0+8},$B{rr},$E${S8A0}:$E${S8A0+8})=0,0,E{rr}/SUMIF($B${S8A0}:$B${S8A0+8},$B{rr},$E${S8A0}:$E${S8A0+8}))').font = F_CALC
    ws8.cell(rr, 7, f'=IF(C{rr}=0,0,E{rr}/C{rr})').font = F_CALC
    ws8.cell(rr, 8, f'=SUMIF({RF["LINE"]},"{ln}",{RF["W12"]})').font = F_CALC
    ws8.cell(rr, 9, NOTE8.get(ln, '')).font = F_SUB
    for c in (3, 5, 8):
        ws8.cell(rr, c).number_format = N2
    for c in (4, 6):
        ws8.cell(rr, c).number_format = P2
    ws8.cell(rr, 7).number_format = P4
    for c in range(1, 10):
        ws8.cell(rr, c).border = BD
        ws8.cell(rr, c).fill = FILL_A if d == '资产' else FILL_L
    r += 1
S8A1 = r - 1
r += 1
r = sec(ws8, r, '【二】按账户类型拆解', 9)
r = hdr(ws8, r, H8)
TP_KEYS = [('信贷', '资产'), ('投资', '资产'), ('金融', '资产'), ('非息', '资产'),
           ('外币', '资产'), ('活期', '负债'), ('定期', '负债'), ('同业', '负债')]
TNOTE8 = {'信贷': '贷款类，余额最大，信用卡 12% 拉高综合利率',
          '投资': '金市 + 司库债券，票息 2.55~2.85%',
          '金融': '同业资产 / 准备金 / 结构化融资',
          '非息': '非生息资产，利率 0%',
          '外币': '外币资产（折人民币）',
          '活期': '剩余期限 3 桶，1 年内全部到期',
          '定期': '剩余期限 12 桶，到期可续作',
          '同业': '人民币市场化负债，货币市场工具'}
S8B0 = r
for ln, d in TP_KEYS:
    rr = r
    ws8.cell(rr, 1, ln).font = F_N
    ws8.cell(rr, 2, d).font = F_N
    ws8.cell(rr, 3, f'=SUMIF({RF["TYPE"]},"{ln}",{RF["BAL"]})').font = F_CALC
    ws8.cell(rr, 4, f'=IF(SUMIF($B${S8B0}:$B${S8B0+7},$B{rr},$C${S8B0}:$C${S8B0+7})=0,0,C{rr}/SUMIF($B${S8B0}:$B${S8B0+7},$B{rr},$C${S8B0}:$C${S8B0+7}))').font = F_CALC
    ws8.cell(rr, 5, f'=SUMIF({RF["TYPE"]},"{ln}",{RF["IY"]})').font = F_CALC
    ws8.cell(rr, 6, f'=IF(SUMIF($B${S8B0}:$B${S8B0+7},$B{rr},$E${S8B0}:$E${S8B0+7})=0,0,E{rr}/SUMIF($B${S8B0}:$B${S8B0+7},$B{rr},$E${S8B0}:$E${S8B0+7}))').font = F_CALC
    ws8.cell(rr, 7, f'=IF(C{rr}=0,0,E{rr}/C{rr})').font = F_CALC
    ws8.cell(rr, 8, f'=SUMIF({RF["TYPE"]},"{ln}",{RF["W12"]})').font = F_CALC
    ws8.cell(rr, 9, TNOTE8.get(ln, '')).font = F_SUB
    for c in (3, 5, 8):
        ws8.cell(rr, c).number_format = N2
    for c in (4, 6):
        ws8.cell(rr, c).number_format = P2
    ws8.cell(rr, 7).number_format = P4
    for c in range(1, 10):
        ws8.cell(rr, c).border = BD
        ws8.cell(rr, c).fill = FILL_A if d == '资产' else FILL_L
    r += 1
S8B1 = r - 1
r += 1
r = sec(ws8, r, '【三】按剩余期限分布拆解（引用 ③期限分布填充）', 9)
r = hdr(ws8, r, ['期限分段', '方向', '余额\n(亿元)', '该方向占比', '桶数',
                 '—', '—', '—', '说明'])
SEG0 = r
SEGS = [('1M~3M', '3 个月内到期（活期存款集中区）'),
        ('4M~12M', '3~12 个月到期'),
        ('1Y~3Y', '1~3 年到期'),
        ('3Y~5Y', '3~5 年到期'),
        ('5Y 以上', '5 年以上（含 10Y/15Y/20Y/30Y 长尾）')]
SEG_COLS = [(3, 5), (6, 14), (15, 38), (39, 62), (63, 66)]
for d in ('资产', '负债'):
    for (lab, note), (c0, c1) in zip(SEGS, SEG_COLS):
        rr = r
        c0s, c1s = L(c0), L(c1)
        ws8.cell(rr, 1, lab).font = F_N
        ws8.cell(rr, 2, d).font = F_N
        ws8.cell(rr, 3, f"=SUMPRODUCT(('①数据源'!$C${D0}:$C${D1}=\"{d}\")*('③期限分布填充'!{c0s}${FL0}:{c1s}${FL1}))").font = F_CALC
        ws8.cell(rr, 4, f"=IF(SUMPRODUCT(('①数据源'!$C${D0}:$C${D1}=\"{d}\")*1)=0,0,C{rr}/SUMPRODUCT(('①数据源'!$C${D0}:$C${D1}=\"{d}\")*1))").font = F_CALC
        ws8.cell(rr, 5, c1 - c0 + 1).font = F_N
        ws8.cell(rr, 9, note).font = F_SUB
        ws8.cell(rr, 3).number_format = N2
        ws8.cell(rr, 4).number_format = P2
        for c in range(1, 10):
            ws8.cell(rr, c).border = BD
            ws8.cell(rr, c).fill = FILL_A if d == '资产' else FILL_L
        r += 1
SEG1 = r - 1
r += 1
r = sec(ws8, r, '【四】NII 贡献分解与校验', 9)
R8A, R8L, R8N, R8C, R8X = r, r + 1, r + 2, r + 3, r + 4
rows8 = [
    (R8A, '资产端年度利息合计', f'=SUM(E{S8A0}:E{S8A0+4})', F_N, '信贷 + 投资 + 金融 + 非息 + 外币'),
    (R8L, '负债端年度利息合计', f'=SUM(E{S8A0+5}:E{S8A1})', F_N, '活期 + 定期 + 市场化 + 外币'),
    (R8N, '★ NII（条线加总）', f'=B{R8A}-B{R8L}', F_KPI, '= 资产端 − 负债端'),
    (R8C, '对照：⑦NII计量表 NII', f"='⑦NII计量表'!B{R_NII}", F_CALC, '交叉验证'),
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
# ⑨ 情景敏感性（不含重定价）
# ===========================================================
ws9 = wb.create_sheet('⑨情景敏感性')
for i, w in enumerate([26, 12, 17, 17, 15, 17, 13, 13, 42], 1):
    ws9.column_dimensions[L(i)].width = w
ws9['A1'] = '⑨ NII 情景敏感性分析（不含重定价建模）'
ws9['A1'].font = F_TITLE
ws9.merge_cells('A1:I1')
ws9['A2'] = ('★ 假设：所有账户利率等幅平移（不区分重定价时点与幅度，不设 β、不计算重定价缺口）  |  '
             'ΔNII = Δr × (生息资产 − 计息负债)  |  NIM 随之变动')
ws9['A2'].font = F_SUB
ws9.merge_cells('A2:I2')
H9 = ['情景', 'Δr (bp)', 'Δ利息收入\n(亿元/年)', 'Δ利息支出\n(亿元/年)', 'ΔNII\n(亿元/年)',
      '情景后 NII\n(亿元/年)', 'ΔNII %', '情景后 NIM', '情景解读']
r = sec(ws9, 4, '【一】利率等幅平移情景', 9)
r = hdr(ws9, r, H9)
SC0 = r
SCEN = [
    ('利率平行上移 250bp', 250, '极端加息：负债端成本同步上行，NII 下降'),
    ('利率平行上移 100bp', 100, '常规加息周期'),
    ('利率平行上移 50bp', 50, '温和加息'),
    ('基准情景（利率不变）', 0, '基准：ΔNII = 0'),
    ('利率平行下移 50bp', -50, '温和降息：成本端受益更快'),
    ('利率平行下移 100bp', -100, '降息周期：NII 改善'),
    ('利率平行下移 250bp', -250, '大幅降息：NII 显著改善'),
]
for lab, bp, note in SCEN:
    ws9.cell(r, 1, lab).font = F_N
    ws9.cell(r, 2, bp).font = F_INPUT
    ws9.cell(r, 2).fill = FILL_IN
    ws9.cell(r, 3, f"=-$B${r}/10000*'⑦NII计量表'!$B${R_EA}").font = F_CALC
    ws9.cell(r, 4, f"=-$B${r}/10000*'⑦NII计量表'!$B${R_TL}").font = F_LIABC
    ws9.cell(r, 5, f'=C{r}-D{r}').font = F_CALC
    ws9.cell(r, 6, f"='⑦NII计量表'!$B${R_NII}+E{r}").font = F_CALC
    ws9.cell(r, 7, f"=IF('⑦NII计量表'!$B${R_NII}=0,0,E{r}/'⑦NII计量表'!$B${R_NII})").font = F_CALC
    ws9.cell(r, 8, f"=IF('⑦NII计量表'!$B${R_EA}=0,0,F{r}/'⑦NII计量表'!$B${R_EA})").font = F_CALC
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
r += 1
r = sec(ws9, r, '【二】单边冲击（仅资产端 / 仅负债端）', 9)
r = hdr(ws9, r, H9)
ONES = [
    ('仅资产端利率 +100bp', 100, 'A', '极端上限：资产端全额重定价、负债端不变'),
    ('仅负债端利率 +100bp', 100, 'L', '极端下限：负债端全额重定价、资产端不变'),
    ('资产端 +100bp / 负债端 +50bp', 100, 'M', '不对称传导：资产端调整更快时的组合'),
]
for lab, bp, mode, note in ONES:
    ws9.cell(r, 1, lab).font = F_N
    ws9.cell(r, 2, bp).font = F_INPUT
    ws9.cell(r, 2).fill = FILL_IN
    if mode == 'A':
        ws9.cell(r, 3, f"=-$B${r}/10000*'⑦NII计量表'!$B${R_EA}").font = F_CALC
        ws9.cell(r, 4, '=0').font = F_LIABC
    elif mode == 'L':
        ws9.cell(r, 3, '=0').font = F_CALC
        ws9.cell(r, 4, f"=-$B${r}/10000*'⑦NII计量表'!$B${R_TL}").font = F_LIABC
    else:
        ws9.cell(r, 3, f"=-$B${r}/10000*'⑦NII计量表'!$B${R_EA}").font = F_CALC
        ws9.cell(r, 4, f"=-$B${r}/20000*'⑦NII计量表'!$B${R_TL}").font = F_LIABC
    ws9.cell(r, 5, f'=C{r}-D{r}').font = F_CALC
    ws9.cell(r, 6, f"='⑦NII计量表'!$B${R_NII}+E{r}").font = F_CALC
    ws9.cell(r, 7, f"=IF('⑦NII计量表'!$B${R_NII}=0,0,E{r}/'⑦NII计量表'!$B${R_NII})").font = F_CALC
    ws9.cell(r, 8, f"=IF('⑦NII计量表'!$B${R_EA}=0,0,F{r}/'⑦NII计量表'!$B${R_EA})").font = F_CALC
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
r = sec(ws9, r, '【三】结构情景（资产/负债结构调整对 NII 的影响）', 9)
r = hdr(ws9, r, ['结构情景', '调整幅度', 'Δ利息收入\n(亿元/年)', 'Δ利息支出\n(亿元/年)',
                 'ΔNII\n(亿元/年)', '情景后 NII\n(亿元/年)', 'ΔNII %', '情景后 NIM', '情景说明'])
ST0 = r
STRUCT = [
    ('信贷占比 +5pp（债券置换为信贷）', '+5pp',
     f"='⑦NII计量表'!$B${R_EA}*0.05*((SUMIF({RF['TYPE']},\"信贷\",{RF['IY']})/SUMIF({RF['TYPE']},\"信贷\",{RF['BAL']}))-(SUMIF({RF['TYPE']},\"投资\",{RF['IY']})/SUMIF({RF['TYPE']},\"投资\",{RF['BAL']})))",
     '=0', '信贷综合 4.63% vs 债券 2.67%，5pp 置换抬升利息收入'),
    ('活期化率 −10pp（定期转活期）', '−10pp',
     '=0',
     f"=SUMIF({RF['TYPE']},\"定期\",{RF['BAL']})*0.1*((SUMIF({RF['TYPE']},\"定期\",{RF['IY']})/SUMIF({RF['TYPE']},\"定期\",{RF['BAL']}))-(SUMIF({RF['TYPE']},\"活期\",{RF['IY']})/SUMIF({RF['TYPE']},\"活期\",{RF['BAL']})))",
     '定期 1.90% → 活期 0.20%，10% 定期转入活期，付息成本下降'),
    ('非生息资产 50% 转为生息（按 2%）', '−50%',
     f"=('⑦NII计量表'!$B${R_TA}-'⑦NII计量表'!$B${R_EA})*0.5*0.02",
     '=0', '非生息资产的一半转为生息资产，利率 2%'),
]
for lab, amt, dii, die, note in STRUCT:
    rr = r
    ws9.cell(rr, 1, lab).font = F_N
    ws9.cell(rr, 2, amt).font = F_SUB
    ws9.cell(rr, 3, dii).font = F_CALC
    ws9.cell(rr, 4, die).font = F_LIABC
    ws9.cell(rr, 5, f'=C{rr}-D{rr}').font = F_CALC
    ws9.cell(rr, 6, f"='⑦NII计量表'!$B${R_NII}+E{rr}").font = F_CALC
    ws9.cell(rr, 7, f"=IF('⑦NII计量表'!$B${R_NII}=0,0,E{rr}/'⑦NII计量表'!$B${R_NII})").font = F_CALC
    ws9.cell(rr, 8, f"=IF('⑦NII计量表'!$B${R_EA}=0,0,F{rr}/'⑦NII计量表'!$B${R_EA})").font = F_CALC
    ws9.cell(rr, 9, note).font = F_SUB
    for c in (3, 4, 5, 6):
        ws9.cell(rr, c).number_format = N2
    ws9.cell(rr, 7).number_format = P2
    ws9.cell(rr, 8).number_format = P4
    for c in range(1, 10):
        ws9.cell(rr, c).border = BD
    r += 1
ST1 = r - 1
r += 1
r = sec(ws9, r, '【四】NII 风险敞口判定', 9)
rows9 = [
    ('加息 100bp 下 ΔNII（核心敏感度）', f"=E{SC0+1}", N2, '亿元/年', '绝对值越大，利率敏感度越高'),
    ('加息 100bp 下 ΔNII %', f"=G{SC0+1}", P2, '%', '相对 NII 的变动幅度'),
    ('加息 250bp 下 NIM 变动', f"=H{SC0}-'⑦NII计量表'!$B${R_NIM}", BP4, '百分点', '情景后 NIM − 基准 NIM'),
    ('NII 敏感度判定', f'=IF(ABS(G{SC0+1})>0.05,"高敏感（|Δ|>5%）",IF(ABS(G{SC0+1})>0.02,"中敏感（2~5%）","低敏感（<2%）"))', '@', '', '100bp 冲击下 NII 变动幅度'),
    ('加息 250bp 是否跌破 NIM 1.50% 下限', f"=IF(H{SC0}<'⑦NII计量表'!$B${R_RL},\"跌破\",\"未跌破\")", '@', '', '监管红线检验'),
]
for k, (lab, fml, fmt, unit, note) in enumerate(rows9):
    rr = r + k
    ws9.cell(rr, 1, lab).font = F_B if k == 0 else F_N
    ws9.cell(rr, 3, fml).font = F_CALC
    ws9.cell(rr, 3).number_format = fmt
    ws9.cell(rr, 4, unit).font = F_SUB
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
for i, w in enumerate([30, 62, 32], 1):
    ws10.column_dimensions[L(i)].width = w
ws10['A1'] = '⑩ NII 计量逻辑说明 · 数据模拟填充规则 · 与 NIM 模版的分工'
ws10['A1'].font = F_TITLE
ws10.merge_cells('A1:C1')
DOC10 = [
    ('SEC', '【一】★ 相对 v2 的两点改造'),
    ('kv', '① 业务不考虑重定价', '删除重定价β列、A_β/L_β/重定价缺口 RG、「⑦期限结构与重定价」整表；'
                                '情景分析改为利率等幅平移 + 单边冲击 + 结构情景，不设 β、不区分重定价时点与幅度'),
    ('kv', '② 数据模拟填充', '剩余期限分布各桶金额合计 = 当前余额。观测值与填充后分列两表（②观测 / ③填充），'
                            '填充过程为公式驱动，可逐格追溯'),
    ('SEC', '【二】数据来源（prcp_basic_20251231.xlsx /「基础数据」，方案 8 / 2025-12-31）'),
    ('kv', '当前余额', '①数据源!F 列 ← EJ 列（列 140），原始单位元，已换算亿元'),
    ('kv', '加权平均利率', '①数据源!G 列 ← EL 列（列 142），已 /100 存为小数'),
    ('kv', '年度利息', '①数据源!H 列 = F × G，等价于参照物 EM 列 × 12'),
    ('kv', '剩余期限分布', '②期限分布观测!C~BN 列 ← BX~EI 列（列 76~139），64 桶'),
    ('kv', '风险权重', '①数据源!K 列 ← EN 列（列 144）'),
    ('kv', '总资产 / 负债 / 权益', '参照物 R4 / R29 / R43 的 EJ 列：108 万亿 / 98 万亿 / 10 万亿'),
    ('SEC', '【三】★ 剩余期限分布的模拟填充规则'),
    ('kv', '观测值', '②期限分布观测 直接引用参照物原始 64 桶（绿色输入区），不做任何修改'),
    ('kv', '观测合计', 'Σ 观测桶。资产端通常仅覆盖余额的 53.07%（16 桶等额分期 + 4 个长尾），'
                      '负债端活期 100%、定期/市场化 99.98%'),
    ('kv', '填充缺口', '缺口 = 当前余额 − 观测合计（②表 BR 列）'),
    ('kv', '填充系数 k', 'k = 当前余额 ÷ 观测合计（③表 BO 列）。等比放大，保持原始期限形态不变'),
    ('kv', '填充后桶值', '填充后桶值 = 观测桶值 × k（③表逐格公式，可追溯）'),
    ('kv', '填充后合计', 'Σ 填充后桶值 = 当前余额，逐账户校验差为 0（23/23 账户全覆盖）'),
    ('kv', '权益的处理', '所有者权益无偿还计划，不纳入期限分布范围；①数据源 中标注「不适用」'),
    ('kv', '为什么用等比放大', '保持各账户原有的相对期限形态（等额分期节奏 + 长尾分布），'
                              '仅按规模缩放，避免人为改变期限结构特征'),
    ('kv', '对 NII 的影响', 'NII 由「余额 × 加权平均利率」直接决定，与期限分布无关；'
                           '填充仅影响「1年内到期」「期限覆盖率」「WAL/MAL」等期限结构指标'),
    ('SEC', '【四】核心计量公式'),
    ('kv', '年度利息', 'I_i = 当前余额_i × 加权平均利率_i'),
    ('kv', '利息收入', 'Σ 生息资产 I_i（仅加权平均利率 > 0）'),
    ('kv', '利息支出', 'Σ 计息负债 I_i（全部计息负债）'),
    ('kv', '★ 净利息收入 NII', 'NII = 利息收入 − 利息支出（亿元/年）'),
    ('kv', '净息差 NIM', 'NIM = NII ÷ 生息资产余额（供与 NIM计量模版 勾稽）'),
    ('kv', '生息资产收益率', '= 利息收入 ÷ 生息资产余额'),
    ('kv', '计息负债成本率', '= 利息支出 ÷ 计息负债余额'),
    ('kv', '净利差 NIS', '= 生息资产收益率 − 计息负债成本率'),
    ('kv', '负债支持率 k', 'k = 计息负债 ÷ 生息资产；NIM = 收益率 − 成本率 × k（不含重定价）'),
    ('kv', '加权平均剩余期限 WAL', 'WAL = Σ(各桶金额 × 桶年数) ÷ Σ桶金额（静态期限结构披露）'),
    ('kv', '加权平均剩余期限 MAL', '负债端同口径；WAL − MAL = 期限结构错配（描述性指标）'),
    ('SEC', '【五】情景分析口径（不含重定价）'),
    ('kv', '利率等幅平移', '假设所有账户利率同幅变动：Δ利息收入 = −Δr × 生息资产，'
                          'Δ利息支出 = −Δr × 计息负债。不设 β、不区分重定价时点'),
    ('kv', '单边冲击', '仅资产端或仅负债端利率变动，用于界定 NII 变动的上下限'),
    ('kv', '结构情景', '信贷占比、活期化率、非生息资产转生息等结构性调整对 NII 的影响'),
    ('SEC', '【六】prcp 平台实体映射'),
    ('kv', 'KpiScheme（指标方案）', 'NII 指标方案主体，绑定账户册方案 CoaScheme（方案 8）'),
    ('kv', 'KpiDefinition（指标定义）', 'NII 定义：formula = Σ(资产利息) − Σ(负债利息)，unit = 亿元/年'),
    ('kv', 'KpiValue（指标值）', '落库：value + value_date + scheme_id + definition_id'),
    ('kv', 'CoaNode（账户节点）', '24 个末级账户对应 prcp_coa_node，node_code 即 ①!A 列编码'),
    ('kv', 'prcp_data_basic', '余额对应 value 列；期限分布对应 rem_* 64 桶列（本模版按填充口径使用）'),
    ('kv', 'SimScheme（测算方案）', '利率与结构情景对应测算方案，支持批量重算 NII'),
    ('SEC', '【七】与 NIM 计量模版的分工'),
    ('kv', 'NII 模版（本模版）', '回答「赚了多少」—— 分子口径与规模，单位亿元/年；含期限分布模拟填充'),
    ('kv', 'NIM 模版', '回答「每元生息资产赚多少」—— 分母界定与效率，单位%；含多口径 NIM 对比与 NIS 误区澄清'),
    ('kv', '交叉校验', '两者分子完全相同：NII 应相等，NIM 应由本模版的 NII ÷ 生息资产得到'),
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
print(f'  末级账户 {NA}资产 / {NL}负债 / {NE}权益 = {len(ACCOUNTS)}；纳入期限分布 {len(DIST_ACCOUNTS)}')
print(f'  ①数据源 D{D0}-D{D1} 合计 S{SR}')
print(f'  ②观测 T{TR0}-T{TR1} 合计 TS{TS}')
print(f'  ③填充 F{FL0}-F{FL1} 合计 FS{FS} 辅助行 T{TROW}')
print(f'  ⑤收入 A{AR0}-{AT-1} 合计 {AT} 非息 {ANZ}')
print(f'  ⑥支出 L{LR0}-{LT-1} 合计 {LT}')
print(f'  ⑦ EA{R_EA} NEA{R_NEA} TA{R_TA} TL{R_TL} II{R_II} IE{R_IE} NII{R_NII} NIM{R_NIM}')
print(f'     WAL{R_WALA} MAL{R_WALL} GAP{R_GAP} 校验首行{R_CHK0}')
print(f'  ⑧ 条线 {S8A0}-{S8A1} 类型 {S8B0}-{S8B1} NII{R8N}')
print(f'  ⑨ SC{SC0}-{SC1} 结构 {ST0}-{ST1}')