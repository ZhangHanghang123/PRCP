# -*- coding: utf-8 -*-
"""NIM 模版：Python 独立复算 + pycel 端到端验证"""
import sys
from pycel import ExcelCompiler
import openpyxl

XL = 'C:/银行经营/PRCP/docs/v2/NIM计量模版_v2_真实数据.xlsx'
SRC = 'C:/银行经营/PRCP/docs/v2/prcp_basic_20251231.xlsx'

ws = openpyxl.load_workbook(SRC, data_only=True)['基础数据']
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


rows = []
TOTAL = {}
for r in range(4, 44):
    code = ws.cell(r, 3).value
    if not code:
        continue
    name = str(ws.cell(r, 4).value or '').strip()
    cat = ws.cell(r, 8).value
    bal = (ws.cell(r, C_CURBAL).value or 0) / 1e8
    if int(ws.cell(r, 7).value or 0) != 1:
        if code in ('S01000000000000', 'S02000000000000', 'S03000000000000'):
            TOTAL[cat] = bal
        continue
    if code == 'S03000000000000':
        TOTAL['EQUITY'] = bal
    rate = (ws.cell(r, C_RATE).value or 0) / 100.0
    iy = bal * rate
    dist = []
    for i in range(64):
        v = ws.cell(r, C_REMAIN0 + i).value
        dist.append((v if isinstance(v, (int, float)) else 0.0) / 1e8)
    tot = sum(dist)
    beta = min(0.98, max(0.10, sum(dist[:12]) / tot)) if tot > 0 else 0.0
    ln = classify(name, cat)
    ea = ('EA' if rate > 0 else 'NEA') if cat == 'ASSET' else '-'
    rows.append(dict(code=code, name=name, cat=cat, bal=bal, rate=rate, iy=iy,
                     dist=dist, beta=beta, line=ln, ea=ea,
                     w12=sum(dist[:12])))

A = [x for x in rows if x['cat'] == 'ASSET']
L = [x for x in rows if x['cat'] == 'LIAB']
EA_A = [x for x in A if x['ea'] == 'EA']
NEA_A = [x for x in A if x['ea'] == 'NEA']

II = sum(x['iy'] for x in EA_A)
IE = sum(x['iy'] for x in L)
NII = II - IE
EA = sum(x['bal'] for x in EA_A)
NEA = sum(x['bal'] for x in NEA_A)
TA = sum(x['bal'] for x in A)
TL = sum(x['bal'] for x in L)
TE = TOTAL.get('EQUITY', 0)
YLD = II / EA
CST = IE / TL
NIS = YLD - CST
NIM = NII / EA
K = TL / EA
DRAG = NIS - NIM
MISCON = NIS * K
MISERR = MISCON - NIM
AB = sum(x['bal'] * x['beta'] for x in EA_A)   # 与 Excel 一致：只算生息资产(EA)
LB = sum(x['bal'] * x['beta'] for x in L)
RG = AB - LB
demand = sum(x['bal'] for x in L if x['line'] == '活期存款')
term = sum(x['bal'] for x in L if x['line'] == '定期存款')
dmd_ratio = demand / (demand + term)

