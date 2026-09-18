-- 升级 KPI 指标定义：新增指标类型（1=公式指标 / 2=函数指标）+ 函数指标脚本路径/名称
-- 数据库：prcp_db（PRCP 平台），执行前请先备份
-- 用法：mysql -ualmd -pAlmd@2026 prcp_db < upgrade_kpi_indicator_type.sql

-- 1. 加 indicator_type 字段（默认 1=公式指标）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_kpi_definition' AND COLUMN_NAME='indicator_type')=0,
  'ALTER TABLE prcp_kpi_definition
     ADD COLUMN indicator_type TINYINT(1) NOT NULL DEFAULT 1
     COMMENT ''1=公式指标 2=函数指标'' AFTER scheme_id',
  'SELECT 1 AS noop_indicator_type'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2. 加 script_path 字段（函数指标用，相对 backend/ 根）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_kpi_definition' AND COLUMN_NAME='script_path')=0,
  'ALTER TABLE prcp_kpi_definition
     ADD COLUMN script_path VARCHAR(255) DEFAULT NULL
     COMMENT ''函数指标：脚本路径，相对 backend/'' AFTER formula',
  'SELECT 1 AS noop_script_path'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 3. 加 script_name 字段（函数指标用：calc()）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='prcp_kpi_definition' AND COLUMN_NAME='script_name')=0,
  'ALTER TABLE prcp_kpi_definition
     ADD COLUMN script_name VARCHAR(128) DEFAULT NULL
     COMMENT ''函数指标：脚本内的入口函数名，默认 calc'' AFTER script_path',
  'SELECT 1 AS noop_script_name'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 4. 把 formula 改为可空（函数指标不需要公式）
ALTER TABLE prcp_kpi_definition MODIFY COLUMN formula TEXT NULL;

-- 5. 验证
SELECT id, kpi_code, kpi_name, indicator_type, script_path, script_name, formula
FROM prcp_kpi_definition
WHERE is_deleted=0
ORDER BY id
LIMIT 10;