-- =============================================================================
-- PRCP 新业务模拟 — 节奏配置 (Rhythm Configuration)
-- 功能：节点参数配置页增加"节奏配置"选项
--   1 = 线性（默认）：新业务按 12 个月均匀分布（每月 100/12 ≈ 8.3333%）
--   2 = 自定义：按 prcp_sim_rhythm 表配置的 12 个月权重分布
-- 数据日期：2026-10-20
-- =============================================================================

USE prcp_db;

-- -----------------------------------------------------------------------------
-- 1. 新建 prcp_sim_rhythm 表（节奏配置 — 12 个月权重）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prcp_sim_rhythm (
  id            bigint          NOT NULL AUTO_INCREMENT COMMENT '主键',
  config_id     bigint          NOT NULL                COMMENT 'FK → prcp_sim_node_config.id',
  scheme_id     bigint          NOT NULL DEFAULT 0      COMMENT '冗余：方案 id（便于按方案查询）',
  coa_node_id   bigint          NOT NULL DEFAULT 0      COMMENT '冗余：账户册节点 id',
  month_no      int             NOT NULL                COMMENT '月份序号（1~12）',
  month_label   varchar(16)     DEFAULT NULL            COMMENT '月份标签（如 1月 / M1）',
  weight        decimal(8,4)    NOT NULL DEFAULT 0.0000 COMMENT '权重（%），12 个月之和必须 = 100',
  sort_order    int             DEFAULT 0               COMMENT '显示顺序（= month_no）',
  remark        varchar(255)    DEFAULT NULL,
  is_deleted    tinyint(1)      DEFAULT 0,
  created_by    bigint          DEFAULT NULL,
  updated_by    bigint          DEFAULT NULL,
  created_at    datetime        DEFAULT CURRENT_TIMESTAMP,
  updated_at    datetime        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_config_month (config_id, month_no),
  KEY idx_config (config_id, is_deleted),
  KEY idx_scheme (scheme_id, is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新业务模拟 — 节奏配置（12 个月权重分布）';

-- -----------------------------------------------------------------------------
-- 2. prcp_sim_node_config 加 rhythm_type 列（1=线性 2=自定义）
-- -----------------------------------------------------------------------------
ALTER TABLE prcp_sim_node_config
  ADD COLUMN rhythm_type TINYINT(1) NOT NULL DEFAULT 1
  COMMENT '节奏配置类型 (1=线性, 2=自定义)'
  AFTER is_model_calc;

-- -----------------------------------------------------------------------------
-- 3. sys_dict 加 PRCP_RHYTHM_TYPE 字典（1=线性 2=自定义）
-- -----------------------------------------------------------------------------
DELETE FROM sys_dict WHERE dict_type = 'PRCP_RHYTHM_TYPE';

INSERT INTO sys_dict
  (dict_type, dict_key, dict_label, color, sort_order, status, description, created_by, updated_by)
VALUES
  ('PRCP_RHYTHM_TYPE', '1', '线性',   'blue',   10, 'ACTIVE', '线性节奏：12 个月均匀分布（每月 8.3333%）', 1, 1),
  ('PRCP_RHYTHM_TYPE', '2', '自定义', 'orange', 20, 'ACTIVE', '自定义节奏：按 prcp_sim_rhythm 配置的 12 个月权重', 1, 1);

-- -----------------------------------------------------------------------------
-- 4. 初始化已有节点配置的节奏配置数据（默认线性 → 12 个月均匀）
-- -----------------------------------------------------------------------------
-- 为所有已存在的 node_config 插入 12 个月线性权重（仅当该 config 尚无节奏数据时）
INSERT INTO prcp_sim_rhythm
  (config_id, scheme_id, coa_node_id, month_no, month_label, weight, sort_order, remark, is_deleted, created_by, updated_by)
SELECT
  c.id, c.scheme_id, c.coa_node_id,
  m.mo,
  CONCAT(m.mo, '月'),
  ROUND(100.0 / 12, 4),
  m.mo,
  '默认线性节奏（12 个月均匀）',
  0, 1, 1
FROM prcp_sim_node_config c
CROSS JOIN (
  SELECT 1 AS mo UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
  UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8
  UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
) m
WHERE c.is_deleted = 0
  AND NOT EXISTS (
    SELECT 1 FROM prcp_sim_rhythm r
    WHERE r.config_id = c.id AND r.is_deleted = 0
  );

-- -----------------------------------------------------------------------------
-- 5. 验证
-- -----------------------------------------------------------------------------
SELECT '====== 节奏配置功能初始化完成 ======' AS status;

SELECT 'prcp_sim_rhythm（新建表）' AS tbl, COUNT(*) AS active_cnt,
       CONCAT('config_id × 12 月 = ', COUNT(DISTINCT config_id), ' × 12') AS note
FROM prcp_sim_rhythm WHERE is_deleted = 0
UNION ALL
SELECT 'prcp_sim_node_config.rhythm_type', COUNT(*), '1=线性（默认）'
FROM prcp_sim_node_config WHERE is_deleted = 0
UNION ALL
SELECT 'sys_dict PRCP_RHYTHM_TYPE', COUNT(*), '2 项：1=线性 2=自定义'
FROM sys_dict WHERE dict_type = 'PRCP_RHYTHM_TYPE' AND is_deleted = 0;

SELECT dict_key, dict_label, color, description FROM sys_dict
WHERE dict_type = 'PRCP_RHYTHM_TYPE' AND is_deleted = 0 ORDER BY sort_order;

SELECT config_id, scheme_id, coa_node_id, COUNT(*) AS month_cnt,
       ROUND(SUM(weight), 4) AS weight_sum
FROM prcp_sim_rhythm WHERE is_deleted = 0
GROUP BY config_id, scheme_id, coa_node_id;