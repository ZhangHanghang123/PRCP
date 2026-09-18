-- 升级 模型管理：模型关联指标方案 prcp_kpi_scheme.id（可空，不强制）
-- 数据库：prcp_db（PRCP 平台），执行前请先备份
-- 用法：mysql -ualmd -pAlmd@2026 prcp_db < upgrade_model_kpi_scheme.sql

-- 1. 加 kpi_scheme_id 字段（NULL 允许，可不绑定方案）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_model' AND COLUMN_NAME='kpi_scheme_id')=0,
  'ALTER TABLE prcp_model
     ADD COLUMN kpi_scheme_id BIGINT DEFAULT NULL
     COMMENT ''关联指标方案 prcp_kpi_scheme.id（可空）'' AFTER biz_domain',
  'SELECT 1 AS noop_kpi_scheme_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2. 加索引（方便按方案查模型）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_model' AND INDEX_NAME='idx_kpi_scheme_id')=0,
  'ALTER TABLE prcp_model ADD INDEX idx_kpi_scheme_id (kpi_scheme_id)',
  'SELECT 1 AS noop_idx_kpi_scheme_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 3. 验证
SELECT id, model_code, model_name, model_type, biz_domain, kpi_scheme_id, status
FROM prcp_model
WHERE is_deleted=0
ORDER BY id
LIMIT 10;