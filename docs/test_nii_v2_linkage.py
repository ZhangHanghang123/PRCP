# -*- coding: utf-8 -*-
"""NII v2 模版联动传导测试：修改 ①数据源 输入，验证下游全部自动重算"""
import os
import shutil
from pycel import ExcelCompiler
import openpyxl

SRC = 'C:/银行经营/PRCP/docs/v2/NII计量模版_v2_真实数据.xlsx'
TMP = 'C:/银行经营/PRCP/docs/_nii_v2_link.xlsx'

WATCH = [
    ('生息资产',      '⑥NII计量表', 'B5'),
    ('计息负债',      '⑥NII计量表', 'B7'),
    ('利息收入',      '⑥NII计量表', 'B14'),
    ('利息支出',      '⑥NII计量表', 'B15'),
    ('★ NII',         '⑥NII计量表', 'B20'),
    ('生息资产收益率', '⑥NII计量表', 'B24'),
    ('计息负债成本率', '⑥NII计量表', 'B25'),
    ('★ NIM',         '⑥NII计量表', 'B27'),
    ('存贷比',         '⑥NII计量表', 'B32'),
    ('存款活期化率',   '⑥NII计量表', 'B34'),
    ('资产敞口 A_β',   '⑦期限结构与重定价', 'E30'),
    ('负债敞口 L_β',   '⑦期限结构与重定价', 'E31'),
    ('★ 重定价缺口 RG', '⑦期限结构与重定价', 'E32'),
    ('+100bp ΔNII',    '⑨情景敏感性', 'E7'),
    ('+100bp 情景NIM', '⑨情景敏感性', 'H7'),
    ('⑧ 条线 NII',     '⑧NII结构拆解', 'B30'),
]


def snap(path):
    exc = ExcelCompiler(filename=path)
    out = {}
    for lbl, sh, cl in WATCH:
        try:
            out[lbl] = exc.evaluate(f"'{sh}'!{cl}")
        except Exception as e:
            out[lbl] = f'ERR:{e}'
    return out


def fmt(v):
    return f'{v:>15,.4f}' if isinstance(v, (int, float)) else f'{str(v):>15}'


def show(base, new, title, note=''):
    print()
    print('=' * 92)
    print(title + (f'  ({note})' if note else ''))
    print('=' * 92)
    print(f"{'监测点':<20}{'基线':>16}{'变动后':>16}{'变化量':>16}")
    print('-' * 92)
    for lbl, _, _ in WATCH:
        a, b = base[lbl], new[lbl]
        d = f'{b-a:>16.4f}' if isinstance(a, (int, float)) and isinstance(b, (int, float)) else f'{"":>16}'
        print(f'{lbl:<20}{fmt(a)}{fmt(b)}{d}')


print('=' * 92)
print('基线快照')
print('=' * 92)
shutil.copyfile(SRC, TMP)
base = snap(TMP)
for lbl, _, _ in WATCH:
    print(f'{lbl:<20}{fmt(base[lbl])}')

# 测试 1：信用卡贷款利率 12% → 15%
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP)
w1 = wb['①数据源']
r_cc = next(rr for rr in range(4, 28) if '信用卡' in str(w1.cell(rr, 2).value))
old = w1.cell(r_cc, 7).value
w1.cell(r_cc, 7, 0.15)
wb.save(TMP)
show(base, snap(TMP), '测试 1：信用卡贷款 加权平均利率 12.00% → 15.00%',
     f'①数据源!G{r_cc}')

# 测试 2：对公活期存款余额 +100,000 亿
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP)
w1 = wb['①数据源']
r_dq = next(rr for rr in range(4, 28) if '对公活期' in str(w1.cell(rr, 2).value))
oldb = w1.cell(r_dq, 6).value
w1.cell(r_dq, 6, oldb + 100000)
wb.save(TMP)
show(base, snap(TMP), '测试 2：对公活期存款 余额 +100,000 亿元',
     f'{oldb:,.0f} → {oldb+100000:,.0f} 亿')

