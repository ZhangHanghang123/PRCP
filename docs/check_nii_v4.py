# -*- coding: utf-8 -*-
"""v4 验证：Python 独立复算 vs pycel 真实求值，逐项比对。"""
import openpyxl
from openpyxl.utils import get_column_letter as L
from pycel import ExcelCompiler

XL = 'v2/NII计量模版_v4_逐月利息推演.xlsx'
import build_nii_v4 as B

acc = B.ACCOUNTS
exc = ExcelCompiler(filename=XL)
wb = openpyxl.load_workbook(XL)
w1, w2, w3 = wb['①数据源'], wb['②剩余期限结构'], wb['③逐月利息推演']
w7, w8 = wb['⑦NII计量表'], wb['⑧NII结构拆解']

D0 = 4
TR0 = 4
TR3_0 = 4


def V(sh, cell):
    try:
        return exc.evaluate(f"'{sh}'!{cell}")
    except Exception as e:
        return f'ERR:{type(e).__name__}:{str(e)[:70]}'


# ========== Python 侧独立复算 ==========
rows = []
for a in acc:
    w = B.SHAPE_W[a['code']]
    amt = [a['bal'] * x for x in w]          # 每桶金额
    bal_m = a['bal']
    months = []
    for m in range(12):
        eom = bal_m - amt[m]
        mi = (bal_m + eom) / 2 * a['rate'] / 12
        months.append((bal_m, amt[m], eom, mi))
        bal_m = eom
    yi = sum(x[3] for x in months)
    base = sum((x[0] + x[2]) / 2 for x in months)
    wal = sum(x * t for x, t in zip(w, [b[1] for b in B.BUCKETS])) / sum(w) if sum(w) else 0
    rows.append(dict(
        code=a['code'], name=a['name'], cat=a['cat'], line=a['line'], atype=a['atype'],
        bal=a['bal'], rate=a['rate'], yi=yi, cmp_=a['bal'] * a['rate'],
        e12=bal_m, base=base, wal=wal,
        w12=sum(amt[:12]), s1=sum(amt[0:3]), s2=sum(amt[3:12]),
        s3=sum(amt[12:36]), s4=sum(amt[36:60]), s5=sum(amt[60:64]),
        months=months))

A = [x for x in rows if x['cat'] == 'ASSET']
L_ = [x for x in rows if x['cat'] == 'LIAB']
E = [x for x in rows if x['cat'] == 'EQUITY']
EA = sum(x['bal'] for x in A if x['rate'] > 0)
NEA = sum(x['bal'] for x in A if x['rate'] == 0)
TA = EA + NEA
TL = sum(x['bal'] for x in L_)
EQ = sum(x['bal'] for x in E)
II = sum(x['yi'] for x in A)
IE = sum(x['yi'] for x in L_)
II_C = sum(x['cmp_'] for x in A)
IE_C = sum(x['cmp_'] for x in L_)
NII = II - IE
NII_C = II_C - IE_C
NIM = NII / EA
NIM_C = NII_C / EA
YLD = II / EA
CST = IE / TL
NIS = YLD - CST
K = TL / EA

