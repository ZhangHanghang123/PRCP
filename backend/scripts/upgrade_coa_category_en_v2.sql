-- ============================================================
-- v2 修复：category 字段长度从 varchar(8) 改为 varchar(16)
-- 原因：LIABILITY (9字符) / OFF_BALANCE (11字符) 被截断
-- ============================================================

ALTER TABLE prcp_data_basic   MODIFY COLUMN category VARCHAR(16);
ALTER TABLE prcp_data_reverse MODIFY COLUMN category VARCHAR(16);

-- 修复历史截断数据（LIABILIT → LIABILITY / OFF_BALA → OFF_BALANCE）
UPDATE prcp_data_basic   SET category='LIABILITY'   WHERE category='LIABILIT';
UPDATE prcp_data_basic   SET category='OFF_BALANCE' WHERE category='OFF_BALA';
UPDATE prcp_data_reverse SET category='LIABILITY'   WHERE category='LIABILIT';
UPDATE prcp_data_reverse SET category='OFF_BALANCE' WHERE category='OFF_BALA';

-- 验证
SELECT category, COUNT(*) cnt FROM prcp_data_basic   GROUP BY category ORDER BY category;
SELECT category, COUNT(*) cnt FROM prcp_data_reverse GROUP BY category ORDER BY category;