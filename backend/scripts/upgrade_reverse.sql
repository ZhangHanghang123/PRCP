-- 组合反算模块：4 张表 + 种子数据
-- 1. 反算方案
CREATE TABLE IF NOT EXISTS prcp_reverse_scheme (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  scheme_code     VARCHAR(32) NOT NULL UNIQUE,
  scheme_name     VARCHAR(128) NOT NULL,
  scheme_type     VARCHAR(32) DEFAULT 'OPTIMIZE',
                 -- OPTIMIZE（最优求解）/ SCENARIO（情景模拟）
  coa_scheme_id   BIGINT NOT NULL,
  data_date       DATE NOT NULL,
  horizon_months  INT DEFAULT 24,
                 -- 反算预测期数（默认 24 个月）
  algorithm       VARCHAR(32) DEFAULT 'CVXPY_QP',
                 -- CVXPY_QP（二次规划）/ CVXPY_LP（线性规划）/ HEURISTIC（启发式）
  description     TEXT,
  status          VARCHAR(16) DEFAULT 'DRAFT',
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_status (status),
  INDEX idx_coa (coa_scheme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组合反算方案';

-- 2. 反算目标指标
CREATE TABLE IF NOT EXISTS prcp_reverse_target (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  scheme_id       BIGINT NOT NULL,
  kpi_id          BIGINT,
  kpi_code        VARCHAR(64),
  target_name     VARCHAR(128) NOT NULL,
  target_value    DECIMAL(20,6) NOT NULL,
  constraint_type VARCHAR(8) DEFAULT 'GE',
                 -- GE（≥）/ LE（≤）/ EQ（=）
  weight          DECIMAL(10,4) DEFAULT 1.0,
                 -- 目标权重（求解时加权）
  horizon_month   INT DEFAULT 0,
                 -- 0=全期；>0=第 N 月生效
  sort_order      INT DEFAULT 0,
  description     TEXT,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_scheme (scheme_id),
  INDEX idx_kpi (kpi_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反算目标指标';

-- 3. 反算执行记录
CREATE TABLE IF NOT EXISTS prcp_reverse_run (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_code        VARCHAR(32) NOT NULL UNIQUE,
  scheme_id       BIGINT NOT NULL,
  status          VARCHAR(16) DEFAULT 'PENDING',
                 -- PENDING / RUNNING / SUCCESS / FAILED / CANCELLED
  progress        DECIMAL(5,2) DEFAULT 0,
  start_at        DATETIME,
  end_at          DATETIME,
  duration_sec    INT,
  optimal_value   DECIMAL(20,6),
                 -- cvxpy 求解的目标函数值
  metrics         JSON,
                 -- {kpi_actual: {...}, gap_total: {...}, status: 'optimal'|'infeasible'}
  error_message   TEXT,
  description     TEXT,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_status (status),
  INDEX idx_scheme (scheme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反算执行记录';

-- 4. 反算结果（每期报表项预测值）
CREATE TABLE IF NOT EXISTS prcp_reverse_result (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id          BIGINT NOT NULL,
  predict_month   INT NOT NULL,
                 -- 第 N 个月（1..24）
  predict_date    DATE NOT NULL,
  rpt_item_id     BIGINT,
  rpt_item_code   VARCHAR(64),
  current_value   DECIMAL(20,4),
                 -- 反算前的当前值
  adjusted_value  DECIMAL(20,4) NOT NULL,
                 -- 反算后的值
  delta_value     DECIMAL(20,4),
                 -- 调整量（adjusted - current）
  is_deleted      TINYINT(1) DEFAULT 0,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_run (run_id),
  INDEX idx_run_month (run_id, predict_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反算结果（每期预测值）';

-- 5. 反算日志
CREATE TABLE IF NOT EXISTS prcp_reverse_run_log (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id          BIGINT NOT NULL,
  log_level       VARCHAR(16) DEFAULT 'INFO',
  log_message     TEXT NOT NULL,
  progress        DECIMAL(5,2),
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_run_time (run_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反算日志';

-- 种子数据：3 个示例反算方案
INSERT IGNORE INTO prcp_reverse_scheme
  (scheme_code, scheme_name, scheme_type, coa_scheme_id, data_date, horizon_months, algorithm, description, status, created_by)
VALUES
('REV_NIM_UP', 'NIM 上行 50BP 反算', 'OPTIMIZE', 6, '2025-12-31', 24, 'CVXPY_QP',
   '在 NIM ≥ 2.8% 约束下，求解资产负债结构调整', 'DRAFT', 1),
('REV_LCR_STRESS', 'LCR 压力情景反算', 'OPTIMIZE', 6, '2025-12-31', 24, 'CVXPY_QP',
   'LCR ≥ 120% 压力情景，求解现金/优质流动性资产最优配置', 'DRAFT', 1),
('REV_GROWTH', '规模增长 15% 反算', 'OPTIMIZE', 6, '2025-12-31', 24, 'CVXPY_QP',
   '总资产增长 15% 约束下，求解资产端最优分配', 'DRAFT', 1);