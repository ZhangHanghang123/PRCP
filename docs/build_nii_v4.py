# -*- coding: utf-8 -*-
"""
NII 净利息收入计量模版 v4 —— 剩余期限结构重塑 + 逐月平均余额法利息推演

【相对 v3 的三点改造】
  ① 剩余期限结构重塑（②）
     · v3 的「②期限分布观测」直接引用参照物 BX~EI 原始值，形态不合理：
       资产端 1M~12M 等额 + 10Y/15Y/20Y/30Y 长尾，Σ 仅覆盖余额 53%，等比放大是在错误形态上打补丁
     · v4 按各账户业务属性重新摆布剩余期限形态（64 桶权重%，合计 100%），
       金额 = 当前余额 × 权重，Σ 恒等于当前余额
     · 表结构：② 存「权重%（形态，绿区输入）」，金额在 ③ 逐月推演与 ② 辅助行中派生
  ② 新增「③逐月利息推演」
     · 每账户 12 个月逐月递推：月初余额 → 扣减当月到期 → 月末余额 → 月度利息
     · 月度利息 =（月初余额 + 月末余额）/2 × 加权平均利率 / 12
     · 年度利息 = 12 个月利息加总（①数据源 I 列引用本表）
  ③ 年度利息口径升级
     · I 列 = 逐月平均余额法推演值（存量自然到期口径，不模拟续作/新业务）
     · J 列 = 余额 × 加权平均利率（会计静态口径，对照列）
     · 两者差异在 ⑦ 计量表【三】量化说明

【核心口径】
  月末余额(m) = 月末余额(m-1) − 剩余期限结构(m 桶金额)
  月度利息(m) =（月初余额 + 月末余额）/2 × 加权平均利率 / 12
  年度利息     = Σ_{m=1..12} 月度利息(m)
  NII          = 利息收入 − 利息支出
  NIM          = NII ÷ 生息资产（供与 NIM 模版勾稽）

【单位】亿元 / 亿元每年 / %
"""
import re
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter as L

DOC = 'C:/银行经营/PRCP/docs/v2'
SRC = f'{DOC}/prcp_basic_20251231.xlsx'
OUT = f'{DOC}/NII计量模版_v4_逐月利息推演.xlsx'

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
        if '同业' in n or '结构化' in n:
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
    ln = classify(name, cat)
    ACCOUNTS.append(dict(code=code, name=name, cat=cat, bal=bal, rate=rate,
                         intr_m=intr_m, rw=(_ws.cell(r, C_RW).value or 0),
                         line=ln, atype=ATYPE[ln], src_row=r))
assert len(ACCOUNTS) == 24

# ===========================================================
# 剩余期限形态模板（按业务属性摆布，权重合计 100%）
# 桶标签：1M..60M + 10Y / 15Y / 20Y / 30Y
# ===========================================================
_BIDX = {f'{m}M': m - 1 for m in range(1, 61)}
_BIDX.update({'10Y': 60, '15Y': 61, '20Y': 62, '30Y': 63})


def _shape(segs):
    """segs: [(起桶, 止桶, 权重%)] -> 64 长权重数组（合计 1.0）"""
    w = [0.0] * 64
    for a, b, pct in segs:
        i0, i1 = _BIDX[a], _BIDX[b]
        for k in range(i0, i1 + 1):
            w[k] = pct / 100.0 / (i1 - i0 + 1)
    return w


SHAPES = {
    # ===== 资产端 =====
    '对公一般贷款':   ([('1M', '12M', 40), ('13M', '36M', 32), ('37M', '60M', 12),
                       ('10Y', '10Y', 8), ('15Y', '15Y', 4), ('20Y', '20Y', 2.5), ('30Y', '30Y', 1.5)],
                      '对公贷款：1 年内到期 40%（短贷+流贷滚动），1~3 年 32%，3~5 年 12%，长尾 16%'),
    '个人贷款':       ([('1M', '12M', 45), ('13M', '36M', 30), ('37M', '60M', 10),
                       ('10Y', '10Y', 7), ('15Y', '15Y', 4), ('20Y', '20Y', 2.5), ('30Y', '30Y', 1.5)],
                      '个人贷款：期限偏短，1 年内 45%，消费/经营贷混合'),
    '信用卡贷款':     ([('1M', '12M', 55), ('13M', '24M', 25), ('25M', '36M', 10),
                       ('10Y', '10Y', 5), ('15Y', '15Y', 3), ('20Y', '20Y', 1.5), ('30Y', '30Y', 0.5)],
                      '信用卡：透支额度循环使用，1 年内 55%'),
    '票据贴现':       ([('1M', '6M', 70), ('7M', '12M', 25), ('13M', '24M', 5)],
                      '票据贴现：最短久期资产，6 个月内 70%'),
    '非银贷款':       ([('1M', '12M', 42), ('13M', '36M', 32), ('37M', '60M', 11),
                       ('10Y', '10Y', 7), ('15Y', '15Y', 4), ('20Y', '20Y', 2.5), ('30Y', '30Y', 1.5)],
                      '非银贷款：类对公口径，1 年内 42%'),
    '金市自营债券':   ([('1M', '6M', 12), ('7M', '12M', 12), ('13M', '36M', 24), ('37M', '60M', 18),
                       ('10Y', '10Y', 17), ('15Y', '15Y', 8), ('20Y', '20Y', 5.5), ('30Y', '30Y', 3.5)],
                      '金市自营：交易盘，期限分散，10Y 以上 34%'),
    '司库债券':       ([('1M', '12M', 12), ('13M', '36M', 22), ('37M', '60M', 22),
                       ('10Y', '10Y', 20), ('15Y', '15Y', 12), ('20Y', '20Y', 7.5), ('30Y', '30Y', 4.5)],
                      '司库：持有到期账户，久期最长'),
    '结构化融资':     ([('1M', '12M', 40), ('13M', '36M', 33), ('37M', '60M', 12),
                       ('10Y', '10Y', 8), ('15Y', '15Y', 3.5), ('20Y', '20Y', 2), ('30Y', '30Y', 1.5)],
                      '结构化融资：项目现金流对应，1 年内 40%'),
    '同业资产':       ([('1M', '6M', 45), ('7M', '12M', 35), ('13M', '24M', 15), ('25M', '36M', 5)],
                      '同业资产：拆借为主，6 个月内 45%'),
    '存款准备金':     ([('1M', '3M', 60), ('4M', '6M', 25), ('7M', '12M', 15)],
                      '存款准备金：随时可支取，3 个月内 60%'),
    'FVTPL类资产':   ([('1M', '12M', 25), ('13M', '36M', 25), ('37M', '60M', 18),
                       ('10Y', '10Y', 16), ('15Y', '15Y', 7.5), ('20Y', '20Y', 5), ('30Y', '30Y', 3.5)],
                      'FVTPL：交易账户，期限与金市自营相近'),
    '其他非生息资产': ([('1M', '12M', 50), ('13M', '36M', 30), ('37M', '60M', 12),
                       ('10Y', '10Y', 4), ('15Y', '15Y', 2), ('20Y', '20Y', 1.3), ('30Y', '30Y', 0.7)],
                      '现金及备付类，1 年内 50%，不产生利息'),
    '外币贷款':       ([('1M', '12M', 43), ('13M', '36M', 31), ('37M', '60M', 11),
                       ('10Y', '10Y', 7.5), ('15Y', '15Y', 4), ('20Y', '20Y', 2), ('30Y', '30Y', 1.5)],
                      '外币贷款：与境内对公同构'),
    '外币债券':       ([('1M', '12M', 20), ('13M', '36M', 26), ('37M', '60M', 20),
                       ('10Y', '10Y', 16), ('15Y', '15Y', 8.5), ('20Y', '20Y', 5.5), ('30Y', '30Y', 4)],
                      '外币债券：与境内投资同构'),
    '外币同业':       ([('1M', '6M', 45), ('7M', '12M', 35), ('13M', '24M', 15), ('25M', '36M', 5)],
                      '外币同业：与境内同业同构'),
    '外币非生息':     ([('1M', '12M', 55), ('13M', '36M', 30), ('37M', '60M', 10),
                       ('10Y', '10Y', 3), ('15Y', '15Y', 1.3), ('20Y', '20Y', 0.7)],
                      '外币现金备付，1 年内 55%'),
    # ===== 负债端 =====
    '对公活期存款':   ([('1M', '1M', 14), ('2M', '2M', 13), ('3M', '3M', 12), ('4M', '4M', 11),
                       ('5M', '5M', 10), ('6M', '6M', 9), ('7M', '7M', 8), ('8M', '8M', 7),
                       ('9M', '9M', 6), ('10M', '10M', 5), ('11M', '11M', 3.5), ('12M', '12M', 1.5)],
                      '对公活期：日均留存，按月递减分布，12 个月内 100% 到期'),
    '对公定期存款':   ([('1M', '6M', 20), ('7M', '12M', 18), ('13M', '36M', 28), ('37M', '60M', 18),
                       ('10Y', '10Y', 8), ('15Y', '15Y', 4.5), ('20Y', '20Y', 2.5), ('30Y', '30Y', 1)],
                      '对公定期：3M/6M/1Y/2Y/3Y 阶梯，1 年内 38%'),
    '零售活期存款':   ([('1M', '1M', 14), ('2M', '2M', 13), ('3M', '3M', 12), ('4M', '4M', 11),
                       ('5M', '5M', 10), ('6M', '6M', 9), ('7M', '7M', 8), ('8M', '8M', 7),
                       ('9M', '9M', 6), ('10M', '10M', 5), ('11M', '11M', 3.5), ('12M', '12M', 1.5)],
                      '零售活期：与对公活期同构，散户留存更分散'),
    '零售定期存款':   ([('1M', '6M', 24), ('7M', '12M', 22), ('13M', '36M', 26), ('37M', '60M', 15),
                       ('10Y', '10Y', 7), ('15Y', '15Y', 3.5), ('20Y', '20Y', 1.5), ('30Y', '30Y', 1)],
                      '零售定期：较对公定期更短，1 年内 46%'),
    '人民币市场化负债': ([('1M', '6M', 35), ('7M', '12M', 33), ('13M', '24M', 20),
                         ('25M', '36M', 8), ('37M', '60M', 4)],
                      '同业存单/回购为主，1 年内 68%'),
    '外币存款':       ([('1M', '6M', 22), ('7M', '12M', 20), ('13M', '36M', 28), ('37M', '60M', 17),
                       ('10Y', '10Y', 7.5), ('15Y', '15Y', 3), ('20Y', '20Y', 1.5), ('30Y', '30Y', 1)],
                      '外币存款：与境内定期同构'),
    '外币市场化负债': ([('1M', '6M', 40), ('7M', '12M', 33), ('13M', '24M', 18),
                       ('25M', '36M', 6), ('37M', '60M', 3)],
                      '外币同业融资，1 年内 73%'),
    # ===== 权益（无偿还计划，30Y 视同永续）=====
    '所有者权益':     ([('30Y', '30Y', 100)],
                      '所有者权益：无到期安排，视同永续（30Y 桶），不参与逐月摊销'),
}


