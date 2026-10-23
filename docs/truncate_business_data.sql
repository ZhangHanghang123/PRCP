-- PRCP 模块业务数据清空脚本（2026-09-29）
-- 清空账户册 / 指标 / 模型 / 资产负债表 / 基础数据表 / 反算指标结果表 / 组合反算 / 反算结果查询 / 新业务模拟方案 / 新业务模拟结果

-- 关闭外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 需要清空的 27 张业务表
TRUNCATE TABLE prcp_sim_term_ratio;
TRUNCATE TABLE prcp_sim_node_config;
TRUNCATE TABLE prcp_sim_result;
TRUNCATE TABLE prcp_sim_run;
TRUNCATE TABLE prcp_sim_scheme;

TRUNCATE TABLE prcp_reverse_run_log;
TRUNCATE TABLE prcp_reverse_result;
TRUNCATE TABLE prcp_reverse_target;
TRUNCATE TABLE prcp_reverse_run;
TRUNCATE TABLE prcp_reverse_scheme;

TRUNCATE TABLE prcp_data_reverse;
TRUNCATE TABLE prcp_data_maint_value;
TRUNCATE TABLE prcp_data_balance;
TRUNCATE TABLE prcp_data_basic;

TRUNCATE TABLE prcp_model_train_log;
TRUNCATE TABLE prcp_model_train_result;
TRUNCATE TABLE prcp_model_train;
TRUNCATE TABLE prcp_model_param;
TRUNCATE TABLE prcp_model_version;
TRUNCATE TABLE prcp_model;

TRUNCATE TABLE prcp_kpi_calc_rule;
TRUNCATE TABLE prcp_kpi_score_segment;
TRUNCATE TABLE prcp_kpi_score_rule;
TRUNCATE TABLE prcp_kpi_value;
TRUNCATE TABLE prcp_kpi_scheme;
TRUNCATE TABLE prcp_kpi_definition;

TRUNCATE TABLE prcp_coa_node;
TRUNCATE TABLE prcp_coa_scheme;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;