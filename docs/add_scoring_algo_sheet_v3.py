"""给 评分标准_v12b.xlsx 更新 "打分算法说明" sheet (v3)

更新:
- 字段命名参考 prcp-java (KpiScheme/KpiDefinition/KpiScoreRule/KpiScoreSegment/KpiValue)
- 评分规则通过 prcp 指标方案的内容封装传入工具类
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
ws.cell(row_idx, 1, "字段命名参考 prcp 指标方案/指标定义/指标维护/指标评分模块 | 本次: LCR/NSFR/EVE/CET1/ROE 5 指标 | 只评分不评级 | 权重默认 1")
ws.cell(row_idx, 1).font = Font(name="微软雅黑", size=10, italic=True, color="555555")
ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor="FFF3E0")
ws.cell(row_idx, 1).alignment = Alignment(horizontal="center", vertical="center")
row_idx += 2

# ===================== 一、算法概述 =====================
row_idx = add_section_header(row_idx, "一、算法概述")

row_idx = add_paragraph(row_idx,
    "打分引擎只做两件事:\n"
    "  1. 单指标评分: 根据 prcp_kpi_score_segment (区间段) 找到实际值所在段, 返回 score\n"
    "  2. 多指标求和: 各指标 score 直接相加 (权重默认 1), 得到总分\n"
    "所有评分规则通过 prcp 指标方案 (prcp_kpi_scheme) 的内容封装传入, 本工具类不内置任何规则."
)
row_idx += 1

row_idx = add_subsection(row_idx, "1.1 算法流程图")
flow_text = [
    "输入: prcp 评分方案内容 (KpiScheme + KpiDefinition + KpiScoreRule + KpiScoreSegment)",
    "  ↓",
    "[1] 单指标评分: 对每个 (kpi_code, value), 在 KpiScoreSegment 中按 seg_order 查找 value 所在段",
    "  ↓",
    "  → 首个满足 min_value <= value <= max_value 的段位 → score",
    "  ↓",
    "[2] 多指标求和: total_score = Σ score_i (各 score 等权相加, 默认 weight=1)",
    "  ↓",
    "(注: 本版不做评级映射)",
    "  ↓",
    "输出: {total_score, details: [{kpi_code, kpi_name, current_value, score, segment_desc}] }",
]
for line in flow_text:
    row_idx = add_paragraph(row_idx, line)
row_idx += 1

# ===================== 二、配置数据结构 (prcp 模块映射) =====================
row_idx = add_section_header(row_idx, "二、配置数据结构 (来自 prcp 指标方案模块)")

row_idx = add_paragraph(row_idx,
    "字段命名参考 prcp-java (com.prcp.business.kpi.entity):\n"
    "  - KpiScheme (prcp_kpi_scheme): 方案元数据\n"
    "  - KpiDefinition (prcp_kpi_definition): 指标定义\n"
    "  - KpiScoreRule (prcp_kpi_score_rule): 评分规则\n"
    "  - KpiScoreSegment (prcp_kpi_score_segment): 评分段位\n"
    "  - KpiValue (prcp_kpi_value): 指标实测值"
)
row_idx += 1

row_idx = add_subsection(row_idx, "2.1 KpiScheme (方案元数据)")

scheme_schema = [
    ("字段", "类型", "必填", "说明"),
    ("id", "long", "否", "数据库主键, 工具类可不关心"),
    ("scheme_code", "str", "是", "方案编码 (唯一), 用于关联 KpiDefinition/KpiScoreRule"),
    ("scheme_name", "str", "是", "方案中文名"),
    ("description", "str", "否", "方案描述"),
    ("kpi_count", "int", "否", "方案包含的指标数 (冗余字段)"),
    ("status", "str", "否", "ACTIVE / DISABLED"),
    ("created_by / updated_by", "long", "否", "审计字段"),
    ("created_at / updated_at", "datetime", "否", "审计字段"),
    ("is_deleted", "int", "否", "逻辑删除 (0/1)"),
]
row_idx = add_table(row_idx, ["字段", "类型", "必填", "说明"], scheme_schema)
row_idx += 1

row_idx = add_subsection(row_idx, "2.2 KpiDefinition (指标定义)")
def_schema = [
    ("字段", "类型", "必填", "说明"),
    ("id", "long", "否", "主键"),
    ("scheme_id", "long", "是", "关联 KpiScheme"),
    ("kpi_code", "str", "是", "指标编码 (如 'LCR'), 唯一"),
    ("kpi_name", "str", "是", "指标中文名 (如 '流动性覆盖率')"),
    ("indicator_type", "int", "否", "1=公式 2=函数, 本工具类只读 score 字段不关心"),
    ("formula", "str", "否", "指标计算公式 (工具类不解析)"),
    ("calc_unit", "str", "否", "计算单位 (%, 倍, 元)"),
    ("formula_desc", "str", "否", "公式说明"),
    ("threshold_min", "decimal", "否", "监管/经营最小值"),
    ("threshold_max", "decimal", "否", "监管/经营最大值"),
    ("status", "str", "否", "ACTIVE / DISABLED"),
]
row_idx = add_table(row_idx, ["字段", "类型", "必填", "说明"], def_schema)
row_idx += 1

row_idx = add_subsection(row_idx, "2.3 KpiScoreRule (评分规则)")
rule_schema = [
    ("字段", "类型", "必填", "说明"),
    ("id", "long", "否", "主键"),
    ("scheme_id", "long", "是", "关联 KpiScheme"),
    ("kpi_id", "long", "是", "关联 KpiDefinition"),
    ("rule_name", "str", "是", "规则名称 (如 'LCR 评分规则')"),
    ("calc_method", "str", "否", "INTERVAL (默认值) / LINEAR / STEP"),
    ("total_score", "decimal", "否", "规则满分 (默认 100, 用于归一化)"),
    ("higher_is_better", "int", "是", "1=越高越好 (如 LCR) / 0=越低越好 (如 EVE)"),
    ("description", "str", "否", "规则描述"),
    ("status", "str", "否", "ACTIVE / DISABLED"),
]
row_idx = add_table(row_idx, ["字段", "类型", "必填", "说明"], rule_schema)
row_idx += 1

row_idx = add_subsection(row_idx, "2.4 KpiScoreSegment (评分段位)")
seg_schema = [
    ("字段", "类型", "必填", "说明"),
    ("id", "long", "否", "主键"),
    ("rule_id", "long", "是", "关联 KpiScoreRule"),
    ("seg_order", "int", "是", "段位序号, 按升序匹配第一个落入区间"),
    ("min_value", "decimal", "是", "区间下限 (含)"),
    ("max_value", "decimal", "是", "区间上限 (含)"),
    ("score", "decimal", "是", "该段位的分数"),
    ("segment_desc", "str", "否", "段位说明 (如 '红线', '适度最优')"),
    ("is_deleted", "int", "否", "逻辑删除"),
]
row_idx = add_table(row_idx, ["字段", "类型", "必填", "说明"], seg_schema)
row_idx += 1

row_idx = add_subsection(row_idx, "2.5 KpiValue (指标实测值)")
val_schema = [
    ("字段", "类型", "必填", "说明"),
    ("id", "long", "否", "主键"),
    ("kpi_id", "long", "是", "关联 KpiDefinition"),
    ("data_date", "date", "是", "数据日期 (如 2025-12-31)"),
    ("version", "str", "否", "方案版本 (如 V1)"),
    ("current_value", "decimal", "是", "当前实测值 (本工具类的输入)"),
    ("prev_value", "decimal", "否", "上一期值 (用于平滑性约束)"),
    ("prev_year_value", "decimal", "否", "上年同期值"),
    ("calc_source", "str", "否", "计算来源 (公式/手工/外部)"),
    ("calc_log", "str", "否", "计算日志"),
    ("score", "decimal", "否", "本工具类输出后回填"),
]
row_idx = add_table(row_idx, ["字段", "类型", "必填", "说明"], val_schema)
row_idx += 1

# ===================== 三、单指标评分算法 =====================
row_idx = add_section_header(row_idx, "三、单指标评分算法")

row_idx = add_subsection(row_idx, "3.1 函数签名 (Python)")
row_idx = add_code_block(row_idx, [
    "def score_indicator(",
    "    kpi_code: str,",
    "    current_value: float,",
    "    score_rule: dict,",
    "    score_segments: List[dict]",
    ") -> dict:",
    '    """',
    '    根据 prcp 评分规则计算单指标得分',
    '    ',
    '    Args:',
    '        kpi_code: 指标编码 (如 "LCR")',
    '        current_value: 指标实测值 (来自 KpiValue.current_value)',
    '        score_rule: KpiScoreRule dict',
    '        score_segments: 该规则的 KpiScoreSegment list (按 seg_order 已排序)',
    '    ',
    '    Returns: dict (写入 KpiValue.score):',
    '        - kpi_code, kpi_name',
    '        - current_value, score, segment_desc',
    '    """',
])
row_idx += 1

