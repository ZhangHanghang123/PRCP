#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成「模型反算」相关的 6 张子流程图流程表（多 Sheet → 多 Visio Page）。

口径来源（全部以源码/官方文档为准，不臆造）：
  ① 模型反算主链路     ← 模型管理_三种模型处理逻辑.html（训练/衔接章节）
  ② 新业务现金流滚动   ← backend/.../new_business/engine.py（v2.2/v2.4 口径）
  ③ 指标计量链路       ← PRCP系统整理流程图.html 0.4 + prcp_kpi_definition
  ④ 指标评分链路       ← 模型管理文档 6.1~6.5（PIECEWISE / LINEAR）
  ⑤ citideepalm 训练   ← C:/银行经营/citideepalm（training/ + engine/）
  ⑥ citideepalm 推理   ← C:/银行经营/citideepalm（export_prcp_mm_deploy 等）

图⑤⑥ 说明：PRCP 的 DNN 反算模型调用 citideepalm 的推理模块；
citideepalm 分训练与推理两条链路，**两者都用到指标计算与指标评分**
（LCR/NSFR/EVE/CAR → 0~500 分 → 惩罚项）。

列规范对齐 visio-flow-generator：阶段 / 具体事项 / 操作 / 责任人 / 备注
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "模型反算_子流程图_流程表.xlsx")

# ============================================================
# 图 1：模型反算主链路
# ============================================================
FLOW1 = {
    "title": "模型反算主链路",
    "rows": [
        # ── 阶段1 取数与建模 ──
        ("STEP1", "模型建模", "配置算法类型与业务域，关联指标方案", "业务人员", "prcp_model.kpi_scheme_id"),
        ("STEP1", "模型建模", "创建模型版本，复制参数快照", "业务人员", "prcp_model_version"),
        ("STEP1", "模型建模", "挂载超参与关联指标 kpi_id", "业务人员", "prcp_model_param"),
        ("STEP1", "模型建模", "发起训练任务：指定窗口与账户册方案", "业务人员", "prcp_model_train"),

        # ── 阶段2 取数 ──
        ("STEP2", "训练取数", "读取余额序列 prcp_data_balance 月度快照", "训练引擎", "prcp_data_balance"),
        ("STEP2", "训练取数", "读取 ESG 曲线计划作为情景特征", "训练引擎", "prcp_esg_curve_point"),
        ("STEP2", "训练取数", "参数 formula 派生特征（余额/指标值/折算系数）", "训练引擎", "param.formula 通道"),

        # ── 阶段3 三类算法（三选一并行分支，非串联）──
        ("STEP3", "算法求解", "按 model_type 三选一，分支求解", "训练引擎", "三类算法并行可选"),
        ("STEP3", "算法求解", "分支A 非线性方程求解 Newton/SLSQP", "训练引擎", "NONLINEAR_SOLVER"),
        ("STEP3", "算法求解", "分支B 蚁群组合优化 群体智能寻优", "训练引擎", "ANT_COLONY"),
        ("STEP3", "算法求解", "分支C DNN 回归 奖励=指标方案评分", "训练引擎", "DNN_NEURAL_NETWORK"),

        # ── 阶段4 落库 ──
        ("STEP4", "结果落库", "写预测值 predicted 与置信区间 CI", "训练引擎", "prcp_model_train_result"),
        ("STEP4", "结果落库", "汇总项 rpt_item_code=SUMMARY 衔接报表", "训练引擎", "rpt_item_id=0"),

        # ── 阶段5 回流与衔接 ──
        ("STEP5", "预测值回流", "指标计量用预测值替代实测值算未来指标", "指标计量引擎", "prcp_kpi_value"),
        ("STEP5", "预测值回流", "指标评分对未来值打分 → 趋势预警", "指标评分引擎", "prcp_kpi_value.score"),
        ("STEP5", "预测值回流", "待补：回写 prcp_kpi_value 未来期次", "系统", "★当前能力缺口（未实现）"),
    ],
}

