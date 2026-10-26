# -*- coding: utf-8 -*-
"""NII v2 模版：Python 独立复算 + pycel 端到端公式验证"""
import sys
from pycel import ExcelCompiler
import openpyxl

XL = 'C:/银行经营/PRCP/docs/v2/NII计量模版_v2_真实数据.xlsx'
SRC = 'C:/银行经营/PRCP/docs/v2/prcp_basic_20251231.xlsx'

# ---------- 1) Python 侧独立复算（直接读参照物，不读生成的 Excel） ----------
ws = openpyxl.load_workbook(SRC, data_only=True)['基础数据']
BUCKETS = [(f'{m}M', m / 12.0) for m in range(1, 61)] + \
          [('10Y', 10.0), ('15Y', 15.0), ('20Y', 20.0), ('30Y', 30.0)]
C_REMAIN0, C_CURBAL, C_RATE, C_INT = 76, 140, 142, 143


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


ATYPE = {'信贷资产': '信贷', '债券投资': '投资', '金融市场': '金融', '非生息资产': '非息',
         '外币资产': '外币', '活期存款': '活期', '定期存款': '定期',
         '市场化负债': '同业', '外币负债': '外币', '权益': '权益'}
rows = []
for r in range(4, 44):
    code = ws.cell(r, 3).value
    if not code or int(ws.cell(r, 7).value or 0) != 1:
        continue
    name = str(ws.cell(r, 4).value or '').strip()
    cat = ws.cell(r, 8).value
    bal = (ws.cell(r, C_CURBAL).value or 0) / 1e8
    rate = (ws.cell(r, C_RATE).value or 0) / 100.0
    im = (ws.cell(r, C_INT).value or 0) / 1e8
    dist = []
    for i in range(64):
        v = ws.cell(r, C_REMAIN0 + i).value
        dist.append((v if isinstance(v, (int, float)) else 0.0) / 1e8)
    tot = sum(dist)
    beta = min(0.98, max(0.10, sum(dist[:12]) / tot)) if tot > 0 else 0.0
    ln = classify(name, cat)
    rows.append(dict(code=code, name=name, cat=cat, bal=bal, rate=rate, im=im,
                     iy=im * 12, dist=dist, beta=beta, line=ln, atype=ATYPE[ln]))

A = [x for x in rows if x['cat'] == 'ASSET']
L = [x for x in rows if x['cat'] == 'LIAB']
E = [x for x in rows if x['cat'] == 'EQUITY']
A_EARN = [x for x in A if x['rate'] > 0]
A_ZERO = [x for x in A if x['rate'] == 0]

II = sum(x['iy'] for x in A_EARN)
IE = sum(x['iy'] for x in L)
NII = II - IE
AEA = sum(x['bal'] for x in A_EARN)
ANZ = sum(x['bal'] for x in A_ZERO)
LEA = sum(x['bal'] for x in L)
IIM = sum(x['im'] for x in A) - sum(x['im'] for x in L)
A_BETA = sum(x['bal'] * x['beta'] for x in A)
L_BETA = sum(x['bal'] * x['beta'] for x in L)
RG = A_BETA - L_BETA

print('=' * 84)
print('Python 独立复算（直接读 prcp_basic_20251231.xlsx，不读生成文件）')
print('=' * 84)
print(f'  生息资产（利率>0，{len(A_EARN)} 个）  : {AEA:>14,.2f} 亿元')
print(f'  已剔除非生息资产（{len(A_ZERO)} 个）   : {ANZ:>14,.2f} 亿元')
print(f'  计息负债（{len(L)} 个）              : {LEA:>14,.2f} 亿元')
print(f'  利息收入                            : {II:>14,.2f} 亿元/年')
print(f'  利息支出                            : {IE:>14,.2f} 亿元/年')
print(f'  ★ NII                               : {NII:>14,.2f} 亿元/年')
print(f'  月度 NII                            : {IIM:>14,.4f} 亿元/月')
print(f'  生息资产收益率                      : {II/AEA*100:>14.4f}%')
print(f'  计息负债成本率                      : {IE/LEA*100:>14.4f}%')
print(f'  净利差 NIS                          : {(II/AEA-IE/LEA)*100:>14.4f}%')
print(f'  ★ NIM                               : {NII/AEA*100:>14.4f}%')
print(f'  存款活期化率                        : {sum(x["bal"] for x in L if x["atype"]=="活期")/sum(x["bal"] for x in L if x["atype"] in ("活期","定期"))*100:>14.4f}%')
print(f'  资产敞口 A_β                        : {A_BETA:>14,.2f} 亿元')
print(f'  负债敞口 L_β                        : {L_BETA:>14,.2f} 亿元')
print(f'  ★ 重定价缺口 RG                     : {RG:>14,.2f} 亿元')
print(f'  NII 利率弹性                        : {-RG/AEA*100:>14.4f}%')

