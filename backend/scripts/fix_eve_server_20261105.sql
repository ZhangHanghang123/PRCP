-- =============================================================================
-- PRCP 服务器修正 · 2026-11-05
--
-- 修正背景（测试发现）：
--   1. prcp_eve_param.is_liability 全库漏标 —— 57 行中 is_liability 全为 0，
--      导致 backend/scripts/kpi_functions/reg_eve.py 的
--      D_L = SUM(is_liability=1 ...) 计算结果为 NULL，
--      久期缺口 D_GAP = D_A - NULL → ΔEVE 恒为 0，KPI 失真。
--      根因：seed 时只写了 is_asset=1，负债账户（is_asset=0）未置 is_liability=1。
--
--   2. REG_EVE 的 calc_unit = AMOUNT，但 0-500 评分规则需要百分比口径。
--      v14.1 起 EVE 统一为 |ΔEVE| / 一级资本（巴塞尔 SRP31.82 监管口径）。
--
--   3. 服务器 REG_EVE 规则仍是 v12b（rule_id=54），L 方向段序被打乱，
--      x=8.40 实际命中段12 得 480 分，而库存值写 440 分（不一致）。
--      → 换用 v14.1 规则（23 段锚点推导，段序按语义顺序）。
--
--   4. 服务器缺 REG_CAR / REG_IBL / REG_LR 三个 KPI 定义（v14.1 已扩到 8 指标）。
--
-- 前置备份：/home/almd/backup/prcp_20261105/eve_score_tables.sql
-- =============================================================================

USE prcp_db;

SET @uid := 1;
SET @today := NOW();

-- =============================================================================
-- 修正 1：prcp_eve_param 负债标记补全
--   规则：is_asset=0 且 duration>0 且 node_code 属于负债科目（S02* 开头，
--         且在 prcp_coa_node 中 path 以 S020000000000 开头）→ is_liability=1
--   这 14 个节点全部为末级负债账户，path 已逐一核对：
--         S020101010100 对公活期存款 / S020101010200 对公定期存款
--         S020101020100 零售活期存款 / S020101020200 零售定期存款
--         S020102010100 货币市场同业拆入 / S020102010200 货币市场债券回购
--         S020102010300 同业存单NCD / S020102010400 同业存款
--         S020102010500 票据转贴现回购 / S020102020200 MLF
--         S020102020300 结构性货币政策工具 / S020102020400 票据再贴现回购
--         S020201000000 外币存款 / S020202000000 外币市场化负债
-- =============================================================================
UPDATE prcp_eve_param p
SET p.is_liability = 1
WHERE p.is_deleted = 0
  AND p.is_asset = 0
  AND p.is_liability = 0
  AND p.duration > 0
  AND EXISTS (
    SELECT 1 FROM prcp_coa_node n
    WHERE n.node_code = p.node_code
      AND n.is_deleted = 0
      AND n.path LIKE '/S020000000000/%'
  );

SELECT '修正1 · 负债标记补全' AS step,
       COUNT(*) AS liab_rows,
       SUM(CASE WHEN is_liability = 1 THEN 1 ELSE 0 END) AS flagged
FROM prcp_eve_param WHERE is_deleted = 0 AND is_liability = 1;

-- =============================================================================
-- 修正 2：新增 3 个 KPI 定义（REG_CAR / REG_IBL / REG_LR）
--   与既有 REG_* 一致：scheme_id=1, rpt_id=19(RPT_RWA), indicator_type=2
--   唯一键 uk_scheme_code(scheme_id, kpi_code)
-- =============================================================================
INSERT INTO prcp_kpi_definition
 (scheme_id, indicator_type, kpi_code, kpi_name, rpt_id, formula,
  calc_unit, formula_desc, status, is_deleted, created_by, updated_by,
  created_at, updated_at)
SELECT 1, 2, 'REG_CAR', 'CAR 资本充足率', 19, NULL, 'PERCENT',
       '2025年报 1.4.6 资本充足率 12.80%', 'ACTIVE', 0, @uid, @uid, @today, @today
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='REG_CAR' AND is_deleted=0);

INSERT INTO prcp_kpi_definition
 (scheme_id, indicator_type, kpi_code, kpi_name, rpt_id, formula,
  calc_unit, formula_desc, status, is_deleted, created_by, updated_by,
  created_at, updated_at)
SELECT 1, 2, 'REG_IBL', 'IBL 同业负债占总负债比例', 19, NULL, 'PERCENT',
       '内部计量口径：同业负债 / 总负债', 'ACTIVE', 0, @uid, @uid, @today, @today
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='REG_IBL' AND is_deleted=0);

INSERT INTO prcp_kpi_definition
 (scheme_id, indicator_type, kpi_code, kpi_name, rpt_id, formula,
  calc_unit, formula_desc, status, is_deleted, created_by, updated_by,
  created_at, updated_at)
SELECT 1, 2, 'REG_LR', 'LR 杠杆率', 19, NULL, 'PERCENT',
       '2025年报第三支柱 LR2 杠杆率 7.09%', 'ACTIVE', 0, @uid, @uid, @today, @today
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM prcp_kpi_definition WHERE kpi_code='REG_LR' AND is_deleted=0);

SELECT '修正2 · 新增 KPI 定义' AS step,
       kpi_code, kpi_name, calc_unit, id
FROM prcp_kpi_definition
WHERE kpi_code IN ('REG_CAR','REG_IBL','REG_LR') AND is_deleted=0;

-- =============================================================================
-- 修正 3：REG_EVE 的 calc_unit 由 AMOUNT 改为 PERCENT
--   v14.1 起 EVE 指标值为百分比（|ΔEVE|/一级资本）
-- =============================================================================
UPDATE prcp_kpi_definition
SET calc_unit = 'PERCENT',
    formula_desc = '行内 ΔEVE = |ΔEVE| / 一级资本（巴塞尔 SRP31.82 监管口径）',
    updated_by = @uid, updated_at = NOW()
WHERE kpi_code = 'REG_EVE' AND is_deleted = 0;

SELECT '修正3 · REG_EVE 单位' AS step, kpi_code, calc_unit FROM prcp_kpi_definition
WHERE kpi_code='REG_EVE' AND is_deleted=0;

-- =============================================================================
-- 修正 4：归档旧 v12b 规则
--   ⚠ 唯一索引 uk_kpi_rule = (kpi_id, rule_name, is_deleted)
--     同名规则只能存在一条 —— 必须先改写 rule_name 再置 is_deleted=1
-- =============================================================================
UPDATE prcp_kpi_score_rule
SET rule_name = CONCAT(rule_name, ' #archived@', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s')),
    is_deleted = 1, updated_by = @uid, updated_at = NOW()
WHERE is_deleted = 0 AND rule_name LIKE '%v12b%';

UPDATE prcp_kpi_score_segment s
JOIN prcp_kpi_score_rule r ON r.id = s.rule_id
SET s.is_deleted = 1, s.updated_at = NOW()
WHERE r.is_deleted = 1 AND s.is_deleted = 0
  AND r.rule_name LIKE '%v12b%';

SELECT '修正4 · v12b 归档' AS step, id, kpi_id, rule_name, is_deleted
FROM prcp_kpi_score_rule WHERE rule_name LIKE '%v12b%' ORDER BY id;
