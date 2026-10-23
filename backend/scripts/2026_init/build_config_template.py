"""build_config_template.py - 生成 PRCP 2026 配置 Excel 模版
6 个 Sheet:
  1. 指标方案 (prcp_kpi_scheme)
  2. 指标定义 (prcp_kpi_definition)
  3. 评分段位 (prcp_kpi_score_segment)
  4. 模型管理 (prcp_model + version + param)
  5. 测算方案 (prcp_sim_scheme + node)
  6. 铺底数据 (prcp_metric_coefficient)
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule
from pathlib import Path

OUTPUT = Path(r"C:/银行经营/PRCP/backend/scripts/2026_init/PRCP_2026_配置模版.xlsx")

# 通用样式
HEADER_FONT = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="C7000B")
NORMAL_FONT = Font(name="微软雅黑", size=10)
TITLE_FONT = Font(name="微软雅黑", size=14, bold=True, color="C7000B")
TITLE_FILL = PatternFill("solid", fgColor="FFF3E0")

THIN_BORDER = Border(
    left=Side(style="thin", color="DDDDDD"),
    right=Side(style="thin", color="DDDDDD"),
    top=Side(style="thin", color="DDDDDD"),
    bottom=Side(style="thin", color="DDDDDD"),
)


def style_header(ws, row, ncols):
    """设置表头样式"""
    for col in range(1, ncols + 1):
        cell = ws.cell(row, col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER


def style_data_row(ws, row, ncols, font=None):
    """设置数据行样式"""
    for col in range(1, ncols + 1):
        cell = ws.cell(row, col)
        if font:
            cell.font = font
        else:
            cell.font = NORMAL_FONT
        cell.alignment = Alignment(horizontal="left" if col == 2 else "center",
                                  vertical="center", wrap_text=True)
        cell.border = THIN_BORDER


def auto_width(ws, headers, sample_data):
    """根据列名和数据自动调整列宽"""
    for col_idx, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_idx)
        max_len = max(
            len(str(header)),
            *[len(str(row[col_idx - 1] or "")) for row in sample_data[:5]]
        )
        ws.column_dimensions[col_letter].width = min(max_len + 4, 40)


def add_title(ws, title, ncols):
    """添加标题行"""
    ws.merge_cells(f"A1:{get_column_letter(ncols)}1")
    cell = ws.cell(1, 1)
    cell.value = title
    cell.font = TITLE_FONT
    cell.fill = TITLE_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32


def build_sheet_kpi_scheme(wb):
    """Sheet 1: 指标方案"""
    ws = wb.create_sheet("01_指标方案")

    data = [
        # scheme_code, scheme_name, description, kpi_count, status
        ("SCH_REG_2026", "2026 监管指标方案", "5 大监管指标 + v12b 0-500 分评分", 5, "ACTIVE"),
        ("SCH_BUSINESS", "2026 业务指标方案", "ROA/ROE/EPS/客户数等业务指标", 8, "ACTIVE"),
    ]
    cols = ["scheme_code", "scheme_name", "description", "kpi_count", "status"]

    add_title(ws, "指标方案配置 (prcp_kpi_scheme)", len(cols))
    for i, c in enumerate(cols, 1):
        ws.cell(3, i, c)
    style_header(ws, 3, len(cols))
    for r, row in enumerate(data, 4):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
        style_data_row(ws, r, len(cols))
    auto_width(ws, cols, data)

    # 说明
    note_row = len(data) + 6
    ws.merge_cells(f"A{note_row}:E{note_row}")
    ws.cell(note_row, 1,
            "说明: scheme_code 是唯一编码，关联 prcp_kpi_definition/kpi_score_rule。\n"
            "kpi_count 由 prcp_kpi_definition 自动计算，无需手动填。")
    ws.cell(note_row, 1).font = Font(name="微软雅黑", size=9, italic=True, color="888888")
    ws.cell(note_row, 1).alignment = Alignment(wrap_text=True, vertical="top")


def build_sheet_kpi_definition(wb):
    """Sheet 2: 指标定义"""
    ws = wb.create_sheet("02_指标定义")

    cols = ["scheme_code", "kpi_code", "kpi_name", "indicator_type",
            "calc_unit", "threshold_min", "threshold_max", "formula_desc", "status"]

    data = [
        # 5 监管指标
        ("SCH_REG_2026", "REG_LCR",  "流动性覆盖率",     "FORMULA", "%", 0,   500, "优质流动性资产 / 净现金流出量 (30 天)",  "ACTIVE"),
        ("SCH_REG_2026", "REG_NSFR", "净稳定资金比例",   "FORMULA", "%", 0,   500, "可用稳定资金 / 所需稳定资金 (1 年)",     "ACTIVE"),
        ("SCH_REG_2026", "REG_EVE",  "银行账户利率风险", "FORMULA", "%", 0,   15,  "ΔEVE / 一级资本",                       "ACTIVE"),
        ("SCH_REG_2026", "REG_CET1", "核心一级资本充足率", "FORMULA", "%", 0,   100, "核心一级资本 / 风险加权资产",            "ACTIVE"),
        ("SCH_REG_2026", "REG_ROE",  "净资产收益率",     "FORMULA", "%", 0,   100, "净利润 / 平均净资产",                   "ACTIVE"),
        # 业务指标示例
        ("SCH_BUSINESS", "BIZ_ROA",   "总资产收益率",   "FORMULA", "%", 0, 5,  "净利润 / 平均总资产",        "ACTIVE"),
        ("SCH_BUSINESS", "BIZ_NIM",   "净息差",         "FORMULA", "%", 0, 10, "利息净收入 / 平均生息资产",  "ACTIVE"),
        ("SCH_BUSINESS", "BIZ_CIR",   "成本收入比",     "FORMULA", "%", 0, 100, "业务费用 / 营业收入",       "ACTIVE"),
    ]

    add_title(ws, "指标定义配置 (prcp_kpi_definition)", len(cols))
    for i, c in enumerate(cols, 1):
        ws.cell(3, i, c)
    style_header(ws, 3, len(cols))
    for r, row in enumerate(data, 4):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
        style_data_row(ws, r, len(cols))
    auto_width(ws, cols, data)

    # UNIQUE 约束说明
    note_row = len(data) + 6
    ws.merge_cells(f"A{note_row}:I{note_row}")
    ws.cell(note_row, 1,
            "UNIQUE 约束: (scheme_id, kpi_code)。indicator_type: FORMULA=公式/FUNCTION=函数。"
            "threshold_min/max 用于指标边界可视化。")
    ws.cell(note_row, 1).font = Font(name="微软雅黑", size=9, italic=True, color="888888")
    ws.cell(note_row, 1).alignment = Alignment(wrap_text=True, vertical="top")


def build_sheet_score_segment(wb):
    """Sheet 3: 评分段位"""
    ws = wb.create_sheet("03_评分段位")

    cols = ["scheme_code", "kpi_code", "rule_name", "calc_method", "total_score",
            "higher_is_better", "seg_order", "min_value", "max_value", "score", "segment_desc"]

    # LCR 23 段示例 (其他指标省略，参考格式)
    lcr_segments = [
        (1, 0.0,   120.0, 0,   "🔴 不达标 (≤红线 120%)"),
        (2, 120.0, 122.0, 15,  "🟠 危险"),
        (3, 122.0, 124.0, 45,  "🟠 危险"),
        (4, 124.0, 126.0, 75,  "🟠 危险"),
        (5, 126.0, 128.0, 105, "🟠 危险"),
        (6, 128.0, 130.0, 135, "🟠 危险"),
        (7, 130.0, 132.0, 165, "🟡 预警"),
        (8, 132.0, 134.0, 195, "🟡 预警"),
        (9, 134.0, 136.0, 225, "🟡 预警"),
        (10, 136.0, 138.0, 255, "🟡 预警"),
        (11, 138.0, 140.0, 250, "🟡 预警"),
        (12, 140.0, 142.0, 320, "🟢 安全"),
        (13, 142.0, 144.0, 360, "🟢 安全"),
        (14, 144.0, 146.0, 400, "🟢 安全"),
        (15, 146.0, 148.0, 440, "🟢 安全"),
        (16, 148.0, 150.0, 480, "🟢 安全 (中信 148% 命中)"),
        (17, 150.0, 150.0, 500, "⭐ 适度最优 150%"),
        (18, 150.0, 160.0, 480, "🟢 过优 资金闲置"),
        (19, 160.0, 170.0, 440, "🟢 过优"),
        (20, 170.0, 180.0, 400, "🟢 过优"),
        (21, 180.0, 200.0, 360, "🟡 过优 减分"),
        (22, 200.0, 250.0, 320, "🟡 过优 严重"),
        (23, 250.0, 9999.0, 280, "🔴 极度过剩"),
    ]
    data = []
    for seg in lcr_segments:
        data.append(("SCH_REG_2026", "REG_LCR", "REG_LCR v12b 0-500 分", "PIECEWISE", 500, 1, *seg))

    add_title(ws, "评分段位配置 (prcp_kpi_score_segment) - LCR 完整 23 段示例", len(cols))
    for i, c in enumerate(cols, 1):
        ws.cell(3, i, c)
    style_header(ws, 3, len(cols))
    for r, row in enumerate(data, 4):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
        style_data_row(ws, r, len(cols))
    auto_width(ws, cols, data)

    # 说明
    note_row = len(data) + 6
    ws.merge_cells(f"A{note_row}:K{note_row}")
    ws.cell(note_row, 1,
            "段位匹配规则: 闭区间 [min_value, max_value)。"
            "higher_is_better: 1=越高越好 (LCR/NSFR/CET1/ROE), 0=越低越好 (EVE)。"
            "⭐ 段表示适度最优，0 分段表示监管红线 (LCR<120%, NSFR<100%, CET1<8.7%, ROE<6%, EVE>15%)。\n"
            "其他指标 (NSFR/EVE/CET1/ROE) 参考 PRCP/backend/scripts/2026_init/01_seed_kpi_scheme_2026.sql 完整段位定义。")
    ws.cell(note_row, 1).font = Font(name="微软雅黑", size=9, italic=True, color="888888")
    ws.cell(note_row, 1).alignment = Alignment(wrap_text=True, vertical="top")


def build_sheet_model(wb):
    """Sheet 4: 模型管理 (主表 + 版本 + 参数)"""
    ws = wb.create_sheet("04_模型管理")

    cols = ["model_code", "model_name", "model_type", "biz_domain",
            "description", "version_code", "param_code", "param_name",
            "param_category", "param_value", "param_value_str", "unit", "sort_order"]

    # 3 模型 × 关键参数示例
    data = [
        # DNN_REG
        ("DNN_REG", "DNN 神经网络回归模型", "DNN_NEURAL_NETWORK", "监管资本",
         "基于深度神经网络 (DNN/MLP) 的非线性回归", "V1_BASELINE",
         "NN_HIDDEN_DIMS", "隐藏层维度序列", "NEURAL_NETWORK", 0, "[256,128,128,64]", None, 1),
        ("DNN_REG", "DNN 神经网络回归模型", "DNN_NEURAL_NETWORK", "监管资本",
         "基于深度神经网络 (DNN/MLP) 的非线性回归", "V1_BASELINE",
         "NN_LATENT_DIM",  "编码维度",            "NEURAL_NETWORK", 32,  None, "维", 2),
        ("DNN_REG", "DNN 神经网络回归模型", "DNN_NEURAL_NETWORK", "监管资本",
         "基于深度神经网络 (DNN/MLP) 的非线性回归", "V1_BASELINE",
         "OPTIM_LEARNING_RATE","学习率",         "OPTIMIZER",    0.001, None, None, 6),
        # ACO_OPT
        ("ACO_OPT", "蚁群算法组合优化模型", "ANT_COLONY", "资产负债",
         "基于蚁群 (ACO) 的组合优化", "V1_BASELINE",
         "ACO_ANT_COUNT", "蚂蚁数量",          "OPTIMIZER", 50,  None, "只", 1),
        ("ACO_OPT", "蚁群算法组合优化模型", "ANT_COLONY", "资产负债",
         "基于蚁群 (ACO) 的组合优化", "V1_BASELINE",
         "ACO_MAX_ITER",  "最大迭代次数",      "OPTIMIZER", 100, None, "轮", 2),
        ("ACO_OPT", "蚁群算法组合优化模型", "ANT_COLONY", "资产负债",
         "基于蚁群 (ACO) 的组合优化", "V1_BASELINE",
         "ACO_ALPHA",      "信息素权重 α",     "OPTIMIZER", 1.0, None, None, 3),
        # NLS_REG
        ("NLS_REG", "非线性方程求解模型", "NONLINEAR_SOLVER", "定价估值",
         "基于 scipy.optimize 非线性求解器", "V1_BASELINE",
         "NLS_SOLVER",   "求解器",          "OPTIMIZER", 0, "TRUST_REGION", None, 1),
        ("NLS_REG", "非线性方程求解模型", "NONLINEAR_SOLVER", "定价估值",
         "基于 scipy.optimize 非线性求解器", "V1_BASELINE",
         "NLS_TOL_FUN",  "函数容差",        "OPTIMIZER", 0.000001, None, None, 3),
        ("NLS_REG", "非线性方程求解模型", "NONLINEAR_SOLVER", "定价估值",
         "基于 scipy.optimize 非线性求解器", "V1_BASELINE",
         "DATA_DATE_CURRENT", "当前数据日期", "DATA_DATE", 0, "2025-12-31", None, 12),
    ]

    add_title(ws, "模型管理配置 (prcp_model + version + param) - 3 模型关键参数", len(cols))
    for i, c in enumerate(cols, 1):
        ws.cell(3, i, c)
    style_header(ws, 3, len(cols))
    for r, row in enumerate(data, 4):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
        style_data_row(ws, r, len(cols))
    auto_width(ws, cols, data)

    # 说明
    note_row = len(data) + 6
    ws.merge_cells(f"A{note_row}:M{note_row}")
    ws.cell(note_row, 1,
            "3 模型: DNN_REG (深度神经网络) / ACO_OPT (蚁群优化) / NLS_REG (非线性求解)。\n"
            "模型主表 (model_code) + 版本 (version_code) + 参数 (param_code) 三级关联。\n"
            "param_value: 数值参数 | param_value_str: 字符串参数 (字符串以非空 / str 标识)。")
    ws.cell(note_row, 1).font = Font(name="微软雅黑", size=9, italic=True, color="888888")
    ws.cell(note_row, 1).alignment = Alignment(wrap_text=True, vertical="top")


def build_sheet_sim_scheme(wb):
    """Sheet 5: 测算方案"""
    ws = wb.create_sheet("05_测算方案")

    # 5.1 方案主表
    cols1 = ["scheme_code", "scheme_name", "coa_scheme_code", "description",
              "config_node_count", "model_code", "model_version_code", "status"]

    data1 = [
        ("SCS_2026", "2026 测算方案 (NLS_REG)", "ZX_COA",
         "基于 NLS_REG 模型，24 月滚动测算 + ΔEVE 监控", 15, "NLS_REG", "V1_BASELINE", "IN_PROGRESS"),
    ]

    add_title(ws, "测算方案配置 (prcp_sim_scheme + node)", len(cols1))
    for i, c in enumerate(cols1, 1):
        ws.cell(3, i, c)
    style_header(ws, 3, len(cols1))
    for r, row in enumerate(data1, 4):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
        style_data_row(ws, r, len(cols1))
    auto_width(ws, cols1, data1)

    # 5.2 节点配置
    cols2 = ["scheme_code", "node_code", "node_name", "alloc_pct", "duration_months",
            "base_balance (元)", "scenario_rate_pct", "scenario_growth_pct"]

    nodes = [
        # 资产 12 节点
        ("SCS_2026", "S010101010000", "1.1.对公一般贷款", 0.207, 36, 2450000000000, 4.50, 0.020),
        ("SCS_2026", "S010101020000", "1.2.个人贷款",     0.154, 60, 1820000000000, 5.20, 0.025),
        ("SCS_2026", "S010101030000", "1.3.信用卡贷款",   0.039, 12, 460000000000,  12.00, 0.015),
        ("SCS_2026", "S010101040000", "1.4.票据贴现",     0.027, 3,  320000000000,   2.50, -0.005),
        ("SCS_2026", "S010101050000", "1.5.非银贷款",     0.042, 24, 500000000000,   4.00, 0.020),
        ("SCS_2026", "S010102010100", "2.1.1金市AC",      0.050, 36, 590000000000,   3.20, 0.018),
        ("SCS_2026", "S010102010200", "2.1.2司库AC",      0.084, 60, 980000000000,   3.20, 0.020),
        ("SCS_2026", "S010102020000", "2.2.结构化融资",   0.035, 24, 410000000000,   4.50, 0.015),
        ("SCS_2026", "S010102030000", "2.3.同业资产",     0.052, 6,  610000000000,   2.20, 0.010),
        ("SCS_2026", "S010102040000", "2.4.存款准备金",   0.025, 1,  290000000000,   1.80, 0.005),
        ("SCS_2026", "S010201000000", "1.外币贷款",       0.034, 24, 400000000000,   5.00, 0.020),
        ("SCS_2026", "S010202010000", "2.1.外币债券",     0.017, 60, 180000000000,   3.50, 0.015),
        # 负债 3 节点
        ("SCS_2026", "S020101010100", "1.1.1对公活期存款", 0.218, 1, 2460000000000,  1.00, 0.030),
        ("SCS_2026", "S020101010200", "1.1.2对公定期存款", 0.184, 24, 2080000000000, 3.50, 0.025),
        ("SCS_2026", "S020101020100", "1.2.1零售活期存款", 0.101, 1, 1140000000000,  0.50, 0.020),
    ]

    start_row = 8
    ws.merge_cells(f"A{start_row}:H{start_row}")
    ws.cell(start_row, 1, "测算节点配置 (prcp_sim_scheme_node) - 15 末级节点")
    ws.cell(start_row, 1).font = Font(name="微软雅黑", size=12, bold=True, color="C7000B")
    ws.cell(start_row, 1).fill = PatternFill("solid", fgColor="FFF3E0")
    ws.cell(start_row, 1).alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[start_row].height = 24

    for i, c in enumerate(cols2, 1):
        ws.cell(start_row + 1, i, c)
    style_header(ws, start_row + 1, len(cols2))
    for r, row in enumerate(nodes, start_row + 2):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
        style_data_row(ws, r, len(cols2))
    auto_width(ws, cols2, nodes)

    # 说明
    note_row = start_row + 2 + len(nodes) + 2
    ws.merge_cells(f"A{note_row}:H{note_row}")
    ws.cell(note_row, 1,
            "alloc_pct: 资金分配占比 (0-1)；duration_months: 期限 (月)；"
            "base_balance: 基准余额 (元)；scenario_rate_pct: 情景利率 (%)；scenario_growth_pct: 月增长率 (%)。\n"
            "节点配置 15 个，覆盖 12 资产 + 3 负债的核心末级账户。")
    ws.cell(note_row, 1).font = Font(name="微软雅黑", size=9, italic=True, color="888888")
    ws.cell(note_row, 1).alignment = Alignment(wrap_text=True, vertical="top")


def build_sheet_metric_coefficient(wb):
    """Sheet 6: 铺底数据"""
    ws = wb.create_sheet("06_铺底数据")

    cols = ["id", "scheme_code", "node_code", "metric_code", "data_date",
            "current_value", "y1_value", "y2_value", "y3_value", "y4_value", "y5_value",
            "unit", "description"]

    # 5 指标 × 16 月 (M0 + M1-M15) × 1 个示例节点 = 80 条
    metrics_data = []
    nodes_demo = ["S010101010000", "S020101010100"]  # 1 资产 + 1 负债示例
    months = [
        ('2025-12-31', 147.29, 145.00, 140.00, 138.00, 135.00, 133.00),
        ('2026-01-31', 147.50, 144.80, 139.80, 137.80, 134.80, 132.80),
        ('2026-02-28', 147.70, 144.60, 139.60, 137.60, 134.60, 132.60),
        ('2026-03-31', 147.90, 144.40, 139.40, 137.40, 134.40, 132.40),
        ('2026-04-30', 148.10, 144.20, 139.20, 137.20, 134.20, 132.20),
        ('2026-05-31', 148.30, 144.00, 139.00, 137.00, 134.00, 132.00),
        ('2026-06-30', 148.50, 143.80, 138.80, 136.80, 133.80, 131.80),
        ('2026-07-31', 148.70, 143.60, 138.60, 136.60, 133.60, 131.60),
        ('2026-08-31', 148.90, 143.40, 138.40, 136.40, 133.40, 131.40),
        ('2026-09-30', 149.10, 143.20, 138.20, 136.20, 133.20, 131.20),
        ('2026-10-31', 149.30, 143.00, 138.00, 136.00, 133.00, 131.00),
        ('2026-11-30', 149.50, 142.80, 137.80, 135.80, 132.80, 130.80),
        ('2026-12-31', 149.70, 142.60, 137.60, 135.60, 132.60, 130.60),
        ('2027-01-31', 149.90, 142.40, 137.40, 135.40, 132.40, 130.40),
        ('2027-02-28', 150.10, 142.20, 137.20, 135.20, 132.20, 130.20),
        ('2027-03-31', 150.30, 142.00, 137.00, 135.00, 132.00, 130.00),
    ]

    kpi_codes = ['REG_LCR', 'REG_NSFR', 'REG_EVE', 'REG_CET1', 'REG_ROE']

    for node_code in nodes_demo:
        for kpi_code in kpi_codes:
            for m_data in months:
                date_str, c, y1, y2, y3, y4, y5 = m_data
                # LCR/NSFR/CET1/ROE 各自有不同数值模式, 这里只用 LCR 示例
                if kpi_code == 'REG_LCR':
                    vals = (c, y1, y2, y3, y4, y5)
                elif kpi_code == 'REG_NSFR':
                    vals = (c - 40, y1 - 40, y2 - 40, y3 - 40, y4 - 40, y5 - 40)
                elif kpi_code == 'REG_EVE':
                    vals = (10, c - 50, y1 - 50, y2 - 50, y3 - 50, y4 - 50)
                elif kpi_code == 'REG_CET1':
                    vals = (c / 15, y1 / 15, y2 / 15, y3 / 15, y4 / 15, y5 / 15)
                else:  # ROE
                    vals = (c / 15, y1 / 15, y2 / 15, y3 / 15, y4 / 15, y5 / 15)

                metrics_data.append([
                    f"ZX_COA-{node_code}-{kpi_code}-{date_str}",
                    "ZX_COA", node_code, kpi_code, date_str,
                    round(vals[0], 2),
                    round(vals[1], 2),
                    round(vals[2], 2),
                    round(vals[3], 2),
                    round(vals[4], 2),
                    round(vals[5], 2),
                    "PERCENT",
                    f"铺底 - {kpi_code} @ {date_str}",
                ])

    add_title(ws, "铺底指标系数配置 (prcp_metric_coefficient) - 5 指标 × 16 月 × 2 示例节点 (80 条)", len(cols))
    for i, c in enumerate(cols, 1):
        ws.cell(3, i, c)
    style_header(ws, 3, len(cols))
    for r, row in enumerate(metrics_data, 4):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
        style_data_row(ws, r, len(cols))
    auto_width(ws, cols, metrics_data)

    # 说明
    note_row = 4 + len(metrics_data) + 2
    ws.merge_cells(f"A{note_row}:M{note_row}")
    ws.cell(note_row, 1,
            "id 格式: ZX_COA-{node_code}-{metric_code}-{data_date} (PRIMARY KEY)\n"
            "UNIQUE 约束: (scheme_code, node_code, metric_code, data_date, is_deleted)\n"
            "current_value: 基期值; y1_value ~ y5_value: 未来 1-5 年预测值。\n"
            "完整铺底应为 5 指标 × 15 节点 × 16 月 = 1200 条 (本示例仅展示 80 条)。")
    ws.cell(note_row, 1).font = Font(name="微软雅黑", size=9, italic=True, color="888888")
    ws.cell(note_row, 1).alignment = Alignment(wrap_text=True, vertical="top")

    # 冻结表头
    ws.freeze_panes = "A4"


def build_sheet_readme(wb):
    """Sheet 0: 使用说明"""
    ws = wb.create_sheet("00_使用说明", 0)

    ws.merge_cells("A1:H1")
    ws.cell(1, 1, "PRCP 2026 配置模版使用文档")
    ws.cell(1, 1).font = Font(name="微软雅黑", size=16, bold=True, color="C7000B")
    ws.cell(1, 1).alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    rows = [
        ("📋 概述", "本模版用于 PRCP 2026 平台的指标管理 / 模型管理 / 测算方案 / 铺底数据配置。\n"
                    "对应 backend/scripts/2026_init/ 下的 00-03 SQL 脚本。"),
        ("📂 Sheet 结构", "01 指标方案 | 02 指标定义 | 03 评分段位 | 04 模型管理 | 05 测算方案 | 06 铺底数据"),
        ("🚀 使用步骤", "1. 在 Excel 中编辑各 Sheet 配置\n"
                    "2. 导出为 CSV 或 INSERT INTO 语句\n"
                    "3. 执行: cd backend/scripts/2026_init && python seed_all.py"),
        ("🔗 关联关系", "scheme_code (01) → kpi_definition (02) → score_rule/segment (03)\n"
                    "scheme_code (05) → coa_scheme → coa_node → sim_scheme_node\n"
                    "model_code (04) → model_version → model_param\n"
                    "metric_coefficient (06) 关联 scheme_code + node_code + metric_code"),
        ("📊 数据日期", "基期: 2025-12-31 (中信银行 2025 年度披露日)\n"
                    "铺底月数: 16 月 (M0 + M1~M15)\n"
                    "测算周期: 2025-12 至 2027-11"),
        ("🛠️ SQL 脚本", "00_setup_schema.sql          建表\n"
                    "01_seed_kpi_scheme_2026.sql  SCH_REG_2026 指标方案 + 5 KPI + v12b 评分段位\n"
                    "02_seed_models.sql           DNN_REG/ACO_OPT/NLS_REG 3 模型 + 参数\n"
                    "03_seed_sim_scheme.sql       ZX_COA + SCS_2026 + 铺底数据"),
        ("⚠️ 注意事项", "1. SCH_REG_2026 scheme_id=1 (硬编码, 修改需同步 SQL)\n"
                    "2. UNIQUE 约束: (scheme_id, kpi_code), (model_code, version_code),\n"
                    "   (version_id, param_code), (scheme_code, node_code),\n"
                    "   (scheme_code, metric_code, data_date, is_deleted)\n"
                    "3. 软删除字段 is_deleted 默认 0, 删除数据时改为 1\n"
                    "4. 评分段位 [min_value, max_value) 左闭右开\n"
                    "5. higher_is_better: 0=越低越好 (EVE), 1=越高越好 (LCR/NSFR/CET1/ROE)"),
    ]

    row_idx = 3
    for title, content in rows:
        ws.merge_cells(f"A{row_idx}:H{row_idx}")
        ws.cell(row_idx, 1, title)
        ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=12, bold=True, color="C7000B")
        ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
        ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[row_idx].height = 22

        row_idx += 1
        ws.merge_cells(f"A{row_idx}:H{row_idx}")
        ws.cell(row_idx, 1, content)
        ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=10)
        ws.cell(row_idx, 1).alignment = Alignment(horizontal="left", vertical="top",
                                              wrap_text=True, indent=2)
        # 根据内容行数设置行高
        line_count = content.count('\n') + 1
        ws.row_dimensions[row_idx].height = 18 * line_count + 6
        row_idx += 2

    # 列宽
    for col_letter in 'ABCDEFGH':
        ws.column_dimensions[col_letter].width = 18


def main():
    wb = Workbook()
    # 删除默认 sheet
    wb.remove(wb.active)

    build_sheet_readme(wb)
    build_sheet_kpi_scheme(wb)
    build_sheet_kpi_definition(wb)
    build_sheet_score_segment(wb)
    build_sheet_model(wb)
    build_sheet_sim_scheme(wb)
    build_sheet_metric_coefficient(wb)

    # 设置每个 sheet 的默认列宽
    for sheet in wb.worksheets:
        if sheet.title != "00_使用说明":
            sheet.sheet_view.showGridLines = False

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT)
    print(f"✅ 配置模版已保存: {OUTPUT}")
    print(f"   - 6 Sheets: {wb.sheetnames}")
    print(f"   - 文件大小: {OUTPUT.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()