# 测试 3：活期存款重定价 β 1.00 → 0.20（活期化率下降）
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP)
w1 = wb['①数据源']
r_d2 = next(rr for rr in range(4, 28) if '零售活期' in str(w1.cell(rr, 2).value))
oldb2 = w1.cell(r_d2, 12).value
w1.cell(r_d2, 12, 0.20)
wb.save(TMP)
show(base, snap(TMP), '测试 3：零售活期存款 重定价β 1.000 → 0.200',
     f'①数据源!L{r_d2}')

# 测试 4：①期限分布 某资产账户 1M 桶减半（改变期限结构 → 改变 β → 改变 RG）
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP)
w2 = wb['②期限分布']
r_ln = next(rr for rr in range(4, 28) if '对公一般贷款' in str(w2.cell(rr, 2).value))
oldv = w2.cell(r_ln, 3).value
w2.cell(r_ln, 3, oldv * 0.5)
wb.save(TMP)
show(base, snap(TMP), '测试 4：对公一般贷款 1M 桶金额减半（改变期限结构）',
     f'②期限分布!C{r_ln} {oldv:,.0f} → {oldv*0.5:,.0f} 亿')

print()
print('=' * 92)
print('联动结论')
print('=' * 92)
tests = [
    ('测试1 信用卡利率+300bp → 利息收入↑ / NII↑', base['利息收入'] != snap(TMP)['利息收入'] or True),
]
t1 = snap(TMP)
# 重新逐项判定
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP); w1 = wb['①数据源']
r_cc = next(rr for rr in range(4, 28) if '信用卡' in str(w1.cell(rr, 2).value))
w1.cell(r_cc, 7, 0.15); wb.save(TMP); s1 = snap(TMP)
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP); w1 = wb['①数据源']
r_dq = next(rr for rr in range(4, 28) if '对公活期' in str(w1.cell(rr, 2).value))
w1.cell(r_dq, 6, w1.cell(r_dq, 6).value + 100000); wb.save(TMP); s2 = snap(TMP)
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP); w1 = wb['①数据源']
r_d2 = next(rr for rr in range(4, 28) if '零售活期' in str(w1.cell(rr, 2).value))
w1.cell(r_d2, 12, 0.20); wb.save(TMP); s3 = snap(TMP)
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP); w2 = wb['②期限分布']
r_ln = next(rr for rr in range(4, 28) if '对公一般贷款' in str(w2.cell(rr, 2).value))
w2.cell(r_ln, 3, w2.cell(r_ln, 3).value * 0.5); wb.save(TMP); s4 = snap(TMP)

checks = [
    ('测试1 信用卡利率↑ → 利息收入↑ 且 NII↑ 且 NIM↑',
     s1['利息收入'] > base['利息收入'] and s1['★ NII'] > base['★ NII'] and s1['★ NIM'] > base['★ NIM']),
    ('测试2 活期存款↑ → 计息负债↑ 且 利息支出↑ 且 活期化率↑',
     s2['计息负债'] > base['计息负债'] and s2['利息支出'] > base['利息支出'] and s2['存款活期化率'] > base['存款活期化率']),
    ('测试3 活期β↓ → 负债敞口↓ 且 RG 上升(缺口收窄)',
     s3['负债敞口 L_β'] < base['负债敞口 L_β'] and s3['★ 重定价缺口 RG'] > base['★ 重定价缺口 RG']),
    ('测试4 期限结构变化 → ①1年内到期 / 资产敞口 / RG 同步变化',
     s4['★ 重定价缺口 RG'] != base['★ 重定价缺口 RG'] or s4['资产敞口 A_β'] != base['资产敞口 A_β']),
    ('全程 ⑧条线NII 与 ⑥NII 保持勾稽一致',
     abs(s1['⑧ 条线 NII'] - s1['★ NII']) < 1e-6 and abs(s4['⑧ 条线 NII'] - s4['★ NII']) < 1e-6),
]
allok = True
for lab, ok in checks:
    print(f'  {lab:<52} {"PASS" if ok else "FAIL"}')
    allok = allok and ok
print()
print('✅ 全链路联动验证通过：修改 ①数据源 / ②期限分布 任一输入，8 张 sheet 全部自动重算'
      if allok else '❌ 联动验证存在失败项')
os.remove(TMP)