print('=' * 88)
print('Python 独立复算（直接读 prcp_basic_20251231.xlsx）')
print('=' * 88)
print(f'  生息资产（EA，{len(EA_A)} 个）        : {EA:>14,.2f} 亿元')
print(f'  非生息资产（NEA，{len(NEA_A)} 个）     : {NEA:>14,.2f} 亿元')
print(f'  资产端合计（= 总资产）               : {TA:>14,.2f} 亿元')
print(f'  计息负债（{len(L)} 个）                : {TL:>14,.2f} 亿元')
print(f'  所有者权益                           : {TE:>14,.2f} 亿元')
print(f'  利息收入                             : {II:>14,.2f} 亿元/年')
print(f'  利息支出                             : {IE:>14,.2f} 亿元/年')
print(f'  利息净收入 NII                       : {NII:>14,.2f} 亿元/年')
print(f'  生息资产收益率                       : {YLD*100:>14.4f}%')
print(f'  计息负债成本率                       : {CST*100:>14.4f}%')
print(f'  ★ 净利差 NIS                         : {NIS*100:>14.4f}%')
print(f'  规模调整系数 k = TL ÷ EA             : {K*100:>14.4f}%')
print(f'  ★ 净息差 NIM                         : {NIM*100:>14.4f}%')
print(f'  规模错配拖累（NIS − NIM）             : {DRAG*100:>14.4f} 个百分点')
print(f'  ★ 正确关系 收益率 − 成本率×k = NIM    : {YLD-CST*K:.10f} vs {NIM:.10f}  差 {abs(YLD-CST*K-NIM):.2e}')
print(f'  ⚠ 误区 NIS × k                      : {MISCON*100:.6f}%  偏差 {MISERR*100:+.4f}pp')
print(f'  存款活期化率                         : {dmd_ratio*100:>14.4f}%')
print(f'  资产敞口 A_β / 负债敞口 L_β          : {AB:>12,.2f} / {LB:,.2f}')
print(f'  重定价缺口 RG                        : {RG:>14,.2f} 亿元')

# 多口径 NIM
DEN = {'口径1 生息资产(监管)': EA, '口径2 资产端合计': TA,
       '口径3 计息负债': TL, '口径4 总资产(+权益)': TA + TE, '口径5 资产端(RWA近似)': TA}
print()
print('  多口径 NIM：')
for k, v in DEN.items():
    print(f'    {k:<24} 分母={v:>14,.2f}  NIM={NII/v*100:>8.4f}%  差={(NII/v-NIM)*100:>+8.4f}pp')

# 杜邦三分解
eff = EA / TA
nim_dup = YLD - CST * K
print()
print(f'  分解复核：资产端 − 负债端 = 收益率 − 成本率×k')
print(f'    = {YLD*100:.4f}% − {CST*100:.4f}% × {K*100:.4f}% = {nim_dup*100:.6f}%  应等于 NIM {NIM*100:.6f}%  差 {abs(nim_dup-NIM):.2e}')
print(f'  （附）总资产口径净息差 = NIM × 资产效率 = {NIM*eff*100:.6f}%')

print()
print('=' * 88)
print('pycel 公式求值')
print('=' * 88)
exc = ExcelCompiler(filename=XL)


def V(sh, cell):
    try:
        return exc.evaluate(f"'{sh}'!{cell}")
    except Exception as e:
        return f'ERR:{type(e).__name__}'