row_idx = add_subsection(row_idx, "3.2 算法伪代码")
pseudocode = [
    "function score_indicator(kpi_code, current_value, score_rule, score_segments):",
    "    higher_is_better = score_rule.higher_is_better  # 1 or 0",
    "    ",
    "    # 步骤 1: 边界检查",
    "    first_seg = score_segments[0]",
    "    last_seg = score_segments[-1]",
    "    if higher_is_better == 1 and current_value < first_seg.min_value:",
    "        return {score: first_seg.score, segment_desc: first_seg.segment_desc}",
    "    if higher_is_better == 0 and current_value > last_seg.max_value:",
    "        return {score: last_seg.score, segment_desc: last_seg.segment_desc}",
    "    ",
    "    # 步骤 2: 按 seg_order 升序遍历, 找首个满足区间的段位",
    "    for segment in score_segments:  # 已按 seg_order 升序",
    "        if segment.min_value <= current_value <= segment.max_value:",
    "            return {",
    "                'kpi_code': kpi_code,",
    "                'current_value': current_value,",
    "                'score': segment.score,",
    "                'segment_desc': segment.segment_desc,",
    "                'seg_order': segment.seg_order,",
    "            }",
    "    ",
    "    return None  # 找不到匹配段位",
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
    '    Returns: dict:',
    '        - total_score: 总分',
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
    "        # 默认等权 (权重 = 1, 来自 KpiScoreRule.totalScore)",
    "        total_score += s.score",
    "    ",
    "    return {",
    "        'total_score': total_score,",
    "        'details': scores,",
    "    }",
]
row_idx = add_code_block(row_idx, pseudo2)
row_idx += 1

