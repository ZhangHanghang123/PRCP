-- =============================================================================
-- PRCP 新业务模拟 — 结果表增加「计划到期」字段（v2.2）
--
-- 背景：
--   v2.2 改为「绝对到期月」口径后，每行结果只体现「截至本月已发生」的投放
--   对未来到期的影响 —— 看不到未来 5 年每月都会新增业务。
--   例：M13 行只显示 M1 投放的 12 月期到期（199.51 亿），
--      而 M2~M12 的投放虽然已落桶，但要到 M14~M24 才到期。
--
-- 新增 2 列（冗余存储，便于前端直接展示未来到期时间轴）：
--   planned_due  第 M 月「计划到期」金额 = 截至 M 月末所有投放中，
--                 原始期限恰好落在 M 月到期的部分
--                 （含存量 + 当月新增），即未来到期时间轴上第 M 格的完整值
--   cum_planned  截至 M 月的累计计划投放额
--
-- 数据日期：2026-10-21
-- =============================================================================

USE prcp_db;

-- -----------------------------------------------------------------------------
-- 1. 加列（幂等）
-- -----------------------------------------------------------------------------
SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_sim_result'
        AND COLUMN_NAME = 'planned_due') > 0,
    'SELECT ''columns already exist, skip'' AS msg',
    'ALTER TABLE prcp_sim_result
       ADD COLUMN planned_due DECIMAL(20,4) DEFAULT NULL
         COMMENT ''当月计划到期金额（绝对到期月口径：存量+当月新增，含未来月份投放本就会到期的部分）'',
       ADD COLUMN cum_planned DECIMAL(20,4) DEFAULT NULL
         COMMENT ''截至当月的累计计划投放额'''
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- -----------------------------------------------------------------------------
-- 2. 验证
-- -----------------------------------------------------------------------------
SELECT '====== 结果表计划到期字段初始化完成 ======' AS status;

SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_sim_result'
  AND COLUMN_NAME IN ('planned_due','cum_planned')
ORDER BY ORDINAL_POSITION;