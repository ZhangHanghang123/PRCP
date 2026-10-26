# -*- coding: utf-8 -*-
"""用 pycel 真实求值 NII_计量模版.xlsx 的公式，与 Python 独立复算逐项比对。"""
import json, sys
from pycel import ExcelCompiler

XL = 'C:/银行经营/PRCP/docs/v2/NII_计量模版.xlsx'
exp = json.load(open('_nii_expected.json', encoding='utf-8'))

print('pycel 加载并编译公式图 ...')
exc = ExcelCompiler(filename=XL)
print('编译完成\n')

def V(sheet, cell):
    try:
        return exc.evaluate(f"'{sheet}'!{cell}")
    except Exception as e:
        return f'ERR:{type(e).__name__}:{e}'

D1, D2, DS = 4, 39, 40
M4 = 'NII计量表'
M5 = 'NII结构拆解'
M6 = 'NII情景敏感性'

# 精确行号（由 build_nii.py 输出 + 关键行定位）
CELLS = [
    ('数据源 Σ 利息收入',        'NII数据源',     f'N{DS}',        exp['sum_ii'],      1e-6),
    ('数据源 Σ 利息支出',        'NII数据源',     f'O{DS}',        exp['sum_ie'],      1e-6),
    ('利息收入明细 合计',        '利息收入明细',   'K26',          exp['sum_ii'],      1e-6),
    ('利息支出明细 合计',        '利息支出明细',   'K20',          exp['sum_ie'],      1e-6),
    ('平均生息资产',            M4,             'B5',           exp['aea'],         1e-6),
    ('其中人民币生息资产',      M4,             'B6',           exp['aea_rmb'],     1e-6),
    ('其中外币生息资产',        M4,             'B7',           exp['aea_fx'],      1e-6),
    ('已剔除非生息资产',        M4,             'B8',           exp['nonearn_a'],    1e-6),
    ('平均计息负债',            M4,             'B9',           exp['lea'],         1e-6),
    ('利息收入合计',            M4,             'B16',          exp['sum_ii'],      1e-6),
    ('利息支出合计',            M4,             'B18',          exp['sum_ie'],      1e-6),
    ('★ NII 计量表 NII',        M4,             'B22',          exp['nii'],         1e-6),
    ('  NII 期末口径',          M4,             'B23',          exp['nii_end'],     1e-6),
    ('  生息资产收益率',        M4,             'B27',          exp['yield_'],      1e-10),
    ('  计息负债成本率',        M4,             'B28',          exp['cost'],        1e-10),
    ('  净利差 NIS',            M4,             'B29',          exp['nis'],         1e-10),
    ('★ NII 计量表 NIM',        M4,             'B30',          exp['nim'],         1e-10),
    ('  平均贷款余额',          M4,             'B34',          exp['loans'],       1e-6),
    ('  存贷比',                M4,             'B36',          exp['ltd'],         1e-10),
    ('  活期化率',              M4,             'B39',          exp['demand_ratio'], 1e-10),
    ('结构拆解 人民币 NII',      M5,             'D27',          exp['ccy_rmb_nii'], 1e-6),
    ('结构拆解 外币 NII',        M5,             'D28',          exp['ccy_fx_nii'],  1e-6),
    ('结构拆解 NII 勾稽差额',   M5,             'D29',          0.0,               1e-6),
    ('敏感性 资产敞口 A_β',      M6,             'C5',           exp['a_beta'],      1e-6),
    ('敏感性 A_β 贷款',         M6,             'C6',           exp['a_beta_loan'], 1e-6),
    ('敏感性 A_β 债券',         M6,             'C7',           exp['a_beta_bond'], 1e-6),
    ('敏感性 A_β 金融',         M6,             'C8',           exp['a_beta_fin'],  1e-6),
    ('敏感性 A_β 外币',         M6,             'C9',           exp['a_beta_fx'],   1e-6),
    ('敏感性 负债敞口 L_β',      M6,             'C10',          exp['l_beta'],      1e-6),
    ('敏感性 L_β 存款',         M6,             'C11',          exp['l_beta_dep'],  1e-6),
    ('敏感性 L_β 同业',         M6,             'C12',          exp['l_beta_ib'],   1e-6),
    ('敏感性 L_β 央行',         M6,             'C13',          exp['l_beta_cb'],   1e-6),
    ('敏感性 L_β 外币',         M6,             'C14',          exp['l_beta_fx'],   1e-6),
    ('★ 敏感性 重定价缺口 RG',   M6,             'C15',          exp['rg'],          1e-6),
    ('  敏感性 利率弹性',        M6,             'C17',          exp['elast'],       1e-10),
]

print('=' * 104)
print('pycel 公式求值 vs Python 独立复算')
print('=' * 104)
print(f"{'指标':<26}{'sheet!cell':<24}{'Excel(pycel)':>20}{'Python':>20}{'差值':>13}")
print('-' * 104)
fails = []
for label, sh, cell, want, tol in CELLS:
    got = V(sh, cell)
    if not isinstance(got, (int, float)):
        print(f'{label:<26}{sh+"!"+cell:<24}{str(got):>20}')
        fails.append((label, sh, cell, 'NON_NUMERIC', got))
        continue
    diff = abs(got - want)
    ok = diff <= tol
    print(f'{label:<26}{sh+"!"+cell:<24}{got:>20.6f}{want:>20.6f}{diff:>13.2e}{"" if ok else "  <-- MISMATCH"}')
    if not ok:
        fails.append((label, sh, cell, got, want))

