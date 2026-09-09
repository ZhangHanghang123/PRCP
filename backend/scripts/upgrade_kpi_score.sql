-- PRCP 指标评分模块 - 数据库升级脚本
-- 新增两张表：评分规则 + 评分段

CREATE TABLE IF NOT EXISTS prcp_kpi_score_rule (
  id                BIGINT AUTO_INCREMENT PRIMARY KEY,
  scheme_id         BIGINT NOT NULL,
  kpi_id            BIGINT NOT NULL,
  rule_name         VARCHAR(128) NOT NULL,
  calc_method       VARCHAR(16) DEFAULT 'PIECEWISE',
  total_score       DECIMAL(8,2) DEFAULT 100.00,
  higher_is_better  TINYINT(1) DEFAULT 1,
  description       TEXT,
  status            VARCHAR(16) DEFAULT 'ACTIVE',
  is_deleted        TINYINT(1) DEFAULT 0,
  created_by        BIGINT,
  updated_by        BIGINT,
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_kpi_rule (kpi_id, rule_name, is_deleted),
  INDEX idx_scheme (scheme_id),
  INDEX idx_kpi (kpi_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标评分规则';

CREATE TABLE IF NOT EXISTS prcp_kpi_score_segment (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  rule_id         BIGINT NOT NULL,
  seg_order       INT NOT NULL DEFAULT 0,
  min_value       DECIMAL(20,6),
  max_value       DECIMAL(20,6),
  score           DECIMAL(8,2) NOT NULL,
  segment_desc    VARCHAR(255),
  is_deleted      TINYINT(1) DEFAULT 0,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_rule (rule_id, seg_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评分规则的分段区间';