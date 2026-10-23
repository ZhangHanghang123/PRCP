"""给 prcp_basic_20251231_v4.xlsx 增加 "折现的计量说明" sheet"""

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_PATH = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v4.xlsx"

# ===================== 1. 加载 =====================
wb = load_workbook(EXCEL_PATH)

# 删除已有的 "折现的计量说明" sheet (如果存在)
if "折现的计量说明" in wb.sheetnames:
    del wb["折现的计量说明"]

ws = wb.create_sheet("折现的计量说明")

# ===================== 2. 样式定义 =====================
border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)

# ===================== 3. 写入内容 =====================
row_idx = 1

# 标题
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "折现的计量说明 (Discount Methodology)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[row_idx].height = 30
row_idx += 1

# 副标题
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "基于 prcp_basic_20251231_v4.xlsx 的折现计量过程, 包含全部公式解释")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=10, italic=True, color="555555")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
row_idx += 2

# ===================== 一、折现基本概念 =====================
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "一、折现基本概念")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

concept_text = [
    ("概念", "说明"),
    ("现值 (PV)", "把未来的现金流按合适的利率折现到现在的价值"),
    ("折现因子 (DF)", "未来 1 元钱在今天的价值, 范围 (0, 1]"),
    ("折现率 (r)", "把未来现金流还原到现在所使用的利率, 通常采用无风险利率 (国债收益率)"),
    ("期限 (t)", "从现在到现金流发生的时间间隔, 单位: 年"),
    ("复利方式", "年复利: DF = 1/(1+r)^t | 连续复利: DF = e^(-rt)"),
]
for r_off, row_data in enumerate(concept_text):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# ===================== 二、核心公式 =====================
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "二、核心公式")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

# 公式 2.1 折现因子
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "2.1 折现因子 (Discount Factor)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "公式 (年复利):  DF_t = 1 / (1 + r_t)^t")
ws.cell(row_idx, 1).font = Font(name="Consolas", size=11, bold=True, color="0070C0")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFFDE7")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
row_idx += 1

ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "公式 (连续复利):  DF_t = e^(-r_t × t)")
ws.cell(row_idx, 1).font = Font(name="Consolas", size=11, bold=True, color="0070C0")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFFDE7")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
row_idx += 1

# 变量说明
df_vars = [
    ("变量", "含义", "单位", "示例"),
    ("DF_t", "期限 t 的折现因子", "无量纲", "1Y 1.5% → 0.9852"),
    ("r_t", "期限 t 的利率 (国债收益率)", "% (年化)", "1.3372 (1Y)"),
    ("t", "期限", "年", "1.0 (1Y), 0.0833 (1M), 30.0 (30Y)"),
]
for r_off, row_data in enumerate(df_vars):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# 公式 2.2 现值
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "2.2 现值 (Present Value)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "公式:  PV = Σ CF_t × DF_t = Σ CF_t / (1 + r_t)^t")
ws.cell(row_idx, 1).font = Font(name="Consolas", size=11, bold=True, color="0070C0")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFFDE7")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
row_idx += 1

pv_vars = [
    ("变量", "含义", "单位", "示例"),
    ("PV", "总现值", "元", "R7 ≈ 12.96 万亿元"),
    ("CF_t", "期限 t 的现金流", "元", "1M: 2.45 万亿"),
    ("DF_t", "期限 t 的折现因子", "无量纲", "1Y 1.34% → 0.9868"),
]
for r_off, row_data in enumerate(pv_vars):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# 公式 2.3 期限转换
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "2.3 期限单位转换")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

tenor_formula = [
    ("单位", "换算公式", "示例", "实际值"),
    ("日 (D)", "1D = 1/365 年", "30D", "30/365 = 0.0822 年"),
    ("月 (M)", "1M = 1/12 年", "3M", "3/12 = 0.25 年"),
    ("年 (Y)", "1Y = 1 年", "5Y", "5.0 年"),
    ("年 (复合)", "mY = m 年, nM = n*30/365 年", "60M + 5Y", "5 + 60/12 = 10 年"),
]
for r_off, row_data in enumerate(tenor_formula):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# ===================== 三、曲线插值方法 =====================
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "三、曲线插值方法 (本表使用线性插值)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

# 3.1 已知曲线点 (2025-12-31)
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "3.1 已知曲线点 (2025-12-31 国债收益率, 来源中债登)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

# 数据来源说明
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "R47-R111: 国债收益率曲线表 (10 个中债登官方期限 + 54 个线性插值期限, 共 64 段位)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=10, italic=True, color="555555")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