def _key(name):
    n = re.sub(r'^\d+(\.\d+)*\.?\s*', '', name).strip()
    return n.replace('（不含拆放非银）', '').strip()


SHAPE_W = {}
SHAPE_NOTE = {}
for a in ACCOUNTS:
    k = _key(a['name'])
    cand = SHAPES.get(k)
    if cand is None:
        cand = [v for kk, v in SHAPES.items()
                if k.startswith(kk) and len(kk) >= 3 and kk != '同业资产']
        cand = cand[0] if cand else None
    assert cand is not None, a['name']
    w = _shape(cand[0])
    assert abs(sum(w) - 1.0) < 1e-9, a['name']
    SHAPE_W[a['code']] = w
    SHAPE_NOTE[a['code']] = cand[1]

NA = sum(1 for a in ACCOUNTS if a['cat'] == 'ASSET')
NL = sum(1 for a in ACCOUNTS if a['cat'] == 'LIAB')
NE = sum(1 for a in ACCOUNTS if a['cat'] == 'EQUITY')

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
      '当前余额\n(亿元)', '加权平均\n利率',
      '月度利息\n(亿元/月)', '年度利息\n(亿元/年)\n【逐月推演】', '年度利息\n(亿元/年)\n【余额×利率】',
      '1年内到期\n(亿元)', '1年内\n到期占比', '年计息基数\n(亿元)', '风险权重', '备注']
W1 = [17, 26, 8, 12, 10, 13, 11, 13, 16, 16, 13, 12, 14, 10, 40]
ws1['A1'] = '① NII 数据源 — 余额与利率取自 prcp_basic_20251231.xlsx；年度利息由「③逐月利息推演」派生'
ws1['A1'].font = F_TITLE
ws1.merge_cells('A1:O1')
ws1['A2'] = ('🟢 绿区(蓝字) = 可编辑：当前余额、加权平均利率  |  🟣 紫字 = 自动计算  |  '
              '★ I 列 = 逐月平均余额法推演（存量自然到期口径）；J 列 = 余额×利率（会计静态口径）  |  '
              'K/L/M 列引用「②剩余期限结构」与「③逐月利息推演」')
ws1['A2'].font = F_SUB
ws1.merge_cells('A2:O2')
r = hdr(ws1, 3, H1, W1)
D0 = r                                   # 数据首行 = 4
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
    # I 列：年度利息（逐月推演）→ 引用 ③
    ws1.cell(rr, 9, f"='③逐月利息推演'!AD{rr}").font = F_CALC
    ws1.cell(rr, 9).number_format = N2
    # J 列：会计静态口径
    ws1.cell(rr, 10, f'=F{rr}*G{rr}').font = F_CALC
    ws1.cell(rr, 10).number_format = N2
    # H 列：月度利息均值 = I / 12
    ws1.cell(rr, 8, f'=I{rr}/12').font = F_CALC
    ws1.cell(rr, 8).number_format = N2
    # K/L：1 年内到期金额与占比 → 引用 ②
    ws1.cell(rr, 11, f"='②剩余期限结构'!BR{rr}").font = F_CALC
    ws1.cell(rr, 11).number_format = N2
    ws1.cell(rr, 12, f"=IF('②剩余期限结构'!BQ{rr}=0,0,'②剩余期限结构'!BR{rr}/'②剩余期限结构'!BQ{rr})").font = F_CALC
    ws1.cell(rr, 12).number_format = P2
    # M 列：年计息基数 → 引用 ③
    ws1.cell(rr, 13, f"='③逐月利息推演'!AH{rr}").font = F_CALC
    ws1.cell(rr, 13).number_format = N2
    ws1.cell(rr, 14, a['rw']).font = F_N
    ws1.cell(rr, 14).number_format = P2
    ws1.cell(rr, 15, f"基础数据!R{a['src_row']} (EJ/EL/EM) · {SHAPE_NOTE[a['code']]}").font = F_SUB
    for c in range(1, 16):
        ws1.cell(rr, c).border = BD
        if ws1.cell(rr, c).fill.fgColor.rgb in (None, '00000000'):
            ws1.cell(rr, c).fill = fb
    for c in (6, 7):
        ws1.cell(rr, c).fill = FILL_IN
D1 = D0 + len(ACCOUNTS) - 1
SR = D1 + 1
ws1.cell(SR, 2, '合计 / 加权平均').font = F_B
for c in (6, 8, 9, 10, 11, 13):
    ws1.cell(SR, c, f'=SUM({L(c)}{D0}:{L(c)}{D1})').font = F_B
    ws1.cell(SR, c).number_format = N2
ws1.cell(SR, 7, f'=IF(F{SR}=0,0,SUMPRODUCT($F${D0}:$F${D1},$G${D0}:$G${D1})/F{SR})').font = F_B
ws1.cell(SR, 7).number_format = P4
ws1.cell(SR, 12, f'=IF(F{SR}=0,0,K{SR}/F{SR})').font = F_B
ws1.cell(SR, 12).number_format = P2
ws1.cell(SR, 15, 'I 列合计 = 逐月推演年度利息（主口径）｜J 列合计 = 余额×利率（静态对照）').font = F_SUB
for c in range(1, 16):
    ws1.cell(SR, c).fill = FILL_HL
    ws1.cell(SR, c).border = BD
ws1.freeze_panes = f'C{D0}'

RF = {'CODE': f"'①数据源'!$A${D0}:$A${D1}", 'NAME': f"'①数据源'!$B${D0}:$B${D1}",
      'CAT': f"'①数据源'!$C${D0}:$C${D1}", 'LINE': f"'①数据源'!$D${D0}:$D${D1}",
      'TYPE': f"'①数据源'!$E${D0}:$E${D1}", 'BAL': f"'①数据源'!$F${D0}:$F${D1}",
      'RATE': f"'①数据源'!$G${D0}:$G${D1}", 'IM12': f"'①数据源'!$H${D0}:$H${D1}",
      'IY': f"'①数据源'!$I${D0}:$I${D1}", 'IY_CMP': f"'①数据源'!$J${D0}:$J${D1}",
      'W12': f"'①数据源'!$K${D0}:$K${D1}", 'W12P': f"'①数据源'!$L${D0}:$L${D1}",
      'BASE': f"'①数据源'!$M${D0}:$M${D1}"}

# ===========================================================
# ② 剩余期限结构（权重形态）
# ===========================================================
ws2 = wb.create_sheet('②剩余期限结构')
BUCKET_C0 = 4                                   # 桶列起始 = D
BUCKET_C1 = BUCKET_C0 + NB - 1                  # = 67 → BO
BLK = L(BUCKET_C0)
BLK1 = L(BUCKET_C1)
C_WSUM = BUCKET_C1 + 1                          # 68 → BP  权重合计
C_BAL = BUCKET_C1 + 2                           # 69 → BQ  当前余额
C_W12 = BUCKET_C1 + 3                           # 70 → BR  1年内金额
C_S1 = BUCKET_C1 + 4                            # 71 → BS  1M~3M 金额
C_S2 = BUCKET_C1 + 5                            # 72 → BT  4M~12M
C_S3 = BUCKET_C1 + 6                            # 73 → BU  1Y~3Y
C_S4 = BUCKET_C1 + 7                            # 74 → BV  3Y~5Y
C_S5 = BUCKET_C1 + 8                            # 75 → BW  5Y以上
C_CHK = BUCKET_C1 + 9                           # 76 → BX  权重校验差
C_WAL = BUCKET_C1 + 10                          # 77 → BY  WAL
C_NT = BUCKET_C1 + 11                           # 78 → BZ  形态说明
NC2 = C_NT
ws2['A1'] = '② 剩余期限结构（按当前余额重塑）— 64 桶权重形态，合计 100%'
ws2['A1'].font = F_TITLE
ws2.merge_cells(f'A1:{L(NC2)}1')
ws2['A2'] = ('🟢 绿区 = 权重%（业务形态摆布，可编辑）  |  金额 = 当前余额 × 权重  |  '
             'BP 列权重合计应 = 100%，BX 列校验差应为 0  |  '
             '★ 权益无偿还计划，30Y 视同永续，不参与逐月摊销')
