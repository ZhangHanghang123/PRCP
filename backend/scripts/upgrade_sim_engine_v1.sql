-- ============================================================
-- PRCP 新业务模拟引擎 v1 — DB 升级脚本
-- 时间：2026-09-21
-- 配套文档：docs/新业务模拟_引擎算法_v1.md
--
-- 新增 2 张表：
--   prcp_sim_run      执行记录
--   prcp_sim_result   快照结果（64+64 桶 + 4 主指标 + sim_scheme_code + date_offset）
--
-- 幂等保护：每张表先检查存在性
-- ============================================================

USE prcp_db;

-- ============================================================
-- 一、prcp_sim_run（执行记录表）
-- ============================================================
SET @t_exists := (
  SELECT COUNT(*) FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_run'
);
SET @sql := IF(@t_exists = 0, '
CREATE TABLE prcp_sim_run (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  sim_scheme_id   BIGINT NOT NULL                      COMMENT "FK → prcp_sim_scheme.id",
  sim_scheme_code VARCHAR(32) NOT NULL                 COMMENT "冗余：方案编码",
  base_data_date  DATE NOT NULL                        COMMENT "基准月（=scheme.data_date）",
  month_count     INT DEFAULT 24                       COMMENT "生成月份数（默认 24）",
  target_data_date DATE                                COMMENT "目标月（=base + month_count 月）",
  status          VARCHAR(16) DEFAULT "PENDING"        COMMENT "PENDING/RUNNING/SUCCESS/FAILED/CANCELLED",
  progress        INT DEFAULT 0                        COMMENT "进度 0-100",
  total_nodes     INT DEFAULT 0                        COMMENT "本次执行的节点总数",
  processed_nodes INT DEFAULT 0                        COMMENT "已处理节点数",
  duration_ms     BIGINT                               COMMENT "执行耗时（毫秒）",
  error_message   TEXT,
  started_at      DATETIME,
  finished_at     DATETIME,
  created_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_sim_scheme (sim_scheme_id),
  INDEX idx_status (status),
  INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT="新业务模拟执行记录"', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ============================================================
-- 二、prcp_sim_result（快照结果表）
-- ============================================================
SET @t_exists := (
  SELECT COUNT(*) FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_result'
);
SET @sql := IF(@t_exists = 0, '
CREATE TABLE prcp_sim_result (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  sim_scheme_code VARCHAR(32) NOT NULL                 COMMENT "业务量方案编码",
  sim_scheme_id   BIGINT NOT NULL                      COMMENT "FK → prcp_sim_scheme.id",
  run_id          BIGINT NOT NULL                      COMMENT "FK → prcp_sim_run.id",
  data_date       DATE NOT NULL                        COMMENT "偏移日期",
  date_offset     INT NOT NULL                         COMMENT "月份数（1..24）",
  coa_scheme_id   BIGINT NOT NULL,
  coa_node_id     BIGINT NOT NULL,
  node_code       VARCHAR(32),
  node_name       VARCHAR(64),
  node_level      INT,
  parent_code     VARCHAR(32),
  is_leaf         TINYINT(1) DEFAULT 0,
  category        VARCHAR(8),
  orig_m1         DECIMAL(20,4) DEFAULT 0,
  orig_m2         DECIMAL(20,4) DEFAULT 0,
  orig_m3         DECIMAL(20,4) DEFAULT 0,
  orig_m4         DECIMAL(20,4) DEFAULT 0,
  orig_m5         DECIMAL(20,4) DEFAULT 0,
  orig_m6         DECIMAL(20,4) DEFAULT 0,
  orig_m7         DECIMAL(20,4) DEFAULT 0,
  orig_m8         DECIMAL(20,4) DEFAULT 0,
  orig_m9         DECIMAL(20,4) DEFAULT 0,
  orig_m10        DECIMAL(20,4) DEFAULT 0,
  orig_m11        DECIMAL(20,4) DEFAULT 0,
  orig_m12        DECIMAL(20,4) DEFAULT 0,
  orig_m13        DECIMAL(20,4) DEFAULT 0,
  orig_m14        DECIMAL(20,4) DEFAULT 0,
  orig_m15        DECIMAL(20,4) DEFAULT 0,
  orig_m16        DECIMAL(20,4) DEFAULT 0,
  orig_m17        DECIMAL(20,4) DEFAULT 0,
  orig_m18        DECIMAL(20,4) DEFAULT 0,
  orig_m19        DECIMAL(20,4) DEFAULT 0,
  orig_m20        DECIMAL(20,4) DEFAULT 0,
  orig_m21        DECIMAL(20,4) DEFAULT 0,
  orig_m22        DECIMAL(20,4) DEFAULT 0,
  orig_m23        DECIMAL(20,4) DEFAULT 0,
  orig_m24        DECIMAL(20,4) DEFAULT 0,
  orig_m25        DECIMAL(20,4) DEFAULT 0,
  orig_m26        DECIMAL(20,4) DEFAULT 0,
  orig_m27        DECIMAL(20,4) DEFAULT 0,
  orig_m28        DECIMAL(20,4) DEFAULT 0,
  orig_m29        DECIMAL(20,4) DEFAULT 0,
  orig_m30        DECIMAL(20,4) DEFAULT 0,
  orig_m31        DECIMAL(20,4) DEFAULT 0,
  orig_m32        DECIMAL(20,4) DEFAULT 0,
  orig_m33        DECIMAL(20,4) DEFAULT 0,
  orig_m34        DECIMAL(20,4) DEFAULT 0,
  orig_m35        DECIMAL(20,4) DEFAULT 0,
  orig_m36        DECIMAL(20,4) DEFAULT 0,
  orig_m37        DECIMAL(20,4) DEFAULT 0,
  orig_m38        DECIMAL(20,4) DEFAULT 0,
  orig_m39        DECIMAL(20,4) DEFAULT 0,
  orig_m40        DECIMAL(20,4) DEFAULT 0,
  orig_m41        DECIMAL(20,4) DEFAULT 0,
  orig_m42        DECIMAL(20,4) DEFAULT 0,
  orig_m43        DECIMAL(20,4) DEFAULT 0,
  orig_m44        DECIMAL(20,4) DEFAULT 0,
  orig_m45        DECIMAL(20,4) DEFAULT 0,
  orig_m46        DECIMAL(20,4) DEFAULT 0,
  orig_m47        DECIMAL(20,4) DEFAULT 0,
  orig_m48        DECIMAL(20,4) DEFAULT 0,
  orig_m49        DECIMAL(20,4) DEFAULT 0,
  orig_m50        DECIMAL(20,4) DEFAULT 0,
  orig_m51        DECIMAL(20,4) DEFAULT 0,
  orig_m52        DECIMAL(20,4) DEFAULT 0,
  orig_m53        DECIMAL(20,4) DEFAULT 0,
  orig_m54        DECIMAL(20,4) DEFAULT 0,
  orig_m55        DECIMAL(20,4) DEFAULT 0,
  orig_m56        DECIMAL(20,4) DEFAULT 0,
  orig_m57        DECIMAL(20,4) DEFAULT 0,
  orig_m58        DECIMAL(20,4) DEFAULT 0,
  orig_m59        DECIMAL(20,4) DEFAULT 0,
  orig_m60        DECIMAL(20,4) DEFAULT 0,
  orig_y10        DECIMAL(20,4) DEFAULT 0,
  orig_y15        DECIMAL(20,4) DEFAULT 0,
  orig_y20        DECIMAL(20,4) DEFAULT 0,
  orig_y30        DECIMAL(20,4) DEFAULT 0,
  rem_m1          DECIMAL(20,4) DEFAULT 0,
  rem_m2          DECIMAL(20,4) DEFAULT 0,
  rem_m3          DECIMAL(20,4) DEFAULT 0,
  rem_m4          DECIMAL(20,4) DEFAULT 0,
  rem_m5          DECIMAL(20,4) DEFAULT 0,
  rem_m6          DECIMAL(20,4) DEFAULT 0,
  rem_m7          DECIMAL(20,4) DEFAULT 0,
  rem_m8          DECIMAL(20,4) DEFAULT 0,
  rem_m9          DECIMAL(20,4) DEFAULT 0,
  rem_m10         DECIMAL(20,4) DEFAULT 0,
  rem_m11         DECIMAL(20,4) DEFAULT 0,
  rem_m12         DECIMAL(20,4) DEFAULT 0,
  rem_m13         DECIMAL(20,4) DEFAULT 0,
  rem_m14         DECIMAL(20,4) DEFAULT 0,
  rem_m15         DECIMAL(20,4) DEFAULT 0,
  rem_m16         DECIMAL(20,4) DEFAULT 0,
  rem_m17         DECIMAL(20,4) DEFAULT 0,
  rem_m18         DECIMAL(20,4) DEFAULT 0,
  rem_m19         DECIMAL(20,4) DEFAULT 0,
  rem_m20         DECIMAL(20,4) DEFAULT 0,
  rem_m21         DECIMAL(20,4) DEFAULT 0,
  rem_m22         DECIMAL(20,4) DEFAULT 0,
  rem_m23         DECIMAL(20,4) DEFAULT 0,
  rem_m24         DECIMAL(20,4) DEFAULT 0,
  rem_m25         DECIMAL(20,4) DEFAULT 0,
  rem_m26         DECIMAL(20,4) DEFAULT 0,
  rem_m27         DECIMAL(20,4) DEFAULT 0,
  rem_m28         DECIMAL(20,4) DEFAULT 0,
  rem_m29         DECIMAL(20,4) DEFAULT 0,
  rem_m30         DECIMAL(20,4) DEFAULT 0,
  rem_m31         DECIMAL(20,4) DEFAULT 0,
  rem_m32         DECIMAL(20,4) DEFAULT 0,
  rem_m33         DECIMAL(20,4) DEFAULT 0,
  rem_m34         DECIMAL(20,4) DEFAULT 0,
  rem_m35         DECIMAL(20,4) DEFAULT 0,
  rem_m36         DECIMAL(20,4) DEFAULT 0,
  rem_m37         DECIMAL(20,4) DEFAULT 0,
  rem_m38         DECIMAL(20,4) DEFAULT 0,
  rem_m39         DECIMAL(20,4) DEFAULT 0,
  rem_m40         DECIMAL(20,4) DEFAULT 0,
  rem_m41         DECIMAL(20,4) DEFAULT 0,
  rem_m42         DECIMAL(20,4) DEFAULT 0,
  rem_m43         DECIMAL(20,4) DEFAULT 0,
  rem_m44         DECIMAL(20,4) DEFAULT 0,
  rem_m45         DECIMAL(20,4) DEFAULT 0,
  rem_m46         DECIMAL(20,4) DEFAULT 0,
  rem_m47         DECIMAL(20,4) DEFAULT 0,
  rem_m48         DECIMAL(20,4) DEFAULT 0,
  rem_m49         DECIMAL(20,4) DEFAULT 0,
  rem_m50         DECIMAL(20,4) DEFAULT 0,
  rem_m51         DECIMAL(20,4) DEFAULT 0,
  rem_m52         DECIMAL(20,4) DEFAULT 0,
  rem_m53         DECIMAL(20,4) DEFAULT 0,
  rem_m54         DECIMAL(20,4) DEFAULT 0,
  rem_m55         DECIMAL(20,4) DEFAULT 0,
  rem_m56         DECIMAL(20,4) DEFAULT 0,
  rem_m57         DECIMAL(20,4) DEFAULT 0,
  rem_m58         DECIMAL(20,4) DEFAULT 0,
  rem_m59         DECIMAL(20,4) DEFAULT 0,
  rem_m60         DECIMAL(20,4) DEFAULT 0,
  rem_y10         DECIMAL(20,4) DEFAULT 0,
  rem_y15         DECIMAL(20,4) DEFAULT 0,
  rem_y20         DECIMAL(20,4) DEFAULT 0,
  rem_y30         DECIMAL(20,4) DEFAULT 0,
  asf_rsf         VARCHAR(8),
  hqla_factor     DECIMAL(8,4),
  current_balance DECIMAL(20,4) DEFAULT 0,
  avg_balance     DECIMAL(20,4) DEFAULT 0,
  weighted_rate   DECIMAL(10,6) DEFAULT 0,
  interest_amount DECIMAL(20,4) DEFAULT 0,
  risk_weight     DECIMAL(10,6) DEFAULT 0,
  calc_note       TEXT,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_sim_node_date (sim_scheme_code, run_id, coa_node_id, data_date, date_offset),
  INDEX idx_sim_scheme (sim_scheme_code),
  INDEX idx_run (run_id),
  INDEX idx_date (data_date),
  INDEX idx_node (coa_node_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT="新业务模拟快照结果"', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ============================================================
-- 三、验证
-- ============================================================
SELECT 'prcp_sim_run' AS tbl_, COUNT(*) AS col_cnt
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_run'
UNION ALL
SELECT 'prcp_sim_result', COUNT(*)
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_result';
