-- =============================================================================
-- PRCP 指标统一治理 · P1 数据模型
-- 迁移编号：V20261125_01
--
-- 1) prcp_kpi_definition 扩展 8 个字段（指标定义承载「是什么/从哪算/是否评分/怎么展示」）
-- 2) prcp_reverse_scheme 增加 kpi_scheme_id（打通 方案 → 指标方案 → 指标定义 链路）
-- 3) prcp_metric_coefficient 字段注释澄清（scheme_id 实为「账户册方案」，不改名以免波及 77+ 处引用）
-- 4) 回填：现有指标补新字段 + 新增 5 个资产负债类指标定义 + 回填 kpi_scheme_id + kpi_count
--
-- 幂等：可重复执行
-- =============================================================================

-- ---------- 1. prcp_kpi_definition 扩展 ----------
SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'is_scored');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN is_scored TINYINT(1) NOT NULL DEFAULT 1 COMMENT ''是否参与评分：1=参与(须配score_rule) 0=只计算不评分''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'value_source');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN value_source VARCHAR(24) NOT NULL DEFAULT ''ENGINE_METRIC'' COMMENT ''取数方式：ENGINE_METRIC/BS_CATEGORY_SUM/NODE_WEIGHTED_RATE/KPI_VALUE''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'source_params');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN source_params JSON NULL COMMENT ''取数参数，如 {"category":"ASSET"}''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'metric_code');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN metric_code VARCHAR(32) NULL COMMENT ''引擎指标码，对齐 prcp_metric_coefficient.metric_code''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'display_order');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN display_order INT NOT NULL DEFAULT 999 COMMENT ''展示顺序，决定默认前8个''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'is_displayable');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN is_displayable TINYINT(1) NOT NULL DEFAULT 1 COMMENT ''是否可上首页卡片区''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'display_group');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN display_group VARCHAR(16) NULL DEFAULT ''REG'' COMMENT ''BS=资产负债类 REG=监管类''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_kpi_definition'
            AND COLUMN_NAME = 'color');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_kpi_definition ADD COLUMN color VARCHAR(16) NULL COMMENT ''卡片配色，空则按 display_group 取默认''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 2. prcp_reverse_scheme 增加 kpi_scheme_id ----------
SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_scheme'
            AND COLUMN_NAME = 'kpi_scheme_id');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_scheme ADD COLUMN kpi_scheme_id BIGINT NULL COMMENT ''关联指标方案 id（prcp_kpi_scheme.id）''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 3. prcp_metric_coefficient 注释澄清（不改名） ----------
-- 说明：scheme_id / scheme_code 实际指向「账户册方案」，与 prcp_kpi_definition.scheme_id
--      （指标方案）同名不同义。为避免波及 662 行路由文件 77+ 处引用，本次不改名，
--      仅用注释明确语义；新增字段一律采用自解释命名（coa_scheme_id）。
SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_metric_coefficient'
            AND COLUMN_NAME = 'scheme_id');
SET @s := IF(@c > 0,
  'ALTER TABLE prcp_metric_coefficient MODIFY COLUMN scheme_id INT NULL COMMENT ''★账户册方案 id（prcp_coa_scheme.id），非指标方案''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_metric_coefficient'
            AND COLUMN_NAME = 'scheme_code');
