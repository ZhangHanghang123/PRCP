-- 报表表项月度值表（数据维护核心存储）
CREATE TABLE IF NOT EXISTS prcp_rpt_value (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_id         BIGINT NOT NULL,
  data_date       DATE NOT NULL,
  value           DECIMAL(20,6) DEFAULT 0,
  source          VARCHAR(32) DEFAULT 'MANUAL' COMMENT 'MANUAL|CALC|IMPORT',
  calc_log        LONGTEXT,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_item_date (item_id, data_date, is_deleted),
  INDEX idx_item (item_id),
  INDEX idx_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报表表项月度值（数据维护）';