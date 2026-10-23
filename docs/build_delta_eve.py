"""ΔEVE (Delta Economic Value of Equity) 计量模版

监管: 银保监《商业银行银行账户利率风险计量》
- 4 个利率冲击情景: 平行上移 250bp / 平行下移 250bp / 变陡峭 / 变平坦
- 监管阈值: |ΔEVE| / 一级资本 <= 15%

公式:
  ΔEVE_基准 = Σ PV(资产现金流) - Σ PV(负债现金流)
  ΔEVE_冲击 = Σ PV_冲击(资产现金流) - Σ PV_冲击(负债现金流)
  ΔEVE_变化 = ΔEVE_冲击 - ΔEVE_基准
  ΔEVE/一级资本 = ΔEVE_变化 / 一级资本

数据基础: prcp_basic_20251231_v4.xlsx (账户册 57 行 + 国债收益率曲线 64 段)
"""

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUTPUT_PATH = r"C:/银行经营/PRCP/docs/v2/DeltaEVE_计量模版.xlsx"

# ===================== 1. 加载基准数据 =====================
wb_src = load_workbook(r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v5.xlsx", data_only=True)
ws_src = wb_src['基础数据']

# 读取国债收益率曲线 (B48-B111)
yield_curve = []  # [(年化期限, 利率%)]
for r in range(48, 112):
    rate = ws_src.cell(r, 2).value
    yield_curve.append(rate or 0)

# 读取 38 个账户的现金流 (R4-R43, C75-C138)
accounts = []  # [(账户编码, 账户名称, 现金流列表, 基准PV)]
for r in range(4, 44):
    sid = ws_src.cell(r, 3).value
    name = ws_src.cell(r, 4).value
    is_leaf = ws_src.cell(r, 7).value
    pv = ws_src.cell(r, 11).value  # K 列 PV
    cf = [ws_src.cell(r, c).value or 0 for c in range(76, 140)]  # C76-C139 (剩余·1M-60M + 10Y/15Y/20Y/30Y)

    if not sid or str(sid).strip() == '':
        continue

    # 只加载末级账户 (避免汇总行重复计算)
    if is_leaf != 1:
        continue

    accounts.append({
        'sid': sid,
        'name': (name or '').strip(),
        'is_leaf': is_leaf,
        'cf': cf,  # 60 月度 + 4 年度
        'pv': pv or 0,
    })

print(f"已加载 {len(accounts)} 个账户, 收益率曲线 {len(yield_curve)} 段")

# ===================== 2. 利率冲击情景定义 =====================
# 基准: 当前收益率曲线
# 冲击1: 平行上移 +250bp
# 冲击2: 平行下移 -250bp
# 冲击3: 变陡峭 (短期不变, 长期 +100bp)
# 冲击4: 变平坦 (短期 -100bp, 长期不变)

def shift_yield_curve(curve, scenario):
    """对收益率曲线应用冲击"""
    shifted = list(curve)
    for i, t_years in enumerate([(m+1)/12 for m in range(60)] + [10, 15, 20, 30]):
        if scenario == "up_250":
            shifted[i] = curve[i] + 2.50  # 平行上移 250bp
        elif scenario == "down_250":
            shifted[i] = max(curve[i] - 2.50, 0)  # 平行下移 250bp (不低于 0)
        elif scenario == "steeper":
            # 变陡峭: 短期(<=1Y)不变, 长期(>1Y)线性增加
            if t_years > 1:
                shift = min((t_years - 1) * 1.0, 1.0)  # 1Y 以上每年 +100bp, 上限 100bp
                shifted[i] = curve[i] + shift
        elif scenario == "flatter":
            # 变平坦: 短期(<=1Y)减少 100bp, 长期不变
            if t_years <= 1:
                shifted[i] = max(curve[i] - 1.0, 0)
    return shifted

# ===================== 3. 计算 PV (含利率冲击) =====================
def calc_pv(cf, rates):
    """计算现金流现值, rates 是年化利率列表 (64 个)"""
    pv = 0
    for m in range(1, 61):
        t = m / 12  # 年
        rate = rates[m-1] / 100
        df = 1 / (1 + rate) ** t
        pv += cf[m-1] * df
    # 4 个年度期限 (10Y, 15Y, 20Y, 30Y)
    for i, t in enumerate([10, 15, 20, 30]):
        rate = rates[60 + i] / 100
        df = 1 / (1 + rate) ** t
        pv += cf[60 + i] * df
    return pv

# 计算各冲击情景下 38 个账户的 PV
scenarios = ['baseline', 'up_250', 'down_250', 'steeper', 'flatter']
shifted_curves = {s: shift_yield_curve(yield_curve, s) if s != 'baseline' else yield_curve
                 for s in scenarios}

for acc in accounts:
    acc['pv_scenarios'] = {}
    for s in scenarios:
        acc['pv_scenarios'][s] = calc_pv(acc['cf'], shifted_curves[s])

# 资产端 vs 负债端 分类 (按账户编码前缀)
def is_asset(sid):
    return sid.startswith('S01')

def is_liab(sid):
    return sid.startswith('S02')

def is_equity(sid):
    return sid.startswith('S03')

# 汇总
print("\n=== ΔEVE 计量 (按情景) ===")
for s in scenarios:
    asset_pv = sum(a['pv_scenarios'][s] for a in accounts if is_asset(a['sid']))
    liab_pv = sum(a['pv_scenarios'][s] for a in accounts if is_liab(a['sid']))
    equity_pv = sum(a['pv_scenarios'][s] for a in accounts if is_equity(a['sid']))
    print(f"  {s:<10}: 资产={asset_pv/1e8:>10.0f}亿  负债={liab_pv/1e8:>10.0f}亿  净资产={equity_pv/1e8:>10.0f}亿")

# ΔEVE 计算
tier1_capital = 768217000000  # 一级资本 (假设) ≈ 所有者权益 7862 亿 * 0.85
print(f"\n一级资本: {tier1_capital/1e8:.0f} 亿元")

# ΔEVE 公式: 资产 PV - 负债 PV (不含权益)
# ΔEVE 变化 = 冲击后 (资产PV-负债PV) - 基准 (资产PV-负债PV)
baseline_net = sum(a['pv_scenarios']['baseline'] for a in accounts if is_asset(a['sid'])) - \
              sum(a['pv_scenarios']['baseline'] for a in accounts if is_liab(a['sid']))
print(f"基准 ΔEVE (资产-负债): {baseline_net/1e8:.2f} 亿元")

for s in ['up_250', 'down_250', 'steeper', 'flatter']:
    shock_net = sum(a['pv_scenarios'][s] for a in accounts if is_asset(a['sid'])) - \
                sum(a['pv_scenarios'][s] for a in accounts if is_liab(a['sid']))
    delta_eve_change = shock_net - baseline_net
    ratio = delta_eve_change / tier1_capital
    print(f"  {s:<10}: ΔEVE变化 = {delta_eve_change/1e8:>10.2f}亿  ΔEVE/一级资本 = {ratio*100:>+.2f}%")

# ===================== 4. 创建 Excel =====================
wb = Workbook()
wb.remove(wb.active)

border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===== Sheet 1: ΔEVE 计量主表 =====
ws1 = wb.create_sheet("ΔEVE 计量主表")
ws1.merge_cells("A1:H1")
ws1["A1"] = "ΔEVE 计量模版 (Delta Economic Value of Equity)"
ws1["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws1["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 30

ws1.merge_cells("A2:H2")
ws1["A2"] = "数据日期: 2025-12-31 | 监管: |ΔEVE| / 一级资本 ≤ 15% | 折现方法: 1/(1+r)^t 年复利"
ws1["A2"].font = Font(name="微软雅黑", size=10, italic=True, color="555555")
ws1["A2"].fill = PatternFill("solid", fgColor="FFF3E0")
ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")

# 表头 (R4)
headers1 = ["账户编码", "账户名称", "大类", "基准PV (亿元)", "+250bp PV (亿元)", "-250bp PV (亿元)",
            "变陡峭 PV (亿元)", "变平坦 PV (亿元)"]
for c, h in enumerate(headers1, 1):
    cell = ws1.cell(4, c, h)
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = border
ws1.row_dimensions[4].height = 30

# 38 账户数据 (R5-)
row_idx = 5
for acc in accounts:
    sid = acc['sid']
    if is_asset(sid):
        kind = "ASSET"
    elif is_liab(sid):
        kind = "LIAB"
    else:
        kind = "EQUITY"

    ws1.cell(row_idx, 1, sid)
    ws1.cell(row_idx, 2, acc['name'])
    ws1.cell(row_idx, 3, kind)
    ws1.cell(row_idx, 4, round(acc['pv_scenarios']['baseline']/1e8, 2))
    ws1.cell(row_idx, 5, round(acc['pv_scenarios']['up_250']/1e8, 2))
    ws1.cell(row_idx, 6, round(acc['pv_scenarios']['down_250']/1e8, 2))
    ws1.cell(row_idx, 7, round(acc['pv_scenarios']['steeper']/1e8, 2))
    ws1.cell(row_idx, 8, round(acc['pv_scenarios']['flatter']/1e8, 2))

    for c in range(1, 9):
        cell = ws1.cell(row_idx, c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=9)
        if c == 1:
            cell.alignment = Alignment(horizontal="left", vertical="center")
        elif c == 2:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        elif c == 3:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "#,##0.00"
        # 着色 (ASSET 绿, LIAB 红, EQUITY 黄)
        if c == 3:
            if kind == "ASSET":
                cell.fill = PatternFill("solid", fgColor="E8F5E9")
            elif kind == "LIAB":
                cell.fill = PatternFill("solid", fgColor="FFEBEE")
            else:
                cell.fill = PatternFill("solid", fgColor="FFF9C4")
    row_idx += 1

# 汇总行
summary_row = row_idx
ws1.cell(summary_row, 1, "汇总 (资产-负债)")
ws1.merge_cells(f"A{summary_row}:C{summary_row}")
ws1.cell(summary_row, 1).font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
ws1.cell(summary_row, 1).fill = PatternFill("solid", fgColor="C7000B")
ws1.cell(summary_row, 1).alignment = Alignment(horizontal="center", vertical="center")

for s_idx, s in enumerate(['baseline', 'up_250', 'down_250', 'steeper', 'flatter']):
    col = 4 + s_idx
    asset_pv = sum(a['pv_scenarios'][s] for a in accounts if is_asset(a['sid']))
    liab_pv = sum(a['pv_scenarios'][s] for a in accounts if is_liab(a['sid']))
    # ΔEVE = 资产 PV - 负债 PV (不含权益)
    delta_eve = asset_pv - liab_pv
    ws1.cell(summary_row, col, round(delta_eve/1e8, 2))

for c in range(4, 9):
    cell = ws1.cell(summary_row, c)
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="right", vertical="center")
    cell.number_format = "#,##0.00"
    cell.border = border

# 列宽
for c, w in enumerate([18, 28, 10, 16, 16, 16, 16, 16], 1):
    ws1.column_dimensions[get_column_letter(c)].width = w

# ===== Sheet 2: 利率冲击情景定义 =====
ws2 = wb.create_sheet("利率冲击情景")
ws2.merge_cells("A1:E1")
ws2["A1"] = "利率冲击情景定义 (银保监 4 情景)"
ws2["A1"].font = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
ws2["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 26

scenarios_desc = [
    ("情景代码", "情景名称", "冲击方式", "适用条件", "备注"),
    ("baseline", "基准情景", "当前收益率曲线", "正常计量", "无冲击"),
    ("up_250", "平行上移 250bp", "所有期限利率 +250bp", "上行风险", "标准监管情景"),
    ("down_250", "平行下移 250bp", "所有期限利率 -250bp (不低于 0)", "下行风险", "标准监管情景"),
    ("steeper", "变陡峭", "短期(≤1Y)不变, 长期(>1Y)线性增加, 上限 100bp", "收益率曲线陡峭化", "可选情景"),
    ("flatter", "变平坦", "短期(≤1Y)-100bp, 长期(>1Y)不变", "收益率曲线平坦化", "可选情景"),
]
for r_off, row_data in enumerate(scenarios_desc):
    for c, val in enumerate(row_data, 1):
        cell = ws2.cell(3 + r_off, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        else:
            cell.font = Font(name="微软雅黑", size=9)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

# 公式说明
ws2.merge_cells("A10:E10")
ws2["A10"] = "ΔEVE 公式"
ws2["A10"].font = Font(name="微软雅黑", size=12, bold=True, color="C7000B")
ws2["A10"].fill = PatternFill("solid", fgColor="FFF3E0")
ws2["A10"].alignment = Alignment(horizontal="left", vertical="center")

formulas = [
    "ΔEVE_基准 = Σ(资产现金流 × 折现因子基准) - Σ(负债现金流 × 折现因子基准)",
    "ΔEVE_冲击 = Σ(资产现金流 × 折现因子冲击) - Σ(负债现金流 × 折现因子冲击)",
    "ΔEVE_变化 = ΔEVE_冲击 - ΔEVE_基准",
    "ΔEVE/一级资本 = ΔEVE_变化 / 一级资本 (应 ≤ 15%)",
    "折现因子: DF_t = 1 / (1 + r_t)^t, t 单位: 年",
    "注意: ΔEVE 是经济价值的变化, 不是会计损益",
]
for r_off, f in enumerate(formulas):
    ws2.merge_cells(f"A{12+r_off}:E{12+r_off}")
    cell = ws2.cell(12+r_off, 1, f)
    cell.font = Font(name="Consolas", size=9, color="0070C0")
    cell.fill = PatternFill("solid", fgColor="FFFDE7")
    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

widths2 = [20, 18, 36, 20, 20]
for c, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(c)].width = w

# ===== Sheet 3: 收益率曲线冲击结果 =====
ws3 = wb.create_sheet("收益率曲线冲击")
ws3.merge_cells("A1:F1")
ws3["A1"] = "国债收益率曲线 4 冲击情景结果 (2025-12-31)"
ws3["A1"].font = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
ws3["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 26

# 表头 (R3)
headers3 = ["期限", "年数", "基准利率(%)", "平行上移 250bp(%)", "平行下移 250bp(%)", "变陡峭(%)"]
for c, h in enumerate(headers3, 1):
    cell = ws3.cell(3, c, h)
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = border
ws3.row_dimensions[3].height = 30

# 期限名称
tenor_names = []
for m in range(1, 61):
    tenor_names.append(f"{m}M")
tenor_names.extend(["10Y", "15Y", "20Y", "30Y"])

# 数据
row_idx = 4
for i, (rate_base, rate_up, rate_down, rate_steep) in enumerate(zip(
    yield_curve,
    shifted_curves['up_250'],
    shifted_curves['down_250'],
    shifted_curves['steeper']
)):
    if i < 60:
        t_years = (i + 1) / 12
    else:
        t_years = [10, 15, 20, 30][i - 60]

    ws3.cell(row_idx, 1, tenor_names[i])
    ws3.cell(row_idx, 2, round(t_years, 4))
    ws3.cell(row_idx, 3, round(rate_base, 4))
    ws3.cell(row_idx, 4, round(rate_up, 4))
    ws3.cell(row_idx, 5, round(rate_down, 4))
    ws3.cell(row_idx, 6, round(rate_steep, 4))

    for c in range(1, 7):
        cell = ws3.cell(row_idx, c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=9)
        if c == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.font = Font(name="微软雅黑", size=9, bold=True)
        elif c == 2:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "0.0000"
        else:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "0.0000"
    row_idx += 1

# 列宽
for c, w in enumerate([10, 10, 18, 22, 22, 16], 1):
    ws3.column_dimensions[get_column_letter(c)].width = w

# ===== Sheet 4: ΔEVE 汇总结果 =====
ws4 = wb.create_sheet("ΔEVE 汇总结果")
ws4.merge_cells("A1:F1")
ws4["A1"] = "ΔEVE 汇总结果 (按情景)"
ws4["A1"].font = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
ws4["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws4.row_dimensions[1].height = 26

headers4 = [
    "情景",
    "资产 PV (亿元)",
    "负债 PV (亿元)",
    "净资产 PV (亿元)",
    "ΔEVE (亿元)",
    "|ΔEVE| / 一级资本 (%)",  # 用户要求的: 监管指标计量值
]
for c, h in enumerate(headers4, 1):
    cell = ws4.cell(3, c, h)
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = border
ws4.row_dimensions[3].height = 30

# 计算结果
scenario_names = {
    'baseline': '基准情景',
    'up_250': '平行上移 250bp',
    'down_250': '平行下移 250bp',
    'steeper': '变陡峭',
    'flatter': '变平坦',
}

# 监管阈值 (银保监《商业银行银行账户利率风险计量》)
REGULATORY_THRESHOLD = 15.0  # %

row_idx = 4
baseline_net = sum(a['pv_scenarios']['baseline'] for a in accounts if is_asset(a['sid'])) - \
              sum(a['pv_scenarios']['baseline'] for a in accounts if is_liab(a['sid']))

for s in scenarios:
    asset_pv = sum(a['pv_scenarios'][s] for a in accounts if is_asset(a['sid']))
    liab_pv = sum(a['pv_scenarios'][s] for a in accounts if is_liab(a['sid']))
    net_pv = asset_pv - liab_pv
    delta_eve = net_pv - baseline_net
    # |ΔEVE| / 一级资本 (绝对值, 用户要求的)
    ratio = abs(delta_eve) / tier1_capital * 100

    ws4.cell(row_idx, 1, scenario_names[s])
    ws4.cell(row_idx, 2, round(asset_pv/1e8, 2))
    ws4.cell(row_idx, 3, round(liab_pv/1e8, 2))
    ws4.cell(row_idx, 4, round(net_pv/1e8, 2))
    ws4.cell(row_idx, 5, round(delta_eve/1e8, 2))
    ws4.cell(row_idx, 6, round(ratio, 4))

    for c in range(1, 7):
        cell = ws4.cell(row_idx, c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10, bold=(c == 1 or c == 6))
        if c == 1:
            cell.alignment = Alignment(horizontal="left", vertical="center")
            if s == "baseline":
                cell.fill = PatternFill("solid", fgColor="FFF9C4")
        else:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            if c <= 4:
                cell.number_format = "#,##0.00"
            else:
                cell.number_format = "0.0000"
            # |ΔEVE|/一级资本 着色
            if c == 6:
                if ratio > REGULATORY_THRESHOLD:
                    cell.font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
                    cell.fill = PatternFill("solid", fgColor="FFCDD2")
                elif ratio > 12:
                    cell.fill = PatternFill("solid", fgColor="FFE0B2")
                elif ratio > 10:
                    cell.fill = PatternFill("solid", fgColor="FFF9C4")
                else:
                    cell.fill = PatternFill("solid", fgColor="C8E6C9")
    row_idx += 1

# 监管阈值行
threshold_row = row_idx + 1
ws4.merge_cells(f"A{threshold_row}:F{threshold_row}")
ws4.cell(threshold_row, 1, "⚠ 监管阈值: |ΔEVE| / 一级资本 ≤ 15% (银保监《商业银行银行账户利率风险计量》) | 计算口径: 4 冲击情景中取最大值")
ws4.cell(threshold_row, 1).font = Font(name="微软雅黑", size=10, bold=True, color="C7000B")
ws4.cell(threshold_row, 1).fill = PatternFill("solid", fgColor="FFFDE7")
ws4.cell(threshold_row, 1).alignment = Alignment(horizontal="center", vertical="center")

# 最坏情景行
worst_row = row_idx + 3
ws4.merge_cells(f"A{worst_row}:F{worst_row}")
ws4.cell(worst_row, 1, "最坏情景监管指标 (4 冲击中最大值)")
ws4.cell(worst_row, 1).font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
ws4.cell(worst_row, 1).fill = PatternFill("solid", fgColor="C7000B")
ws4.cell(worst_row, 1).alignment = Alignment(horizontal="center", vertical="center")

# 计算 4 冲击 (不含 baseline) 中最大值
max_reg = 0
max_scenario = ""
for s in ['up_250', 'down_250', 'steeper', 'flatter']:
    asset_pv = sum(a['pv_scenarios'][s] for a in accounts if is_asset(a['sid']))
    liab_pv = sum(a['pv_scenarios'][s] for a in accounts if is_liab(a['sid']))
    net_pv = asset_pv - liab_pv
    delta_eve = net_pv - baseline_net
    ratio = abs(delta_eve) / tier1_capital * 100
    if ratio > max_reg:
        max_reg = ratio
        max_scenario = scenario_names[s]

ws4.cell(worst_row + 1, 1, max_scenario)
ws4.cell(worst_row + 1, 6, round(max_reg, 4))
for c in range(1, 7):
    cell = ws4.cell(worst_row + 1, c)
    cell.border = border
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="C7000B")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    if c == 6:
        cell.number_format = "0.0000"
        if max_reg > REGULATORY_THRESHOLD:
            cell.fill = PatternFill("solid", fgColor="FFCDD2")
        else:
            cell.fill = PatternFill("solid", fgColor="C8E6C9")

# 列宽
for c, w in enumerate([20, 18, 18, 18, 16, 26], 1):
    ws4.column_dimensions[get_column_letter(c)].width = w

# ===== Sheet 5: 计算逻辑说明 =====
ws5 = wb.create_sheet("计算逻辑说明")
ws5.merge_cells("A1:B1")
ws5["A1"] = "ΔEVE 计算逻辑说明 (基于 prcp_basic_20251231_v4.xlsx 折现方法)"
ws5["A1"].font = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
ws5["A1"].fill = PatternFill("solid", fgColor="C7000B")
ws5["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws5.row_dimensions[1].height = 26

explanations = [
    ("基础数据", "来自 prcp_basic_20251231_v4.xlsx 基础数据 sheet 的 38 账户现金流 (C75-C138)"),
    ("折现方法", "DF_t = 1/(1+r_t)^t, 年复利, t 单位: 年"),
    ("利率冲击", "银保监 4 情景: 平行上移/下移 250bp, 变陡峭/变平坦"),
    ("ΔEVE 定义", "经济价值变化 = 冲击后资产 PV - 冲击后负债 PV - (基准资产 PV - 基准负债 PV)"),
    ("ΔEVE 含义", "反映利率变动时银行净资产的潜在变化"),
    ("监管要求", "|ΔEVE| / 一级资本 ≤ 15% (银保监商业银行银行账户利率风险计量)"),
    ("一级资本", "假设 7,682.17 亿元 (所有者权益 7,862.17 × 0.85)"),
    ("计算工具", "docs/scoring_engine.py + docs/discount_tool.py 衍生"),
]
for r_off, (a, b) in enumerate(explanations):
    ws5.cell(3 + r_off, 1, a)
    ws5.cell(3 + r_off, 2, b)
    for c in [1, 2]:
        cell = ws5.cell(3 + r_off, c)
        cell.border = border
        cell.font = Font(name="微软雅黑", size=10, bold=(c == 1))
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off % 2 == 0:
        for c in [1, 2]:
            ws5.cell(3 + r_off, c).fill = PatternFill("solid", fgColor="F5F5F5")

widths5 = [16, 80]
for c, w in enumerate(widths5, 1):
    ws5.column_dimensions[get_column_letter(c)].width = w

# ===================== 5. 保存 =====================
wb.save(OUTPUT_PATH)
print(f"\n已保存: {OUTPUT_PATH}")
print(f"Sheets: {wb.sheetnames}")