"""给 评分标准_v12b.xlsx 重新生成 "打分算法说明" sheet

更新:
1. 只做评分, 不做评级映射
2. 权重默认都给 1
"""

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_PATH = r"C:/银行经营/PRCP/docs/v2/评分标准_v12b.xlsx"

# ===================== 1. 加载 =====================
wb = load_workbook(EXCEL_PATH)

if "打分算法说明" in wb.sheetnames:
    del wb["打分算法说明"]

ws = wb.create_sheet("打分算法说明")

# ===================== 2. 样式 =====================
border = Border(
    left=Side(style="thin", color="BDBDBD"),
    right=Side(style="thin", color="BDBDBD"),
    top=Side(style="thin", color="BDBDBD"),
    bottom=Side(style="thin", color="BDBDBD"),
)


def add_section_header(row, title):
    ws.merge_cells(f"A{row}:F{row}")
    cell = ws.cell(row, 1, title)
    cell.font = Font(name="微软雅黑", size=13, bold=True, color="C7000B")
    cell.fill = PatternFill("solid", fgColor="FFF3E0")
    cell.alignment = Alignment(horizontal="left", vertical="center")
    cell.border = border
    ws.row_dimensions[row].height = 26
    return row + 1


def add_subsection(row, title):
    ws.merge_cells(f"A{row}:F{row}")
    cell = ws.cell(row, 1, title)
    cell.font = Font(name="微软雅黑", size=11, bold=True, color="0070C0")
    cell.alignment = Alignment(horizontal="left", vertical="center")
    return row + 1


def add_table(row, headers, data):
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row, c, h)
        cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="C7000B")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
    ws.row_dimensions[row].height = 24
    for r_off, row_data in enumerate(data):
        r = row + 1 + r_off
        for c, val in enumerate(row_data, 1):
            cell = ws.cell(r, c, val)
            cell.border = border
            cell.font = Font(name="微软雅黑", size=9, color="555555")
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            if c == 1 and isinstance(val, str) and ('=' in str(val) or '{' in str(val) or 'def' in str(val)):
                cell.font = Font(name="Consolas", size=9, color="0070C0")
            if c == 2 and isinstance(val, str) and ('=' in str(val) or '{' in str(val)):
                cell.font = Font(name="Consolas", size=9, color="0070C0")
    return row + 1 + len(data)


def add_code_block(row, code_lines, color="0070C0"):
    ws.merge_cells(f"A{row}:F{row}")
    code_text = "\n".join(code_lines)
    cell = ws.cell(row, 1, code_text)
    cell.font = Font(name="Consolas", size=9, color=color)
    cell.fill = PatternFill("solid", fgColor="FFFDE7")
    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    n_lines = code_text.count("\n") + 1
    ws.row_dimensions[row].height = max(20, n_lines * 14)
    return row + 1


def add_paragraph(row, text):
    ws.merge_cells(f"A{row}:F{row}")
    cell = ws.cell(row, 1, text)
    cell.font = Font(name="微软雅黑", size=10, color="555555")
    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    n_lines = text.count("\n") + 1
    ws.row_dimensions[row].height = max(18, n_lines * 16)
    return row + 1


# ===================== 3. 写入内容 =====================
row_idx = 1

# 标题
ws.merge_cells(f"A{row_idx}:F{row_idx}")
ws.cell(row_idx, 1, "打分算法说明 (Scoring Algorithm Specification)")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="C7000B")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[row_idx].height = 30
row_idx += 1

# 副标题
ws.merge_cells(f"A{row_idx}:F{row_idx}")
ws.cell(row_idx, 1, "面向 Python 开发人员的算法规格 | 本次: LCR/NSFR/EVE/CET1/ROE 5 指标 | 只评分不评级 | 权重默认 1")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=10, italic=True, color="555555")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
row_idx += 2

# ===================== 一、算法概述 =====================
row_idx = add_section_header(row_idx, "一、算法概述")