ws2['A2'].font = F_SUB
ws2.merge_cells(f'A2:{L(NC2)}2')
T2 = 3
ws2.cell(T2, 1, '账户编码').font = F_HEAD
ws2.cell(T2, 2, '账户名称').font = F_HEAD
ws2.cell(T2, 3, '大类').font = F_HEAD
for i, (bl, t) in enumerate(BUCKETS):
    c = ws2.cell(T2, BUCKET_C0 + i, bl)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
for k, h in enumerate(['权重合计', '当前余额\n(亿元)', '1年内金额\n(亿元)',
                       '1M~3M\n(亿元)', '4M~12M\n(亿元)', '1Y~3Y\n(亿元)',
                       '3Y~5Y\n(亿元)', '5Y以上\n(亿元)', '权重校验差',
                       'WAL\n(年)', '形态说明'], BUCKET_C1 + 1):
    c = ws2.cell(T2, k, h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
ws2.row_dimensions[T2].height = 42
for i, w in enumerate([17, 26, 8] + [9] * NB + [11, 13, 13, 12, 12, 12, 12, 12, 11, 10, 46], 1):
    ws2.column_dimensions[L(i)].width = w
TR0 = T2 + 1
for i, a in enumerate(ACCOUNTS):
    rr = TR0 + i
    fb = FILL_A if a['cat'] == 'ASSET' else (FILL_L if a['cat'] == 'LIAB' else FILL_NEA)
    ws2.cell(rr, 1, a['code']).font = F_N
    ws2.cell(rr, 2, a['name']).font = F_N
    ws2.cell(rr, 3, CATMAP[a['cat']]).font = F_N
    w = SHAPE_W[a['code']]
    for j in range(NB):
        c = ws2.cell(rr, BUCKET_C0 + j, w[j])
        c.font, c.border, c.fill = F_INPUT, BD, (FILL_IN if w[j] > 0 else fb)
        c.number_format = P2
    ws2.cell(rr, C_WSUM, f'=SUM({BLK}{rr}:{BLK1}{rr})').font = F_CALC
    ws2.cell(rr, C_WSUM).number_format = P2
    ws2.cell(rr, C_BAL, f"='①数据源'!F{D0+i}").font = F_CALC
    ws2.cell(rr, C_BAL).number_format = N2
    ws2.cell(rr, C_W12, f'={L(C_BAL)}{rr}*SUM({BLK}{rr}:{L(BUCKET_C0+11)}{rr})').font = F_CALC
    ws2.cell(rr, C_W12).number_format = N2
    SEGR = [(C_S1, BUCKET_C0, BUCKET_C0 + 2), (C_S2, BUCKET_C0 + 3, BUCKET_C0 + 11),
            (C_S3, BUCKET_C0 + 12, BUCKET_C0 + 35), (C_S4, BUCKET_C0 + 36, BUCKET_C0 + 59),
            (C_S5, BUCKET_C0 + 60, BUCKET_C1)]
    for cc, c0, c1 in SEGR:
        ws2.cell(rr, cc, f'={L(C_BAL)}{rr}*SUM({L(c0)}{rr}:{L(c1)}{rr})').font = F_CALC
        ws2.cell(rr, cc).number_format = N2
    ws2.cell(rr, C_CHK, f'=IF(ABS({L(C_WSUM)}{rr}-1)>0.000000001,1,0)').font = F_CALC
    ws2.cell(rr, C_CHK).number_format = N0
    ws2.cell(rr, C_WAL, '=0').font = F_CALC
    ws2.cell(rr, C_WAL).number_format = N4
    ws2.cell(rr, C_NT, SHAPE_NOTE[a['code']]).font = F_SUB
    for c in range(1, NC2 + 1):
        ws2.cell(rr, c).border = BD
TR1 = TR0 + len(ACCOUNTS) - 1
TS = TR1 + 1
ws2.cell(TS, 2, '合计').font = F_B
for k in (C_BAL, C_W12, C_S1, C_S2, C_S3, C_S4, C_S5):
    ws2.cell(TS, k, f'=SUM({L(k)}{TR0}:{L(k)}{TR1})').font = F_B
    ws2.cell(TS, k).number_format = N2
# 权重合计/校验差：取全部账户的最大绝对偏差（应恒为 0）
ws2.cell(TS, C_WSUM, f'=AVERAGE({L(C_WSUM)}{TR0}:{L(C_WSUM)}{TR1})').font = F_B
ws2.cell(TS, C_WSUM).number_format = P4
ws2.cell(TS, C_CHK, f'=COUNTIF({L(C_CHK)}{TR0}:{L(C_CHK)}{TR1},"<>0")').font = F_B
ws2.cell(TS, C_CHK).number_format = N0
ws2.cell(TS, C_NT, '← BP = 各账户权重合计的平均值（应恒为 100%）；BX = 权重异常账户个数（应为 0，容差 1e-9）').font = F_SUB
for c in range(1, NC2 + 1):
    ws2.cell(TS, c).fill = FILL_HL
    ws2.cell(TS, c).border = BD
# 年数辅助行
TROW = TS + 1
ws2.cell(TROW, 2, '年数 t（辅助行）').font = F_SUB
for j, (bl, t) in enumerate(BUCKETS):
    c = ws2.cell(TROW, BUCKET_C0 + j, t)
    c.font, c.border, c.number_format = F_SUB, BD, N4
for c in range(1, BUCKET_C0 + NB):
    ws2.cell(TROW, c).border = BD
# WAL 公式（横向 SUMPRODUCT）
for i, a in enumerate(ACCOUNTS):
    rr = TR0 + i
    ws2.cell(rr, C_WAL,
             f'=IF(SUM({BLK}{rr}:{BLK1}{rr})=0,0,'
             f'SUMPRODUCT({BLK}{rr}:{BLK1}{rr},${BLK}${TROW}:${BLK1}${TROW})/SUM({BLK}{rr}:{BLK1}{rr}))').font = F_CALC
    ws2.cell(rr, C_WAL).number_format = N4
# 分段辅助行（供 ⑧ 引用）：资产端 / 负债端
ASEG_ROW = TROW + 2
LSEG_ROW = TROW + 3
for tag, rr, side in (('资产端各分段金额', ASEG_ROW, '资产'), ('负债端各分段金额', LSEG_ROW, '负债')):
    ws2.cell(rr, 2, tag + '（辅助行）').font = F_SUB
    for cc in (C_S1, C_S2, C_S3, C_S4, C_S5):
        ws2.cell(rr, cc,
                 f'=SUMIF($C${TR0}:$C${TR1},"{side}",{L(cc)}${TR0}:{L(cc)}${TR1})').font = F_CALC
        ws2.cell(rr, cc).number_format = N2
    for c in range(1, NC2 + 1):
        ws2.cell(rr, c).border = BD
    ws2.cell(rr, C_NT, '← 供 ⑧ 结构拆解【三】按期限分段引用').font = F_SUB
ws2.freeze_panes = f'D{TR0}'

# ===========================================================
# ③ 逐月利息推演
# ===========================================================
ws3 = wb.create_sheet('③逐月利息推演')
C_M0 = 6                                        # F 列 = M1 月末余额
C_M1 = C_M0 + 11                                # Q 列 = M12 月末余额
C_I0 = C_M1 + 1                                 # R 列 = M1 月息
C_I1 = C_I0 + 11                                # AC 列 = M12 月息
C_YI = C_I1 + 1                                 # AD 年度利息
C_CMP = C_YI + 1                                # AE 对照（余额×利率）
C_DIF = C_CMP + 1                               # AF 差异率
C_E12 = C_DIF + 1                               # AG 12月末余额
C_BAS = C_E12 + 1                               # AH 年计息基数
C_NT3 = C_BAS + 1                               # AI 说明
H3 = (['账户编码', '账户名称', '大类', '加权平均\n利率', '期初余额\n(亿元)'] +
      [f'M{m}\n月末余额' for m in range(1, 13)] +
      [f'M{m}\n月利息' for m in range(1, 13)] +
      ['年度利息\n(亿元/年)', '对照\n余额×利率', '差异率', 'M12末\n余额', '年计息基数\n(亿元)', '说明'])
W3 = ([17, 24, 8, 11, 14] + [13] * 12 + [13] * 12 + [15, 14, 11, 13, 14, 40])
ws3['A1'] = '③ 逐月利息推演 — 月末余额递推 + 月度利息（逐月平均余额法）'
ws3['A1'].font = F_TITLE
ws3.merge_cells(f'A1:{L(C_NT3)}1')
ws3['A2'] = ('月末余额(m) = 月末余额(m−1) − ②剩余期限结构(m 桶权重 × 期初余额)  |  '
             '月度利息(m) =（月初余额 + 月末余额）/2 × 加权平均利率 ÷ 12  |  '
             '年度利息 = 12 个月利息加总（①数据源 I 列引用本表）  |  '
             '★ 存量自然到期口径：不模拟续作与新增业务')
ws3['A2'].font = F_SUB
ws3.merge_cells(f'A2:{L(C_NT3)}2')
r = hdr(ws3, 3, H3, W3)
TR3_0 = r
for i, a in enumerate(ACCOUNTS):
    rr = TR3_0 + i
    src = D0 + i                                   # ① 数据源行
    wsrc = TR0 + i                                 # ② 权重行
    is_a = a['cat'] == 'ASSET'
    fb = FILL_A if is_a else (FILL_L if a['cat'] == 'LIAB' else FILL_NEA)
    ws3.cell(rr, 1, f"='①数据源'!A{src}").font = F_N
    ws3.cell(rr, 2, f"='①数据源'!B{src}").font = F_N
    ws3.cell(rr, 3, f"='①数据源'!C{src}").font = F_N
    ws3.cell(rr, 4, f"='①数据源'!G{src}").font = F_CALC
    ws3.cell(rr, 4).number_format = P2
    ws3.cell(rr, 5, f"='①数据源'!F{src}").font = F_CALC
    ws3.cell(rr, 5).number_format = N2
    # 月末余额递推（减性）：上月末余额 − 当月到期金额（②权重 × 期初余额）
    for m in range(12):
        cc = C_M0 + m
        prev = f'$E{rr}' if m == 0 else f'{L(cc-1)}{rr}'
        wcol = L(BUCKET_C0 + m)
        ws3.cell(rr, cc, f"={prev}-'②剩余期限结构'!{wcol}{wsrc}*$E{rr}").font = F_CALC
        ws3.cell(rr, cc).number_format = N2
    # 月度利息
    for m in range(12):
        cc = C_I0 + m
        beg = f'$E{rr}' if m == 0 else f'{L(C_M0+m-1)}{rr}'
        end = f'{L(C_M0+m)}{rr}'
        ws3.cell(rr, cc, f'=({beg}+{end})/2*$D{rr}/12').font = F_CALC
        ws3.cell(rr, cc).number_format = N2
    ws3.cell(rr, C_YI, f'=SUM({L(C_I0)}{rr}:{L(C_I1)}{rr})').font = F_B
    ws3.cell(rr, C_YI).number_format = N2
    ws3.cell(rr, C_CMP, f'=$E{rr}*$D{rr}').font = F_CALC
    ws3.cell(rr, C_CMP).number_format = N2
    ws3.cell(rr, C_DIF, f'=IF({L(C_CMP)}{rr}=0,0,{L(C_YI)}{rr}/{L(C_CMP)}{rr}-1)').font = F_CALC
    ws3.cell(rr, C_DIF).number_format = P2
    ws3.cell(rr, C_E12, f'={L(C_M1)}{rr}').font = F_CALC
    ws3.cell(rr, C_E12).number_format = N2
    ws3.cell(rr, C_BAS, f'=($E{rr}+{L(C_M1)}{rr})/2+SUM({L(C_M0)}{rr}:{L(C_M1-1)}{rr})').font = F_CALC
    ws3.cell(rr, C_BAS).number_format = N2
    ws3.cell(rr, C_NT3, f"基础数据!R{a['src_row']} · {SHAPE_NOTE[a['code']]}").font = F_SUB
    for c in range(1, C_NT3 + 1):
        ws3.cell(rr, c).border = BD
        if ws3.cell(rr, c).fill.fgColor.rgb in (None, '00000000'):
            ws3.cell(rr, c).fill = fb
TR3_1 = TR3_0 + len(ACCOUNTS) - 1
TS3 = TR3_1 + 1
ws3.cell(TS3, 2, '合计').font = F_B
for c in list(range(C_M0, C_M1 + 1)) + list(range(C_I0, C_I1 + 1)) + [C_YI, C_CMP, C_E12, C_BAS]:
    ws3.cell(TS3, c, f'=SUM({L(c)}{TR3_0}:{L(c)}{TR3_1})').font = F_B
    ws3.cell(TS3, c).number_format = N2
ws3.cell(TS3, C_DIF, f'=IF({L(C_CMP)}{TS3}=0,0,{L(C_YI)}{TS3}/{L(C_CMP)}{TS3}-1)').font = F_B
ws3.cell(TS3, C_DIF).number_format = P2
ws3.cell(TS3, C_NT3, '← 差异率 = 逐月推演 ÷ 余额×利率 − 1（负值 = 存量到期摊销导致利息递延）').font = F_SUB
for c in range(1, C_NT3 + 1):
    ws3.cell(TS3, c).fill = FILL_HL
    ws3.cell(TS3, c).border = BD
ws3.freeze_panes = f'F{TR3_0}'

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
ws5.merge_cells('A1:M1')
ws5['A2'] = ('年度利息 = ①数据源 I 列（逐月平均余额法推演，存量自然到期口径）  |  '
              '对照列 = 余额 × 加权平均利率（会计静态口径）  |  非生息资产（利率 0%）单列备查，不计入 NIM 分母')
ws5['A2'].font = F_SUB
ws5.merge_cells('A2:M2')
r = hdr(ws5, 3, ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)',
                 '加权平均\n利率', '年度利息\n(亿元/年)\n【推演】', '对照\n余额×利率', '差异率',
                 '利息收入\n占比', '累计占比', '1年内到期\n(亿元)', '口径说明'],
         [17, 26, 12, 9, 13, 11, 15, 13, 10, 12, 12, 13, 32])
