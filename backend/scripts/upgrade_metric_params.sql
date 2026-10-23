-- ============================================================
-- CET1 / EVE / NIM / ROE 4 个指标参数补录表
-- 创建时间：2026-09-30
-- 模板：与 LCR/NSFR 一致（is/factor/operator/category）
-- ============================================================

USE prcp_db;

-- ------------------------------------------------------------
-- 1. CET1 核心一级资本充足率参数
-- ------------------------------------------------------------
DROP TABLE IF EXISTS prcp_cet1_param;
CREATE TABLE prcp_cet1_param (
  id              VARCHAR(64)  NOT NULL                              COMMENT '主键 {scheme}_{node}_{YYYYMMDD}',
  scheme_id       INT          NOT NULL                              COMMENT '账户册方案 ID',
  scheme_code     VARCHAR(64)  NOT NULL                              COMMENT '账户册方案编码',
  node_id         INT          NOT NULL                              COMMENT '节点 ID',
  node_code       VARCHAR(64)  NOT NULL                              COMMENT '账户册编码',
  node_name       VARCHAR(128) NOT NULL                              COMMENT '账户册名称',
  data_date       DATE         NOT NULL                              COMMENT '数据日期',
  is_numerator    TINYINT(1)   DEFAULT 0                             COMMENT '是否 CET1 分子',
  numerator_factor DECIMAL(12,6) DEFAULT NULL                         COMMENT '分子折算系数',
  numerator_operator VARCHAR(8) DEFAULT '+'                          COMMENT '分子运算符',
  numerator_category VARCHAR(32) DEFAULT NULL                        COMMENT 'CET1 分子类别（分子/扣减/无）',
  is_rwa          TINYINT(1)   DEFAULT 0                             COMMENT '是否计入 RWA',
  rwa_weight      DECIMAL(8,4) DEFAULT NULL                          COMMENT 'RWA 风险权重',
  rwa_operator    VARCHAR(8)   DEFAULT '+'                           COMMENT 'RWA 运算符',
  rwa_category    VARCHAR(32) DEFAULT NULL                           COMMENT 'RWA 类别（信用/市场/操作/无）',
  current_balance DECIMAL(20,4) DEFAULT NULL                         COMMENT '当前余额（元）',
  rule_note       VARCHAR(500) DEFAULT NULL                          COMMENT 'CET1 规则说明',
  status          VARCHAR(16)  DEFAULT 'ACTIVE'                      COMMENT '状态',
  is_deleted      TINYINT(1)   DEFAULT 0                             COMMENT '软删标记',
  created_by      VARCHAR(64)  DEFAULT NULL,
  updated_by      VARCHAR(64)  DEFAULT NULL,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_cet1 (scheme_code, node_code, data_date, is_deleted),
  KEY idx_node (node_code),
  KEY idx_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='CET1 资本充足率参数补录';

-- ------------------------------------------------------------
-- 2. EVE 经济价值变动（IRRBB 银行账簿利率风险）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS prcp_eve_param;
CREATE TABLE prcp_eve_param (
  id              VARCHAR(64)  NOT NULL                              COMMENT '主键',
  scheme_id       INT          NOT NULL,
  scheme_code     VARCHAR(64)  NOT NULL,
  node_id         INT          NOT NULL,
  node_code       VARCHAR(64)  NOT NULL,
  node_name       VARCHAR(128) NOT NULL,
  data_date       DATE         NOT NULL,
  is_asset        TINYINT(1)   DEFAULT 0                             COMMENT '是否资产端',
  asset_type      VARCHAR(32) DEFAULT NULL                           COMMENT '资产类型（贷款/债券/同业/...）',
  asset_category  VARCHAR(32) DEFAULT NULL                           COMMENT '类别（asset/汇总）',
  asset_operator  VARCHAR(8)  DEFAULT '+'                            COMMENT '运算符',
  is_liability    TINYINT(1)  DEFAULT 0                              COMMENT '是否负债端',
  liability_type  VARCHAR(32) DEFAULT NULL                           COMMENT '负债类型',
  liability_category VARCHAR(32) DEFAULT NULL                        COMMENT '负债类别',
  liability_operator VARCHAR(8) DEFAULT '+'                          COMMENT '负债运算符',
  duration        DECIMAL(8,4) DEFAULT NULL                          COMMENT '久期（年）',
  current_balance DECIMAL(20,4) DEFAULT NULL,
  rule_note       VARCHAR(500) DEFAULT NULL,
  status          VARCHAR(16)  DEFAULT 'ACTIVE',
  is_deleted      TINYINT(1)   DEFAULT 0,
  created_by      VARCHAR(64)  DEFAULT NULL,
  updated_by      VARCHAR(64)  DEFAULT NULL,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_eve (scheme_code, node_code, data_date, is_deleted),
  KEY idx_node (node_code),
  KEY idx_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='EVE 经济价值变动参数补录';

-- ------------------------------------------------------------
-- 3. NIM 净息差
-- ------------------------------------------------------------
DROP TABLE IF EXISTS prcp_nim_param;
CREATE TABLE prcp_nim_param (
  id              VARCHAR(64)  NOT NULL,
  scheme_id       INT          NOT NULL,
  scheme_code     VARCHAR(64)  NOT NULL,
  node_id         INT          NOT NULL,
  node_code       VARCHAR(64)  NOT NULL,
  node_name       VARCHAR(128) NOT NULL,
  data_date       DATE         NOT NULL,
  is_interest_asset    TINYINT(1)   DEFAULT 0                       COMMENT '是否生息资产',
  asset_rate           DECIMAL(10,6) DEFAULT NULL                   COMMENT '资产利率',
  asset_operator       VARCHAR(8) DEFAULT '+'                       COMMENT '资产运算符',
  asset_category       VARCHAR(32) DEFAULT NULL                     COMMENT '资产类别（用于业务标记）',
  is_interest_liability TINYINT(1) DEFAULT 0                        COMMENT '是否计息负债',
  liability_rate       DECIMAL(10,6) DEFAULT NULL                   COMMENT '负债利率',
  liability_operator   VARCHAR(8) DEFAULT '+'                       COMMENT '负债运算符',
  liability_category   VARCHAR(32) DEFAULT NULL                     COMMENT '负债类别',
  current_balance      DECIMAL(20,4) DEFAULT NULL,
  rule_note            VARCHAR(500) DEFAULT NULL,
  status          VARCHAR(16)  DEFAULT 'ACTIVE',
  is_deleted      TINYINT(1)   DEFAULT 0,
  created_by      VARCHAR(64)  DEFAULT NULL,
  updated_by      VARCHAR(64)  DEFAULT NULL,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_nim (scheme_code, node_code, data_date, is_deleted),
  KEY idx_node (node_code),
  KEY idx_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='NIM 净息差参数补录';

-- ------------------------------------------------------------
-- 4. ROE 净资产收益率
-- ------------------------------------------------------------
DROP TABLE IF EXISTS prcp_roe_param;
CREATE TABLE prcp_roe_param (
  id              VARCHAR(64)  NOT NULL,
  scheme_id       INT          NOT NULL,
  scheme_code     VARCHAR(64)  NOT NULL,
  node_id         INT          NOT NULL,
  node_code       VARCHAR(64)  NOT NULL,
  node_name       VARCHAR(128) NOT NULL,
  data_date       DATE         NOT NULL,
  is_net_profit   TINYINT(1)   DEFAULT 0                             COMMENT '是否计入净利润',
  net_profit_symbol VARCHAR(8) DEFAULT '+'                           COMMENT '净利润符号（+/-）',
  net_profit_factor DECIMAL(12,6) DEFAULT NULL                       COMMENT '净利润折算系数',
  net_profit_category VARCHAR(32) DEFAULT NULL                      COMMENT '净利润类别（营收/支出/...）',
  is_net_asset    TINYINT(1)   DEFAULT 0                             COMMENT '是否计入净资产',
  net_asset_symbol VARCHAR(8) DEFAULT '+'                            COMMENT '净资产符号',
  net_asset_factor DECIMAL(12,6) DEFAULT NULL                       COMMENT '净资产折算系数',
  net_asset_category VARCHAR(32) DEFAULT NULL                       COMMENT '净资产类别',
  current_balance DECIMAL(20,4) DEFAULT NULL,
  rule_note       VARCHAR(500) DEFAULT NULL,
  status          VARCHAR(16)  DEFAULT 'ACTIVE',
  is_deleted      TINYINT(1)   DEFAULT 0,
  created_by      VARCHAR(64)  DEFAULT NULL,
  updated_by      VARCHAR(64)  DEFAULT NULL,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_roe (scheme_code, node_code, data_date, is_deleted),
  KEY idx_node (node_code),
  KEY idx_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ROE 净资产收益率参数补录';