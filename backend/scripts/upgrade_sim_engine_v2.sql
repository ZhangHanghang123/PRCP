-- 引擎计量 v2 — 无配置节点也参与计算
-- 改动：
--   1. prcp_sim_result 加 is_configured 字段（1=已配置/新业务模拟 / 0=未配置/纯滚动）
--   2. 不需要新建表
--   3. 兼容旧数据（默认 0）

USE prcp_db;

ALTER TABLE prcp_sim_result
    ADD COLUMN is_configured TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '是否有节点配置（1=已配置 → 新业务模拟；0=未配置 → 纯桶滚动）'
    AFTER category;

-- 为加速过滤，添加索引
ALTER TABLE prcp_sim_result
    ADD INDEX idx_is_configured (is_configured);

-- 同时给 prcp_sim_run 加个统计字段
ALTER TABLE prcp_sim_run
    ADD COLUMN configured_node_count INT NOT NULL DEFAULT 0
    COMMENT '已配置节点数（参与新业务模拟）'
    AFTER total_nodes;

ALTER TABLE prcp_sim_run
    ADD COLUMN rolled_node_count INT NOT NULL DEFAULT 0
    COMMENT '未配置节点数（只做桶滚动）'
    AFTER configured_node_count;
