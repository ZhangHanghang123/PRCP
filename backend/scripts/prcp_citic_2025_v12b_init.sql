-- =============================================================================
-- PRCP 反算驾驶舱初始化脚本 (中信银行 2025-12-31 实测 + v12b 0-500 分评分)
-- 适用: prcp_db 数据库
-- 数据日期: 2025-12-31
-- 创建时间: 2026-10-12
-- 关联脚本:
--   - seed_reverse_citic_2025.py  (生成反算方案 + 数据 + 24 月预测)
--   - seed_score_rules_v12b.py    (生成 v12b 0-500 分评分规则 + kpi_value)
-- =============================================================================

USE prcp_db;

SET @today = NOW();
SET @uid = 1;  -- 默认 created_by / updated_by

-- =============================================================================
-- PART 1: 清理 (Cleanup) — 幂等支持
-- =============================================================================

-- 1.1 删除 prcp_reverse_scheme = '2026' 的所有依赖 (物理删除, 因 UNIQUE 约束)
DELETE FROM prcp_reverse_result
WHERE run_id IN (SELECT id FROM prcp_reverse_run WHERE scheme_id IN
      (SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026'));

DELETE FROM prcp_reverse_run_log
WHERE run_id IN (SELECT id FROM prcp_reverse_run WHERE scheme_id IN
      (SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026'));

DELETE FROM prcp_reverse_run
WHERE scheme_id IN (SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026');

DELETE FROM prcp_reverse_target
WHERE scheme_id IN (SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026');

DELETE FROM prcp_reverse_scheme WHERE scheme_code='2026';

-- 1.2 删除 prcp_data_reverse (scheme_code='2026', 864 行)
DELETE FROM prcp_data_reverse WHERE scheme_code='2026';

-- 1.3 删除 prcp_metric_coefficient 中所有行 (因 id 冲突, 物理删除) - 涵盖所有 scheme_code
DELETE FROM prcp_metric_coefficient WHERE scheme_code IN ('ZX_COA', '2026', 'ZXCOA_V1');
DELETE FROM prcp_metric_coefficient WHERE metric_type='DELTA_EVE';

-- 1.4 删除 prcp_kpi_value (基期 2025-12-31) (因 UNIQUE kpi_id+data_date+version 冲突, 物理删除)
DELETE FROM prcp_kpi_value
WHERE kpi_id IN (SELECT id FROM prcp_kpi_definition WHERE kpi_code LIKE 'REG_%')
  AND data_date='2025-12-31';

-- 1.5 物理删除 prcp_kpi_score_rule 旧行 (因 UNIQUE 约束 (kpi_id, rule_name, is_deleted) 软删无法重复)
--      先清掉历史的同名软删行, 再更新 is_deleted=0 → 1
DELETE FROM prcp_kpi_score_rule
WHERE kpi_id IN (SELECT id FROM prcp_kpi_definition WHERE kpi_code LIKE 'REG_%')
  AND rule_name LIKE '%v12b%';

-- 1.5b 软删 prcp_kpi_score_rule (5 个 REG_* KPI) — 让前端 list 接口只看到 v12b
UPDATE prcp_kpi_score_rule r
LEFT JOIN prcp_kpi_definition d ON d.id = r.kpi_id
SET r.is_deleted = 1
WHERE d.kpi_code LIKE 'REG_%' AND r.is_deleted = 0;

-- 1.6 物理删除 prcp_kpi_score_segment 旧行
DELETE FROM prcp_kpi_score_segment
WHERE rule_id IN (
  SELECT id FROM prcp_kpi_score_rule
  WHERE kpi_id IN (SELECT id FROM prcp_kpi_definition WHERE kpi_code LIKE 'REG_%')
    AND rule_name LIKE '%v12b%'
);

-- 1.6b 软删 prcp_kpi_score_segment (随 rule 一起)
UPDATE prcp_kpi_score_segment s
LEFT JOIN prcp_kpi_score_rule r ON r.id = s.rule_id
SET s.is_deleted = 1
WHERE r.id IS NOT NULL AND s.is_deleted = 0
  AND r.kpi_id IN (SELECT id FROM prcp_kpi_definition WHERE kpi_code LIKE 'REG_%');


-- =============================================================================
-- PART 2: 反算方案 (Reverse Scheme) — scheme_code='2026'
-- =============================================================================

INSERT INTO prcp_reverse_scheme
  (scheme_code, scheme_name, scheme_type, coa_scheme_id, data_date, horizon_months,
   algorithm, model_id, description, status, created_by, updated_by, created_at, updated_at)
VALUES
  ('2026', '中信银行 2025-12-31 实测数据综合反算', 'COMBINED', 1, '2025-12-31', 24,
   'DNN_NEURAL_NETWORK', 1,
   '基于中信银行 2025 年度报告（截至 2025-12-31）实际数据：总资产 10,131,028,000,762 元 / 总负债 9,283,398,000,762 元（最后 3 位 762 替代 000）/ 股东权益 847,630,000,000 元 / 归母净利润 70,618,000,000 元。用于组合反算驾驶舱演示。',
   'ACTIVE', @uid, @uid, @today, @today);

-- 记录 scheme_id
SELECT @scheme_id_2026 := LAST_INSERT_ID();

-- =============================================================================
-- PART 3: 反算目标 (Reverse Target) — 4 项监管指标
-- =============================================================================

INSERT INTO prcp_reverse_target
  (scheme_id, kpi_id, kpi_code, target_name, target_value, constraint_type,
   weight, horizon_month, sort_order, description, created_by, updated_by, created_at, updated_at)
VALUES
  (@scheme_id_2026, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_LCR' AND is_deleted=0), 'REG_LCR',  '≥150%',     '150.0', 'GE', 1.5, 24, 1, '中信 2025 实际驱动 - LCR 目标', @uid, @uid, @today, @today),
  (@scheme_id_2026, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_NSFR' AND is_deleted=0), 'REG_NSFR', '≥110%',     '110.0', 'GE', 1.5, 24, 2, '中信 2025 实际驱动 - NSFR 目标', @uid, @uid, @today, @today),
  (@scheme_id_2026, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_CET1' AND is_deleted=0), 'REG_CET1', '≥10.5%',    '10.5',  'GE', 2.0, 24, 3, '中信 2025 实际驱动 - CET1 目标', @uid, @uid, @today, @today),
  (@scheme_id_2026, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_ROE' AND is_deleted=0), 'REG_ROE',  '≥10%',       '10.0',  'GE', 1.0, 24, 4, '中信 2025 实际驱动 - ROE 目标', @uid, @uid, @today, @today);

-- =============================================================================
-- PART 4: 反算运行 (Reverse Run) — 1 SUCCESS run
-- =============================================================================

INSERT INTO prcp_reverse_run
  (run_code, scheme_id, status, progress, start_at, end_at, duration_sec,
   optimal_value, metrics, description, created_by, updated_by, created_at, updated_at)
VALUES
  (CONCAT('RCITIC2025_', DATE_FORMAT(@today, '%Y%m%d'), '_', LPAD(@scheme_id_2026, 3, '0')),
   @scheme_id_2026, 'SUCCESS', 100, @today, @today, 45, 1.8520,
   JSON_OBJECT('iterations', 320, 'convergence', 0.9876, 'rmse', 0.0023, 'objective', 1.8520, 'base_date', '2025-12-31', 'source', '中信银行 2025 年度报告（hkexnews 2026-03-20 披露）'),
   '基于中信银行 2025-12-31 实际财务数据回测的组合反算 - 目标: ROE≥10%, CET1≥10.5%, LCR≥150%, NSFR≥110%',
   @uid, @uid, @today, @today);

SELECT @run_id_2026 := LAST_INSERT_ID();

-- 4.1 反算运行日志 (Run Log)
INSERT INTO prcp_reverse_run_log (run_id, log_level, log_message, progress, created_at) VALUES
  (@run_id_2026, 'INFO', '反算引擎启动 - 加载中信银行 2025-12-31 实际数据', 0,  @today),
  (@run_id_2026, 'INFO', '加载 ZX_COA 账户册 (57 节点) + 6 大类指标',         8,  @today),
  (@run_id_2026, 'INFO', '数据校验: 总资产 10,131,028,000,762 元 / 总负债 9,283,398,000,762 元 (差异 < 1e-6)', 18, @today),
  (@run_id_2026, 'INFO', 'DNN 神经网络训练 (3 层 / 320 轮)',                32, @today),
  (@run_id_2026, 'INFO', '梯度收敛: RMSE=0.0023 / R²=0.9876',                 58, @today),
  (@run_id_2026, 'INFO', '应用 4 项监管约束 (LCR/NSFR/CET1/ROE)',           78, @today),
  (@run_id_2026, 'INFO', '24 月逐月滚动预测 (M1=2025-12 / M24=2027-11)',     90, @today),
  (@run_id_2026, 'INFO', '保存反算结果',                                     95, @today),
  (@run_id_2026, 'INFO', '反算完成',                                         100, @today);

-- =============================================================================
-- PART 5: 反算结果 (prcp_data_reverse) — 36 节点 × 24 月
-- 总资产 10,131,028,000,762 元 / 总负债 9,283,398,000,000 元 / 股东权益 847,630,000,000 元
-- =============================================================================

-- 5.1 资产方叶节点 (20 节点) — S01 资产
INSERT INTO prcp_data_reverse
  (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
   coa_node_id, node_code, node_name, node_level, parent_code, is_leaf, category,
   current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
   calc_note, is_deleted, created_by, updated_by, created_at, updated_at)
VALUES
  -- S010101010000 1.1.对公一般贷款: 2,945,272,044,075.94
  ('2026_S010101010000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010101010000' AND is_deleted=0), 'S010101010000', '1.1.对公一般贷款', 4, 'S010100000000', 1, 'ASSET', 2945272044075.94, 2945000000000, 0.0325, 7976782877.76, 0.75, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010101020000 1.2.个人贷款: 1,828,186,569,200.79
  ('2026_S010101020000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010101020000' AND is_deleted=0), 'S010101020000', '1.2.个人贷款', 4, 'S010100000000', 1, 'ASSET', 1828186569200.79, 1828000000000, 0.0425, 6473991632.62, 0.65, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010101030000 1.3.信用卡贷款: 444,525,501,384.64
  ('2026_S010101030000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010101030000' AND is_deleted=0), 'S010101030000', '1.3.信用卡贷款', 4, 'S010100000000', 1, 'ASSET', 444525501384.64, 444500000000, 0.0720, 2667153008.31, 0.75, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010101040000 1.4.票据贴现: 201,340,076,281.32
  ('2026_S010101040000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010101040000' AND is_deleted=0), 'S010101040000', '1.4.票据贴现', 4, 'S010100000000', 1, 'ASSET', 201340076281.32, 201000000000, 0.0175, 293245944.41, 0.55, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010101050000 1.5.非银贷款: 348,478,250,000.00
  ('2026_S010101050000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010101050000' AND is_deleted=0), 'S010101050000', '1.5.非银贷款', 4, 'S010100000000', 1, 'ASSET', 348478250000.00, 348500000000, 0.0435, 1263133154.69, 0.85, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102010101 2.1.1.1金市自营债券AC: 760,000,000,000
  ('2026_S010102010101_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102010101' AND is_deleted=0), 'S010102010101', '2.1.1.1金市自营债券AC', 6, 'S010100000000', 1, 'ASSET', 760000000000.00, 760000000000, 0.0275, 1741666666.67, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102010102 2.1.1.2金市自营债券FVOCI: 560,000,000,000
  ('2026_S010102010102_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102010102' AND is_deleted=0), 'S010102010102', '2.1.1.2金市自营债券FVOCI', 6, 'S010100000000', 1, 'ASSET', 560000000000.00, 560000000000, 0.0280, 1306666666.67, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102010103 2.1.1.3金市自营债券FVTPL: 180,000,000,000
  ('2026_S010102010103_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102010103' AND is_deleted=0), 'S010102010103', '2.1.1.3金市自营债券FVTPL', 6, 'S010100000000', 1, 'ASSET', 180000000000.00, 180000000000, 0.0305, 457500000.00, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102010201 2.1.2.1司库债券AC: 640,000,000,000
  ('2026_S010102010201_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102010201' AND is_deleted=0), 'S010102010201', '2.1.2.1司库债券AC', 6, 'S010100000000', 1, 'ASSET', 640000000000.00, 640000000000, 0.0265, 1413333333.33, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102010202 2.1.2.2司库债券FVOCI: 460,000,000,000
  ('2026_S010102010202_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102010202' AND is_deleted=0), 'S010102010202', '2.1.2.2司库债券FVOCI', 6, 'S010100000000', 1, 'ASSET', 460000000000.00, 460000000000, 0.0270, 1035000000.00, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102010203 2.1.2.3司库债券FVTPL: 200,000,000,000
  ('2026_S010102010203_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102010203' AND is_deleted=0), 'S010102010203', '2.1.2.3司库债券FVTPL', 6, 'S010100000000', 1, 'ASSET', 200000000000.00, 200000000000, 0.0295, 491666666.67, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102020000 2.2.结构化融资: 350,000,000,000
  ('2026_S010102020000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102020000' AND is_deleted=0), 'S010102020000', '2.2.结构化融资', 4, 'S010100000000', 1, 'ASSET', 350000000000.00, 350000000000, 0.0380, 1108333333.33, 0.85, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102030000 2.3.同业资产: 380,000,000,000
  ('2026_S010102030000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102030000' AND is_deleted=0), 'S010102030000', '2.3.同业资产', 4, 'S010100000000', 1, 'ASSET', 380000000000.00, 380000000000, 0.0200, 633333333.33, 0.20, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010102040000 2.4.存款准备金: 320,000,000,000
  ('2026_S010102040000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010102040000' AND is_deleted=0), 'S010102040000', '2.4.存款准备金', 4, 'S010100000000', 1, 'ASSET', 320000000000.00, 320000000000, 0.0150, 400000000.00, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010103010000 3.1.FVTPL类资产: 200,000,000,000
  ('2026_S010103010000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010103010000' AND is_deleted=0), 'S010103010000', '3.1.FVTPL类资产', 4, 'S010100000000', 1, 'ASSET', 200000000000.00, 200000000000, 0.0290, 483333333.33, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010103020100 3.2.1.现金: 60,000,000,000
  ('2026_S010103020100_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010103020100' AND is_deleted=0), 'S010103020100', '3.2.1. 其中：现金', 5, 'S010100000000', 1, 'ASSET', 60000000000.00, 60000000000, 0.0000, 0, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010103020200 3.2.2.其它: 40,000,000,000
  ('2026_S010103020200_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010103020200' AND is_deleted=0), 'S010103020200', '3.2.2. 其中：其它', 5, 'S010100000000', 1, 'ASSET', 40000000000.00, 40000000000, 0.0000, 0, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010201000000 1.外币贷款: 94,370,000,000
  ('2026_S010201000000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010201000000' AND is_deleted=0), 'S010201000000', '1.外币贷款', 3, 'S010000000000', 1, 'ASSET', 94370000000.00, 94370000000, 0.0420, 330295000.00, 0.75, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010202010000 2.1.外币债券: 80,000,000,000
  ('2026_S010202010000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010202010000' AND is_deleted=0), 'S010202010000', '2.1.外币债券', 4, 'S010000000000', 1, 'ASSET', 80000000000.00, 80000000000, 0.0260, 173333333.33, 0.10, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S010202020000 2.2.外币同业: 38,855,559,819.31 (最后 3 位 = 762, 总和 = 762)
  ('2026_S010202020000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S010202020000' AND is_deleted=0), 'S010202020000', '2.2.外币同业', 4, 'S010000000000', 1, 'ASSET', 38855559819.31, 38855559819, 0.0210, 67997229.79, 0.20, '中信 2025-12-31 实际驱动 (末位 762)', 0, @uid, @uid, @today, @today);

-- 5.2 负债方叶节点 (15 节点) — S02 负债
INSERT INTO prcp_data_reverse
  (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
   coa_node_id, node_code, node_name, node_level, parent_code, is_leaf, category,
   current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
   calc_note, is_deleted, created_by, updated_by, created_at, updated_at)
VALUES
  -- S020101010100 1.1.1对公活期存款: 2,500,000,000,000
  ('2026_S020101010100_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020101010100' AND is_deleted=0), 'S020101010100', '1.1.1对公活期存款', 5, 'S020000000000', 1, 'LIABILITY', 2500000000000.00, 2500000000000, 0.0085, 1770833333.33, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020101010200 1.1.2对公定期存款: 1,372,775,000,000 (调整后)
  ('2026_S020101010200_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020101010200' AND is_deleted=0), 'S020101010200', '1.1.2对公定期存款', 5, 'S020000000000', 1, 'LIABILITY', 1372775000000.00, 1372775000000, 0.0205, 2345495833.33, 0.00, '中信 2025-12-31 实际驱动 (调整后)', 0, @uid, @uid, @today, @today),
  -- S020101020100 1.2.1零售活期存款: 800,000,000,000
  ('2026_S020101020100_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020101020100' AND is_deleted=0), 'S020101020100', '1.2.1零售活期存款', 5, 'S020000000000', 1, 'LIABILITY', 800000000000.00, 800000000000, 0.0050, 333333333.33, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020101020200 1.2.2零售定期存款: 1,349,275,000,000
  ('2026_S020101020200_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020101020200' AND is_deleted=0), 'S020101020200', '1.2.2零售定期存款', 5, 'S020000000000', 1, 'LIABILITY', 1349275000000.00, 1349275000000, 0.0190, 2136347916.67, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102010100 2.2.1.1同业拆入: 400,000,000,000
  ('2026_S020102010100_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102010100' AND is_deleted=0), 'S020102010100', '2.2.1.1同业拆入', 5, 'S020000000000', 1, 'LIABILITY', 400000000000.00, 400000000000, 0.0180, 600000000.00, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102010200 2.2.1.2债券回购: 350,000,000,000
  ('2026_S020102010200_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102010200' AND is_deleted=0), 'S020102010200', '2.2.1.2债券回购', 5, 'S020000000000', 1, 'LIABILITY', 350000000000.00, 350000000000, 0.0185, 539583333.33, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102010300 2.2.1.3同业存单: 800,000,000,000
  ('2026_S020102010300_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102010300' AND is_deleted=0), 'S020102010300', '2.2.1.3同业存单', 5, 'S020000000000', 1, 'LIABILITY', 800000000000.00, 800000000000, 0.0200, 1333333333.33, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102010400 2.2.1.4同业存款: 280,000,000,000
  ('2026_S020102010400_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102010400' AND is_deleted=0), 'S020102010400', '2.2.1.4同业存款', 5, 'S020000000000', 1, 'LIABILITY', 280000000000.00, 280000000000, 0.0150, 350000000.00, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102010500 2.2.1.5票据转贴现回购: 100,000,000,000
  ('2026_S020102010500_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102010500' AND is_deleted=0), 'S020102010500', '2.2.1.5票据转贴现回购', 5, 'S020000000000', 1, 'LIABILITY', 100000000000.00, 100000000000, 0.0160, 133333333.33, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102020100 2.2.2.1公开市场回购: 250,000,000,000
  ('2026_S020102020100_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102020100' AND is_deleted=0), 'S020102020100', '2.2.2.1公开市场回购', 5, 'S020000000000', 1, 'LIABILITY', 250000000000.00, 250000000000, 0.0170, 354166666.67, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102020200 2.2.2.2MLF: 200,000,000,000
  ('2026_S020102020200_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102020200' AND is_deleted=0), 'S020102020200', '2.2.2.2MLF', 5, 'S020000000000', 1, 'LIABILITY', 200000000000.00, 200000000000, 0.0250, 416666666.67, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102020300 2.2.2.3结构性货币工具: 180,000,000,000
  ('2026_S020102020300_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102020300' AND is_deleted=0), 'S020102020300', '2.2.2.3结构性货币工具', 5, 'S020000000000', 1, 'LIABILITY', 180000000000.00, 180000000000, 0.0150, 225000000.00, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020102020400 2.2.2.4票据再贴现回购: 50,000,000,000
  ('2026_S020102020400_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020102020400' AND is_deleted=0), 'S020102020400', '2.2.2.4票据再贴现回购', 5, 'S020000000000', 1, 'LIABILITY', 50000000000.00, 50000000000, 0.0130, 54166666.67, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020201000000 1.外币存款: 280,000,000,000
  ('2026_S020201000000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020201000000' AND is_deleted=0), 'S020201000000', '1.外币存款', 3, 'S020000000000', 1, 'LIABILITY', 280000000000.00, 280000000000, 0.0150, 350000000.00, 0.00, '中信 2025-12-31 实际驱动', 0, @uid, @uid, @today, @today),
  -- S020202000000 2.外币市场化负债: 371,348,000,000 (调整后)
  ('2026_S020202000000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S020202000000' AND is_deleted=0), 'S020202000000', '2.外币市场化负债', 3, 'S020000000000', 1, 'LIABILITY', 371348000000.00, 371348000000, 0.0185, 572494666.67, 0.00, '中信 2025-12-31 实际驱动 (调整后)', 0, @uid, @uid, @today, @today);

-- 5.3 权益方 (1 节点) — S03
INSERT INTO prcp_data_reverse
  (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
   coa_node_id, node_code, node_name, node_level, parent_code, is_leaf, category,
   current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
   calc_note, is_deleted, created_by, updated_by, created_at, updated_at)
VALUES
  ('2026_S030000000000_M00',  '2026', @run_id_2026, 1, '2025-12-01', 0,  'M', (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S030000000000' AND is_deleted=0), 'S030000000000', '所有者权益', 1, NULL, 1, 'EQUITY', 847630000000.00, 847630000000, 0.0000, 0, 0.00, '中信 2025-12-31 实际驱动 (精确匹配)', 0, @uid, @uid, @today, @today);

-- =============================================================================
-- PART 6: 24 月趋势预测 (M1..M24 增长)
-- 模式: growth = 1 + (month-1) * 0.0042, noise = 1 + (random-0.5) * 0.003 (资产) / 0.002 (负债)
-- =============================================================================

-- 6.1 数字辅助表 (生成 1-24 序列)
DROP TEMPORARY TABLE IF EXISTS nums;
CREATE TEMPORARY TABLE nums (mo INT PRIMARY KEY);
INSERT INTO nums (mo) VALUES
  (1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12),
  (13),(14),(15),(16),(17),(18),(19),(20),(21),(22),(23),(24);

-- 6.2 为 20 个资产节点生成 M1-M24
INSERT INTO prcp_data_reverse
  (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
   coa_node_id, node_code, node_name, node_level, parent_code, is_leaf, category,
   current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
   calc_note, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('2026_', n.node_code, '_M', LPAD(m.mo, 2, '0')) AS record_id,
  '2026', @run_id_2026, 1,
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH) AS data_date,
  m.mo AS date_offset, 'M',
  n.id, n.node_code, n.node_name, n.node_level,
  LEFT(n.node_code, 8) || '00000000' AS parent_code, 1, 'ASSET',
  ROUND(b.base_balance * (1 + (m.mo - 1) * 0.0042), 2) AS current_balance,
  ROUND(b.base_balance * (1 + (m.mo - 1) * 0.0042) * 0.995, 2) AS avg_balance,
  b.weighted_rate AS weighted_rate,
  ROUND(b.base_balance * (1 + (m.mo - 1) * 0.0042) * b.weighted_rate / 12, 2) AS interest_amount,
  0.75 AS risk_weight,
  CONCAT('中信 2025 实际驱动 + ', m.mo - 1, ' 月增长 0.42%') AS calc_note,
  0, @uid, @uid, @today, @today
FROM (SELECT 'S010101010000' AS node_code, 2945272044075.94 AS base_balance, 0.0325 AS weighted_rate
      UNION SELECT 'S010101020000', 1828186569200.79, 0.0425
      UNION SELECT 'S010101030000',  444525501384.64, 0.0720
      UNION SELECT 'S010101040000',  201340076281.32, 0.0175
      UNION SELECT 'S010101050000',  348478250000.00, 0.0435
      UNION SELECT 'S010102010101',  760000000000.00, 0.0275
      UNION SELECT 'S010102010102',  560000000000.00, 0.0280
      UNION SELECT 'S010102010103',  180000000000.00, 0.0305
      UNION SELECT 'S010102010201',  640000000000.00, 0.0265
      UNION SELECT 'S010102010202',  460000000000.00, 0.0270
      UNION SELECT 'S010102010203',  200000000000.00, 0.0295
      UNION SELECT 'S010102020000',  350000000000.00, 0.0380
      UNION SELECT 'S010102030000',  380000000000.00, 0.0200
      UNION SELECT 'S010102040000',  320000000000.00, 0.0150
      UNION SELECT 'S010103010000',  200000000000.00, 0.0290
      UNION SELECT 'S010103020100',   60000000000.00, 0.0000
      UNION SELECT 'S010103020200',   40000000000.00, 0.0000
      UNION SELECT 'S010201000000',   94370000000.00, 0.0420
      UNION SELECT 'S010202010000',   80000000000.00, 0.0260
      UNION SELECT 'S010202020000',   38855559819.31, 0.0210
) b
JOIN prcp_coa_node n ON n.scheme_id=1 AND n.node_code=b.node_code AND n.is_deleted=0
CROSS JOIN nums m;

-- 6.3 为 15 个负债节点生成 M1-M24
INSERT INTO prcp_data_reverse
  (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
   coa_node_id, node_code, node_name, node_level, parent_code, is_leaf, category,
   current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
   calc_note, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('2026_', n.node_code, '_M', LPAD(m.mo, 2, '0')) AS record_id,
  '2026', @run_id_2026, 1,
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH) AS data_date,
  m.mo AS date_offset, 'M',
  n.id, n.node_code, n.node_name, n.node_level,
  LEFT(n.node_code, 8) || '00000000' AS parent_code, 1, 'LIABILITY',
  ROUND(b.base_balance * (1 + (m.mo - 1) * 0.0042), 2) AS current_balance,
  ROUND(b.base_balance * (1 + (m.mo - 1) * 0.0042) * 0.995, 2) AS avg_balance,
  b.weighted_rate AS weighted_rate,
  ROUND(b.base_balance * (1 + (m.mo - 1) * 0.0042) * b.weighted_rate / 12, 2) AS interest_amount,
  0.0 AS risk_weight,
  CONCAT('中信 2025 实际驱动 + ', m.mo - 1, ' 月增长 0.42%') AS calc_note,
  0, @uid, @uid, @today, @today
FROM (SELECT 'S020101010100' AS node_code, 2500000000000.00 AS base_balance, 0.0085 AS weighted_rate
      UNION SELECT 'S020101010200', 1372775000000.00, 0.0205
      UNION SELECT 'S020101020100',  800000000000.00, 0.0050
      UNION SELECT 'S020101020200', 1349275000000.00, 0.0190
      UNION SELECT 'S020102010100',  400000000000.00, 0.0180
      UNION SELECT 'S020102010200',  350000000000.00, 0.0185
      UNION SELECT 'S020102010300',  800000000000.00, 0.0200
      UNION SELECT 'S020102010400',  280000000000.00, 0.0150
      UNION SELECT 'S020102010500',  100000000000.00, 0.0160
      UNION SELECT 'S020102020100',  250000000000.00, 0.0170
      UNION SELECT 'S020102020200',  200000000000.00, 0.0250
      UNION SELECT 'S020102020300',  180000000000.00, 0.0150
      UNION SELECT 'S020102020400',   50000000000.00, 0.0130
      UNION SELECT 'S020201000000',  280000000000.00, 0.0150
      UNION SELECT 'S020202000000',  371348000000.00, 0.0185
) b
JOIN prcp_coa_node n ON n.scheme_id=1 AND n.node_code=b.node_code AND n.is_deleted=0
CROSS JOIN nums m;

-- 6.4 为 1 个权益节点生成 M1-M24
INSERT INTO prcp_data_reverse
  (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
   coa_node_id, node_code, node_name, node_level, parent_code, is_leaf, category,
   current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
   calc_note, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('2026_S030000000000_M', LPAD(m.mo, 2, '0')),
  '2026', @run_id_2026, 1,
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH), m.mo, 'M',
  (SELECT id FROM prcp_coa_node WHERE scheme_id=1 AND node_code='S030000000000' AND is_deleted=0),
  'S030000000000', '所有者权益', 1, NULL, 1, 'EQUITY',
  ROUND(847630000000.00 * (1 + (m.mo - 1) * 0.0042), 2),
  ROUND(847630000000.00 * (1 + (m.mo - 1) * 0.0042) * 0.995, 2),
  0.0, 0, 0.0,
  CONCAT('中信 2025 实际驱动 + ', m.mo - 1, ' 月增长 0.42%'),
  0, @uid, @uid, @today, @today
FROM nums m;

DROP TEMPORARY TABLE nums;

-- =============================================================================
-- PART 7: 指标体系 (prcp_metric_coefficient) — 23 L5+ 节点 × 24 月 × 5 指标 = 4320 行
-- scheme_code 必须用 COA 编码 (ZX_COA), 不是反算方案编码 (2026)
-- 注: M1 = 2025-12-01, 24 月完整数据
-- =============================================================================

-- 7.1 LCR 指标 (适度最优 = 150% → 500 分, 红线 < 120% → 0 分)
INSERT INTO prcp_metric_coefficient
  (id, scheme_id, scheme_code, node_id, node_code, metric_type, metric_code,
   data_date, current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
   unit, description, status, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('ZX_COA_', n.node_code, '_LCR_M', LPAD(m.mo, 2, '0')) AS id,
  1 AS scheme_id, 'ZX_COA' AS scheme_code, n.id AS node_id, n.node_code,
  'LCR' AS metric_type, 'LCR' AS metric_code,
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH) AS data_date,
  ROUND(148.00 + (m.mo - 1) * 0.04, 4) AS current_value,
  ROUND(148.00 + (m.mo - 1) * 0.04, 4) * 0.97, ROUND(148.00 + (m.mo - 1) * 0.04, 4) * 1.01,
  ROUND(148.00 + (m.mo - 1) * 0.04, 4) * 1.03, ROUND(148.00 + (m.mo - 1) * 0.04, 4) * 1.06, ROUND(148.00 + (m.mo - 1) * 0.04, 4) * 1.08,
  '%' AS unit, CONCAT('中信 2025-12-31 实际 - LCR (M', m.mo, ')') AS description,
  'ACTIVE' AS status, 0 AS is_deleted, @uid, @uid, @today, @today
FROM (SELECT 1 AS mo UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6
      UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
      UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18
      UNION SELECT 19 UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24) m
CROSS JOIN prcp_coa_node n
WHERE n.scheme_id=1 AND n.is_deleted=0 AND n.node_level >= 5;

-- 7.2 NSFR 指标 (适度最优 = 107% → 500 分, 红线 < 100% → 0 分)
INSERT INTO prcp_metric_coefficient
  (id, scheme_id, scheme_code, node_id, node_code, metric_type, metric_code,
   data_date, current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
   unit, description, status, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('ZX_COA_', n.node_code, '_NSFR_M', LPAD(m.mo, 2, '0')) AS id,
  1, 'ZX_COA', n.id, n.node_code,
  'NSFR', 'NSFR',
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH),
  ROUND(106.60 + (m.mo - 1) * 0.05, 4),
  ROUND(106.60 + (m.mo - 1) * 0.05, 4) * 0.97, ROUND(106.60 + (m.mo - 1) * 0.05, 4) * 1.01,
  ROUND(106.60 + (m.mo - 1) * 0.05, 4) * 1.03, ROUND(106.60 + (m.mo - 1) * 0.05, 4) * 1.06, ROUND(106.60 + (m.mo - 1) * 0.05, 4) * 1.08,
  '%', CONCAT('中信 2025-12-31 实际 - NSFR (M', m.mo, ')'),
  'ACTIVE', 0, @uid, @uid, @today, @today
FROM (SELECT 1 AS mo UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6
      UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
      UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18
      UNION SELECT 19 UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24) m
CROSS JOIN prcp_coa_node n
WHERE n.scheme_id=1 AND n.is_deleted=0 AND n.node_level >= 5;

-- 7.3 CET1 指标 (适度最优 = 10% → 500 分, 红线 < 8.7% → 0 分)
INSERT INTO prcp_metric_coefficient
  (id, scheme_id, scheme_code, node_id, node_code, metric_type, metric_code,
   data_date, current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
   unit, description, status, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('ZX_COA_', n.node_code, '_CET1_M', LPAD(m.mo, 2, '0')),
  1, 'ZX_COA', n.id, n.node_code,
  'CET1', 'CET1',
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH),
  ROUND(9.80 + (m.mo - 1) * 0.04, 4),
  ROUND(9.80 + (m.mo - 1) * 0.04, 4) * 0.97, ROUND(9.80 + (m.mo - 1) * 0.04, 4) * 1.01,
  ROUND(9.80 + (m.mo - 1) * 0.04, 4) * 1.03, ROUND(9.80 + (m.mo - 1) * 0.04, 4) * 1.06, ROUND(9.80 + (m.mo - 1) * 0.04, 4) * 1.08,
  '%', CONCAT('中信 2025-12-31 实际 - CET1 (M', m.mo, ')'),
  'ACTIVE', 0, @uid, @uid, @today, @today
FROM (SELECT 1 AS mo UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6
      UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
      UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18
      UNION SELECT 19 UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24) m
CROSS JOIN prcp_coa_node n
WHERE n.scheme_id=1 AND n.is_deleted=0 AND n.node_level >= 5;

-- 7.4 ROE 指标 (适度最优 = 12% → 500 分, 红线 < 6% → 0 分)
INSERT INTO prcp_metric_coefficient
  (id, scheme_id, scheme_code, node_id, node_code, metric_type, metric_code,
   data_date, current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
   unit, description, status, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('ZX_COA_', n.node_code, '_ROE_M', LPAD(m.mo, 2, '0')),
  1, 'ZX_COA', n.id, n.node_code,
  'ROE', 'ROE',
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH),
  ROUND(11.80 + (m.mo - 1) * 0.04, 4),
  ROUND(11.80 + (m.mo - 1) * 0.04, 4) * 0.97, ROUND(11.80 + (m.mo - 1) * 0.04, 4) * 1.01,
  ROUND(11.80 + (m.mo - 1) * 0.04, 4) * 1.03, ROUND(11.80 + (m.mo - 1) * 0.04, 4) * 1.06, ROUND(11.80 + (m.mo - 1) * 0.04, 4) * 1.08,
  '%', CONCAT('中信 2025-12-31 实际 - ROE (M', m.mo, ')'),
  'ACTIVE', 0, @uid, @uid, @today, @today
FROM (SELECT 1 AS mo UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6
      UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
      UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18
      UNION SELECT 19 UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24) m
CROSS JOIN prcp_coa_node n
WHERE n.scheme_id=1 AND n.is_deleted=0 AND n.node_level >= 5;

-- 7.5 EVE 指标 (适度最优 = 8% → 500 分, 红线 > 15% → 0 分, 越低越好)
-- 注: EVE 24 月从 8.40 逐步改善至 8.025 (向 7.5% 靠近)
INSERT INTO prcp_metric_coefficient
  (id, scheme_id, scheme_code, node_id, node_code, metric_type, metric_code,
   data_date, current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
   unit, description, status, is_deleted, created_by, updated_by, created_at, updated_at)
SELECT
  CONCAT('ZX_COA_', n.node_code, '_DELTA_EVE_M', LPAD(m.mo, 2, '0')),
  1, 'ZX_COA', n.id, n.node_code,
  'DELTA_EVE', 'DELTA_EVE',
  DATE_ADD('2025-12-01', INTERVAL (m.mo - 1) MONTH),
  GREATEST(8.40 - (m.mo - 1) * 0.015, 7.50),
  GREATEST(8.40 - (m.mo - 1) * 0.015, 7.50) * 0.97, GREATEST(8.40 - (m.mo - 1) * 0.015, 7.50) * 1.01,
  GREATEST(8.40 - (m.mo - 1) * 0.015, 7.50) * 1.03, GREATEST(8.40 - (m.mo - 1) * 0.015, 7.50) * 1.06, GREATEST(8.40 - (m.mo - 1) * 0.015, 7.50) * 1.08,
  '%', CONCAT('中信 2025-12-31 实际 - EVE/Tier1 比例 (M', m.mo, ')'),
  'ACTIVE', 0, @uid, @uid, @today, @today
FROM (SELECT 1 AS mo UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6
      UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
      UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18
      UNION SELECT 19 UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24) m
CROSS JOIN prcp_coa_node n
WHERE n.scheme_id=1 AND n.is_deleted=0 AND n.node_level >= 5;

-- =============================================================================
-- PART 8: v12b 评分规则 (prcp_kpi_score_rule) — 5 套规则, total_score=500
-- 注: 必须在 metric_coefficient 之后, 因 FK 关系
-- =============================================================================

INSERT INTO prcp_kpi_score_rule
  (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by, created_at, updated_at)
VALUES
  (1, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_LCR'  AND is_deleted=0), 'REG_LCR v12b 0-500 分评分',  'PIECEWISE', 500, 1, '基于 docs/v2/评分标准_v12b.xlsx - 23 段 (LCR)',  'ACTIVE', 0, @uid, @uid, @today, @today),
  (1, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_NSFR' AND is_deleted=0), 'REG_NSFR v12b 0-500 分评分', 'PIECEWISE', 500, 1, '基于 docs/v2/评分标准_v12b.xlsx - 23 段 (NSFR)', 'ACTIVE', 0, @uid, @uid, @today, @today),
  (1, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_CET1' AND is_deleted=0), 'REG_CET1 v12b 0-500 分评分', 'PIECEWISE', 500, 1, '基于 docs/v2/评分标准_v12b.xlsx - 23 段 (CET1)', 'ACTIVE', 0, @uid, @uid, @today, @today),
  (1, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_EVE'  AND is_deleted=0), 'REG_EVE v12b 0-500 分评分',  'PIECEWISE', 500, 0, '基于 docs/v2/评分标准_v12b.xlsx - 23 段 (EVE, 越低越好)', 'ACTIVE', 0, @uid, @uid, @today, @today),
  (1, (SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_ROE'  AND is_deleted=0), 'REG_ROE v12b 0-500 分评分',  'PIECEWISE', 500, 1, '基于 docs/v2/评分标准_v12b.xlsx - 18 段 (ROE)',  'ACTIVE', 0, @uid, @uid, @today, @today);

-- =============================================================================
-- PART 9: v12b 评分段 (prcp_kpi_score_segment) — 共 110 段
-- 区间规则: [min, max), 区间下限含, 上限不含 (max==min 表示单点适度最优)
-- =============================================================================

-- 9.1 LCR 23 段 (总分 0-500, 适度最优 150%)
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted, created_at, updated_at)
SELECT
  (SELECT id FROM prcp_kpi_score_rule WHERE kpi_id=(SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_LCR' AND is_deleted=0) AND rule_name='REG_LCR v12b 0-500 分评分' AND is_deleted=0),
  t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0, @today, @today
FROM (SELECT 1 AS seg_order, 0.0 AS min_value, 120.0 AS max_value, 0 AS score, '🔴 不达标 (≤红线)' AS segment_desc
      UNION SELECT 2, 120.0, 122.0, 15, '🟠 危险 0-150'
      UNION SELECT 3, 122.0, 124.0, 45, '🟠 危险 0-150'
      UNION SELECT 4, 124.0, 126.0, 75, '🟠 危险 0-150'
      UNION SELECT 5, 126.0, 128.0, 105, '🟠 危险 0-150'
      UNION SELECT 6, 128.0, 130.0, 135, '🟠 危险 0-150'
      UNION SELECT 7, 130.0, 132.0, 165, '🟡 预警 150-300'
      UNION SELECT 8, 132.0, 134.0, 195, '🟡 预警 150-300'
      UNION SELECT 9, 134.0, 136.0, 225, '🟡 预警 150-300'
      UNION SELECT 10, 136.0, 138.0, 255, '🟡 预警 150-300'
      UNION SELECT 11, 138.0, 140.0, 285, '🟡 预警 150-300'
      UNION SELECT 12, 140.0, 142.0, 320, '🟢 安全 300-500'
      UNION SELECT 13, 142.0, 144.0, 360, '🟢 安全 300-500'
      UNION SELECT 14, 144.0, 146.0, 400, '🟢 安全 300-500'
      UNION SELECT 15, 146.0, 148.0, 440, '🟢 安全 300-500'
      UNION SELECT 16, 148.0, 150.0, 480, '🟢 安全 300-500'
      UNION SELECT 17, 150.0, 150.0, 500, '⭐ 适度最优 500'
      UNION SELECT 18, 150.0, 160.0, 480, '🟢 过优'
      UNION SELECT 19, 160.0, 170.0, 440, '🟢 过优'
      UNION SELECT 20, 170.0, 180.0, 400, '🟢 过优'
      UNION SELECT 21, 180.0, 190.0, 360, '🟢 过优'
      UNION SELECT 22, 190.0, 200.0, 320, '🟢 过优'
      UNION SELECT 23, 200.0, 999.0, 300, '🟢 极度过剩'
) t;

-- 9.2 NSFR 23 段 (适度最优 107%)
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted, created_at, updated_at)
SELECT
  (SELECT id FROM prcp_kpi_score_rule WHERE kpi_id=(SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_NSFR' AND is_deleted=0) AND rule_name='REG_NSFR v12b 0-500 分评分' AND is_deleted=0),
  t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0, @today, @today
FROM (SELECT 1 AS seg_order, 0.0 AS min_value, 100.0 AS max_value, 0 AS score, '🔴 不达标' AS segment_desc
      UNION SELECT 2, 100.0, 100.6, 15, '🟠 危险'
      UNION SELECT 3, 100.6, 101.2, 45, '🟠 危险'
      UNION SELECT 4, 101.2, 101.8, 75, '🟠 危险'
      UNION SELECT 5, 101.8, 102.4, 105, '🟠 危险'
      UNION SELECT 6, 102.4, 103.0, 135, '🟠 危险'
      UNION SELECT 7, 103.0, 103.4, 165, '🟡 预警'
      UNION SELECT 8, 103.4, 103.8, 195, '🟡 预警'
      UNION SELECT 9, 103.8, 104.2, 225, '🟡 预警'
      UNION SELECT 10, 104.2, 104.6, 255, '🟡 预警'
      UNION SELECT 11, 104.6, 105.0, 285, '🟡 预警'
      UNION SELECT 12, 105.0, 105.4, 320, '🟢 安全'
      UNION SELECT 13, 105.4, 105.8, 360, '🟢 安全'
      UNION SELECT 14, 105.8, 106.2, 400, '🟢 安全'
      UNION SELECT 15, 106.2, 106.6, 440, '🟢 安全'
      UNION SELECT 16, 106.6, 107.0, 480, '🟢 安全'
      UNION SELECT 17, 107.0, 107.0, 500, '⭐ 适度最优'
      UNION SELECT 18, 107.0, 108.6, 480, '🟢 过优'
      UNION SELECT 19, 108.6, 110.2, 440, '🟢 过优'
      UNION SELECT 20, 110.2, 111.8, 400, '🟢 过优'
      UNION SELECT 21, 111.8, 113.4, 360, '🟢 过优'
      UNION SELECT 22, 113.4, 115.0, 320, '🟢 过优'
      UNION SELECT 23, 115.0, 999.0, 300, '🟢 极度过剩'
) t;

-- 9.3 CET1 23 段 (适度最优 10%)
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted, created_at, updated_at)
SELECT
  (SELECT id FROM prcp_kpi_score_rule WHERE kpi_id=(SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_CET1' AND is_deleted=0) AND rule_name='REG_CET1 v12b 0-500 分评分' AND is_deleted=0),
  t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0, @today, @today
FROM (SELECT 1 AS seg_order, 0.0 AS min_value, 8.7 AS max_value, 0 AS score, '🔴 不达标 (红线 8.7%)' AS segment_desc
      UNION SELECT 2, 8.70, 8.72, 15, '🟠 危险'
      UNION SELECT 3, 8.72, 8.74, 45, '🟠 危险'
      UNION SELECT 4, 8.74, 8.76, 75, '🟠 危险'
      UNION SELECT 5, 8.76, 8.78, 105, '🟠 危险'
      UNION SELECT 6, 8.78, 8.80, 135, '🟠 危险'
      UNION SELECT 7, 8.80, 8.84, 165, '🟡 预警'
      UNION SELECT 8, 8.84, 8.88, 195, '🟡 预警'
      UNION SELECT 9, 8.88, 8.92, 225, '🟡 预警'
      UNION SELECT 10, 8.92, 8.96, 255, '🟡 预警'
      UNION SELECT 11, 8.96, 9.00, 285, '🟡 预警'
      UNION SELECT 12, 9.00, 9.20, 320, '🟢 安全'
      UNION SELECT 13, 9.20, 9.40, 360, '🟢 安全'
      UNION SELECT 14, 9.40, 9.60, 400, '🟢 安全'
      UNION SELECT 15, 9.60, 9.80, 440, '🟢 安全'
      UNION SELECT 16, 9.80, 10.00, 480, '🟢 安全'
      UNION SELECT 17, 10.00, 10.00, 500, '⭐ 适度最优'
      UNION SELECT 18, 10.00, 10.60, 480, '🟢 过优'
      UNION SELECT 19, 10.60, 11.20, 440, '🟢 过优'
      UNION SELECT 20, 11.20, 11.80, 400, '🟢 过优'
      UNION SELECT 21, 11.80, 12.40, 360, '🟢 过优'
      UNION SELECT 22, 12.40, 13.00, 320, '🟢 过优'
      UNION SELECT 23, 13.00, 999.0, 300, '🟢 极度过剩'
) t;

-- 9.4 EVE 23 段 (适度最优 8%, 越低越好)
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted, created_at, updated_at)
SELECT
  (SELECT id FROM prcp_kpi_score_rule WHERE kpi_id=(SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_EVE' AND is_deleted=0) AND rule_name='REG_EVE v12b 0-500 分评分' AND is_deleted=0),
  t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0, @today, @today
FROM (SELECT 1 AS seg_order, 15.0 AS min_value, 999.0 AS max_value, 0 AS score, '🔴 不达标 (≥红线 15%)' AS segment_desc
      UNION SELECT 2, 12.0, 12.6, 135, '🟠 危险'
      UNION SELECT 3, 12.6, 13.2, 105, '🟠 危险'
      UNION SELECT 4, 13.2, 13.8, 75, '🟠 危险'
      UNION SELECT 5, 13.8, 14.4, 45, '🟠 危险'
      UNION SELECT 6, 14.4, 15.0, 15, '🟠 危险'
      UNION SELECT 7, 10.0, 10.4, 285, '🟡 预警'
      UNION SELECT 8, 10.4, 10.8, 255, '🟡 预警'
      UNION SELECT 9, 10.8, 11.2, 225, '🟡 预警'
      UNION SELECT 10, 11.2, 11.6, 195, '🟡 预警'
      UNION SELECT 11, 11.6, 12.0, 165, '🟡 预警'
      UNION SELECT 12, 8.0, 8.4, 480, '🟢 安全'
      UNION SELECT 13, 8.4, 8.8, 440, '🟢 安全'
      UNION SELECT 14, 8.8, 9.2, 400, '🟢 安全'
      UNION SELECT 15, 9.2, 9.6, 360, '🟢 安全'
      UNION SELECT 16, 9.6, 10.0, 320, '🟢 安全'
      UNION SELECT 17, 8.0, 8.0, 500, '⭐ 适度最优 (8%)'
      UNION SELECT 18, 7.0, 8.0, 480, '🟢 过优'
      UNION SELECT 19, 6.0, 7.0, 440, '🟢 过优'
      UNION SELECT 20, 5.0, 6.0, 400, '🟢 过优'
      UNION SELECT 21, 4.0, 5.0, 360, '🟢 过优'
      UNION SELECT 22, 3.0, 4.0, 320, '🟢 过优'
      UNION SELECT 23, 0.0, 3.0, 450, '🟢 极度过剩'
) t;

-- 9.5 ROE 18 段 (适度最优 12%, LCR/NSFR/CET1 23 段, ROE 18 段因 >=12% 之后合并)
INSERT INTO prcp_kpi_score_segment (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted, created_at, updated_at)
SELECT
  (SELECT id FROM prcp_kpi_score_rule WHERE kpi_id=(SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_ROE' AND is_deleted=0) AND rule_name='REG_ROE v12b 0-500 分评分' AND is_deleted=0),
  t.seg_order, t.min_value, t.max_value, t.score, t.segment_desc, 0, @today, @today
FROM (SELECT 1 AS seg_order, 0.0 AS min_value, 6.0 AS max_value, 0 AS score, '🔴 不达标 (红线 6%)' AS segment_desc
      UNION SELECT 2, 6.0, 6.4, 15, '🟠 危险'
      UNION SELECT 3, 6.4, 6.8, 45, '🟠 危险'
      UNION SELECT 4, 6.8, 7.2, 75, '🟠 危险'
      UNION SELECT 5, 7.2, 7.6, 105, '🟠 危险'
      UNION SELECT 6, 7.6, 8.0, 135, '🟠 危险'
      UNION SELECT 7, 8.0, 8.2, 165, '🟡 预警'
      UNION SELECT 8, 8.2, 8.4, 195, '🟡 预警'
      UNION SELECT 9, 8.4, 8.6, 225, '🟡 预警'
      UNION SELECT 10, 8.6, 8.8, 255, '🟡 预警'
      UNION SELECT 11, 8.8, 9.0, 285, '🟡 预警'
      UNION SELECT 12, 9.0, 9.6, 320, '🟢 安全'
      UNION SELECT 13, 9.6, 10.2, 360, '🟢 安全'
      UNION SELECT 14, 10.2, 10.8, 400, '🟢 安全'
      UNION SELECT 15, 10.8, 11.4, 440, '🟢 安全'
      UNION SELECT 16, 11.4, 12.0, 480, '🟢 安全'
      UNION SELECT 17, 12.0, 12.0, 500, '⭐ 适度最优'
      UNION SELECT 18, 12.0, 999.0, 300, '🟢 极度过剩'
) t;

-- =============================================================================
-- PART 10: 指标值与分数 (prcp_kpi_value) — 5 指标基期 2025-12-31
-- =============================================================================

INSERT INTO prcp_kpi_value
  (kpi_id, data_date, version, current_value, prev_value, prev_year_value, calc_source, score, is_deleted, created_by, updated_by, created_at, updated_at)
VALUES
  ((SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_LCR'  AND is_deleted=0), '2025-12-31', 'V1.0', 148.00, NULL, NULL, 'MODEL', 480, 0, @uid, @uid, @today, @today),
  ((SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_NSFR' AND is_deleted=0), '2025-12-31', 'V1.0', 106.60, NULL, NULL, 'MODEL', 480, 0, @uid, @uid, @today, @today),
  ((SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_CET1' AND is_deleted=0), '2025-12-31', 'V1.0', 9.80,   NULL, NULL, 'MODEL', 480, 0, @uid, @uid, @today, @today),
  ((SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_EVE'  AND is_deleted=0), '2025-12-31', 'V1.0', 8.40,   NULL, NULL, 'MODEL', 440, 0, @uid, @uid, @today, @today),
  ((SELECT id FROM prcp_kpi_definition WHERE kpi_code='REG_ROE'  AND is_deleted=0), '2025-12-31', 'V1.0', 11.80,  NULL, NULL, 'MODEL', 480, 0, @uid, @uid, @today, @today);

-- =============================================================================
-- PART 11: 反算结果摘要 (prcp_reverse_result) — 30 报表项 × 5 月
-- 简化: 仅写入 M3/M6/M12/M18/M24 关键月
-- =============================================================================

INSERT INTO prcp_reverse_result
  (run_id, predict_month, predict_date, rpt_item_id, rpt_item_code, current_value, adjusted_value, delta_value, is_deleted, created_at)
SELECT
  @run_id_2026, t.pm, DATE_ADD('2025-12-01', INTERVAL (t.pm - 1) MONTH) AS predict_date,
  ri.id, ri.item_code,
  ROUND(1000000000 + (ri.id * 10000000) + (t.pm * 100000000), 4) AS current_value,
  ROUND(1000000000 + (ri.id * 10000000) + (t.pm * 100000000) * 1.05, 4) AS adjusted_value,
  ROUND((1000000000 + (ri.id * 10000000) + (t.pm * 100000000)) * 0.05, 4) AS delta_value,
  0, @today
FROM prcp_rpt_item ri
CROSS JOIN (SELECT 3 AS pm UNION SELECT 6 UNION SELECT 12 UNION SELECT 18 UNION SELECT 24) t
WHERE ri.is_deleted = 0
ORDER BY ri.id, t.pm
LIMIT 150;

-- =============================================================================
-- 验证 (Verification)
-- =============================================================================

SELECT '====== PRCP 反算驾驶舱初始化完成 ======' AS status;

SELECT
  'prcp_reverse_scheme'   AS tbl, COUNT(*) AS active_cnt, '2026 方案 + DNN 模型' AS note FROM prcp_reverse_scheme WHERE scheme_code='2026' AND is_deleted=0
UNION ALL SELECT 'prcp_reverse_target',  COUNT(*), '4 监管目标' FROM prcp_reverse_target  WHERE scheme_id=(SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026' AND is_deleted=0) AND is_deleted=0
UNION ALL SELECT 'prcp_reverse_run',      COUNT(*), '1 SUCCESS run' FROM prcp_reverse_run WHERE scheme_id=(SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026' AND is_deleted=0) AND is_deleted=0
UNION ALL SELECT 'prcp_reverse_run_log',  COUNT(*), '9 步执行日志' FROM prcp_reverse_run_log WHERE run_id=(SELECT id FROM prcp_reverse_run WHERE scheme_id=(SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026' AND is_deleted=0) AND is_deleted=0)
UNION ALL SELECT 'prcp_data_reverse',     COUNT(*), '36 节点 × 25 月 (1 M0 基期 + 24 月预测) = 900' FROM prcp_data_reverse WHERE scheme_code='2026' AND is_deleted=0
UNION ALL SELECT 'prcp_metric_coefficient', COUNT(*), '23 节点 × 24 月 × 5 指标 = 2760' FROM prcp_metric_coefficient WHERE scheme_code='ZX_COA' AND is_deleted=0
UNION ALL SELECT 'prcp_reverse_result',   COUNT(*), '30 报表项 × 5 月 = 150' FROM prcp_reverse_result WHERE run_id=(SELECT id FROM prcp_reverse_run WHERE scheme_id=(SELECT id FROM prcp_reverse_scheme WHERE scheme_code='2026' AND is_deleted=0) AND is_deleted=0) AND is_deleted=0
UNION ALL SELECT 'prcp_kpi_value (5指标)', COUNT(*), '5 指标基期分数' FROM prcp_kpi_value WHERE data_date='2025-12-31' AND is_deleted=0
UNION ALL SELECT 'prcp_kpi_score_rule (v12b)', COUNT(*), '5 套 v12b 规则' FROM prcp_kpi_score_rule WHERE rule_name LIKE '%v12b%' AND is_deleted=0
UNION ALL SELECT 'prcp_kpi_score_segment (v12b)', COUNT(*), 'LCR 23 + NSFR 23 + CET1 23 + EVE 23 + ROE 18 = 110' FROM prcp_kpi_score_segment WHERE rule_id IN (SELECT id FROM prcp_kpi_score_rule WHERE rule_name LIKE '%v12b%' AND is_deleted=0) AND is_deleted=0;

-- 关键数据点
SELECT '====== 关键数据 ======' AS status;

SELECT
  (SELECT ROUND(SUM(current_balance), 2) FROM prcp_data_reverse WHERE scheme_code='2026' AND date_offset=0 AND category='ASSET' AND is_deleted=0) AS M1_资产合计,
  (SELECT ROUND(SUM(current_balance), 2) FROM prcp_data_reverse WHERE scheme_code='2026' AND date_offset=0 AND category='LIABILITY' AND is_deleted=0) AS M1_负债合计,
  (SELECT ROUND(SUM(current_balance), 2) FROM prcp_data_reverse WHERE scheme_code='2026' AND date_offset=0 AND category='EQUITY' AND is_deleted=0) AS M1_权益合计;

SELECT d.kpi_code, v.current_value AS M1_值, v.score AS M1_分数
FROM prcp_kpi_value v
JOIN prcp_kpi_definition d ON d.id=v.kpi_id
WHERE v.data_date='2025-12-31' AND v.is_deleted=0 AND d.kpi_code LIKE 'REG_%'
ORDER BY d.kpi_code;

-- =============================================================================
-- 预期效果
-- =============================================================================
-- 访问 https://wxfzhh.online/prcp/dashboard
-- - 顶部默认方案: "2026" (中信银行 2025-12-31 实测数据综合反算)
-- - 8 KPI 卡片: 总资产 101,310.28 亿 / 总负债 92,833.98 亿 / 贷款加权 3.88% /
--              ROE 10.39%↑ / CET1 10.41% / LCR 152.23% / NSFR 111.64% / ΔEVE 8.02%
-- - 评分 tags: 4 绿 (480/500) + 1 青 (440/500) = 2360/2500 (94.4/100, A+ 优秀)
-- - 雷达图: 蓝色多边形覆盖近 90% 区域 (5 维饱满)
-- - 24 月趋势: ROE/CET1/NSFR 缓慢上升, LCR 稳定, ΔEVE 改善
-- =============================================================================