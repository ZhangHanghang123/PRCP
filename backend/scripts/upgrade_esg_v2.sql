-- =============================================================
-- PRCP ESG · v2 schema 升级（B+D 方案）
--
-- 目标：把 .npz 文件存到数据库
--   - paths_blob LONGBLOB: 完整 npz 字节流（保留原始数据）
--   - 9 个 JSON 统计列：预计算派生统计（前端免算）
--   - n_zeros/n_negatives: 异常样本计数
--   - source_npz_path: 保留旧文件路径（兼容过渡期）
--
-- 兼容性：
--   - ALTER TABLE 可逆
--   - 旧场景（无 blob/JSON）仍可通过 file_path 读取
--   - download endpoint 优先读 blob，缺失则回退到 file_path
-- =============================================================

ALTER TABLE prcp_esg_scenario
  -- B+D 方案核心
  ADD COLUMN paths_blob LONGBLOB NULL
    COMMENT 'npz 字节流（压缩后），完整保留 paths + maturities + initial_yields + seed + metadata_json',
  -- 派生统计：HJM 包络图（p10/p50/p90）
  ADD COLUMN p10_json JSON NULL
    COMMENT 'p10 百分位带 (n_steps × n_maturities)',
  ADD COLUMN p50_json JSON NULL
    COMMENT 'p50 百分位带（中位数路径）',
  ADD COLUMN p90_json JSON NULL
    COMMENT 'p90 百分位带',
  -- 派生统计：终期分布
  ADD COLUMN final_mean_json JSON NULL
    COMMENT '终期利率均值 (n_maturities)',
  ADD COLUMN final_std_json JSON NULL
    COMMENT '终期利率标准差 (n_maturities)',
  ADD COLUMN final_min_json JSON NULL
    COMMENT '终期利率最小值 (n_maturities)',
  ADD COLUMN final_max_json JSON NULL
    COMMENT '终期利率最大值 (n_maturities)',
  -- 派生统计：波动率结构
  ADD COLUMN vol_per_maturity_json JSON NULL
    COMMENT '每个期限的波动率（标准差）',
  -- 异常指标
  ADD COLUMN n_zeros INT DEFAULT 0
    COMMENT '≤0 的利率样本数',
  ADD COLUMN n_negatives INT DEFAULT 0
    COMMENT '<0 的利率样本数';

-- 索引：便于按时间窗查询
CREATE INDEX idx_esg_scenario_scheme_created
  ON prcp_esg_scenario (scheme_id, created_at DESC);