# 逐行求值
print()
print('-' * 104)
print('逐账户求值汇总（36 行 × 2 列）')
print('-' * 104)
s_ii = sum(V('NII数据源', f'N{r}') for r in range(D1, D2+1) if isinstance(V('NII数据源', f'N{r}'), (int, float)))
s_ie = sum(V('NII数据源', f'O{r}') for r in range(D1, D2+1) if isinstance(V('NII数据源', f'O{r}'), (int, float)))
print(f'逐行 Σ 利息收入 = {s_ii:>18,.6f}   期望 {exp["sum_ii"]:>18,.6f}   差 {abs(s_ii-exp["sum_ii"]):.2e}')
print(f'逐行 Σ 利息支出 = {s_ie:>18,.6f}   期望 {exp["sum_ie"]:>18,.6f}   差 {abs(s_ie-exp["sum_ie"]):.2e}')
if abs(s_ii-exp['sum_ii']) > 1e-6: fails.append(('逐行Σ利息收入', 'NII数据源', 'N4:N39', s_ii, exp['sum_ii']))
if abs(s_ie-exp['sum_ie']) > 1e-6: fails.append(('逐行Σ利息支出', 'NII数据源', 'O4:O39', s_ie, exp['sum_ie']))

# 勾稽校验
print()
print('-' * 104)
print('勾稽校验单元格（校验 1~7 / 9 / 10 应为 0）')
print('-' * 104)
CHK = [('校验1 明细↔数据源 利息收入', 'B42', 0.0), ('校验2 明细↔数据源 利息支出', 'B43', 0.0),
       ('校验3 利息收入占比=100%',    'B44', 0.0), ('校验4 利息支出占比=100%',    'B45', 0.0),
       ('校验5 NII 恒等式',          'B46', 0.0), ('校验6 资产条线加总',        'B47', 0.0),
       ('校验7 负债条线加总',        'B48', 0.0), ('校验9 币种加总(资产)',      'B50', 0.0),
       ('校验10 币种加总(负债)',     'B51', 0.0)]
for label, cell, want in CHK:
    v = V(M4, cell)
    ok = isinstance(v, (int, float)) and abs(v - want) < 1e-4
    print(f'  {label:<28} {cell:<5} = {v!s:>22}   {"PASS" if ok else "CHECK"}')
    if not ok:
        fails.append((label, M4, cell, v, want))
v8 = V(M4, 'B49')
print(f'  {"校验8 已剔除非息(信息)":<28} {"B49":<5} = {v8!s:>22}   (期望 {exp["nonearn_a"]:,.2f})')

# 存款校验
print(f'  {"结构拆解 存款活期化率":<28} = {V(M5,"B37")!s:>22}   期望 {exp["demand_ratio"]*100:.4f}%')
print(f'  {"结构拆解 存款校验差额":<28} = {V(M5,"B38")!s:>22}   期望 0.000000')

# 情景
print()
print('-' * 104)
print('情景敏感性（7 档平行移动 + 4 档单边冲击）')
print('-' * 104)
SC0 = 22
print(f"{'情景':<26}{'ΔNII(Excel)':>16}{'ΔNII(Python)':>16}{'情景后NII':>14}{'情景后NIM':>12}")
for i, bp in enumerate([250, 100, 50, 0, -50, -100, -250]):
    rr = SC0 + i
    dii = -bp/10000*exp['a_beta']; die = -bp/10000*exp['l_beta']; dnii = dii-die
    got = V(M6, f'E{rr}')
    snii = V(M6, f'F{rr}'); snim = V(M6, f'H{rr}')
    diff = abs(got-dnii) if isinstance(got,(int,float)) else 999
    print(f"{('Δr=%+dbp' % bp):<26}{got:>16.4f}{dnii:>16.4f}{snii:>14.2f}{snim*100:>11.4f}%{'' if diff<1e-5 else '  <-- MISMATCH'}")
    if diff >= 1e-5: fails.append((f'情景{bp}', M6, f'E{rr}', got, dnii))
print()
SD0 = 34
print(f"{'单边冲击':<26}{'ΔNII(Excel)':>16}{'ΔNII(Python)':>16}{'情景后NII':>14}")
for i, (lbl, ka, kl) in enumerate([('仅负债端全额', 0.0, 1.0), ('仅资产端全额', 1.0, 0.0),
                                   ('实际按β加权', 1.0, 1.0), ('负债重定价滞后', 1.0, 0.3)]):
    rr = SD0 + i
    dnii = (-100/10000*exp['a_beta']*ka) - (-100/10000*exp['l_beta']*kl)
    got = V(M6, f'E{rr}'); snii = V(M6, f'F{rr}')
    diff = abs(got-dnii) if isinstance(got,(int,float)) else 999
    print(f"{lbl:<26}{got:>16.4f}{dnii:>16.4f}{snii:>14.2f}{'' if diff<1e-5 else '  <-- MISMATCH'}")
    if diff >= 1e-5: fails.append((f'单边{lbl}', M6, f'E{rr}', got, dnii))

# 判定文本
print()
print('-' * 104)
print('监管判定文本')
print('-' * 104)
for lbl, cell in [('NIM 达标判定', 'B56'), ('NIM 区间判定', 'B57'), ('存贷比判定', 'B58')]:
    print(f'  {lbl:<16} {cell} = {V(M4, cell)}')
for lbl, cell in [('RG 方向判定', 'C44'), ('敞口强弱判定', 'C45')]:
    print(f'  {lbl:<16} {cell} = {V(M6, cell)}')

print()
print('=' * 104)
if fails:
    print(f'❌ {len(fails)} 项不一致：')
    for f in fails:
        print('   ', f)
    sys.exit(1)
print('✅ 全部 pycel 公式求值与 Python 独立复算完全一致（容差内）')
print('=' * 104)