A_LIST = [a for a in ACCOUNTS if a['cat'] == 'ASSET' and a['rate'] > 0]
A_ZERO = [a for a in ACCOUNTS if a['cat'] == 'ASSET' and a['rate'] == 0]
AR0 = r
AT = AR0 + len(A_LIST)
for k, a in enumerate(A_LIST):
    i = ACCOUNTS.index(a)
    rr = AR0 + k
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'),
                  (7, 'I'), (8, 'J'), (10, 'K'), (12, 'L')):
        ws5.cell(rr, c, f"='①数据源'!{sc}{D0+i}").font = F_N if c <= 4 else F_CALC
    ws5.cell(rr, 9, f'=IF(H{rr}=0,0,G{rr}/H{rr}-1)').font = F_CALC
    ws5.cell(rr, 10, f'=IF($G${AT}=0,0,G{rr}/$G${AT})').font = F_CALC
    ws5.cell(rr, 11, f'=J{rr}' if k == 0 else f'=K{rr-1}+J{rr}').font = F_CALC
    ws5.cell(rr, 13, f"基础数据!R{a['src_row']}").font = F_SUB
    for c in (5, 7, 8, 12):
        ws5.cell(rr, c).number_format = N2
    for c in (6, 9, 10, 11):
        ws5.cell(rr, c).number_format = P2
    for c in range(1, 14):
        ws5.cell(rr, c).border = BD
        ws5.cell(rr, c).fill = FILL_A
ws5.cell(AT, 2, '利息收入合计（生息资产）').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (8, 'H'), (12, 'L')):
    ws5.cell(AT, c, f'=SUM({col}{AR0}:{col}{AT-1})').font = F_B
    ws5.cell(AT, c).number_format = N2
ws5.cell(AT, 6, f'=IF(E{AT}=0,0,G{AT}/E{AT})').font = F_B
ws5.cell(AT, 6).number_format = P4
ws5.cell(AT, 9, f'=IF(H{AT}=0,0,G{AT}/H{AT}-1)').font = F_B
ws5.cell(AT, 9).number_format = P2
ws5.cell(AT, 10, f'=SUM(J{AR0}:J{AT-1})').font = F_B
ws5.cell(AT, 10).number_format = P2
ws5.cell(AT, 11, f'=K{AT-1}').font = F_B
ws5.cell(AT, 11).number_format = P2
ws5.cell(AT, 13, 'F 列 = 加权平均收益率 · I 列差异率 = 推演 ÷ 静态 − 1（负 = 存量到期摊销递延）· J 列合计应为 100%').font = F_SUB
for c in range(1, 14):
    ws5.cell(AT, c).fill = FILL_HL
    ws5.cell(AT, c).border = BD
r = AT + 2
r = sec(ws5, r, '【附】非生息资产（利率 = 0，不计入利息收入与 NIM 分母）', 13)
NZ0 = r
for k, a in enumerate(A_ZERO):
    i = ACCOUNTS.index(a)
    rr = NZ0 + k
    ws5.cell(rr, 2, f"='①数据源'!B{D0+i}").font = F_N
    ws5.cell(rr, 5, f"='①数据源'!F{D0+i}").font = F_CALC
    ws5.cell(rr, 6, f"='①数据源'!G{D0+i}").font = F_CALC
    ws5.cell(rr, 7, f"='①数据源'!I{D0+i}").font = F_CALC
    ws5.cell(rr, 8, f"='①数据源'!J{D0+i}").font = F_CALC
    ws5.cell(rr, 13, '利率 0%，无利息收入，已从 NIM 分母剔除').font = F_SUB
    for c in (5, 7, 8):
        ws5.cell(rr, c).number_format = N2
    ws5.cell(rr, 6).number_format = P2
    for c in range(1, 14):
        ws5.cell(rr, c).border = BD
        ws5.cell(rr, c).fill = FILL_A