# ===================== 五、本次上线 5 指标配置 (prcp 风格) =====================
row_idx = add_section_header(row_idx, "五、本次上线 5 指标配置 (prcp 风格)")

row_idx = add_paragraph(row_idx,
    "配置通过 prcp 指标方案的内容封装传入工具类, 不内置在本表中.\n"
    "以下示例展示本次推荐配置的结构."
)

row_idx = add_subsection(row_idx, "5.1 KpiScheme + KpiDefinition (5 指标)")
scheme_def = [
    "{",
    '    "scheme": {',
    '        "scheme_code": "BANK_SCORE_2025_V1",',
    '        "scheme_name": "中信银行 2025 年度评分方案",',
    '        "description": "LCR/NSFR/EVE/CET1/ROE 5 指标",',
    '        "kpi_count": 5,',
    '        "status": "ACTIVE"',
    "    },",
    '    "definitions": [',
    '        {"kpi_code": "LCR",  "kpi_name": "流动性覆盖率",    "calc_unit": "%"},',
    '        {"kpi_code": "NSFR", "kpi_name": "净稳定资金比例",  "calc_unit": "%"},',
    '        {"kpi_code": "EVE",  "kpi_name": "银行账户利率风险", "calc_unit": "%"},',
    '        {"kpi_code": "CET1", "kpi_name": "核心一级资本充足率", "calc_unit": "%"},',
    '        {"kpi_code": "ROE",  "kpi_name": "净资产收益率",    "calc_unit": "%"},',
    "    ]",
    "}",
]
row_idx = add_code_block(row_idx, scheme_def)
row_idx += 1

row_idx = add_subsection(row_idx, "5.2 KpiScoreRule + KpiScoreSegment (LCR 示例)")
rule_seg = [
    "{",
    '    "rule": {',
    '        "scheme_code": "BANK_SCORE_2025_V1",',
    '        "kpi_code": "LCR",',
    '        "rule_name": "LCR 评分规则",',
    '        "calc_method": "INTERVAL",',
    '        "total_score": 100,',
    '        "higher_is_better": 1,',
    '        "description": "LCR 监管底线 120%"',
    "    },",
    '    "segments": [',
    '        {"seg_order": 1,  "min_value": 0.00, "max_value": 1.00, "score": 0,    "segment_desc": "红线 <100%"},',
    '        {"seg_order": 2,  "min_value": 1.00, "max_value": 1.10, "score": -50,  "segment_desc": "贴近本行底线"},',
    '        {"seg_order": 3,  "min_value": 1.10, "max_value": 1.20, "score": -100, "segment_desc": "贴近红线"},',
    '        {"seg_order": 4,  "min_value": 1.20, "max_value": 1.30, "score": 30,   "segment_desc": "危险-重惩罚"},',
    '        {"seg_order": 5,  "min_value": 1.30, "max_value": 1.40, "score": 80,   "segment_desc": "预警-轻惩罚"},',
    '        {"seg_order": 6,  "min_value": 1.40, "max_value": 1.50, "score": 100,  "segment_desc": "⭐适度最优"},',
    '        {"seg_order": 7,  "min_value": 1.50, "max_value": 2.00, "score": 95,   "segment_desc": "略高 资金闲置"},',
    '        {"seg_order": 8,  "min_value": 2.00, "max_value": 9.99, "score": 75,   "segment_desc": "极度过剩"},',
    "    ]",
    "}",
]
row_idx = add_code_block(row_idx, rule_seg)
row_idx += 1

