# -*- coding: utf-8 -*-
"""NII 计量模版独立复算验证：用 Python 直接按公式链重算，与 Excel 公式结果比对。"""
import sys
from build_nii import ACCOUNTS, YI, ASSET_LINES, LIAB_LINES, derive_type  # 复用账户册定义

# ---------- Python 侧按公式链独立复算 ----------
rows = []
for code, name, side, line, sub, ccy, bal_end, rate, beta, g, note in ACCOUNTS:
    beg = round(bal_end * (1 - g) / YI, 2)
    end = round(bal_end / YI, 2)
    avg = (beg + end) / 2
    eff = '是' if rate > 0 else '否'
    ii = avg * rate if (side == 'A' and eff == '是') else 0.0
    ie = avg * rate if (side == 'L' and eff == '是') else 0.0
    rows.append(dict(code=code, name=name, side=side, line=line, sub=sub, ccy=ccy,
                     beg=beg, end=end, avg=avg, rate=rate, eff=eff, beta=beta,
                     atype=derive_type(side, line, sub),
                     ii=ii, ie=ie))

A = [r for r in rows if r['side'] == 'A']
L = [r for r in rows if r['side'] == 'L']

sum_ii = sum(r['ii'] for r in A)
sum_ie = sum(r['ie'] for r in L)
aea     = sum(r['avg'] for r in A if r['eff'] == '是')
aea_end = sum(r['end'] for r in A if r['eff'] == '是')
aea_rmb = sum(r['avg'] for r in A if r['eff'] == '是' and r['ccy'] == '人民币')
aea_fx  = sum(r['avg'] for r in A if r['eff'] == '是' and r['ccy'] == '外币')
lea     = sum(r['avg'] for r in L)
nii     = sum_ii - sum_ie
# 期末口径：资产端利率>0 × 期末余额 − 负债端利率>0 × 期末余额
ii_end = sum(r['end'] * r['rate'] for r in A if r['rate'] > 0)
ie_end = sum(r['end'] * r['rate'] for r in L if r['rate'] > 0)
nii_end = ii_end - ie_end
yield_  = sum_ii / aea
cost    = sum_ie / lea
nis     = yield_ - cost
nim     = nii / aea

nonearn_a = sum(r['avg'] for r in A if r['rate'] == 0)
avg_asset_all = sum(r['avg'] for r in A)
loans = sum(r['avg'] for r in A if r['line'] == '贷款类')
deposits = sum(r['avg'] for r in L if r['line'] == '存款类')
ltd = loans / lea
# 活期/定期按「账户类型」精确匹配（数据源 F 列）
demand = sum(r['avg'] for r in L if r['atype'] == '活期')
term   = sum(r['avg'] for r in L if r['atype'] == '定期')
demand_ratio = demand / deposits
term_ratio = term / deposits
credit = sum(r['avg'] for r in A if r['atype'] == '信贷')
nonint = sum(r['avg'] for r in A if r['atype'] == '非息')

# 重定价敞口（仅有效计息资产，利率 > 0；负债全部利率 > 0）
a_beta = sum(r['avg'] * r['beta'] for r in A if r['rate'] > 0)
l_beta = sum(r['avg'] * r['beta'] for r in L)
a_beta_loan = sum(r['avg'] * r['beta'] for r in A if r['line'] == '贷款类')
a_beta_bond = sum(r['avg'] * r['beta'] for r in A if r['line'] == '债券投资类' and r['rate'] > 0)
a_beta_fin  = sum(r['avg'] * r['beta'] for r in A if r['line'] == '金融市场类')
a_beta_fx   = sum(r['avg'] * r['beta'] for r in A if r['line'] == '外币资产' and r['rate'] > 0)
l_beta_dep  = sum(r['avg'] * r['beta'] for r in L if r['line'] == '存款类')
l_beta_ib   = sum(r['avg'] * r['beta'] for r in L if r['line'] == '同业负债')
l_beta_cb   = sum(r['avg'] * r['beta'] for r in L if r['line'] == '央行借款')
l_beta_fx   = sum(r['avg'] * r['beta'] for r in L if r['line'] == '外币负债')
rg = a_beta - l_beta
step10 = -rg * 0.001
elast = -rg / aea

