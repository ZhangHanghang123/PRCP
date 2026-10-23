-- PRCP 中信银行账户册 ZX_CITIC_2026 数据同步脚本（服务器端）
-- 由 backend/scripts/gen_citic_coa_scheme.py 同源生成
-- 用法：mysql -uprcp -pPrcp@2026 prcp_db < zx_citic_2026_insert.sql

SET NAMES utf8mb4;
SET @scheme_id := NULL;

-- 0) 幂等检查：若方案已存在则中止
SELECT id INTO @existing_id FROM prcp_coa_scheme WHERE scheme_code='ZX_CITIC_2026' AND is_deleted=0 LIMIT 1;
SELECT IF(@existing_id IS NOT NULL, CONCAT('ABORT:id=', @existing_id), 'CONTINUE') AS __step0;

-- 1) 创建方案
INSERT INTO prcp_coa_scheme (scheme_code, scheme_name, description, status, node_count, created_by, updated_by)
VALUES ('ZX_CITIC_2026', '中信银行账户册 2026',
        '依据中信银行账户册结构整理：资产/负债/权益三大类，5 级层级，38 个节点。',
        'ACTIVE', 0, 1, 1);

SET @scheme_id := LAST_INSERT_ID();
SELECT @scheme_id AS scheme_id;

-- 2) 节点表（创建临时 code→id 映射表用于回填 parent_id）
DROP TEMPORARY TABLE IF EXISTS _tmp_node_id_map;
CREATE TEMPORARY TABLE _tmp_node_id_map (
  code VARCHAR(32) PRIMARY KEY,
  id BIGINT NOT NULL
) ENGINE=MEMORY;

-- Level 1 节点（parent 顶级）
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01000000000000', '总资产', NULL, 1, 'ASSET_GROUP', '/S01000000000000/', 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01000000000000', LAST_INSERT_ID());

INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02000000000000', '总负债', NULL, 1, 'LIAB_GROUP', '/S02000000000000/', 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02000000000000', LAST_INSERT_ID());

INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S03000000000000', '所有者权益', NULL, 1, 'EQUITY_LEAF', '/S03000000000000/', 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S03000000000000', LAST_INSERT_ID());


-- Level 2 节点
SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01000000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010000000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010000000000', '（一）人民币小计', @pid, 2, 'ASSET_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010000000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01000000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01020000000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01020000000000', '（二）外币小计（美元）', @pid, 2, 'ASSET_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01020000000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02000000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02010000000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02010000000000', '（一）人民币小计', @pid, 2, 'LIAB_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02010000000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02000000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02020000000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02020000000000', '（二）外币小计（美元）', @pid, 2, 'LIAB_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02020000000000', LAST_INSERT_ID());


-- Level 3 节点
SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010100000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010100000000', '1. 境内人民币各项贷款', @pid, 3, 'ASSET_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010100000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010200000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010200000000', '2. 人民币非信贷类业务', @pid, 3, 'ASSET_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010200000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010300000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010300000000', '3. 人民币非生息资产', @pid, 3, 'ASSET_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010300000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01020000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01020100000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01020100000000', '1. 外币贷款', @pid, 3, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01020100000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01020000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01020200000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01020200000000', '2. 外币非信贷资产', @pid, 3, 'ASSET_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01020200000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01020000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01020300000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01020300000000', '3. 外币非生息资产', @pid, 3, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01020300000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02010100000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02010100000000', '1. 境内人民币自营存款', @pid, 3, 'LIAB_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02010100000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02010200000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02010200000000', '2. 人民币市场化负债', @pid, 3, 'LIAB_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02010200000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02020000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02020100000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02020100000000', '1. 外币存款', @pid, 3, 'LIAB_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02020100000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02020000000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02020200000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02020200000000', '2. 外币市场化负债', @pid, 3, 'LIAB_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02020200000000', LAST_INSERT_ID());


-- Level 4 节点
SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010100000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010101000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010101000000', '1.1. 对公一般贷款', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010101000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010100000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010102000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010102000000', '1.2. 个人贷款', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010102000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010100000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010103000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010103000000', '1.3. 信用卡贷款', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010103000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010100000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010104000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010104000000', '1.4. 票据贴现', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010104000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010100000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010105000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010105000000', '1.5. 非银贷款', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010105000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010200000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010201000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010201000000', '2.1. 债券投资', @pid, 4, 'ASSET_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010201000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010200000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010202000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010202000000', '2.2. 结构化融资', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010202000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010200000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010203000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010203000000', '2.3. 同业资产（不含拆放非银）', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010203000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010200000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010204000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010204000000', '2.4. 存款准备金', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010204000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010300000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010301000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010301000000', '3.1. FVTPL类资产', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010301000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010300000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01010302000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01010302000000', '3.2. 其他非生息资产', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01010302000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01020200000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01020201000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01020201000000', '2.1. 外币债券', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01020201000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01020200000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S01020202000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S01020202000000', '2.2. 同业资产', @pid, 4, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S01020202000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010100000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02010101000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02010101000000', '1.1. 对公存款', @pid, 4, 'LIAB_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02010101000000', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010100000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S02010102000000', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S02010102000000', '1.2. 零售存款', @pid, 4, 'LIAB_GROUP', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S02010102000000', LAST_INSERT_ID());


-- Level 5 节点
SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010201000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S010102010100', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S010102010100', '2.1.1 金市自营债券', @pid, 5, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S010102010100', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S01010201000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S010102010200', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S010102010200', '2.1.2 司库债券', @pid, 5, 'ASSET_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S010102010200', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010101000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S020101010100', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S020101010100', '1.1.1 对公活期存款', @pid, 5, 'LIAB_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S020101010100', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010101000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S020101010200', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S020101010200', '1.1.2 对公定期存款', @pid, 5, 'LIAB_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S020101010200', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010102000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S020101020100', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S020101020100', '1.2.1 零售活期存款', @pid, 5, 'LIAB_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S020101020100', LAST_INSERT_ID());

SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m
  JOIN prcp_coa_node n ON n.id = m.id
  WHERE m.code='S02010102000000' LIMIT 1;
SET @path := CONCAT(@ppath, 'S020101020200', '/');
INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)
VALUES (@scheme_id, 'S020101020200', '1.2.2 零售定期存款', @pid, 5, 'LIAB_LEAF', @path, 0, 'ACTIVE', NULL, 1, 1);
INSERT INTO _tmp_node_id_map (code, id) VALUES ('S020101020200', LAST_INSERT_ID());


-- 3) 回填方案 node_count
UPDATE prcp_coa_scheme
SET node_count = (SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id=@scheme_id AND is_deleted=0)
WHERE id=@scheme_id;

-- 4) 验证
SELECT id, scheme_code, scheme_name, node_count, status FROM prcp_coa_scheme WHERE id=@scheme_id;
SELECT node_level, COUNT(*) AS cnt FROM prcp_coa_node WHERE scheme_id=@scheme_id AND is_deleted=0 GROUP BY node_level ORDER BY node_level;
SELECT node_type, COUNT(*) AS cnt FROM prcp_coa_node WHERE scheme_id=@scheme_id AND is_deleted=0 GROUP BY node_type ORDER BY node_type;

-- 5) 清理临时表
DROP TEMPORARY TABLE IF EXISTS _tmp_node_id_map;