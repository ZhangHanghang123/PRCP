-- ============================================================
-- 03_seed_sim_scheme.sql - 测算方案 + 铺底数据
-- 1. 账户册方案 (ZX_COA)
-- 2. 测算方案 (SCS_2026, 关联 ZX_COA)
-- 3. 测算节点配置 (15 个核心节点)
-- 4. 铺底 metric_coefficient (5 指标 × 16 月 = 80 条)
-- ============================================================

SET NAMES utf8mb4;

-- 1. 插入账户册方案 (中信银行 ZX_COA)
INSERT IGNORE INTO prcp_coa_scheme
    (scheme_code, scheme_name, description, status, node_count, created_by, updated_by)
VALUES
    ('ZX_COA', '中信银行账户册方案',
     '中信银行 2025 年度披露账户册 (30 资产 + 24 负债 + 1 权益 + 2 空行 = 57 行)',
     'ACTIVE', 57, 1, 1);

-- 2. 插入账户册节点 (15 个末级示例节点 - 用于测算)
-- 注: 实际项目会从 init_coa_from_xlsx.py 导入完整 57 行
INSERT IGNORE INTO prcp_coa_node
    (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, created_by, updated_by)
SELECT
    s.id, t.node_code, t.node_name, NULL, t.node_level, t.node_type, t.path, t.sort_order, 'ACTIVE', 1, 1
FROM prcp_coa_scheme s
CROSS JOIN (
    -- 资产侧 15 个节点
    SELECT 'S010101010000' AS node_code, '1.1.对公一般贷款' AS node_name, 4 AS node_level, 'LEAF' AS node_type, '/S01/S010101/S010101010000' AS path, 1 AS sort_order UNION ALL
    SELECT 'S010101020000', '1.2.个人贷款', 4, 'LEAF', '/S01/S010101/S010101020000', 2 UNION ALL
    SELECT 'S010101030000', '1.3.信用卡贷款', 4, 'LEAF', '/S01/S010101/S010101030000', 3 UNION ALL
    SELECT 'S010101040000', '1.4.票据贴现', 4, 'LEAF', '/S01/S010101/S010101040000', 4 UNION ALL
    SELECT 'S010101050000', '1.5.非银贷款', 4, 'LEAF', '/S01/S010101/S010101050000', 5 UNION ALL
    SELECT 'S010102010100', '2.1.1金市AC', 5, 'LEAF', '/S01/S010102/S010102010100', 6 UNION ALL
    SELECT 'S010102010200', '2.1.2司库AC', 5, 'LEAF', '/S01/S010102/S010102010200', 7 UNION ALL
    SELECT 'S010102020000', '2.2.结构化融资', 4, 'LEAF', '/S01/S010102/S010102020000', 8 UNION ALL
    SELECT 'S010102030000', '2.3.同业资产', 4, 'LEAF', '/S01/S010102/S010102030000', 9 UNION ALL
    SELECT 'S010102040000', '2.4.存款准备金', 4, 'LEAF', '/S01/S010102/S010102040000', 10 UNION ALL
    SELECT 'S010201000000', '1.外币贷款', 3, 'LEAF', '/S01/S010201/S010201000000', 11 UNION ALL
    SELECT 'S010202010000', '2.1.外币债券', 4, 'LEAF', '/S01/S010202/S010202010000', 12 UNION ALL
    -- 负债侧
    SELECT 'S020101010100', '1.1.1对公活期存款', 5, 'LEAF', '/S02/S020101/S020101010100', 13 UNION ALL
    SELECT 'S020101010200', '1.1.2对公定期存款', 5, 'LEAF', '/S02/S020101/S020101010200', 14 UNION ALL
    SELECT 'S020101020100', '1.2.1零售活期存款', 5, 'LEAF', '/S02/S020101/S020101020100', 15
) t
WHERE s.scheme_code='ZX_COA' AND s.is_deleted=0;

-- 3. 插入测算方案 (SCS_2026)
INSERT IGNORE INTO prcp_sim_scheme
    (scheme_code, scheme_name, coa_scheme_id, description, config_node_count, status, created_by, updated_by)
SELECT
    'SCS_2026', '2026 测算方案 (NLS_REG)',
    (SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0 LIMIT 1),
    '基于 NLS_REG 非线性求解模型，24 月滚动测算 + ΔEVE 监控',
    15, 'IN_PROGRESS', 1, 1;

-- 4. 插入测算节点配置 (15 节点, 各节点配置基准余额/利率/期限)
INSERT IGNORE INTO prcp_sim_scheme_node
    (scheme_id, node_id, node_code, node_name, alloc_pct, duration_months, base_balance, scenario_rate_pct, scenario_growth_pct, sort_order, created_by, updated_by)