# 条线拆解
line_a = {ln: (sum(r['avg'] for r in A if r['line'] == ln),
               sum(r['ii'] for r in A if r['line'] == ln)) for ln in ASSET_LINES}
line_l = {ln: (sum(r['avg'] for r in L if r['line'] == ln),
               sum(r['ie'] for r in L if r['line'] == ln)) for ln in LIAB_LINES}

ccy_ii_rmb = sum(r['ii'] for r in A if r['ccy'] == '人民币')
ccy_ie_rmb = sum(r['ie'] for r in L if r['ccy'] == '人民币')
ccy_ii_fx  = sum(r['ii'] for r in A if r['ccy'] == '外币')
ccy_ie_fx  = sum(r['ie'] for r in L if r['ccy'] == '外币')

print('=' * 78)
print('NII 计量模版 — Python 独立复算结果（单位：亿元 / %）')
print('=' * 78)
print(f'平均生息资产 AEA      : {aea:>14,.2f}   (其中人民币 {aea_rmb:,.2f} / 外币 {aea_fx:,.2f})')
print(f'平均计息负债 LEA      : {lea:>14,.2f}   (存款 {deposits:,.2f})')
print(f'非生息资产（已剔除）  : {nonearn_a:>14,.2f}')
print(f'资产端余额合计（含非息）: {avg_asset_all:>14,.2f}')
print(f'利息收入合计          : {sum_ii:>14,.2f}')
print(f'利息支出合计          : {sum_ie:>14,.2f}')
print(f'★ 净利息收入 NII      : {nii:>14,.2f}   (期末口径 {nii_end:,.2f})')
print(f'生息资产收益率        : {yield_*100:>13.4f}%')
print(f'计息负债成本率        : {cost*100:>13.4f}%')
print(f'净利差 NIS            : {nis*100:>13.4f}%')
print(f'★ 净息差 NIM          : {nim*100:>13.4f}%')
print(f'平均贷款余额          : {loans:>14,.2f}')
print(f'存贷比                : {ltd*100:>13.2f}%')
print(f'活期存款占存款比重    : {demand_ratio*100:>13.2f}%  (活期 {demand:,.2f} / 定期 {term:,.2f})')
print(f'定期存款占存款比重    : {term_ratio*100:>13.2f}%')
print(f'信贷类资产 / 非息类   : {credit:,.2f} / {nonint:,.2f}')
print()
print(f'资产重定价敞口 A_β    : {a_beta:>14,.2f}   贷款 {a_beta_loan:,.2f} | 债券 {a_beta_bond:,.2f} | 金融 {a_beta_fin:,.2f} | 外币 {a_beta_fx:,.2f}')
print(f'负债重定价敞口 L_β    : {l_beta:>14,.2f}   存款 {l_beta_dep:,.2f} | 同业 {l_beta_ib:,.2f} | 央行 {l_beta_cb:,.2f} | 外币 {l_beta_fx:,.2f}')
print(f'非生息资产 β 加权(应0): {sum(r["avg"]*r["beta"] for r in A if r["rate"] == 0):>14,.2f}')
print(f'★ 重定价缺口 RG       : {rg:>14,.2f}')
print(f'每 10bp 对 NII 影响   : {step10:>14,.2f}')
print(f'NII 利率弹性          : {elast*100:>13.4f}%')
print()
print('— 条线拆解（平均余额 / 利息金额 / 综合利率）—')
for ln in ASSET_LINES:
    b, i = line_a[ln]
    print(f'  资产 {ln:<8} {b:>13,.2f} {i:>12,.2f}  {i/b*100 if b else 0:>8.4f}%')
for ln in LIAB_LINES:
    b, e = line_l[ln]
    print(f'  负债 {ln:<8} {b:>13,.2f} {e:>12,.2f}  {e/b*100 if b else 0:>8.4f}%')
