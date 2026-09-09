-- 升级 prcp_data_balance 表：增加 7 个指标列（v6 账户册月度量纲）
-- MySQL 8 不支持 IF NOT EXISTS，用 INFORMATION_SCHEMA + PREPARE 实现幂等
SET @col := 'begin_balance';
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_data_balance' AND COLUMN_NAME = @col) = 0,
  'ALTER TABLE prcp_data_balance ADD COLUMN begin_balance DECIMAL(20,4) DEFAULT 0 COMMENT ''月初余额'' AFTER current_amount',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := 'avg_balance';
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_data_balance' AND COLUMN_NAME = @col) = 0,
  'ALTER TABLE prcp_data_balance ADD COLUMN avg_balance DECIMAL(20,4) DEFAULT 0 COMMENT ''平均余额'' AFTER begin_balance',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := 'interest_rate';
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_data_balance' AND COLUMN_NAME = @col) = 0,
  'ALTER TABLE prcp_data_balance ADD COLUMN interest_rate DECIMAL(10,6) DEFAULT 0 COMMENT ''加权平均利率%'' AFTER avg_balance',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := 'interest_amount';
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_data_balance' AND COLUMN_NAME = @col) = 0,
  'ALTER TABLE prcp_data_balance ADD COLUMN interest_amount DECIMAL(20,6) DEFAULT 0 COMMENT ''平均利息收支'' AFTER interest_rate',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := 'capital_ratio';
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_data_balance' AND COLUMN_NAME = @col) = 0,
  'ALTER TABLE prcp_data_balance ADD COLUMN capital_ratio DECIMAL(10,6) DEFAULT 0 COMMENT ''资本占用比例%'' AFTER interest_amount',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := 'risk_weight';
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prcp_data_balance' AND COLUMN_NAME = @col) = 0,
  'ALTER TABLE prcp_data_balance ADD COLUMN risk_weight DECIMAL(10,6) DEFAULT 0 COMMENT ''风险权重%'' AFTER capital_ratio',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;