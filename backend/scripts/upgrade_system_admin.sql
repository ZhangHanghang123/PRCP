-- PRCP 系统管理 - 数据库升级（角色 + 字典）

CREATE TABLE IF NOT EXISTS sys_role (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  role_code       VARCHAR(32) NOT NULL UNIQUE,
  role_name       VARCHAR(64) NOT NULL,
  description     TEXT,
  status          TINYINT(1) DEFAULT 1,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统角色';

CREATE TABLE IF NOT EXISTS sys_user_role (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id         BIGINT NOT NULL,
  role_id         BIGINT NOT NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_role (user_id, role_id),
  INDEX idx_user (user_id),
  INDEX idx_role (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户-角色关联';

CREATE TABLE IF NOT EXISTS sys_dict (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  dict_code       VARCHAR(64) NOT NULL UNIQUE,
  dict_name       VARCHAR(128) NOT NULL,
  description     TEXT,
  status          TINYINT(1) DEFAULT 1,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='字典分类';

CREATE TABLE IF NOT EXISTS sys_dict_item (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  dict_id         BIGINT NOT NULL,
  item_code       VARCHAR(64) NOT NULL,
  item_name       VARCHAR(128) NOT NULL,
  item_value      VARCHAR(255),
  sort_order      INT DEFAULT 0,
  status          TINYINT(1) DEFAULT 1,
  is_deleted      TINYINT(1) DEFAULT 0,
  created_by      BIGINT,
  updated_by      BIGINT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_dict_item (dict_id, item_code, is_deleted),
  INDEX idx_dict (dict_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='字典项';