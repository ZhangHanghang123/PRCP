-- 演示数据：给 REV_GROWTH 关联的 ZXCOA_V1 方案的几个核心节点挂上 5 个指标
-- 数据日期: 2025-12-01（M1）

INSERT IGNORE INTO prcp_metric_coefficient
  (id, scheme_id, scheme_code, node_id, node_code, metric_type, metric_code, data_date,
   current_value, y1_value, y2_value, y3_value, y4_value, y5_value, unit, description, status, created_by, updated_by)
SELECT
  CONCAT('ZXCOA_V1_', n.node_code, '_', m.metric_code, '_20251201') AS id,
  6 AS scheme_id, 'ZXCOA_V1' AS scheme_code,
  n.id AS node_id, n.node_code,
  m.metric_type, m.metric_code,
  STR_TO_DATE('2025-12-01', '%Y-%m-%d'),
  m.cv AS current_value, m.cv+0.5 AS y1_value, m.cv+1.0 AS y2_value,
  m.cv+1.5 AS y3_value, m.cv+2.0 AS y4_value, m.cv+2.5 AS y5_value,
  'PERCENT' AS unit,
  CONCAT('演示数据 ', m.metric_type) AS description,
  'ACTIVE', 1, 1
FROM prcp_coa_node n
JOIN (
  -- 只取 5 个核心 L1/L2 节点（避免给所有 40 个节点全挂）
  SELECT id, node_code FROM prcp_coa_node
  WHERE scheme_id=6 AND node_level<=2
  ORDER BY path LIMIT 8
) nn ON nn.id=n.id
JOIN (
  SELECT 'ROE'       AS metric_type, 'ROE' AS metric_code, 12.5 AS cv UNION ALL
  SELECT 'CET1',      'CET1',                  11.2          UNION ALL
  SELECT 'LCR',       'LCR',                  150.0          UNION ALL
  SELECT 'NSFR',      'NSFR',                 108.5          UNION ALL
  SELECT 'DELTA_EVE', 'DELTA_EVE',             -3.2
) m;