row_idx = add_paragraph(row_idx,
    "打分引擎只做两件事:\n"
    "  1. 单指标评分: 每个指标根据段位配置 (Segment) 找到实际值所在区间, 返回该区间的分数\n"
    "  2. 多指标求和: 各指标的分数直接相加, 得到总分 (本版不评级映射)\n"
    "所有指标分段和分数都可调整. 权重默认 1, 即各指标分数等权相加 (实际汇总时仍可按权重调整)."
)
row_idx += 1

row_idx = add_subsection(row_idx, "1.1 算法流程图")
flow_text = [
    "输入: 实际指标值 (dict: {指标代码: 值, ...})",
    "  ↓",
    "[1] 单指标评分: 对每个 (code, value), 在 INDICATORS_CONFIG[code]['segments'] 中查找 value 所在段位",
    "  ↓",
    "  → score = segment['score']   (权重默认 1.0)",
    "  ↓",
    "[2] 多指标求和: total_score = Σ score_i (或 Σ score_i × weight_i)",
    "  ↓",
    "(注: 本版不做评级映射)",
    "  ↓",
    "输出: {total_score, details: [{指标, value, score, weight}, ...] }",
]
for line in flow_text:
    row_idx = add_paragraph(row_idx, line)
row_idx += 1

# ===================== 二、配置数据结构 =====================
row_idx = add_section_header(row_idx, "二、配置数据结构 (可配置)")

row_idx = add_paragraph(row_idx,
    "每个指标的配置是一个 dict, 包含方向、段位列表等. 权重默认 1, 可选."
)

row_idx = add_subsection(row_idx, "2.1 指标配置 Schema")
config_schema = [
    ("字段", "类型", "必填", "说明"),
    ("code", "str", "是", "指标代码 (如 'LCR'), 必须唯一"),
    ("name", "str", "是", "指标中文名 (如 '流动性覆盖率')"),
    ("direction", "str", "是", "'higher' (越高越好) 或 'lower' (越低越好)"),
    ("weight", "float", "否", "权重, 默认 1.0 (等权相加). 如需加权汇总, 可设为其他值"),
    ("regulation", "str", "否", "监管线描述 (用于显示)"),
    ("segments", "list", "是", "段位列表, 每段包含 lo/hi/score/tier"),
    ("segments[].lo", "float", "是", "区间下限 (含)"),
    ("segments[].hi", "float", "是", "区间上限 (含)"),
    ("segments[].score", "int/float", "是", "该区间对应的分数"),
    ("segments[].tier", "str", "否", "档位名称 (如 '红线', '危险', '预警', '安全', '满分')"),
]
row_idx = add_table(row_idx, ["字段", "类型", "必填", "说明"], config_schema)
row_idx += 1

row_idx = add_subsection(row_idx, "2.2 段位查找规则")
row_idx = add_paragraph(row_idx,
    "对每个 (指标, 值), 在 segments 中查找满足 lo <= value <= hi 的第一个段位 (闭区间).\n"
    "若找不到, 返回 None 或抛出异常 (取决于实现)."
)
row_idx += 1

# ===================== 三、单指标评分算法 =====================
row_idx = add_section_header(row_idx, "三、单指标评分算法")

row_idx = add_subsection(row_idx, "3.1 函数签名 (Python)")
row_idx = add_code_block(row_idx, [
    "def score_indicator(code: str, value: float) -> dict:",
    '    """',
    '    计算单个指标的得分',
    '    ',
    '    Args:',
    '        code: 指标代码 (如 "LCR")',
    '        value: 指标实际值 (float, 比例形式如 1.5 表示 150%)',
    '    ',
    '    Returns: dict 包含:',
    '        - indicator: 指标代码',
    '        - name: 指标中文名',
    '        - value: 实际值',
    '        - score: 该指标得分',
    '        - tier: 档位名称',
    '        - weight: 权重 (默认 1.0)',
    '        - weighted: 加权后分数 (score × weight)',
    '    """',
])
row_idx += 1

