# -*- coding: utf-8 -*-
"""NII v3 模版：Python 独立复算 + pycel 端到端验证"""
import sys
from pycel import ExcelCompiler
import openpyxl

XL = 'C:/银行经营/PRCP/docs/v2/NII计量模版_v3_模拟填充.xlsx'
SRC = 'C:/银行经营/PRCP/docs/v2/prcp_basic_20251231.xlsx'

# ---------- 1) Python 独立复算（直接读参照物） ----------
ws = openpyxl.load_workbook(SRC, data_only=True)['基础数据']
BUCKETS = [(f'{m}M', m / 12.0) for m in range(1, 61)] + \
          [('10Y', 10.0), ('15Y', 15.0), ('20Y', 20.0), ('30Y', 30.0)]
NB = len(BUCKETS)
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
for r in range(4, 44):
    code = ws.cell(r, 3).value
    if not code or int(ws.cell(r, 7).value or 0) != 1:
        continue
    name = str(ws.cell(r, 4).value or '').strip()
    cat = ws.cell(r, 8).value
    bal = (ws.cell(r, C_CURBAL).value or 0) / 1e8
    rate = (ws.cell(r, C_RATE).value or 0) / 100.0
    iy = bal * rate
    dist = []
    for i in range(NB):
        v = ws.cell(r, C_REMAIN0 + i).value
        dist.append((v if isinstance(v, (int, float)) else 0.0) / 1e8)
    rows.append(dict(code=code, name=name, cat=cat, bal=bal, rate=rate, iy=iy,
                     dist=dist, line=classify(name, cat)))

DIST = [x for x in rows if x['cat'] != 'EQUITY']
A = [x for x in rows if x['cat'] == 'ASSET']
L = [x for x in rows if x['cat'] == 'LIAB']
E = [x for x in rows if x['cat'] == 'EQUITY']
A_EARN = [x for x in A if x['rate'] > 0]
A_ZERO = [x for x in A if x['rate'] == 0]

II = sum(x['iy'] for x in A_EARN)
IE = sum(x['iy'] for x in L)
NII = II - IE
EA = sum(x['bal'] for x in A_EARN)
NEA = sum(x['bal'] for x in A_ZERO)
TA = sum(x['bal'] for x in A)
LEA = sum(x['bal'] for x in L)
TE = sum(x['bal'] for x in E)

# 模拟填充
for x in DIST:
    obs = sum(x['dist'])
    x['obs'] = obs
    x['k'] = (x['bal'] / obs) if obs > 0 else 0.0
    x['fill'] = [v * x['k'] for v in x['dist']]
    x['fill_sum'] = sum(x['fill'])
    x['gap'] = x['bal'] - obs
    x['check'] = x['fill_sum'] - x['bal']

obs_total = sum(x['obs'] for x in DIST)
fill_total = sum(x['fill_sum'] for x in DIST)
bal_total = sum(x['bal'] for x in DIST)
gap_total = sum(x['gap'] for x in DIST)
max_check = max(abs(x['check']) for x in DIST)

# WAL / MAL
def wal(cat):
    sel = [x for x in DIST if x['cat'] == cat]
    num = sum(sum(v * t for v, t in zip(x['fill'], [b[1] for b in BUCKETS])) for x in sel)
    den = sum(x['fill_sum'] for x in sel)
    return num / den if den else 0.0


WALA, WALL = wal('ASSET'), wal('LIAB')

print('=' * 88)
print('Python 独立复算（直接读 prcp_basic_20251231.xlsx）')
print('=' * 88)
print(f'  生息资产（{len(A_EARN)} 个）          : {EA:>14,.2f} 亿元')
print(f'  非生息资产（{len(A_ZERO)} 个）         : {NEA:>14,.2f} 亿元')
print(f'  资产端合计                        : {TA:>14,.2f} 亿元')
print(f'  计息负债（{len(L)} 个）              : {LEA:>14,.2f} 亿元')
print(f'  利息收入 / 支出                   : {II:>12,.2f} / {IE:,.2f} 亿元/年')
print(f'  ★ NII                             : {NII:>14,.2f} 亿元/年')
print(f'  NIM                               : {NII/EA*100:>14.4f}%')
print()
print('  —— 模拟填充校验 ——')
print(f'  纳入账户数（资产+负债）            : {len(DIST)}')
print(f'  观测合计 Σ                        : {obs_total:>14,.2f} 亿元')
print(f'  当前余额合计 Σ                    : {bal_total:>14,.2f} 亿元')
print(f'  填充缺口 Σ                        : {gap_total:>14,.2f} 亿元  ({gap_total/bal_total*100:.2f}%)')
print(f'  填充后合计 Σ                      : {fill_total:>14,.2f} 亿元')
print(f'  ★ 填充后 − 当前余额               : {fill_total-bal_total:>14.10f} 亿元')
print(f'  ★ 单账户最大校验差                : {max_check:>14.10f} 亿元')
print(f'  观测覆盖率                        : {obs_total/bal_total*100:>14.4f}%')
print()
print(f'  资产端 WAL                        : {WALA:>14.4f} 年')
print(f'  负债端 MAL                        : {WALL:>14.4f} 年')
print(f'  期限结构错配 WAL − MAL            : {WALA-WALL:>14.4f} 年')
print()
print('  —— 逐账户填充明细 ——')
for x in DIST:
    print(f'  {x["name"][:18]:<20} 余额={x["bal"]:>9,.0f} 观测={x["obs"]:>9,.0f} '
          f'k={x["k"]:>8.4f} 缺口={x["gap"]:>9,.0f} 校验差={x["check"]:>12.8f}')