print('=' * 78)
print('Python 侧独立复算结果')
print('=' * 78)
print(f'  生息资产 EA          : {EA:>16,.2f}')
print(f'  非生息资产 NEA       : {NEA:>16,.2f}')
print(f'  资产端合计 TA        : {TA:>16,.2f}')
print(f'  计息负债 TL          : {TL:>16,.2f}')
print(f'  所有者权益 EQ        : {EQ:>16,.2f}')
print(f'  利息收入(推演) II    : {II:>16,.2f}')
print(f'  利息支出(推演) IE    : {IE:>16,.2f}')
print(f'  ★ NII (推演)         : {NII:>16,.2f}')
print(f'  利息收入(静态)       : {II_C:>16,.2f}')
print(f'  利息支出(静态)       : {IE_C:>16,.2f}')
print(f'  对照 NII (静态)      : {NII_C:>16,.2f}')
print(f'  生息资产收益率 YLD   : {YLD*100:>15.4f}%')
print(f'  计息负债成本率 CST   : {CST*100:>15.4f}%')
print(f'  净利差 NIS           : {NIS*100:>15.4f}%')
print(f'  ★ NIM (推演)         : {NIM*100:>15.4f}%')
print(f'  对照 NIM (静态)      : {NIM_C*100:>15.4f}%')
print(f'  资产端差异率         : {(II/II_C-1)*100:>15.4f}%')
print(f'  负债端差异率         : {(IE/IE_C-1)*100:>15.4f}%')
wa = sum(x['bal'] * x['wal'] for x in A) / TA
wl = sum(x['bal'] * x['wal'] for x in L_) / TL
print(f'  资产端 WAL           : {wa:>16.4f} 年  （全资产端口径）')
print(f'  负债端 MAL           : {wl:>16.4f} 年')
print(f'  期限错配             : {wa-wl:>16.4f} 年')

# ========== pycel 关键单元格比对 ==========
print()
print('=' * 78)
print('pycel 端到端公式验证')
print('=' * 78)
CASES = [
    ('① Σ年度利息(推演)', '①数据源', 'I28', II + IE, 1e-4),
    ('① Σ年度利息(静态)', '①数据源', 'J28', II_C + IE_C, 1e-4),
    ('① Σ1年内到期', '①数据源', 'K28', sum(x['w12'] for x in rows), 1e-4),
    ('① Σ年计息基数', '①数据源', 'M28', sum(x['base'] for x in rows), 1e-4),
    ('③ Σ推演年度利息', '③逐月利息推演', 'AD28', II + IE, 1e-4),
    ('③ Σ对照年度利息', '③逐月利息推演', 'AE28', II_C + IE_C, 1e-4),
    ('③ ΣM12末余额', '③逐月利息推演', 'AG28', sum(x['e12'] for x in rows), 1e-4),
    ('③ Σ年计息基数', '③逐月利息推演', 'AH28', sum(x['base'] for x in rows), 1e-4),
    ('② 权重合计均值', '②剩余期限结构', 'BP28', 1.0, 1e-9),
    ('② 权重校验差', '②剩余期限结构', 'BX28', 0.0, 1e-9),
    ('② Σ当前余额', '②剩余期限结构', 'BQ28', TA + TL + EQ, 1e-4),
    ('② Σ1年内金额', '②剩余期限结构', 'BR28', sum(x['w12'] for x in rows), 1e-4),
    ('② 1M~3M 资产端', '②剩余期限结构', 'BS31', sum(x['s1'] for x in A), 1e-4),
    ('② 4M~12M 资产端', '②剩余期限结构', 'BT31', sum(x['s2'] for x in A), 1e-4),
    ('② 1Y~3Y 资产端', '②剩余期限结构', 'BU31', sum(x['s3'] for x in A), 1e-4),
    ('② 3Y~5Y 资产端', '②剩余期限结构', 'BV31', sum(x['s4'] for x in A), 1e-4),
    ('② 5Y+ 资产端', '②剩余期限结构', 'BW31', sum(x['s5'] for x in A), 1e-4),
    ('⑤ 利息收入合计', '⑤利息收入明细', 'G18', II, 1e-4),
    ('⑤ 对照利息收入', '⑤利息收入明细', 'H18', II_C, 1e-4),
    ('⑥ 利息支出合计', '⑥利息支出明细', 'G11', IE, 1e-4),
    ('⑥ 对照利息支出', '⑥利息支出明细', 'H11', IE_C, 1e-4),
    ('⑦ 生息资产', '⑦NII计量表', 'B5', EA, 1e-4),
    ('⑦ 资产端合计', '⑦NII计量表', 'B7', TA, 1e-4),
    ('⑦ 计息负债', '⑦NII计量表', 'B9', TL, 1e-4),
    ('⑦ 利息收入(推演)', '⑦NII计量表', 'B12', II, 1e-4),
    ('⑦ 利息支出(推演)', '⑦NII计量表', 'B13', IE, 1e-4),
    ('⑦ 利息收入(静态)', '⑦NII计量表', 'B14', II_C, 1e-4),
    ('⑦ 利息支出(静态)', '⑦NII计量表', 'B15', IE_C, 1e-4),
    ('⑦ 资产端差异率', '⑦NII计量表', 'B23', II / II_C - 1, 1e-9),
    ('⑦ 负债端差异率', '⑦NII计量表', 'B24', IE / IE_C - 1, 1e-9),
    ('⑦ NII(推演)', '⑦NII计量表', 'B27', NII, 1e-4),
    ('⑦ NIM(推演)', '⑦NII计量表', 'B28', NIM, 1e-10),
    ('⑦ 资产收益率', '⑦NII计量表', 'B29', YLD, 1e-10),
    ('⑦ 负债成本率', '⑦NII计量表', 'B30', CST, 1e-10),
    ('⑦ NIS', '⑦NII计量表', 'B31', NIS, 1e-10),
    ('⑦ k 负债支持率', '⑦NII计量表', 'B32', K, 1e-10),
    ('⑦ NII(静态对照)', '⑦NII计量表', 'B33', NII_C, 1e-4),
    ('⑦ NIM(静态对照)', '⑦NII计量表', 'B34', NIM_C, 1e-10),
    ('⑦ 资产端WAL', '⑦NII计量表', 'B43', wa, 1e-9),
    ('⑦ 负债端MAL', '⑦NII计量表', 'B44', wl, 1e-9),
    ('⑧ 条线NII', '⑧NII结构拆解', 'B43', NII, 1e-4),
]

