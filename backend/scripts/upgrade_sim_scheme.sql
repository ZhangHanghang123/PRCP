-- ============================================================
-- PRCP 新业务模拟方案 3 张表 升级脚本
-- 时间：2026-09-21
-- 配套文档：docs/新业务模拟_需求分析.md + 数据库设计.md + 页面原型.html
--
-- 新增 3 张表：
--   prcp_sim_scheme         方案主表
--   prcp_sim_node_config    节点配置表（per 叶子节点）
--   prcp_sim_term_ratio     期限占比明细表（per 节点配置）
--
-- 幂等保护：每张表先检查存在性
-- ============================================================

USE prcp_db;

-- ============================================================
-- 一、prcp_sim_scheme（方案主表）
-- ============================================================
SET @t_exists := (
  SELECT COUNT(*) FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_scheme'
);
SET @sql := IF(@t_exists = 0, '
CREATE TABLE prcp_sim_scheme (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  scheme_code     VARCHAR(32) NOT NULL,
  scheme_name     VARCHAR(64) NOT NULL,
  coa_scheme_id   BIGINT NOT NULL                          COMMENT "FK → prcp_coa_scheme.id（创建后不可变更）",
  description     TEXT,
  config_node_count INT DEFAULT 0                          COMMENT "冗余：已配置节点数",
  status          VARCHAR(16) DEFAULT "ACTIVE"            COMMENT "ACTIVE/INACTIVE",
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_scheme_code (scheme_code, is_deleted)    COMMENT "软删除 + UNIQUE 复活",
  INDEX idx_coa_scheme (coa_scheme_id),
  INDEX idx_status (status),
  CONSTRAINT fk_sim_scheme_coa FOREIGN KEY (coa_scheme_id) REFERENCES prcp_coa_scheme(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT="新业务模拟方案"', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ============================================================
-- 二、prcp_sim_node_config（节点配置表）
-- ============================================================
SET @t_exists := (
  SELECT COUNT(*) FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_node_config'
);
SET @sql := IF(@t_exists = 0, '
CREATE TABLE prcp_sim_node_config (
  id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
  scheme_id           BIGINT NOT NULL                      COMMENT "FK → prcp_sim_scheme.id",
  coa_node_id         BIGINT NOT NULL                      COMMENT "FK → prcp_coa_node.id（仅 L3+ 叶子）",
  coa_node_code       VARCHAR(32)                          COMMENT "冗余：节点编码（兼容历史归档）",
  annual_growth_rate  DECIMAL(8,4) DEFAULT 0               COMMENT "年化目标增长率（%）",
  term_unit           VARCHAR(8) DEFAULT "MONTH"           COMMENT "期限单位 ENUM（当前固定 MONTH）",
  term_count          INT DEFAULT 0                        COMMENT "冗余：当前配置的期限条数",
  remark              TEXT,
  is_deleted          TINYINT(1) DEFAULT 0,
  created_by          BIGINT,
  updated_by          BIGINT,
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_scheme_node (scheme_id, coa_node_id, is_deleted) COMMENT "软删除 + UNIQUE 复活",
  INDEX idx_scheme (scheme_id),
  INDEX idx_node (coa_node_id),
  CONSTRAINT fk_sim_cfg_scheme FOREIGN KEY (scheme_id) REFERENCES prcp_sim_scheme(id),
  CONSTRAINT fk_sim_cfg_node FOREIGN KEY (coa_node_id) REFERENCES prcp_coa_node(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT="新业务模拟节点配置"', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ============================================================
-- 三、prcp_sim_term_ratio（期限占比明细表）
-- ============================================================
SET @t_exists := (
  SELECT COUNT(*) FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_term_ratio'
);
SET @sql := IF(@t_exists = 0, '
CREATE TABLE prcp_sim_term_ratio (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  config_id       BIGINT NOT NULL                          COMMENT "FK → prcp_sim_node_config.id",
  term_value      INT NOT NULL                             COMMENT "期限值（1~60 月）",
  term_unit       VARCHAR(8) DEFAULT "MONTH"               COMMENT "期限单位（与 config.term_unit 一致）",
  business_ratio  DECIMAL(8,4) NOT NULL                    COMMENT "业务占比（%）",
  sort_order      INT DEFAULT 0                            COMMENT "显示顺序",
  remark          VARCHAR(255),
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_config (config_id),
  INDEX idx_term (term_value, term_unit),
  CONSTRAINT fk_sim_ratio_cfg FOREIGN KEY (config_id) REFERENCES prcp_sim_node_config(id),
  CONSTRAINT chk_term_value CHECK (term_value BETWEEN 1 AND 60),
  CONSTRAINT chk_business_ratio CHECK (business_ratio >= 0 AND business_ratio <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT="新业务期限占比明细（应用层校验求和=100%）"', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ============================================================
-- 四、验证
-- ============================================================
SELECT 'prcp_sim_scheme' AS tbl_, COUNT(*) AS col_cnt
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_scheme'
UNION ALL
SELECT 'prcp_sim_node_config', COUNT(*)
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_node_config'
UNION ALL
SELECT 'prcp_sim_term_ratio', COUNT(*)
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'prcp_db' AND TABLE_NAME = 'prcp_sim_term_ratio';