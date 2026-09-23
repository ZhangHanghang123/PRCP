-- PRCP 指标计量系数维护（V1）2026-09-23
-- 1) 指标计量系数表 prcp_metric_coefficient
-- 2) sys_dict 字典 METRIC_TYPE（指标类型：ROE / CET1 / LCR / NSFR / DELTA_EVE）
-- 3) sys_dict 字典 METRIC_UNIT（指标计量单位：百分比/绝对值）

CREATE TABLE IF NOT EXISTS prcp_metric_coefficient (
  id              VARCHAR(128) NOT NULL,
  scheme_id       INT          NOT NULL                COMMENT '账户册方案 id',
  scheme_code     VARCHAR(64)  NOT NULL                COMMENT '账户册方案编码',
  node_id         INT          NOT NULL                COMMENT '账户册节点 id',
  node_code       VARCHAR(64)  NOT NULL                COMMENT '账户册编码',
  metric_type     VARCHAR(32)  NOT NULL                COMMENT '指标类型（字典 METRIC_TYPE）',
  metric_code     VARCHAR(32)  NOT NULL                COMMENT '指标码值（与 metric_type 一致）',
  data_date       DATE         NOT NULL                COMMENT '数据日期',
  current_value   DECIMAL(20,6) DEFAULT 0              COMMENT '当前值',
  y1_value        DECIMAL(20,6) DEFAULT 0              COMMENT '未来一年值',
  y2_value        DECIMAL(20,6) DEFAULT 0              COMMENT '未来两年值',
  y3_value        DECIMAL(20,6) DEFAULT 0              COMMENT '未来三年值',
  y4_value        DECIMAL(20,6) DEFAULT 0              COMMENT '未来四年值',
  y5_value        DECIMAL(20,6) DEFAULT 0              COMMENT '未来五年值',
  unit            VARCHAR(16)  DEFAULT 'PERCENT'       COMMENT '计量单位（字典 METRIC_UNIT）',
  description     VARCHAR(500)                         COMMENT '备注',
  status          VARCHAR(16)  DEFAULT 'ACTIVE'        COMMENT 'ACTIVE / DISABLED',
  is_deleted      TINYINT(1)   DEFAULT 0,
  created_by      INT,
  updated_by      INT,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_mc_unique (scheme_code, node_code, metric_code, data_date, is_deleted),
  KEY idx_mc_scheme_date (scheme_id, data_date),
  KEY idx_mc_node_date   (node_id, data_date),
  KEY idx_mc_metric_type (metric_type, data_date),
  KEY idx_mc_updated     (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标计量系数维护';

-- 指标类型字典 METRIC_TYPE
INSERT INTO sys_dict (dict_type, dict_key, dict_label, sort_order, status, description, created_by, updated_by)
SELECT * FROM (
  SELECT 'METRIC_TYPE' AS dict_type, 'ROE'        AS dict_key, 'ROE 净资产收益率'        AS dict_label, 10 AS sort_order, 'ACTIVE' AS status, 'Return on Equity' AS description, 1 AS created_by, 1 AS updated_by UNION ALL
  SELECT 'METRIC_TYPE',         'CET1',                '核心一级资本充足率',         20,            'ACTIVE',           'Common Equity Tier 1 Ratio',                1,            1 UNION ALL
  SELECT 'METRIC_TYPE',         'LCR',                 '流动性覆盖率（LCR）',        30,            'ACTIVE',           'Liquidity Coverage Ratio',                   1,            1 UNION ALL
  SELECT 'METRIC_TYPE',         'NSFR',                '净稳定资金比例（NSFR）',     40,            'ACTIVE',           'Net Stable Funding Ratio',                   1,            1 UNION ALL
  SELECT 'METRIC_TYPE',         'DELTA_EVE',           '△EVE 利率风险经济价值变动',   50,            'ACTIVE',           'Interest Rate Risk in Banking Book (EVE)',    1,            1
) t
WHERE NOT EXISTS (
  SELECT 1 FROM sys_dict d
  WHERE d.dict_type='METRIC_TYPE' AND d.dict_key=t.dict_key AND d.is_deleted=0
);

-- 计量单位字典 METRIC_UNIT
INSERT INTO sys_dict (dict_type, dict_key, dict_label, sort_order, status, description, created_by, updated_by)
SELECT * FROM (
  SELECT 'METRIC_UNIT' AS dict_type, 'PERCENT'    AS dict_key, '百分比（%）'         AS dict_label, 10 AS sort_order, 'ACTIVE' AS status, '如 12.5 表示 12.5%'  AS description, 1 AS created_by, 1 AS updated_by UNION ALL
  SELECT 'METRIC_UNIT',         'ABSOLUTE',                 '绝对值',              20,            'ACTIVE',           '保留 6 位小数',                1,            1
) t
WHERE NOT EXISTS (
  SELECT 1 FROM sys_dict d
  WHERE d.dict_type='METRIC_UNIT' AND d.dict_key=t.dict_key AND d.is_deleted=0
);