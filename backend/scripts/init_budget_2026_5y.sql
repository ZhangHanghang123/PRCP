-- ============================================================================
-- PRCP 2026-2030 五年业务预算方案（BUDGET_2026_5Y）
-- 基准日 2025-12-31 | 预测期 60 月（5 年）
-- 37 个末级节点全覆盖 | 4 种增长方式全覆盖 | 每年增长约 5%
--
-- growth_type 分配策略（按中信实际业务特征）：
--   1 目标增长百分比 → 贷款类（净增长口径，到期回补保证达标）
--   2 目标增长绝对值 → 同业负债（净增额口径，绝对额管控）
--   3 增长百分比     → 债券投资（毛投放口径，到期自然出表）
--   4 增长值         → 存款 + 权益（余额锚定，可为负）
--
-- 节奏：线性（均衡）/ 开门红 / 季末冲量 / 前低后高
-- ============================================================================

USE prcp_db;
SET @uid = 1;

-- ----------------------------------------------------------------------------
-- PART 1 清理（幂等）
-- ----------------------------------------------------------------------------
SET @sid := (SELECT id FROM prcp_sim_scheme WHERE scheme_code='BUDGET_2026_5Y' AND is_deleted=0 LIMIT 1);
SET @sid := IFNULL(@sid, 0);

DELETE FROM prcp_sim_result WHERE run_id IN (SELECT id FROM prcp_sim_run WHERE sim_scheme_id=@sid);
DELETE FROM prcp_sim_run WHERE sim_scheme_id=@sid;
DELETE FROM prcp_sim_growth_config WHERE scheme_id=@sid;
DELETE FROM prcp_sim_rhythm WHERE config_id IN (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid);
DELETE FROM prcp_sim_term_ratio WHERE config_id IN (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid);
DELETE FROM prcp_sim_node_config WHERE scheme_id=@sid;
DELETE FROM prcp_sim_scheme WHERE id=@sid;

-- ----------------------------------------------------------------------------
-- PART 2 新建方案
-- ----------------------------------------------------------------------------
INSERT INTO prcp_sim_scheme
  (scheme_code, scheme_name, coa_scheme_id, data_date, description, config_node_count, status, is_deleted, created_by, updated_by)
VALUES (
  'BUDGET_2026_5Y', '中信银行 2026-2030 五年业务预算方案', 1, '2025-12-31',
  '中信银行 2026-2030 五年业务预算方案。基准日 2025-12-31（对齐 prcp_data_basic 基础数据），预测期 60 月（5 年）。',
  37, 'ACTIVE', 0, @uid, @uid);

SET @sid := LAST_INSERT_ID();

-- ----------------------------------------------------------------------------
-- PART 3 节点配置（37 个末级节点）+ 增长配置（5 年参数）
-- ----------------------------------------------------------------------------
INSERT INTO prcp_sim_node_config
  (scheme_id, coa_node_id, coa_node_code, annual_growth_rate, term_unit, term_count,
   is_model_calc, rhythm_type, remark, is_deleted, created_by, updated_by)
VALUES
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010101010000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010101010000', 5.0, 'MONTH', 4, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010101020000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010101020000', 5.2, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010101030000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010101030000', 6.0, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010101040000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010101040000', 4.0, 'MONTH', 4, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010101050000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010101050000', 5.5, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102010101' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102010101', 5.5, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102010102' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102010102', 5.0, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102010103' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102010103', 5.0, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102010201' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102010201', 5.5, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102010202' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102010202', 5.0, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102010203' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102010203', 5.0, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102020000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102020000', 5.0, 'MONTH', 4, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102030000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102030000', 4.5, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010102040000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010102040000', 3.0, 'MONTH', 4, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010103010000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010103010000', 5.0, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010103020100' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010103020100', 5.0, 'MONTH', 4, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010103020200' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010103020200', 5.0, 'MONTH', 4, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010201000000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010201000000', 5.0, 'MONTH', 4, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010202010000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010202010000', 5.0, 'MONTH', 4, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010202020000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010202020000', 5.0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S010203000000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S010203000000', 0, 'MONTH', 4, 2, 1, '存量保持（不参与模型测算）', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020101010100' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020101010100', 0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020101010200' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020101010200', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020101020100' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020101020100', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020101020200' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020101020200', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102010100' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102010100', 0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102010200' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102010200', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102010300' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102010300', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102010400' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102010400', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102010500' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102010500', 0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102020100' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102020100', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102020200' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102020200', 0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102020300' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102020300', 0, 'MONTH', 3, 1, 2, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020102020400' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020102020400', 0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020201000000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020201000000', 0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S020202000000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S020202000000', 0, 'MONTH', 3, 1, 1, '参与模型测算', 0, @uid, @uid),
  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='S030000000000' AND scheme_id=1 AND is_deleted=0 LIMIT 1),
   'S030000000000', 0, 'MONTH', 1, 1, 1, '参与模型测算', 0, @uid, @uid);