SELECT
    s.id, n.id, n.node_code, n.node_name,
    t.alloc_pct, t.duration_months, t.base_balance, t.scenario_rate_pct, t.scenario_growth_pct, n.sort_order, 1, 1
FROM prcp_sim_scheme s
JOIN prcp_coa_node n ON n.scheme_id = (SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0)
CROSS JOIN (
    -- 资产侧 (按余额占比 + 期限)
    SELECT 'S010101010000' AS node_code, 0.207 AS alloc_pct, 36 AS duration_months, 2450000000000 AS base_balance, 4.50 AS scenario_rate_pct, 0.020 AS scenario_growth_pct UNION ALL
    SELECT 'S010101020000', 0.154, 60, 1820000000000, 5.20, 0.025 UNION ALL
    SELECT 'S010101030000', 0.039, 12, 460000000000, 12.00, 0.015 UNION ALL
    SELECT 'S010101040000', 0.027, 3,  320000000000, 2.50, -0.005 UNION ALL
    SELECT 'S010101050000', 0.042, 24, 500000000000, 4.00, 0.020 UNION ALL
    SELECT 'S010102010100', 0.050, 36, 590000000000, 3.20, 0.018 UNION ALL
    SELECT 'S010102010200', 0.084, 60, 980000000000, 3.20, 0.020 UNION ALL
    SELECT 'S010102020000', 0.035, 24, 410000000000, 4.50, 0.015 UNION ALL
    SELECT 'S010102030000', 0.052, 6,  610000000000, 2.20, 0.010 UNION ALL
    SELECT 'S010102040000', 0.025, 1,  290000000000, 1.80, 0.005 UNION ALL
    SELECT 'S010201000000', 0.034, 24, 400000000000, 5.00, 0.020 UNION ALL
    SELECT 'S010202010000', 0.017, 60, 180000000000, 3.50, 0.015 UNION ALL
    -- 负债侧
    SELECT 'S020101010100', 0.218, 1,  2460000000000, 1.00, 0.030 UNION ALL
    SELECT 'S020101010200', 0.184, 24, 2080000000000, 3.50, 0.025 UNION ALL
    SELECT 'S020101020100', 0.101, 1,  1140000000000, 0.50, 0.020
) t
WHERE t.node_code = n.node_code
  AND s.scheme_code = 'SCS_2026' AND s.is_deleted = 0
  AND n.is_deleted = 0;

-- 更新节点配置计数
UPDATE prcp_sim_scheme s
SET config_node_count = (
    SELECT COUNT(*) FROM prcp_sim_scheme_node n
    WHERE n.scheme_id = s.id AND n.is_deleted = 0
)
WHERE s.scheme_code = 'SCS_2026';

-- 5. 创建测算运行实例
INSERT IGNORE INTO prcp_sim_run
    (sim_scheme_id, sim_scheme_code, base_data_date, month_count, target_data_date, status, total_nodes, model_id, model_version_id, created_by, updated_by)
SELECT
    s.id, 'SCS_2026', '2025-12-01', 24, '2027-11-01', 'PENDING', 15,
    (SELECT id FROM prcp_model WHERE model_code='NLS_REG' AND is_deleted=0 LIMIT 1),
    (SELECT v.id FROM prcp_model_version v JOIN prcp_model m ON v.model_id=m.id
     WHERE m.model_code='NLS_REG' AND v.version_code='V1_BASELINE' AND m.is_deleted=0 AND v.is_deleted=0 LIMIT 1),
    1, 1
FROM prcp_sim_scheme s
WHERE s.scheme_code='SCS_2026' AND s.is_deleted=0
  AND NOT EXISTS (SELECT 1 FROM prcp_sim_run r WHERE r.sim_scheme_id=s.id AND r.is_deleted=0);

-- 6. 铺底 metric_coefficient (5 指标 × 16 月 = 80 条)
-- metric_type: ALLOCATION (占比), GROWTH_RATE (增长率), INTEREST_RATE (利率)
-- 5 指标 × 4 类型 × 4 月 = 80 (简化演示: 5 指标 × 16 月 = 80)

-- 先清理旧铺底
UPDATE prcp_metric_coefficient
SET is_deleted = 1
WHERE scheme_code = 'ZX_COA' AND metric_code IN ('REG_LCR','REG_NSFR','REG_EVE','REG_CET1','REG_ROE');

-- 插入 5 指标 × 16 月 (M0=基期 + M1-M15)
INSERT INTO prcp_metric_coefficient
    (id, scheme_id, scheme_code, node_id, node_code, metric_type, metric_code, data_date,
     current_value, y1_value, y2_value, y3_value, y4_value, y5_value, unit, description, status, created_by, updated_by)