wb = openpyxl.load_workbook(XL)
CASES = [
    ('① Σ 当前余额', '①分母口径数据源', 'F28', sum(x['bal'] for x in rows), 1e-4),
    ('① Σ 年度利息', '①分母口径数据源', 'H28', sum(x['iy'] for x in rows), 1e-4),
    ('① Σ 1年内到期', '①分母口径数据源', 'L28', sum(x['w12'] for x in rows), 1e-4),
    ('② Σ 1年内到期', '②期限分布', 'BO28', sum(x['w12'] for x in rows), 1e-4),
    ('② Σ 分布合计', '②期限分布', 'BP28', sum(sum(x['dist']) for x in rows), 1e-4),
    ('③ 资产端合计', '③生息资产界定', 'E20', TA, 1e-4),
    ('★ ③ 生息资产', '③生息资产界定', 'E21', EA, 1e-4),
    ('③ 生息资产年度利息', '③生息资产界定', 'G21', II, 1e-4),
    ('③ 生息资产收益率', '③生息资产界定', 'F21', YLD, 1e-10),
    ('③ 非生息资产', '③生息资产界定', 'E22', NEA, 1e-4),
    ('③ 校验(资产-总资产)', '③生息资产界定', 'E26', 0.0, 1e-4),
    ('⑤ 误区 NIS×k', '⑤NIM计量表', 'B27', MISCON, 1e-10),
    ('⑤ 误区偏差', '⑤NIM计量表', 'B28', MISERR, 1e-10),
    ('④ 计息负债合计', '④计息负债明细', 'E11', TL, 1e-4),
    ('④ 年度利息支出', '④计息负债明细', 'G11', IE, 1e-4),
    ('④ 成本率', '④计息负债明细', 'F11', CST, 1e-10),
    ('④ 活期化率', '④计息负债明细', 'E18', dmd_ratio, 1e-10),
    ('⑤ 生息资产(分母)', '⑤NIM计量表', 'B5', EA, 1e-4),
    ('⑤ 非生息资产', '⑤NIM计量表', 'B6', NEA, 1e-4),
    ('⑤ 资产端合计', '⑤NIM计量表', 'B7', TA, 1e-4),
    ('⑤ 所有者权益', '⑤NIM计量表', 'B8', TE, 1e-4),
    ('⑤ 计息负债', '⑤NIM计量表', 'B9', TL, 1e-4),
    ('⑤ 利息收入', '⑤NIM计量表', 'B12', II, 1e-4),
    ('⑤ 利息支出', '⑤NIM计量表', 'B13', IE, 1e-4),
    ('⑤ NII', '⑤NIM计量表', 'B16', NII, 1e-4),
    ('★ ⑤ NIM', '⑤NIM计量表', 'B17', NIM, 1e-10),
    ('⑤ 生息资产收益率', '⑤NIM计量表', 'B18', YLD, 1e-10),
    ('⑤ 计息负债成本率', '⑤NIM计量表', 'B19', CST, 1e-10),
    ('★ ⑤ NIS', '⑤NIM计量表', 'B20', NIS, 1e-10),
    ('⑤ 规模调整系数', '⑤NIM计量表', 'B24', K, 1e-10),
    ('⑤ 校验 收益率-成本率×k=NIM', '⑤NIM计量表', 'B25', 0.0, 1e-6),
    ('⑤ NIS − NIM', '⑤NIM计量表', 'B26', DRAG, 1e-10),
    ('⑤ 多口径1', '⑤NIM计量表', 'B31', NIM, 1e-10),
    ('⑤ 多口径2', '⑤NIM计量表', 'B32', NII / TA, 1e-10),
    ('⑤ 多口径3', '⑤NIM计量表', 'B33', NII / TL, 1e-10),
    ('⑤ 多口径4', '⑤NIM计量表', 'B34', NII / (TA + TE), 1e-10),
    ('⑤ 多口径5', '⑤NIM计量表', 'B35', NII / TA, 1e-10),
    ('⑤ 口径差(1-2)', '⑤NIM计量表', 'B36', NIM - NII / TA, 1e-10),
    ('⑤ 资产效率', '⑤NIM计量表', 'B39', eff, 1e-10),
    ('⑤ 资产端贡献', '⑤NIM计量表', 'B41', YLD, 1e-10),
    ('⑤ 负债端贡献', '⑤NIM计量表', 'B42', CST * K, 1e-10),
    ('⑤ 分解复核', '⑤NIM计量表', 'B43', nim_dup, 1e-9),
    ('⑤ 总资产口径息差', '⑤NIM计量表', 'B45', NIM * eff, 1e-10),
    ('⑤ 分解校验', '⑤NIM计量表', 'B44', 0.0, 1e-6),
]
print(f"{'检查项':<26}{'sheet!cell':<30}{'Excel(pycel)':>20}{'Python':>20}{'差值':>12}")
print('-' * 88)
fails = []
for lab, sh, cell, want, tol in CASES:
    got = V(sh, cell)
    if not isinstance(got, (int, float)):
        print(f'{lab:<26}{sh+"!"+cell:<30}{str(got):>20}')
        fails.append((lab, sh, cell, 'NON_NUM', got))
        continue
    d = abs(got - want)
    ok = d <= tol
    print(f'{lab:<26}{sh+"!"+cell:<30}{got:>20.8f}{want:>20.8f}{d:>12.2e}{"" if ok else "  <-- MISMATCH"}')
    if not ok:
        fails.append((lab, sh, cell, got, want))

