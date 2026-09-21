-- ============================================================
-- PRCP 新业务模拟方案 v3 升级脚本
-- 时间：2026-09-21
-- 配套文档：docs/新业务模拟_需求分析.md + 数据库设计.md
--
-- 变更：prcp_sim_term_ratio 表加 interest_rate 字段
--   - interest_rate DECIMAL(8,4) DEFAULT 0  COMMENT "新业务利率（%）"
--   - CHECK 0~100 范围
--
-- 兼容：旧数据自动填 0（不报错）
-- ============================================================

USE prcp_db;

-- 1) 检查列是否存在
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'prcp_db'
    AND TABLE_NAME = 'prcp_sim_term_ratio'
    AND COLUMN_NAME = 'interest_rate'
);

-- 2) 加可空列（如果不存在）
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE prcp_sim_term_ratio ADD COLUMN interest_rate DECIMAL(8,4) NULL COMMENT "新业务利率（%），0~100"',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- 3) 兜底默认值：旧记录填 0
SET @sql := IF(@col_exists = 0,
  'UPDATE prcp_sim_term_ratio SET interest_rate = 0 WHERE interest_rate IS NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- 4) 强 NOT NULL + DEFAULT 0 + CHECK
SET @is_nullable := (
  SELECT IS_NULLABLE FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'prcp_db'
    AND TABLE_NAME = 'prcp_sim_term_ratio'
    AND COLUMN_NAME = 'interest_rate'
);

SET @sql := IF(@is_nullable = 'YES',
  'ALTER TABLE prcp_sim_term_ratio MODIFY COLUMN interest_rate DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT "新业务利率（%），0~100"',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- 5) CHECK 约束（幂等）
SET @chk_exists := (
  SELECT COUNT(*) FROM information_schema.CHECK_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = 'prcp_db'
    AND CONSTRAINT_NAME = 'chk_interest_rate'
);

SET @sql := IF(@chk_exists = 0,
  'ALTER TABLE prcp_sim_term_ratio ADD CONSTRAINT chk_interest_rate CHECK (interest_rate >= 0 AND interest_rate <= 100)',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ============================================================
-- 验证
-- ============================================================
SELECT 'prcp_sim_term_ratio.interest_rate' AS field_,
       COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'prcp_db'
  AND TABLE_NAME = 'prcp_sim_term_ratio'
  AND COLUMN_NAME = 'interest_rate';

SELECT 'chk_interest_rate' AS chk_, CONSTRAINT_NAME, CHECK_CLAUSE
FROM information_schema.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'prcp_db'
  AND CONSTRAINT_NAME = 'chk_interest_rate';
