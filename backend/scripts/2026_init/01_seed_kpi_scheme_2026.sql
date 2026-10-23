-- ============================================================
-- 01_seed_kpi_scheme_2026.sql - 指标管理 (SCH_REG_2026)
-- 5 大监管指标 + v12b 23 段评分规则
-- ============================================================

SET NAMES utf8mb4;

-- 1. 插入方案
INSERT IGNORE INTO prcp_kpi_scheme
    (scheme_code, scheme_name, description, kpi_count, status, created_by, updated_by)
VALUES
    ('SCH_REG_2026', '2026 监管指标方案',
     '5 大监管指标（LCR/NSFR/EVE/CET1/ROE）+ v12b 0-500 分评分，基于 评分标准_v12b.xlsx',
     5, 'ACTIVE', 1, 1);

-- 2. 插入 5 个 KPI 定义
INSERT IGNORE INTO prcp_kpi_definition
    (scheme_id, kpi_code, kpi_name, indicator_type, calc_unit, threshold_min, threshold_max, formula_desc, status, created_by, updated_by)
VALUES
    ((SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     'REG_LCR',  '流动性覆盖率',  'FORMULA', '%', 0,    500,  '优质流动性资产 / 净现金流出量 (30 天) | ≥ 100%',  'ACTIVE', 1, 1),
    ((SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     'REG_NSFR', '净稳定资金比例', 'FORMULA', '%', 0,    500,  '可用稳定资金 / 所需稳定资金 (1 年) | ≥ 100%',   'ACTIVE', 1, 1),
    ((SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     'REG_EVE',  '银行账户利率风险', 'FORMULA', '%', 0,    15,   'ΔEVE / 一级资本 | ≤ 15%',                          'ACTIVE', 1, 1),
    ((SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     'REG_CET1', '核心一级资本充足率', 'FORMULA', '%', 0,    100,  '核心一级资本 / 风险加权资产 | ≥ 8.7% (7.5+0.5+0.7)','ACTIVE', 1, 1),
    ((SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0 LIMIT 1),
     'REG_ROE',  '净资产收益率',  'FORMULA', '%', 0,    100,  '净利润 / 平均净资产 | 非监管但 < 6% 不可接受',   'ACTIVE', 1, 1);

-- 3. 为每个 KPI 创建 v12b 评分规则
-- higher_is_better: 1=越高越好 (LCR/NSFR/CET1/ROE), 0=越低越好 (EVE)

-- LCR: higher_is_better=1
INSERT INTO prcp_kpi_score_rule
    (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,
     description, status, is_deleted, created_by, updated_by)
SELECT
    s.id, k.id, 'REG_LCR v12b 0-500 分', 'PIECEWISE', 500, 1,
    'LCR 流动性覆盖率 v12b 评分规则 - 23 段 + 过优减分 + 适度最优 500',
    'ACTIVE', 0, 1, 1
FROM prcp_kpi_scheme s
JOIN prcp_kpi_definition k ON k.scheme_id = s.id AND k.kpi_code='REG_LCR' AND k.is_deleted=0
WHERE s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
  AND NOT EXISTS (SELECT 1 FROM prcp_kpi_score_rule r
                  WHERE r.kpi_id=k.id AND r.rule_name='REG_LCR v12b 0-500 分' AND r.is_deleted=0);

-- NSFR: higher_is_better=1
INSERT INTO prcp_kpi_score_rule
    (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,
     description, status, is_deleted, created_by, updated_by)
SELECT
    s.id, k.id, 'REG_NSFR v12b 0-500 分', 'PIECEWISE', 500, 1,
    'NSFR 净稳定资金比例 v12b 评分规则',
    'ACTIVE', 0, 1, 1
FROM prcp_kpi_scheme s
JOIN prcp_kpi_definition k ON k.scheme_id = s.id AND k.kpi_code='REG_NSFR' AND k.is_deleted=0
WHERE s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
  AND NOT EXISTS (SELECT 1 FROM prcp_kpi_score_rule r
                  WHERE r.kpi_id=k.id AND r.rule_name='REG_NSFR v12b 0-500 分' AND r.is_deleted=0);

-- EVE: higher_is_better=0
INSERT INTO prcp_kpi_score_rule
    (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,
     description, status, is_deleted, created_by, updated_by)
SELECT
    s.id, k.id, 'REG_EVE v12b 0-500 分', 'PIECEWISE', 500, 0,
    'EVE 银行账户利率风险 v12b 评分规则（越低越好）',
    'ACTIVE', 0, 1, 1
FROM prcp_kpi_scheme s
JOIN prcp_kpi_definition k ON k.scheme_id = s.id AND k.kpi_code='REG_EVE' AND k.is_deleted=0
WHERE s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
  AND NOT EXISTS (SELECT 1 FROM prcp_kpi_score_rule r
                  WHERE r.kpi_id=k.id AND r.rule_name='REG_EVE v12b 0-500 分' AND r.is_deleted=0);

-- CET1: higher_is_better=1
INSERT INTO prcp_kpi_score_rule
    (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,
     description, status, is_deleted, created_by, updated_by)
SELECT
    s.id, k.id, 'REG_CET1 v12b 0-500 分', 'PIECEWISE', 500, 1,
    'CET1 核心一级资本充足率 v12b 评分规则',
    'ACTIVE', 0, 1, 1
FROM prcp_kpi_scheme s
JOIN prcp_kpi_definition k ON k.scheme_id = s.id AND k.kpi_code='REG_CET1' AND k.is_deleted=0
WHERE s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
  AND NOT EXISTS (SELECT 1 FROM prcp_kpi_score_rule r
                  WHERE r.kpi_id=k.id AND r.rule_name='REG_CET1 v12b 0-500 分' AND r.is_deleted=0);

-- ROE: higher_is_better=1, 红线 6%
INSERT INTO prcp_kpi_score_rule
    (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,
     description, status, is_deleted, created_by, updated_by)
SELECT
    s.id, k.id, 'REG_ROE v12b 0-500 分', 'PIECEWISE', 500, 1,
    'ROE 净资产收益率 v12b 评分规则（< 6% 红线 -500 → 0 分）',
    'ACTIVE', 0, 1, 1
FROM prcp_kpi_scheme s
JOIN prcp_kpi_definition k ON k.scheme_id = s.id AND k.kpi_code='REG_ROE' AND k.is_deleted=0
WHERE s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
  AND NOT EXISTS (SELECT 1 FROM prcp_kpi_score_rule r
                  WHERE r.kpi_id=k.id AND r.rule_name='REG_ROE v12b 0-500 分' AND r.is_deleted=0);

-- 4. 删除旧段位（如果有 v12b 规则）
UPDATE prcp_kpi_score_segment
SET is_deleted=1
WHERE rule_id IN (
    SELECT r.id FROM prcp_kpi_score_rule r
    JOIN prcp_kpi_definition k ON r.kpi_id=k.id AND k.is_deleted=0
    JOIN prcp_kpi_scheme s ON r.scheme_id=s.id AND s.is_deleted=0
    WHERE s.scheme_code='SCH_REG_2026' AND r.rule_name LIKE '%v12b 0-500 分%'
);

-- 5. 插入 v12b 段位 (5 套, 每套 23 段)
-- 用存储过程或批量 INSERT 处理

-- 5.1 LCR 段位
INSERT INTO prcp_kpi_score_segment
    (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted)
SELECT r.id, t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0
FROM prcp_kpi_score_rule r
JOIN prcp_kpi_definition k ON r.kpi_id=k.id AND k.kpi_code='REG_LCR' AND k.is_deleted=0
JOIN prcp_kpi_scheme s ON r.scheme_id=s.id AND s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
CROSS JOIN (
    SELECT 1 AS seg_order, 0.0    AS min_value, 120.0  AS max_value, 0    AS score, '🔴 不达标 (≤红线 120%)' AS segment_desc UNION ALL
    SELECT 2, 120.0,  122.0,  15,   '🟠 危险 0-150' UNION ALL
    SELECT 3, 122.0,  124.0,  45,   '🟠 危险' UNION ALL
    SELECT 4, 124.0,  126.0,  75,   '🟠 危险' UNION ALL
    SELECT 5, 126.0,  128.0,  105,  '🟠 危险' UNION ALL
    SELECT 6, 128.0,  130.0,  135,  '🟠 危险' UNION ALL
    SELECT 7, 130.0,  132.0,  165,  '🟡 预警 150-300' UNION ALL
    SELECT 8, 132.0,  134.0,  195,  '🟡 预警' UNION ALL
    SELECT 9, 134.0,  136.0,  225,  '🟡 预警' UNION ALL
    SELECT 10, 136.0, 138.0,  255,  '🟡 预警' UNION ALL
    SELECT 11, 138.0, 140.0,  285,  '🟡 预警' UNION ALL
    SELECT 12, 140.0, 142.0,  320,  '🟢 安全 300-500' UNION ALL
    SELECT 13, 142.0, 144.0,  360,  '🟢 安全' UNION ALL
    SELECT 14, 144.0, 146.0,  400,  '🟢 安全' UNION ALL
    SELECT 15, 146.0, 148.0,  440,  '🟢 安全' UNION ALL
    SELECT 16, 148.0, 150.0,  480,  '🟢 安全 (中信 148% 命中)' UNION ALL
    SELECT 17, 150.0, 150.0,  500,  '⭐ 适度最优 150%' UNION ALL
    SELECT 18, 150.0, 160.0,  480,  '🟢 过优 资金闲置' UNION ALL
    SELECT 19, 160.0, 170.0,  440,  '🟢 过优' UNION ALL
    SELECT 20, 170.0, 180.0,  400,  '🟢 过优' UNION ALL
    SELECT 21, 180.0, 200.0,  360,  '🟡 过优 减分' UNION ALL
    SELECT 22, 200.0, 250.0,  320,  '🟡 过优 严重' UNION ALL
    SELECT 23, 250.0, 9999.0, 280,  '🔴 极度过剩'
) t
WHERE r.rule_name='REG_LCR v12b 0-500 分' AND r.is_deleted=0;

-- 5.2 NSFR 段位
INSERT INTO prcp_kpi_score_segment
    (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted)
SELECT r.id, t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0
FROM prcp_kpi_score_rule r
JOIN prcp_kpi_definition k ON r.kpi_id=k.id AND k.kpi_code='REG_NSFR' AND k.is_deleted=0
JOIN prcp_kpi_scheme s ON r.scheme_id=s.id AND s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
CROSS JOIN (
    SELECT 1 AS seg_order, 0.0  AS min_value, 100.0 AS max_value, 0    AS score, '🔴 不达标 (≤红线 100%)' AS segment_desc UNION ALL
    SELECT 2, 100.0, 100.5, 15,   '🟠 危险' UNION ALL
    SELECT 3, 100.5, 101.0, 45,   '🟠 危险' UNION ALL
    SELECT 4, 101.0, 101.5, 75,   '🟠 危险' UNION ALL
    SELECT 5, 101.5, 102.0, 105,  '🟠 危险' UNION ALL
    SELECT 6, 102.0, 103.0, 135,  '🟠 危险' UNION ALL
    SELECT 7, 103.0, 103.5, 165,  '🟡 预警' UNION ALL
    SELECT 8, 103.5, 104.0, 195,  '🟡 预警' UNION ALL
    SELECT 9, 104.0, 104.5, 225,  '🟡 预警' UNION ALL
    SELECT 10, 104.5, 105.0, 255, '🟡 预警 (中信 104.52% 命中)' UNION ALL
    SELECT 11, 105.0, 105.5, 285, '🟡 预警' UNION ALL
    SELECT 12, 105.5, 106.0, 320, '🟢 安全' UNION ALL
    SELECT 13, 106.0, 106.5, 360, '🟢 安全 (适度最优)' UNION ALL
    SELECT 14, 106.5, 107.0, 400, '🟢 安全' UNION ALL
    SELECT 15, 107.0, 107.5, 440, '🟢 安全' UNION ALL
    SELECT 16, 107.5, 108.0, 480, '🟢 安全' UNION ALL
    SELECT 17, 108.0, 108.0, 500, '⭐ 适度最优 108%' UNION ALL
    SELECT 18, 108.0, 110.0, 480, '🟢 过优' UNION ALL
    SELECT 19, 110.0, 112.0, 440, '🟢 过优' UNION ALL
    SELECT 20, 112.0, 115.0, 400, '🟡 过优' UNION ALL
    SELECT 21, 115.0, 120.0, 360, '🟡 过优' UNION ALL
    SELECT 22, 120.0, 130.0, 320, '🟡 过优' UNION ALL
    SELECT 23, 130.0, 9999.0, 280, '🔴 极度过剩'
) t
WHERE r.rule_name='REG_NSFR v12b 0-500 分' AND r.is_deleted=0;

-- 5.3 EVE 段位 (越低越好, 段位反向)
INSERT INTO prcp_kpi_score_segment
    (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted)
SELECT r.id, t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0
FROM prcp_kpi_score_rule r
JOIN prcp_kpi_definition k ON r.kpi_id=k.id AND k.kpi_code='REG_EVE' AND k.is_deleted=0
JOIN prcp_kpi_scheme s ON r.scheme_id=s.id AND s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
CROSS JOIN (
    SELECT 1 AS seg_order, 15.0  AS min_value, 9999.0 AS max_value, 0    AS score, '🔴 不达标 (≥红线 15%)' AS segment_desc UNION ALL
    SELECT 2, 14.4,  15.0,  15,   '🟠 危险' UNION ALL
    SELECT 3, 13.8,  14.4,  45,   '🟠 危险' UNION ALL
    SELECT 4, 13.2,  13.8,  75,   '🟠 危险' UNION ALL
    SELECT 5, 12.6,  13.2,  105,  '🟠 危险' UNION ALL
    SELECT 6, 12.0,  12.6,  135,  '🟠 危险' UNION ALL
    SELECT 7, 11.6,  12.0,  165,  '🟡 预警' UNION ALL
    SELECT 8, 11.2,  11.6,  195,  '🟡 预警' UNION ALL
    SELECT 9, 10.8,  11.2,  225,  '🟡 预警' UNION ALL
    SELECT 10, 10.4, 10.8,  255,  '🟡 预警' UNION ALL
    SELECT 11, 10.0, 10.4,  285,  '🟡 预警 (中信 10.54% 命中)' UNION ALL
    SELECT 12, 9.6,  10.0,  320,  '🟢 安全' UNION ALL
    SELECT 13, 9.2,  9.6,  360,  '🟢 安全' UNION ALL
    SELECT 14, 8.8,  9.2,  400,  '🟢 安全' UNION ALL
    SELECT 15, 8.4,  8.8,  440,  '🟢 安全 (适度最优 8.4%)' UNION ALL
    SELECT 16, 8.0,  8.4,  480,  '🟢 安全' UNION ALL
    SELECT 17, 8.0,  8.0,  500,  '⭐ 适度最优 8%' UNION ALL
    SELECT 18, 7.0,  8.0,  480,  '🟢 过优 (错失上行)' UNION ALL
    SELECT 19, 6.0,  7.0,  440,  '🟢 过优' UNION ALL
    SELECT 20, 5.0,  6.0,  400,  '🟢 过优' UNION ALL
    SELECT 21, 4.0,  5.0,  360,  '🟢 过优' UNION ALL
    SELECT 22, 3.0,  4.0,  320,  '🟡 过优' UNION ALL
    SELECT 23, 0.0,  3.0,  450,  '🔴 极度过剩 (不可达)'
) t
WHERE r.rule_name='REG_EVE v12b 0-500 分' AND r.is_deleted=0;

-- 5.4 CET1 段位 (红线 8.7%, 越低越危险)
INSERT INTO prcp_kpi_score_segment
    (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted)
SELECT r.id, t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0
FROM prcp_kpi_score_rule r
JOIN prcp_kpi_definition k ON r.kpi_id=k.id AND k.kpi_code='REG_CET1' AND k.is_deleted=0
JOIN prcp_kpi_scheme s ON r.scheme_id=s.id AND s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
CROSS JOIN (
    SELECT 1 AS seg_order, 0.0   AS min_value, 8.7  AS max_value, 0    AS score, '🔴 不达标 (≤红线 8.7%)' AS segment_desc UNION ALL
    SELECT 2, 8.7,  8.75, 15,   '🟠 危险' UNION ALL
    SELECT 3, 8.75, 8.8,  45,   '🟠 危险' UNION ALL
    SELECT 4, 8.8,  8.85, 75,   '🟠 危险' UNION ALL
    SELECT 5, 8.85, 8.9,  105,  '🟠 危险' UNION ALL
    SELECT 6, 8.9,  9.0,  135,  '🟠 危险 (中信 8.98% 命中)' UNION ALL
    SELECT 7, 9.0,  9.1,  165,  '🟡 预警' UNION ALL
    SELECT 8, 9.1,  9.2,  195,  '🟡 预警' UNION ALL
    SELECT 9, 9.2,  9.3,  225,  '🟡 预警' UNION ALL
    SELECT 10, 9.3, 9.4,  255,  '🟡 预警' UNION ALL
    SELECT 11, 9.4, 9.5,  285,  '🟡 预警' UNION ALL
    SELECT 12, 9.5, 9.6,  320,  '🟢 安全 (D-SIBs 基线)' UNION ALL
    SELECT 13, 9.6, 9.7,  360,  '🟢 安全' UNION ALL
    SELECT 14, 9.7, 9.8,  400,  '🟢 安全' UNION ALL
    SELECT 15, 9.8, 9.9,  440,  '🟢 安全' UNION ALL
    SELECT 16, 9.9, 10.0, 480,  '🟢 安全 (适度最优)' UNION ALL
    SELECT 17, 10.0, 10.0, 500, '⭐ 适度最优 10%' UNION ALL
    SELECT 18, 10.0, 11.0, 480, '🟢 过优 (ROE 承压)' UNION ALL
    SELECT 19, 11.0, 12.0, 440, '🟢 过优' UNION ALL
    SELECT 20, 12.0, 13.0, 400, '🟢 过优' UNION ALL
    SELECT 21, 13.0, 15.0, 360, '🟡 过优 (资本冗余)' UNION ALL
    SELECT 22, 15.0, 20.0, 320, '🟡 过优' UNION ALL
    SELECT 23, 20.0, 9999.0, 280, '🔴 极度过剩'
) t
WHERE r.rule_name='REG_CET1 v12b 0-500 分' AND r.is_deleted=0;

-- 5.5 ROE 段位 (红线 6%, 越高越好)
INSERT INTO prcp_kpi_score_segment
    (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted)
SELECT r.id, t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0
FROM prcp_kpi_score_rule r
JOIN prcp_kpi_definition k ON r.kpi_id=k.id AND k.kpi_code='REG_ROE' AND k.is_deleted=0
JOIN prcp_kpi_scheme s ON r.scheme_id=s.id AND s.scheme_code='SCH_REG_2026' AND s.is_deleted=0
CROSS JOIN (
    SELECT 1 AS seg_order, 0.0 AS min_value, 6.0 AS max_value, 0    AS score, '🔴 不达标 (红线 6% 硬约束)' AS segment_desc UNION ALL
    SELECT 2, 6.0,  6.4,  15,   '🟠 危险' UNION ALL
    SELECT 3, 6.4,  6.8,  45,   '🟠 危险' UNION ALL
    SELECT 4, 6.8,  7.2,  75,   '🟠 危险' UNION ALL
    SELECT 5, 7.2,  7.6,  105,  '🟠 危险' UNION ALL
    SELECT 6, 7.6,  8.0,  135,  '🟠 危险' UNION ALL
    SELECT 7, 8.0,  8.2,  165,  '🟡 预警' UNION ALL
    SELECT 8, 8.2,  8.4,  195,  '🟡 预警' UNION ALL
    SELECT 9, 8.4,  8.6,  225,  '🟡 预警' UNION ALL
    SELECT 10, 8.6, 8.8,  255,  '🟡 预警' UNION ALL
    SELECT 11, 8.8, 9.0,  285,  '🟡 预警 (中信 9.61% 命中)' UNION ALL
    SELECT 12, 9.0, 9.6,  320,  '🟢 安全' UNION ALL
    SELECT 13, 9.6, 10.2, 360,  '🟢 安全' UNION ALL
    SELECT 14, 10.2, 10.8, 400, '🟢 安全' UNION ALL
    SELECT 15, 10.8, 11.4, 440, '🟢 安全' UNION ALL
    SELECT 16, 11.4, 12.0, 480, '🟢 安全 (适度最优)' UNION ALL
    SELECT 17, 12.0, 12.0, 500, '⭐ 适度最优 12%' UNION ALL
    SELECT 18, 12.0, 14.0, 480, '🟢 过优 (可能高杠杆)' UNION ALL
    SELECT 19, 14.0, 16.0, 440, '🟢 过优' UNION ALL
    SELECT 20, 16.0, 18.0, 400, '🟡 过优' UNION ALL
    SELECT 21, 18.0, 20.0, 360, '🟡 过优' UNION ALL
    SELECT 22, 20.0, 25.0, 320, '🟡 过优 (异常高)' UNION ALL
    SELECT 23, 25.0, 9999.0, 280, '🔴 极度过剩'
) t
WHERE r.rule_name='REG_ROE v12b 0-500 分' AND r.is_deleted=0;

-- 6. 更新方案 kpi_count
UPDATE prcp_kpi_scheme s
SET kpi_count = (
    SELECT COUNT(*) FROM prcp_kpi_definition k
    WHERE k.scheme_id = s.id AND k.is_deleted = 0
)
WHERE s.scheme_code = 'SCH_REG_2026';

-- 7. 验证
SELECT '====== 01_seed_kpi_scheme_2026.sql 完成 ======' AS status;
SELECT
    s.scheme_code, s.scheme_name, s.kpi_count, s.status,
    COUNT(DISTINCT r.id) AS rule_count,
    COUNT(DISTINCT seg.id) AS segment_count
FROM prcp_kpi_scheme s
LEFT JOIN prcp_kpi_definition k ON k.scheme_id = s.id AND k.is_deleted = 0
LEFT JOIN prcp_kpi_score_rule r ON r.kpi_id = k.id AND r.is_deleted = 0
LEFT JOIN prcp_kpi_score_segment seg ON seg.rule_id = r.id AND seg.is_deleted = 0
WHERE s.scheme_code = 'SCH_REG_2026' AND s.is_deleted = 0
GROUP BY s.id, s.scheme_code, s.scheme_name, s.kpi_count, s.status;