SELECT
    CONCAT('ZX_COA-', n.node_code, '-', k.kpi_code, '-', d.date_str),
    (SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0 LIMIT 1),
    'ZX_COA',
    n.id, n.node_code,
    'BASE_PARAM', k.kpi_code,
    d.date_str,
    -- current_value (基期值): LCR 147% / NSFR 104% / EVE 10% / CET1 9% / ROE 9.6%
    CASE k.kpi_code
        WHEN 'REG_LCR'  THEN 147.29
        WHEN 'REG_NSFR' THEN 104.52
        WHEN 'REG_EVE'  THEN 10.54
        WHEN 'REG_CET1' THEN 8.98
        WHEN 'REG_ROE'  THEN 9.61
    END,
    -- y1_value (未来1年): LCR 稳定, NSFR +0.5, EVE -0.5, CET1 +0.3, ROE +0.4
    CASE k.kpi_code
        WHEN 'REG_LCR'  THEN 145.0
        WHEN 'REG_NSFR' THEN 105.0
        WHEN 'REG_EVE'  THEN 10.0
        WHEN 'REG_CET1' THEN 9.3
        WHEN 'REG_ROE'  THEN 10.0
    END,
    CASE k.kpi_code
        WHEN 'REG_LCR'  THEN 140.0
        WHEN 'REG_NSFR' THEN 105.5
        WHEN 'REG_EVE'  THEN 9.5
        WHEN 'REG_CET1' THEN 9.5
        WHEN 'REG_ROE'  THEN 10.3
    END,
    CASE k.kpi_code
        WHEN 'REG_LCR'  THEN 138.0
        WHEN 'REG_NSFR' THEN 106.0
        WHEN 'REG_EVE'  THEN 9.0
        WHEN 'REG_CET1' THEN 9.7
        WHEN 'REG_ROE'  THEN 10.5
    END,
    CASE k.kpi_code
        WHEN 'REG_LCR'  THEN 135.0
        WHEN 'REG_NSFR' THEN 106.5
        WHEN 'REG_EVE'  THEN 8.5
        WHEN 'REG_CET1' THEN 9.9
        WHEN 'REG_ROE'  THEN 10.7
    END,
    CASE k.kpi_code
        WHEN 'REG_LCR'  THEN 133.0
        WHEN 'REG_NSFR' THEN 107.0
        WHEN 'REG_EVE'  THEN 8.0
        WHEN 'REG_CET1' THEN 10.0
        WHEN 'REG_ROE'  THEN 10.9
    END,
    'PERCENT',
    CONCAT('铺底 - ', k.kpi_code, ' @ ', d.date_str),
    'ACTIVE', 1, 1
FROM prcp_coa_node n
CROSS JOIN prcp_kpi_definition k ON TRUE
CROSS JOIN (
    SELECT '2025-12-31' AS date_str UNION ALL SELECT '2026-01-31' UNION ALL SELECT '2026-02-28'
    UNION ALL SELECT '2026-03-31' UNION ALL SELECT '2026-04-30' UNION ALL SELECT '2026-05-31'
    UNION ALL SELECT '2026-06-30' UNION ALL SELECT '2026-07-31' UNION ALL SELECT '2026-08-31'
    UNION ALL SELECT '2026-09-30' UNION ALL SELECT '2026-10-31' UNION ALL SELECT '2026-11-30'
    UNION ALL SELECT '2026-12-31' UNION ALL SELECT '2027-01-31' UNION ALL SELECT '2027-02-28'
    UNION ALL SELECT '2027-03-31'
) d
WHERE n.scheme_id = (SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0)
  AND n.is_deleted = 0
  AND k.scheme_id = (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_REG_2026' AND is_deleted=0)
  AND k.kpi_code IN ('REG_LCR','REG_NSFR','REG_EVE','REG_CET1','REG_ROE')
  AND k.is_deleted = 0
  AND n.id IS NOT NULL;  -- 跳过没找到节点的行

-- 验证
SELECT '====== 03_seed_sim_scheme.sql 完成 ======' AS status;
SELECT
    (SELECT COUNT(*) FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0) AS coa_scheme_count,
    (SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id=(SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0) AND is_deleted=0) AS coa_node_count,
    (SELECT COUNT(*) FROM prcp_sim_scheme WHERE scheme_code='SCS_2026' AND is_deleted=0) AS sim_scheme_count,
    (SELECT COUNT(*) FROM prcp_sim_scheme_node WHERE scheme_id=(SELECT id FROM prcp_sim_scheme WHERE scheme_code='SCS_2026' AND is_deleted=0) AND is_deleted=0) AS sim_node_count,
    (SELECT COUNT(*) FROM prcp_sim_run WHERE sim_scheme_code='SCS_2026' AND is_deleted=0) AS sim_run_count,
    (SELECT COUNT(*) FROM prcp_metric_coefficient WHERE scheme_code='ZX_COA' AND is_deleted=0) AS metric_coefficient_count;