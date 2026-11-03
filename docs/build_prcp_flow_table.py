#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成「PRCP 组合反算主流程」泳道流程表 Excel
输入源：PRCP/docs/PRCP系统整理流程图.html (0.2 泳道总图)
列规范对齐 visio-flow-generator：阶段 / 具体事项 / 操作 / 责任人 / 备注
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "PRCP组合反算主流程_流程表.xlsx")

# (阶段, 具体事项, 操作, 责任人, 备注)
ROWS = [
    # ── ① 业务人员操作（前端 · 组合反算模块）────────────────────────────
    ("STEP1", "方案发起", "进入组合反算方案页", "业务人员", "prcp_reverse_scheme"),
    ("STEP1", "方案发起", "创建反算方案，填写编号与类型", "业务人员", "scheme_code / name / type"),
    ("STEP1", "方案发起", "选择计量模型，指定算法与模型 ID", "业务人员", "prcp_model"),
    ("STEP1", "方案发起", "选账户册方案，定位账户册树", "业务人员", "coa_scheme_id"),
    ("STEP1", "方案发起", "选数据日期，定位基准日数据", "业务人员", "data_date"),
    ("STEP1", "方案发起", "配置目标约束，设定目标值与类型", "业务人员", "prcp_reverse_target"),

    # ── ② 底层数据准备 ────────────────────────────────────────────────
    ("STEP2", "数据准备", "展开账户册树，加载全量节点及层级", "数据准备服务", "prcp_coa_node"),
    ("STEP2", "数据准备", "载入基准日余额、加权利率与期限桶", "数据准备服务", "prcp_data_basic"),
    ("STEP2", "数据准备", "按节点分流为模型节点与非模型节点", "数据准备服务", "is_model_calc"),

    # ── ③ 非模型训练节点 · 新业务模拟 ──────────────────────────────────
    ("STEP3", "新业务模拟", "匹配模拟方案，按账户册方案关联", "新业务模拟引擎", "sim_scheme"),
    ("STEP3", "新业务模拟", "增长配置，设定 4 种方式与 5 年参数", "新业务模拟引擎", "sim_growth_config"),
    ("STEP3", "新业务模拟", "节奏配置，设定 12 个月投放权重", "新业务模拟引擎", "sim_rhythm"),
    ("STEP3", "新业务模拟", "期限占比配置，设定占比与利率", "新业务模拟引擎", "sim_term_ratio"),
    ("STEP3", "新业务模拟", "运行模拟，按月推演 60 个月", "新业务模拟引擎", "NewBusinessEngine"),
    ("STEP3", "新业务模拟", "产出模拟结果：余额/利率/利息/桶", "新业务模拟引擎", "sim_result"),

    # ── 任务包传递 ────────────────────────────────────────────────────
    ("STEP4", "任务下发", "打包 7 类信息，下发计量引擎", "计量引擎", "prcp_reverse_scheme/run"),

    # ── ④ 模型训练节点 · 计量模型反算 ──────────────────────────────────
    ("STEP5", "模型反算", "非线性方程求解 Newton / SLSQP", "计量模型引擎", "NONLINEAR_SOLVER"),
    ("STEP5", "模型反算", "蚁群组合优化，群体智能寻优", "计量模型引擎", "ANT_COLONY"),
    ("STEP5", "模型反算", "DNN 回归，评分为奖励函数", "计量模型引擎", "DNN_NEURAL_NETWORK"),
    ("STEP5", "模型反算", "输出模型节点 24 月业务量预测", "计量模型引擎", "prcp_model_param"),

    # ── ⑤ 合并成完整业务表 ────────────────────────────────────────────
    ("STEP6", "指标计量", "并集合并：模拟结果 ∪ 模型结果", "指标计量引擎", "全量账户册 × 24 月"),
    ("STEP6", "指标计量", "生成完整业务表 current/adjusted/delta", "指标计量引擎", "prcp_data_basic"),
    ("STEP6", "指标计量", "指标值计量：公式引擎与函数执行器", "指标计量引擎", "prcp_kpi_definition"),
    ("STEP6", "指标计量", "指标评分：分段插值与锚点插值", "指标计量引擎", "DNN 训练作奖励函数"),

    # ── ⑥ 结果整理与展示 ──────────────────────────────────────────────
    ("STEP7", "结果输出", "约束校验，按 GE/LE/EQ 比对达成", "反算驾驶舱", "prcp_reverse_target"),
    ("STEP7", "结果输出", "写结果表，落库 64 期限桶", "反算驾驶舱", "reverse_result"),
    ("STEP7", "结果输出", "结果对比 current 与 adjusted 变化", "反算驾驶舱", "64 桶 delta"),
    ("STEP7", "结果输出", "驾驶舱展示 KPI 卡、趋势与达成", "反算驾驶舱", "反算驾驶舱"),
]

TITLE = "PRCP 组合反算主流程"

wb = Workbook()

thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
head_fill = PatternFill("solid", fgColor="1F4E79")
head_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
body_font = Font(name="微软雅黑", size=10)
title_font = Font(name="微软雅黑", size=12, bold=True, color="1F4E79")

ws = wb.active
ws.title = "组合反算主流程"

# 标题行（整行仅一个非空单元格 + 含「流程」→ 被识别为 Page 名）
ws.cell(row=1, column=1, value=TITLE).font = title_font
ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
ws.row_dimensions[1].height = 24

# 表头行
HEADERS = ["阶段", "具体事项", "操作", "责任人", "备注"]
for c, h in enumerate(HEADERS, 1):
    cell = ws.cell(row=2, column=c, value=h)
    cell.fill = head_fill
    cell.font = head_font
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border

# 数据行
for r, row in enumerate(ROWS, 3):
    for c, v in enumerate(row, 1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = body_font
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = border

widths = {"A": 10, "B": 20, "C": 52, "D": 16, "E": 30}
for col, w in widths.items():
    ws.column_dimensions[col].width = w

wb.save(OUT)
print("OK ->", OUT)
print("数据行数:", len(ROWS))
print("阶段数:", len({r[0] for r in ROWS}))
print("角色数:", len({r[3] for r in ROWS}))
