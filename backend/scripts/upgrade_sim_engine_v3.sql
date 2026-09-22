-- 引擎计量 v3 — 叶子节点 + 汇总节点拆分
-- 改动：
--   1. prcp_sim_result 加 is_aggregated TINYINT(1) DEFAULT 0
--      1=从子叶子聚合出来的汇总节点
--      0=叶子节点（执行了 5 步算法 或 仅滚动）
--   2. 不需要新建表
--   3. 兼容旧数据（默认 0）

USE prcp_db;

ALTER TABLE prcp_sim_result
    ADD COLUMN is_aggregated TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '是否为汇总节点（1=从后代叶子聚合 / 0=叶子节点）'
    AFTER is_configured;

-- 索引加速过滤
ALTER TABLE prcp_sim_result
    ADD INDEX idx_is_aggregated (is_aggregated);
