-- PRCP 基础数据表 v4 拆分（2026-09-20）
-- 改造原因：原 prcp_data_basic 单表 11+128+7+1+4=151 字段过宽（orig_m1~orig_m60/orig_y10~orig_y30 + rem_m1~rem_m60/rem_y10~rem_y30 + 度量），
-- 不便于维护和扩展。v4 拆为 3 表：
--   1) prcp_data_basic（主表）：11 维度 + asf_rsf/hqla_factor + 5 度量 + calc_note + 4 审计 = 23 字段
--   2) prcp_data_basic_orig（原始期限）：4 元组 + 64 orig_* + 4 审计 = 72 字段
--   3) prcp_data_basic_rem（剩余期限）：4 元组 + 64 rem_* + 4 审计 = 72 字段
-- 三表通过 (coa_node_id, data_date, date_offset, offset_unit) 四元组关联。

-- 步骤 1：创建 prcp_data_basic_orig（原始期限）
CREATE TABLE IF NOT EXISTS prcp_data_basic_orig (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  coa_node_id     BIGINT NOT NULL,
  data_date       DATE NOT NULL,
  date_offset     INT DEFAULT 0,
  offset_unit     VARCHAR(2) DEFAULT 'D',
  orig_m1         DECIMAL(20,4) DEFAULT 0,
  orig_m2         DECIMAL(20,4) DEFAULT 0,
  orig_m3         DECIMAL(20,4) DEFAULT 0,
  orig_m4         DECIMAL(20,4) DEFAULT 0,
  orig_m5         DECIMAL(20,4) DEFAULT 0,
  orig_m6         DECIMAL(20,4) DEFAULT 0,
  orig_m7         DECIMAL(20,4) DEFAULT 0,
  orig_m8         DECIMAL(20,4) DEFAULT 0,
  orig_m9         DECIMAL(20,4) DEFAULT 0,
  orig_m10        DECIMAL(20,4) DEFAULT 0,
  orig_m11        DECIMAL(20,4) DEFAULT 0,
  orig_m12        DECIMAL(20,4) DEFAULT 0,
  orig_m13        DECIMAL(20,4) DEFAULT 0,
  orig_m14        DECIMAL(20,4) DEFAULT 0,
  orig_m15        DECIMAL(20,4) DEFAULT 0,
  orig_m16        DECIMAL(20,4) DEFAULT 0,
  orig_m17        DECIMAL(20,4) DEFAULT 0,
  orig_m18        DECIMAL(20,4) DEFAULT 0,
  orig_m19        DECIMAL(20,4) DEFAULT 0,
  orig_m20        DECIMAL(20,4) DEFAULT 0,
  orig_m21        DECIMAL(20,4) DEFAULT 0,
  orig_m22        DECIMAL(20,4) DEFAULT 0,
  orig_m23        DECIMAL(20,4) DEFAULT 0,
  orig_m24        DECIMAL(20,4) DEFAULT 0,
  orig_m25        DECIMAL(20,4) DEFAULT 0,
  orig_m26        DECIMAL(20,4) DEFAULT 0,
  orig_m27        DECIMAL(20,4) DEFAULT 0,
  orig_m28        DECIMAL(20,4) DEFAULT 0,
  orig_m29        DECIMAL(20,4) DEFAULT 0,
  orig_m30        DECIMAL(20,4) DEFAULT 0,
  orig_m31        DECIMAL(20,4) DEFAULT 0,
  orig_m32        DECIMAL(20,4) DEFAULT 0,
  orig_m33        DECIMAL(20,4) DEFAULT 0,
  orig_m34        DECIMAL(20,4) DEFAULT 0,
  orig_m35        DECIMAL(20,4) DEFAULT 0,
  orig_m36        DECIMAL(20,4) DEFAULT 0,
  orig_m37        DECIMAL(20,4) DEFAULT 0,
  orig_m38        DECIMAL(20,4) DEFAULT 0,
  orig_m39        DECIMAL(20,4) DEFAULT 0,
  orig_m40        DECIMAL(20,4) DEFAULT 0,
  orig_m41        DECIMAL(20,4) DEFAULT 0,
  orig_m42        DECIMAL(20,4) DEFAULT 0,
  orig_m43        DECIMAL(20,4) DEFAULT 0,
  orig_m44        DECIMAL(20,4) DEFAULT 0,
  orig_m45        DECIMAL(20,4) DEFAULT 0,
  orig_m46        DECIMAL(20,4) DEFAULT 0,
  orig_m47        DECIMAL(20,4) DEFAULT 0,
  orig_m48        DECIMAL(20,4) DEFAULT 0,
  orig_m49        DECIMAL(20,4) DEFAULT 0,
  orig_m50        DECIMAL(20,4) DEFAULT 0,
  orig_m51        DECIMAL(20,4) DEFAULT 0,
  orig_m52        DECIMAL(20,4) DEFAULT 0,
  orig_m53        DECIMAL(20,4) DEFAULT 0,
  orig_m54        DECIMAL(20,4) DEFAULT 0,
  orig_m55        DECIMAL(20,4) DEFAULT 0,
  orig_m56        DECIMAL(20,4) DEFAULT 0,
  orig_m57        DECIMAL(20,4) DEFAULT 0,
  orig_m58        DECIMAL(20,4) DEFAULT 0,
  orig_m59        DECIMAL(20,4) DEFAULT 0,
  orig_m60        DECIMAL(20,4) DEFAULT 0,
  orig_y10        DECIMAL(20,4) DEFAULT 0,
  orig_y15        DECIMAL(20,4) DEFAULT 0,
  orig_y20        DECIMAL(20,4) DEFAULT 0,
  orig_y30        DECIMAL(20,4) DEFAULT 0,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_node_date_offset (coa_node_id, data_date, date_offset, offset_unit),
  INDEX idx_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基础数据表 — 原始期限 64 桶（5年按月m1~m60 + 长端y10/y15/y20/y30）';

-- 步骤 2：创建 prcp_data_basic_rem（剩余期限）
CREATE TABLE IF NOT EXISTS prcp_data_basic_rem (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  coa_node_id     BIGINT NOT NULL,
  data_date       DATE NOT NULL,
  date_offset     INT DEFAULT 0,
  offset_unit     VARCHAR(2) DEFAULT 'D',
  rem_m1          DECIMAL(20,4) DEFAULT 0,
  rem_m2          DECIMAL(20,4) DEFAULT 0,
  rem_m3          DECIMAL(20,4) DEFAULT 0,
  rem_m4          DECIMAL(20,4) DEFAULT 0,
  rem_m5          DECIMAL(20,4) DEFAULT 0,
  rem_m6          DECIMAL(20,4) DEFAULT 0,
  rem_m7          DECIMAL(20,4) DEFAULT 0,
  rem_m8          DECIMAL(20,4) DEFAULT 0,
  rem_m9          DECIMAL(20,4) DEFAULT 0,
  rem_m10         DECIMAL(20,4) DEFAULT 0,
  rem_m11         DECIMAL(20,4) DEFAULT 0,
  rem_m12         DECIMAL(20,4) DEFAULT 0,
  rem_m13         DECIMAL(20,4) DEFAULT 0,
  rem_m14         DECIMAL(20,4) DEFAULT 0,
  rem_m15         DECIMAL(20,4) DEFAULT 0,
  rem_m16         DECIMAL(20,4) DEFAULT 0,
  rem_m17         DECIMAL(20,4) DEFAULT 0,
  rem_m18         DECIMAL(20,4) DEFAULT 0,
  rem_m19         DECIMAL(20,4) DEFAULT 0,
  rem_m20         DECIMAL(20,4) DEFAULT 0,
  rem_m21         DECIMAL(20,4) DEFAULT 0,
  rem_m22         DECIMAL(20,4) DEFAULT 0,
  rem_m23         DECIMAL(20,4) DEFAULT 0,
  rem_m24         DECIMAL(20,4) DEFAULT 0,
  rem_m25         DECIMAL(20,4) DEFAULT 0,
  rem_m26         DECIMAL(20,4) DEFAULT 0,
  rem_m27         DECIMAL(20,4) DEFAULT 0,
  rem_m28         DECIMAL(20,4) DEFAULT 0,
  rem_m29         DECIMAL(20,4) DEFAULT 0,
  rem_m30         DECIMAL(20,4) DEFAULT 0,
  rem_m31         DECIMAL(20,4) DEFAULT 0,
  rem_m32         DECIMAL(20,4) DEFAULT 0,
  rem_m33         DECIMAL(20,4) DEFAULT 0,
  rem_m34         DECIMAL(20,4) DEFAULT 0,
  rem_m35         DECIMAL(20,4) DEFAULT 0,
  rem_m36         DECIMAL(20,4) DEFAULT 0,
  rem_m37         DECIMAL(20,4) DEFAULT 0,
  rem_m38         DECIMAL(20,4) DEFAULT 0,
  rem_m39         DECIMAL(20,4) DEFAULT 0,
  rem_m40         DECIMAL(20,4) DEFAULT 0,
  rem_m41         DECIMAL(20,4) DEFAULT 0,
  rem_m42         DECIMAL(20,4) DEFAULT 0,
  rem_m43         DECIMAL(20,4) DEFAULT 0,
  rem_m44         DECIMAL(20,4) DEFAULT 0,
  rem_m45         DECIMAL(20,4) DEFAULT 0,
  rem_m46         DECIMAL(20,4) DEFAULT 0,
  rem_m47         DECIMAL(20,4) DEFAULT 0,
  rem_m48         DECIMAL(20,4) DEFAULT 0,
  rem_m49         DECIMAL(20,4) DEFAULT 0,
  rem_m50         DECIMAL(20,4) DEFAULT 0,
  rem_m51         DECIMAL(20,4) DEFAULT 0,
  rem_m52         DECIMAL(20,4) DEFAULT 0,
  rem_m53         DECIMAL(20,4) DEFAULT 0,
  rem_m54         DECIMAL(20,4) DEFAULT 0,
  rem_m55         DECIMAL(20,4) DEFAULT 0,
  rem_m56         DECIMAL(20,4) DEFAULT 0,
  rem_m57         DECIMAL(20,4) DEFAULT 0,
  rem_m58         DECIMAL(20,4) DEFAULT 0,
  rem_m59         DECIMAL(20,4) DEFAULT 0,
  rem_m60         DECIMAL(20,4) DEFAULT 0,
  rem_y10         DECIMAL(20,4) DEFAULT 0,
  rem_y15         DECIMAL(20,4) DEFAULT 0,
  rem_y20         DECIMAL(20,4) DEFAULT 0,
  rem_y30         DECIMAL(20,4) DEFAULT 0,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_node_date_offset (coa_node_id, data_date, date_offset, offset_unit),
  INDEX idx_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基础数据表 — 剩余期限 64 桶（5年按月m1~m60 + 长端y10/y15/y20/y30）';

-- 步骤 3：迁移现有数据（如果 prcp_data_basic 存在 orig_*/rem_* 字段）
-- 注：仅当 prcp_data_basic 还有 128 期限字段时执行迁移
INSERT INTO prcp_data_basic_orig
  (coa_node_id, data_date, date_offset, offset_unit,
   orig_m1, orig_m2, orig_m3, orig_m4, orig_m5, orig_m6, orig_m7, orig_m8, orig_m9, orig_m10, orig_m11, orig_m12,
   orig_m13, orig_m14, orig_m15, orig_m16, orig_m17, orig_m18, orig_m19, orig_m20, orig_m21, orig_m22, orig_m23, orig_m24,
   orig_m25, orig_m26, orig_m27, orig_m28, orig_m29, orig_m30, orig_m31, orig_m32, orig_m33, orig_m34, orig_m35, orig_m36,
   orig_m37, orig_m38, orig_m39, orig_m40, orig_m41, orig_m42, orig_m43, orig_m44, orig_m45, orig_m46, orig_m47, orig_m48,
   orig_m49, orig_m50, orig_m51, orig_m52, orig_m53, orig_m54, orig_m55, orig_m56, orig_m57, orig_m58, orig_m59, orig_m60,
   orig_y10, orig_y15, orig_y20, orig_y30,
   is_deleted, created_by, updated_by, created_at, updated_at)
SELECT coa_node_id, data_date, date_offset, offset_unit,
       orig_m1, orig_m2, orig_m3, orig_m4, orig_m5, orig_m6, orig_m7, orig_m8, orig_m9, orig_m10, orig_m11, orig_m12,
       orig_m13, orig_m14, orig_m15, orig_m16, orig_m17, orig_m18, orig_m19, orig_m20, orig_m21, orig_m22, orig_m23, orig_m24,
       orig_m25, orig_m26, orig_m27, orig_m28, orig_m29, orig_m30, orig_m31, orig_m32, orig_m33, orig_m34, orig_m35, orig_m36,
       orig_m37, orig_m38, orig_m39, orig_m40, orig_m41, orig_m42, orig_m43, orig_m44, orig_m45, orig_m46, orig_m47, orig_m48,
       orig_m49, orig_m50, orig_m51, orig_m52, orig_m53, orig_m54, orig_m55, orig_m56, orig_m57, orig_m58, orig_m59, orig_m60,
       orig_y10, orig_y15, orig_y20, orig_y30,
       is_deleted, created_by, updated_by, created_at, updated_at
FROM prcp_data_basic
WHERE NOT EXISTS (
  SELECT 1 FROM prcp_data_basic_orig o
  WHERE o.coa_node_id = prcp_data_basic.coa_node_id
    AND o.data_date = prcp_data_basic.data_date
    AND o.date_offset = prcp_data_basic.date_offset
    AND o.offset_unit = prcp_data_basic.offset_unit
)
ON DUPLICATE KEY UPDATE
  orig_m1 = VALUES(orig_m1), orig_m60 = VALUES(orig_m60), orig_y30 = VALUES(orig_y30),
  updated_at = CURRENT_TIMESTAMP;

INSERT INTO prcp_data_basic_rem
  (coa_node_id, data_date, date_offset, offset_unit,
   rem_m1, rem_m2, rem_m3, rem_m4, rem_m5, rem_m6, rem_m7, rem_m8, rem_m9, rem_m10, rem_m11, rem_m12,
   rem_m13, rem_m14, rem_m15, rem_m16, rem_m17, rem_m18, rem_m19, rem_m20, rem_m21, rem_m22, rem_m23, rem_m24,
   rem_m25, rem_m26, rem_m27, rem_m28, rem_m29, rem_m30, rem_m31, rem_m32, rem_m33, rem_m34, rem_m35, rem_m36,
   rem_m37, rem_m38, rem_m39, rem_m40, rem_m41, rem_m42, rem_m43, rem_m44, rem_m45, rem_m46, rem_m47, rem_m48,
   rem_m49, rem_m50, rem_m51, rem_m52, rem_m53, rem_m54, rem_m55, rem_m56, rem_m57, rem_m58, rem_m59, rem_m60,
   rem_y10, rem_y15, rem_y20, rem_y30,
   is_deleted, created_by, updated_by, created_at, updated_at)
SELECT coa_node_id, data_date, date_offset, offset_unit,
       rem_m1, rem_m2, rem_m3, rem_m4, rem_m5, rem_m6, rem_m7, rem_m8, rem_m9, rem_m10, rem_m11, rem_m12,
       rem_m13, rem_m14, rem_m15, rem_m16, rem_m17, rem_m18, rem_m19, rem_m20, rem_m21, rem_m22, rem_m23, rem_m24,
       rem_m25, rem_m26, rem_m27, rem_m28, rem_m29, rem_m30, rem_m31, rem_m32, rem_m33, rem_m34, rem_m35, rem_m36,
       rem_m37, rem_m38, rem_m39, rem_m40, rem_m41, rem_m42, rem_m43, rem_m44, rem_m45, rem_m46, rem_m47, rem_m48,
       rem_m49, rem_m50, rem_m51, rem_m52, rem_m53, rem_m54, rem_m55, rem_m56, rem_m57, rem_m58, rem_m59, rem_m60,
       rem_y10, rem_y15, rem_y20, rem_y30,
       is_deleted, created_by, updated_by, created_at, updated_at
FROM prcp_data_basic
WHERE NOT EXISTS (
  SELECT 1 FROM prcp_data_basic_rem r
  WHERE r.coa_node_id = prcp_data_basic.coa_node_id
    AND r.data_date = prcp_data_basic.data_date
    AND r.date_offset = prcp_data_basic.date_offset
    AND r.offset_unit = prcp_data_basic.offset_unit
)
ON DUPLICATE KEY UPDATE
  rem_m1 = VALUES(rem_m1), rem_m60 = VALUES(rem_m60), rem_y30 = VALUES(rem_y30),
  updated_at = CURRENT_TIMESTAMP;

-- 步骤 4：删除 prcp_data_basic 中 128 个 orig_*/rem_* 字段
ALTER TABLE prcp_data_basic
  DROP COLUMN orig_d1,  DROP COLUMN orig_d7,
  DROP COLUMN orig_m1,  DROP COLUMN orig_m3,  DROP COLUMN orig_m6,  DROP COLUMN orig_y1,  DROP COLUMN orig_y2,  DROP COLUMN orig_y3,  DROP COLUMN orig_y5,
  DROP COLUMN orig_y10, DROP COLUMN orig_y15, DROP COLUMN orig_y20, DROP COLUMN orig_y30,
  DROP COLUMN rem_d1,   DROP COLUMN rem_d7,
  DROP COLUMN rem_m1,   DROP COLUMN rem_m3,   DROP COLUMN rem_m6,   DROP COLUMN rem_y1,   DROP COLUMN rem_y2,   DROP COLUMN rem_y3,   DROP COLUMN rem_y5,
  DROP COLUMN rem_y10,  DROP COLUMN rem_y15,  DROP COLUMN rem_y20,  DROP COLUMN rem_y30;

-- 注：prcp_data_basic_orig / prcp_data_basic_rem 保留 m1~m60 字段（v3 规范）。
-- 后续如需扩展到更多桶（如 m61~m72），ALTER TABLE 增加字段即可，不需要影响主表。