-- 回填 term_count（按实际占比行数）

-- 增长配置（growth_type + 5 年参数 + 单位）
INSERT INTO prcp_sim_growth_config
  (scheme_id, scheme_code, scheme_name, coa_node_id, coa_node_code, coa_node_name,
   config_id, growth_type, year1_value, year2_value, year3_value, year4_value, year5_value,
   unit, amount_unit, remark, is_deleted, created_by, updated_by)
SELECT
  @sid, 'BUDGET_2026_5Y', '中信银行 2026-2030 五年业务预算方案', c.coa_node_id, c.coa_node_code,
  (SELECT n.node_name FROM prcp_coa_node n WHERE n.id = c.coa_node_id),
  c.id, t.gt, t.y1, t.y2, t.y3, t.y4, t.y5,
  t.unit, t.amt_unit, t.rmk, 0, @uid, @uid
FROM prcp_sim_node_config c
JOIN (
  SELECT 'S010101010000' AS code, 1 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '1.1.对公一般贷款，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010101020000' AS code, 1 AS gt, 5.2000 AS y1, 5.2000 AS y2, 5.0000 AS y3, 5.0000 AS y4, 5.2000 AS y5,
         '%' AS unit, NULL AS amt_unit, '1.2.个人贷款，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010101030000' AS code, 1 AS gt, 6.0000 AS y1, 6.0000 AS y2, 5.8000 AS y3, 5.8000 AS y4, 6.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '1.3.信用卡贷款，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010101040000' AS code, 1 AS gt, 4.0000 AS y1, 4.0000 AS y2, 3.8000 AS y3, 3.8000 AS y4, 4.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '1.4.票据贴现，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010101050000' AS code, 1 AS gt, 5.5000 AS y1, 5.5000 AS y2, 5.3000 AS y3, 5.3000 AS y4, 5.5000 AS y5,
         '%' AS unit, NULL AS amt_unit, '1.5.非银贷款，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102010101' AS code, 3 AS gt, 5.5000 AS y1, 5.5000 AS y2, 5.3000 AS y3, 5.3000 AS y4, 5.5000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.1.1.1AC，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102010102' AS code, 3 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.1.1.2FVOCI，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102010103' AS code, 3 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.1.1.3FVTPL，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102010201' AS code, 3 AS gt, 5.5000 AS y1, 5.5000 AS y2, 5.3000 AS y3, 5.3000 AS y4, 5.5000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.1.2.1AC，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102010202' AS code, 3 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.1.2.2FVOCI，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102010203' AS code, 3 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.1.2.3FVTPL，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102020000' AS code, 1 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.2.结构化融资，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102030000' AS code, 1 AS gt, 4.5000 AS y1, 4.5000 AS y2, 4.3000 AS y3, 4.3000 AS y4, 4.5000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.3.同业资产，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010102040000' AS code, 1 AS gt, 3.0000 AS y1, 3.0000 AS y2, 2.8000 AS y3, 2.8000 AS y4, 3.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.4.存款准备金，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010103010000' AS code, 3 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '3.1.FVTPL类资产，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010103020100' AS code, 1 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '3.2.1.现金，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010103020200' AS code, 1 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '3.2.2.其它，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010201000000' AS code, 1 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '1.外币贷款，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010202010000' AS code, 3 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.1.外币债券，毛投放口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S010202020000' AS code, 1 AS gt, 5.0000 AS y1, 5.0000 AS y2, 4.8000 AS y3, 4.8000 AS y4, 5.0000 AS y5,
         '%' AS unit, NULL AS amt_unit, '2.2.外币同业资产，净增长口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020101010100' AS code, 4 AS gt, 261052260.0000 AS y1, 274104873.0000 AS y2, 287810116.6500 AS y3, 302200622.4800 AS y4, 317310653.6100 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '1.1.1对公活期存款，余额锚定，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020101010200' AS code, 4 AS gt, 182676644.0000 AS y1, 192175829.4900 AS y2, 202168972.6200 AS y3, 212681759.2000 AS y4, 223741210.6800 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '1.1.2对公定期存款，余额锚定，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020101020100' AS code, 4 AS gt, 45661035.0000 AS y1, 47944086.7500 AS y2, 50341291.0900 AS y3, 52858355.6400 AS y4, 55501273.4200 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '1.2.1零售活期存款，余额锚定，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020101020200' AS code, 4 AS gt, 182476132.8000 AS y1, 191964891.7100 AS y2, 201947066.0700 AS y3, 212448313.5100 AS y4, 223495625.8100 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '1.2.2零售定期存款，余额锚定，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102010100' AS code, 2 AS gt, 164940.0000 AS y1, 173187.0000 AS y2, 181846.3500 AS y3, 190938.6700 AS y4, 200485.6000 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.1.1同业拆入，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102010200' AS code, 2 AS gt, 479375.0000 AS y1, 503343.7500 AS y2, 528510.9400 AS y3, 554936.4800 AS y4, 582683.3100 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.1.2债券回购，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102010300' AS code, 2 AS gt, 4661190.0000 AS y1, 4894249.5000 AS y2, 5138961.9700 AS y3, 5395910.0700 AS y4, 5665705.5800 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.1.3同业存单NCD，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102010400' AS code, 2 AS gt, 4578025.0000 AS y1, 4806926.2500 AS y2, 5047272.5600 AS y3, 5299636.1900 AS y4, 5564618.0000 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.1.4同业存款，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102010500' AS code, 2 AS gt, 5000.0000 AS y1, 5250.0000 AS y2, 5512.5000 AS y3, 5788.1200 AS y4, 6077.5300 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.1.5票据转贴现回购，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102020100' AS code, 2 AS gt, 1769440.0000 AS y1, 1857912.0000 AS y2, 1950807.6000 AS y3, 2048347.9800 AS y4, 2150765.3800 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.2.1公开市场回购，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102020200' AS code, 2 AS gt, 801850.0000 AS y1, 841942.5000 AS y2, 884039.6200 AS y3, 928241.6100 AS y4, 974653.6900 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.2.2 MLF，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102020300' AS code, 2 AS gt, 211060.0000 AS y1, 221613.0000 AS y2, 232693.6500 AS y3, 244328.3300 AS y4, 256544.7500 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.2.3结构性货币工具，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020102020400' AS code, 2 AS gt, 7625.0000 AS y1, 8006.2500 AS y2, 8406.5600 AS y3, 8826.8900 AS y4, 9268.2400 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.2.2.4票据再贴现回购，净增额口径，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020201000000' AS code, 4 AS gt, 15750000.0000 AS y1, 16537500.0000 AS y2, 17364375.0000 AS y3, 18232593.7500 AS y4, 19144223.4400 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '1.外币存款，余额锚定，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S020202000000' AS code, 4 AS gt, 8400000.0000 AS y1, 8820000.0000 AS y2, 9261000.0000 AS y3, 9724050.0000 AS y4, 10210252.5000 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '2.外币市场化负债，余额锚定，5 年复合增长' AS rmk
  UNION ALL
  SELECT 'S030000000000' AS code, 4 AS gt, 82552785.0000 AS y1, 86680424.2500 AS y2, 91014445.4600 AS y3, 95565167.7400 AS y4, 100343426.1200 AS y5,
         'ABS' AS unit, 'WAN' AS amt_unit, '所有者权益，余额锚定，5 年复合增长' AS rmk
) t ON t.code = c.coa_node_code
WHERE c.scheme_id = @sid;

