-- ============================================================
-- 监管指标方案 SCH_REG_2026 · 5 个评分规则 + 25 段
-- 监管参考：
--   LCR  ≥ 100% / NSFR ≥ 100% / CET1 ≥ 7.5% / EVE ≥ -Tier1×15% / ROE 8%-15%
-- ============================================================

USE prcp_db;

-- ============== LCR 评分（监管底线 100%）==============
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 1, 'LCR 五档评分', 'PIECEWISE', 100, 1, 'LCR ≥ 100% 为合格。监管底线 100%。优秀 ≥ 150%，良好 130-150%，合格 110-130%，关注 100-110%，差 < 100%', 'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 150.00, NULL,   100.00, '优秀（≥150%），流动性储备充裕',  NOW(), NOW()),
  (@rule_id, 2, 130.00, 150.00,  85.00, '良好（130%-150%），高于监管底线充裕', NOW(), NOW()),
  (@rule_id, 3, 110.00, 130.00,  70.00, '合格（110%-130%），高于监管底线',     NOW(), NOW()),
  (@rule_id, 4, 100.00, 110.00,  60.00, '关注（100%-110%），刚达监管底线',     NOW(), NOW()),
  (@rule_id, 5, NULL,   100.00,  30.00, '差（<100%），未达监管底线',           NOW(), NOW());

-- ============== NSFR 评分 ==============
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 2, 'NSFR 五档评分', 'PIECEWISE', 100, 1, 'NSFR ≥ 100% 为合格。监管底线 100%。', 'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 120.00, NULL,    100.00, '优秀（≥120%），长期资金匹配充裕',   NOW(), NOW()),
  (@rule_id, 2, 110.00, 120.00,   85.00, '良好（110%-120%）',                    NOW(), NOW()),
  (@rule_id, 3, 105.00, 110.00,   70.00, '合格（105%-110%）',                    NOW(), NOW()),
  (@rule_id, 4, 100.00, 105.00,   60.00, '关注（100%-105%），刚达监管底线',      NOW(), NOW()),
  (@rule_id, 5, NULL,   100.00,   30.00, '差（<100%），未达监管底线',            NOW(), NOW());

-- ============== CET1 评分（监管底线 7.5%）==============
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 3, 'CET1 五档评分', 'PIECEWISE', 100, 1, 'CET1 ≥ 7.5% 为合格（含 2.5% 储备资本）。', 'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 13.00, NULL,    100.00, '优秀（≥13%），资本极为充裕',         NOW(), NOW()),
  (@rule_id, 2, 11.00, 13.00,    85.00, '良好（11%-13%）',                    NOW(), NOW()),
  (@rule_id, 3,  9.00, 11.00,    70.00, '合格（9%-11%），含 2.5% 储备资本',    NOW(), NOW()),
  (@rule_id, 4,  7.50,  9.00,    60.00, '关注（7.5%-9%），刚达监管底线',       NOW(), NOW()),
  (@rule_id, 5, NULL,   7.50,    30.00, '差（<7.5%），未达监管底线',           NOW(), NOW());

-- ============== EVE 评分（≥ 占 Tier1 × -15% 合格）==============
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 4, 'EVE 五档评分', 'PIECEWISE', 100, 0, 'EVE 数值越大（损失越小）越好。监管要求 △EVE ≥ -15% × Tier1。', 'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, -50000000000, NULL,        100.00, '优秀（≥-5 亿），利率风险敞口可控',     NOW(), NOW()),
  (@rule_id, 2, -100000000000, -50000000000, 85.00, '良好（-10亿 ~ -5亿）',                 NOW(), NOW()),
  (@rule_id, 3, -117903500000,   -100000000000, 70.00, '合格（-15%×Tier1 ~ -10 亿）',          NOW(), NOW()),
  (@rule_id, 4, -200000000000,   -117903500000, 60.00, '关注（-20 亿 ~ -15%×Tier1），接近监管线', NOW(), NOW()),
  (@rule_id, 5, NULL,            -200000000000, 30.00, '差（<-20 亿），超出监管容忍度',        NOW(), NOW());

-- ============== ROE 评分（监管参考 8%-15%）==============
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 5, 'ROE 五档评分', 'PIECEWISE', 100, 1, 'ROE 监管参考 8%-15%。', 'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 15.00, NULL,    100.00, '优秀（≥15%），盈利能力领先',         NOW(), NOW()),
  (@rule_id, 2, 12.00, 15.00,    85.00, '良好（12%-15%）',                    NOW(), NOW()),
  (@rule_id, 3,  9.00, 12.00,    70.00, '合格（9%-12%），行业中等水平',       NOW(), NOW()),
  (@rule_id, 4,  8.00,  9.00,    60.00, '关注（8%-9%），刚达监管参考下限',     NOW(), NOW()),
  (@rule_id, 5, NULL,   8.00,    30.00, '差（<8%），低于监管参考下限',         NOW(), NOW());