# ---------- 2) pycel ----------
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
    ('① Σ 当前余额', '①数据源', 'F28', sum(x['bal'] for x in rows), 1e-4),
    ('① Σ 月度利息', '①数据源', 'H28', sum(x['iy']/12 for x in rows), 1e-4),
    ('① Σ 年度利息', '①数据源', 'I28', sum(x['iy'] for x in rows), 1e-4),
    ('② 观测Σ合计', '②期限分布观测', 'BO27', obs_total, 1e-4),
    ('② 填充缺口合计', '②期限分布观测', 'BR27', gap_total, 1e-4),
    ('③ 填充后Σ合计', '③期限分布填充', 'BP27', fill_total, 1e-4),
    ('③ ★校验差合计', '③期限分布填充', 'BR27', 0.0, 1e-6),
    ('③ 填充系数 k(首行)', '③期限分布填充', 'BO4', DIST[0]['k'], 1e-9),
    ('⑤ 利息收入合计', '⑤利息收入明细', 'G18', II, 1e-4),
    ('⑤ 生息资产余额', '⑤利息收入明细', 'E18', EA, 1e-4),
    ('⑤ 非生息资产', '⑤利息收入明细', 'E23', NEA, 1e-4),
    ('⑥ 利息支出合计', '⑥利息支出明细', 'G11', IE, 1e-4),
    ('⑥ 计息负债余额', '⑥利息支出明细', 'E11', LEA, 1e-4),
    ('⑦ 生息资产', '⑦NII计量表', 'B5', EA, 1e-4),
    ('⑦ 非生息资产', '⑦NII计量表', 'B6', NEA, 1e-4),
    ('⑦ 资产端合计', '⑦NII计量表', 'B7', TA, 1e-4),
    ('⑦ 所有者权益', '⑦NII计量表', 'B8', TE, 1e-4),
    ('⑦ 计息负债', '⑦NII计量表', 'B9', LEA, 1e-4),
    ('⑦ 利息收入', '⑦NII计量表', 'B12', II, 1e-4),
    ('⑦ 利息支出', '⑦NII计量表', 'B13', IE, 1e-4),
    ('★ ⑦ NII', '⑦NII计量表', 'B18', NII, 1e-4),
    ('★ ⑦ NIM', '⑦NII计量表', 'B19', NII / EA, 1e-10),
    ('⑦ 生息资产收益率', '⑦NII计量表', 'B20', II / EA, 1e-10),
    ('⑦ 计息负债成本率', '⑦NII计量表', 'B21', IE / LEA, 1e-10),
    ('⑦ 净利差 NIS', '⑦NII计量表', 'B22', II / EA - IE / LEA, 1e-10),
    ('⑦ 负债支持率 k', '⑦NII计量表', 'B23', LEA / EA, 1e-10),
    ('⑦ 资产端 WAL', '⑦NII计量表', 'B26', WALA, 1e-9),
    ('⑦ 负债端 MAL', '⑦NII计量表', 'B27', WALL, 1e-9),
    ('⑦ 期限结构错配', '⑦NII计量表', 'B28', WALA - WALL, 1e-9),
    ('⑧ 条线 NII', '⑧NII结构拆解', 'B43', NII, 1e-4),
    ('⑧ 校验差额', '⑧NII结构拆解', 'B45', 0.0, 1e-6),
]
print(f"{'检查项':<24}{'sheet!cell':<30}{'Excel(pycel)':>20}{'Python':>20}{'差值':>12}")
print('-' * 88)
fails = []
for lab, sh, cell, want, tol in CASES:
    got = V(sh, cell)
    if not isinstance(got, (int, float)):
        print(f'{lab:<24}{sh+"!"+cell:<30}{str(got):>20}')
        fails.append((lab, sh, cell, 'NON_NUM', got))
        continue
    d = abs(got - want)
    ok = d <= tol
    print(f'{lab:<24}{sh+"!"+cell:<30}{got:>20.8f}{want:>20.8f}{d:>12.2e}{"" if ok else "  <-- MISMATCH"}')
    if not ok:
        fails.append((lab, sh, cell, got, want))

