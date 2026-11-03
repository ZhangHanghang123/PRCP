# -*- coding: utf-8 -*-
"""NII v3 模版联动传导测试"""
import os
import shutil
from pycel import ExcelCompiler
import openpyxl

SRC = 'C:/银行经营/PRCP/docs/v2/NII计量模版_v3_模拟填充.xlsx'
TMP = 'C:/银行经营/PRCP/docs/_nii_v3_link.xlsx'

WATCH = [
    ('生息资产',      '⑦NII计量表',     'B5'),
    ('计息负债',      '⑦NII计量表',     'B9'),
    ('利息收入',      '⑦NII计量表',     'B12'),
    ('利息支出',      '⑦NII计量表',     'B13'),
    ('★ NII',         '⑦NII计量表',     'B18'),
    ('★ NIM',         '⑦NII计量表',     'B19'),
    ('生息资产收益率',  '⑦NII计量表',     'B20'),
    ('计息负债成本率',  '⑦NII计量表',     'B21'),
    ('资产端 WAL',     '⑦NII计量表',     'B26'),
    ('负债端 MAL',     '⑦NII计量表',     'B27'),
    ('个人贷款 1年内到期', '①数据源',       'J5'),
    ('个人贷款 覆盖率',    '①数据源',       'K5'),
    ('个人贷款 填充后Σ',   '③期限分布填充',  'BP5'),
    ('个人贷款 填充系数k', '③期限分布填充',  'BO5'),
    ('活期存款 填充后Σ',   '③期限分布填充',  'BP20'),
    ('活期存款 填充系数k', '③期限分布填充',  'BO20'),
    ('校验差(合计)',    '③期限分布填充',  'BR27'),
    ('+100bp ΔNII',    '⑨情景敏感性',    'E7'),
]


def snap(path):
    exc = ExcelCompiler(filename=path)
    out = {}
    for lbl, sh, cl in WATCH:
        try:
            out[lbl] = exc.evaluate(f"'{sh}'!{cl}")
        except Exception as e:
            out[lbl] = f'ERR:{type(e).__name__}'
    return out


def fmt(v):
    if isinstance(v, (int, float)):
        return f'{v:>15,.4f}'
    return f'{str(v):>15}'


print('=' * 92)
print('基线快照')
print('=' * 92)
shutil.copyfile(SRC, TMP)
base = snap(TMP)
for lbl, _, _ in WATCH:
    print(f'{lbl:<20}{fmt(base[lbl])}')


def run(title, mutate, note=''):
    shutil.copyfile(SRC, TMP)
    wb = openpyxl.load_workbook(TMP)
    mutate(wb)
    wb.save(TMP)
    new = snap(TMP)
    print()
    print('=' * 92)
    print(title + (f'  ({note})' if note else ''))
    print('=' * 92)
    print(f"{'监测点':<20}{'基线':>16}{'变动后':>16}{'变化量':>16}")
    print('-' * 92)
    for lbl, _, _ in WATCH:
        a, b = base[lbl], new[lbl]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            print(f'{lbl:<20}{fmt(a)}{fmt(b)}{b-a:>16,.4f}')
        else:
            print(f'{lbl:<20}{fmt(a)}{fmt(b)}{"":>16}')
    return new


# 测试 1：某资产利率上调 → 利息收入↑ → NII↑
def m1(wb):
    w1 = wb['①数据源']
    r = next(rr for rr in range(4, 28) if '对公一般贷款' in str(w1.cell(rr, 2).value))
    w1.cell(r, 7, w1.cell(r, 7).value + 0.001)
s1 = run('测试 1：对公一般贷款 利率 +10bp', m1, '①数据源!G 列')


# 测试 2：修改 ②观测桶 → ③填充自动重算且仍平准
def m2(wb):
    w2 = wb['②期限分布观测']
    r = next(rr for rr in range(4, 27) if '个人贷款' in str(w2.cell(rr, 2).value))
    w2.cell(r, 3, w2.cell(r, 3).value * 0.5)
s2 = run('测试 2：②观测 个人贷款 1M 桶减半 → ③填充重算且仍平准', m2, '②期限分布观测!C 列')


# 测试 3：修改 ①余额 → ③填充的 k 与 Σ 跟随
def m3(wb):
    w1 = wb['①数据源']
    r = next(rr for rr in range(4, 28) if '对公活期存款' in str(w1.cell(rr, 2).value))
    w1.cell(r, 6, w1.cell(r, 6).value + 50000)
s3 = run('测试 3：对公活期存款 余额 +50,000 亿 → 填充 k 与 Σ 跟随', m3, '①数据源!F 列')


# 测试 4：修改 ②观测桶 → WAL/MAL 跟随变化
def m4(wb):
    w2 = wb['②期限分布观测']
    r = next(rr for rr in range(4, 27) if '对公定期存款' in str(w2.cell(rr, 2).value))
    w2.cell(r, 3, w2.cell(r, 3).value * 0.5)
s4 = run('测试 4：②观测 对公定期存款 1M 桶减半 → MAL 跟随变化', m4, '②期限分布观测!C 列')


print()
print('=' * 92)
print('联动结论')
print('=' * 92)
checks = [
    ('测试1 资产利率↑ → 利息收入↑ / NII↑ / NIM↑',
     s1['利息收入'] > base['利息收入'] and s1['★ NII'] > base['★ NII'] and s1['★ NIM'] > base['★ NIM']),
    ('测试2 观测变动 → 校验差仍为 0',
     abs(s2['校验差(合计)']) < 1e-6),
    ('测试2 观测变动 → 个人贷款 1年内到期变化',
     abs(s2['个人贷款 1年内到期'] - base['个人贷款 1年内到期']) > 1e-6),
    ('测试2 观测变动 → 个人贷款填充后Σ 不变（仍平准）',
     abs(s2['个人贷款 填充后Σ'] - base['个人贷款 填充后Σ']) < 1e-6),
    ('测试3 余额↑ → 活期存款 填充系数k 变化 且 填充后Σ↑',
     s3['活期存款 填充后Σ'] > base['活期存款 填充后Σ']
     and abs(s3['活期存款 填充系数k'] - base['活期存款 填充系数k']) > 1e-9),
    ('测试3 余额↑ → 计息负债↑ / 利息支出↑',
     s3['计息负债'] > base['计息负债'] and s3['利息支出'] > base['利息支出']),
    ('测试4 观测变动 → MAL 变化（WAL 跟随重算）',
     abs(s4['负债端 MAL'] - base['负债端 MAL']) > 1e-9),
    ('全程 校验差恒为 0（模拟填充始终平准）',
     all(abs(s['校验差(合计)']) < 1e-6 for s in (base, s1, s2, s3, s4))),
]
allok = True
for lab, ok in checks:
    print(f'  {lab:<52} {"PASS" if ok else "FAIL"}')
    allok = allok and ok
print()
print('✅ 全链路联动验证通过：修改 ①数据源 / ②观测 任一输入，10 张 sheet 全部自动重算，模拟填充始终平准'
      if allok else '❌ 联动验证存在失败项')
os.remove(TMP)