-- 数据维护模块：取数逻辑定义表
CREATE TABLE IF NOT EXISTS prcp_kpi_calc_rule (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  scheme_id       BIGINT NOT NULL,
  kpi_id          BIGINT NOT NULL,
  numerator_json  LONGTEXT COMMENT '分子：coa_node_id 列表',
  denominator_json LONGTEXT COMMENT '分母：coa_node_id 列表',
  calc_unit       VARCHAR(16) DEFAULT 'PERCENT' COMMENT 'PERCENT|RATIO|AMOUNT',
  calc_method     VARCHAR(32) DEFAULT 'RATIO' COMMENT 'RATIO|DIFF|SUM|AVG',
  description     TEXT,
  status          VARCHAR(16) DEFAULT 'ACTIVE',
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_scheme_kpi (scheme_id, kpi_id, is_deleted),
  INDEX idx_scheme (scheme_id),
  INDEX idx_kpi (kpi_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标取数逻辑（分子/分母 = 账户册节点）';

-- 数据维护表：用于手动维护损益输入、非息输入、市场参数等不可由账户册推出的指标
CREATE TABLE IF NOT EXISTS prcp_data_maint_value (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  kpi_id          BIGINT NOT NULL,
  data_date       DATE NOT NULL,
  version         VARCHAR(32) DEFAULT 'V1.0',
  input_value     DECIMAL(20,6) DEFAULT 0 COMMENT '手动输入值',
  source          VARCHAR(32) DEFAULT 'MANUAL' COMMENT 'MANUAL|IMPORT|MODEL',
  remark          VARCHAR(255),
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_kpi_date_ver (kpi_id, data_date, version),
  INDEX idx_date (data_date),
  INDEX idx_kpi (kpi_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据维护值（损益/非息/市场参数等）';