-- 升级期限桶：1年内按月拆分(m1-m12)，去掉 1日/7日 (d1/d7)，清理 m13-m60 死列
-- 影响表：prcp_data_basic + prcp_data_reverse
-- 数据库：prcp_db（PRCP 平台），执行前请先备份

SET @db := DATABASE();

-- ============================================================
-- A) prcp_data_basic
-- ============================================================

-- A1) 删除 d1, d7 期限桶（1日/7日）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_basic' AND COLUMN_NAME='orig_d1')>0,
  'ALTER TABLE prcp_data_basic DROP COLUMN orig_d1, DROP COLUMN orig_d7, DROP COLUMN rem_d1, DROP COLUMN rem_d7',
  'SELECT 1 AS noop_drop_basic_d'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- A2) 添加 m1-m12 月度桶（替换原 m1/m3/m6 聚合桶）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_basic' AND COLUMN_NAME='orig_m2')=0,
  'ALTER TABLE prcp_data_basic
     ADD COLUMN orig_m2  DECIMAL(20,4) DEFAULT 0 AFTER orig_m1,
     ADD COLUMN orig_m4  DECIMAL(20,4) DEFAULT 0 AFTER orig_m3,
     ADD COLUMN orig_m5  DECIMAL(20,4) DEFAULT 0 AFTER orig_m4,
     ADD COLUMN orig_m7  DECIMAL(20,4) DEFAULT 0 AFTER orig_m6,
     ADD COLUMN orig_m8  DECIMAL(20,4) DEFAULT 0 AFTER orig_m7,
     ADD COLUMN orig_m9  DECIMAL(20,4) DEFAULT 0 AFTER orig_m8,
     ADD COLUMN orig_m10 DECIMAL(20,4) DEFAULT 0 AFTER orig_m9,
     ADD COLUMN orig_m11 DECIMAL(20,4) DEFAULT 0 AFTER orig_m10,
     ADD COLUMN orig_m12 DECIMAL(20,4) DEFAULT 0 AFTER orig_m11',
  'SELECT 1 AS noop_add_basic_orig_m'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_basic' AND COLUMN_NAME='rem_m2')=0,
  'ALTER TABLE prcp_data_basic
     ADD COLUMN rem_m2  DECIMAL(20,4) DEFAULT 0 AFTER rem_m1,
     ADD COLUMN rem_m4  DECIMAL(20,4) DEFAULT 0 AFTER rem_m3,
     ADD COLUMN rem_m5  DECIMAL(20,4) DEFAULT 0 AFTER rem_m4,
     ADD COLUMN rem_m7  DECIMAL(20,4) DEFAULT 0 AFTER rem_m6,
     ADD COLUMN rem_m8  DECIMAL(20,4) DEFAULT 0 AFTER rem_m7,
     ADD COLUMN rem_m9  DECIMAL(20,4) DEFAULT 0 AFTER rem_m8,
     ADD COLUMN rem_m10 DECIMAL(20,4) DEFAULT 0 AFTER rem_m9,
     ADD COLUMN rem_m11 DECIMAL(20,4) DEFAULT 0 AFTER rem_m10,
     ADD COLUMN rem_m12 DECIMAL(20,4) DEFAULT 0 AFTER rem_m11',
  'SELECT 1 AS noop_add_basic_rem_m'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- A3) 删除 m13-m60 死列（这些列从未被填充，全为 0）
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_basic' AND COLUMN_NAME='orig_m13')>0,
  'ALTER TABLE prcp_data_basic
     DROP COLUMN orig_m13, DROP COLUMN orig_m14, DROP COLUMN orig_m15, DROP COLUMN orig_m16, DROP COLUMN orig_m17,
     DROP COLUMN orig_m18, DROP COLUMN orig_m19, DROP COLUMN orig_m20, DROP COLUMN orig_m21, DROP COLUMN orig_m22,
     DROP COLUMN orig_m23, DROP COLUMN orig_m24, DROP COLUMN orig_m25, DROP COLUMN orig_m26, DROP COLUMN orig_m27,
     DROP COLUMN orig_m28, DROP COLUMN orig_m29, DROP COLUMN orig_m30, DROP COLUMN orig_m31, DROP COLUMN orig_m32,
     DROP COLUMN orig_m33, DROP COLUMN orig_m34, DROP COLUMN orig_m35, DROP COLUMN orig_m36, DROP COLUMN orig_m37,
     DROP COLUMN orig_m38, DROP COLUMN orig_m39, DROP COLUMN orig_m40, DROP COLUMN orig_m41, DROP COLUMN orig_m42,
     DROP COLUMN orig_m43, DROP COLUMN orig_m44, DROP COLUMN orig_m45, DROP COLUMN orig_m46, DROP COLUMN orig_m47,
     DROP COLUMN orig_m48, DROP COLUMN orig_m49, DROP COLUMN orig_m50, DROP COLUMN orig_m51, DROP COLUMN orig_m52,
     DROP COLUMN orig_m53, DROP COLUMN orig_m54, DROP COLUMN orig_m55, DROP COLUMN orig_m56, DROP COLUMN orig_m57,
     DROP COLUMN orig_m58, DROP COLUMN orig_m59, DROP COLUMN orig_m60',
  'SELECT 1 AS noop_drop_basic_orig_m13_60'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_basic' AND COLUMN_NAME='rem_m13')>0,
  'ALTER TABLE prcp_data_basic
     DROP COLUMN rem_m13, DROP COLUMN rem_m14, DROP COLUMN rem_m15, DROP COLUMN rem_m16, DROP COLUMN rem_m17,
     DROP COLUMN rem_m18, DROP COLUMN rem_m19, DROP COLUMN rem_m20, DROP COLUMN rem_m21, DROP COLUMN rem_m22,
     DROP COLUMN rem_m23, DROP COLUMN rem_m24, DROP COLUMN rem_m25, DROP COLUMN rem_m26, DROP COLUMN rem_m27,
     DROP COLUMN rem_m28, DROP COLUMN rem_m29, DROP COLUMN rem_m30, DROP COLUMN rem_m31, DROP COLUMN rem_m32,
     DROP COLUMN rem_m33, DROP COLUMN rem_m34, DROP COLUMN rem_m35, DROP COLUMN rem_m36, DROP COLUMN rem_m37,
     DROP COLUMN rem_m38, DROP COLUMN rem_m39, DROP COLUMN rem_m40, DROP COLUMN rem_m41, DROP COLUMN rem_m42,
     DROP COLUMN rem_m43, DROP COLUMN rem_m44, DROP COLUMN rem_m45, DROP COLUMN rem_m46, DROP COLUMN rem_m47,
     DROP COLUMN rem_m48, DROP COLUMN rem_m49, DROP COLUMN rem_m50, DROP COLUMN rem_m51, DROP COLUMN rem_m52,
     DROP COLUMN rem_m53, DROP COLUMN rem_m54, DROP COLUMN rem_m55, DROP COLUMN rem_m56, DROP COLUMN rem_m57,
     DROP COLUMN rem_m58, DROP COLUMN rem_m59, DROP COLUMN rem_m60',
  'SELECT 1 AS noop_drop_basic_rem_m13_60'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- A4) 验证 prcp_data_basic 列