# ---------- 2) pycel 端到端 ----------
print()
print('=' * 84)
print('pycel 公式求值')
print('=' * 84)
exc = ExcelCompiler(filename=XL)


def V(sh, cell):
    try:
        return exc.evaluate(f"'{sh}'!{cell}")
    except Exception as e:
        return f'ERR:{type(e).__name__}'


# 定位行号
wb2 = openpyxl.load_workbook(XL)
w6 = wb2['⑥NII计量表']
ROW = {}
for rr in range(1, 70):
    v = w6.cell(rr, 1).value
    if v and isinstance(v, str):
        ROW[v.strip()[:20]] = rr
w7 = wb2['⑦期限结构与重定价']
ROW7 = {}
for rr in range(1, 70):
    v = w7.cell(rr, 1).value
    if v and isinstance(v, str) and ('敞口' in v or '缺口' in v):
        ROW7[v.strip()[:14]] = rr

CASES = [
    ('①数据源 Σ 当前余额', '①数据源', 'F28', sum(x['bal'] for x in rows), 1e-4),
    ('①数据源 Σ 月度利息', '①数据源', 'H28', sum(x['im'] for x in rows), 1e-4),
    ('①数据源 Σ 年度利息', '①数据源', 'I28', sum(x['iy'] for x in rows), 1e-4),
    ('②期限分布 Σ 1年内到期', '②期限分布', 'BO28', sum(sum(x['dist'][:12]) for x in rows), 1e-4),
    ('②期限分布 Σ 分布合计', '②期限分布', 'BP28', sum(sum(x['dist']) for x in rows), 1e-4),
    ('②期限分布 Σ 当前余额', '②期限分布', 'BQ28', sum(x['bal'] for x in rows), 1e-4),
    ('④利息收入合计', '④利息收入明细', 'E18', AEA, 1e-4),
    ('④年度利息合计', '④利息收入明细', 'G18', II, 1e-4),
    ('④非生息资产合计', '④利息收入明细', 'E23', ANZ, 1e-4),
    ('⑤利息支出合计 余额', '⑤利息支出明细', 'E11', LEA, 1e-4),
    ('⑤年度利息合计', '⑤利息支出明细', 'G11', IE, 1e-4),
    ('⑥ 生息资产', '⑥NII计量表', 'B5', AEA, 1e-4),
    ('⑥ 非生息（已剔除）', '⑥NII计量表', 'B6', ANZ, 1e-4),
    ('⑥ 计息负债', '⑥NII计量表', 'B7', LEA, 1e-4),
    ('⑥ 存款类负债', '⑥NII计量表', 'B8', sum(x['bal'] for x in L if x['atype'] in ('活期', '定期')), 1e-4),
    ('⑥ 市场化负债', '⑥NII计量表', 'B9', sum(x['bal'] for x in L if x['atype'] == '同业'), 1e-4),
    ('⑥ 所有者权益', '⑥NII计量表', 'B11', sum(x['bal'] for x in E), 1e-4),
    ('⑥ 利息收入', '⑥NII计量表', 'B14', II, 1e-4),
    ('⑥ 利息支出', '⑥NII计量表', 'B15', IE, 1e-4),
    ('⑥ 月度校验(资产)', '⑥NII计量表', 'B16', sum(x['im'] for x in A) * 12, 1e-4),
    ('★ ⑥ NII', '⑥NII计量表', 'B20', NII, 1e-4),
    ('⑥ 月度 NII', '⑥NII计量表', 'B21', IIM, 1e-4),
    ('⑥ 生息资产收益率', '⑥NII计量表', 'B24', II / AEA, 1e-10),
    ('⑥ 计息负债成本率', '⑥NII计量表', 'B25', IE / LEA, 1e-10),
    ('⑥ 净利差 NIS', '⑥NII计量表', 'B26', II / AEA - IE / LEA, 1e-10),
    ('★ ⑥ NIM', '⑥NII计量表', 'B27', NII / AEA, 1e-10),
    ('⑥ 信贷资产余额', '⑥NII计量表', 'B30', sum(x['bal'] for x in rows if x['atype'] == '信贷'), 1e-4),
    ('⑥ 存款余额', '⑥NII计量表', 'B31', sum(x['bal'] for x in L if x['atype'] in ('活期', '定期')), 1e-4),
    ('⑥ 存贷比', '⑥NII计量表', 'B32', sum(x['bal'] for x in rows if x['atype'] == '信贷') / LEA, 1e-10),
    ('⑥ 存款活期化率', '⑥NII计量表', 'B34', sum(x['bal'] for x in L if x['atype'] == '活期') / sum(x['bal'] for x in L if x['atype'] in ('活期', '定期')), 1e-10),
    ('⑦ 资产敞口 A_β', '⑦期限结构与重定价', 'E30', A_BETA, 1e-4),
    ('⑦ 负债敞口 L_β', '⑦期限结构与重定价', 'E31', L_BETA, 1e-4),
    ('★ ⑦ 重定价缺口 RG', '⑦期限结构与重定价', 'E32', RG, 1e-4),
    ('⑦ 每 10bp 影响', '⑦期限结构与重定价', 'E33', -RG * 0.001, 1e-6),
    ('⑦ NII 利率弹性', '⑦期限结构与重定价', 'E34', -RG / AEA, 1e-10),
    ('⑧ 资产端利息加总', '⑧NII结构拆解', 'B28', II, 1e-4),
    ('⑧ 负债端利息加总', '⑧NII结构拆解', 'B29', IE, 1e-4),
    ('★ ⑧ NII（条线加总）', '⑧NII结构拆解', 'B30', NII, 1e-4),
    ('⑧ 校验差额（应 0）', '⑧NII结构拆解', 'B32', 0.0, 1e-4),
]

