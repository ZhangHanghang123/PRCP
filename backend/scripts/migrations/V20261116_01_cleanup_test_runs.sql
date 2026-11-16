-- =============================================================================
-- 清理测试反算运行记录（2026-11-11 调试产生）
-- 背景：
--   调试期间创建了若干测试 run。其中 run 36（2026 方案）因引擎读取空表
--   prcp_data_balance 导致求解结果全 0，并成为 options 的默认 run，
--   使驾驶舱「资产余额/负债余额」显示 0.00、「末级账户册余额走势」无数据。
-- 处理：
--   1) 软删除测试 run（is_deleted=1，保留可追溯）
--   2) 同步软删除其关联的 prcp_data_reverse / prcp_reverse_result /
--      prcp_reverse_run_log / prcp_reverse_run_round
--   3) 软删除测试方案 HEUR_RND_TEST
-- 幂等：可重复执行
-- =============================================================================

-- ---------- 1. 软删除测试 run 及其关联数据 ----------
-- 测试 run：32~37（run 31 为 2026 方案的原始正确数据，必须保留）
-- 注意：prcp_reverse_run_log 与 prcp_reverse_run_round 无 is_deleted 列，
--      仅物理保留（不影响任何查询，接口均按 run_id 过滤）
UPDATE prcp_reverse_run       SET is_deleted = 1 WHERE id BETWEEN 32 AND 37 AND is_deleted = 0;
UPDATE prcp_data_reverse      SET is_deleted = 1 WHERE run_id BETWEEN 32 AND 37 AND is_deleted = 0;
UPDATE prcp_reverse_result    SET is_deleted = 1 WHERE run_id BETWEEN 32 AND 37 AND is_deleted = 0;

-- prcp_reverse_result / prcp_reverse_run_log / prcp_reverse_run_round 可能没有 is_deleted 列
-- 用 information_schema 判断后再执行，避免报错
SET @has := (SELECT COUNT(*) FROM information_schema.COLUMNS
             WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_log'
               AND COLUMN_NAME = 'is_deleted');
SET @s := IF(@has > 0,
  'UPDATE prcp_reverse_run_log SET is_deleted = 1 WHERE run_id BETWEEN 32 AND 37 AND is_deleted = 0',
  'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @has := (SELECT COUNT(*) FROM information_schema.COLUMNS
             WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_round'
               AND COLUMN_NAME = 'is_deleted');
SET @s := IF(@has > 0,
  'UPDATE prcp_reverse_run_round SET is_deleted = 1 WHERE run_id BETWEEN 32 AND 37 AND is_deleted = 0',
  'SELECT 1');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 2. 软删除测试方案 ----------
UPDATE prcp_reverse_scheme SET is_deleted = 1 WHERE scheme_code = 'HEUR_RND_TEST' AND is_deleted = 0;
UPDATE prcp_reverse_target SET is_deleted = 1
WHERE scheme_id IN (SELECT id FROM prcp_reverse_scheme WHERE scheme_code = 'HEUR_RND_TEST')
  AND is_deleted = 0;

-- ---------- 3. 校验 ----------
SELECT '各方案可见 SUCCESS run' AS check_item,
       s.scheme_code,
       GROUP_CONCAT(r.id ORDER BY r.id) AS run_ids,
       COUNT(*) AS n
FROM prcp_reverse_scheme s
JOIN prcp_reverse_run r ON r.scheme_id = s.id AND r.is_deleted = 0
WHERE s.is_deleted = 0 AND r.status = 'SUCCESS'
GROUP BY s.scheme_code;
