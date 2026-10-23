-- ============================================================
-- 02_seed_models.sql - 模型管理
-- NLS_REG (非线性求解) + ACO_OPT (蚁群优化) + DNN_REG (深度神经网络)
-- 每个模型 1 个 V1_BASELINE 版本 + 12-13 个参数
-- ============================================================

SET NAMES utf8mb4;

-- 1. 插入 3 个模型
INSERT IGNORE INTO prcp_model
    (model_code, model_name, model_type, biz_domain, kpi_scheme_id, description, algo_config, status, created_by, updated_by)
VALUES
    ('DNN_REG',
     'DNN 神经网络回归模型',
     'DNN_NEURAL_NETWORK',
     '监管资本',
     (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     '基于深度神经网络（DNN/MLP）的非线性回归模型，用于监管资本指标的预测与情景生成',
     JSON_OBJECT('input_dim', 64, 'output_dim', 5, 'framework', 'PyTorch', 'task', 'REGRESSION'),
     'ACTIVE', 1, 1),
    ('ACO_OPT',
     '蚁群算法组合优化模型',
     'ANT_COLONY',
     '资产负债',
     (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     '基于蚁群（ACO）的组合优化模型，用于资产负债结构/资产配置/路径规划',
     JSON_OBJECT('objective', 'MAX_RETURN', 'constraints', JSON_ARRAY('RISK_LIMIT', 'LIQUIDITY_FLOOR')),
     'ACTIVE', 1, 1),
    ('NLS_REG',
     '非线性方程求解模型',
     'NONLINEAR_SOLVER',
     '定价估值',
     (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     '基于 scipy.optimize 的非线性求解器，用于隐含波动率/IRRBB/EVE 等非线性方程求解',
     JSON_OBJECT('solver', 'trust-constr', 'method', 'SLSQP', 'task', 'ROOT_FINDING'),
     'ACTIVE', 1, 1);

-- 2. 为每个模型创建 V1_BASELINE 版本 (幂等)
INSERT IGNORE INTO prcp_model_version
    (model_id, version_code, version_name, description, status, created_by, updated_by)
SELECT m.id, 'V1_BASELINE', '基准情景', '自动创建的初始版本', 'DRAFT', 1, 1
FROM prcp_model m
WHERE m.model_code IN ('DNN_REG', 'ACO_OPT', 'NLS_REG') AND m.is_deleted = 0
  AND NOT EXISTS (
      SELECT 1 FROM prcp_model_version v
      WHERE v.model_id = m.id AND v.version_code = 'V1_BASELINE' AND v.is_deleted = 0
  );

-- 3. 软删旧参数 (幂等)
UPDATE prcp_model_param
SET is_deleted = 1
WHERE version_id IN (
    SELECT v.id FROM prcp_model_version v
    JOIN prcp_model m ON v.model_id = m.id
    WHERE m.model_code IN ('DNN_REG', 'ACO_OPT', 'NLS_REG')
      AND v.version_code = 'V1_BASELINE' AND v.is_deleted = 0
) AND is_deleted = 0;

-- 4. DNN_REG 参数 (13 个)
INSERT INTO prcp_model_param
    (version_id, kpi_id, kpi_code, param_code, param_name, param_type, param_category,
     param_value, param_value_str, unit, sort_order, description, created_by, updated_by)
SELECT
    v.id,
    k.id, k.kpi_code,
    t.param_code, t.param_name, 'BASE', t.param_category,
    CASE WHEN t.is_str THEN 0 ELSE t.param_value END,
    CASE WHEN t.is_str THEN t.param_value_str ELSE NULL END,
    t.unit, t.sort_order,
    'DNN 神经网络回归模型 V1 默认参数', 1, 1
FROM prcp_model_version v
JOIN prcp_model m ON v.model_id = m.id
JOIN prcp_kpi_definition k ON k.scheme_id = (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1) AND k.kpi_code='REG_LCR' AND k.is_deleted=0
CROSS JOIN (
    SELECT 'NN_ENCODER_LAYERS' AS param_code, '隐藏编码层维度' AS param_name, 128 AS param_value, '维' AS unit, 1 AS sort_order, 'NEURAL_NETWORK' AS param_category, 0 AS is_str, NULL AS param_value_str UNION ALL
    SELECT 'NN_LATENT_DIM',     '编码维度',          32,  '维', 2, 'NEURAL_NETWORK', 0, NULL UNION ALL
    SELECT 'NN_HIDDEN_DIMS',    '隐藏层维度序列',    0,   NULL, 3, 'NEURAL_NETWORK', 1, '[256,128,64]' UNION ALL
    SELECT 'NN_ACTIVATION',     '激活函数',          0,   NULL, 4, 'NEURAL_NETWORK', 1, 'RELU' UNION ALL
    SELECT 'OPTIM_TYPE',       '优化器',            0,   NULL, 5, 'OPTIMIZER', 1, 'ADAM' UNION ALL
    SELECT 'OPTIM_LEARNING_RATE','学习率',           0,   NULL, 6, 'OPTIMIZER', 1, '0.001' UNION ALL
    SELECT 'OPTIM_GRAD_CLIP',  '梯度裁剪值',        0.5, NULL, 7, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'TRAIN_EPOCH',      '训练轮次',          100, '轮', 8, 'TRAINING', 0, NULL UNION ALL
    SELECT 'TRAIN_BATCH_SIZE', '批大小',            64,  NULL, 9, 'TRAINING', 0, NULL UNION ALL
    SELECT 'LOSS_MU',          '目标参数 μ',        0,   NULL, 10, 'LOSS_FUNCTION', 1, '[0.04, 0.07]' UNION ALL
    SELECT 'LOSS_SIGMA',       '惩罚系数 σ',        0,   NULL, 11, 'LOSS_FUNCTION', 1, '[1.0,0.2,1.0,2.5,2.0]' UNION ALL
    SELECT 'LOSS_LAMBDA',      '惩罚权重 λ',        0,   NULL, 12, 'LOSS_FUNCTION', 1, '[0.05, 25.0]' UNION ALL
    SELECT 'DATA_DATE_CURRENT','当前数据日期',      0,   NULL, 13, 'DATA_DATE', 1, '2025-12-31'
) t
WHERE m.model_code = 'DNN_REG' AND m.is_deleted = 0
  AND v.version_code = 'V1_BASELINE' AND v.is_deleted = 0;

-- 5. ACO_OPT 参数 (12 个)
INSERT INTO prcp_model_param
    (version_id, kpi_id, kpi_code, param_code, param_name, param_type, param_category,
     param_value, param_value_str, unit, sort_order, description, created_by, updated_by)
SELECT
    v.id,
    k.id, k.kpi_code,
    t.param_code, t.param_name, 'BASE', t.param_category,
    CASE WHEN t.is_str THEN 0 ELSE t.param_value END,
    CASE WHEN t.is_str THEN t.param_value_str ELSE NULL END,
    t.unit, t.sort_order,
    'ACO 蚁群优化模型 V1 默认参数', 1, 1
FROM prcp_model_version v
JOIN prcp_model m ON v.model_id = m.id
JOIN prcp_kpi_definition k ON k.scheme_id = (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1) AND k.kpi_code='REG_NSFR' AND k.is_deleted=0
CROSS JOIN (
    SELECT 'ACO_ANT_COUNT' AS param_code, '蚂蚁数量' AS param_name, 50 AS param_value, '只' AS unit, 1 AS sort_order, 'OPTIMIZER' AS param_category, 0 AS is_str, NULL AS param_value_str UNION ALL
    SELECT 'ACO_MAX_ITER',   '最大迭代次数',       100,  '轮', 2, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'ACO_ALPHA',      '信息素权重 α',      1.0, NULL, 3, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'ACO_BETA',       '启发式权重 β',      2.0, NULL, 4, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'ACO_RHO',        '信息素挥发系数 ρ',  0.5, NULL, 5, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'ACO_Q0',         '信息素常量 Q',      100, NULL, 6, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'ACO_TAU_INIT',   '初始信息素浓度',    1.0, NULL, 7, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'ACO_EPSILON',    '精英蚂蚁权重 ε',    2.0, NULL, 8, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'ACO_SEED',       '随机种子',          42,  NULL, 9, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'OPTIM_TYPE',     '优化器',            0,   NULL, 10, 'OPTIMIZER', 1, 'ADAM' UNION ALL
    SELECT 'TRAIN_EPOCH',    '训练轮次',          100, '轮', 11, 'TRAINING', 0, NULL UNION ALL
    SELECT 'DATA_DATE_CURRENT','当前数据日期',     0,   NULL, 12, 'DATA_DATE', 1, '2025-12-31'
) t
WHERE m.model_code = 'ACO_OPT' AND m.is_deleted = 0
  AND v.version_code = 'V1_BASELINE' AND v.is_deleted = 0;

-- 6. NLS_REG 参数 (12 个)
INSERT INTO prcp_model_param
    (version_id, kpi_id, kpi_code, param_code, param_name, param_type, param_category,
     param_value, param_value_str, unit, sort_order, description, created_by, updated_by)
SELECT
    v.id,
    k.id, k.kpi_code,
    t.param_code, t.param_name, 'BASE', t.param_category,
    CASE WHEN t.is_str THEN 0 ELSE t.param_value END,
    CASE WHEN t.is_str THEN t.param_value_str ELSE NULL END,
    t.unit, t.sort_order,
    'NLS 非线性求解模型 V1 默认参数', 1, 1
FROM prcp_model_version v
JOIN prcp_model m ON v.model_id = m.id
JOIN prcp_kpi_definition k ON k.scheme_id = (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1) AND k.kpi_code='REG_EVE' AND k.is_deleted=0
CROSS JOIN (
    SELECT 'NLS_SOLVER' AS param_code, '求解器' AS param_name, 0 AS param_value, NULL AS unit, 1 AS sort_order, 'OPTIMIZER' AS param_category, 1 AS is_str, 'TRUST_REGION' AS param_value_str UNION ALL
    SELECT 'NLS_METHOD',   '数值方法',           0,  NULL, 2, 'OPTIMIZER', 1, 'NEWTON_CG' UNION ALL
    SELECT 'NLS_TOL_FUN',  '函数容差',           0,  NULL, 3, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'NLS_TOL_X',    '变量容差',           0,  NULL, 4, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'NLS_MAX_ITER', '最大迭代次数',       100,'轮', 5, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'NLS_JAC',      '雅可比近似',         0,  NULL, 6, 'OPTIMIZER', 1, '2-point' UNION ALL
    SELECT 'NLS_HESS',     'Hessian 近似',       0,  NULL, 7, 'OPTIMIZER', 1, 'BFGS' UNION ALL
    SELECT 'NLS_REG_ALPHA','正则化系数 α',      0.01,NULL, 8, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'NLS_BOUND_LOWER','下界',             -1000000, NULL, 9, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'NLS_BOUND_UPPER','上界',             1000000, NULL, 10, 'OPTIMIZER', 0, NULL UNION ALL
    SELECT 'TRAIN_EPOCH',  '训练轮次',           50, '轮', 11, 'TRAINING', 0, NULL UNION ALL
    SELECT 'DATA_DATE_CURRENT','当前数据日期',    0, NULL, 12, 'DATA_DATE', 1, '2025-12-31'
) t
WHERE m.model_code = 'NLS_REG' AND m.is_deleted = 0
  AND v.version_code = 'V1_BASELINE' AND v.is_deleted = 0;

-- 7. 更新版本 param_count
UPDATE prcp_model_version v
SET param_count = (
    SELECT COUNT(*) FROM prcp_model_param p
    WHERE p.version_id = v.id AND p.is_deleted = 0
)
WHERE v.id IN (
    SELECT v2.id FROM prcp_model_version v2
    JOIN prcp_model m ON v2.model_id = m.id
    WHERE m.model_code IN ('DNN_REG', 'ACO_OPT', 'NLS_REG') AND v2.is_deleted = 0
);

-- 验证
SELECT '====== 02_seed_models.sql 完成 ======' AS status;
SELECT
    m.model_code, m.model_name, m.model_type, m.biz_domain,
    v.version_code, v.status AS v_state, v.param_count
FROM prcp_model m
LEFT JOIN prcp_model_version v ON v.model_id = m.id AND v.is_deleted = 0
WHERE m.model_code IN ('DNN_REG', 'ACO_OPT', 'NLS_REG') AND m.is_deleted = 0
ORDER BY m.model_code, v.version_code;