-- ============================================================
-- 监管指标方案 SCH_REG_2026 · 5 个 LINEAR 线性评分规则
-- 业务背景：行业监管常采用「指标值 ↔ 分数」的连续线性映射，
-- 例如 ROE 在 [8%, 15%] 区间线性 60→100，CET1 在 [7.5%, 11%]
-- 区间线性 60→100。与五档分段 PIECEWISE 形成「阶梯 vs 连续」
-- 两种风格，供业务团队按需选用。
--
-- 字段语义（LINEAR 规则下的非常规解读）：
--   min_value = 锚点的输入值（x 轴）
--   score     = 该锚点的得分（y 轴）
--   max_value = 占位字段，不参与计算（保持 schema 与 PIECEWISE 一致）
--   seg_order = 锚点顺序，按升序在 x 轴上从左到右排列
--
-- 插值规则：
--   v ≤ 首个锚点 x → 首个锚点的 score
--   v ≥ 末个锚点 x → 末个锚点的 score
--   否则在相邻两锚点间线性插值（按比例）
-- ============================================================

USE prcp_db;

-- 兼容：先清理已存在的同名规则（重跑幂等）
DELETE FROM prcp_kpi_score_rule
WHERE scheme_id = 1
  AND calc_method = 'LINEAR'
  AND rule_name IN (
    'ROE 线性插值评分',
    'CET1 线性插值评分',
    'LCR 线性插值评分',
    'NSFR 线性插值评分',
    'EVE 线性插值评分'
  );

-- ============== ROE 线性（监管参考 8%-15%）==============
-- 设计：8% → 60 分、15% → 100 分，两端之外 clamp
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 5, 'ROE 线性插值评分', 'LINEAR', 100, 1,
   'ROE 在 [8%, 15%] 区间线性映射：8% → 60 分；15% → 100 分；区间外按端点 clamp。',
   'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 8.00,  NULL, 60.00,  '下端锚点：ROE=8% 对应 60 分（监管参考下限）', NOW(), NOW()),
  (@rule_id, 2, 15.00, NULL, 100.00, '上端锚点：ROE=15% 对应 100 分（行业优秀水平）', NOW(), NOW());

-- ============== CET1 线性（监管底线 7.5%）==============
-- 设计：7.5% → 60 分、11% → 90 分、13% → 100 分（三段折线）
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 3, 'CET1 线性插值评分', 'LINEAR', 100, 1,
   'CET1 在 [7.5%, 13%] 区间按 3 个锚点折线插值：7.5%→60；11%→90；13%→100。',
   'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 7.50,  NULL, 60.00,  '锚点1：监管底线 7.5% → 60 分',  NOW(), NOW()),
  (@rule_id, 2, 11.00, NULL, 90.00,  '锚点2：良好水平 11% → 90 分',  NOW(), NOW()),
  (@rule_id, 3, 13.00, NULL, 100.00, '锚点3：优秀水平 13% → 100 分', NOW(), NOW());

-- ============== LCR 线性（监管底线 100%）==============
-- 设计：100% → 60 分、120% → 85 分、150% → 100 分（三段折线）
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 1, 'LCR 线性插值评分', 'LINEAR', 100, 1,
   'LCR 在 [100%, 150%] 区间按 3 个锚点折线插值：100%→60；120%→85；150%→100。',
   'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 100.00, NULL, 60.00,  '锚点1：监管底线 100% → 60 分', NOW(), NOW()),
  (@rule_id, 2, 120.00, NULL, 85.00,  '锚点2：稳健水平 120% → 85 分', NOW(), NOW()),
  (@rule_id, 3, 150.00, NULL, 100.00, '锚点3：优秀水平 150% → 100 分', NOW(), NOW());

-- ============== NSFR 线性（监管底线 100%）==============
-- 设计：100% → 60 分、120% → 100 分
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 2, 'NSFR 线性插值评分', 'LINEAR', 100, 1,
   'NSFR 在 [100%, 120%] 区间线性映射：100% → 60 分；120% → 100 分。',
   'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, 100.00, NULL, 60.00,  '下端锚点：监管底线 100% → 60 分', NOW(), NOW()),
  (@rule_id, 2, 120.00, NULL, 100.00, '上端锚点：优秀水平 120% → 100 分', NOW(), NOW());

-- ============== EVE 线性（↓ 逆向；损失越小分数越高）==============
-- 设计：-200 亿 → 30 分；-15%×Tier1(≈-118 亿) → 70 分；0 → 100 分
INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
VALUES
  (1, 4, 'EVE 线性插值评分', 'LINEAR', 100, 0,
   'EVE 数值越大（损失越小）越好。在 [-200亿, 0] 区间按 3 个锚点折线插值：-200亿→30；-118亿→100；0→100。',
   'ACTIVE', 0, 1, 1);
SET @rule_id := LAST_INSERT_ID();
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, created_at, updated_at) VALUES
  (@rule_id, 1, -200000000000, NULL, 30.00,  '锚点1：损失 -200 亿 → 30 分（监管容忍上限）', NOW(), NOW()),
  (@rule_id, 2, -117903500000, NULL, 100.00, '锚点2：监管线 -15%×Tier1 ≈ -117.9 亿 → 100 分', NOW(), NOW()),
  (@rule_id, 3, 0,             NULL, 100.00, '锚点3：无损失 0 → 100 分',                     NOW(), NOW());