# ============================================================
# 图 2：新业务现金流滚动（逐月推演）
# ============================================================
FLOW2 = {
    "title": "新业务现金流逐月滚动",
    "rows": [
        # ── 阶段1 初始化 ──
        ("STEP1", "初始状态", "取基准日状态：余额/均值/加权利率/月息", "新业务模拟引擎", "get_initial_state"),
        ("STEP1", "初始状态", "判定节点是否测算：is_model_calc", "新业务模拟引擎", "1=模型 2=非模型"),

        # ── 阶段2 年目标 ──
        ("STEP2", "年目标增量", "type1/3 目标=B×参数%/100", "新业务模拟引擎", "compute_year_target"),
        ("STEP2", "年目标增量", "type2 目标=参数×单位换算", "新业务模拟引擎", "万元 1e4 / 亿元 1e8"),
        ("STEP2", "年目标增量", "type4 目标=年末余额−年初余额（可为负）", "新业务模拟引擎", "余额锚定=缩表"),

        # ── 阶段3 当月投放 ──
        ("STEP3", "当月投放", "按节奏权重分摊：add=年目标×w[m]/100", "新业务模拟引擎", "12月权重，跨年复用"),
        ("STEP3", "当月投放", "快照计划到期额（take_due 之前）", "新业务模拟引擎", "peek_due"),
        ("STEP3", "当月投放", "取走当月到期额并清零：release=rem_m[k]", "新业务模拟引擎", "take_due"),
        ("STEP3", "当月投放", "type1/2 回补到期：month_new=release+add", "新业务模拟引擎", "净增长口径"),
        ("STEP3", "当月投放", "type3/4 不回补：month_new=add", "新业务模拟引擎", "毛投放口径"),

        # ── 阶段4 落桶 ──
        ("STEP4", "期限落桶", "按期限占比拆分：amount_v=month_new×pct/100", "新业务模拟引擎", "apply_term_split"),
        ("STEP4", "期限落桶", "原始期限桶只进不出：orig_mv += amount_v", "新业务模拟引擎", "记录投放时原始期限"),
        ("STEP4", "期限落桶", "绝对到期月直落：rem_m{k+v} += amount_v", "新业务模拟引擎", "v2.2 取消整体前移"),
        ("STEP4", "期限落桶", "超 60 月归档长端：y10/y15/y20/y30", "新业务模拟引擎", "_due_key"),

        # ── 阶段5 指标重算 ──
        ("STEP5", "指标重算", "余额：new_current = B + add", "新业务模拟引擎", "分支A 不测算则不变"),
        ("STEP5", "指标重算", "均值：new_avg = avg_balance + add/2", "新业务模拟引擎", "投放期中点法"),
        ("STEP5", "指标重算", "加权利率：加权平均后除以 avg+month_new", "新业务模拟引擎", "★利率单位需统一"),
        ("STEP5", "指标重算", "月息：new_interest = new_avg × new_wr / 12", "新业务模拟引擎", "月息=均值×加权利率/12"),

        # ── 阶段6 排期汇总 ──
        ("STEP6", "排期汇总", "累加 60 月完整到期排期（存量+全部投放）", "新业务模拟引擎", "accumulate_plan"),
        ("STEP6", "排期汇总", "写回结果行：每格都有值，形成时间轴", "新业务模拟引擎", "apply_final_plan"),
    ],
}

# ============================================================
# 图 3：指标计量链路
# ============================================================
FLOW3 = {
    "title": "指标计量计算链路",
    "rows": [
        # ── 阶段1 取定义 ──
        ("STEP1", "取指标定义", "按模型关联的 kpi_scheme_id 取指标方案", "指标计量引擎", "prcp_kpi_scheme"),
        ("STEP1", "取指标定义", "逐条加载指标定义：公式或函数脚本", "指标计量引擎", "prcp_kpi_definition"),
        ("STEP1", "取指标定义", "加载折算系数与运算符参数", "指标计量引擎", "prcp_*_param"),

        # ── 阶段2 准备上下文 ──
        ("STEP2", "准备上下文", "注入完整业务表：current/adjusted/delta", "指标计量引擎", "prcp_data_basic"),
        ("STEP2", "准备上下文", "注入同方案其他指标的该期值 ctx", "指标计量引擎", "★ctx 互引用"),
        ("STEP2", "准备上下文", "实测值或模型预测值（未来期次）", "指标计量引擎", "prcp_kpi_value"),

        # ── 阶段3 求值 ──
        ("STEP3", "逐项求值", "type=1 公式引擎：evaluate(formula, ctx)", "指标计量引擎", "prcp_kpi_value"),
        ("STEP3", "逐项求值", "type=2 函数执行器：run_function_kpi(...)", "指标计量引擎", "指标函数脚本"),
        ("STEP3", "逐项求值", "按期次循环：24 期逐月计算", "指标计量引擎", "current / adjusted"),

        # ── 阶段4 结果 ──
        ("STEP4", "结果落库", "写指标值：指标编码 + 期次 + 当前值", "指标计量引擎", "prcp_kpi_value"),
        ("STEP4", "结果落库", "记录 delta 变化供对比展示", "指标计量引擎", "adjusted − current"),
    ],
}