row_idx = add_subsection(row_idx, "3.2 算法伪代码")
pseudocode = [
    "function score_indicator(code, value):",
    "    config = INDICATORS_CONFIG[code]",
    "    weight = config.get('weight', 1.0)  # 权重默认 1",
    "    ",
    "    # 步骤 1: 验证 value 范围",
    "    if config.direction == 'higher' and value < config.segments[0].lo:",
    "        return {score: config.segments[0].score, tier: '低于最低区间'}",
    "    if config.direction == 'lower' and value > config.segments[-1].hi:",
    "        return {score: config.segments[-1].score, tier: '高于最高区间'}",
    "    ",
    "    # 步骤 2: 查找 value 所在段位",
    "    for segment in config.segments:",
    "        if segment.lo <= value <= segment.hi:",
    "            score = segment.score",
    "            tier = segment.tier",
    "            break",
    "    ",
    "    # 步骤 3: 返回结果",
    "    return {",
    "        'indicator': code,",
    "        'name': config.name,",
    "        'value': value,",
    "        'score': score,",
    "        'tier': tier,",
    "        'weight': weight,",
    "        'weighted': score * weight,",
    "    }",
]
row_idx = add_code_block(row_idx, pseudocode)
row_idx += 1

# ===================== 四、多指标汇总算法 =====================
row_idx = add_section_header(row_idx, "四、多指标汇总算法 (只求和, 不评级)")

row_idx = add_subsection(row_idx, "4.1 函数签名 (Python)")
row_idx = add_code_block(row_idx, [
    "def aggregate_scores(scores: List[dict]) -> dict:",
    '    """',
    '    汇总多个指标的总分 (本版不做评级映射)',
    '    ',
    '    Args:',
    '        scores: score_indicator() 返回的 dict 列表',
    '    ',
    '    Returns: dict 包含:',
    '        - total_score: 总分 (各指标分数之和)',
    '        - details: 各指标明细',
    '    """',
])
row_idx += 1

row_idx = add_subsection(row_idx, "4.2 算法伪代码")
pseudo2 = [
    "function aggregate_scores(scores):",
    "    total_score = 0",
    "    ",
    "    for s in scores:",
    "        # 默认等权相加 (weight = 1), 或按 score * weight 求和",
    "        total_score += s.score * s.weight",
    "    ",
    "    return {",
    "        'total_score': total_score,",
    "        'details': scores,",
    "    }",
    "",
    "# 备注: 权重默认 1, 即各指标分数直接相加",
    "# 若需加权, 配置 INDICATORS_CONFIG 时指定 weight 即可",
]
row_idx = add_code_block(row_idx, pseudo2)
row_idx += 1

# ===================== 五、本次上线 5 指标配置 =====================
row_idx = add_section_header(row_idx, "五、本次上线 5 指标配置 (Python dict, 权重默认 1)")

row_idx = add_paragraph(row_idx,
    "本节提供 5 个指标完整配置, 权重默认 1 (等权), 可根据需要修改 weight 字段."
)

row_idx = add_subsection(row_idx, "5.1 LCR (流动性覆盖率)")
lcr_cfg = [
    "{",
    '    "code": "LCR",',
    '    "name": "流动性覆盖率",',
    '    "direction": "higher",',
    '    "weight": 1,  # 默认 1',
    '    "regulation": "< 120% (本行底线, 监管 100%)",',
    '    "segments": [',
    '        {"lo": 0.00, "hi": 1.00, "score": 0,    "tier": "红线"},',
    '        {"lo": 1.00, "hi": 1.10, "score": -50,  "tier": "贴近本行底线"},',
    '        {"lo": 1.10, "hi": 1.20, "score": -100, "tier": "贴近红线"},',
    '        {"lo": 1.20, "hi": 1.30, "score": 30,   "tier": "危险-重惩罚"},',
    '        {"lo": 1.30, "hi": 1.40, "score": 80,   "tier": "预警-轻惩罚"},',
    '        {"lo": 1.40, "hi": 1.50, "score": 100,  "tier": "⭐适度最优"},',
    '        {"lo": 1.50, "hi": 2.00, "score": 95,   "tier": "略高 资金闲置"},',
    '        {"lo": 2.00, "hi": 9.99, "score": 75,   "tier": "极度过剩"},',
    "    ],",
    "}",
]
row_idx = add_code_block(row_idx, lcr_cfg)
row_idx += 1

