-- 升级模型管理模块：6 张新表 + 种子数据（拆分版，避免 heredoc 引号问题）
-- 1. 模型主表
CREATE TABLE IF NOT EXISTS prcp_model (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  model_code      VARCHAR(32) NOT NULL UNIQUE,
  model_name      VARCHAR(128) NOT NULL,
  model_type      VARCHAR(32) NOT NULL DEFAULT 'LINEAR_REGRESSION',
  description     TEXT,
  algo_config     JSON,
  biz_domain      VARCHAR(32),
  status          VARCHAR(16) DEFAULT 'ACTIVE',
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_type (model_type),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型主表';

-- 2. 参数版本表
CREATE TABLE IF NOT EXISTS prcp_model_version (
  id                 BIGINT AUTO_INCREMENT PRIMARY KEY,
  model_id           BIGINT NOT NULL,
  version_code       VARCHAR(32) NOT NULL,
  version_name       VARCHAR(128) NOT NULL,
  parent_version_id  BIGINT DEFAULT NULL,
  param_count        INT DEFAULT 0,
  description        TEXT,
  status             VARCHAR(16) DEFAULT 'DRAFT',
  is_deleted         TINYINT(1) DEFAULT 0,
  created_by         BIGINT,
  updated_by         BIGINT,
  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_model_version (model_id, version_code),
  INDEX idx_parent (parent_version_id),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型参数版本';

-- 3. 参数明细表
CREATE TABLE IF NOT EXISTS prcp_model_param (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  version_id      BIGINT NOT NULL,
  kpi_id          BIGINT NOT NULL,
  kpi_code        VARCHAR(64),
  param_code      VARCHAR(64) NOT NULL,
  param_name      VARCHAR(128) NOT NULL,
  param_type      VARCHAR(16) DEFAULT 'BASE',
  param_value     DECIMAL(20,6) NOT NULL,
  unit            VARCHAR(16),
  formula         TEXT,
  formula_desc    TEXT,
  sort_order      INT DEFAULT 0,
  description     TEXT,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_version_param (version_id, param_code),
  INDEX idx_kpi (kpi_id),
  INDEX idx_version (version_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型参数明细';

-- 4. 训练任务表
CREATE TABLE IF NOT EXISTS prcp_model_train (
  id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
  train_code          VARCHAR(32) NOT NULL UNIQUE,
  model_id            BIGINT NOT NULL,
  version_id          BIGINT NOT NULL,
  coa_scheme_id       BIGINT NOT NULL,
  balance_date_from   DATE NOT NULL,
  balance_date_to     DATE NOT NULL,
  status              VARCHAR(16) DEFAULT 'PENDING',
  progress            DECIMAL(5,2) DEFAULT 0,
  start_at            DATETIME,
  end_at              DATETIME,
  duration_sec        INT,
  metrics             JSON,
  error_message       TEXT,
  description         TEXT,
  is_deleted          TINYINT(1) DEFAULT 0,
  created_by          BIGINT,
  updated_by          BIGINT,
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_status (status),
  INDEX idx_model (model_id),
  INDEX idx_version (version_id),
  INDEX idx_dates (balance_date_from, balance_date_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型训练任务';

-- 5. 训练日志表
CREATE TABLE IF NOT EXISTS prcp_model_train_log (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  train_id        BIGINT NOT NULL,
  log_level       VARCHAR(16) DEFAULT 'INFO',
  log_message     TEXT NOT NULL,
  progress        DECIMAL(5,2),
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_train_time (train_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型训练日志';

-- 6. 训练结果表
CREATE TABLE IF NOT EXISTS prcp_model_train_result (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  train_id        BIGINT NOT NULL,
  rpt_item_id     BIGINT NOT NULL,
  rpt_item_code   VARCHAR(64),
  predict_period  DATE NOT NULL,
  predicted_value DECIMAL(20,6) NOT NULL,
  actual_value    DECIMAL(20,6),
  confidence_low  DECIMAL(20,6),
  confidence_high DECIMAL(20,6),
  is_deleted      TINYINT(1) DEFAULT 0,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_train_item_period (train_id, rpt_item_id, predict_period),
  INDEX idx_train (train_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型训练结果';

-- 种子数据
INSERT IGNORE INTO prcp_model (model_code, model_name, model_type, biz_domain, description, status, created_by)
VALUES
('DGM_2026', '存款增长模型', 'LINEAR_REGRESSION', 'DEPOSIT', '基于历史数据预测存款规模', 'ACTIVE', 1),
('NIM_2026', '净息差预测模型', 'LINEAR_REGRESSION', 'NIM', 'NIM 时序预测', 'ACTIVE', 1),
('RWA_2026', '资本充足率优化模型', 'LINEAR_REGRESSION', 'RWA', '资产结构优化', 'ACTIVE', 1);

-- 自动为每个模型创建 V1_BASELINE 版本（用子查询取 id）
INSERT IGNORE INTO prcp_model_version (model_id, version_code, version_name, description, status, created_by)
SELECT id, 'V1_BASELINE', '基准情景', '初始基准参数配置', 'READY', 1
FROM prcp_model
WHERE model_code IN ('DGM_2026', 'NIM_2026', 'RWA_2026') AND is_deleted=0;