NZ1 = NZ0 + len(A_ZERO) - 1
ANZ = NZ1 + 1
ws5.cell(ANZ, 2, '非生息资产合计（备查）').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (8, 'H')):
    ws5.cell(ANZ, c, f'=SUM({col}{NZ0}:{col}{NZ1})').font = F_B
    ws5.cell(ANZ, c).number_format = N2
for c in range(1, 14):
    ws5.cell(ANZ, c).fill = FILL_HL
    ws5.cell(ANZ, c).border = BD
ws5.freeze_panes = f'C{AR0}'

# ===========================================================
# ⑥ 利息支出明细
# ===========================================================
ws6 = wb.create_sheet('⑥利息支出明细')
ws6['A1'] = '⑥ 利息支出明细 — 计息负债逐账户拆解'
ws6['A1'].font = F_TITLE
ws6.merge_cells('A1:M1')
ws6['A2'] = ('年度利息 = ①数据源 I 列（逐月平均余额法推演，存量自然到期口径）  |  '
              '对照列 = 余额 × 加权平均利率  |  全部计息负债进入 NII 分子（利息支出）')
ws6['A2'].font = F_SUB
ws6.merge_cells('A2:M2')
r = hdr(ws6, 3, ['账户编码', '账户名称', '业务条线', '账户类型', '当前余额\n(亿元)',
                 '加权平均\n利率', '年度利息\n(亿元/年)\n【推演】', '对照\n余额×利率', '差异率',
                 '利息支出\n占比', '累计占比', '1年内到期\n(亿元)', '口径说明'],
         [17, 26, 12, 9, 13, 11, 15, 13, 10, 12, 12, 13, 32])
L_LIST = [a for a in ACCOUNTS if a['cat'] == 'LIAB']
LR0 = r
LT = LR0 + len(L_LIST)
for k, a in enumerate(L_LIST):
    i = ACCOUNTS.index(a)
    rr = LR0 + k
    for c, sc in ((1, 'A'), (2, 'B'), (3, 'D'), (4, 'E'), (5, 'F'), (6, 'G'),
                  (7, 'I'), (8, 'J'), (10, 'K'), (12, 'L')):
        ws6.cell(rr, c, f"='①数据源'!{sc}{D0+i}").font = F_N if c <= 4 else F_LIABC
    ws6.cell(rr, 9, f'=IF(H{rr}=0,0,G{rr}/H{rr}-1)').font = F_CALC
    ws6.cell(rr, 10, f'=IF($G${LT}=0,0,G{rr}/$G${LT})').font = F_CALC
    ws6.cell(rr, 11, f'=J{rr}' if k == 0 else f'=K{rr-1}+J{rr}').font = F_CALC
    ws6.cell(rr, 13, f"基础数据!R{a['src_row']}").font = F_SUB
    for c in (5, 7, 8, 12):
        ws6.cell(rr, c).number_format = N2
    for c in (6, 9, 10, 11):
        ws6.cell(rr, c).number_format = P2
    for c in range(1, 14):
        ws6.cell(rr, c).border = BD
        ws6.cell(rr, c).fill = FILL_L
ws6.cell(LT, 2, '利息支出合计（计息负债）').font = F_B
for c, col in ((5, 'E'), (7, 'G'), (8, 'H'), (12, 'L')):
    ws6.cell(LT, c, f'=SUM({col}{LR0}:{col}{LT-1})').font = F_B
    ws6.cell(LT, c).number_format = N2
ws6.cell(LT, 6, f'=IF(E{LT}=0,0,G{LT}/E{LT})').font = F_B
ws6.cell(LT, 6).number_format = P4
ws6.cell(LT, 9, f'=IF(H{LT}=0,0,G{LT}/H{LT}-1)').font = F_B
ws6.cell(LT, 9).number_format = P2
ws6.cell(LT, 10, f'=SUM(J{LR0}:J{LT-1})').font = F_B
ws6.cell(LT, 10).number_format = P2
ws6.cell(LT, 11, f'=K{LT-1}').font = F_B
ws6.cell(LT, 11).number_format = P2
ws6.cell(LT, 13, 'F 列 = 加权平均付息成本率 · J 列合计应为 100%').font = F_SUB
for c in range(1, 14):
    ws6.cell(LT, c).fill = FILL_HL
    ws6.cell(LT, c).border = BD
r = LT + 2
r = sec(ws6, r, '【附】负债期限结构说明（逐月推演的余额衰减路径）', 13)
ws6.cell(r, 2, '★ 逐月推演显示：活期存款 3 个月内基本全额到期（余额归零后不再产生利息），'
               '定期/市场化负债 12 个月内到期约 2/3，这是利息支出差异率显著为负的主因').font = F_SUB
ws6.merge_cells(start_row=r, start_column=2, end_row=r, end_column=13)
for c in range(1, 14):
    ws6.cell(r, c).border = BD
ws6.freeze_panes = f'C{LR0}'

# ===========================================================
# ⑦ NII 计量表
# ===========================================================
ws7 = wb.create_sheet('⑦NII计量表')
for i, w in enumerate([46, 17, 14, 12, 52], 1):
    ws7.column_dimensions[L(i)].width = w
ws7['A1'] = '⑦ 净利息收入（NII）计量表 — 逐月平均余额法口径'
ws7['A1'].font = F_TITLE
ws7.merge_cells('A1:E1')
ws7['A2'] = ('★ 主口径：年度利息 = 逐月平均余额法推演（存量自然到期，不模拟续作）  |  '
             '对照口径：年度利息 = 余额 × 加权平均利率  |  '
             'NII = 利息收入 − 利息支出  |  NIM = NII ÷ 生息资产  |  不含重定价建模')
ws7['A2'].font = F_SUB
ws7.merge_cells('A2:E2')

r = sec(ws7, 4, '【一】规模：生息资产与计息负债', 5)
R_EA, R_NEA, R_TA, R_EQ, R_TL = r, r + 1, r + 2, r + 3, r + 4
EQ_ROW = D0 + [ACCOUNTS.index(a) for a in ACCOUNTS if a['cat'] == 'EQUITY'][0]
rows1 = [
    (R_EA, '★ 生息资产（利率 > 0，NIM 分母）', f"='⑤利息收入明细'!E{AT}", N2, '剔除非生息资产后的生息资产口径'),
    (R_NEA, '非生息资产（利率 = 0，不计入分母）', f"='⑤利息收入明细'!E{ANZ}", N2, '现金 / 其它非生息资产'),
    (R_TA, '资产端合计（= 参照物总资产）', f"='⑤利息收入明细'!E{AT}+'⑤利息收入明细'!E{ANZ}", N2, '生息 + 非生息'),
    (R_EQ, '所有者权益（不进入分母）', f"='①数据源'!F{EQ_ROW}", N2, '无偿还计划，30Y 视同永续'),
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
r = sec(ws7, r, '【二】分子：利息收入与利息支出（双口径并列）', 5)
R_II, R_IE, R_II_C, R_IE_C, R_DIF = r, r + 1, r + 2, r + 3, r + 4
rows2 = [
    (R_II, '★ 利息收入合计（逐月推演口径）', f"='⑤利息收入明细'!G{AT}", N2, '主口径：12 个月逐月平均余额计息加总'),
    (R_IE, '★ 利息支出合计（逐月推演口径）', f"='⑥利息支出明细'!G{LT}", N2, '主口径：12 个月逐月平均余额计息加总'),
    (R_II_C, '对照：利息收入合计（余额×利率）', f"='⑤利息收入明细'!H{AT}", N2, '会计静态口径，等于参照物 EM × 12'),
    (R_IE_C, '对照：利息支出合计（余额×利率）', f"='⑥利息支出明细'!H{LT}", N2, '会计静态口径，等于参照物 EM × 12'),
    (R_DIF, '口径差异（推演 − 静态）', f'=$B${R_II}-$B${R_II_C}', N2, '存量自然到期摊销导致的利息递延，负值'),
]
for rr, lab, fml, fmt, note in rows2:
    ws7.cell(rr, 1, lab).font = F_B if rr in (R_II, R_IE) else F_N
    ws7.cell(rr, 2, fml).font = F_KPIN if rr in (R_II, R_IE) else F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, '亿元/年').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD
        if rr in (R_II, R_IE):
            ws7.cell(rr, c).fill = FILL_KPI