# ============================================================
# 图 4：指标评分链路
# ============================================================
FLOW4 = {
    "title": "指标评分计算链路",
    "rows": [
        # ── 阶段1 取规则 ──
        ("STEP1", "取评分规则", "按指标取评分规则：算法/满分/方向", "指标评分引擎", "prcp_kpi_score_rule"),
        ("STEP1", "取评分规则", "加载评分分段：区间→分数映射", "指标评分引擎", "prcp_kpi_score_segment"),
        ("STEP1", "取评分规则", "higher_is_better 决定优劣方向", "指标评分引擎", "评分方向"),

        # ── 阶段2 取值 ──
        ("STEP2", "取待评价值", "value 可以是实测值 / 模型预测值 / 情景值", "指标评分引擎", "★语义与来源无关"),
        ("STEP2", "取待评价值", "蒙特卡洛可取三值：悲观/中性/乐观", "指标评分引擎", "conf_low / predicted / conf_high"),

        # ── 阶段3 算分 ──
        ("STEP3", "区间命中", "PIECEWISE：按 [min,max) 命中分段", "指标评分引擎", "监管档位指标"),
        ("STEP3", "区间命中", "LINEAR：按锚点对 (x,score) 插值", "指标评分引擎", "平滑指标"),
        ("STEP3", "区间命中", "段内插值：score_min+(x−min)/(max−min)×Δscore", "指标评分引擎", "score_min 空则阶梯"),
        ("STEP3", "区间命中", "LINEAR 超端点做 clamp 截断", "指标评分引擎", "y1+(x−x1)/(x2−x1)×(y2−y1)"),

        # ── 阶段4 出分 ──
        ("STEP4", "出分落库", "写 score 到指标值行（与 current_value 同行）", "指标评分引擎", "prcp_kpi_value.score"),
        ("STEP4", "出分落库", "DNN 训练时评分作为奖励函数驱动收敛", "指标评分引擎", "★指标↔模型闭环"),
        ("STEP4", "出分落库", "未来期次评分对比当前 → 趋势预警", "指标评分引擎", "风险幅度"),
    ],
}