SET @s := IF(@c > 0,
  'ALTER TABLE prcp_metric_coefficient MODIFY COLUMN scheme_code VARCHAR(64) NULL COMMENT ''★账户册方案编码（prcp_coa_scheme.scheme_code），非指标方案''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 4. 回填现有指标定义的新字段 ----------
-- 4.1 监管指标：metric_code 对齐引擎指标码 + display_order + 颜色 + 口径角色
UPDATE prcp_kpi_definition SET
  is_scored     = 1,
  value_source  = 'ENGINE_METRIC',
  metric_code   = 'ROE',
  display_order = 4,  display_group = 'REG', color = '#722ed1',
  formula_desc  = COALESCE(NULLIF(formula_desc,''), '净资产收益率 = 净利润 / 平均净资产（引擎按节点逐月计量后聚合）'),
  source_params = NULL
WHERE kpi_code = 'REG_ROE' AND is_deleted = 0;

UPDATE prcp_kpi_definition SET
  is_scored = 1, value_source = 'ENGINE_METRIC', metric_code = 'CET1',
  display_order = 5, display_group = 'REG', color = '#1890ff',
  formula_desc = COALESCE(NULLIF(formula_desc,''), '核心一级资本充足率 = 核心一级资本 / 风险加权资产')
WHERE kpi_code = 'REG_CET1' AND is_deleted = 0;

UPDATE prcp_kpi_definition SET
  is_scored = 1, value_source = 'ENGINE_METRIC', metric_code = 'LCR',
  display_order = 6, display_group = 'REG', color = '#52c41a',
  formula_desc = COALESCE(NULLIF(formula_desc,''), '流动性覆盖率 = 优质流动性资产 / 未来 30 日净现金流出')
WHERE kpi_code = 'REG_LCR' AND is_deleted = 0;

UPDATE prcp_kpi_definition SET
  is_scored = 1, value_source = 'ENGINE_METRIC', metric_code = 'NSFR',
  display_order = 7, display_group = 'REG', color = '#13c2c2',
  formula_desc = COALESCE(NULLIF(formula_desc,''), '净稳定资金比例 = 可用稳定资金 / 所需稳定资金')
WHERE kpi_code = 'REG_NSFR' AND is_deleted = 0;

UPDATE prcp_kpi_definition SET
  is_scored = 1, value_source = 'ENGINE_METRIC', metric_code = 'DELTA_EVE',
  display_order = 8, display_group = 'REG', color = '#eb2f96',
  formula_desc = COALESCE(NULLIF(formula_desc,''), '经济价值变动率 |ΔEVE| / 一级资本（越低越好）')
WHERE kpi_code = 'REG_EVE' AND is_deleted = 0;

-- 4.2 无评分规则的指标显式标 is_scored=0（口径：只计算不评分）
UPDATE prcp_kpi_definition SET is_scored = 0, value_source = 'ENGINE_METRIC'
WHERE kpi_code IN ('REG_CAR','REG_IBL','REG_LR') AND is_deleted = 0
  AND id NOT IN (SELECT DISTINCT kpi_id FROM prcp_kpi_score_rule WHERE is_deleted = 0);

UPDATE prcp_kpi_definition SET display_order = 11, display_group = 'REG', color = '#fa8c16',
  formula_desc = COALESCE(NULLIF(formula_desc,''), '资本充足率 = 总资本 / 风险加权资产（当前无评分规则，只计算不评分）')
WHERE kpi_code = 'REG_CAR' AND is_deleted = 0;

UPDATE prcp_kpi_definition SET display_order = 12, display_group = 'REG', color = '#8c8c8c',
  formula_desc = COALESCE(NULLIF(formula_desc,''), '同业负债占比（当前为占位值，取不到数时不参与评分）')
WHERE kpi_code = 'REG_IBL' AND is_deleted = 0;

UPDATE prcp_kpi_definition SET display_order = 13, display_group = 'REG', color = '#8c8c8c',
  formula_desc = COALESCE(NULLIF(formula_desc,''), '杠杆率（当前为占位值，取不到数时不参与评分）')
WHERE kpi_code = 'REG_LR' AND is_deleted = 0;

-- ---------- 5. 新增 5 个资产负债类指标定义 ----------
-- 5.1 资产余额
INSERT INTO prcp_kpi_definition
  (scheme_id, indicator_type, kpi_code, kpi_name, calc_unit, formula_desc,
   is_scored, value_source, source_params, metric_code, display_order,
   is_displayable, display_group, color, status, is_deleted)
SELECT 1, 1, 'BS_ASSET_TOTAL', '资产余额', 'AMOUNT',
       '按末级节点汇总的资产余额（基准日口径，父节点不重复计入）',
       0, 'BS_CATEGORY_SUM', JSON_OBJECT('category','ASSET'), NULL, 1, 1, 'BS', '#1890ff', 'ACTIVE', 0
WHERE NOT EXISTS (SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='BS_ASSET_TOTAL' AND is_deleted=0);

-- 5.2 负债余额
INSERT INTO prcp_kpi_definition
  (scheme_id, indicator_type, kpi_code, kpi_name, calc_unit, formula_desc,
   is_scored, value_source, source_params, metric_code, display_order,
   is_displayable, display_group, color, status, is_deleted)
SELECT 1, 1, 'BS_LIAB_TOTAL', '负债余额', 'AMOUNT',
       '按末级节点汇总的负债余额（基准日口径，父节点不重复计入）',
       0, 'BS_CATEGORY_SUM', JSON_OBJECT('category','LIABILITY'), NULL, 2, 1, 'BS', '#fa8c16', 'ACTIVE', 0
WHERE NOT EXISTS (SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='BS_LIAB_TOTAL' AND is_deleted=0);

-- 5.3 贷款加权平均利率
INSERT INTO prcp_kpi_definition
  (scheme_id, indicator_type, kpi_code, kpi_name, calc_unit, formula_desc,
   is_scored, value_source, source_params, metric_code, display_order,
   is_displayable, display_group, color, status, is_deleted)
SELECT 1, 1, 'BS_LOAN_RATE', '贷款加权平均利率', 'RATE',
       '境内各项人民币贷款下属末级节点，按当前余额加权的加权平均利率',
       0, 'NODE_WEIGHTED_RATE', JSON_OBJECT('node_prefixes', JSON_ARRAY('S01010101','S01010102','S01010103','S01010104','S01010105')), NULL, 3, 1, 'BS', '#fa541c', 'ACTIVE', 0
WHERE NOT EXISTS (SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='BS_LOAN_RATE' AND is_deleted=0);

-- 5.4 所有者权益
INSERT INTO prcp_kpi_definition
  (scheme_id, indicator_type, kpi_code, kpi_name, calc_unit, formula_desc,
   is_scored, value_source, source_params, metric_code, display_order,
   is_displayable, display_group, color, status, is_deleted)
SELECT 1, 1, 'BS_EQUITY_TOTAL', '所有者权益', 'AMOUNT',
       '按末级节点汇总的所有者权益（基准日口径）',
       0, 'BS_CATEGORY_SUM', JSON_OBJECT('category','EQUITY'), NULL, 9, 1, 'BS', '#722ed1', 'ACTIVE', 0
WHERE NOT EXISTS (SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='BS_EQUITY_TOTAL' AND is_deleted=0);

-- 5.5 表外余额
INSERT INTO prcp_kpi_definition
  (scheme_id, indicator_type, kpi_code, kpi_name, calc_unit, formula_desc,
   is_scored, value_source, source_params, metric_code, display_order,
   is_displayable, display_group, color, status, is_deleted)
SELECT 1, 1, 'BS_OFFBAL_TOTAL', '表外余额', 'AMOUNT',
       '按末级节点汇总的表外科目余额（基准日口径）',
       0, 'BS_CATEGORY_SUM', JSON_OBJECT('category','OFF_BALANCE'), NULL, 10, 1, 'BS', '#13c2c2', 'ACTIVE', 0
WHERE NOT EXISTS (SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='BS_OFFBAL_TOTAL' AND is_deleted=0);

-- ---------- 6. 回填组合方案的 kpi_scheme_id ----------
-- 默认关联「2026 监管指标方案」（scheme_code=SCH_REG_2026）
UPDATE prcp_reverse_scheme r
JOIN prcp_kpi_scheme k ON k.scheme_code = 'SCH_REG_2026' AND k.is_deleted = 0
SET r.kpi_scheme_id = k.id
WHERE r.kpi_scheme_id IS NULL AND r.is_deleted = 0;

-- ---------- 7. 回填指标方案的 kpi_count ----------
UPDATE prcp_kpi_scheme k
SET k.kpi_count = (
  SELECT COUNT(*) FROM prcp_kpi_definition d
  WHERE d.scheme_id = k.id AND d.is_deleted = 0 AND d.is_displayable = 1
)
WHERE k.is_deleted = 0;

-- ---------- 8. 校验 ----------
SELECT '指标定义总览' AS check_item,
       display_group, is_scored, is_displayable, COUNT(*) AS n
FROM prcp_kpi_definition WHERE is_deleted = 0
GROUP BY display_group, is_scored, is_displayable
ORDER BY display_group, is_scored;

SELECT '默认前8个（display_order 升序）' AS check_item,
       GROUP_CONCAT(kpi_code ORDER BY display_order SEPARATOR ', ') AS selected
FROM (
  SELECT kpi_code, display_order FROM prcp_kpi_definition
  WHERE is_deleted = 0 AND is_displayable = 1
  ORDER BY display_order LIMIT 8
) t;

SELECT '组合方案关联指标方案' AS check_item,
       r.scheme_code, r.kpi_scheme_id, k.scheme_code AS kpi_scheme
FROM prcp_reverse_scheme r LEFT JOIN prcp_kpi_scheme k ON k.id = r.kpi_scheme_id
WHERE r.is_deleted = 0;
