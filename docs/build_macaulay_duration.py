"""麦考林久期 (Macaulay Duration) 计量模版 v2 — 全公式联动版

改动 vs v1:
  1. 新增「折现数据源」sheet: 收益率曲线 64 段 + 折现因子公式 + 24 账户 × 64 现金流
  2. 所有计算单元格改为 Excel 公式 (SUMPRODUCT / SUMIF 等), 修改源头自动联动
  3. 麦考林久期计算表 / 久期缺口 / 期限分布 全部引用「折现数据源」

公式设计:
  折现数据源 sheet:
    B 列 = 收益率 (可改, 联动全局)
    C 列 = 期限(年)
    D 列 = 折现因子 = 1/(1+B/100)^C      ← 公式
    E:V 列 = 24 个账户的现金流 (可改)

  麦考林久期计算表:
    PV 合计   = SUMPRODUCT(折现数据源!E$5:E$68, 折现数据源!$D$5:$D$68)
    Σ t×PV    = SUMPRODUCT(折现数据源!E$5:E$68, 折现数据源!$D$5:$D$68, 折现数据源!$C$5:$C$68)
    麦考林久期 = Σt×PV / PV合计
    修正久期   = D_mac / (1 + 加权平均收益率)
"""
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule

OUTPUT_PATH = r"C:/银行经营/PRCP/docs/v2/MacaulayDuration_计量模版.xlsx"

# ===================== 1. 读取源数据 =====================
wb_src = load_workbook(r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v5.xlsx",
                       data_only=True)
ws_src = wb_src['基础数据']

# 收益率曲线 (B48-B111, 64 段, 单位 %)
YIELD_CURVE = [ws_src.cell(r, 2).value or 0 for r in range(48, 112)]

# 64 个期限 (年) + 标签
TENORS = [(m + 1) / 12 for m in range(60)] + [10.0, 15.0, 20.0, 30.0]
TENOR_LABELS = [f"{m}M" for m in range(1, 61)] + ["10Y", "15Y", "20Y", "30Y"]

# 账户 (R4-R43, 只取末级)
ACCOUNTS = []
for r in range(4, 44):
    sid = ws_src.cell(r, 3).value
    name = ws_src.cell(r, 4).value
    is_leaf = ws_src.cell(r, 7).value
    balance = ws_src.cell(r, 140).value or 0
    cf = [ws_src.cell(r, c).value or 0 for c in range(76, 140)]

    if not sid or str(sid).strip() == '':
        continue
    if is_leaf != 1:
        continue
    if not isinstance(balance, (int, float)):
        balance = 0
    balance = balance / 10          # v5 文件 C140 有 10 倍单位误差

    ACCOUNTS.append({
        'sid': sid,
        'name': (name or '').strip(),
        'balance': balance,
        'cf': cf,
    })

N_ACC = len(ACCOUNTS)
N_TEN = len(TENORS)
print(f"已加载 {N_ACC} 个末级账户, 收益率曲线 {len(YIELD_CURVE)} 段")


def is_asset(sid):  return sid.startswith('S01')
def is_liab(sid):   return sid.startswith('S02')
def is_equity(sid): return sid.startswith('S03')


# ===================== 2. Python 侧预计算 (校验用) =====================
def calc_dur(cf, rates):
    pv = tp = 0.0
    for i in range(N_TEN):
        r = rates[i] / 100
        p = cf[i] / (1 + r) ** TENORS[i]
        pv += p
        tp += TENORS[i] * p
    mac = tp / pv if pv else 0.0
    y = sum(rates[i] / 100 * (cf[i] / (1 + rates[i] / 100) ** TENORS[i])
            for i in range(N_TEN)) / pv if pv else 0.0
    return pv, tp, mac, mac / (1 + y), y


for a in ACCOUNTS:
    a['pv'], a['tpv'], a['mac'], a['mod'], a['y'] = calc_dur(a['cf'], YIELD_CURVE)

A_PV = sum(a['pv'] for a in ACCOUNTS if is_asset(a['sid']))
L_PV = sum(a['pv'] for a in ACCOUNTS if is_liab(a['sid']))
A_TPV = sum(a['tpv'] for a in ACCOUNTS if is_asset(a['sid']))
L_TPV = sum(a['tpv'] for a in ACCOUNTS if is_liab(a['sid']))
A_MAC = A_TPV / A_PV
L_MAC = L_TPV / L_PV
A_Y = sum(a['y'] * a['pv'] for a in ACCOUNTS if is_asset(a['sid'])) / A_PV
L_Y = sum(a['y'] * a['pv'] for a in ACCOUNTS if is_liab(a['sid'])) / L_PV
GAP = A_MAC - L_MAC