row_idx = add_subsection(row_idx, "5.2 NSFR (净稳定资金比例)")
nsfr_cfg = [
    "{",
    '    "code": "NSFR",',
    '    "name": "净稳定资金比例",',
    '    "direction": "higher",',
    '    "weight": 1,',
    '    "regulation": "< 100% (监管)",',
    '    "segments": [',
    '        {"lo": 0.00, "hi": 1.00, "score": 0,    "tier": "红线"},',
    '        {"lo": 1.00, "hi": 1.03, "score": 35,   "tier": "危险-重惩罚"},',
    '        {"lo": 1.03, "hi": 1.045,"score": 65,   "tier": "预警-轻惩罚"},',
    '        {"lo": 1.045,"hi": 1.05, "score": 85,   "tier": "⭐中信实测 104.52%"},',
    '        {"lo": 1.05, "hi": 1.07, "score": 100,  "tier": "⭐适度最优"},',
    '        {"lo": 1.07, "hi": 1.15, "score": 90,   "tier": "略高"},',
    '        {"lo": 1.15, "hi": 9.99, "score": 75,   "tier": "过度稳定"},',
    "    ],",
    "}",
]
row_idx = add_code_block(row_idx, nsfr_cfg)
row_idx += 1

row_idx = add_subsection(row_idx, "5.3 EVE (银行账户利率风险, 越低越好)")
eve_cfg = [
    "{",
    '    "code": "EVE",',
    '    "name": "银行账户利率风险",',
    '    "direction": "lower",',
    '    "weight": 1,',
    '    "regulation": "> 15% (监管)",',
    '    "segments": [',
    '        {"lo": 0.15, "hi": 9.99, "score": 0,   "tier": "红线"},',
    '        {"lo": 0.12, "hi": 0.15, "score": 20,  "tier": "危险-重惩罚"},',
    '        {"lo": 0.105,"hi": 0.11,"score": 55,  "tier": "⭐中信实测 10.54%"},',
    '        {"lo": 0.10, "hi": 0.12, "score": 65,  "tier": "预警-轻惩罚"},',
    '        {"lo": 0.08, "hi": 0.10, "score": 85,  "tier": "可控"},',
    '        {"lo": 0.06, "hi": 0.08, "score": 96,  "tier": "⭐适度最优"},',
    '        {"lo": 0.00, "hi": 0.06, "score": 95,  "tier": "极低 (错失上行收益)"},',
    "    ],",
    "}",
]
row_idx = add_code_block(row_idx, eve_cfg)
row_idx += 1

row_idx = add_subsection(row_idx, "5.4 CET1 (核心一级资本充足率)")
cet1_cfg = [
    "{",
    '    "code": "CET1",',
    '    "name": "核心一级资本充足率",',
    '    "direction": "higher",',
    '    "weight": 1,',
    '    "regulation": "< 8.7% (7.5 监管 + 0.5 附加 + 0.7 本行)",',
    '    "segments": [',
    '        {"lo": 0.000,"hi": 0.087,"score": 0,   "tier": "红线"},',
    '        {"lo": 0.087,"hi": 0.089,"score": 35,  "tier": "危险-重惩罚"},',
    '        {"lo": 0.089,"hi": 0.090,"score": 88,  "tier": "⭐中信实测 8.98%"},',
    '        {"lo": 0.090,"hi": 0.100,"score": 100, "tier": "⭐适度最优"},',
    '        {"lo": 0.100,"hi": 0.130,"score": 92,  "tier": "过高"},',
    '        {"lo": 0.130,"hi": 1.000,"score": 78,  "tier": "极度过剩"},',
    "    ],",
    "}",
]
row_idx = add_code_block(row_idx, cet1_cfg)
row_idx += 1

