-- PRCP 指标维护 - 试算分数列（MySQL 8 兼容）
SET @col_exists = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_kpi_value' AND COLUMN_NAME = 'score'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE prcp_kpi_value ADD COLUMN score DECIMAL(8,2) DEFAULT NULL COMMENT ''试算分数（来自 prcp_kpi_score_rule）''',
  'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;