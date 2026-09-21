-- ============================================================
-- PRCP 新业务模拟方案 v2 升级脚本
-- 时间：2026-09-21
-- 配套文档：docs/新业务模拟_需求分析.md + 数据库设计.md
--
-- 变更：prcp_sim_scheme 表加 data_date 字段
--   - data_date DATE NOT NULL  COMMENT "模拟的基准数据日期（起始月）"
--   - 索引 idx_data_date
--   - 兼容旧数据：先加可空列 + UPDATE 兜底默认值 + ALTER NOT NULL
-- ============================================================

USE prcp_db;

-- ============================================================
-- 一、加 data_date 列（兼容旧数据：先加可空 + UPDATE + 强 NOT NULL）
-- ============================================================

-- 1.1 检查列是否存在，幂等保护
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'prcp_db'
    AND TABLE_NAME = 'prcp_sim_scheme'
    AND COLUMN_NAME = 'data_date'
);

-- 1.2 加可空列（如果不存在）
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE prcp_sim_scheme ADD COLUMN data_date DATE NULL COMMENT "模拟的基准数据日期（起始月）；引擎从此月开始按月滚动生成未来 N 月快照"',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- 1.3 兜底默认值：旧记录用当前月第一天
SET @sql := IF(@col_exists = 0,
  'UPDATE prcp_sim_scheme SET data_date = DATE_FORMAT(NOW(), ''%Y-%m-01'') WHERE data_date IS NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- 1.4 强 NOT NULL（仅在列为可空时）
SET @is_nullable := (
  SELECT IS_NULLABLE FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'prcp_db'
    AND TABLE_NAME = 'prcp_sim_scheme'
    AND COLUMN_NAME = 'data_date'
);

SET @sql := IF(@is_nullable = 'YES',
  'ALTER TABLE prcp_sim_scheme MODIFY COLUMN data_date DATE NOT NULL COMMENT "模拟的基准数据日期（起始月）；引擎从此月开始按月滚动生成未来 N 月快照"',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- 1.5 加索引（幂等）
SET @idx_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = 'prcp_db'
    AND TABLE_NAME = 'prcp_sim_scheme'
    AND INDEX_NAME = 'idx_data_date'
);

SET @sql := IF(@idx_exists = 0,
  'ALTER TABLE prcp_sim_scheme ADD INDEX idx_data_date (data_date)',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ============================================================
-- 二、验证
-- ============================================================
SELECT 'prcp_sim_scheme.data_date' AS field_,
       COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'prcp_db'
  AND TABLE_NAME = 'prcp_sim_scheme'
  AND COLUMN_NAME = 'data_date';

SELECT 'idx_data_date' AS idx_, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'prcp_db'
  AND TABLE_NAME = 'prcp_sim_scheme'
  AND INDEX_NAME = 'idx_data_date';