# ============================================================
# 图 5：citideepalm 策略模型训练流程（被 PRCP 的 DNN 模型调用）
# ============================================================
FLOW5 = {
    "title": "citideepalm策略模型训练流程",
    "rows": [
        # ── 阶段1 场景与数据准备 ──
        ("STEP1", "场景准备", "生成 ESG 情景包：HJM 5 因子 × 情景 × 期限", "ESG 场景工厂", "hjm_5f_*.pt"),
        ("STEP1", "场景准备", "读取 T0 账户工作簿：余额/期限/权重", "账户引擎", "engine/data/t0/"),
        ("STEP1", "场景准备", "切分训练集:验证集 = 95:5（固定种子）", "训练调度器", "种子 20261025"),
        ("STEP1", "场景准备", "冻结策略 PCA 3 因子状态", "ESG 场景工厂", "policy_pca_3f.npz"),

        # ── 阶段2 系数采样 ──
        ("STEP2", "系数采样", "按情景采样 τ：目标增长率 0.075~0.11", "训练调度器", "sample_training_coefficients"),
        ("STEP2", "系数采样", "按情景采样 γ：评分损失权重 0.5~10", "训练调度器", "★验证取 τ=0.0925 γ=5.25"),
        ("STEP2", "系数采样", "采样经营成本 / 增长 / 派息比例", "训练调度器", "派息 30.7% 准备金 6%/1.6%"),

        # ── 阶段3 账本推演（引擎核心）──
        ("STEP3", "账户账本推演", "run_account_rollout 逐月推进 360 月网格", "账户引擎", "prcp_alm.ledger"),
        ("STEP3", "账户账本推演", "策略网络输出决策：65 期限档配置分布", "策略网络", "AccountPolicy / AccountHead"),
        ("STEP3", "账户账本推演", "按决策档重配资产，产生现金流与余额", "账户引擎", "★决策档受 T0 权重约束"),
        ("STEP3", "账户账本推演", "记录每月后置状态：余额/现金/权益/现金流", "账户引擎", "post 状态供指标计算"),

        # ── 阶段4 指标计算（每月）──
        ("STEP4", "指标计算", "LCR：HQLA ÷ 净流出（流入按 75% 封顶）", "指标计算模块", "calculate_lcr_nsfr_indicators"),
        ("STEP4", "指标计算", "NSFR：ASF ÷ RSF × 最终调整系数", "指标计算模块", "nsfr_final_adjustment_factor"),
        ("STEP4", "指标计算", "EVE：六情景冲击下 ΔEVE 绝对值比率", "指标计算模块", "delta_eve_from_cashflows"),
        ("STEP4", "指标计算", "CAR：CET1 资本 ÷ 风险加权资产", "指标计算模块", "★CAR 为规则指标"),

        # ── 阶段5 指标评分（每月）──
        ("STEP5", "指标评分", "四项原始指标映射为 0~500 分（分段插值）", "指标评分模块", "map_indicator_tensors"),
        ("STEP5", "指标评分", "四指标等权加权：LCR/NSFR/EVE/CAR 各 0.25", "指标评分模块", "weighted_score_tensor"),
        ("STEP5", "指标评分", "距离最优 500 分的二次惩罚 ((500−q)/40)²", "指标评分模块", "score_penalty_tensor"),

        # ── 阶段6 损失与反传 ──
        ("STEP6", "损失计算", "目标损失：未达目标权益的缺口平方", "训练调度器", "target_loss"),
        ("STEP6", "损失计算", "评分惩罚损失：γ × 月均惩罚", "训练调度器", "rule_penalty_loss"),
        ("STEP6", "损失计算", "总损失 = 目标损失 + 评分惩罚损失", "训练调度器", "compute_account_objective"),
        ("STEP6", "损失计算", "反向传播更新策略网络参数（梯度裁剪）", "训练调度器", "lr 0.02 / 梯度裁剪 0.2"),
        ("STEP6", "损失计算", "早停与最优权重保存（耐心 5 轮）", "训练调度器", "★早停耐心 5"),

        # ── 阶段7 验证与导出 ──
        ("STEP7", "验证评估", "验证集逐月推演并重新计算指标与评分", "训练调度器", "★验证同样走指标+评分"),
        ("STEP7", "验证评估", "对比 growth_loss / rule_loss / total_loss", "训练调度器", "objective 三分量"),
        ("STEP7", "验证评估", "导出模型包：策略权重 + PCA 状态 + manifest", "训练调度器", "export_prcp_mm_deploy"),
    ],
}