print()
print('-' * 88)
print('勾稽校验（校验 1~9 应为 0）')
print('-' * 88)
w5 = wb['⑤NIM计量表']
for k in range(9):
    rr = 56 + k
    lab = w5.cell(rr, 1).value
    if lab and '校验' in str(lab):
        v = V('⑤NIM计量表', f'B{rr}')
        ok = isinstance(v, (int, float)) and abs(v) < 1e-4
        print(f'  {str(lab).strip()[:46]:<48} B{rr:<3} = {v!s:>18}  {"PASS" if ok else "CHECK"}')
        if not ok:
            fails.append((str(lab)[:18], '⑤NIM计量表', f'B{rr}', v, 0.0))

print()
print('-' * 88)
print('情景敏感性（7 档平行移动）')
print('-' * 88)
print(f"{'情景':<22}{'ΔNIM(Excel)':>16}{'ΔNIM(Python)':>16}{'情景后NIM':>13}{'ΔNII':>14}")
SC0 = 6
for i, bp in enumerate([250, 100, 50, 0, -50, -100, -250]):
    rr = SC0 + i
    dnii = (-bp / 10000 * AB) - (-bp / 10000 * LB)
    snim = (NII + dnii) / EA
    dnim = snim - NIM
    got_h = V('⑦情景敏感性', f'H{rr}')
    got_e = V('⑦情景敏感性', f'E{rr}')
    got_g = V('⑦情景敏感性', f'G{rr}')
    dh = abs(got_h - dnim) if isinstance(got_h, (int, float)) else 999
    de = abs(got_e - dnii) if isinstance(got_e, (int, float)) else 999
    print(f"{('Δr=%+dbp' % bp):<22}{got_h*100:>15.4f}%{dnim*100:>15.4f}%{got_g*100:>12.4f}%{got_e:>14,.2f}{'' if dh < 1e-9 and de < 1e-5 else '  MISMATCH'}")
    if dh >= 1e-9:
        fails.append((f'ΔNIM{bp}', '⑦情景敏感性', f'H{rr}', got_h, dnim))
    if de >= 1e-5:
        fails.append((f'ΔNII{bp}', '⑦情景敏感性', f'E{rr}', got_e, dnii))

print()
print('-' * 88)
print('分母口径切换')
print('-' * 88)
DEN_ORD = [('口径1 生息资产(监管)', EA), ('口径2 资产端合计', TA),
           ('口径3 总资产(+权益)', TA + TE), ('口径4 RWA近似', TA)]
for k, (name, dv) in enumerate(DEN_ORD):
    rr = 18 + k
    got = V('⑦情景敏感性', f'D{rr}')
    gd = V('⑦情景敏感性', f'E{rr}')
    want = NII / dv
    ok = isinstance(got, (int, float)) and abs(got - want) < 1e-10
    print(f'  {name:<24} 分母={dv:>14,.0f}  NIM={got*100 if isinstance(got,(int,float)) else got:>9.4f}%  Δ={gd*100 if isinstance(gd,(int,float)) else gd:>+9.4f}pp  {"PASS" if ok else "CHECK"}')
    if isinstance(got, (int, float)) and isinstance(gd, (int, float)):
        print(f'      Excel NIM={got*100:.6f}%   Python={want*100:.6f}%   ΔNIM={gd*100:+.6f}pp')
    if not ok:
        fails.append((name, '⑦情景敏感性', f'D{rr}', got, want))

print()
print('-' * 88)
print('监管判定')
print('-' * 88)
for rr in range(67, 74):
    lab = w5.cell(rr, 1).value
    if lab:
        print(f'  {str(lab).strip()[:40]:<42} B{rr} = {V("⑤NIM计量表", f"B{rr}")}')
w7 = wb['⑦情景敏感性']
for rr in range(24, 31):
    lab = w7.cell(rr, 1).value
    if lab:
        print(f'  {str(lab).strip()[:40]:<42} B{rr} = {V("⑦情景敏感性", f"B{rr}")}')

print()
print('=' * 88)
if fails:
    print(f'❌ {len(fails)} 项不一致：')
    for f in fails:
        print('   ', f)
    sys.exit(1)
print(f'✅ 全部 {len(CASES)} 项关键单元格 + 勾稽 + 情景 + 口径，pycel 与 Python 独立复算一致')
print('=' * 88)