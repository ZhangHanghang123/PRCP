-- =============================================================================
-- PRCP 组合反算 · 运行轮次增强（剩余轮次 / 预计耗时 / 每轮指标与评分明细）
-- 迁移编号：V20261111_02
-- 说明：
--   1) prcp_reverse_run_round 增加总轮次、预计总耗时、每指标评分明细
--   2) 幂等：可重复执行，已存在则跳过
-- 执行：mysql -u prcp -p prcp_db < V20261111_02_reverse_run_round_eta.sql
-- =============================================================================

-- ---------- 1. total_rounds：本次运行的总轮次 ----------
SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_round'
            AND COLUMN_NAME = 'total_rounds');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_round ADD COLUMN total_rounds INT NULL COMMENT ''本次运行的总轮次''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 2. eta_total_sec：预计总耗时（秒）----------
SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_round'
            AND COLUMN_NAME = 'eta_total_sec');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_round ADD COLUMN eta_total_sec INT NULL COMMENT ''预计总耗时（秒），由引擎按已完成轮次均速推算''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 3. score_details：每轮各指标的得分明细 ----------
SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_round'
            AND COLUMN_NAME = 'score_details');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_round ADD COLUMN score_details JSON NULL COMMENT ''每指标评分明细：{kpi_code:{target,actual,score,segment_desc,ratio,weight}}''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 4. 校验 ----------
SELECT 'prcp_reverse_run_round 新增列' AS check_item,
       GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION) AS columns_now
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_round'
  AND COLUMN_NAME IN ('total_rounds','eta_total_sec','score_details');
