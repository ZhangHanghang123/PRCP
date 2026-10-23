-- ============================================================
-- PRCP LCR 参数补录表（V1）2026-09-30
-- 表 prcp_lcr_param + 字典 LCR_OPERATOR
-- ============================================================

CREATE TABLE IF NOT EXISTS prcp_lcr_param (
  id              VARCHAR(128) NOT NULL                COMMENT '主键：{scheme_code}_{node_code}_{YYYYMMDD}',
  scheme_id       INT          NOT NULL                COMMENT '账户册方案 id',
  scheme_code     VARCHAR(64)  NOT NULL                COMMENT '账户册方案编码',
  node_id         INT          NOT NULL                COMMENT '账户册节点 id',
  node_code       VARCHAR(64)  NOT NULL                COMMENT '账户册编码',
  node_name       VARCHAR(128) NOT NULL                COMMENT '账户册名称（冗余）',
  data_date       DATE         NOT NULL                COMMENT '数据日期',
  is_numerator    TINYINT(1)   DEFAULT 0               COMMENT '是否分子（0/1）',
  num_factor      DECIMAL(10,6) DEFAULT 0              COMMENT '分子折算系数',
  num_operator    VARCHAR(8)   DEFAULT '+'             COMMENT '分子运算符（字典 LCR_OPERATOR：+/-）',
  is_denominator  TINYINT(1)   DEFAULT 0               COMMENT '是否分母（0/1）',
  den_factor      DECIMAL(10,6) DEFAULT 0              COMMENT '分母折算系数',
  den_operator    VARCHAR(8)   DEFAULT '+'             COMMENT '分母运算符（字典 LCR_OPERATOR：+/-）',
  current_balance DECIMAL(20,4) DEFAULT 0              COMMENT '当前余额（元）',
  rule_note       VARCHAR(500)                        COMMENT 'LCR 规则说明',
  status          VARCHAR(16)  DEFAULT 'ACTIVE'        COMMENT 'ACTIVE/INACTIVE',
  is_deleted      TINYINT(1)   DEFAULT 0,
  created_by      INT,
  updated_by      INT,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_lcr_p_unique (scheme_code, node_code, data_date, is_deleted),
  KEY idx_lcr_p_scheme_date (scheme_id, data_date),
  KEY idx_lcr_p_node_date   (node_id, data_date),
  KEY idx_lcr_p_updated     (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='LCR 参数补录（按方案+节点+数据日期维护分子分母折算系数和运算符）';

-- 运算符字典（LCR_OPERATOR）
INSERT INTO sys_dict (dict_type, dict_key, dict_label, sort_order, status, description, created_by, updated_by)
SELECT * FROM (
  SELECT 'LCR_OPERATOR' AS dict_type, 'PLUS'  AS dict_key, '+ 加' AS dict_label, 10 AS sort_order, 'ACTIVE' AS status, '' AS description, 1 AS created_by, 1 AS updated_by UNION ALL
  SELECT 'LCR_OPERATOR',                  'MINUS', '- 减',                       20,            'ACTIVE',           '',                  1,            1
) t
WHERE NOT EXISTS (
  SELECT 1 FROM sys_dict d
  WHERE d.dict_type='LCR_OPERATOR' AND d.dict_key=t.dict_key AND d.is_deleted=0
);