fails = []
for label, sh, cell, want, tol in CASES:
    got = V(sh, cell)
    if not isinstance(got, (int, float)):
        print(f'  {label:<26}{sh+"!"+cell:<22}  非数值: {got}')
        fails.append((label, sh, cell, got, want))
        continue
    diff = abs(got - want)
    ok = diff <= tol
    flag = '' if ok else '  <-- MISMATCH'
    print(f'  {label:<26}{sh+"!"+cell:<22}{got:>18.6f}{want:>18.6f}{diff:>12.2e}{flag}')
    if not ok:
        fails.append((label, sh, cell, got, want))

# 逐账户 I 列一致性
print()
print('— 逐账户校验（①I 列 vs ③AD 列 vs Python）—')
bad = 0
for i, x in enumerate(rows):
    rr = D0 + i
    a = V('①数据源', f'I{rr}')
    b = V('③逐月利息推演', f'AD{rr}')
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        print(f'  R{rr} {x["name"][:14]:<16} 非数值 ①I={a} ③AD={b}')
        bad += 1
        continue
    if abs(a - x['yi']) > 1e-4 or abs(b - x['yi']) > 1e-4 or abs(a - b) > 1e-6:
        print(f'  R{rr} {x["name"][:14]:<16} MISMATCH ①I={a:.4f} ③AD={b:.4f} Py={x["yi"]:.4f}')
        bad += 1
print(f'  逐账户不一致数 = {bad} / {len(rows)}')
if bad:
    fails.append(('逐账户 I/AD 一致性', '', '', bad, 0))

# 勾稽校验（第 6 区）
print()
print('— ⑦ 勾稽校验区 —')
for k in range(11):
    rr = 48 + k
    lab = w7.cell(rr, 1).value
    if not lab:
        continue
    v = V('⑦NII计量表', f'B{rr}')
    print(f'  {str(lab)[:44]:<46} = {v}')

print()
print('=' * 78)
print(f'验证结论：{len(CASES) + 1} 项，失败 {len(fails)} 项')
for f in fails:
    print('  FAIL:', f)
print('=' * 78)
