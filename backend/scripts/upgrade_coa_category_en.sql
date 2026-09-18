-- ============================================================
-- PRCP COA 资产负债分类码值国际化改造
-- 日期：2026-09-18
--
-- 变更：
--   字典码值：资产/负债/权益/表外 → ASSET/LIABILITY/EQUITY/OFF_BALANCE
--   同步更新所有引用表的 data：
--   - prcp_data_basic.category
--   - prcp_data_reverse.category
--   - ZXCOA 路径（prcp_coa_node.path 中 L1_资产/负债/权益/表外 → L1_ASSET 等）
-- ============================================================

-- 1. 更新字典码值
UPDATE sys_dict SET dict_key='ASSET',       updated_at=NOW() WHERE dict_type='PRCP_COA_CATEGORY' AND dict_key='资产';
UPDATE sys_dict SET dict_key='LIABILITY',   updated_at=NOW() WHERE dict_type='PRCP_COA_CATEGORY' AND dict_key='负债';
UPDATE sys_dict SET dict_key='EQUITY',      updated_at=NOW() WHERE dict_type='PRCP_COA_CATEGORY' AND dict_key='权益';
UPDATE sys_dict SET dict_key='OFF_BALANCE', updated_at=NOW() WHERE dict_type='PRCP_COA_CATEGORY' AND dict_key='表外';

-- 2. 同步基础数据表
UPDATE prcp_data_basic SET category='ASSET'       WHERE category='资产';
UPDATE prcp_data_basic SET category='LIABILITY'   WHERE category='负债';
UPDATE prcp_data_basic SET category='EQUITY'      WHERE category='权益';
UPDATE prcp_data_basic SET category='OFF_BALANCE' WHERE category='表外';

-- 3. 同步反算结果表
UPDATE prcp_data_reverse SET category='ASSET'       WHERE category='资产';
UPDATE prcp_data_reverse SET category='LIABILITY'   WHERE category='负债';
UPDATE prcp_data_reverse SET category='EQUITY'      WHERE category='权益';
UPDATE prcp_data_reverse SET category='OFF_BALANCE' WHERE category='表外';

-- 4. 同步 ZXCOA 路径（path 中 L1_资产 / L1_负债 / L1_权益 / L1_表外 → L1_ASSET 等）
UPDATE prcp_coa_node SET path=REPLACE(path, '/L1_资产/', '/L1_ASSET/')       WHERE path LIKE '/L1_资产/%';
UPDATE prcp_coa_node SET path=REPLACE(path, '/L1_负债/', '/L1_LIABILITY/')   WHERE path LIKE '/L1_负债/%';
UPDATE prcp_coa_node SET path=REPLACE(path, '/L1_权益/', '/L1_EQUITY/')      WHERE path LIKE '/L1_权益/%';
UPDATE prcp_coa_node SET path=REPLACE(path, '/L1_表外/', '/L1_OFF_BALANCE/') WHERE path LIKE '/L1_表外/%';

-- 5. 验证
SELECT dict_type, dict_key, dict_label FROM sys_dict WHERE dict_type='PRCP_COA_CATEGORY';
SELECT category, COUNT(*) cnt FROM prcp_data_basic GROUP BY category ORDER BY category;
SELECT category, COUNT(*) cnt FROM prcp_data_reverse GROUP BY category ORDER BY category;
SELECT
  CASE
    WHEN path LIKE '/L1_ASSET/%' THEN 'ASSET'
    WHEN path LIKE '/L1_LIABILITY/%' THEN 'LIABILITY'
    WHEN path LIKE '/L1_EQUITY/%' THEN 'EQUITY'
    WHEN path LIKE '/L1_OFF_BALANCE/%' THEN 'OFF_BALANCE'
    ELSE 'OTHER'
  END AS cat,
  COUNT(*) cnt
FROM prcp_coa_node
WHERE node_level=1 AND is_deleted=0
GROUP BY cat;