SELECT 'basic_columns_after' AS info, COLUMN_NAME, ORDINAL_POSITION
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_basic'
  AND (COLUMN_NAME LIKE 'orig\_%' OR COLUMN_NAME LIKE 'rem\_%')
ORDER BY ORDINAL_POSITION;

-- ============================================================
-- B) prcp_data_reverse
-- ============================================================

-- B1) 删除 d1, d7 期限桶
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_reverse' AND COLUMN_NAME='orig_d1')>0,
  'ALTER TABLE prcp_data_reverse DROP COLUMN orig_d1, DROP COLUMN orig_d7, DROP COLUMN rem_d1, DROP COLUMN rem_d7',
  'SELECT 1 AS noop_drop_reverse_d'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- B2) 添加 m1-m12 月度桶
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_reverse' AND COLUMN_NAME='orig_m2')=0,
  'ALTER TABLE prcp_data_reverse
     ADD COLUMN orig_m2  DECIMAL(20,4) DEFAULT 0 AFTER orig_m1,
     ADD COLUMN orig_m4  DECIMAL(20,4) DEFAULT 0 AFTER orig_m3,
     ADD COLUMN orig_m5  DECIMAL(20,4) DEFAULT 0 AFTER orig_m4,
     ADD COLUMN orig_m7  DECIMAL(20,4) DEFAULT 0 AFTER orig_m6,
     ADD COLUMN orig_m8  DECIMAL(20,4) DEFAULT 0 AFTER orig_m7,
     ADD COLUMN orig_m9  DECIMAL(20,4) DEFAULT 0 AFTER orig_m8,
     ADD COLUMN orig_m10 DECIMAL(20,4) DEFAULT 0 AFTER orig_m9,
     ADD COLUMN orig_m11 DECIMAL(20,4) DEFAULT 0 AFTER orig_m10,
     ADD COLUMN orig_m12 DECIMAL(20,4) DEFAULT 0 AFTER orig_m11',
  'SELECT 1 AS noop_add_reverse_orig_m'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_reverse' AND COLUMN_NAME='rem_m2')=0,
  'ALTER TABLE prcp_data_reverse
     ADD COLUMN rem_m2  DECIMAL(20,4) DEFAULT 0 AFTER rem_m1,
     ADD COLUMN rem_m4  DECIMAL(20,4) DEFAULT 0 AFTER rem_m3,
     ADD COLUMN rem_m5  DECIMAL(20,4) DEFAULT 0 AFTER rem_m4,
     ADD COLUMN rem_m7  DECIMAL(20,4) DEFAULT 0 AFTER rem_m6,
     ADD COLUMN rem_m8  DECIMAL(20,4) DEFAULT 0 AFTER rem_m7,
     ADD COLUMN rem_m9  DECIMAL(20,4) DEFAULT 0 AFTER rem_m8,
     ADD COLUMN rem_m10 DECIMAL(20,4) DEFAULT 0 AFTER rem_m9,
     ADD COLUMN rem_m11 DECIMAL(20,4) DEFAULT 0 AFTER rem_m10,
     ADD COLUMN rem_m12 DECIMAL(20,4) DEFAULT 0 AFTER rem_m11',
  'SELECT 1 AS noop_add_reverse_rem_m'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- B3) 删除 m13-m60 死列
SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_reverse' AND COLUMN_NAME='orig_m13')>0,
  'ALTER TABLE prcp_data_reverse
     DROP COLUMN orig_m13, DROP COLUMN orig_m14, DROP COLUMN orig_m15, DROP COLUMN orig_m16, DROP COLUMN orig_m17,
     DROP COLUMN orig_m18, DROP COLUMN orig_m19, DROP COLUMN orig_m20, DROP COLUMN orig_m21, DROP COLUMN orig_m22,
     DROP COLUMN orig_m23, DROP COLUMN orig_m24, DROP COLUMN orig_m25, DROP COLUMN orig_m26, DROP COLUMN orig_m27,
     DROP COLUMN orig_m28, DROP COLUMN orig_m29, DROP COLUMN orig_m30, DROP COLUMN orig_m31, DROP COLUMN orig_m32,
     DROP COLUMN orig_m33, DROP COLUMN orig_m34, DROP COLUMN orig_m35, DROP COLUMN orig_m36, DROP COLUMN orig_m37,
     DROP COLUMN orig_m38, DROP COLUMN orig_m39, DROP COLUMN orig_m40, DROP COLUMN orig_m41, DROP COLUMN orig_m42,
     DROP COLUMN orig_m43, DROP COLUMN orig_m44, DROP COLUMN orig_m45, DROP COLUMN orig_m46, DROP COLUMN orig_m47,
     DROP COLUMN orig_m48, DROP COLUMN orig_m49, DROP COLUMN orig_m50, DROP COLUMN orig_m51, DROP COLUMN orig_m52,
     DROP COLUMN orig_m53, DROP COLUMN orig_m54, DROP COLUMN orig_m55, DROP COLUMN orig_m56, DROP COLUMN orig_m57,
     DROP COLUMN orig_m58, DROP COLUMN orig_m59, DROP COLUMN orig_m60',
  'SELECT 1 AS noop_drop_reverse_orig_m13_60'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql := IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_reverse' AND COLUMN_NAME='rem_m13')>0,
  'ALTER TABLE prcp_data_reverse
     DROP COLUMN rem_m13, DROP COLUMN rem_m14, DROP COLUMN rem_m15, DROP COLUMN rem_m16, DROP COLUMN rem_m17,
     DROP COLUMN rem_m18, DROP COLUMN rem_m19, DROP COLUMN rem_m20, DROP COLUMN rem_m21, DROP COLUMN rem_m22,
     DROP COLUMN rem_m23, DROP COLUMN rem_m24, DROP COLUMN rem_m25, DROP COLUMN rem_m26, DROP COLUMN rem_m27,
     DROP COLUMN rem_m28, DROP COLUMN rem_m29, DROP COLUMN rem_m30, DROP COLUMN rem_m31, DROP COLUMN rem_m32,
     DROP COLUMN rem_m33, DROP COLUMN rem_m34, DROP COLUMN rem_m35, DROP COLUMN rem_m36, DROP COLUMN rem_m37,
     DROP COLUMN rem_m38, DROP COLUMN rem_m39, DROP COLUMN rem_m40, DROP COLUMN rem_m41, DROP COLUMN rem_m42,
     DROP COLUMN rem_m43, DROP COLUMN rem_m44, DROP COLUMN rem_m45, DROP COLUMN rem_m46, DROP COLUMN rem_m47,
     DROP COLUMN rem_m48, DROP COLUMN rem_m49, DROP COLUMN rem_m50, DROP COLUMN rem_m51, DROP COLUMN rem_m52,
     DROP COLUMN rem_m53, DROP COLUMN rem_m54, DROP COLUMN rem_m55, DROP COLUMN rem_m56, DROP COLUMN rem_m57,
     DROP COLUMN rem_m58, DROP COLUMN rem_m59, DROP COLUMN rem_m60',
  'SELECT 1 AS noop_drop_reverse_rem_m13_60'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- B4) 验证 prcp_data_reverse 列
SELECT 'reverse_columns_after' AS info, COLUMN_NAME, ORDINAL_POSITION
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA=@db AND TABLE_NAME='prcp_data_reverse'
  AND (COLUMN_NAME LIKE 'orig\_%' OR COLUMN_NAME LIKE 'rem\_%')
ORDER BY ORDINAL_POSITION;