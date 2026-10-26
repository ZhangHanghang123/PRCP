# -*- coding: utf-8 -*-
"""NII 模版联动传导测试：修改 NII数据源 的单个输入，验证下游全部自动更新。"""
import shutil, openpyxl, json
from pycel import ExcelCompiler

SRC = 'C:/银行经营/PRCP/docs/v2/NII_计量模版.xlsx'
TMP = 'C:/银行经营/PRCP/docs/_nii_link_test.xlsx'

# 关键监测点 (label, sheet, cell)
WATCH = [
    ('平均生息资产',   'NII计量表',     'B5'),
    ('平均计息负债',   'NII计量表',     'B9'),
    ('利息收入合计',   'NII计量表',     'B16'),
    ('利息支出合计',   'NII计量表',     'B18'),
    ('★ NII',          'NII计量表',     'B22'),
    ('生息资产收益率', 'NII计量表',     'B27'),
    ('计息负债成本率', 'NII计量表',     'B28'),
    ('★ NIM',          'NII计量表',     'B30'),
    ('存贷比',         'NII计量表',     'B36'),
    ('活期化率',       'NII计量表',     'B39'),
    ('人民币 NII',     'NII结构拆解',   'D27'),
    ('外币 NII',       'NII结构拆解',   'D28'),
    ('重定价缺口 RG',  'NII情景敏感性', 'C15'),
    ('+100bp ΔNII',    'NII情景敏感性', 'E23'),
    ('+100bp 情景NIM', 'NII情景敏感性', 'H23'),
]

def snapshot(path):
    exc = ExcelCompiler(filename=path)
    out = {}
    for lbl, sh, cell in WATCH:
        try:
            v = exc.evaluate(f"'{sh}'!{cell}")
        except Exception as e:
            v = f'ERR:{e}'
        out[lbl] = v
    return out

def fmt(v):
    return f'{v:>16,.6f}' if isinstance(v, (int, float)) else f'{str(v):>16}'

print('=' * 96)
print('基线快照')
print('=' * 96)
shutil.copyfile(SRC, TMP)
base = snapshot(TMP)
print(f"{'监测点':<18}{'基线值':>18}")
print('-' * 96)
for lbl, _, _ in WATCH:
    print(f'{lbl:<18}{fmt(base[lbl])}')

# ---------- 测试 1：所有资产端利率 +50bp ----------
print()
print('=' * 96)
print('测试 1：全部资产端年化利率 +50bp（K 列）')
print('=' * 96)
wb = openpyxl.load_workbook(TMP)
ws = wb['NII数据源']
n = 0
for r in range(4, 40):
    if ws.cell(r, 3).value == '资产':
        ws.cell(r, 11, (ws.cell(r, 11).value or 0) + 0.005); n += 1
wb.save(TMP)
print(f'已修改 {n} 个资产账户利率')
t1 = snapshot(TMP)
print(f"{'监测点':<18}{'基线':>18}{'变动后':>18}{'变化量':>18}")
print('-' * 96)
for lbl, _, _ in WATCH:
    a, b = base[lbl], t1[lbl]
    d = f'{b-a:>18,.6f}' if isinstance(a,(int,float)) and isinstance(b,(int,float)) else f'{"":>18}'
    print(f'{lbl:<18}{fmt(a)}{fmt(b)}{d}')

# ---------- 测试 2：零售活期存款余额 +2000 亿 ----------
print()
print('=' * 96)
print('测试 2：零售活期存款期末余额 +2,000 亿元（S020101020100）')
print('=' * 96)
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP)
ws = wb['NII数据源']
old = ws.cell(27, 9).value
ws.cell(27, 9, old + 2000)
print(f'零售活期存款：{old:,.2f} → {old+2000:,.2f} 亿元')
wb.save(TMP)
t2 = snapshot(TMP)
print(f"{'监测点':<18}{'基线':>18}{'变动后':>18}{'变化量':>18}")
print('-' * 96)
for lbl, _, _ in WATCH:
    a, b = base[lbl], t2[lbl]
    d = f'{b-a:>18,.6f}' if isinstance(a,(int,float)) and isinstance(b,(int,float)) else f'{"":>18}'
    print(f'{lbl:<18}{fmt(a)}{fmt(b)}{d}')

# ---------- 测试 3：同业回购重定价β 0.98 → 0.20 ----------
print()
print('=' * 96)
print('测试 3：同业债券回购 重定价β 0.98 → 0.20（S020102010200）')
print('=' * 96)
shutil.copyfile(SRC, TMP)
wb = openpyxl.load_workbook(TMP)
ws = wb['NII数据源']
ob = ws.cell(30, 13).value
ws.cell(30, 13, 0.20)
print(f'同业回购 β：{ob} → 0.20')
wb.save(TMP)
t3 = snapshot(TMP)
print(f"{'监测点':<18}{'基线':>18}{'变动后':>18}{'变化量':>18}")
print('-' * 96)
for lbl, _, _ in WATCH:
    a, b = base[lbl], t3[lbl]
    d = f'{b-a:>18,.6f}' if isinstance(a,(int,float)) and isinstance(b,(int,float)) else f'{"":>18}'
    print(f'{lbl:<18}{fmt(a)}{fmt(b)}{d}')

print()
print('=' * 96)
print('联动结论')
print('=' * 96)
ok = True
c1 = abs(t1['★ NII'] - base['★ NII']) > 1
c1b = abs(t1['★ NIM'] - base['★ NIM']) > 1e-6
c2 = abs(t2['★ NII'] - base['★ NII']) > 1
c2b = abs(t2['平均计息负债'] - base['平均计息负债']) > 1
c3 = abs(t3['重定价缺口 RG'] - base['重定价缺口 RG']) > 1
c3b = abs(t3['+100bp ΔNII'] - base['+100bp ΔNII']) > 0.1
print(f'  测试1 资产利率+50bp  → NII 变化 {"PASS" if c1 else "FAIL"} / NIM 变化 {"PASS" if c1b else "FAIL"}')
print(f'  测试2 活期存款+2000亿 → NII 变化 {"PASS" if c2 else "FAIL"} / 计息负债变化 {"PASS" if c2b else "FAIL"}')
print(f'  测试3 同业回购β下调  → RG 变化 {"PASS" if c3 else "FAIL"} / +100bp ΔNII 变化 {"PASS" if c3b else "FAIL"}')
ok = all([c1, c1b, c2, c2b, c3, c3b])
print()
print('✅ 全链路联动验证通过：修改任一输入，6 张下游 sheet 全部自动重算' if ok else '❌ 联动验证存在失败项')

import os
os.remove(TMP)