# 10 个中债登官方数据
official_curve = [
    ("期限", "利率(%)", "来源", "说明"),
    ("3M", "1.27", "中债登", "官方数据"),
    ("6M", "1.30", "中债登", "官方数据"),
    ("9M", "1.32", "中债登", "官方数据"),
    ("1Y", "1.3372", "中债登", "官方数据"),
    ("2Y", "1.3605", "中债登", "官方数据"),
    ("3Y", "1.3830", "中债登", "官方数据"),
    ("5Y", "1.6309", "中债登", "官方数据"),
    ("7Y", "1.7359", "中债登", "官方数据"),
    ("10Y", "1.8473", "中债登", "官方数据"),
    ("30Y", "2.2674", "中债登", "官方数据"),
]
for r_off, row_data in enumerate(official_curve):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if r_off in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] and c == 3:
                # 标记中债登行为浅绿色
                cell.fill = PatternFill("solid", fgColor="E8F5E9")
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# 3.2 线性插值公式
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "3.2 线性插值公式 (Linear Interpolation)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "公式:  r(t) = r_lo + (r_hi - r_lo) × (t - t_lo) / (t_hi - t_lo)")
ws.cell(row_idx, 1).font = Font(name="Consolas", size=11, bold=True, color="0070C0")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFFDE7")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
row_idx += 1

interp_vars = [
    ("变量", "含义"),
    ("r(t)", "期限 t 的插值利率 (%)"),
    ("r_lo, r_hi", "相邻已知曲线点的利率 (%)"),
    ("t_lo, t_hi", "相邻已知曲线点的期限 (年)"),
    ("t", "目标期限 (年)"),
    ("约束", "t_lo ≤ t ≤ t_hi (在线性段内), 超出范围线性外推"),
]
for r_off, row_data in enumerate(interp_vars):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1

# 插值示例
row_idx += 1
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "插值示例: 18M (1.5 年)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=10, bold=True, color="0070C0")
row_idx += 1
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "r(1.5) = 1.3372 + (1.3605 - 1.3372) × (1.5 - 1.0) / (2.0 - 1.0) = 1.3372 + 0.0117 = 1.34885")
ws.cell(row_idx, 1).font = Font(name="Consolas", size=10, color="555555")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="F5F5F5")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
row_idx += 2

# ===================== 四、计量流程 =====================
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "四、计量流程 (单条现金流)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

flow_steps = [
    ("步骤", "操作", "公式", "示例"),
    ("1", "期限 → 年数", "t = tenor_to_years(\"3M\")", "3M → 0.25 年"),
    ("2", "插值 → 利率", "r_t = INTERP(curve, t)", "0.25 年 → 1.27%"),
    ("3", "计算折现因子", "DF_t = 1/(1+r_t)^t", "1.27% 0.25年 → 0.99685"),
    ("4", "计算现值", "PV = CF × DF_t", "573.3亿 × 0.99685 = 571.5亿"),
    ("5", "汇总 (批量)", "PV_total = Σ PV_t", "R7 = 12.96 万亿"),
]
for r_off, row_data in enumerate(flow_steps):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="Consolas", size=9, color="555555") if c == 2 else Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="center" if c in [1, 4] else "left", vertical="center", wrap_text=True)
            if r_off in [2, 3, 4] and c == 2:
                cell.fill = PatternFill("solid", fgColor="FFFDE7")
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# ===================== 五、本表的具体应用 =====================
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "五、本表 (prcp_basic_20251231_v4.xlsx) 的具体应用")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

# 5.1 工作表结构
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "5.1 工作表结构")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

sheet_struct = [
    ("行/列", "内容", "公式类型", "示例"),
    ("R3-R43", "38 个账户册数据", "基础数据", "总资产/总负债/各分项"),
    ("C11 (K列)", "现值 (38 账户)", "=Σ CF×DF (数值)", "R7 = 129,571 亿"),
    ("C12 (L列)", "现值审计公式", "=Σ C×B (公式)", "60+4 项乘法"),
    ("R47-R111", "国债收益率曲线", "64 段位数值", "3M=1.27, 10Y=1.85"),
    ("R114-R173", "60 月度折现因子", "=1/(1+B48)^(m/12)", "DF_1M=0.9989"),
    ("R175-R178", "4 年度折现因子", "=1/(1+B108)^(10/15/20/30)", "DF_10Y=0.8327"),
]
for r_off, row_data in enumerate(sheet_struct):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# 5.2 折现因子公式
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "5.2 折现因子公式 (B114-B178)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "月度 (B114-B173):  =1/(1+B$48)^(1/12) ~ =1/(1+B$107)^(60/12)")
ws.cell(row_idx, 1).font = Font(name="Consolas", size=10, color="0070C0")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFFDE7")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "年度 (B175-B178):  =1/(1+B$108)^10 ~ =1/(1+B$111)^30")
ws.cell(row_idx, 1).font = Font(name="Consolas", size=10, color="0070C0")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFFDE7")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 2

