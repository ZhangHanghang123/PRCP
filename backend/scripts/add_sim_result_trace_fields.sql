-- =============================================================================
-- PRCP 新业务模拟 — 结果表增加投放分解追溯字段（v2.1）
--
-- 用途：支持驾驶舱底部「投放节奏」展示区 + 投放分解对账
-- 新增 5 列：
--   growth_type    增长方式 (1=目标增长百分比 2=目标增长绝对值 3=增长百分比 4=增长值)
--   year_target    当年目标增量（元）
--   rhythm_weight  当月节奏权重（%）
--   month_add      当月纯新增投放（不含到期，可为负 = 缩表）
--   month_release  当月到期释放（= 上月 rem_m1）
--
-- 数据日期：2026-10-21
-- =============================================================================

USE prcp_db;

-- -----------------------------------------------------------------------------
-- 1. prcp_sim_result 加 5 列（幂等：先判存在再改）
-- -----------------------------------------------------------------------------
SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_sim_result'
        AND COLUMN_NAME = 'growth_type') > 0,
    'SELECT ''columns already exist, skip'' AS msg',
    'ALTER TABLE prcp_sim_result
       ADD COLUMN growth_type   TINYINT(1)    DEFAULT NULL COMMENT ''增长方式 (1=目标增长百分比 2=目标增长绝对值 3=增长百分比 4=增长值)'',
       ADD COLUMN year_target   DECIMAL(20,4) DEFAULT NULL COMMENT ''当年目标增量（元）'',
       ADD COLUMN rhythm_weight DECIMAL(8,4)  DEFAULT NULL COMMENT ''当月节奏权重（%）'',
       ADD COLUMN month_add     DECIMAL(20,4) DEFAULT NULL COMMENT ''当月纯新增投放（元，可为负=缩表）'',
       ADD COLUMN month_release DECIMAL(20,4) DEFAULT NULL COMMENT ''当月到期释放（元）'''
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- -----------------------------------------------------------------------------
-- 2. 验证
-- -----------------------------------------------------------------------------
SELECT '====== 结果表追溯字段初始化完成 ======' AS status;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_sim_result'
  AND COLUMN_NAME IN ('growth_type','year_target','rhythm_weight','month_add','month_release')
ORDER BY ORDINAL_POSITION;
