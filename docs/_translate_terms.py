"""PRCP 字段中文名翻译字典

按业务领域分组，覆盖 PRCP 全部 46 张表的 1108 个字段名。
- 优先用 COMMENT（数据库实际注释）
- COMMENT 为空时按本字典推断中文名
- 字典无匹配时返回原文
"""

# 完整字段 → 中文名 映射（含 PRCP 业务术语）
COLUMN_TRANSLATE = {
    # ---------- 通用审计字段 ----------
    "id": "主键ID",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "created_by": "创建人",
    "updated_by": "更新人",
    "is_deleted": "是否删除（软删除）",
    "remark": "备注",
    "description": "描述",
    "sort_order": "排序",
    "status": "状态",
    "version": "版本号",
    "color": "颜色（前端标签）",
    "extra_json": "扩展属性JSON",

    # ---------- 账户册 ----------
    "scheme_code": "方案编码",
    "scheme_name": "方案名称",
    "scheme_type": "方案类型",
    "scheme_id": "方案ID",
    "scheme_count": "方案数量",
    "coa_scheme_id": "账户册方案ID",
    "coa_node_id": "账户册节点ID",
    "coa_node_code": "账户册节点编码",
    "node_code": "节点编码",
    "node_name": "节点名称",
    "node_level": "节点层级",
    "node_type": "节点类型",
    "parent_id": "父节点ID",
    "parent_code": "父节点编码",
    "path": "节点路径",
    "is_leaf": "是否叶子节点",
    "category": "资产负债分类",
    "node_count": "节点数量",
    "description": "描述",
    "start_date": "起始日期",
    "end_date": "结束日期",

    # ---------- 基础数据 / 期限桶 ----------
    "data_date": "数据日期",
    "date_offset": "日期偏移量",
    "offset_unit": "偏移单位（D日/M月）",
    "asf_rsf": "ASF/RSF（可用/所需稳定资金）",
    "hqla_factor": "HQLA 优质流动性资产因子",
    "current_balance": "当前余额",
    "current_amount": "当前金额",
    "begin_balance": "月初余额",
    "avg_balance": "平均余额",
    "weighted_rate": "加权平均利率",
    "interest_rate": "利率",
    "interest_amount": "利息金额",
    "risk_weight": "风险权重",
    "capital_ratio": "资本占用比例",
    "calc_note": "计算备注",
    "current_value": "当前值",
    "prev_value": "上期值",
    "prev_year_value": "去年同期值",
    "input_value": "手动输入值",
    "source": "数据来源",

    # ---------- 报表 ----------
    "report_code": "报表编码",
    "report_name": "报表名称",
    "report_type": "报表类型",
    "rpt_id": "报表ID",
    "rpt_item_id": "报表表项ID",
    "rpt_item_code": "报表表项编码",
    "item_code": "表项编码",
    "item_name": "表项名称",
    "item_id": "表项ID",
    "item_level": "表项层级",
    "data_type": "数据类型",
    "formula": "计算公式",
    "formula_desc": "公式说明",
    "coa_node_ids": "关联账户册节点IDs",
    "item_count": "表项数量",
    "value": "数值",

    # ---------- 指标 ----------
    "kpi_id": "指标ID",
    "kpi_code": "指标编码",
    "kpi_name": "指标名称",
    "kpi_count": "指标数量",
    "kpi_scheme_id": "指标方案ID",
    "indicator_type": "指标类型（1=公式/2=函数）",
    "script_path": "函数脚本路径",
    "script_name": "脚本入口函数名",
    "calc_unit": "计算单位",
    "calc_method": "计算方法",
    "calc_source": "计算来源",
    "calc_log": "计算日志",
    "threshold_min": "阈值下限",
    "threshold_max": "阈值上限",
    "threshold_low": "阈值下限",
    "threshold_high": "阈值上限",
    "score": "评分",
    "rule_name": "规则名称",
    "total_score": "总分",
    "higher_is_better": "是否越高越好",
    "seg_order": "分段顺序",
    "min_value": "最小值",
    "max_value": "最大值",
    "segment_desc": "分段描述",
    "numerator_json": "分子节点列表JSON",
    "denominator_json": "分母节点列表JSON",
    "target_value": "目标值",
    "constraint_type": "约束类型",
    "weight": "权重",

    # ---------- 利率曲线 ----------
    "curve_code": "曲线编码",
    "curve_name": "曲线名称",
    "curve_type": "曲线类型",
    "curve_id": "曲线ID",
    "ccy": "币种",
    "data_source": "数据源",
    "source_date": "数据发布日期",
    "rate_d1": "1日利率（%）",
    "rate_d7": "7日利率（%）",
    "rate_m1": "1月期利率（%）",
    "rate_m3": "3月期利率（%）",
    "rate_m6": "6月期利率（%）",
    "rate_y1": "1年期利率（%）",
    "rate_y2": "2年期利率（%）",
    "rate_y3": "3年期利率（%）",
    "rate_y5": "5年期利率（%）",
    "rate_y10": "10年期利率（%）",
    "rate_y15": "15年期利率（%）",
    "rate_y20": "20年期利率（%）",
    "rate_y30": "30年期利率（%）",
    "curve_shift_bps": "曲线平移（BP）",
    "curve_slope": "曲线斜率（10Y-1Y）",

    # ---------- ESG 场景工厂 ----------
    "n_factors": "PCA 因子数",
    "n_scenarios": "情景数",
    "n_steps": "时间步数（月）",
    "n_maturities": "期限数",
    "seed": "随机种子",
    "maturities_json": "期限列表JSON",
    "initial_yields_json": "初始收益率JSON",
    "theta0": "Svensson β0（水平因子）",
    "theta1": "Svensson β1（斜率因子）",
    "theta2": "Svensson β2（曲率因子）",
    "theta3": "Svensson β3（第二曲率因子）",
    "lambda1": "Svensson λ1（衰减率1）",
    "lambda2": "Svensson λ2（衰减率2）",
    "raw_data_json": "原始数据JSON",
    "run_type": "运行类型（PCA/HJM/Scenario）",
    "params_json": "运行参数JSON",
    "output_json": "运行输出JSON",
    "file_path": "文件路径",
    "file_size_bytes": "文件大小（字节）",
    "duration_ms": "耗时（毫秒）",
    "duration_sec": "耗时（秒）",
    "error_message": "错误信息",
    "paths_blob": "路径二进制（npz 字节流）",
    "p10_json": "P10 分位带JSON",
    "p50_json": "P50 分位带（中位数）JSON",
    "p90_json": "P90 分位带JSON",
    "final_mean_json": "终期利率均值JSON",
    "final_std_json": "终期利率标准差JSON",
    "final_min_json": "终期利率最小值JSON",
    "final_max_json": "终期利率最大值JSON",
    "vol_per_maturity_json": "各期限波动率JSON",
    "n_zeros": "零值样本数",
    "n_negatives": "负值样本数",
    "scenario_type": "情景类型",
    "scenario_code": "情景编码",
    "last_run_id": "最近运行ID",

    # ---------- 模型 ----------
    "model_id": "模型ID",
    "model_code": "模型编码",
    "model_name": "模型名称",
    "model_type": "模型类型",
    "algo_config": "算法配置JSON",
    "biz_domain": "业务域",
    "version_code": "版本编码",
    "version_name": "版本名称",
    "version_id": "版本ID",
    "parent_version_id": "父版本ID",
    "param_count": "参数数量",
    "param_id": "参数ID",
    "param_code": "参数编码",
    "param_name": "参数名称",
    "param_type": "参数类型（BASE/SCENARIO/STRESS）",
    "param_category": "参数分类（DATA_ESG/NEURAL_NETWORK/...）",
    "param_value": "参数数值",
    "param_value_str": "参数字符串值",
    "unit": "单位",
    "train_id": "训练任务ID",
    "train_code": "训练任务编码",
    "balance_date_from": "数据日期起点",
    "balance_date_to": "数据日期终点",
    "progress": "进度（0-100）",
    "start_at": "开始时间",
    "end_at": "结束时间",
    "started_at": "开始时间",
    "finished_at": "结束时间",
    "metrics": "评估指标JSON",
    "log_level": "日志级别",
    "log_message": "日志消息",
    "predict_period": "预测周期",
    "predicted_value": "预测值",
    "actual_value": "实际值",
    "confidence_low": "置信下限",
    "confidence_high": "置信上限",

    # ---------- 反算 ----------
    "run_id": "运行ID",
    "run_code": "运行编码",
    "scheme_id": "方案ID",
    "horizon_months": "预测期数（月）",
    "horizon_month": "生效月份",
    "algorithm": "求解算法",
    "optimal_value": "最优解目标值",
    "predict_month": "预测月份序号",
    "predict_date": "预测日期",
    "adjusted_value": "调整后值",
    "delta_value": "调整量",
    "record_id": "业务ID",
    "target_name": "目标名称",

    # ---------- 指标计量系数 ----------
    "metric_type": "指标类型（ROE/CET1/LCR/...）",
    "metric_code": "指标编码",
    "y1_value": "未来1年值",
    "y2_value": "未来2年值",
    "y3_value": "未来3年值",
    "y4_value": "未来4年值",
    "y5_value": "未来5年值",

    # ---------- 新业务模拟 ----------
    "sim_scheme_id": "模拟方案ID",
    "sim_scheme_code": "模拟方案编码",
    "sim_scheme_name": "模拟方案名称",
    "config_node_count": "已配置节点数",
    "annual_growth_rate": "年化目标增长率（%）",
    "term_unit": "期限单位",
    "term_count": "期限条数",
    "config_id": "节点配置ID",
    "term_value": "期限值（1~60月）",
    "business_ratio": "业务占比（%）",
    "base_data_date": "基准数据日期",
    "month_count": "生成月份数",
    "target_data_date": "目标数据日期",
    "total_nodes": "总节点数",
    "processed_nodes": "已处理节点数",
    "is_configured": "是否已配置（1=新业务模拟/0=纯滚动）",
    "is_aggregated": "是否汇总节点",

    # ---------- 系统管理 ----------
    "username": "用户名",
    "password_hash": "密码哈希",
    "display_name": "显示名称",
    "role": "角色",
    "role_code": "角色编码",
    "role_name": "角色名称",
    "user_id": "用户ID",
    "dict_type": "字典类型",
    "dict_key": "字典键",
    "dict_label": "字典标签",
    "dict_id": "字典ID",
    "dict_code": "字典编码",
    "dict_name": "字典名称",
    "item_value": "字典项值",
    "login_at": "登录时间",
    "logout_at": "登出时间",
    "ip": "IP地址",
    "user_agent": "用户代理",
    "op_type": "操作类型",
    "op_time": "操作时间",
}