# 5.3 案例: R7 1.1对公一般贷款
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "5.3 案例: R7 (1.1.对公一般贷款) 折现计算")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
row_idx += 1

r7_case = [
    ("项", "数值/说明"),
    ("账户", "1.1.对公一般贷款"),
    ("现金流条数", "15 条 (1M-12M + 15Y/20Y/30Y)"),
    ("数据日期", "2025-12-31"),
    ("插值方法", "线性 (linear)"),
    ("复利方式", "年复利 (annual)"),
    ("1M 现金流", "2,450 亿元"),
    ("1M 折现因子", "0.9989 (1.27% 1/12 年)"),
    ("1M 现值", "2,447.5 亿元"),
    ("15Y 现金流", "30,625 亿元"),
    ("15Y 折现因子", "0.7482 (1.95% 15 年)"),
    ("15Y 现值", "22,915 亿元"),
    ("总现值", "124,065 亿元 (用 10 关键点), 129,571 亿元 (用 64 段位, 写于 K 列)"),
]
for r_off, row_data in enumerate(r7_case):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        if r_off == 13:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="0070C0")
            cell.fill = PatternFill("solid", fgColor="FFFDE7")
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# ===================== 六、注意事项 =====================
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "六、注意事项")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

notes = [
    ("序号", "注意事项"),
    ("1", "WPS 打开后 K 列 (现值) 已直接写数值, 不依赖公式计算"),
    ("2", "B114-B178 折现因子是公式, 修改 B48-B111 收益率后自动重算"),
    ("3", "WPS 打开后建议按 Ctrl+Alt+F9 强制重算所有公式"),
    ("4", "1 年 = 365 日, 1 月 = 1/12 年, 单位换算固定"),
    ("5", "超出曲线范围的期限会线性外推, 需谨慎使用"),
    ("6", "折现只考虑时间价值, 不考虑信用风险/流动性风险等其他调整"),
    ("7", "本表采用年复利, 若需连续复利或月度复利, 可调整 discount_factor 函数"),
    ("8", "K 列是数值, L 列是公式 (审计用), 修改 L 列公式不影响 K 列"),
]
for r_off, row_data in enumerate(notes):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1
row_idx += 1

# ===================== 七、参考文档 =====================
ws.merge_cells(f"A{row_idx}:D{row_idx}")
ws.cell(row_idx, 1, "七、参考文档")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center")
row_idx += 1

refs = [
    ("文档", "路径", "用途"),
    ("数据表 (本表)", "docs/v2/prcp_basic_20251231_v4.xlsx", "基础数据 + 折现结果"),
    ("折现工具脚本", "docs/discount_tool.py", "工具类 (TenorUnit/parse_tenor/折现因子/批量折现)"),
    ("测试脚本", "docs/test_discount_tool.py", "59 个测试用例"),
    ("生成脚本", "docs/build_yield_curve.py", "生成 R47-R111 收益率曲线"),
    ("生成脚本", "docs/build_pv_v6.py", "生成 B112-B178 折现因子 + K 列 PV"),
]
for r_off, row_data in enumerate(refs):
    for c, val in enumerate(row_data, 1):
        cell = ws.cell(row_idx, c, val)
        cell.border = border
        if r_off == 0:
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="C7000B")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.font = Font(name="微软雅黑", size=10)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if r_off == 0:
        ws.row_dimensions[row_idx].height = 22
    row_idx += 1

# ===================== 列宽 =====================
ws.column_dimensions['A'].width = 16
ws.column_dimensions['B'].width = 36
ws.column_dimensions['C'].width = 28
ws.column_dimensions['D'].width = 28

# 冻结首行
ws.freeze_panes = "A4"

# ===================== 保存 =====================
wb.save(EXCEL_PATH)
print(f"已保存: {EXCEL_PATH}")
print(f"新增 Sheet: 折现的计量说明 (共 {row_idx-1} 行)")
print(f"Sheets: {wb.sheetnames}")