-- ----------------------------------------------------------------------------
-- PART 4 节奏配置（12 个月权重）
-- ----------------------------------------------------------------------------
INSERT INTO prcp_sim_rhythm
  (config_id, scheme_id, coa_node_id, month_no, month_label, weight, sort_order, remark, is_deleted, created_by, updated_by)
SELECT c.id, @sid, c.coa_node_id, t.mo, CONCAT(t.mo, '月'), t.w, t.mo, NULL, 0, @uid, @uid
FROM prcp_sim_node_config c
JOIN (
  SELECT 'S010101010000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101010000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 1 AS mo, 18.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 2 AS mo, 14.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 3 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 5 AS mo, 7.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 7 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 8 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 9 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 10 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010101020000' AS code, 12 AS mo, 2.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 1 AS mo, 18.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 2 AS mo, 14.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 3 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 5 AS mo, 7.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 7 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 8 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 9 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 10 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010101030000' AS code, 12 AS mo, 2.0000 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101040000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 1 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 2 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 3 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 5 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 7 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 8 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 9 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 10 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 11 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010101050000' AS code, 12 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010101' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010102' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010103' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010201' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010202' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010102010203' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102020000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 1 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 2 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 3 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 5 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 7 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 8 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 9 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 10 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 11 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010102030000' AS code, 12 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010102040000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010103010000' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020100' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010103020200' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010201000000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S010202010000' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S010202020000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010100' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 1 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 2 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 3 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 5 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 7 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 8 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 9 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 10 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 11 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101010200' AS code, 12 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 1 AS mo, 18.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 2 AS mo, 14.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 3 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 5 AS mo, 7.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 7 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 8 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 9 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 10 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020101020100' AS code, 12 AS mo, 2.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 1 AS mo, 18.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 2 AS mo, 14.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 3 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 5 AS mo, 7.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 7 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 8 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 9 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 10 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020101020200' AS code, 12 AS mo, 2.0000 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010100' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010200' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102010300' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 1 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 2 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 3 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 5 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 7 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 8 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 9 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 10 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 11 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102010400' AS code, 12 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102010500' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 1 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 2 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 3 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 4 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 5 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 6 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 7 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 8 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 9 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 10 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 11 AS mo, 5.0000 AS w
  UNION ALL
  SELECT 'S020102020100' AS code, 12 AS mo, 15.0000 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020200' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 1 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 2 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 3 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 4 AS mo, 8.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 5 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 6 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 7 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 8 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 9 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 10 AS mo, 10.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 11 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102020300' AS code, 12 AS mo, 6.0000 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020102020400' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020201000000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S020202000000' AS code, 12 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 1 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 2 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 3 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 4 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 5 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 6 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 7 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 8 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 9 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 10 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 11 AS mo, 8.3333 AS w
  UNION ALL
  SELECT 'S030000000000' AS code, 12 AS mo, 8.3333 AS w
) t ON t.code = c.coa_node_code
WHERE c.scheme_id = @sid;