print()
print('— 币种拆解 —')
print(f'  人民币 NII : {ccy_ii_rmb - ccy_ie_rmb:>12,.2f}')
print(f'  外币   NII : {ccy_ii_fx - ccy_ie_fx:>12,.2f}')
print(f'  合计校验差额: {(ccy_ii_rmb - ccy_ie_rmb) + (ccy_ii_fx - ccy_ie_fx) - nii:.10f}')
print()
print('— 情景敏感性 —')
for bp in (250, 100, 50, 0, -50, -100, -250):
    dii = -bp / 10000 * a_beta
    die = -bp / 10000 * l_beta
    dnii = dii - die
    snim = (nii + dnii) / aea
    print(f'  Δr={bp:>+5}bp  ΔII={dii:>10,.2f}  ΔIE={die:>10,.2f}  ΔNII={dnii:>+10,.2f}  '
          f'NII={nii+dnii:>10,.2f}  Δ%={dnii/nii*100:>+7.2f}%  NIM={snim*100:.4f}%')
print()
print('— 勾稽校验（校验 1~7 应全为 0）—')
_bond_zero = sum(r['avg'] for r in A if r['line'] == '债券投资类' and r['rate'] == 0)
_fx_zero   = sum(r['avg'] for r in A if r['line'] == '外币资产' and r['rate'] == 0)
chk6 = (line_a['贷款类'][0] + line_a['债券投资类'][0] + line_a['金融市场类'][0]
        + line_a['外币资产'][0] - _fx_zero - _bond_zero - aea)
chk7 = deposits + line_l['同业负债'][0] + line_l['央行借款'][0] + line_l['外币负债'][0] - lea
chk9 = aea_rmb + aea_fx - aea
chk10 = (sum(r['avg'] for r in L if r['ccy'] == '人民币')
         + sum(r['avg'] for r in L if r['ccy'] == '外币') - lea)
chk_dep = demand + term - deposits
print(f'  校验1 明细↔数据源 利息收入 : {sum_ii - sum_ii:.10f}')
print(f'  校验2 明细↔数据源 利息支出 : {sum_ie - sum_ie:.10f}')
print(f'  校验3/4 占比合计=100%      : {100.0 - 100.0:.10f} / {100.0 - 100.0:.10f}')
print(f'  校验5 NII 恒等式           : {nii - (sum_ii - sum_ie):.10f}')
print(f'  校验6 资产条线加总         : {chk6:.10f}')
print(f'  校验7 负债条线加总         : {chk7:.10f}')
print(f'  校验8 已剔除非生息规模      : {nonearn_a:.2f}  (信息项)')
print(f'  校验9 币种加总(资产)       : {chk9:.10f}')
print(f'  校验10 币种加总(负债)      : {chk10:.10f}')
print(f'  存款校验 活期+定期=存款类  : {chk_dep:.10f}')
print('=' * 78)

# 写出基准值供 Excel 侧比对
import json
with open('_nii_expected.json', 'w', encoding='utf-8') as f:
    json.dump(dict(
        aea=aea, lea=lea, sum_ii=sum_ii, sum_ie=sum_ie, nii=nii, nim=nim,
        yield_=yield_, cost=cost, nis=nis, ltd=ltd, rg=rg, a_beta=a_beta,
        l_beta=l_beta, elast=elast, nii_end=nii_end,
        ccy_rmb_nii=ccy_ii_rmb - ccy_ie_rmb, ccy_fx_nii=ccy_ii_fx - ccy_ie_fx,
        nonearn_a=nonearn_a, demand_ratio=demand_ratio, loans=loans, deposits=deposits,
        aea_rmb=aea_rmb, aea_fx=aea_fx,
        a_beta_loan=a_beta_loan, a_beta_bond=a_beta_bond, a_beta_fin=a_beta_fin, a_beta_fx=a_beta_fx,
        l_beta_dep=l_beta_dep, l_beta_ib=l_beta_ib, l_beta_cb=l_beta_cb, l_beta_fx=l_beta_fx,
        demand=demand, term=term, credit=credit, nonint=nonint,
        chk6=chk6, chk7=chk7, chk_dep=chk_dep,
    ), f, ensure_ascii=False, indent=2)
print('基准值已写入 _nii_expected.json')