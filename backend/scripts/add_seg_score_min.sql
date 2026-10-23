-- =============================================================================
-- 指标评分 · 分段规则：分数拆分为「最大值分数 / 最小值分数」
--
-- 目的：支持分段内线性插值
--   区间 [min_value, max_value) 对应分数区间 [score_min, score_max]
--   score_max = 该段上界（max_value）处的分数
--   score_min = 该段下界（min_value）处的分数
--   段内插值：score = score_min + (x - min_value) / (max_value - min_value)
--                      × (score_max - score_min)
--
-- 兼容性：
--   新列默认 NULL。NULL 时后端回退到原 score 字段（阶梯评分，行为不变）
--   旧数据无需迁移，score 字段保留为「默认分」
--
-- 数据日期：2026-10-22
-- =============================================================================

USE prcp_db;

SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_score_segment'
        AND COLUMN_NAME = 'score_min') > 0,
    'SELECT ''column score_min already exists, skip'' AS msg',
    'ALTER TABLE prcp_kpi_score_segment
       ADD COLUMN score_min DECIMAL(8,2) DEFAULT NULL
         COMMENT ''最小值分数（下界 min_value 处的得分），NULL 表示不启用段内插值''
       AFTER `score`'
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_score_segment'
  AND COLUMN_NAME IN ('score', 'score_min')
ORDER BY ORDINAL_POSITION;