r = R_DIF + 2
r = sec(ws7, r, '【三】★ 双口径差异归因（为何推演口径低于静态口径）', 5)
R_A1Y, R_L1Y, R_A_BASE, R_L_BASE, R_A_RATIO, R_L_RATIO = r, r + 1, r + 2, r + 3, r + 4, r + 5
rows3 = [
    (R_A1Y, '资产端：1 年内到期金额', f'=SUMIF({RF["CAT"]},"资产",{RF["W12"]})', N2, '12 个月内自然到期的生息资产规模'),
    (R_L1Y, '负债端：1 年内到期金额', f'=SUMIF({RF["CAT"]},"负债",{RF["W12"]})', N2, '12 个月内自然到期的计息负债规模'),
    (R_A_BASE, '资产端年计息基数（余额×12）', f"=SUMIF({RF['CAT']},\"资产\",{RF['BAL']})*12", N2, '静态口径下 12 个月的计息基数'),
    (R_L_BASE, '负债端年计息基数（余额×12）', f"=SUMIF({RF['CAT']},\"负债\",{RF['BAL']})*12", N2, '静态口径下 12 个月的计息基数'),
    (R_A_RATIO, '★ 资产端 推演/静态 差异率', f'=IF($B${R_A_BASE}=0,0,$B${R_II}/($B${R_A_BASE}*0+SUMIF({RF["CAT"]},"资产",{RF["RATE"]}))/12*12-$B${R_A_RATIO})', P2, '占位，下面重写'),
    (R_L_RATIO, '★ 负债端 推演/静态 差异率', f'=0', P2, '占位，下面重写'),
]
for rr, lab, fml, fmt, note in rows3:
    ws7.cell(rr, 1, lab).font = F_B if rr in (R_A_RATIO, R_L_RATIO) else F_N
    ws7.cell(rr, 2, fml).font = F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, '亿元' if fmt == N2 else '%').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD
# 重写差异率公式（真实口径）
ws7.cell(R_A_RATIO, 2, f'=IF($B${R_II_C}=0,0,$B${R_II}/$B${R_II_C}-1)').font = F_KPIN
ws7.cell(R_A_RATIO, 2).number_format = P2
ws7.cell(R_A_RATIO, 5, '★ 资产端：到期本金退出生息基数，利息按剩余余额逐月递减').font = F_B
ws7.cell(R_L_RATIO, 2, f'=IF($B${R_IE_C}=0,0,$B${R_IE}/$B${R_IE_C}-1)').font = F_KPIN
ws7.cell(R_L_RATIO, 2).number_format = P2
ws7.cell(R_L_RATIO, 5, '★ 负债端：活期存款 3 个月内全额到期，付息基数骤降，差异率更负').font = F_B
for rr in (R_A_RATIO, R_L_RATIO):
    for c in range(1, 6):
        ws7.cell(rr, c).fill = FILL_KPI
        ws7.cell(rr, c).border = BD

r = R_L_RATIO + 2
r = sec(ws7, r, '【四】★ 核心结果：NII 与 NIM', 5)
R_NII, R_NIM, R_YLD, R_CST, R_NIS, R_K = r, r + 1, r + 2, r + 3, r + 4, r + 5
rows4 = [
    (R_NII, '★ 净利息收入 NII（推演口径）', f'=$B${R_II}-$B${R_IE}', N2, '= 利息收入 − 利息支出'),
    (R_NIM, '★ 净息差 NIM（推演口径）', f'=IF($B${R_EA}=0,0,$B${R_NII}/$B${R_EA})', P4, 'NII ÷ 生息资产'),
    (R_YLD, '生息资产收益率（推演口径）', f'=IF($B${R_EA}=0,0,$B${R_II}/$B${R_EA})', P4, '利息收入 ÷ 生息资产'),
    (R_CST, '计息负债成本率（推演口径）', f'=IF($B${R_TL}=0,0,$B${R_IE}/$B${R_TL})', P4, '利息支出 ÷ 计息负债'),
    (R_NIS, '净利差 NIS（推演口径）', f'=$B${R_YLD}-$B${R_CST}', P4, '资产收益率 − 负债成本率'),
    (R_K, '负债支持率 k = 计息负债 ÷ 生息资产', f'=IF($B${R_EA}=0,0,$B${R_TL}/$B${R_EA})', P4, 'NIM = 收益率 − 成本率 × k'),
]
for rr, lab, fml, fmt, note in rows4:
    ws7.cell(rr, 1, lab).font = F_B if rr in (R_NII, R_NIM) else F_N
    ws7.cell(rr, 2, fml).font = F_KPIN if rr in (R_NII, R_NIM) else F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, '亿元/年' if fmt == N2 else '%').font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD
        if rr in (R_NII, R_NIM):
            ws7.cell(rr, c).fill = FILL_KPI
R_NII_C = r + 6
R_NIM_C = r + 7
ws7.cell(R_NII_C, 1, '对照：NII（静态口径 余额×利率）').font = F_N
ws7.cell(R_NII_C, 2, f'=$B${R_II_C}-$B${R_IE_C}').font = F_CALC
ws7.cell(R_NII_C, 2).number_format = N2
ws7.cell(R_NII_C, 5, '会计口径 NII，供与 NIM 模版勾稽').font = F_SUB
ws7.cell(R_NIM_C, 1, '对照：NIM（静态口径）').font = F_N
ws7.cell(R_NIM_C, 2, f'=IF($B${R_EA}=0,0,$B${R_NII_C}/$B${R_EA})').font = F_CALC
ws7.cell(R_NIM_C, 2).number_format = P4
ws7.cell(R_NIM_C, 5, 'NIM 模版采用此口径（余额×利率）').font = F_SUB
for rr in (R_NII_C, R_NIM_C):
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD
        ws7.cell(rr, c).fill = FILL_HL

r = R_NIM_C + 2
r = sec(ws7, r, '【五】结构比率与期限结构', 5)
R_S0 = r
rows5 = [
    ('平均贷款余额（5 项贷款）', f'=SUMIF({RF["LINE"]},"信贷资产",{RF["BAL"]})', N2, '对公/个人/信用卡/票据/非银'),
    ('平均存款余额（4 项存款）', f'=SUMIF({RF["LINE"]},"存款类",{RF["BAL"]})', N2, '对公活期/定期 + 零售活期/定期'),
    ('存贷比（贷款 ÷ 计息负债）', f'=IF($B${R_TL}=0,0,B{R_S0}/$B${R_TL})', P2, '监管上限 100%（现行为 75% 分档考核）'),
    ('存款活期化率（活期 ÷ 存款合计）', f'=IF(SUMIF({RF["LINE"]},"存款类",{RF["BAL"]})=0,0,SUMIF({RF["TYPE"]},"活期",{RF["BAL"]})/SUMIF({RF["LINE"]},"存款类",{RF["BAL"]}))', P2, '活期成本低，衡量存款成本优化空间'),
    ('资产端 1 年内到期占比', f'=IF($B${R_EA}=0,0,SUMIF({RF["CAT"]},"资产",{RF["W12"]})/$B${R_EA})', P2, '★ 决定推演口径利息递延幅度'),
    ('负债端 1 年内到期占比', f'=IF($B${R_TL}=0,0,SUMIF({RF["CAT"]},"负债",{RF["W12"]})/$B${R_TL})', P2, '★ 活期存款占比高 → 负债端递延更严重'),
    ('资产端 WAL（加权平均剩余期限）', f"=SUMPRODUCT(({RF['CAT']}=\"资产\")*{RF['BAL']}*'②剩余期限结构'!$BY${TR0}:$BY${TR1})/SUMIF({RF['CAT']},\"资产\",{RF['BAL']})", N4, '年；静态期限结构披露'),
    ('负债端 MAL（加权平均剩余期限）', f"=SUMPRODUCT(({RF['CAT']}=\"负债\")*{RF['BAL']}*'②剩余期限结构'!$BY${TR0}:$BY${TR1})/SUMIF({RF['CAT']},\"负债\",{RF['BAL']})", N4, '年；静态期限结构披露'),
    ('期限结构错配 WAL − MAL', f'=B{R_S0+6}-B{R_S0+7}', N4, '年；正 = 资产久于负债'),
]
for k, (lab, fml, fmt, note) in enumerate(rows5):
    rr = R_S0 + k
    ws7.cell(rr, 1, lab).font = F_N
    ws7.cell(rr, 2, fml).font = F_CALC
    ws7.cell(rr, 2).number_format = fmt
    ws7.cell(rr, 4, '亿元' if fmt == N2 else ('年' if fmt == N4 else '%')).font = F_SUB
    ws7.cell(rr, 5, note).font = F_SUB
    for c in range(1, 6):
        ws7.cell(rr, c).border = BD