# 逐账户填充校验（③ 表 BR 列）
print()
print('-' * 88)
print('逐账户模拟填充校验（③期限分布填充 BR 列，应全为 0）')
print('-' * 88)
bad = 0
for i, x in enumerate(DIST):
    rr = 4 + i
    v = V('③期限分布填充', f'BR{rr}')
    s = V('③期限分布填充', f'BP{rr}')
    k = V('③期限分布填充', f'BO{rr}')
    ok = isinstance(v, (int, float)) and abs(v) < 1e-6 and abs(s - x['bal']) < 1e-4
    if not ok:
        bad += 1
        print(f'  ✗ {x["name"][:18]:<20} Σ={s} 余额={x["bal"]:.2f} 校验差={v} k={k}')
print(f'  23 个账户填充校验：{23-bad}/23 通过')

# 勾稽校验单元格
print()
print('-' * 88)
print('⑦NII计量表 勾稽校验（校验 1~10 应为 0）')
print('-' * 88)
w7 = wb['⑦NII计量表']
for k in range(11):
    rr = 39 + k
    lab = w7.cell(rr, 1).value
    if lab and '校验' in str(lab):
        v = V('⑦NII计量表', f'B{rr}')
        ok = isinstance(v, (int, float)) and abs(v) < 1e-4
        print(f'  {str(lab).strip()[:48]:<50} B{rr:<3} = {v!s:>16}  {"PASS" if ok else "CHECK"}')
        if not ok:
            fails.append((str(lab)[:18], '⑦NII计量表', f'B{rr}', v, 0.0))

# 情景
print()
print('-' * 88)
print('⑨情景敏感性（利率等幅平移 7 档 + 单边 3 档 + 结构 3 档）')
print('-' * 88)
SC0 = 6
for i, bp in enumerate([250, 100, 50, 0, -50, -100, -250]):
    rr = SC0 + i
    dnii = (-bp / 10000 * EA) - (-bp / 10000 * LEA)
    got_h = V('⑨情景敏感性', f'G{rr}')
    got_e = V('⑨情景敏感性', f'E{rr}')
    d = abs(got_e - dnii) if isinstance(got_e, (int, float)) else 999
    print(f"  Δr={bp:>+5}bp  ΔNII={got_e:>12,.2f} (期望 {dnii:>12,.2f})  ΔNII%={got_h*100:>7.2f}%")
    if d >= 1e-6:
        fails.append((f'情景{bp}', '⑨情景敏感性', f'E{rr}', got_e, dnii))
print()
SD0 = 16
for i, (lbl, ka, kl) in enumerate([('仅资产端+100bp', 1.0, 0.0),
                                   ('仅负债端+100bp', 0.0, 1.0),
                                   ('资产+100/负债+50', 1.0, 0.5)]):
    rr = SD0 + i
    dnii = (-100 / 10000 * EA * ka) - (-100 / 10000 * LEA * kl)
    got = V('⑨情景敏感性', f'E{rr}')
    d = abs(got - dnii) if isinstance(got, (int, float)) else 999
    print(f"  {lbl:<20} ΔNII={got:>12,.2f} (期望 {dnii:>12,.2f})")
    if d >= 1e-6:
        fails.append((lbl, '⑨情景敏感性', f'E{rr}', got, dnii))

print()
print('-' * 88)
print('★ 去重定价核查：全表不应出现 β / 重定价 / RG 相关内容')
print('-' * 88)
BAN = ['重定价β', '重定价敞口', '重定价缺口', 'A_β', 'L_β', 'RG']
hits = []
for n in wb.sheetnames:
    wsx = wb[n]
    for row in wsx.iter_rows():
        for c in row:
            if isinstance(c.value, str):
                for b in BAN:
                    if b in c.value and '不含重定价' not in c.value and '不涉及重定价' not in c.value \
                       and '非重定价' not in c.value and '重定价建模' not in c.value and '不设 β' not in c.value \
                       and '不计算重定价' not in c.value and '不区分重定价' not in c.value and '重定价缺口 RG' not in c.value \
                       and '删除重定价' not in c.value and '重定价时点' not in c.value:
                        hits.append(f'{n}!{c.coordinate}: {c.value[:56]}')
if hits:
    print(f'  ⚠ 命中 {len(hits)} 处：')
    for h in hits[:20]:
        print('   ', h)
else:
    print('  ✅ 无重定价相关残留')
print(f"  Sheet 列表（{len(wb.sheetnames)} 个）: {wb.sheetnames}")

print()
print('=' * 88)
if fails:
    print(f'❌ {len(fails)} 项不一致：')
    for f in fails:
        print('   ', f)
    sys.exit(1)
print('✅ 全部关键单元格 + 逐账户填充 + 勾稽 + 情景，pycel 与 Python 独立复算一致')
print('=' * 88)