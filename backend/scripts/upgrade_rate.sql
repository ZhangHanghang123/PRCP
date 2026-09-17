-- =====================================================================
-- PRCP 利率管理模块（2 张表）
-- 表结构：每条曲线 × 每个数据日期 = 一行
--         13 个期限利率作为列存储（rate_d1..rate_y30）
-- =====================================================================

-- 1. 收益率曲线方案
CREATE TABLE IF NOT EXISTS prcp_rate_scheme (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  curve_code      VARCHAR(64) NOT NULL UNIQUE,
                 -- 曲线编码（如 CN_SOV_CNY 中国国债 / CN_POL_CNY 政金）
  curve_name      VARCHAR(128) NOT NULL,
                 -- 曲线名称
  curve_type      VARCHAR(32) NOT NULL,
                 -- 曲线类型：SOVEREIGN/POLICY/CD/LPR/FTP/CUSTOM
  ccy             VARCHAR(8) NOT NULL DEFAULT 'CNY',
                 -- 币种
  data_source     VARCHAR(32) NOT NULL DEFAULT 'WIND',
                 -- 数据源：WIND/CHOICE/中债登/央行/手工
  description     TEXT,
  status          VARCHAR(16) DEFAULT 'ACTIVE',
                 -- ACTIVE/HISTORY/DRAFT
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_type (curve_type),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收益率曲线方案';

-- 2. 收益率曲线明细（每行 = 一条曲线 × 一个数据日期）
CREATE TABLE IF NOT EXISTS prcp_rate_point (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  curve_id        BIGINT NOT NULL,
                 -- 关联 prcp_rate_scheme.id
  curve_code      VARCHAR(64) NOT NULL,
                 -- 冗余：便于按曲线编码快速查询
  data_date       DATE NOT NULL,
                 -- 利率数据日期
  ccy             VARCHAR(8) NOT NULL DEFAULT 'CNY',
                 -- 冗余币种
  -- 13 个期限点（年化利率，单位 %，保留 4 位小数）
  rate_d1         DECIMAL(10,6) DEFAULT 0,
                 -- 1日
  rate_d7         DECIMAL(10,6) DEFAULT 0,
                 -- 7日
  rate_m1         DECIMAL(10,6) DEFAULT 0,
                 -- 1M
  rate_m3         DECIMAL(10,6) DEFAULT 0,
                 -- 3M
  rate_m6         DECIMAL(10,6) DEFAULT 0,
                 -- 6M
  rate_y1         DECIMAL(10,6) DEFAULT 0,
                 -- 1Y
  rate_y2         DECIMAL(10,6) DEFAULT 0,
                 -- 2Y
  rate_y3         DECIMAL(10,6) DEFAULT 0,
                 -- 3Y
  rate_y5         DECIMAL(10,6) DEFAULT 0,
                 -- 5Y
  rate_y10        DECIMAL(10,6) DEFAULT 0,
                 -- 10Y（关键期限）
  rate_y15        DECIMAL(10,6) DEFAULT 0,
                 -- 15Y
  rate_y20        DECIMAL(10,6) DEFAULT 0,
                 -- 20Y
  rate_y30        DECIMAL(10,6) DEFAULT 0,
                 -- 30Y
  -- 度量
  curve_shift_bps DECIMAL(10,4) DEFAULT 0,
                 -- BP 平移：当日 10Y - 上日 10Y（自动计算）
  curve_slope     DECIMAL(10,6) DEFAULT 0,
                 -- 曲线斜率：10Y - 1Y
  source_date     DATE,
                 -- 数据发布日期（数据源提供的日期）
  remark          TEXT,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_curve_date (curve_code, data_date, is_deleted),
  INDEX idx_curve (curve_id),
  INDEX idx_date (data_date),
  INDEX idx_curve_date_active (curve_code, data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收益率曲线明细（每条曲线×每个日期一行）';

-- 3. 种子数据：6 条曲线方案
INSERT IGNORE INTO prcp_rate_scheme
  (curve_code, curve_name, curve_type, ccy, data_source, description, status, created_by)
VALUES
  ('CN_SOV_CNY',   '中国国债收益率曲线（人民币）',           'SOVEREIGN', 'CNY', 'WIND',     '财政部发行的记账式国债收益率',           'ACTIVE', 1),
  ('CN_POL_CNY',   '政策性金融债收益率曲线（人民币）',       'POLICY',    'CNY', 'WIND',     '国开行/进出口行/农发行的金融债收益率',   'ACTIVE', 1),
  ('CN_CD_CNY',    '同业存单收益率曲线（人民币）',           'CD',        'CNY', 'WIND',     '银行间市场同业存单收益率',               'ACTIVE', 1),
  ('CN_LPR_CNY',   'LPR 贷款市场报价利率曲线（人民币）',    'LPR',       'CNY', '央行',     '央行授权全国银行间同业拆借中心发布',     'ACTIVE', 1),
  ('CN_FTP_CNY',   '内部 FTP 转移定价曲线（人民币）',        'FTP',       'CNY', '内部',     '银行内部资金转移定价',                   'ACTIVE', 1),
  ('CN_CORP_CNY',  '企业债（AAA）收益率曲线（人民币）',      'CUSTOM',    'CNY', 'WIND',     'AAA 级企业债收益率（参考）',             'HISTORY', 1);

-- 4. 种子数据：CN_SOV_CNY 中国国债（2026-09-17 当日）
INSERT IGNORE INTO prcp_rate_point
  (curve_code, data_date, ccy, rate_d1, rate_d7, rate_m1, rate_m3, rate_m6,
   rate_y1, rate_y2, rate_y3, rate_y5, rate_y10, rate_y15, rate_y20, rate_y30,
   curve_slope, source_date, remark, created_by)
VALUES
  ('CN_SOV_CNY', '2026-09-17', 'CNY',
   1.5000, 1.6500, 1.8500, 2.0500, 2.1500,
   2.2500, 2.3500, 2.4500, 2.6000, 2.7500, 2.8500, 2.9500, 3.0500,
   0.5000, '2026-09-17', '中国国债收益率曲线 · 初始化种子数据', 1);

-- 5. 种子数据：CN_FTP_CNY 内部 FTP（2026-09-17 当日）
INSERT IGNORE INTO prcp_rate_point
  (curve_code, data_date, ccy, rate_d1, rate_d7, rate_m1, rate_m3, rate_m6,
   rate_y1, rate_y2, rate_y3, rate_y5, rate_y10, rate_y15, rate_y20, rate_y30,
   curve_slope, source_date, remark, created_by)
VALUES
  ('CN_FTP_CNY', '2026-09-17', 'CNY',
   1.8000, 2.0000, 2.2000, 2.4000, 2.5000,
   2.6000, 2.7000, 2.8000, 3.0000, 3.1500, 3.2500, 3.3500, 3.4500,
   0.5500, '2026-09-17', '内部 FTP 转移定价曲线 · 初始化种子数据', 1);