-- =============================================================================
-- PRCP 组合反算 · 运行记录日志增强
-- 迁移编号：V20261111_01
-- 说明：
--   1) prcp_reverse_run_log 扩展结构化字段（阶段 / 轮次 / 算法 / 轮次结果）
--   2) 新增 prcp_reverse_run_round 轮次记录表（每轮状态与结果）
--   3) 幂等：可重复执行，已存在则跳过
-- 执行：mysql -u prcp -p prcp_db < V20261111_01_reverse_run_log_round.sql
-- =============================================================================

-- ---------- 1. 扩展 prcp_reverse_run_log ----------
-- stage：阶段标识 SUBMIT / LOAD_TARGET / LOAD_BALANCE / SOLVE / SAVE_RESULT / DONE / FAILED
-- round_no：轮次序号（1 起；单轮算法恒为 1）
-- algo：算法或引擎标识 CVXPY_QP / CVXPY_LP / HEURISTIC / ACOR / DE / SLSQP / DL
-- round_result：该轮关键结果快照 JSON（评分 / 最优值 / 目标达成）
SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_log'
            AND COLUMN_NAME = 'stage');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_log ADD COLUMN stage VARCHAR(24) NULL COMMENT ''阶段：SUBMIT/LOAD_TARGET/LOAD_BALANCE/SOLVE/SAVE_RESULT/DONE/FAILED''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_log'
            AND COLUMN_NAME = 'round_no');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_log ADD COLUMN round_no INT NULL COMMENT ''轮次序号，1 起；单轮算法恒为 1''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_log'
            AND COLUMN_NAME = 'algo');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_log ADD COLUMN algo VARCHAR(24) NULL COMMENT ''算法/引擎标识：CVXPY_QP/CVXPY_LP/HEURISTIC/ACOR/DE/SLSQP/DL''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_log'
            AND COLUMN_NAME = 'round_result');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_log ADD COLUMN round_result JSON NULL COMMENT ''该轮关键结果快照：score/optimal_value/target_hit/metrics''',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @c := (SELECT COUNT(*) FROM information_schema.STATISTICS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_log'
            AND INDEX_NAME = 'idx_run_stage');
SET @s := IF(@c = 0,
  'ALTER TABLE prcp_reverse_run_log ADD INDEX idx_run_stage (run_id, stage, id)',
  'DO 0');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

-- ---------- 2. 新增 prcp_reverse_run_round（轮次记录）----------
CREATE TABLE IF NOT EXISTS prcp_reverse_run_round (
  id             BIGINT       NOT NULL AUTO_INCREMENT,
  run_id         BIGINT       NOT NULL COMMENT '运行记录 id',
  round_no       INT          NOT NULL COMMENT '轮次序号，1 起',
  algo           VARCHAR(24)  NOT NULL COMMENT '算法/引擎标识',
  stage          VARCHAR(24)  NULL     COMMENT '该轮所处阶段',
  status         VARCHAR(16)  NOT NULL DEFAULT 'RUNNING'
                             COMMENT 'RUNNING / SUCCESS / FAILED / CANCELLED',
  progress       DECIMAL(5,2) NULL     DEFAULT 0.00,
  score          DECIMAL(10,2) NULL    COMMENT '该轮综合评分（0~500）',
  optimal_value  DECIMAL(20,6) NULL    COMMENT '该轮最优目标函数值',
  target_hit     TINYINT(1)   NULL     COMMENT '是否全部目标达成：1 是 0 否',
  message        VARCHAR(500) NULL     COMMENT '该轮结论摘要',
  metrics        JSON         NULL     COMMENT '该轮指标实测值快照',
  started_at     DATETIME     NULL,
  ended_at       DATETIME     NULL,
  duration_sec   INT          NULL,
  created_at     DATETIME     NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME     NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_run_round_algo (run_id, round_no, algo),
  KEY idx_run (run_id),
  KEY idx_run_status (run_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组合反算运行轮次记录（每轮状态与结果）';

-- ---------- 3. 校验 ----------
SELECT 'prcp_reverse_run_log 结构化字段' AS check_item,
       GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION) AS columns_now
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_log'
  AND COLUMN_NAME IN ('stage','round_no','algo','round_result');

SELECT 'prcp_reverse_run_round' AS check_item,
       COUNT(*) AS cols FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_reverse_run_round';