print(f"  资产 D_mac={A_MAC:.4f}年  负债 D_mac={L_MAC:.4f}年  GAP={GAP:+.4f}年")


# ===================== 3. 样式 =====================
wb = Workbook()
wb.remove(wb.active)

B = Border(*(Side(style="thin", color="DDDDDD"),) * 4)
F_TITLE = Font(name="微软雅黑", size=14, bold=True, color="C7000B")
F_HDR = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
FILL_HDR = PatternFill("solid", fgColor="C7000B")
FILL_TITLE = PatternFill("solid", fgColor="FFF3E0")
FILL_KEY = PatternFill("solid", fgColor="FFE082")
FILL_GOOD = PatternFill("solid", fgColor="C8E6C9")
FILL_WARN = PatternFill("solid", fgColor="FFF9C4")
FILL_BAD = PatternFill("solid", fgColor="FFCDD2")
FILL_ASSET = PatternFill("solid", fgColor="E3F2FD")
FILL_LIAB = PatternFill("solid", fgColor="FFF3E0")
FILL_INPUT = PatternFill("solid", fgColor="E8F5E9")     # 可编辑输入区
FILL_FORMULA = PatternFill("solid", fgColor="F3E5F5")   # 公式区


def hdr(ws, row, labels):
    for i, h in enumerate(labels, 1):
        c = ws.cell(row, i, h)
        c.font = F_HDR
        c.fill = FILL_HDR
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = B


def title(ws, ncols, text, sub=None):
    ws.merge_cells(f"A1:{get_column_letter(ncols)}1")
    ws.cell(1, 1, text)
    ws.cell(1, 1).font = F_TITLE
    ws.cell(1, 1).fill = FILL_TITLE
    ws.cell(1, 1).alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30
    if sub:
        ws.merge_cells(f"A2:{get_column_letter(ncols)}2")
        ws.cell(2, 1, sub)
        ws.cell(2, 1).font = Font(name="微软雅黑", size=9, italic=True, color="666666")
        ws.cell(2, 1).alignment = Alignment(horizontal="center", vertical="center")


# ===================== Sheet 1: 折现数据源 =====================
ws0 = wb.create_sheet("折现数据源")
NCOL0 = 4 + N_ACC     # A期限 B年数 C利率 D折现因子 + 24 账户

title(ws0, min(NCOL0, 10),
      "折现数据源 (Discount Data Source) — 收益率曲线 + 折现因子 + 账户现金流",
      "🟢 绿区 = 可编辑输入 (收益率/现金流)  |  🟣 紫区 = 自动计算 (折现因子)  |  "
      "修改此处，下游所有 sheet 自动联动")

hdr_labels = ["期限", "年数 (t)", "利率 r_t (%)", "折现因子 DF_t = 1/(1+r/100)^t"]
for i, h in enumerate(hdr_labels, 1):
    ws0.cell(3, i, h)
for j, a in enumerate(ACCOUNTS):
    kind = "资产" if is_asset(a['sid']) else ("负债" if is_liab(a['sid']) else "权益")
    c = ws0.cell(3, 5 + j, f"{a['sid'][-6:]}\n{a['name'][:12]}\n({kind})")
    c.font = F_HDR
    c.fill = PatternFill("solid", fgColor="1565C0" if is_asset(a['sid'])
                        else ("E65100" if is_liab(a['sid']) else "616161"))
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = B
ws0.row_dimensions[3].height = 42

DF_R0 = 4                             # 数据起始行
DF_R1 = DF_R0 + N_TEN - 1              # 末行 = 67

for i in range(N_TEN):
    r = DF_R0 + i
    # A 期限标签
    ws0.cell(r, 1, TENOR_LABELS[i]).font = Font(name="微软雅黑", size=9, bold=True)
    ws0.cell(r, 1).alignment = Alignment(horizontal="center", vertical="center")
    ws0.cell(r, 1).border = B

    # B 年数 (固定值)
    ws0.cell(r, 2, round(TENORS[i], 6))
    ws0.cell(r, 2).number_format = "0.000000"
    ws0.cell(r, 2).font = Font(name="微软雅黑", size=9)
    ws0.cell(r, 2).alignment = Alignment(horizontal="center")
    ws0.cell(r, 2).border = B

    # C 利率 (输入)
    ws0.cell(r, 3, YIELD_CURVE[i])
    ws0.cell(r, 3).number_format = "0.0000"
    ws0.cell(r, 3).font = Font(name="微软雅黑", size=9, color="1B5E20")
    ws0.cell(r, 3).fill = FILL_INPUT
    ws0.cell(r, 3).alignment = Alignment(horizontal="center")
    ws0.cell(r, 3).border = B

    # D 折现因子 (公式)
    ws0.cell(r, 4, f"=1/(1+C{r}/100)^B{r}")
    ws0.cell(r, 4).number_format = "0.00000000"
    ws0.cell(r, 4).font = Font(name="微软雅黑", size=9, color="6A1B9A")
    ws0.cell(r, 4).fill = FILL_FORMULA
    ws0.cell(r, 4).alignment = Alignment(horizontal="center")
    ws0.cell(r, 4).border = B

    # E.. 现金流 (输入)
    for j, a in enumerate(ACCOUNTS):
        c = ws0.cell(r, 5 + j, round(a['cf'][i] / 1e8, 4))   # 单位: 亿元
        c.number_format = "#,##0.0000"
        c.font = Font(name="微软雅黑", size=8, color="1B5E20")
        c.fill = FILL_INPUT
        c.alignment = Alignment(horizontal="right")
        c.border = B