row_idx = add_subsection(row_idx, "5.5 ROE (净资产收益率)")
roe_cfg = [
    "{",
    '    "code": "ROE",',
    '    "name": "净资产收益率",',
    '    "direction": "higher",',
    '    "weight": 1,',
    '    "regulation": "< 6% (硬约束, 非监管但不可接受)",',
    '    "segments": [',
    '        {"lo": 0.00,"hi": 0.06,"score": 0,   "tier": "硬约束红线"},',
    '        {"lo": 0.06,"hi": 0.08,"score": 50,  "tier": "低于行业"},',
    '        {"lo": 0.08,"hi": 0.09,"score": 75,  "tier": "行业中位"},',
    '        {"lo": 0.095,"hi": 0.0961,"score": 85,"tier": "⭐中信实测 9.61%"},',
    '        {"lo": 0.09,"hi": 0.10,"score": 85,  "tier": "行业中上"},',
    '        {"lo": 0.10,"hi": 0.12,"score": 94,  "tier": "优秀"},',
    '        {"lo": 0.12,"hi": 1.00,"score": 100, "tier": "⭐满分"},',
    "    ],",
    "}",
]
row_idx = add_code_block(row_idx, roe_cfg)
row_idx += 1

row_idx = add_subsection(row_idx, "5.6 5 指标配置 (汇总, 权重全 1)")
row_idx = add_paragraph(row_idx,
    "INDICATORS_CONFIG = {LCR: {...}, NSFR: {...}, EVE: {...}, CET1: {...}, ROE: {...}}\n"
    "所有 weight = 1 (默认等权, 汇总时直接相加分数)"
)
row_idx += 1

# ===================== 六、Python 接口契约 =====================
row_idx = add_section_header(row_idx, "六、Python 接口契约 (供开发人员实现)")

row_idx = add_subsection(row_idx, "6.1 类结构建议")
class_struct = [
    "class ScoringEngine:",
    '    """',
    '    打分引擎 (只评分, 不评级)',
    '    ',
    '    Attributes:',
    '        INDICATORS_CONFIG: dict, 5 指标配置 (权重默认 1)',
    '    ',
    '    Methods:',
    '        score_indicator(code, value) -> dict',
    '        score_all(indicator_values: dict) -> dict',
    '    """',
    "    ",
    "    INDICATORS_CONFIG = { ... }  # 5 指标配置",
    "    ",
    "    def score_indicator(self, code, value): ...",
    "    def score_all(self, indicator_values): ...",
]
row_idx = add_code_block(row_idx, class_struct)
row_idx += 1

row_idx = add_subsection(row_idx, "6.2 输入输出契约")
io_contract = [
    "输入 (score_all):",
    "    indicator_values = {",
    '        "LCR": 1.4729,        # 147.29% (比例形式)',
    '        "NSFR": 1.0452,       # 104.52%',
    '        "EVE": 0.1054,       # 10.54%',
    '        "CET1": 0.0898,      # 8.98%',
    '        "ROE": 0.0961,       # 9.61%',
    "    }",
    "    ",
    "输出 (score_all 返回值):",
    "    {",
    '        "total_score": 413.0,           # 5 指标分数之和 (各 100, 65, 65, 100, 85 + LCR/NSFR/EVE/CET1/ROE)',
    '        "details": [                   # 各指标明细',
    "            {",
    '                "indicator": "LCR",',
    '                "name": "流动性覆盖率",',
    '                "value": 1.4729,',
    '                "score": 100,',
    '                "tier": "⭐适度最优",',
    '                "weight": 1,',
    '                "weighted": 100,',
    "            },",
    "            ...",
    "        ]",
    "    }",
]
row_idx = add_code_block(row_idx, io_contract)
row_idx += 1

# ===================== 七、测试用例 =====================
row_idx = add_section_header(row_idx, "七、测试用例 (验收标准)")

