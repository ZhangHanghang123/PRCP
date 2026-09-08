-- 升级 KPI 模块：新增 prcp_kpi_scheme + 改 prcp_kpi_definition
-- 旧 prcp_kpi_definition 表：id, kpi_code (UNIQUE), kpi_name, rpt_id, formula, ...
-- 新 prcp_kpi_definition 表：id, scheme_id (FK), kpi_code, kpi_name, rpt_id (FK), formula, ...
--     唯一键改为 (scheme_id, kpi_code)

-- 1. 创建 prcp_kpi_scheme 表
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

-- 2. prcp_kpi_definition 加 scheme_id 字段
-- 若已存在则跳过
ALTER TABLE prcp_kpi_definition
  ADD COLUMN IF NOT EXISTS scheme_id BIGINT NULL AFTER id,
  ADD INDEX IF NOT EXISTS idx_scheme (scheme_id);

-- 3. 删除旧的唯一键 kpi_code，加新的 (scheme_id, kpi_code)
ALTER TABLE prcp_kpi_definition DROP INDEX kpi_code;
ALTER TABLE prcp_kpi_definition ADD UNIQUE KEY uk_scheme_code (scheme_id, kpi_code);

-- 4. 创建默认指标方案
INSERT IGNORE INTO prcp_kpi_scheme (scheme_code, scheme_name, description, status, created_by, updated_by)
VALUES ('SCH_DEFAULT', '默认指标方案', '系统默认指标方案，可基于此扩展', 'ACTIVE', 1, 1);

-- 5. 把现有 prcp_kpi_definition 数据迁移到默认方案
UPDATE prcp_kpi_definition SET scheme_id = (SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_DEFAULT' AND is_deleted=0 LIMIT 1)
WHERE scheme_id IS NULL;

-- 6. 字段改为 NOT NULL
ALTER TABLE prcp_kpi_definition MODIFY COLUMN scheme_id BIGINT NOT NULL;

-- 7. prcp_kpi_value 不变（仍按 kpi_id 关联）

-- 验证
SELECT 'scheme count:' label, COUNT(*) cnt FROM prcp_kpi_scheme WHERE is_deleted=0
UNION ALL
SELECT 'def count:', COUNT(*) FROM prcp_kpi_definition WHERE is_deleted=0;