row_idx = add_subsection(row_idx, "5.3 KpiValue (5 指标实测值)")
kpi_values = [
    "{",
    '    "data_date": "2025-12-31",',
    '    "version": "BANK_SCORE_2025_V1",',
    '    "values": [',
    '        {"kpi_code": "LCR",  "current_value": 1.4729},   # 147.29%',
    '        {"kpi_code": "NSFR", "current_value": 1.0452},   # 104.52%',
    '        {"kpi_code": "EVE",  "current_value": 0.1054},   # 10.54%',
    '        {"kpi_code": "CET1", "current_value": 0.0898},   # 8.98%',
    '        {"kpi_code": "ROE",  "current_value": 0.0961},   # 9.61%',
    "    ]",
    "}",
]
row_idx = add_code_block(row_idx, kpi_values)
row_idx += 1

# ===================== 六、Python 接口契约 =====================
row_idx = add_section_header(row_idx, "六、Python 接口契约")

row_idx = add_subsection(row_idx, "6.1 类结构建议")
class_struct = [
    "class ScoringEngine:",
    '    """',
    '    打分引擎 (输入: prcp 评分方案内容, 输出: 单指标 score + 总分)',
    '    ',
    '    Attributes:',
    '        scheme: dict (KpiScheme)',
    '        definitions: list[dict] (KpiDefinition × N)',
    '        rules: dict[kpi_code, dict] (KpiScoreRule 按 kpi_code 索引)',
    '        segments: dict[kpi_code, list[dict]] (KpiScoreSegment 按 kpi_code 索引)',
    '    ',
    '    Methods:',
    '        score_indicator(kpi_code, current_value) -> dict',
    '        score_all(kpi_values: dict) -> dict',
    '    """',
    "    ",
    "    def __init__(self, scheme, definitions, rules, segments): ...",
    "    def score_indicator(self, kpi_code, current_value): ...",
    "    def score_all(self, kpi_values: dict): ...",
]
row_idx = add_code_block(row_idx, class_struct)
row_idx += 1

row_idx = add_subsection(row_idx, "6.2 输入输出契约")
io_contract = [
    "输入 (ScoringEngine.__init__):",
    "    scheme: dict = {",
    '        "scheme_code": "BANK_SCORE_2025_V1",',
    '        "scheme_name": "...",',
    "    }",
    "    definitions: list[dict] = [",
    '        {"kpi_code": "LCR", "kpi_name": "流动性覆盖率", ...},',
    "        ...",
    "    ]",
    "    rules: dict = {",
    '        "LCR": {"kpi_code": "LCR", "higher_is_better": 1, "total_score": 100, ...},',
    "        ...",
    "    }",
    "    segments: dict = {",
    '        "LCR": [{"seg_order": 1, "min_value": 0, "max_value": 1.0, "score": 0, ...}, ...],',
    "        ...",
    "    }",
    "    ",
    "输入 (score_all):",
    "    kpi_values = {",
    '        "kpi_code": "LCR",  "current_value": 1.4729',
    '        "kpi_code": "NSFR", "current_value": 1.0452',
    "        ...",
    "    }",
    "    ",
    "输出 (score_all 返回值):",
    "    {",
    '        "total_score": 413.0,           # 各指标 score 之和',
    '        "details": [',
    "            {",
    '                "kpi_code": "LCR",',
    '                "current_value": 1.4729,',
    '                "score": 100,',
    '                "segment_desc": "⭐适度最优",',
    '                "seg_order": 6,',
    "            },",
    "            ...",
    "        ]",
    "    }",
]
row_idx = add_code_block(row_idx, io_contract)
row_idx += 1

# ===================== 七、测试用例 =====================
row_idx = add_section_header(row_idx, "七、测试用例")