ws0.column_dimensions["A"].width = 8
ws0.column_dimensions["B"].width = 11
ws0.column_dimensions["C"].width = 12
ws0.column_dimensions["D"].width = 16
for j in range(N_ACC):
    ws0.column_dimensions[get_column_letter(5 + j)].width = 13

ws0.freeze_panes = "E4"

# 底部说明
r = DF_R1 + 2
notes0 = [
    "【数据来源】prcp_basic_20251231_v5.xlsx → 基础数据 sheet",
    "  · 收益率曲线: B48-B111 = 64 段 (中债登 2025-12-31 + 线性插值)",
    "  · 现金流: C76-C139 = 剩余·1M-60M (60 段) + 剩余·10Y/15Y/20Y/30Y (4 段)",
    "  · 账户范围: 24 个末级账户 (is_leaf=1), 已剔除汇总行避免重复计算",
    "",
    "【单位说明】",
    "  · 利率列单位 = % (如 1.27 表示 1.27%)",
    "  · 现金流列单位 = 亿元",
    "  · 折现因子 = 1/(1 + 利率/100)^年数, 无量纲",
    "",
    "【联动关系】",
    "  · 修改 C 列 (利率) → D 列折现因子重算 → 麦考林久期计算表 / 久期缺口 / 期限分布 全部自动更新",
    "  · 修改 E 列及以后 (现金流) → 同上",
]
for t in notes0:
    ws0.merge_cells(f"A{r}:{get_column_letter(min(6, NCOL0))}{r}")
    ws0.cell(r, 1, t)
    ws0.cell(r, 1).font = Font(name="微软雅黑", size=9,
                               bold=t.startswith("【"),
                               color="C7000B" if t.startswith("【") else "666666")
    ws0.cell(r, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    r += 1


# ===================== Sheet 2: 麦考林久期计算表 =====================
ws1 = wb.create_sheet("麦考林久期计算表")
title(ws1, 10,
      "麦考林久期计量表 (Macaulay Duration) — 中信银行 2025-12-31",
      "D_mac = Σ(t × PV_t) / Σ(PV_t)  |  D_mod = D_mac / (1 + y_avg)  |  "
      "所有数值均由「折现数据源」sheet 公式计算，联动更新")

hdr(ws1, 4, ["账户编码", "账户名称", "大类", "当前余额 (亿元)", "PV 合计 (亿元)",
             "Σ t×PV (亿元·年)", "麦考林久期 (年)", "修正久期 (年)",
             "加权平均收益率 (%)", "PV 占比 (%)"])
ws1.row_dimensions[4].height = 32

# 列映射: 折现数据源 E..AB = 账户 0..23
COL_SRC = [get_column_letter(5 + j) for j in range(N_ACC)]

ROW1 = 5
for j, a in enumerate(ACCOUNTS):
    r = ROW1 + j
    src = f"折现数据源!{COL_SRC[j]}${DF_R0}:{COL_SRC[j]}${DF_R1}"
    kind = "资产" if is_asset(a['sid']) else ("负债" if is_liab(a['sid']) else "权益")

    ws1.cell(r, 1, a['sid'])
    ws1.cell(r, 2, a['name'])
    ws1.cell(r, 3, kind)
    ws1.cell(r, 4, round(a['balance'] / 1e8, 2))           # 余额

    # E: PV = SUMPRODUCT(CF, DF) — 纵向数组, WPS/Excel/pycel 通用
    ws1.cell(r, 5, f"=SUMPRODUCT(折现数据源!{COL_SRC[j]}${DF_R0}:"
                   f"{COL_SRC[j]}${DF_R1},折现数据源!$D${DF_R0}:$D${DF_R1})")
    # F: Σt×PV = SUMPRODUCT(CF, DF, t)
    ws1.cell(r, 6, f"=SUMPRODUCT(折现数据源!{COL_SRC[j]}${DF_R0}:"
                   f"{COL_SRC[j]}${DF_R1},折现数据源!$D${DF_R0}:$D${DF_R1},"
                   f"折现数据源!$B${DF_R0}:$B${DF_R1})")
    # G: D_mac = F/E
    ws1.cell(r, 7, f"=IF(E{r}=0,0,F{r}/E{r})")
    # I: y_avg = SUMPRODUCT(CF, r/100, DF) / PV
    ws1.cell(r, 9, f"=IF(E{r}=0,0,SUMPRODUCT(折现数据源!{COL_SRC[j]}${DF_R0}:"
                   f"{COL_SRC[j]}${DF_R1},折现数据源!$C${DF_R0}:$C${DF_R1}/100,"
                   f"折现数据源!$D${DF_R0}:$D${DF_R1})/E{r})")
    # H: D_mod = D_mac / (1 + y)
    ws1.cell(r, 8, f"=IF(I{r}=0,G{r},G{r}/(1+I{r}))")
    # J: PV 占比
    ws1.cell(r, 10, f"=IF(SUM($E${ROW1}:$E${ROW1+N_ACC-1})=0,0,"
                    f"E{r}/SUM($E${ROW1}:$E${ROW1+N_ACC-1}))")

    for c in range(1, 11):
        cell = ws1.cell(r, c)
        cell.border = B
        cell.font = Font(name="微软雅黑", size=9)
        cell.alignment = Alignment(
            horizontal="left" if c == 2 else "center", vertical="center")
        if c in (4, 5, 6):
            cell.number_format = "#,##0.00"
        elif c in (7, 8):
            cell.number_format = "0.0000"
        elif c == 9:
            cell.number_format = "0.0000"
        elif c == 10:
            cell.number_format = "0.00"
        if kind == "资产":
            cell.fill = FILL_ASSET
        elif kind == "负债":
            cell.fill = FILL_LIAB
        if c in (5, 6, 7, 8, 9, 10):
            cell.font = Font(name="微软雅黑", size=9, color="6A1B9A")

SUM1 = ROW1 + N_ACC       # 汇总起始行

# 资产汇总 (SUMIF 按大类)
ws1.merge_cells(f"A{SUM1}:D{SUM1}")
ws1.cell(SUM1, 1, "组合汇总")
for c in range(1, 5):
    ws1.cell(SUM1, c).font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    ws1.cell(SUM1, c).fill = PatternFill("solid", fgColor="C7000B")
    ws1.cell(SUM1, c).alignment = Alignment(horizontal="center", vertical="center")
    ws1.cell(SUM1, c).border = B

agg_rows = [
    (SUM1 + 1, "资产", FILL_ASSET, "1565C0"),
    (SUM1 + 2, "负债", FILL_LIAB, "E65100"),
    (SUM1 + 3, "权益", PatternFill("solid", fgColor="ECEFF1"), "616161"),
]
for rr, label, fill, color in agg_rows:
    ws1.cell(rr, 5, f'=SUMIF($C${ROW1}:$C${ROW1+N_ACC-1},"{label}",'
                    f'$E${ROW1}:$E${ROW1+N_ACC-1})')
    ws1.cell(rr, 6, f'=SUMIF($C${ROW1}:$C${ROW1+N_ACC-1},"{label}",'
                    f'$F${ROW1}:$F${ROW1+N_ACC-1})')
    ws1.cell(rr, 7, f"=IF(E{rr}=0,0,F{rr}/E{rr})")
    # y_avg = SUMPRODUCT(本组的 y_i × PV_i) / SUM(本组 PV_i)
    ws1.cell(rr, 9, f'=IF(E{rr}=0,0,SUMPRODUCT(($C${ROW1}:$C${ROW1+N_ACC-1}="{label}")'
                   f'*$I${ROW1}:$I${ROW1+N_ACC-1}*$E${ROW1}:$E${ROW1+N_ACC-1})/E{rr})')
    ws1.cell(rr, 8, f"=IF(I{rr}=0,G{rr},G{rr}/(1+I{rr}))")
    ws1.cell(rr, 10, f"=IF(SUM($E${ROW1}:$E${ROW1+N_ACC-1})=0,0,"
                    f"E{rr}/SUM($E${ROW1}:$E${ROW1+N_ACC-1}))")
    ws1.cell(rr, 5).value = ws1.cell(rr, 5).value   # keep
    for c in range(5, 11):
        cell = ws1.cell(rr, c)
        cell.font = Font(name="微软雅黑", size=10, bold=True, color="6A1B9A")
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = B
        if c in (5, 6):
            cell.number_format = "#,##0.00"
        elif c in (7, 8, 9):
            cell.number_format = "0.0000"
        elif c == 10:
            cell.number_format = "0.00"
    ws1.cell(rr, 5).font = Font(name="微软雅黑", size=10, bold=True, color=color)

# 缺口行
GP_ROW = SUM1 + 4
ws1.cell(GP_ROW, 5, "DA - DL")
ws1.cell(GP_ROW, 7, f"=G{SUM1+1}-G{SUM1+2}")
ws1.cell(GP_ROW, 8, f"=H{SUM1+1}-H{SUM1+2}")
for c in range(5, 11):
    cell = ws1.cell(GP_ROW, c)
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
    cell.fill = FILL_KEY
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = B
    if c in (7, 8):
        cell.number_format = "+0.0000;-0.0000;0"
ws1.cell(GP_ROW, 5).font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
ws1.cell(GP_ROW, 5).alignment = Alignment(horizontal="center", vertical="center")
ws1.cell(GP_ROW, 9, "")
ws1.cell(GP_ROW, 10, "")

for w, c in zip([22, 24, 8, 15, 16, 18, 16, 16, 16, 12], range(1, 11)):
    ws1.column_dimensions[get_column_letter(c)].width = w
ws1.freeze_panes = "D5"

# 缺口解读 (公式联动, 直接引用单元格, 避免定义名称兼容性问题)
GAP_REF = f"'麦考林久期计算表'!$G${GP_ROW}"


# ===================== Sheet 3: 久期缺口与敏感性 =====================
ws2 = wb.create_sheet("久期缺口与敏感性")
title(ws2, 7, "久期缺口 (Duration Gap) 与 NII 利率敏感性",
      "GAP = DA - DL  |  ΔNII/NII ≈ -GAP × Δr  |  引用「麦考林久期计算表」汇总行，联动更新")

hdr(ws2, 4, ["情景", "Δr (%)", "资产久期 DA (年)", "负债久期 DL (年)",
             "久期缺口 GAP (年)", "NII 敏感度 (%)", "说明"])
ws2.row_dimensions[4].height = 32

SCEN = [
    ("基准情景",       0.0,   "基准, 无冲击"),
    ("平行上移 250bp", 0.025, "利率上行 → 正缺口银行 NII 受损"),
    ("平行下移 250bp", -0.025, "利率下行 → 正缺口银行 NII 受益"),
    ("变陡峭",        0.005, "长期利率上行, 加权 Δr ≈ +50bp"),
    ("变平坦",        -0.005, "短期利率下行, 加权 Δr ≈ -50bp"),
]

for i, (nm, dr, note) in enumerate(SCEN):
    r = 5 + i
    ws2.cell(r, 1, nm)
    ws2.cell(r, 2, round(dr * 100, 3))
    ws2.cell(r, 3, f"='麦考林久期计算表'!G{SUM1+1}")
    ws2.cell(r, 4, f"='麦考林久期计算表'!G{SUM1+2}")
    ws2.cell(r, 5, f"=C{r}-D{r}")
    ws2.cell(r, 6, f"=-E{r}*B{r}/100*100")   # -GAP × Δr (Δr 已用 % 数值)
    ws2.cell(r, 7, note)

    for c in range(1, 8):
        cell = ws2.cell(r, c)
        cell.border = B
        cell.font = Font(name="微软雅黑", size=10, bold=(c in (1, 5)))
        cell.alignment = Alignment(
            horizontal="left" if c == 7 else "center", vertical="center")
        if c in (3, 4, 5):
            cell.number_format = "0.0000"
        elif c in (2, 6):
            cell.number_format = "+0.0000;-0.0000;0"
        if c in (3, 4, 5, 6):
            cell.font = Font(name="微软雅黑", size=10, bold=(c == 5),
                             color="6A1B9A")
    ws2.cell(r, 5).fill = FILL_KEY if i == 0 else FILL_WARN
    ws2.cell(r, 6).fill = FILL_KEY if i == 0 else FILL_BAD

# 缺口解读 (公式联动)
r = 12
ws2.merge_cells(f"A{r}:G{r}")
ws2.cell(r, 1, "久期缺口解读 (自动联动)")
ws2.cell(r, 1).font = Font(name="微软雅黑", size=12, bold=True, color="C7000B")
ws2.cell(r, 1).fill = FILL_TITLE
ws2.cell(r, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)

interp = [
    ("久期缺口类型", f'=IF({GAP_REF}>0,"正缺口 (资产久期 > 负债久期)",'
                     f'IF({GAP_REF}<0,"负缺口 (资产久期 < 负债久期)","零缺口"))'),
    ("GAP 值", f'=TEXT({GAP_REF},"+0.0000;-0.0000")&" 年"'),
    ("利率 +25bp 的 NII 影响", f'=TEXT(-{GAP_REF}*0.025*100,"+0.0000")&"% ("&'
                               f'IF(-{GAP_REF}>0,"NII 受损","NII 受益")&")"'),
    ("利率 -25bp 的 NII 影响", f'=TEXT({GAP_REF}*0.025*100,"+0.0000")&"% ("&'
                               f'IF({GAP_REF}>0,"NII 受损","NII 受益")&")"'),
    ("管理含义", f'=IF({GAP_REF}>0,'
                 '"正缺口银行: 利率上行期重定价压力, 需通过拉长久期负债或配置长久期资产对冲",'
                 '"负缺口银行: 利率下行期承压, 负债重定价快于资产, 建议缩短资产久期")'),
    ("调节手段", "① 发行长期同业存单 / 金融债拉长久期负债  "
               "② 配置长久期债券 / 拉长久期贷款  "
               "③ 利率衍生品对冲 (国债期货 / 利率互换)"),
]

for k, v in interp:
    ws2.cell(r + 1, 1, k).font = Font(name="微软雅黑", size=10, bold=True)
    ws2.cell(r + 1, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws2.cell(r + 1, 1).border = B
    ws2.merge_cells(f"B{r+1}:G{r+1}")
    ws2.cell(r + 1, 2, v)
    ws2.cell(r + 1, 2).font = Font(name="微软雅黑", size=10, color="6A1B9A")
    ws2.cell(r + 1, 2).alignment = Alignment(horizontal="left", vertical="center",
                                            wrap_text=True)
    for c in range(2, 8):
        ws2.cell(r + 1, c).border = B
    r += 1

for w, c in zip([22, 12, 18, 18, 18, 18, 42], range(1, 8)):
    ws2.column_dimensions[get_column_letter(c)].width = w


# ===================== Sheet 4: 期限分布分析 =====================
ws3 = wb.create_sheet("期限分布分析")
title(ws3, 8, "现金流期限分布 (按 PV 汇总) — 久期成因拆解",
      "Σ 各账户现金流 × 折现因子, 按期限汇总  |  引用「折现数据源」sheet，联动更新")

hdr(ws3, 4, ["期限", "年数 (t)", "利率 (%)", "折现因子", "资产 PV (亿元)",
             "负债 PV (亿元)", "资产 PV 占比 (%)", "累计占比 (%)"])
ws3.row_dimensions[4].height = 32

# 资产/负债列号集合
ASSET_JS = [5 + j for j, a in enumerate(ACCOUNTS) if is_asset(a['sid'])]
LIAB_JS = [5 + j for j, a in enumerate(ACCOUNTS) if is_liab(a['sid'])]

ROW3 = 5
for i in range(N_TEN):
    r = ROW3 + i
    src_r = DF_R0 + i
    ws3.cell(r, 1, f"=折现数据源!A{src_r}")
    ws3.cell(r, 2, f"=折现数据源!B{src_r}")
    ws3.cell(r, 3, f"=折现数据源!C{src_r}")
    ws3.cell(r, 4, f"=折现数据源!D{src_r}")

    # 资产 PV: 逐账户 CF×DF 显式累加 (只用本行的 DF, 避免整列区间重复累加)
    ws3.cell(r, 5, "=" + "+".join(
        f"折现数据源!{get_column_letter(c)}{src_r}*折现数据源!$D${src_r}"
        for c in ASSET_JS))
    ws3.cell(r, 6, "=" + "+".join(
        f"折现数据源!{get_column_letter(c)}{src_r}*折现数据源!$D${src_r}"
        for c in LIAB_JS))

    for c in range(1, 7):
        cell = ws3.cell(r, c)
        cell.border = B
        cell.font = Font(name="微软雅黑", size=9)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        if c == 2:
            cell.number_format = "0.000000"
        elif c == 3:
            cell.number_format = "0.0000"
        elif c == 4:
            cell.number_format = "0.00000000"
        elif c in (5, 6):
            cell.number_format = "#,##0.00"
            cell.font = Font(name="微软雅黑", size=9, color="6A1B9A")

ROW3_END = ROW3 + N_TEN - 1
# 占比 + 累计
for i in range(N_TEN):
    r = ROW3 + i
    ws3.cell(r, 7, f"=IF(SUM($E${ROW3}:$E${ROW3_END})=0,0,"
                   f"E{r}/SUM($E${ROW3}:$E${ROW3_END}))")
    if i == 0:
        ws3.cell(r, 8, f"=G{r}")
    else:
        ws3.cell(r, 8, f"=H{r-1}+G{r}")
    for c in (7, 8):
        cell = ws3.cell(r, c)
        cell.border = B
        cell.font = Font(name="微软雅黑", size=9, color="6A1B9A")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.number_format = "0.00"

TOT3 = ROW3_END + 1
ws3.merge_cells(f"A{TOT3}:D{TOT3}")
ws3.cell(TOT3, 1, "合计")
for c in range(1, 5):
    ws3.cell(TOT3, c).font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    ws3.cell(TOT3, c).fill = PatternFill("solid", fgColor="C7000B")
    ws3.cell(TOT3, c).alignment = Alignment(horizontal="center", vertical="center")
    ws3.cell(TOT3, c).border = B
ws3.cell(TOT3, 5, f"=SUM(E{ROW3}:E{ROW3_END})")
ws3.cell(TOT3, 6, f"=SUM(F{ROW3}:F{ROW3_END})")
ws3.cell(TOT3, 7, f"=SUM(G{ROW3}:G{ROW3_END})")
for c in range(5, 9):
    cell = ws3.cell(TOT3, c)
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = B
    if c in (5, 6):
        cell.number_format = "#,##0.00"
    else:
        cell.number_format = "0.00"

# 久期贡献拆解
DEC3 = TOT3 + 2
ws3.merge_cells(f"A{DEC3}:D{DEC3}")
ws3.cell(DEC3, 1, "久期贡献拆解 (Σ t×PV / Σ PV)")
ws3.cell(DEC3, 1).font = Font(name="微软雅黑", size=11, bold=True, color="C7000B")
ws3.cell(DEC3, 1).fill = FILL_TITLE
ws3.cell(DEC3, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)

dec = [
    ("资产加权平均年数 Σ(t×PV)/Σ(PV)",
     f"=SUMPRODUCT(B{ROW3}:B{ROW3_END},E{ROW3}:E{ROW3_END})/SUM(E{ROW3}:E{ROW3_END})"),
    ("负债加权平均年数 Σ(t×PV)/Σ(PV)",
     f"=SUMPRODUCT(B{ROW3}:B{ROW3_END},F{ROW3}:F{ROW3_END})/SUM(F{ROW3}:F{ROW3_END})"),
    ("久期缺口 (资产 - 负债)",
     f"=SUMPRODUCT(B{ROW3}:B{ROW3_END},E{ROW3}:E{ROW3_END})/SUM(E{ROW3}:E{ROW3_END})"
     f"-SUMPRODUCT(B{ROW3}:B{ROW3_END},F{ROW3}:F{ROW3_END})/SUM(F{ROW3}:F{ROW3_END})"),
]
for i, (k, f) in enumerate(dec):
    rr = DEC3 + 1 + i
    ws3.cell(rr, 1, k).font = Font(name="微软雅黑", size=10, bold=True)
    ws3.cell(rr, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws3.cell(rr, 1).border = B
    ws3.merge_cells(f"A{rr}:D{rr}")
    for c in range(1, 5):
        ws3.cell(rr, c).border = B
    ws3.cell(rr, 5, f)
    ws3.cell(rr, 5).number_format = "0.0000"
    ws3.cell(rr, 5).font = Font(name="微软雅黑", size=10, bold=True, color="6A1B9A")
    ws3.cell(rr, 5).alignment = Alignment(horizontal="center", vertical="center")
    ws3.cell(rr, 5).fill = FILL_KEY
    ws3.cell(rr, 5).border = B

for w, c in zip([12, 12, 12, 16, 18, 18, 16, 14], range(1, 9)):
    ws3.column_dimensions[get_column_letter(c)].width = w
ws3.freeze_panes = "A5"


# ===================== Sheet 5: 计算逻辑说明 =====================
ws4 = wb.create_sheet("计算逻辑说明")
title(ws4, 3, "麦考林久期计算逻辑说明")

logic = [
    ("【一】基础概念", ""),
    ("麦考林久期", "衡量现金流回到面值的时间 = Σ(t × PV_t) / Σ(PV_t), 单位: 年"),
    ("修正久期", "D_mod = D_mac / (1 + y_avg), 利率变动 1% 时价格变动的百分比"),
    ("久期缺口 GAP", "GAP = 资产久期 DA - 负债久期 DL, 衡量资产负债期限错配"),
    ("加权平均收益率", "y_avg = Σ(r_t × PV_t) / Σ(PV_t), PV 加权"),
    ("", ""),
    ("【二】核心公式", ""),
    ("折现因子", "DF_t = 1 / (1 + r_t/100)^t\n"
               "  r_t = 对应期限国债收益率 (%), t = 期限 (年)"),
    ("单账户久期", "D_i = Σ(t × PV_t) / Σ(PV_t)\n"
                  "  其中 PV_t = CF_t × DF_t"),
    ("组合久期 (PV 加权)", "DA = Σ(D_i × PV_i) / Σ(PV_i)   (i ∈ 资产)\n"
                        "DL = Σ(D_i × PV_i) / Σ(PV_i)   (i ∈ 负债)"),
    ("久期缺口", "GAP = DA - DL"),
    ("修正久期", "D_mod = D_mac / (1 + y_avg)"),
    ("NII 敏感度", "ΔNII/NII ≈ -GAP × Δr\n"
                  "  GAP > 0 (正缺口): 利率上行 → NII 受损"),
    ("", ""),
    ("【三】Sheet 结构与公式联动", ""),
    ("折现数据源", "🟢 C 列 (收益率) + E 列起 (现金流) = 可编辑输入区\n"
                 "🟣 D 列 (折现因子) = 公式 = 1/(1+C/100)^B\n"
                 "  → 修改输入, D 列自动重算"),
    ("麦考林久期计算表", "E 列 PV = SUMPRODUCT(现金流列, 折现因子列)\n"
                     "F 列 Σt×PV = SUMPRODUCT(现金流列, 折现因子列, 年数列)\n"
                     "G 列 D_mac = F/E\n"
                     "H 列 D_mod = G/(1+I)\n"
                     "汇总用 SUMIF 按大类加权聚合"),
    ("久期缺口与敏感性", "C/D 列引用「麦考林久期计算表」汇总行\n"
                     "解读区用 IF/TEXT 函数自动生成文字结论"),
    ("期限分布分析", "按期限汇总 Σ 各账户 CF × DF\n"
                  "底部用 SUMPRODUCT(B,E)/SUM(E) 独立复核久期 (交叉校验)"),
    ("", ""),
    ("【四】数据基础", ""),
    ("来源文件", "prcp_basic_20251231_v5.xlsx → 基础数据 sheet"),
    ("账户范围", "24 个末级账户 (is_leaf=1), 剔除汇总行避免重复计算"),
    ("现金流列", "C76-C139 = 剩余·1M-60M (60 段) + 剩余·10Y/15Y/20Y/30Y (4 段)"),
    ("收益率曲线", "B48-B111 = 64 段国债收益率 (中债登 2025-12-31 + 线性插值)"),
    ("单位", "利率 = %, 现金流 = 亿元, 久期 = 年"),
    ("", ""),
    ("【五】注意事项", ""),
    ("适用性", "麦考林久期假设现金流一次性到期, 对分期偿还的贷款/存款存在偏差\n"
             "生产环境建议用修正久期或利率敏感性 GAP (按重定价期限) 而非到期期限"),
    ("行为假设", "活期存款未做「内核假设」处理, 若按 5 年最长期限重定价, 负债久期会显著上升\n"
              "这是当前负债久期仅 0.32 年的主要原因"),
    ("监管口径", "银保监《商业银行银行账户利率风险计量》要求以重定价期限 (repricing) 为核心,\n"
                "麦考林久期可作为 EVE 分析的补充视角"),
    ("重算提示", "WPS/Excel 打开后如数值未更新, 按 Ctrl+Alt+F9 强制全表重算"),
]

r = 3
for k, v in logic:
    ws4.cell(r, 1, k)
    if k.startswith("【"):
        ws4.merge_cells(f"A{r}:C{r}")
        ws4.cell(r, 1).font = Font(name="微软雅黑", size=11, bold=True, color="C7000B")
        ws4.cell(r, 1).fill = FILL_TITLE
        ws4.cell(r, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws4.row_dimensions[r].height = 24
    elif k:
        ws4.cell(r, 1).font = Font(name="微软雅黑", size=10, bold=True)
        ws4.cell(r, 1).border = B
        ws4.cell(r, 1).alignment = Alignment(horizontal="left", vertical="top", indent=1)
        ws4.merge_cells(f"B{r}:C{r}")
        ws4.cell(r, 2, v)
        ws4.cell(r, 2).font = Font(name="微软雅黑", size=10)
        ws4.cell(r, 2).alignment = Alignment(horizontal="left", vertical="top",
                                            wrap_text=True, indent=1)
        ws4.cell(r, 2).border = B
        ws4.cell(r, 3).border = B
        ws4.row_dimensions[r].height = max(16 * (v.count('\n') + 1), 18)
    r += 1

ws4.column_dimensions["A"].width = 24
ws4.column_dimensions["B"].width = 52
ws4.column_dimensions["C"].width = 26


# ===================== 保存 =====================
wb.save(OUTPUT_PATH)
print(f"\n已保存: {OUTPUT_PATH}")
print(f"Sheets: {wb.sheetnames}")
print(f"预期值校验: DA={A_MAC:.4f} DL={L_MAC:.4f} GAP={GAP:+.4f}")