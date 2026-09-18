-- ============================================================
-- PRCP 通用字典表 sys_dict + 种子数据
-- 日期：2026-09-18  作者：PRCP WorkBuddy Agent
-- ============================================================

-- 1. 字典主表
DROP TABLE IF EXISTS sys_dict;
CREATE TABLE sys_dict (
  id          BIGINT PRIMARY KEY AUTO_INCREMENT,
  dict_type   VARCHAR(48)  NOT NULL  COMMENT '字典类别（PRCP_ALGO / PRCP_STATUS ...）',
  dict_key    VARCHAR(48)  NOT NULL  COMMENT '字典值（代码）',
  dict_label  VARCHAR(128) NOT NULL  COMMENT '字典显示标签（中文）',
  color       VARCHAR(32)  DEFAULT NULL COMMENT 'AntD Tag/Select 颜色',
  sort_order  INT          NOT NULL DEFAULT 0  COMMENT '显示顺序',
  status      VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE / DEPRECATED',
  description VARCHAR(255) DEFAULT NULL,
  extra_json  JSON         DEFAULT NULL COMMENT '扩展属性（icon/scope/handler 等）',
  created_by  BIGINT       DEFAULT NULL,
  updated_by  BIGINT       DEFAULT NULL,
  created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_deleted  TINYINT(1)   NOT NULL DEFAULT 0,
  UNIQUE KEY uk_dict_type_key (dict_type, dict_key, is_deleted),
  KEY        idx_dict_type (dict_type, status, is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='PRCP 通用字典表';

-- 2. 种子数据（按 dict_type 分组）
INSERT IGNORE INTO sys_dict (dict_type, dict_key, dict_label, color, sort_order, description) VALUES
-- ---------- PRCP_ALGO：模型算法 ----------
('PRCP_ALGO', 'LINEAR_REGRESSION', '线性回归', 'blue', 10, '普通最小二乘法'),
('PRCP_ALGO', 'LOGISTIC_GROWTH', '逻辑斯蒂增长', 'purple', 20, 'S 形曲线'),
('PRCP_ALGO', 'MONTE_CARLO', '蒙特卡洛模拟', 'cyan', 30, '随机抽样'),
('PRCP_ALGO', 'LINEAR_PROGRAM', '线性规划', 'gold', 40, 'CVXPY 求解'),
('PRCP_ALGO', 'ARIMA', 'ARIMA 时间序列', 'magenta', 50, '自回归滑动平均'),
('PRCP_ALGO', 'ANT_COLONY', '蚁群算法', 'volcano', 60, 'ACO 优化'),
('PRCP_ALGO', 'FNN_LLM', 'FNN 大模型', 'geekblue', 70, '神经网络 + 大模型'),

-- ---------- PRCP_BIZ_DOMAIN：模型业务域 ----------
('PRCP_BIZ_DOMAIN', 'DEPOSIT', '存款', 'blue', 10, '存款业务'),
('PRCP_BIZ_DOMAIN', 'LOAN', '贷款', 'orange', 20, '贷款业务'),
('PRCP_BIZ_DOMAIN', 'NIM', '净息差', 'green', 30, '净息差相关'),
('PRCP_BIZ_DOMAIN', 'RWA', '资本', 'red', 40, '风险加权资产'),
('PRCP_BIZ_DOMAIN', 'OPERATIONAL', '运营', 'purple', 50, '运营相关'),

-- ---------- PRCP_STATUS：通用状态（模型/方案/参数共用） ----------
('PRCP_STATUS', 'DRAFT', '草稿', 'default', 10, '初始状态'),
('PRCP_STATUS', 'READY', '就绪', 'cyan', 20, '待运行'),
('PRCP_STATUS', 'ACTIVE', '启用', 'green', 30, '正在使用'),
('PRCP_STATUS', 'DEPRECATED', '停用', 'red', 40, '已废弃'),
('PRCP_STATUS', 'ARCHIVE', '归档', 'default', 50, '已归档'),

-- ---------- PRCP_PARAM_TYPE：参数类型 ----------
('PRCP_PARAM_TYPE', 'BASE', '基准', 'blue', 10, '基准情景'),
('PRCP_PARAM_TYPE', 'SCENARIO', '情景', 'purple', 20, '情景分析'),
('PRCP_PARAM_TYPE', 'STRESS', '压力', 'red', 30, '压力测试'),
('PRCP_PARAM_TYPE', 'SENSITIVITY', '敏感度', 'cyan', 40, '敏感度分析'),

-- ---------- PRCP_PARAM_CATEGORY：参数分类 ----------
('PRCP_PARAM_CATEGORY', 'DATA_DATE', '数据日期', 'geekblue', 10, '当前数据日期'),
('PRCP_PARAM_CATEGORY', 'DATA_ESG', '数据/ESG', 'blue', 20, '收益率曲线模拟'),
('PRCP_PARAM_CATEGORY', 'NEURAL_NETWORK', '神经网络', 'purple', 30, '神经网络参数'),
('PRCP_PARAM_CATEGORY', 'LOSS_FUNCTION', '损失函数', 'red', 40, '损失函数参数'),
('PRCP_PARAM_CATEGORY', 'TRAINING', '训练', 'cyan', 50, '训练参数'),
('PRCP_PARAM_CATEGORY', 'OPTIMIZER', '优化器', 'gold', 60, '模型优化参数'),
('PRCP_PARAM_CATEGORY', 'KPI_DRIVEN', 'KPI 驱动', 'geekblue', 70, 'KPI 衍生参数'),

-- ---------- PRCP_CALC_UNIT：KPI 单位 ----------
('PRCP_CALC_UNIT', 'PERCENT', '百分比 %', 'blue', 10, '百分比'),
('PRCP_CALC_UNIT', 'BP', '基点 BP', 'cyan', 20, '基点'),
('PRCP_CALC_UNIT', 'RATIO', '比率', 'green', 30, '比率'),
('PRCP_CALC_UNIT', 'AMOUNT', '金额', 'gold', 40, '金额'),

-- ---------- PRCP_INDICATOR_TYPE：指标类型 ----------
('PRCP_INDICATOR_TYPE', '1', '公式指标', 'blue', 10, '按报表表项公式计算'),
('PRCP_INDICATOR_TYPE', '2', '函数指标', 'purple', 20, '执行外部脚本'),

-- ---------- PRCP_REVERSE_ALGO：反算算法 ----------
('PRCP_REVERSE_ALGO', 'CVXPY_QP', '二次规划（推荐）', 'blue', 10, 'CVXPY QP 求解'),
('PRCP_REVERSE_ALGO', 'CVXPY_LP', '线性规划', 'cyan', 20, 'CVXPY LP 求解'),
('PRCP_REVERSE_ALGO', 'HEURISTIC', '启发式', 'gold', 30, '启发式搜索'),

-- ---------- PRCP_SCHEME_TYPE：反算方案类型 ----------
('PRCP_SCHEME_TYPE', 'OPTIMIZE', 'OPTIMIZE（最优求解）', 'blue', 10, '目标最优化'),
('PRCP_SCHEME_TYPE', 'SCENARIO', 'SCENARIO（情景模拟）', 'purple', 20, '情景模拟'),
('PRCP_SCHEME_TYPE', 'REBALANCE', 'REBALANCE（再平衡）', 'green', 30, '资产再平衡'),

-- ---------- PRCP_RUN_STATUS：反算运行状态 ----------
('PRCP_RUN_STATUS', 'PENDING', '等待中', 'default', 10, '已创建待启动'),
('PRCP_RUN_STATUS', 'RUNNING', '运行中', 'processing', 20, '正在执行'),
('PRCP_RUN_STATUS', 'SUCCESS', '成功', 'green', 30, '执行成功'),
('PRCP_RUN_STATUS', 'FAILED', '失败', 'red', 40, '执行失败'),
('PRCP_RUN_STATUS', 'CANCELLED', '已取消', 'orange', 50, '用户取消'),

-- ---------- PRCP_CURVE_TYPE：收益率曲线类型 ----------
('PRCP_CURVE_TYPE', 'SOVEREIGN', '国债', 'red', 10, '主权债收益率'),
('PRCP_CURVE_TYPE', 'POLICY', '政金', 'orange', 20, '政策性金融债'),
('PRCP_CURVE_TYPE', 'CD', '同业存单', 'blue', 30, '同业存单'),
('PRCP_CURVE_TYPE', 'LPR', 'LPR', 'purple', 40, '贷款基准利率'),
('PRCP_CURVE_TYPE', 'FTP', 'FTP', 'green', 50, '内部资金转移定价'),
('PRCP_CURVE_TYPE', 'CUSTOM', '自定义', 'cyan', 60, '自定义曲线'),

-- ---------- PRCP_NODE_LEVEL：COA 节点层级 ----------
('PRCP_NODE_LEVEL', '1', '大类', 'blue', 10, '一级分类'),
('PRCP_NODE_LEVEL', '2', '分组', 'purple', 20, '二级分组'),
('PRCP_NODE_LEVEL', '3', '明细', 'cyan', 30, '三级明细'),
('PRCP_NODE_LEVEL', '4', '子项', 'geekblue', 40, '四级子项'),
('PRCP_NODE_LEVEL', '5', '叶节点', 'green', 50, '五级叶子'),

-- ---------- PRCP_COA_CATEGORY：COA 资产负债分类 ----------
('PRCP_COA_CATEGORY', '资产', '资产', 'blue', 10, 'Asset'),
('PRCP_COA_CATEGORY', '负债', '负债', 'orange', 20, 'Liability'),
('PRCP_COA_CATEGORY', '权益', '权益', 'gold', 30, 'Equity'),
('PRCP_COA_CATEGORY', '表外', '表外', 'purple', 40, 'Off-balance'),

-- ---------- PRCP_UNIT：度量单位 ----------
('PRCP_UNIT', '%', '%', 'blue', 10, '百分比'),
('PRCP_UNIT', 'BP', 'BP', 'cyan', 20, '基点'),
('PRCP_UNIT', 'YUAN', '元', 'gold', 30, '人民币元'),
('PRCP_UNIT', 'YI', '亿元', 'green', 40, '亿元');

-- 3. 验证
SELECT dict_type, COUNT(*) cnt FROM sys_dict WHERE is_deleted=0 GROUP BY dict_type ORDER BY dict_type;
