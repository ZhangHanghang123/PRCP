-- 根据 账户册0929_结构表.xlsx 造账户册方案数据（方案编码 ZX_COA）
-- 生成时间：2026-09-29
-- 节点数：57（按层级分布：{1: 3, 2: 4, 3: 10, 4: 17, 5: 17, 6: 6}）

SET @admin_id = 1;

-- 1. 插入账户册方案
INSERT INTO prcp_coa_scheme
  (scheme_code, scheme_name, description, status, node_count, is_deleted, created_by, updated_by)
VALUES
  ('ZX_COA', '中信银行账户册方案 ZX_COA', '依据账户册0929_结构表.xlsx 拆分更新；3 大板块（资产/负债/权益），共 57 个节点', 'ACTIVE', 57, 0, @admin_id, @admin_id);

SET @scheme_id = LAST_INSERT_ID();

-- 层级 1（3 个节点）
INSERT INTO prcp_coa_node
  (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, is_deleted, created_by, updated_by)
VALUES
  (@scheme_id, 'S010000000000', '总资产', 0, 1, 'ASSET', '/S010000000000/', 1, 'ACTIVE', 'ZX_COA 节点 - 总资产', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020000000000', '总负债', 0, 1, 'LIABILITY', '/S020000000000/', 2, 'ACTIVE', 'ZX_COA 节点 - 总负债', 0, @admin_id, @admin_id),
  (@scheme_id, 'S030000000000', '所有者权益', 0, 1, 'EQUITY', '/S030000000000/', 3, 'ACTIVE', 'ZX_COA 节点 - 所有者权益', 0, @admin_id, @admin_id);

SET @first_id_lv1 = LAST_INSERT_ID();
SET @n_S010000000000 = @first_id_lv1;
SET @n_S020000000000 = @first_id_lv1 + 1;
SET @n_S030000000000 = @first_id_lv1 + 2;

-- 层级 2（4 个节点）
INSERT INTO prcp_coa_node
  (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, is_deleted, created_by, updated_by)
VALUES
  (@scheme_id, 'S010100000000', '（一）人民币小计', @n_S010000000000, 2, 'ASSET', '/S010000000000/S010100000000/', 1, 'ACTIVE', 'ZX_COA 节点 - （一）人民币小计', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010200000000', '（二）外币小计（美元）', @n_S010000000000, 2, 'ASSET', '/S010000000000/S010200000000/', 2, 'ACTIVE', 'ZX_COA 节点 - （二）外币小计（美元）', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020100000000', '（一）人民币小计', @n_S020000000000, 2, 'LIABILITY', '/S020000000000/S020100000000/', 3, 'ACTIVE', 'ZX_COA 节点 - （一）人民币小计', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020200000000', '（二）外币小计（美元）', @n_S020000000000, 2, 'LIABILITY', '/S020000000000/S020200000000/', 4, 'ACTIVE', 'ZX_COA 节点 - （二）外币小计（美元）', 0, @admin_id, @admin_id);

SET @first_id_lv2 = LAST_INSERT_ID();
SET @n_S010100000000 = @first_id_lv2;
SET @n_S010200000000 = @first_id_lv2 + 1;
SET @n_S020100000000 = @first_id_lv2 + 2;
SET @n_S020200000000 = @first_id_lv2 + 3;

-- 层级 3（10 个节点）
INSERT INTO prcp_coa_node
  (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, is_deleted, created_by, updated_by)
VALUES
  (@scheme_id, 'S010101000000', '1.境内人民币各项贷款', @n_S010100000000, 3, 'ASSET', '/S010000000000/S010100000000/S010101000000/', 1, 'ACTIVE', 'ZX_COA 节点 - 1.境内人民币各项贷款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102000000', '2.人民币非信贷类业务', @n_S010100000000, 3, 'ASSET', '/S010000000000/S010100000000/S010102000000/', 2, 'ACTIVE', 'ZX_COA 节点 - 2.人民币非信贷类业务', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010103000000', '3.人民币非生息资产', @n_S010100000000, 3, 'ASSET', '/S010000000000/S010100000000/S010103000000/', 3, 'ACTIVE', 'ZX_COA 节点 - 3.人民币非生息资产', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010201000000', '1.外币贷款', @n_S010200000000, 3, 'ASSET', '/S010000000000/S010200000000/S010201000000/', 4, 'ACTIVE', 'ZX_COA 节点 - 1.外币贷款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010202000000', '2.外币非信贷资产', @n_S010200000000, 3, 'ASSET', '/S010000000000/S010200000000/S010202000000/', 5, 'ACTIVE', 'ZX_COA 节点 - 2.外币非信贷资产', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010203000000', '3.外币非生息资产', @n_S010200000000, 3, 'ASSET', '/S010000000000/S010200000000/S010203000000/', 6, 'ACTIVE', 'ZX_COA 节点 - 3.外币非生息资产', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020101000000', '1.境内人民币自营存款', @n_S020100000000, 3, 'LIABILITY', '/S020000000000/S020100000000/S020101000000/', 7, 'ACTIVE', 'ZX_COA 节点 - 1.境内人民币自营存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102000000', '2.人民币市场化负债', @n_S020100000000, 3, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/', 8, 'ACTIVE', 'ZX_COA 节点 - 2.人民币市场化负债', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020201000000', '1.外币存款', @n_S020200000000, 3, 'LIABILITY', '/S020000000000/S020200000000/S020201000000/', 9, 'ACTIVE', 'ZX_COA 节点 - 1.外币存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020202000000', '2.外币市场化负债', @n_S020200000000, 3, 'LIABILITY', '/S020000000000/S020200000000/S020202000000/', 10, 'ACTIVE', 'ZX_COA 节点 - 2.外币市场化负债', 0, @admin_id, @admin_id);

SET @first_id_lv3 = LAST_INSERT_ID();
SET @n_S010101000000 = @first_id_lv3;
SET @n_S010102000000 = @first_id_lv3 + 1;
SET @n_S010103000000 = @first_id_lv3 + 2;
SET @n_S010201000000 = @first_id_lv3 + 3;
SET @n_S010202000000 = @first_id_lv3 + 4;
SET @n_S010203000000 = @first_id_lv3 + 5;
SET @n_S020101000000 = @first_id_lv3 + 6;
SET @n_S020102000000 = @first_id_lv3 + 7;
SET @n_S020201000000 = @first_id_lv3 + 8;
SET @n_S020202000000 = @first_id_lv3 + 9;

-- 层级 4（17 个节点）
INSERT INTO prcp_coa_node
  (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, is_deleted, created_by, updated_by)
VALUES
  (@scheme_id, 'S010101010000', '1.1.对公一般贷款', @n_S010101000000, 4, 'ASSET', '/S010000000000/S010100000000/S010101000000/S010101010000/', 1, 'ACTIVE', 'ZX_COA 节点 - 1.1.对公一般贷款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010101020000', '1.2.个人贷款', @n_S010101000000, 4, 'ASSET', '/S010000000000/S010100000000/S010101000000/S010101020000/', 2, 'ACTIVE', 'ZX_COA 节点 - 1.2.个人贷款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010101030000', '1.3.信用卡贷款', @n_S010101000000, 4, 'ASSET', '/S010000000000/S010100000000/S010101000000/S010101030000/', 3, 'ACTIVE', 'ZX_COA 节点 - 1.3.信用卡贷款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010101040000', '1.4.票据贴现', @n_S010101000000, 4, 'ASSET', '/S010000000000/S010100000000/S010101000000/S010101040000/', 4, 'ACTIVE', 'ZX_COA 节点 - 1.4.票据贴现', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010101050000', '1.5.非银贷款', @n_S010101000000, 4, 'ASSET', '/S010000000000/S010100000000/S010101000000/S010101050000/', 5, 'ACTIVE', 'ZX_COA 节点 - 1.5.非银贷款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102010000', '2.1.债券投资', @n_S010102000000, 4, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/', 6, 'ACTIVE', 'ZX_COA 节点 - 2.1.债券投资', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102020000', '2.2.结构化融资', @n_S010102000000, 4, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102020000/', 7, 'ACTIVE', 'ZX_COA 节点 - 2.2.结构化融资', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102030000', '2.3.同业资产（不含拆放非银）', @n_S010102000000, 4, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102030000/', 8, 'ACTIVE', 'ZX_COA 节点 - 2.3.同业资产（不含拆放非银）', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102040000', '2.4.存款准备金', @n_S010102000000, 4, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102040000/', 9, 'ACTIVE', 'ZX_COA 节点 - 2.4.存款准备金', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010103010000', '3.1.FVTPL类资产', @n_S010103000000, 4, 'ASSET', '/S010000000000/S010100000000/S010103000000/S010103010000/', 10, 'ACTIVE', 'ZX_COA 节点 - 3.1.FVTPL类资产', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010103020000', '3.2.其他非生息资产', @n_S010103000000, 4, 'ASSET', '/S010000000000/S010100000000/S010103000000/S010103020000/', 11, 'ACTIVE', 'ZX_COA 节点 - 3.2.其他非生息资产', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010202010000', '2.1.外币债券', @n_S010202000000, 4, 'ASSET', '/S010000000000/S010200000000/S010202000000/S010202010000/', 12, 'ACTIVE', 'ZX_COA 节点 - 2.1.外币债券', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010202020000', '2.2.同业资产', @n_S010202000000, 4, 'ASSET', '/S010000000000/S010200000000/S010202000000/S010202020000/', 13, 'ACTIVE', 'ZX_COA 节点 - 2.2.同业资产', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020101010000', '1.1.对公存款', @n_S020101000000, 4, 'LIABILITY', '/S020000000000/S020100000000/S020101000000/S020101010000/', 14, 'ACTIVE', 'ZX_COA 节点 - 1.1.对公存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020101020000', '1.2.零售存款', @n_S020101000000, 4, 'LIABILITY', '/S020000000000/S020100000000/S020101000000/S020101020000/', 15, 'ACTIVE', 'ZX_COA 节点 - 1.2.零售存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102010000', '2.2.1同业负债', @n_S020102000000, 4, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102010000/', 16, 'ACTIVE', 'ZX_COA 节点 - 2.2.1同业负债', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102020000', '2.2.2央行借款', @n_S020102000000, 4, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102020000/', 17, 'ACTIVE', 'ZX_COA 节点 - 2.2.2央行借款', 0, @admin_id, @admin_id);

SET @first_id_lv4 = LAST_INSERT_ID();
SET @n_S010101010000 = @first_id_lv4;
SET @n_S010101020000 = @first_id_lv4 + 1;
SET @n_S010101030000 = @first_id_lv4 + 2;
SET @n_S010101040000 = @first_id_lv4 + 3;
SET @n_S010101050000 = @first_id_lv4 + 4;
SET @n_S010102010000 = @first_id_lv4 + 5;
SET @n_S010102020000 = @first_id_lv4 + 6;
SET @n_S010102030000 = @first_id_lv4 + 7;
SET @n_S010102040000 = @first_id_lv4 + 8;
SET @n_S010103010000 = @first_id_lv4 + 9;
SET @n_S010103020000 = @first_id_lv4 + 10;
SET @n_S010202010000 = @first_id_lv4 + 11;
SET @n_S010202020000 = @first_id_lv4 + 12;
SET @n_S020101010000 = @first_id_lv4 + 13;
SET @n_S020101020000 = @first_id_lv4 + 14;
SET @n_S020102010000 = @first_id_lv4 + 15;
SET @n_S020102020000 = @first_id_lv4 + 16;

-- 层级 5（17 个节点）
INSERT INTO prcp_coa_node
  (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, is_deleted, created_by, updated_by)
VALUES
  (@scheme_id, 'S010102010100', '2.1.1金市自营债券', @n_S010102010000, 5, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010100/', 1, 'ACTIVE', 'ZX_COA 节点 - 2.1.1金市自营债券', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102010200', '2.1.2司库债券', @n_S010102010000, 5, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010200/', 2, 'ACTIVE', 'ZX_COA 节点 - 2.1.2司库债券', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010103020100', '3.2.1. 其中：现金', @n_S010103020000, 5, 'ASSET', '/S010000000000/S010100000000/S010103000000/S010103020000/S010103020100/', 3, 'ACTIVE', 'ZX_COA 节点 - 3.2.1. 其中：现金', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010103020200', '3.2.2. 其中：其它', @n_S010103020000, 5, 'ASSET', '/S010000000000/S010100000000/S010103000000/S010103020000/S010103020200/', 4, 'ACTIVE', 'ZX_COA 节点 - 3.2.2. 其中：其它', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020101010100', '1.1.1对公活期存款', @n_S020101010000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020101000000/S020101010000/S020101010100/', 5, 'ACTIVE', 'ZX_COA 节点 - 1.1.1对公活期存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020101010200', '1.1.2对公定期存款', @n_S020101010000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020101000000/S020101010000/S020101010200/', 6, 'ACTIVE', 'ZX_COA 节点 - 1.1.2对公定期存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020101020100', '1.2.1零售活期存款', @n_S020101020000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020101000000/S020101020000/S020101020100/', 7, 'ACTIVE', 'ZX_COA 节点 - 1.2.1零售活期存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020101020200', '1.2.2零售定期存款', @n_S020101020000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020101000000/S020101020000/S020101020200/', 8, 'ACTIVE', 'ZX_COA 节点 - 1.2.2零售定期存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102010100', '2.2.1.1货币市场同业拆入', @n_S020102010000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102010000/S020102010100/', 9, 'ACTIVE', 'ZX_COA 节点 - 2.2.1.1货币市场同业拆入', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102010200', '2.2.1.2货币市场债券回购', @n_S020102010000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102010000/S020102010200/', 10, 'ACTIVE', 'ZX_COA 节点 - 2.2.1.2货币市场债券回购', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102010300', '2.2.1.3同业存单（NCD）', @n_S020102010000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102010000/S020102010300/', 11, 'ACTIVE', 'ZX_COA 节点 - 2.2.1.3同业存单（NCD）', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102010400', '2.2.1.4同业存款', @n_S020102010000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102010000/S020102010400/', 12, 'ACTIVE', 'ZX_COA 节点 - 2.2.1.4同业存款', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102010500', '2.2.1.5票据转贴现回购', @n_S020102010000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102010000/S020102010500/', 13, 'ACTIVE', 'ZX_COA 节点 - 2.2.1.5票据转贴现回购', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102020100', '2.2.2.1公开市场回购（买断）', @n_S020102020000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102020000/S020102020100/', 14, 'ACTIVE', 'ZX_COA 节点 - 2.2.2.1公开市场回购（买断）', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102020200', '2.2.2.2中期借贷便利（MLF）', @n_S020102020000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102020000/S020102020200/', 15, 'ACTIVE', 'ZX_COA 节点 - 2.2.2.2中期借贷便利（MLF）', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102020300', '2.2.2.3结构性货币政策工具', @n_S020102020000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102020000/S020102020300/', 16, 'ACTIVE', 'ZX_COA 节点 - 2.2.2.3结构性货币政策工具', 0, @admin_id, @admin_id),
  (@scheme_id, 'S020102020400', '2.2.2.4票据再贴现回购', @n_S020102020000, 5, 'LIABILITY', '/S020000000000/S020100000000/S020102000000/S020102020000/S020102020400/', 17, 'ACTIVE', 'ZX_COA 节点 - 2.2.2.4票据再贴现回购', 0, @admin_id, @admin_id);

SET @first_id_lv5 = LAST_INSERT_ID();
SET @n_S010102010100 = @first_id_lv5;
SET @n_S010102010200 = @first_id_lv5 + 1;
SET @n_S010103020100 = @first_id_lv5 + 2;
SET @n_S010103020200 = @first_id_lv5 + 3;
SET @n_S020101010100 = @first_id_lv5 + 4;
SET @n_S020101010200 = @first_id_lv5 + 5;
SET @n_S020101020100 = @first_id_lv5 + 6;
SET @n_S020101020200 = @first_id_lv5 + 7;
SET @n_S020102010100 = @first_id_lv5 + 8;
SET @n_S020102010200 = @first_id_lv5 + 9;
SET @n_S020102010300 = @first_id_lv5 + 10;
SET @n_S020102010400 = @first_id_lv5 + 11;
SET @n_S020102010500 = @first_id_lv5 + 12;
SET @n_S020102020100 = @first_id_lv5 + 13;
SET @n_S020102020200 = @first_id_lv5 + 14;
SET @n_S020102020300 = @first_id_lv5 + 15;
SET @n_S020102020400 = @first_id_lv5 + 16;

-- 层级 6（6 个节点）
INSERT INTO prcp_coa_node
  (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, is_deleted, created_by, updated_by)
VALUES
  (@scheme_id, 'S010102010101', '2.1.1.1AC', @n_S010102010100, 6, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010100/S010102010101/', 1, 'ACTIVE', 'ZX_COA 节点 - 2.1.1.1AC', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102010102', '2.1.1.2FVOCI', @n_S010102010100, 6, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010100/S010102010102/', 2, 'ACTIVE', 'ZX_COA 节点 - 2.1.1.2FVOCI', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102010103', '2.1.1.3FVTPL', @n_S010102010100, 6, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010100/S010102010103/', 3, 'ACTIVE', 'ZX_COA 节点 - 2.1.1.3FVTPL', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102010201', '2.1.2.1AC', @n_S010102010200, 6, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010200/S010102010201/', 4, 'ACTIVE', 'ZX_COA 节点 - 2.1.2.1AC', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102010202', '2.1.2.2FVOCI', @n_S010102010200, 6, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010200/S010102010202/', 5, 'ACTIVE', 'ZX_COA 节点 - 2.1.2.2FVOCI', 0, @admin_id, @admin_id),
  (@scheme_id, 'S010102010203', '2.1.2.3FVTPL', @n_S010102010200, 6, 'ASSET', '/S010000000000/S010100000000/S010102000000/S010102010000/S010102010200/S010102010203/', 6, 'ACTIVE', 'ZX_COA 节点 - 2.1.2.3FVTPL', 0, @admin_id, @admin_id);

SET @first_id_lv6 = LAST_INSERT_ID();
SET @n_S010102010101 = @first_id_lv6;
SET @n_S010102010102 = @first_id_lv6 + 1;
SET @n_S010102010103 = @first_id_lv6 + 2;
SET @n_S010102010201 = @first_id_lv6 + 3;
SET @n_S010102010202 = @first_id_lv6 + 4;
SET @n_S010102010203 = @first_id_lv6 + 5;

-- 2. 更新方案节点计数
UPDATE prcp_coa_scheme
SET node_count = (SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id = @scheme_id AND is_deleted = 0)
WHERE id = @scheme_id;

-- 3. 验证
SELECT '4. 验证 ZX_COA 方案：' AS info;
SELECT s.id, s.scheme_code, s.scheme_name, s.status, s.node_count,
       (SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id = s.id) AS actual_nodes
FROM prcp_coa_scheme s WHERE s.scheme_code = 'ZX_COA';