-- ----------------------------------------------------------------------------
-- PART 5 期限占比（按业务类型的期限结构）
-- ----------------------------------------------------------------------------
INSERT INTO prcp_sim_term_ratio
  (config_id, term_value, term_unit, business_ratio, interest_rate, sort_order, remark, is_deleted, created_by, updated_by)
SELECT c.id, t.tv, 'MONTH', t.br, t.ir, t.so, NULL, 0, @uid, @uid
FROM prcp_sim_node_config c
JOIN (
  SELECT 'S010101010000' AS code, 12 AS tv, 20.00 AS br, 3.2000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010101010000' AS code, 24 AS tv, 30.00 AS br, 3.3500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010101010000' AS code, 36 AS tv, 25.00 AS br, 3.5000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010101010000' AS code, 60 AS tv, 25.00 AS br, 3.7000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010101020000' AS code, 12 AS tv, 20.00 AS br, 3.8000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010101020000' AS code, 24 AS tv, 30.00 AS br, 3.9500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010101020000' AS code, 36 AS tv, 25.00 AS br, 4.1000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010101020000' AS code, 60 AS tv, 25.00 AS br, 4.3000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010101030000' AS code, 6 AS tv, 30.00 AS br, 7.0000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010101030000' AS code, 12 AS tv, 40.00 AS br, 7.2000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010101030000' AS code, 24 AS tv, 20.00 AS br, 7.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010101030000' AS code, 36 AS tv, 10.00 AS br, 7.9000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010101040000' AS code, 6 AS tv, 30.00 AS br, 1.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010101040000' AS code, 12 AS tv, 40.00 AS br, 1.7000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010101040000' AS code, 24 AS tv, 20.00 AS br, 2.1000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010101040000' AS code, 36 AS tv, 10.00 AS br, 2.4000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010101050000' AS code, 12 AS tv, 20.00 AS br, 3.6000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010101050000' AS code, 24 AS tv, 30.00 AS br, 3.7500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010101050000' AS code, 36 AS tv, 25.00 AS br, 3.9000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010101050000' AS code, 60 AS tv, 25.00 AS br, 4.1000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102010101' AS code, 12 AS tv, 25.00 AS br, 2.6000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102010101' AS code, 24 AS tv, 25.00 AS br, 2.6000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102010101' AS code, 36 AS tv, 25.00 AS br, 2.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102010101' AS code, 60 AS tv, 25.00 AS br, 2.6000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102010102' AS code, 12 AS tv, 25.00 AS br, 2.7000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102010102' AS code, 24 AS tv, 25.00 AS br, 2.7000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102010102' AS code, 36 AS tv, 25.00 AS br, 2.7000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102010102' AS code, 60 AS tv, 25.00 AS br, 2.7000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102010103' AS code, 12 AS tv, 25.00 AS br, 2.9000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102010103' AS code, 24 AS tv, 25.00 AS br, 2.9000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102010103' AS code, 36 AS tv, 25.00 AS br, 2.9000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102010103' AS code, 60 AS tv, 25.00 AS br, 2.9000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102010201' AS code, 12 AS tv, 25.00 AS br, 2.6000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102010201' AS code, 24 AS tv, 25.00 AS br, 2.6000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102010201' AS code, 36 AS tv, 25.00 AS br, 2.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102010201' AS code, 60 AS tv, 25.00 AS br, 2.6000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102010202' AS code, 12 AS tv, 25.00 AS br, 2.7000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102010202' AS code, 24 AS tv, 25.00 AS br, 2.7000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102010202' AS code, 36 AS tv, 25.00 AS br, 2.7000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102010202' AS code, 60 AS tv, 25.00 AS br, 2.7000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102010203' AS code, 12 AS tv, 25.00 AS br, 2.9000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102010203' AS code, 24 AS tv, 25.00 AS br, 2.9000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102010203' AS code, 36 AS tv, 25.00 AS br, 2.9000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102010203' AS code, 60 AS tv, 25.00 AS br, 2.9000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102020000' AS code, 12 AS tv, 20.00 AS br, 3.4000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102020000' AS code, 24 AS tv, 30.00 AS br, 3.5500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102020000' AS code, 36 AS tv, 25.00 AS br, 3.7000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102020000' AS code, 60 AS tv, 25.00 AS br, 3.9000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010102030000' AS code, 3 AS tv, 40.00 AS br, 2.0000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102030000' AS code, 6 AS tv, 30.00 AS br, 2.0500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102030000' AS code, 12 AS tv, 30.00 AS br, 2.1000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102040000' AS code, 6 AS tv, 30.00 AS br, 1.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010102040000' AS code, 12 AS tv, 40.00 AS br, 1.7000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010102040000' AS code, 24 AS tv, 20.00 AS br, 2.1000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010102040000' AS code, 36 AS tv, 10.00 AS br, 2.4000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010103010000' AS code, 12 AS tv, 25.00 AS br, 2.8000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010103010000' AS code, 24 AS tv, 25.00 AS br, 2.8000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010103010000' AS code, 36 AS tv, 25.00 AS br, 2.8000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010103010000' AS code, 60 AS tv, 25.00 AS br, 2.8000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010103020100' AS code, 6 AS tv, 30.00 AS br, 0.0000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010103020100' AS code, 12 AS tv, 40.00 AS br, 0.2000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010103020100' AS code, 24 AS tv, 20.00 AS br, 0.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010103020100' AS code, 36 AS tv, 10.00 AS br, 0.9000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010103020200' AS code, 6 AS tv, 30.00 AS br, 0.0000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010103020200' AS code, 12 AS tv, 40.00 AS br, 0.2000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010103020200' AS code, 24 AS tv, 20.00 AS br, 0.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010103020200' AS code, 36 AS tv, 10.00 AS br, 0.9000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010201000000' AS code, 12 AS tv, 20.00 AS br, 4.0000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010201000000' AS code, 24 AS tv, 30.00 AS br, 4.1500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010201000000' AS code, 36 AS tv, 25.00 AS br, 4.3000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010201000000' AS code, 60 AS tv, 25.00 AS br, 4.5000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010202010000' AS code, 12 AS tv, 25.00 AS br, 2.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010202010000' AS code, 24 AS tv, 25.00 AS br, 2.5000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010202010000' AS code, 36 AS tv, 25.00 AS br, 2.5000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S010202010000' AS code, 60 AS tv, 25.00 AS br, 2.5000 AS ir, 4 AS so
  UNION ALL
  SELECT 'S010202020000' AS code, 3 AS tv, 40.00 AS br, 2.2000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S010202020000' AS code, 6 AS tv, 30.00 AS br, 2.2500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S010202020000' AS code, 12 AS tv, 30.00 AS br, 2.3000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020101010100' AS code, 12 AS tv, 40.00 AS br, 0.8500 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020101010100' AS code, 24 AS tv, 35.00 AS br, 1.0000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020101010100' AS code, 36 AS tv, 25.00 AS br, 1.1500 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020101010200' AS code, 12 AS tv, 40.00 AS br, 2.0500 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020101010200' AS code, 24 AS tv, 35.00 AS br, 2.2000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020101010200' AS code, 36 AS tv, 25.00 AS br, 2.3500 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020101020100' AS code, 12 AS tv, 40.00 AS br, 0.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020101020100' AS code, 24 AS tv, 35.00 AS br, 0.6500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020101020100' AS code, 36 AS tv, 25.00 AS br, 0.8000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020101020200' AS code, 12 AS tv, 40.00 AS br, 2.0000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020101020200' AS code, 24 AS tv, 35.00 AS br, 2.1500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020101020200' AS code, 36 AS tv, 25.00 AS br, 2.3000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102010100' AS code, 3 AS tv, 40.00 AS br, 1.8000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102010100' AS code, 6 AS tv, 30.00 AS br, 1.8500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102010100' AS code, 12 AS tv, 30.00 AS br, 1.9000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102010200' AS code, 3 AS tv, 40.00 AS br, 1.8500 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102010200' AS code, 6 AS tv, 30.00 AS br, 1.9000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102010200' AS code, 12 AS tv, 30.00 AS br, 1.9500 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102010300' AS code, 3 AS tv, 40.00 AS br, 2.0000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102010300' AS code, 6 AS tv, 30.00 AS br, 2.0500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102010300' AS code, 12 AS tv, 30.00 AS br, 2.1000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102010400' AS code, 3 AS tv, 40.00 AS br, 1.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102010400' AS code, 6 AS tv, 30.00 AS br, 1.5500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102010400' AS code, 12 AS tv, 30.00 AS br, 1.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102010500' AS code, 3 AS tv, 40.00 AS br, 1.6000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102010500' AS code, 6 AS tv, 30.00 AS br, 1.6500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102010500' AS code, 12 AS tv, 30.00 AS br, 1.7000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102020100' AS code, 3 AS tv, 40.00 AS br, 1.7000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102020100' AS code, 6 AS tv, 30.00 AS br, 1.7500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102020100' AS code, 12 AS tv, 30.00 AS br, 1.8000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102020200' AS code, 3 AS tv, 40.00 AS br, 2.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102020200' AS code, 6 AS tv, 30.00 AS br, 2.5500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102020200' AS code, 12 AS tv, 30.00 AS br, 2.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102020300' AS code, 3 AS tv, 40.00 AS br, 1.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102020300' AS code, 6 AS tv, 30.00 AS br, 1.5500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102020300' AS code, 12 AS tv, 30.00 AS br, 1.6000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020102020400' AS code, 3 AS tv, 40.00 AS br, 1.3000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020102020400' AS code, 6 AS tv, 30.00 AS br, 1.3500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020102020400' AS code, 12 AS tv, 30.00 AS br, 1.4000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020201000000' AS code, 12 AS tv, 40.00 AS br, 1.5000 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020201000000' AS code, 24 AS tv, 35.00 AS br, 1.6500 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020201000000' AS code, 36 AS tv, 25.00 AS br, 1.8000 AS ir, 3 AS so
  UNION ALL
  SELECT 'S020202000000' AS code, 12 AS tv, 40.00 AS br, 1.8500 AS ir, 1 AS so
  UNION ALL
  SELECT 'S020202000000' AS code, 24 AS tv, 35.00 AS br, 2.0000 AS ir, 2 AS so
  UNION ALL
  SELECT 'S020202000000' AS code, 36 AS tv, 25.00 AS br, 2.1500 AS ir, 3 AS so
  UNION ALL
  SELECT 'S030000000000' AS code, 60 AS tv, 100.00 AS br, 0.0000 AS ir, 1 AS so
) t ON t.code = c.coa_node_code
WHERE c.scheme_id = @sid;