test_cases = [
    ("测试", "输入", "期望输出", "说明"),
    ("LCR 适中", '{"kpi_code": "LCR", "current_value": 1.4729}', "score=100", "147.29% 适度最优"),
    ("LCR 红线", '{"kpi_code": "LCR", "current_value": 0.95}', "score=0", "<100% 红线"),
    ("CET1 适中", '{"kpi_code": "CET1", "current_value": 0.095}', "score=100", "9.5% 适度最优"),
    ("CET1 红线", '{"kpi_code": "CET1", "current_value": 0.08}', "score=0", "<8.7% 红线"),
    ("EVE 适中", '{"kpi_code": "EVE", "current_value": 0.07}', "score=96", "7% 适度最优 (越低越好)"),
    ("EVE 危险", '{"kpi_code": "EVE", "current_value": 0.14}', "score=20", "14% 接近红线"),
    ("ROE 红线", '{"kpi_code": "ROE", "current_value": 0.05}', "score=0", "<6% 硬约束"),
    ("ROE 满分", '{"kpi_code": "ROE", "current_value": 0.13}', "score=100", "13% 满分"),
    ("5 指标汇总", "5 指标全在安全区", "total_score = Σscore", "等权相加"),
    ("缺指标", "只传 3 个指标", "默认 0 分或报错", "需明确缺失处理"),
]
row_idx = add_table(row_idx, ["测试", "输入", "期望输出", "说明"], test_cases)
row_idx += 1

# ===================== 八、注意事项 =====================
row_idx = add_section_header(row_idx, "八、注意事项")

notes = [
    "1. 字段命名: 严格使用 prcp_kpi_* 实体字段名 (snake_case), 不创造新字段",
    "2. 配置来源: KpiScheme/KpiDefinition/KpiScoreRule/KpiScoreSegment 来自 prcp 指标方案模块, 不内置在工具类",
    "3. 权重: 默认 1 (KpiScoreRule.totalScore 即满分, 用于归一化)",
    "4. 评级映射: 本版不包含评级 (A+/A/B+/B/C/D), 需要评级可后续扩展",
    "5. 段位查找: 按 seg_order 升序遍历, 首个满足 min_value <= value <= max_value 的段位胜出",
    "6. 方向处理: KpiScoreRule.higher_is_better = 1/0, 不再使用 direction 字符串",
    "7. 缺失指标: 默认 score=0, 或抛出异常 (取决于实现)",
    "8. 数据类型: KpiScoreSegment.min_value 是 Decimal, 工具类需支持 Decimal/float",
    "9. 异常处理: kpi_code 不存在, value 类型错误, 段位空都需要明确异常",
    "10. 性能: 批量计算时建议预处理 segments (按 kpi_code 索引), 避免重复遍历",
]
for note in notes:
    row_idx = add_paragraph(row_idx, note)
    row_idx += 1

# ===================== 九、参考 =====================
row_idx = add_section_header(row_idx, "九、参考")

refs = [
    ("模块", "prcp-java 实体", "字段命名参考"),
    ("指标方案", "com.prcp.business.kpi.entity.KpiScheme", "scheme_code / scheme_name / description / kpi_count / status"),
    ("指标定义", "com.prcp.business.kpi.entity.KpiDefinition", "scheme_id / kpi_code / kpi_name / calc_unit / threshold_min / threshold_max"),
    ("评分规则", "com.prcp.business.kpi.entity.KpiScoreRule", "scheme_id / kpi_id / rule_name / calc_method / total_score / higher_is_better"),
    ("评分段位", "com.prcp.business.kpi.entity.KpiScoreSegment", "rule_id / seg_order / min_value / max_value / score / segment_desc"),
    ("指标值", "com.prcp.business.kpi.entity.KpiValue", "kpi_id / data_date / version / current_value / prev_value / prev_year_value / score"),
]
row_idx = add_table(row_idx, ["模块", "prcp-java 实体", "字段命名参考"], refs)
row_idx += 1

# ===================== 列宽 =====================
ws.column_dimensions['A'].width = 22
ws.column_dimensions['B'].width = 14
ws.column_dimensions['C'].width = 16
ws.column_dimensions['D'].width = 22
ws.column_dimensions['E'].width = 24
ws.column_dimensions['F'].width = 24
ws.freeze_panes = "A4"

wb.save(EXCEL_PATH)
print(f"已保存: {EXCEL_PATH}")
print(f"更新 Sheet: 打分算法说明 (共 {row_idx-1} 行)")
print(f"Sheets: {wb.sheetnames}")