-- 升级 模型参数：参数分类（param_category）+ 放宽 kpi_id 必填（支持纯算法超参数）
-- 数据库：prcp_db（PRCP 平台），执行前请先备份

-- 1. 加 param_category 字段（NULL 允许，兼容老数据）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_model_param' AND COLUMN_NAME='param_category')=0,
  'ALTER TABLE prcp_model_param
     ADD COLUMN param_category VARCHAR(32) DEFAULT NULL
     COMMENT ''参数分类：DATA_ESG/NEURAL_NETWORK/LOSS_FUNCTION/TRAINING/OPTIMIZER/KPI_DRIVEN/OTHER'' AFTER param_type',
  'SELECT 1 AS noop_param_category'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2. 加索引（方便按分类筛选）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_model_param' AND INDEX_NAME='idx_param_category')=0,
  'ALTER TABLE prcp_model_param ADD INDEX idx_param_category (param_category)',
  'SELECT 1 AS noop_idx_param_category'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 3. 把 kpi_id 改为可空（支持无 KPI 关联的纯算法超参）
ALTER TABLE prcp_model_param MODIFY COLUMN kpi_id BIGINT DEFAULT NULL;

-- 4. 加 param_value_str 字段（用于存字符串型参数值，如 HJM_PCA、RELU、ADAM 等）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_model_param' AND COLUMN_NAME='param_value_str')=0,
  'ALTER TABLE prcp_model_param
     ADD COLUMN param_value_str VARCHAR(255) DEFAULT NULL
     COMMENT ''字符串型参数值（枚举/路径/列表等）'' AFTER param_value',
  'SELECT 1 AS noop_param_value_str'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 5. 验证
SELECT id, version_id, param_code, param_name, param_category, param_type, kpi_id, param_value, param_value_str
FROM prcp_model_param
WHERE is_deleted=0
ORDER BY id
LIMIT 10;