def translate_column(name, comment=""):
    """翻译字段名为中文。

    优先级（确保"中文名"列格式统一、易读）：
    1. 字典直接命中 → 使用字典翻译
    2. 字典未命中但 COMMENT 是中文 → 使用 COMMENT
    3. 字典未命中且 COMMENT 是英文/空 → 使用 COMMENT 或字段名原文

    Args:
        name: 字段名（snake_case）
        comment: 数据库 COMMENT

    返回:
        中文名字符串（统一格式，优先字典）
    """
    # 字典直接命中（最一致的中文命名）
    if name in COLUMN_TRANSLATE:
        return COLUMN_TRANSLATE[name]

    # 特殊模式：orig_m1 ~ orig_m60, rem_m1 ~ rem_m60
    if name.startswith("orig_"):
        suffix = name[5:]
        if suffix.startswith("m") and suffix[1:].isdigit():
            return f"原始期限{suffix[1:]}月金额"
        if suffix.startswith("y") and suffix[1:].isdigit():
            return f"原始期限{suffix[1:]}年金额"
        return f"原始{suffix}"

    if name.startswith("rem_"):
        suffix = name[4:]
        if suffix.startswith("m") and suffix[1:].isdigit():
            return f"剩余期限{suffix[1:]}月金额"
        if suffix.startswith("y") and suffix[1:].isdigit():
            return f"剩余期限{suffix[1:]}年金额"
        return f"剩余{suffix}"

    # 字典未命中：判断 COMMENT 是否为中文（避免把英文注释当翻译）
    if comment and comment.strip() and contains_chinese(comment):
        return comment.strip()

    # 兜底返回字段名
    return name


def contains_chinese(text):
    """判断字符串是否包含中文字符"""
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


def translate_table(name, comment=""):
    """翻译表名为中文。

    优先级：
    1. 数据库 COMMENT（最权威）
    2. 兜底按命名推断
    """
    if comment and comment.strip():
        return comment.strip()

    # prcp_ 前缀的表
    if name.startswith("prcp_"):
        suffix = name[5:]
        # 已知简写
        mapping = {
            "coa": "账户册",
            "rpt": "报表",
            "kpi": "指标",
            "data": "数据",
            "model": "模型",
            "reverse": "反算",
            "sim": "模拟",
            "rate": "利率",
            "esg": "ESG场景",
            "metric": "指标计量",
        }
        for k, v in mapping.items():
            if suffix.startswith(k):
                rest = suffix[len(k):].lstrip("_")
                if rest:
                    return f"{v}-{rest.replace('_', '-')}"
                return v

    if name.startswith("sys_"):
        suffix = name[4:]
        mapping = {
            "user": "用户",
            "role": "角色",
            "dict": "字典",
            "login_log": "登录日志",
            "op_log": "操作日志",
        }
        if suffix in mapping:
            return mapping[suffix]
        return suffix

    return name