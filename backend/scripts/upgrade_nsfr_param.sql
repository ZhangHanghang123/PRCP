-- ============================================================
-- PRCP NSFR 参数补录表（V1）2026-09-30
-- 表 prcp_nsfr_param + 字典 NSFR_OPERATOR
-- ============================================================

CREATE TABLE IF NOT EXISTS prcp_nsfr_param (
  id              VARCHAR(128) NOT NULL                COMMENT '主键：{scheme_code}_{node_code}_{YYYYMMDD}',
  scheme_id       INT          NOT NULL                COMMENT '账户册方案 id',
  scheme_code     VARCHAR(64)  NOT NULL                COMMENT '账户册方案编码',
  node_id         INT          NOT NULL                COMMENT '账户册节点 id',
  node_code       VARCHAR(64)  NOT NULL                COMMENT '账户册编码',
  node_name       VARCHAR(128) NOT NULL                COMMENT '账户册名称（冗余）',
  data_date       DATE         NOT NULL                COMMENT '数据日期',
  is_asf          TINYINT(1)   DEFAULT 0               COMMENT '是否ASF（可用稳定资金）（0/1）',
  asf_factor      DECIMAL(10,6) DEFAULT 0              COMMENT 'ASF 折算系数',
  asf_operator    VARCHAR(8)   DEFAULT '+'             COMMENT 'ASF 运算符（字典 NSFR_OPERATOR：+/-）',
  is_rsf          TINYINT(1)   DEFAULT 0               COMMENT '是否RSF（所需稳定资金）（0/1）',
  rsf_factor      DECIMAL(10,6) DEFAULT 0              COMMENT 'RSF 折算系数',
  rsf_operator    VARCHAR(8)   DEFAULT '+'             COMMENT 'RSF 运算符（字典 NSFR_OPERATOR：+/-）',
  rule_note       VARCHAR(500)                        COMMENT 'NSFR 规则说明',
  status          VARCHAR(16)  DEFAULT 'ACTIVE'        COMMENT 'ACTIVE/INACTIVE',
  is_deleted      TINYINT(1)   DEFAULT 0,
  created_by      INT,
  updated_by      INT,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_nsfr_p_unique (scheme_code, node_code, data_date, is_deleted),
  KEY idx_nsfr_p_scheme_date (scheme_id, data_date),
  KEY idx_nsfr_p_node_date   (node_id, data_date),
  KEY idx_nsfr_p_updated     (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='NSFR 参数补录（按方案+节点+数据日期维护 ASF/RSF 折算系数和运算符）';

-- 运算符字典（NSFR_OPERATOR）
INSERT INTO sys_dict (dict_type, dict_key, dict_label, sort_order, status, description, created_by, updated_by)
SELECT * FROM (
  SELECT 'NSFR_OPERATOR' AS dict_type, 'PLUS'  AS dict_key, '+ 加' AS dict_label, 10 AS sort_order, 'ACTIVE' AS status, '' AS description, 1 AS created_by, 1 AS updated_by UNION ALL
  SELECT 'NSFR_OPERATOR',                  'MINUS', '- 减',                       20,            'ACTIVE',           '',                  1,            1
) t
WHERE NOT EXISTS (
  SELECT 1 FROM sys_dict d
  WHERE d.dict_type='NSFR_OPERATOR' AND d.dict_key=t.dict_key AND d.is_deleted=0
);