-- ----------------------------------------------------------------------------
-- PART 6 回填计数
-- ----------------------------------------------------------------------------
UPDATE prcp_sim_node_config c SET
  term_count = (SELECT COUNT(*) FROM prcp_sim_term_ratio t
                  WHERE t.config_id = c.id AND t.is_deleted = 0)
WHERE c.scheme_id = @sid;

UPDATE prcp_sim_scheme s SET
  config_node_count = (SELECT COUNT(*) FROM prcp_sim_node_config c
                      WHERE c.scheme_id = s.id AND c.is_deleted = 0)
WHERE s.id = @sid;

-- ----------------------------------------------------------------------------
-- PART 7 验证
-- ----------------------------------------------------------------------------
SELECT '====== 方案初始化完成 ======' AS status;
SELECT id, scheme_code, scheme_name, data_date, config_node_count, status
FROM prcp_sim_scheme WHERE id = @sid;

-- growth_type 分布
SELECT g.growth_type AS gt, d.dict_label AS 名称, COUNT(*) AS 节点数
FROM prcp_sim_growth_config g
LEFT JOIN sys_dict d ON d.dict_type='PRCP_GROWTH_TYPE' AND d.dict_key=g.growth_type
WHERE g.scheme_id = @sid AND g.is_deleted = 0
GROUP BY g.growth_type, d.dict_label ORDER BY g.growth_type;