print(f"{'检查项':<26}{'sheet!cell':<28}{'Excel(pycel)':>20}{'Python':>20}{'差值':>12}")
print('-' * 84)
fails = []
for lab, sh, cell, want, tol in CASES:
    got = V(sh, cell)
    if not isinstance(got, (int, float)):
        print(f'{lab:<26}{sh+"!"+cell:<28}{str(got):>20}')
        fails.append((lab, sh, cell, 'NON_NUM', got))
        continue
    d = abs(got - want)
    ok = d <= tol
    print(f'{lab:<26}{sh+"!"+cell:<28}{got:>20.6f}{want:>20.6f}{d:>12.2e}{"" if ok else "  <-- MISMATCH"}')
    if not ok:
        fails.append((lab, sh, cell, got, want))

print()
print('-' * 84)
print('勾稽校验单元格（校验 1~9 应为 0）')
print('-' * 84)
for k in range(1, 10):
    lab = w6.cell(36 + k, 1).value
    if lab and '校验' in str(lab):
        v = V('⑥NII计量表', f'B{36+k}')
        ok = isinstance(v, (int, float)) and abs(v) < 1e-4
        print(f'  {str(lab).strip()[:44]:<46} B{36+k:<3} = {v!s:>20}  {"PASS" if ok else "CHECK"}')
        if not ok:
            fails.append((str(lab)[:20], '⑥NII计量表', f'B{36+k}', v, 0.0))

print()
print('-' * 84)
print('情景敏感性（7 档平行移动）')
print('-' * 84)
print(f"{'情景':<22}{'ΔNII(Excel)':>16}{'ΔNII(Python)':>16}{'情景后NII':>14}{'情景后NIM':>12}")
SC0 = 6
for i, bp in enumerate([250, 100, 50, 0, -50, -100, -250]):
    rr = SC0 + i
    dnii = (-bp / 10000 * A_BETA) - (-bp / 10000 * L_BETA)
    got = V('⑨情景敏感性', f'E{rr}')
    snii = V('⑨情景敏感性', f'F{rr}')
    snim = V('⑨情景敏感性', f'H{rr}')
    diff = abs(got - dnii) if isinstance(got, (int, float)) else 999
    nim_p = (NII + dnii) / AEA
    print(f"{('Δr=%+dbp' % bp):<22}{got:>16.4f}{dnii:>16.4f}{snii:>14,.2f}{snim*100:>11.4f}%{'' if diff < 1e-5 else '  MISMATCH'}")
    if diff >= 1e-5:
        fails.append((f'情景{bp}', '⑨情景敏感性', f'E{rr}', got, dnii))

print()
print('-' * 84)
print('监管判定')
print('-' * 84)
for rr in range(48, 56):
    lab = w6.cell(rr, 1).value
    if lab:
        print(f'  {str(lab).strip()[:40]:<42} B{rr} = {V("⑥NII计量表", f"B{rr}")}')
w9 = wb2['⑨情景敏感性']
for rr in range(45, 56):
    lab = w9.cell(rr, 1).value
    if lab and ('判定' in str(lab) or '敏感度' in str(lab) or '跌破' in str(lab)):
        print(f'  {str(lab).strip()[:40]:<42} C{rr} = {V("⑨情景敏感性", f"C{rr}")}')

print()
print('=' * 84)
if fails:
    print(f'❌ {len(fails)} 项不一致：')
    for f in fails:
        print('   ', f)
    sys.exit(1)
print(f'✅ 全部 {len(CASES)} 项关键单元格 + 勾稽 + 情景，pycel 求值与 Python 独立复算一致')
print('=' * 84)