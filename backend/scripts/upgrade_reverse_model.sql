-- 升级 反算方案：新增 计量模型 字段（关联 prcp_model.id，可空）
-- 数据库：prcp_db（PRCP 平台），执行前请先备份

-- 1. 加 model_id 字段
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_reverse_scheme' AND COLUMN_NAME='model_id')=0,
  'ALTER TABLE prcp_reverse_scheme
     ADD COLUMN model_id BIGINT DEFAULT NULL
     COMMENT ''关联计量模型 prcp_model.id（可空）'' AFTER algorithm',
  'SELECT 1 AS noop_model_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2. 加索引（方便按模型查方案）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_reverse_scheme' AND INDEX_NAME='idx_model_id')=0,
  'ALTER TABLE prcp_reverse_scheme ADD INDEX idx_model_id (model_id)',
  'SELECT 1 AS noop_idx_model_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 3. 验证
SELECT id, scheme_code, scheme_name, algorithm, model_id, status
FROM prcp_reverse_scheme
WHERE is_deleted=0
ORDER BY id
LIMIT 10;