# ============================================================
# 图 6：citideepalm 策略模型推理流程（PRCP DNN 反算的落地路径）
# ============================================================
FLOW6 = {
    "title": "citideepalm策略模型推理流程",
    "rows": [
        # ── 阶段1 加载模型 ──
        ("STEP1", "加载模型", "读取策略权重 mm_policy_weights.pt", "推理引擎", "export_prcp_mm_deploy"),
        ("STEP1", "加载模型", "读取收益率 PCA 状态 mm_yield_pca.pt", "推理引擎", "policy_pca_version 校验"),
        ("STEP1", "加载模型", "校验 manifest：维度/摘要哈希/决策档布局", "推理引擎", "policy_schema_hash"),
        ("STEP1", "加载模型", "固定推理系数 τ=0.0925、γ=5.25", "推理引擎", "★推理不再采样"),

        # ── 阶段2 情景输入 ──
        ("STEP2", "情景输入", "加载 ESG 情景包：市场收益率路径", "ESG 场景工厂", "HJM 5 因子"),
        ("STEP2", "情景输入", "取策略输入 PCA 3 因子（180 月）", "ESG 场景工厂", "policy_pca_3f"),
        ("STEP2", "情景输入", "加载 T0 账户工作簿与训练账户配置", "账户引擎", "training_accounts.json"),

        # ── 阶段3 账本推演 ──
        ("STEP3", "账户账本推演", "run_account_rollout 逐月推进（推理模式）", "账户引擎", "★train=False 不建梯度图"),
        ("STEP3", "账户账本推演", "策略网络推理决策：65 期限档配置", "策略网络", "provider(tau, gamma 固定)"),
        ("STEP3", "账户账本推演", "按决策重配资产，生成现金流与余额", "账户引擎", "决策档受 T0 权重约束"),
        ("STEP3", "账户账本推演", "记录每月后置状态供指标计算", "账户引擎", "post 状态"),

        # ── 阶段4 指标计算 ──
        ("STEP4", "指标计算", "LCR：HQLA ÷ 净流出（流入 75% 封顶）", "指标计算模块", "calculate_lcr_nsfr_indicators"),
        ("STEP4", "指标计算", "NSFR：ASF ÷ RSF × 调整系数", "指标计算模块", "engine_params_real.json"),
        ("STEP4", "指标计算", "EVE：六情景 ΔEVE 绝对值比率", "指标计算模块", "delta_eve_from_cashflows"),
        ("STEP4", "指标计算", "CAR：CET1 资本 ÷ 风险加权资产", "指标计算模块", "★四项规则指标"),

        # ── 阶段5 指标评分 ──
        ("STEP5", "指标评分", "四项指标映射为 0~500 分（分段插值）", "指标评分模块", "map_indicator_tensors"),
        ("STEP5", "指标评分", "等权加权得综合分：各 0.25", "指标评分模块", "weighted_score_tensor"),
        ("STEP5", "指标评分", "计算距离 500 分的二次惩罚", "指标评分模块", "score_penalty_tensor"),

        # ── 阶段6 结果输出 ──
        ("STEP6", "结果输出", "输出各情景期末权益与 ROE", "推理引擎", "final_equity / roe_after_dividend"),
        ("STEP6", "结果输出", "导出月度台账明细供核对", "推理引擎", "monthly_ledger_export"),
        ("STEP6", "结果输出", "★回传 PRCP：预测业务量 → 指标计量", "PRCP 平台", "prcp_model_train_result"),
        ("STEP6", "结果输出", "★PRCP 指标评分再算分 → 目标达成校验", "PRCP 平台", "prcp_kpi_value.score"),
    ],
}

FLOWS = [FLOW1, FLOW2, FLOW3, FLOW4, FLOW5, FLOW6]

TITLE_FONT = Font(name="微软雅黑", size=12, bold=True, color="1F4E79")
HEAD_FILL = PatternFill("solid", fgColor="1F4E79")
HEAD_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="微软雅黑", size=10)
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
HEADERS = ["阶段", "具体事项", "操作", "责任人", "备注"]

wb = Workbook()
wb.remove(wb.active)

for flow in FLOWS:
    ws = wb.create_sheet(flow["title"][:28])
    # 标题行（整行仅一个非空单元格 + 含「流程/链路」→ 被识别为 Page 名）
    ws.cell(row=1, column=1, value=flow["title"]).font = TITLE_FONT
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    ws.row_dimensions[1].height = 24
    # 表头行
    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=2, column=c, value=h)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
    # 数据行
    for r, row in enumerate(flow["rows"], 3):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BODY_FONT
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = BORDER
    for col, w in {"A": 10, "B": 18, "C": 50, "D": 16, "E": 30}.items():
        ws.column_dimensions[col].width = w

wb.save(OUT)
print("OK ->", OUT)
for f in FLOWS:
    print(f"  {f['title']}: {len(f['rows'])} 项 / {len({r[0] for r in f['rows']})} 阶段")

# ============================================================
# 同时输出 4 个独立的单页 xlsx
#   原因：ProcessOn 导入多页 .vsdx 时，可能只保留第一页。
#   单页文件逐个上传无此风险。
# ============================================================
SINGLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "single")
os.makedirs(SINGLE_DIR, exist_ok=True)
print()
print("单页流程表:")
for flow in FLOWS:
    wb1 = Workbook()
    ws = wb1.active
    ws.title = flow["title"][:28]
    ws.cell(row=1, column=1, value=flow["title"]).font = TITLE_FONT
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    ws.row_dimensions[1].height = 24
    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=2, column=c, value=h)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
    for r, row in enumerate(flow["rows"], 3):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BODY_FONT
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = BORDER
    for col, w in {"A": 10, "B": 18, "C": 50, "D": 16, "E": 30}.items():
        ws.column_dimensions[col].width = w
    p = os.path.join(SINGLE_DIR, f"{flow['title']}.xlsx")
    wb1.save(p)
    print(f"  {p}")