test_cases = [
    ("测试", "输入", "期望输出", "说明"),
    ("LCR 适中", '{"LCR": 1.4729, ...}', "LCR.score=100", "中信实测 LCR=147.29%"),
    ("LCR 红线", '{"LCR": 0.95, ...}', "LCR.score=0 (红线)", "< 100% 触发监管"),
    ("CET1 适中", '{"CET1": 0.095, ...}', "CET1.score=100 (适度最优)", "9.5% 处于适度最优区间"),
    ("CET1 红线", '{"CET1": 0.08, ...}', "CET1.score=0 (红线)", "< 8.7% 触发监管"),
    ("EVE 适中", '{"EVE": 0.07, ...}', "EVE.score=96 (适度最优)", "7% 适度最优"),
    ("EVE 危险", '{"EVE": 0.14, ...}', "EVE.score=20 (危险-重惩罚)", "14% 接近红线"),
    ("ROE 红线", '{"ROE": 0.05, ...}', "ROE.score=0 (硬约束)", "< 6% 不可接受"),
    ("ROE 满分", '{"ROE": 0.13, ...}', "ROE.score=100 (满分)", "13% 满分"),
    ("5 指标汇总", "全指标在安全区", "total_score = Σscore (各 100, 65, 65, 100, 85 = 415)", "等权相加"),
    ("缺指标", "只传 3 个指标", "缺指标默认 0 分或报错", "需明确缺失处理"),
]
row_idx = add_table(row_idx, ["测试", "输入", "期望输出", "说明"], test_cases)
row_idx += 1

# ===================== 八、注意事项 =====================
row_idx = add_section_header(row_idx, "八、注意事项")

notes = [
    "1. 权重默认 1: 不配置 weight 字段时, 默认 1.0 (等权相加)",
    "2. 只评分不评级: 本版不包含评级映射 (A+/A/B+/B/C/D), 需要评级可后续扩展",
    "3. 配置驱动: 所有分段和分数都是配置, 修改 INDICATORS_CONFIG 不需要改代码",
    "4. 段位查找: 使用闭区间 lo <= value <= hi, 第一个匹配的段位胜出",
    "5. 方向处理: 'higher' (越高越好) 和 'lower' (越低越好) 的段位查找逻辑略有不同",
    "6. 边界值: 段位 lo=hi 时, 仅在该点匹配; 否则按区间查找",
    "7. 缺失指标: 缺指标默认 0 分, 或抛出异常 (取决于实现策略)",
    "8. 数值单位: 比例形式 (1.5 = 150%), 工具类需在配置中明确单位",
    "9. 异常处理: 指标代码不存在, value 类型错误, 段位空等都需要明确异常",
    "10. 性能: 批量计算时建议复用 INDICATORS_CONFIG, 避免重复解析",
]
for note in notes:
    row_idx = add_paragraph(row_idx, note)
    row_idx += 1

# ===================== 九、参考 =====================
row_idx = add_section_header(row_idx, "九、参考")

refs = [
    ("文档", "路径", "说明"),
    ("当前评分标准", "docs/v2/评分标准_v12b.xlsx", "4 档评分规则, 75 段位, 7 指标"),
    ("历史版本", "docs/v2/评分标准_v8.xlsx (5 指标含 LR)", "v8 版本"),
    ("折现工具参考", "docs/discount_tool.py", "Python 工具类示例"),
]
row_idx = add_table(row_idx, ["文档", "路径", "说明"], refs)
row_idx += 1

# ===================== 列宽 =====================
ws.column_dimensions['A'].width = 14
ws.column_dimensions['B'].width = 20
ws.column_dimensions['C'].width = 18
ws.column_dimensions['D'].width = 20
ws.column_dimensions['E'].width = 24
ws.column_dimensions['F'].width = 26
ws.freeze_panes = "A4"

wb.save(EXCEL_PATH)
print(f"已保存: {EXCEL_PATH}")
print(f"新增 Sheet: 打分算法说明 (共 {row_idx-1} 行)")
print(f"Sheets: {wb.sheetnames}")