-- ============================================================
-- 00_setup_schema.sql - 建表语句（指标管理 / 模型管理 / 测算方案）
-- 数据库: prcp_db (MySQL 8.0, InnoDB, utf8mb4)
-- 说明: 全部用 IF NOT EXISTS，幂等可重复执行
-- ============================================================

SET NAMES utf8mb4;

-- ============================================================
-- 一、指标管理 (KPI Scheme / Definition / Score Rule / Segment)
-- ============================================================

CREATE TABLE IF NOT EXISTS prcp_kpi_scheme (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_code     VARCHAR(32) NOT NULL UNIQUE,
    scheme_name     VARCHAR(64) NOT NULL,
    description     TEXT,
    kpi_count       INT DEFAULT 0,
    status          VARCHAR(16) DEFAULT 'ACTIVE',
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      BIGINT,
    updated_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标方案';

CREATE TABLE IF NOT EXISTS prcp_kpi_definition (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_id       BIGINT NOT NULL,
    kpi_code        VARCHAR(64) NOT NULL,
    kpi_name        VARCHAR(128) NOT NULL,
    indicator_type  VARCHAR(16) DEFAULT 'FORMULA',
    formula         TEXT,
    calc_unit       VARCHAR(16),
    threshold_min   DECIMAL(20,6),
    threshold_max   DECIMAL(20,6),
    formula_desc    TEXT,
    status          VARCHAR(16) DEFAULT 'ACTIVE',
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      BIGINT,
    updated_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_scheme_code (scheme_id, kpi_code),
    INDEX idx_scheme (scheme_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标定义';

CREATE TABLE IF NOT EXISTS prcp_kpi_score_rule (
    id                BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_id         BIGINT NOT NULL,
    kpi_id            BIGINT NOT NULL,
    rule_name         VARCHAR(128) NOT NULL,
    calc_method       VARCHAR(16) DEFAULT 'PIECEWISE',
    total_score       DECIMAL(8,2) DEFAULT 100.00,
    higher_is_better  TINYINT(1) DEFAULT 1,
    description       TEXT,
    status            VARCHAR(16) DEFAULT 'ACTIVE',
    is_deleted        TINYINT(1) DEFAULT 0,
    created_by        BIGINT,
    updated_by        BIGINT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_kpi_rule (kpi_id, rule_name, is_deleted),
    INDEX idx_kpi (kpi_id),
    INDEX idx_scheme (scheme_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评分规则';

CREATE TABLE IF NOT EXISTS prcp_kpi_score_segment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_id         BIGINT NOT NULL,
    seg_order       INT NOT NULL DEFAULT 0,
    min_value       DECIMAL(20,6),
    max_value       DECIMAL(20,6),
    score           DECIMAL(8,2) NOT NULL,
    segment_desc    VARCHAR(255),
    is_deleted      TINYINT(1) DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rule (rule_id, seg_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评分规则的分段区间';

CREATE TABLE IF NOT EXISTS prcp_kpi_value (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    kpi_id          BIGINT NOT NULL,
    data_date       DATE NOT NULL,
    version         VARCHAR(32) NOT NULL DEFAULT 'V1.0',
    current_value   DECIMAL(20,6),
    prev_value      DECIMAL(20,6),
    prev_year_value DECIMAL(20,6),
    calc_source     VARCHAR(32) DEFAULT 'MODEL',
    calc_log        TEXT,
    score           DECIMAL(8,2),
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      BIGINT,
    updated_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_kpi_date (kpi_id, data_date, version, is_deleted),
    INDEX idx_data_date (data_date),
    INDEX idx_kpi (kpi_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标值';

-- ============================================================
-- 二、模型管理 (Model / Version / Param)
-- ============================================================

CREATE TABLE IF NOT EXISTS prcp_model (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_code      VARCHAR(32) NOT NULL UNIQUE,
    model_name      VARCHAR(128) NOT NULL,
    model_type      VARCHAR(32) NOT NULL DEFAULT 'LINEAR_REGRESSION',
    description     TEXT,
    algo_config     JSON,
    biz_domain      VARCHAR(32),
    kpi_scheme_id   BIGINT,
    status          VARCHAR(16) DEFAULT 'ACTIVE',
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      BIGINT,
    updated_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (model_type),
    INDEX idx_status (status),
    INDEX idx_kpi_scheme (kpi_scheme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型主表';

CREATE TABLE IF NOT EXISTS prcp_model_version (
    id                BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id          BIGINT NOT NULL,
    version_code      VARCHAR(32) NOT NULL,
    version_name      VARCHAR(128) NOT NULL,
    parent_version_id BIGINT DEFAULT NULL,
    param_count       INT DEFAULT 0,
    description       TEXT,
    status            VARCHAR(16) DEFAULT 'DRAFT',
    is_deleted        TINYINT(1) DEFAULT 0,
    created_by        BIGINT,
    updated_by        BIGINT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_model_version (model_id, version_code, is_deleted),
    INDEX idx_parent (parent_version_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型参数版本';

CREATE TABLE IF NOT EXISTS prcp_model_param (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    version_id      BIGINT NOT NULL,
    kpi_id          BIGINT NOT NULL,
    kpi_code        VARCHAR(64),
    param_code      VARCHAR(64) NOT NULL,
    param_name      VARCHAR(128) NOT NULL,
    param_type      VARCHAR(16) DEFAULT 'BASE',
    param_category  VARCHAR(32) DEFAULT 'BASE',
    param_value     DECIMAL(20,6) DEFAULT 0,
    param_value_str VARCHAR(255),
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
    UNIQUE KEY uk_version_param (version_id, param_code, is_deleted),
    INDEX idx_kpi (kpi_id),
    INDEX idx_version (version_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型参数明细';

-- ============================================================
-- 三、测算方案 (Sim Scheme / Run / Result)
-- ============================================================

CREATE TABLE IF NOT EXISTS prcp_sim_scheme (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_code         VARCHAR(32) NOT NULL,
    scheme_name         VARCHAR(64) NOT NULL,
    coa_scheme_id       BIGINT NOT NULL COMMENT 'FK → prcp_coa_scheme.id',
    description         TEXT,
    config_node_count   INT DEFAULT 0,
    status              VARCHAR(16) DEFAULT 'ACTIVE',
    is_deleted          TINYINT(1) DEFAULT 0,
    created_by          BIGINT,
    updated_by          BIGINT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_scheme_code (scheme_code, is_deleted),
    INDEX idx_coa_scheme (coa_scheme_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测算方案';

CREATE TABLE IF NOT EXISTS prcp_sim_scheme_node (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_id           BIGINT NOT NULL,
    node_id             BIGINT NOT NULL,
    node_code           VARCHAR(32),
    node_name           VARCHAR(64),
    alloc_pct           DECIMAL(8,4) DEFAULT 0 COMMENT '信贷/带息负债占比',
    duration_months     INT DEFAULT 12 COMMENT '期限（月）',
    base_balance        DECIMAL(20,4) DEFAULT 0 COMMENT '基准余额',
    scenario_rate_pct   DECIMAL(20,4)  DEFAULT 0 COMMENT '情景利率(%)',
    scenario_growth_pct DECIMAL(8,4) DEFAULT 0 COMMENT '增长率(%)',
    description         TEXT,
    sort_order          INT DEFAULT 0,
    is_deleted          TINYINT(1) DEFAULT 0,
    created_by          BIGINT,
    updated_by          BIGINT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_scheme_node (scheme_id, node_id),
    INDEX idx_scheme (scheme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测算方案节点配置';

CREATE TABLE IF NOT EXISTS prcp_sim_run (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    sim_scheme_id   BIGINT NOT NULL,
    sim_scheme_code VARCHAR(32) NOT NULL,
    base_data_date  DATE NOT NULL COMMENT '基准月',
    month_count     INT DEFAULT 24,
    target_data_date DATE,
    status          VARCHAR(16) DEFAULT 'PENDING',
    progress        INT DEFAULT 0,
    total_nodes     INT DEFAULT 0,
    processed_nodes INT DEFAULT 0,
    model_id        BIGINT COMMENT '使用的模型 (NLS_REG/ACO_OPT/DNN_REG)',
    model_version_id BIGINT DEFAULT NULL,
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      BIGINT,
    updated_by      BIGINT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_scheme (sim_scheme_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测算运行实例';

-- ============================================================
-- 四、账户册方案 (COA Scheme / Node) + 铺底指标系数
-- ============================================================

CREATE TABLE IF NOT EXISTS prcp_coa_scheme (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_code     VARCHAR(32) NOT NULL UNIQUE,
    scheme_name     VARCHAR(64) NOT NULL,
    description     TEXT,
    status          VARCHAR(16) DEFAULT 'ACTIVE',
    node_count      INT DEFAULT 0,
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      BIGINT,
    updated_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户册方案';

CREATE TABLE IF NOT EXISTS prcp_coa_node (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    scheme_id       BIGINT NOT NULL,
    node_code       VARCHAR(32) NOT NULL,
    node_name       VARCHAR(64) NOT NULL,
    parent_id       BIGINT,
    node_level      INT DEFAULT 1,
    node_type       VARCHAR(16),
    path            VARCHAR(255),
    sort_order      INT DEFAULT 0,
    status          VARCHAR(16) DEFAULT 'ACTIVE',
    description     TEXT,
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      BIGINT,
    updated_by      BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_scheme_code (scheme_id, node_code),
    INDEX idx_parent (parent_id),
    INDEX idx_scheme (scheme_id),
    INDEX idx_path (path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户册节点';

CREATE TABLE IF NOT EXISTS prcp_metric_coefficient (
    id              VARCHAR(128) NOT NULL,
    scheme_id       INT NOT NULL,
    scheme_code     VARCHAR(64) NOT NULL,
    node_id         INT NOT NULL,
    node_code       VARCHAR(64) NOT NULL,
    metric_type     VARCHAR(32) NOT NULL,
    metric_code     VARCHAR(32) NOT NULL,
    data_date       DATE NOT NULL,
    current_value   DECIMAL(20,6) DEFAULT 0,
    y1_value        DECIMAL(20,6) DEFAULT 0,
    y2_value        DECIMAL(20,6) DEFAULT 0,
    y3_value        DECIMAL(20,6) DEFAULT 0,
    y4_value        DECIMAL(20,6) DEFAULT 0,
    y5_value        DECIMAL(20,6) DEFAULT 0,
    unit            VARCHAR(16) DEFAULT 'PERCENT',
    description     VARCHAR(500),
    status          VARCHAR(16) DEFAULT 'ACTIVE',
    is_deleted      TINYINT(1) DEFAULT 0,
    created_by      INT,
    updated_by      INT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_mc_unique (scheme_code, node_code, metric_code, data_date, is_deleted),
    INDEX idx_mc_scheme_date (scheme_id, data_date),
    INDEX idx_mc_node_date   (node_id, data_date),
    INDEX idx_mc_metric_type (metric_type, data_date),
    INDEX idx_mc_updated     (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标计量系数维护';

-- ============================================================
-- 结束
-- ============================================================
SELECT '✅ 00_setup_schema.sql 完成 - 共 10 张表' AS status;