-- rhythm_type 分布
SELECT rhythm_type, COUNT(*) AS 节点数 FROM prcp_sim_node_config
WHERE scheme_id = @sid AND is_deleted = 0 GROUP BY rhythm_type ORDER BY rhythm_type;

-- 是否模型测算分布
SELECT is_model_calc, COUNT(*) AS 节点数 FROM prcp_sim_node_config
WHERE scheme_id = @sid AND is_deleted = 0 GROUP BY is_model_calc ORDER BY is_model_calc;

-- 配置完整性检查
SELECT
  (SELECT COUNT(*) FROM prcp_sim_node_config WHERE scheme_id=@sid AND is_deleted=0) AS node_cfg,
  (SELECT COUNT(*) FROM prcp_sim_growth_config WHERE scheme_id=@sid AND is_deleted=0) AS growth_cfg,
  (SELECT COUNT(DISTINCT config_id) FROM prcp_sim_rhythm WHERE config_id IN
     (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid) AND is_deleted=0) AS rhythm_cfg,
  (SELECT COUNT(DISTINCT config_id) FROM prcp_sim_term_ratio WHERE config_id IN
     (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid) AND is_deleted=0) AS term_cfg;

-- 权重和校验（应全部 = 100）
SELECT r.config_id, c.coa_node_code, ROUND(SUM(r.weight),4) AS 权重和, COUNT(*) AS 月数
FROM prcp_sim_rhythm r
JOIN prcp_sim_node_config c ON c.id = r.config_id
WHERE c.scheme_id = @sid AND r.is_deleted = 0
GROUP BY r.config_id, c.coa_node_code
HAVING ROUND(SUM(r.weight),4) <> 100.0000 OR COUNT(*) <> 12;
-- （无输出 = 全部通过）

-- 占比和校验（应全部 = 100）
SELECT t.config_id, c.coa_node_code, ROUND(SUM(t.business_ratio),4) AS 占比和, COUNT(*) AS 行数
FROM prcp_sim_term_ratio t
JOIN prcp_sim_node_config c ON c.id = t.config_id
WHERE c.scheme_id = @sid AND t.is_deleted = 0
GROUP BY t.config_id, c.coa_node_code
HAVING ROUND(SUM(t.business_ratio),4) <> 100.0000;
-- （无输出 = 全部通过）
