-- ===========================================
-- PRCP ESG 场景工厂 v1.0 升级脚本 (2026-09-22)
-- 新增 4 张表 + sys_dict 字典 13 项
-- 可重入：每步 IF NOT EXISTS 检查
-- ===========================================
SET NAMES utf8mb4;

-- 1. prcp_esg_scheme（方案配置）
CREATE TABLE IF NOT EXISTS prcp_esg_scheme (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    scheme_code         VARCHAR(32)     NOT NULL,
    scheme_name         VARCHAR(64)     NOT NULL,
    description         TEXT,

    data_source         VARCHAR(16)     NOT NULL DEFAULT 'ECB',
    start_date          DATE,
    end_date            DATE,

    n_factors           INT             NOT NULL DEFAULT 3,
    maturities_json     JSON            NOT NULL,

    n_scenarios         INT             NOT NULL DEFAULT 1000,
    n_steps             INT             NOT NULL DEFAULT 120,
    seed                INT             NOT NULL DEFAULT 42,
    initial_yields_json JSON            NULL,

    status              VARCHAR(16)     NOT NULL DEFAULT 'DRAFT',
    is_deleted          TINYINT(1)      NOT NULL DEFAULT 0,

    created_by          BIGINT,
    updated_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_scheme_code (scheme_code, is_deleted),
    KEY idx_status (status, is_deleted),
    KEY idx_source (data_source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 工厂方案配置';


-- 2. prcp_esg_run（运行历史）
CREATE TABLE IF NOT EXISTS prcp_esg_run (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    scheme_id           BIGINT          NOT NULL,
    scheme_code         VARCHAR(32),

    run_type            VARCHAR(32)     NOT NULL,
    status              VARCHAR(16)     NOT NULL DEFAULT 'SUCCESS',
    params_json         JSON,
    output_json         JSON,
    file_path           VARCHAR(512),

    duration_ms         INT,
    error_message       TEXT,

    created_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_run_scheme (scheme_id, run_type),
    KEY idx_run_status (status),
    KEY idx_run_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 工厂运行历史';


-- 3. prcp_esg_curve_point（Svensson 6 参数曲线）
CREATE TABLE IF NOT EXISTS prcp_esg_curve_point (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    curve_date          DATE            NOT NULL,
    source              VARCHAR(16)     NOT NULL,

    theta0              DECIMAL(20,9),
    theta1              DECIMAL(20,9),
    theta2              DECIMAL(20,9),
    theta3              DECIMAL(20,9),
    lambda1             DECIMAL(20,9),
    lambda2             DECIMAL(20,9),

    raw_data_json       JSON,
    description         VARCHAR(255),

    is_deleted          TINYINT(1)      NOT NULL DEFAULT 0,
    created_by          BIGINT,
    updated_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_curve (source, curve_date, is_deleted),
    KEY idx_curve_date (curve_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Svensson 6 参数曲线统一表';


-- 4. prcp_esg_scenario（情景集持久化索引）
CREATE TABLE IF NOT EXISTS prcp_esg_scenario (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    scheme_id           BIGINT          NOT NULL,
    last_run_id         BIGINT,

    scenario_type       VARCHAR(32)     NOT NULL DEFAULT 'esg_factory',
    file_path           VARCHAR(512)    NOT NULL,
    n_scenarios         INT             NOT NULL,
    n_steps             INT             NOT NULL,
    n_maturities        INT             NOT NULL,
    seed                INT,
    maturities_json     JSON,
    file_size_bytes     BIGINT,
    description         VARCHAR(255),

    created_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted          TINYINT(1)      NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    KEY idx_scn_scheme (scheme_id),
    KEY idx_scn_type (scenario_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 情景集持久化索引';


-- 5. sys_dict 字典扩展（13 项，INSERT IGNORE 可重入）
INSERT IGNORE INTO sys_dict (dict_type, dict_key, dict_label, color, sort_order, status, description, is_deleted)
VALUES
-- 数据源
('PRCP_ESG_SOURCE','ECB','欧洲央行','blue',10,'ACTIVE','ECB AAA 国债收益率',0),
('PRCP_ESG_SOURCE','FRB','美联储','red',20,'ACTIVE','FRB H.15 利率',0),
('PRCP_ESG_SOURCE','CUSTOM','自定义','cyan',30,'ACTIVE','银行自定义曲线',0),
('PRCP_ESG_SOURCE','BANK','本行加点','gold',40,'ACTIVE','本行账簿加点估算',0),
-- 运行类型
('PRCP_ESG_RUN_TYPE','PCA_FIT','PCA 拟合','blue',10,'ACTIVE','主成分因子分解',0),
('PRCP_ESG_RUN_TYPE','HJM_GENERATE','HJM 建模','cyan',20,'ACTIVE','HJM 利率路径生成',0),
('PRCP_ESG_RUN_TYPE','SCENARIO_GENERATE','情景集生成','purple',30,'ACTIVE','.npz 文件持久化',0),
-- 方案状态
('PRCP_ESG_STATUS','DRAFT','草稿','default',10,'ACTIVE','新建未配置完',0),
('PRCP_ESG_STATUS','READY','就绪','green',20,'ACTIVE','配置完成可执行',0),
('PRCP_ESG_STATUS','ARCHIVED','已归档','gray',30,'ACTIVE','历史方案',0),
-- 运行状态
('PRCP_ESG_RUN_STATUS','SUCCESS','成功','green',10,'ACTIVE','执行成功',0),
('PRCP_ESG_RUN_STATUS','FAILED','失败','red',20,'ACTIVE','执行失败',0),
('PRCP_ESG_RUN_STATUS','RUNNING','运行中','blue',30,'ACTIVE','正在执行',0);