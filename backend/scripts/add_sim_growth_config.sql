-- =============================================================================
-- PRCP 新业务模拟 — 新业务增长配置（Growth Configuration）
--
-- 改造背景：
--   原「上栏 · 新业务年化目标增长比例」只有 1 个 annual_growth_rate 字段，
--   无法表达未来 5 年分期增长的不同参数。本脚本将其拆表独立存储。
--
-- 增长方式（字典 PRCP_GROWTH_TYPE）：
--   1 = 目标增长百分比   unit = '%'     单位：%
--   2 = 目标增长绝对值   unit = 'ABS'   单位：万元 / 亿元（元）
--   3 = 增长百分比       unit = '%'     单位：%
--   4 = 增长值           unit = 'ABS'   单位：万元 / 亿元（元）
--
-- 参数值：year1_value ~ year5_value 共 5 列，分别对应第 1 ~ 5 年的增长参数
--
-- 关联维度：scheme_id / scheme_code（方案编码）+ coa_node_id / coa_node_code
--          （账户册编码）+ config_id（节点配置 id）
--
-- 数据日期：2026-10-21
-- =============================================================================

USE prcp_db;

-- -----------------------------------------------------------------------------
-- 1. 新建 prcp_sim_growth_config 表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prcp_sim_growth_config (
  id             bigint        NOT NULL AUTO_INCREMENT COMMENT '主键',
  -- 关联维度 1：方案
  scheme_id      bigint        NOT NULL                COMMENT '方案 id（→ prcp_sim_scheme.id）',
  scheme_code    varchar(32)   DEFAULT NULL            COMMENT '方案编码（冗余，如 SIM_BOND_INTERBANK）',
  scheme_name    varchar(64)   DEFAULT NULL            COMMENT '方案名称（冗余）',
  -- 关联维度 2：账户册
  coa_node_id    bigint        NOT NULL                COMMENT '账户册节点 id（→ prcp_coa_node.id）',
  coa_node_code  varchar(32)   DEFAULT NULL            COMMENT '账户册节点编码（冗余，如 S010101010000）',
  coa_node_name  varchar(128)  DEFAULT NULL            COMMENT '账户册节点名称（冗余）',
  -- 关联维度 3：节点配置
  config_id      bigint        NOT NULL                COMMENT '节点配置 id（→ prcp_sim_node_config.id）',
  -- 增长方式
  growth_type    tinyint(1)    NOT NULL DEFAULT 1      COMMENT '增长方式 (1=目标增长百分比 2=目标增长绝对值 3=增长百分比 4=增长值)',
  -- 5 年增长参数（第 1 ~ 5 年）
  year1_value    decimal(20,4) NOT NULL DEFAULT 0.0000 COMMENT '第 1 年增长参数',
  year2_value    decimal(20,4) NOT NULL DEFAULT 0.0000 COMMENT '第 2 年增长参数',
  year3_value    decimal(20,4) NOT NULL DEFAULT 0.0000 COMMENT '第 3 年增长参数',
  year4_value    decimal(20,4) NOT NULL DEFAULT 0.0000 COMMENT '第 4 年增长参数',
  year5_value    decimal(20,4) NOT NULL DEFAULT 0.0000 COMMENT '第 5 年增长参数',
  -- 单位与备注
  unit           varchar(16)   DEFAULT '%'             COMMENT '参数单位 (% / ABS 绝对值 / WAN 万元)',
  amount_unit    varchar(16)   DEFAULT NULL            COMMENT '绝对值单位 (WAN=万元 / YI=亿元)，growth_type=2/4 生效',
  remark         varchar(255)  DEFAULT NULL,
  is_deleted     tinyint(1)    DEFAULT 0,
  created_by     bigint        DEFAULT NULL,
  updated_by     bigint        DEFAULT NULL,
  created_at     datetime      DEFAULT CURRENT_TIMESTAMP,
  updated_at     datetime      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_config (config_id),
  KEY idx_scheme (scheme_id, is_deleted),
  KEY idx_coa_node (coa_node_id, is_deleted),
  KEY idx_growth_type (growth_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='新业务模拟 — 新业务增长配置（5 年分期增长参数）';

-- -----------------------------------------------------------------------------
-- 2. sys_dict 加 PRCP_GROWTH_TYPE 字典（4 种增长方式）
-- -----------------------------------------------------------------------------
DELETE FROM sys_dict WHERE dict_type = 'PRCP_GROWTH_TYPE';

INSERT INTO sys_dict
  (dict_type, dict_key, dict_label, color, sort_order, status, description, created_by, updated_by)
VALUES
  ('PRCP_GROWTH_TYPE', '1', '目标增长百分比', 'blue',   10, 'ACTIVE',
   '增长方式1：目标增长百分比 — 参数单位 %，表示目标增长率', 1, 1),
  ('PRCP_GROWTH_TYPE', '2', '目标增长绝对值', 'purple', 20, 'ACTIVE',
   '增长方式2：目标增长绝对值 — 参数单位为金额（万元/亿元），表示目标新增余额绝对额', 1, 1),
  ('PRCP_GROWTH_TYPE', '3', '增长百分比',     'cyan',   30, 'ACTIVE',
   '增长方式3：增长百分比 — 参数单位 %，表示期间增长率', 1, 1),
  ('PRCP_GROWTH_TYPE', '4', '增长值',         'gold',   40, 'ACTIVE',
   '增长方式4：增长值 — 参数单位为金额（万元/亿元），表示期末余额绝对额', 1, 1);

-- -----------------------------------------------------------------------------
-- 3. 迁移已有节点配置的 annual_growth_rate → year1_value
--    （原 annual_growth_rate 保留不动，作为向后兼容的兜底字段）
-- -----------------------------------------------------------------------------
INSERT INTO prcp_sim_growth_config
  (scheme_id, scheme_code, scheme_name,
   coa_node_id, coa_node_code, coa_node_name,
   config_id, growth_type,
   year1_value, year2_value, year3_value, year4_value, year5_value,
   unit, amount_unit, remark, is_deleted, created_by, updated_by)
SELECT
  c.scheme_id, s.scheme_code, s.scheme_name,
  c.coa_node_id, c.coa_node_code, n.node_name,
  c.id, 1,
  c.annual_growth_rate, 0.0000, 0.0000, 0.0000, 0.0000,
  '%', NULL,
  CONCAT('由 annual_growth_rate=', c.annual_growth_rate, ' 迁移（原「年化目标增长比例」）'),
  0, 1, 1
FROM prcp_sim_node_config c
LEFT JOIN prcp_sim_scheme s  ON s.id = c.scheme_id AND s.is_deleted = 0
LEFT JOIN prcp_coa_node n   ON n.id = c.coa_node_id AND n.is_deleted = 0
WHERE c.is_deleted = 0
  AND NOT EXISTS (
    SELECT 1 FROM prcp_sim_growth_config g WHERE g.config_id = c.id
  );

-- -----------------------------------------------------------------------------
-- 4. 验证
-- -----------------------------------------------------------------------------
SELECT '====== 新业务增长配置初始化完成 ======' AS status;

SELECT 'prcp_sim_growth_config（新建表）' AS tbl, COUNT(*) AS active_cnt,
       CONCAT(CONCAT(COUNT(DISTINCT config_id), ' 个节点配置 × 5 年参数'), '') AS note
FROM prcp_sim_growth_config WHERE is_deleted = 0
UNION ALL
SELECT 'sys_dict PRCP_GROWTH_TYPE', COUNT(*), '4 项：1~4 种增长方式'
FROM sys_dict WHERE dict_type = 'PRCP_GROWTH_TYPE' AND is_deleted = 0;

SELECT dict_key, dict_label, color, sort_order, description
FROM sys_dict WHERE dict_type = 'PRCP_GROWTH_TYPE' AND is_deleted = 0
ORDER BY sort_order;

SELECT
  g.id, g.scheme_code, g.coa_node_code, g.config_id,
  g.growth_type, g.unit,
  g.year1_value, g.year2_value, g.year3_value, g.year4_value, g.year5_value,
  g.remark
FROM prcp_sim_growth_config g
WHERE g.is_deleted = 0
ORDER BY g.id;