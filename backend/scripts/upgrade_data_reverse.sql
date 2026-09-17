-- =====================================================================
-- PRCP 反算结果查询表（结构参考 prcp_data_basic + 反算方案编码）
-- 用途：保存反算引擎跑出的预测数据，每期预测一行
-- ID 生成：record_id = CONCAT(scheme_code, '_', id)
-- =====================================================================

-- 1. 反算结果主表
CREATE TABLE IF NOT EXISTS prcp_data_reverse (
  id              BIGINT AUTO_INCREMENT,
  record_id       VARCHAR(80) NOT NULL,
                 -- 业务 ID = scheme_code + '_' + id（前端展示用）
  scheme_code     VARCHAR(32) NOT NULL,
                 -- 反算方案编码（来自 prcp_reverse_scheme.scheme_code）
  run_id          BIGINT NOT NULL,
                 -- 反算执行记录 ID（来自 prcp_reverse_run.id）
  coa_scheme_id   BIGINT,
                 -- 关联的账户册方案 ID
  data_date       DATE NOT NULL,
                 -- 预测月份的实际日期（按月起算的第 N 月）
  date_offset     INT DEFAULT 1,
                 -- 月份数（1..24，对应 M1~M24）
  offset_unit     VARCHAR(2) DEFAULT 'M',
                 -- 'M' = 月，反算结果是按月预测
  coa_node_id     BIGINT NOT NULL,
  node_code       VARCHAR(32),
  node_name       VARCHAR(64),
  node_level      INT,
  parent_code     VARCHAR(32),
  is_leaf         TINYINT(1) DEFAULT 0,
  category        VARCHAR(8),
  -- 原始期限金额（13 个期限桶，与 prcp_data_basic 一致）
  orig_d1         DECIMAL(20,4) DEFAULT 0,
  orig_d7         DECIMAL(20,4) DEFAULT 0,
  orig_m1         DECIMAL(20,4) DEFAULT 0,
  orig_m3         DECIMAL(20,4) DEFAULT 0,
  orig_m6         DECIMAL(20,4) DEFAULT 0,
  orig_y1         DECIMAL(20,4) DEFAULT 0,
  orig_y2         DECIMAL(20,4) DEFAULT 0,
  orig_y3         DECIMAL(20,4) DEFAULT 0,
  orig_y5         DECIMAL(20,4) DEFAULT 0,
  orig_y10        DECIMAL(20,4) DEFAULT 0,
  orig_y15        DECIMAL(20,4) DEFAULT 0,
  orig_y20        DECIMAL(20,4) DEFAULT 0,
  orig_y30        DECIMAL(20,4) DEFAULT 0,
  -- 剩余期限金额（13 个期限桶）
  rem_d1          DECIMAL(20,4) DEFAULT 0,
  rem_d7          DECIMAL(20,4) DEFAULT 0,
  rem_m1          DECIMAL(20,4) DEFAULT 0,
  rem_m3          DECIMAL(20,4) DEFAULT 0,
  rem_m6          DECIMAL(20,4) DEFAULT 0,
  rem_y1          DECIMAL(20,4) DEFAULT 0,
  rem_y2          DECIMAL(20,4) DEFAULT 0,
  rem_y3          DECIMAL(20,4) DEFAULT 0,
  rem_y5          DECIMAL(20,4) DEFAULT 0,
  rem_y10         DECIMAL(20,4) DEFAULT 0,
  rem_y15         DECIMAL(20,4) DEFAULT 0,
  rem_y20         DECIMAL(20,4) DEFAULT 0,
  rem_y30         DECIMAL(20,4) DEFAULT 0,
  -- 流动性指标
  asf_rsf         VARCHAR(8),
  hqla_factor     DECIMAL(8,4),
  -- 余额/利率类指标
  current_balance DECIMAL(20,4) DEFAULT 0,
  avg_balance     DECIMAL(20,4) DEFAULT 0,
  weighted_rate   DECIMAL(10,6) DEFAULT 0,
  interest_amount DECIMAL(20,4) DEFAULT 0,
  risk_weight     DECIMAL(10,6) DEFAULT 0,
  calc_note       TEXT,
                 -- 反算备注（如"基于 KPI_NIM ≥ 2.8 反算"）
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_record_id (record_id),
  UNIQUE KEY uk_node_date (scheme_code, run_id, coa_node_id, data_date, date_offset),
  INDEX idx_scheme (scheme_code),
  INDEX idx_run (run_id),
  INDEX idx_date (data_date),
  INDEX idx_node (coa_node_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反算结果查询表（基础数据表结构 + scheme_code + run_id）';