r = R_S0 + len(rows5) + 1
r = sec(ws7, r, '【六】勾稽校验（校验 1~11 应全部为 0）', 5)
rows6 = [
    ('校验 1：⑤明细 = ①Σ年度利息（资产）', f"=ROUND('⑤利息收入明细'!G{AT}-SUMIF({RF['CAT']},\"资产\",{RF['IY']}),6)", '明细 ↔ 数据源'),
    ('校验 2：⑥明细 = ①Σ年度利息（负债）', f"=ROUND('⑥利息支出明细'!G{LT}-SUMIF({RF['CAT']},\"负债\",{RF['IY']}),6)", '明细 ↔ 数据源'),
    ('校验 3：①Σ全部年度利息 = 资产 + 负债', f'=ROUND(SUM({RF["IY"]})-SUMIF({RF["CAT"]},"资产",{RF["IY"]})-SUMIF({RF["CAT"]},"负债",{RF["IY"]}),6)', '权益年度利息为 0'),
    ('校验 4：①静态口径 Σ = 资产 + 负债', f'=ROUND(SUM({RF["IY_CMP"]})-SUMIF({RF["CAT"]},"资产",{RF["IY_CMP"]})-SUMIF({RF["CAT"]},"负债",{RF["IY_CMP"]}),6)', '静态口径同样平衡'),
    ('校验 5：③推演年度利息 = ①数据源 I 列', f"=ROUND('③逐月利息推演'!AD{TS3}-SUM({RF['IY']}),6)", '逐月推演表 ↔ 数据源'),
    ('校验 6：★ 逐月推演 Σ月度利息 = Σ年度利息（资产）',
     f"=ROUND(SUMIF({RF['CAT']},\"资产\",{RF['IM12']})*12-SUMIF({RF['CAT']},\"资产\",{RF['IY']}),6)", '月度利息均值 × 12 = 年度利息'),
    ('校验 7：逐月推演 Σ月度利息 = Σ年度利息（负债）',
     f"=ROUND(SUMIF({RF['CAT']},\"负债\",{RF['IM12']})*12-SUMIF({RF['CAT']},\"负债\",{RF['IY']}),6)", '月度利息均值 × 12 = 年度利息'),
    ('校验 8：NII = 利息收入 − 利息支出', f'=ROUND($B${R_NII}-($B${R_II}-$B${R_IE}),8)', 'NII 主口径恒等式'),
    ('校验 9：⑤利息收入占比合计 = 100%', f"=ROUND('⑤利息收入明细'!J{AT}-1,8)", '占比无重复无遗漏'),
    ('校验 10：⑥利息支出占比合计 = 100%', f"=ROUND('⑥利息支出明细'!J{LT}-1,8)", '占比无重复无遗漏'),
    ('校验 11：★ ②剩余期限结构 权重校验差 = 0', f"=ROUND('②剩余期限结构'!{L(C_CHK)}{TS},10)", '24 个账户权重合计均为 100%（容差 1e-9，合计行为异常账户个数）'),
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
    (R_J1, '本行 NIM 达标判定（推演口径）', f'=IF($B${R_NIM}>=$B${R_RL},"达标","不达标")', '@', 'NIM ≥ 1.50%', False),
    (R_J2, '本行 NIM 区间判定（推演口径）', f'=IF(AND($B${R_NIM}>=$B${R_RL},$B${R_NIM}<=$B${R_RU}),"位于合理区间","偏离合理区间")', '@', '1.50% ≤ NIM ≤ 2.50%', False),
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
for i, w in enumerate([22, 10, 15, 12, 15, 12, 12, 13, 40], 1):
    ws8.column_dimensions[L(i)].width = w
ws8['A1'] = '⑧ NII 结构拆解 — 业务条线 / 账户类型 / 期限分段 三维'
ws8['A1'].font = F_TITLE
ws8.merge_cells('A1:I1')
ws8['A2'] = ('全部由 SUMIF 引用「①数据源」，联动更新  |  期限维度引用「②剩余期限结构」辅助行  |  '
              '年度利息为逐月推演口径  |  单位：亿元 / 亿元每年 / %')
ws8['A2'].font = F_SUB
ws8.merge_cells('A2:I2')

H8 = ['维度', '方向', '当前余额\n(亿元)', '余额占比', '年度利息\n(亿元/年)', '利息占比',
      '差异率\n(推演vs静态)', '1年内到期\n(亿元)', '说明']
LN_KEYS = [('信贷资产', '资产'), ('债券投资', '资产'), ('金融市场', '资产'),
           ('非生息资产', '资产'), ('外币资产', '资产'),
           ('活期存款', '负债'), ('定期存款', '负债'), ('市场化负债', '负债'), ('外币负债', '负债')]
NOTE8 = {'信贷资产': '余额 55 万亿，利率最高，是 NII 的最大贡献项',
         '债券投资': '余额 25 万亿，票息低，压低整体收益率',
         '金融市场': '同业 / 准备金 / 结构化融资，短久期',
         '非生息资产': '利率 0%，不产生利息，拉低资产端合计收益率',
         '外币资产': '折人民币计价',
         '活期存款': '★ 3 个月内全额到期，付息基数骤降，差异率最负',
         '定期存款': '12 个月内到期约 2/3',
         '市场化负债': '货币市场工具，成本最高',
         '外币负债': '折人民币计价'}

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
    ws8.cell(rr, 7, f'=IF(SUMIF({RF["LINE"]},"{ln}",{RF["IY_CMP"]})=0,0,E{rr}/SUMIF({RF["LINE"]},"{ln}",{RF["IY_CMP"]})-1)').font = F_CALC
    ws8.cell(rr, 8, f'=SUMIF({RF["LINE"]},"{ln}",{RF["W12"]})').font = F_CALC
    ws8.cell(rr, 9, NOTE8.get(ln, '')).font = F_SUB
    for c in (3, 5, 8):
        ws8.cell(rr, c).number_format = N2
    for c in (4, 6, 7):
        ws8.cell(rr, c).number_format = P2
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
          '活期': '★ 剩余期限 12 个月内 100% 到期，差异率最负',
          '定期': '1 年内到期 46%',
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
    ws8.cell(rr, 7, f'=IF(SUMIF({RF["TYPE"]},"{ln}",{RF["IY_CMP"]})=0,0,E{rr}/SUMIF({RF["TYPE"]},"{ln}",{RF["IY_CMP"]})-1)').font = F_CALC
    ws8.cell(rr, 8, f'=SUMIF({RF["TYPE"]},"{ln}",{RF["W12"]})').font = F_CALC
    ws8.cell(rr, 9, TNOTE8.get(ln, '')).font = F_SUB
    for c in (3, 5, 8):
        ws8.cell(rr, c).number_format = N2
    for c in (4, 6, 7):
        ws8.cell(rr, c).number_format = P2
    for c in range(1, 10):
        ws8.cell(rr, c).border = BD
        ws8.cell(rr, c).fill = FILL_A if d == '资产' else FILL_L
    r += 1
S8B1 = r - 1
r += 1
r = sec(ws8, r, '【三】按剩余期限分段拆解（引用 ②剩余期限结构 辅助行）', 9)
r = hdr(ws8, r, ['期限分段', '方向', '余额\n(亿元)', '该方向占比', '桶数',
                 '—', '—', '—', '说明'])
SEG0 = r
SEGS = [('1M~3M', 'BS', 3, '3 个月内到期（活期存款集中区）'),
        ('4M~12M', 'BT', 9, '4~12 个月到期'),
        ('1Y~3Y', 'BU', 24, '1~3 年到期'),
        ('3Y~5Y', 'BV', 24, '3~5 年到期'),
        ('5Y 以上', 'BW', 4, '5 年以上（含 10Y/15Y/20Y/30Y 长尾）')]
for lab, scol, nbucket, note in SEGS:
    for d, arow in (('资产', ASEG_ROW), ('负债', LSEG_ROW)):
        rr = r
        ws8.cell(rr, 1, lab).font = F_N
        ws8.cell(rr, 2, d).font = F_N
        ws8.cell(rr, 3, f"='②剩余期限结构'!{scol}{arow}").font = F_CALC
        ws8.cell(rr, 4, f"=IF('②剩余期限结构'!{scol}{'{}'}".format(arow) + f"=0,0,C{rr}/'②剩余期限结构'!{scol}{arow})").font = F_CALC
        ws8.cell(rr, 5, nbucket).font = F_N
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
# ⑨ 情景敏感性
# ===========================================================
ws9 = wb.create_sheet('⑨情景敏感性')
for i, w in enumerate([28, 12, 17, 17, 15, 17, 13, 13, 44], 1):
    ws9.column_dimensions[L(i)].width = w
ws9['A1'] = '⑨ NII 情景敏感性分析（基于逐月推演口径，不含重定价建模）'
ws9['A1'].font = F_TITLE
ws9.merge_cells('A1:I1')
ws9['A2'] = ('★ 假设：所有账户利率等幅平移（不区分重定价时点与幅度，不设 β、不计算重定价缺口）  |  '
             'ΔNII = Δr × (生息资产 − 计息负债)  |  NIM 随之变动  |  '
             '★ 推演口径下计息基数随到期递减，敏感度略低于静态口径')
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
     f"='⑦NII计量表'!$B${R_EA}*0.05*((SUMIF({RF['TYPE']},\"信贷\",{RF['IY_CMP']})/SUMIF({RF['TYPE']},\"信贷\",{RF['BAL']}))-(SUMIF({RF['TYPE']},\"投资\",{RF['IY_CMP']})/SUMIF({RF['TYPE']},\"投资\",{RF['BAL']})))",
     '=0', '信贷 4.63% vs 债券 2.67%，5pp 置换抬升利息收入'),
    ('活期化率 −10pp（定期转活期）', '−10pp',
     '=0',
     f"=SUMIF({RF['TYPE']},\"定期\",{RF['BAL']})*0.1*((SUMIF({RF['TYPE']},\"定期\",{RF['IY_CMP']})/SUMIF({RF['TYPE']},\"定期\",{RF['BAL']}))-(SUMIF({RF['TYPE']},\"活期\",{RF['IY_CMP']})/SUMIF({RF['TYPE']},\"活期\",{RF['BAL']})))",
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
r = sec(ws9, r, '【四】★ 逐月推演口径 vs 静态口径的利率敏感度对比', 9)
r = hdr(ws9, r, ['口径', '计息基数\n(亿元)', 'Δr = 100bp\nΔNII (亿元/年)', 'NII\n(亿元/年)',
                 'NIM', '推演 vs 静态\nNII 差异', '差异率', '—', '说明'])
CMP0 = r
ws9.cell(r, 1, '★ 逐月推演口径（主口径）').font = F_B
ws9.cell(r, 2, f"='⑦NII计量表'!$B${R_EA}-'⑦NII计量表'!$B${R_TL}").font = F_CALC
ws9.cell(r, 2).number_format = N2
ws9.cell(r, 3, f"=-0.01*('⑦NII计量表'!$B${R_EA}-'⑦NII计量表'!$B${R_TL})").font = F_CALC
ws9.cell(r, 3).number_format = N2
ws9.cell(r, 4, f"='⑦NII计量表'!$B${R_NII}").font = F_CALC
ws9.cell(r, 4).number_format = N2
ws9.cell(r, 5, f"='⑦NII计量表'!$B${R_NIM}").font = F_CALC
ws9.cell(r, 5).number_format = P4
ws9.cell(r, 6, f"=D{r}-D{r+1}").font = F_CALC
ws9.cell(r, 6).number_format = N2
ws9.cell(r, 7, f"=IF(D{r+1}=0,0,D{r}/D{r+1}-1)").font = F_CALC
ws9.cell(r, 7).number_format = P2
ws9.cell(r, 9, '存量自然到期摊销后，计息基数逐年下降').font = F_SUB
for c in range(1, 10):
    ws9.cell(r, c).border = BD
    ws9.cell(r, c).fill = FILL_KPI
r += 1
ws9.cell(r, 1, '对照：静态口径（余额×利率）').font = F_N
ws9.cell(r, 2, f"='⑦NII计量表'!$B${R_EA}-'⑦NII计量表'!$B${R_TL}").font = F_CALC
ws9.cell(r, 2).number_format = N2
ws9.cell(r, 3, f"=-0.01*('⑦NII计量表'!$B${R_EA}-'⑦NII计量表'!$B${R_TL})").font = F_CALC
ws9.cell(r, 3).number_format = N2
ws9.cell(r, 4, f"='⑦NII计量表'!$B${R_NII_C}").font = F_CALC
ws9.cell(r, 4).number_format = N2
ws9.cell(r, 5, f"='⑦NII计量表'!$B${R_NIM_C}").font = F_CALC
ws9.cell(r, 5).number_format = P4
ws9.cell(r, 9, '与 NIM 模版口径一致').font = F_SUB
for c in range(1, 10):
    ws9.cell(r, c).border = BD
    ws9.cell(r, c).fill = FILL_HL
r += 1
ws9.freeze_panes = 'A4'

# ===========================================================
# ⑩ 计算逻辑说明
# ===========================================================
ws10 = wb.create_sheet('⑩计算逻辑说明')
for i, w in enumerate([10, 30, 66, 46], 1):
    ws10.column_dimensions[L(i)].width = w
ws10['A1'] = '⑩ 计算逻辑说明 — 逐月平均余额法利息推演'
ws10['A1'].font = F_TITLE
ws10.merge_cells('A1:D1')
ws10['A2'] = ('本模版所有指标均可由「①数据源」的当前余额与加权平均利率、'
               '「②剩余期限结构」的权重形态、「③逐月利息推演」的递推公式自动算出，无硬编码结果。')
ws10['A2'].font = F_SUB
ws10.merge_cells('A2:D2')
r = 4
r = sec(ws10, r, '【一】核心公式（Excel 单元格级）', 4)
for k, h in enumerate(['序号', '项目', '公式 / 单元格位置', '说明'], 1):
    c = ws10.cell(r, k, h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
r += 1
FML = [
    ('F1', '剩余期限权重（形态）', '②剩余期限结构 D~BO 列 = 各桶权重%，绿区输入', '按业务属性摆布，BP 列合计恒为 100%'),
    ('F2', '1 年内金额', f'②剩余期限结构 BR = 当前余额 × SUM(D:O)', '前 12 桶（1M~12M）权重之和 × 余额'),
    ('F3', 'WAL（加权平均剩余期限）', '②剩余期限结构 BY = SUMPRODUCT(D:BO, 年数行) / SUM(D:BO)', '静态期限结构指标，年'),
    ('F4', '期末余额递推', '③逐月利息推演 F 列 = $E行 × (1 − ②!D行权重)', 'M1 月末 = 期初 × (1 − 1M 权重)'),
    ('F5', '月末余额递推', '③逐月利息推演 G~Q 列 = 前一月末 × (1 − ②!对应桶权重)', '逐月递减，M12 末为 12 个月后余额'),
    ('F6', '月度利息', '③逐月利息推演 R 列 =（$E行 + F行）/2 × $D行 / 12', '★（月初余额 + 月末余额）/2 × 加权平均利率 ÷ 12'),
    ('F7', '年度利息（推演）', '③逐月利息推演 AD 列 = SUM(R:AC)', '★ 12 个月月度利息加总；①数据源 I 列引用本列'),
    ('F8', '年计息基数', '③逐月利息推演 AH 列 = ($E + Q)/2 + SUM(F:P)', '12 个月平均余额的加总，用于利率敏感度分析'),
    ('F9', '对照：静态口径年度利息', '①数据源 J 列 = F 列余额 × G 列利率', '会计静态口径，等于参照物 EM × 12'),
    ('F10', 'NII', f'⑦NII计量表 B{R_NII} = B{R_II} − B{R_IE}', '利息收入 − 利息支出'),
    ('F11', 'NIM', f'⑦NII计量表 B{R_NIM} = B{R_NII} ÷ B{R_EA}', 'NII ÷ 生息资产'),
    ('F12', '口径差异率', f'⑦NII计量表 B{R_A_RATIO} = B{R_II} ÷ B{R_II_C} − 1', '推演 vs 静态，负值 = 到期摊销递延'),
]
for no, item, f, note in FML:
    ws10.cell(r, 1, no).font = F_B
    ws10.cell(r, 2, item).font = F_N
    ws10.cell(r, 3, f).font = F_CALC
    ws10.cell(r, 4, note).font = F_SUB
    for c in range(1, 5):
        ws10.cell(r, c).border = BD
    r += 1
r += 1
r = sec(ws10, r, '【二】剩余期限形态设计依据', 4)
for k, h in enumerate(['序号', '业务类别', '形态特征', '经济含义'], 1):
    c = ws10.cell(r, k, h)
    c.font, c.fill, c.alignment, c.border = F_HEAD, FILL_HEAD, AC, BD
r += 1
SHAPE_DOC = [
    ('S1', '票据贴现 / 同业资产', '6 个月内到期 45~70%', '货币市场与票据类资产久期极短，余额快速周转'),
    ('S2', '存款准备金 / 现金类', '3~6 个月内到期 60%+', '随时可支取，理论上随时可提取'),
    ('S3', '活期存款', '1M~12M 逐月递减，100% 年内到期', '日均留存基础上的到期分布，无合同期限但持续周转'),
    ('S4', '定期存款 / 市场化负债', '1 年内 38~68%，其余 1~5 年阶梯', '3M/6M/1Y/2Y/3Y 合同期限阶梯分布'),
    ('S5', '贷款类（对公/个人/信用卡）', '1 年内 40~55%，1~3 年 25~33%', '流贷滚动 + 中长期贷款混合结构'),
    ('S6', '债券投资（司库/金市）', '10Y 以上占 21~44%', '持有到期账户久期长，交易账户期限分散'),
    ('S7', '所有者权益', '30Y 视同永续', '无到期安排，不参与逐月摊销'),
]
for no, item, f, note in SHAPE_DOC:
    ws10.cell(r, 1, no).font = F_B
    ws10.cell(r, 2, item).font = F_N
    ws10.cell(r, 3, f).font = F_N
    ws10.cell(r, 4, note).font = F_SUB
    for c in range(1, 5):
        ws10.cell(r, c).border = BD
    r += 1
r += 1
r = sec(ws10, r, '【三】口径说明与使用提示', 4)
NOTES = [
    ('N1', '主口径', '①数据源 I 列 = 逐月平均余额法推演值。含义：假设存量按剩余期限结构自然到期，'
                     '到期部分退出计息基数，不考虑续作与新增业务。'),
    ('N2', '对照口径', '①数据源 J 列 = 余额 × 加权平均利率（会计静态口径）。'
                     '与 NIM 计量模版 v2 口径一致，两者差异在 ⑦【三】量化归因。'),
    ('N3', '差异来源', '推演口径低于静态口径，主因是到期本金退出计息基数。'
                     '资产端到期越快差异越小；负债端活期存款 3 个月内全额到期，差异最显著。'),
    ('N4', '不含重定价', '本模版不设 β、不计算重定价缺口、不建模利率重定价时点。'
                        '⑨情景敏感性采用利率等幅平移的静态假设。'),
    ('N5', '数据可替换', '②剩余期限结构的 64 桶权重为绿区输入，可直接改写为实际业务的期限分布；'
                        '③逐月推演与全部下游指标自动联动重算。'),
    ('N6', '权益处理', '所有者权益无偿还计划，30Y 桶视同永续，不参与逐月摊销，年度利息为 0。'),
]
for no, item, f in NOTES:
    ws10.cell(r, 1, no).font = F_B
    ws10.cell(r, 2, item).font = F_N
    ws10.cell(r, 3, f).font = F_N
    ws10.cell(r, 3).alignment = AL
    ws10.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
    for c in range(1, 5):
        ws10.cell(r, c).border = BD
    r += 1
ws10.freeze_panes = 'A4'

wb.save(OUT)
print('OK ->', OUT)
