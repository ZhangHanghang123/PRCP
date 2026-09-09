"""PRCP 数据库初始化 — 创建 prcp_db 库 + 所有业务表 + 默认 admin"""
import hashlib
import sys
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymysql
from sqlalchemy import create_engine, text

from app.config import settings

# 1) 创建数据库（无库时）
host = settings.MYSQL_HOST
port = int(settings.MYSQL_PORT)
user = settings.MYSQL_USER
pwd = settings.MYSQL_PASSWORD
db = settings.MYSQL_DB

print(f"→ 连接 MySQL {user}@{host}:{port}")
conn = pymysql.connect(host=host, port=port, user=user, password=pwd, charset="utf8mb4")
with conn.cursor() as c:
    c.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci")
    print(f"✅ 数据库 `{db}` 已就绪")
conn.close()

# 2) 创建表（业务表 + sys_user）
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

DDLS = [
    # 用户表
    """
    CREATE TABLE IF NOT EXISTS sys_user (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      username VARCHAR(64) NOT NULL UNIQUE,
      password_hash VARCHAR(128) NOT NULL,
      display_name VARCHAR(128),
      role VARCHAR(32) DEFAULT 'user',
      status TINYINT(1) DEFAULT 1,
      is_deleted TINYINT(1) DEFAULT 0,
      created_by BIGINT,
      updated_by BIGINT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_username (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # 资金组
    """
    CREATE TABLE IF NOT EXISTS prcp_group (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      group_code VARCHAR(64) NOT NULL,
      group_name VARCHAR(128) NOT NULL,
      group_type VARCHAR(32),
      currency VARCHAR(16) DEFAULT 'CNY',
      total_limit DECIMAL(18,2) DEFAULT 0,
      used_limit DECIMAL(18,2) DEFAULT 0,
      status VARCHAR(16) DEFAULT 'ACTIVE',
      description TEXT,
      is_deleted TINYINT(1) DEFAULT 0,
      created_by BIGINT, updated_by BIGINT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_code (group_code),
      INDEX idx_type (group_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # 头寸
    """
    CREATE TABLE IF NOT EXISTS prcp_position (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      position_code VARCHAR(64) NOT NULL,
      group_id BIGINT,
      account_code VARCHAR(64),
      currency VARCHAR(16) DEFAULT 'CNY',
      direction VARCHAR(8) DEFAULT 'IN',
      amount DECIMAL(18,2) DEFAULT 0,
      rate DECIMAL(10,6) DEFAULT 0,
      status VARCHAR(16) DEFAULT 'PENDING',
      trade_date DATE,
      settle_date DATE,
      counterparty VARCHAR(128),
      description TEXT,
      is_deleted TINYINT(1) DEFAULT 0,
      created_by BIGINT, updated_by BIGINT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_code (position_code),
      INDEX idx_group (group_id),
      INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # 组算规则
    """
    CREATE TABLE IF NOT EXISTS prcp_rule (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      rule_code VARCHAR(64) NOT NULL,
      rule_name VARCHAR(128) NOT NULL,
      rule_type VARCHAR(32),
      priority INT DEFAULT 0,
      source_group VARCHAR(64),
      target_group VARCHAR(64),
      currency VARCHAR(16),
      threshold DECIMAL(18,2) DEFAULT 0,
      action VARCHAR(32),
      status VARCHAR(16) DEFAULT 'ACTIVE',
      description TEXT,
      is_deleted TINYINT(1) DEFAULT 0,
      created_by BIGINT, updated_by BIGINT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_code (rule_code),
      INDEX idx_type (rule_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # 组算任务
    """
    CREATE TABLE IF NOT EXISTS prcp_task (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      task_code VARCHAR(64) NOT NULL,
      task_name VARCHAR(128) NOT NULL,
      schedule_date DATE,
      total_amount DECIMAL(18,2) DEFAULT 0,
      matched_amount DECIMAL(18,2) DEFAULT 0,
      matched_count INT DEFAULT 0,
      gap_amount DECIMAL(18,2) DEFAULT 0,
      status VARCHAR(16) DEFAULT 'PENDING',
      description TEXT,
      started_at DATETIME,
      finished_at DATETIME,
      is_deleted TINYINT(1) DEFAULT 0,
      created_by BIGINT, updated_by BIGINT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_code (task_code),
      INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # 任务流水
    """
    CREATE TABLE IF NOT EXISTS prcp_task_log (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      task_id BIGINT NOT NULL,
      log_type VARCHAR(32),
      summary_json LONGTEXT,
      created_by BIGINT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_task (task_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # 注：prcp_metric_item 表已废弃（193 条数据已迁移到 prcp_rpt_item 的 6 个 category）
    """
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
      INDEX idx_code (scheme_code),
      INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户册方案'
    """,
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户册节点（树形）'
    """,
    # ===== 报表表项管理 =====
    """
    CREATE TABLE IF NOT EXISTS prcp_rpt_report (
      id              BIGINT AUTO_INCREMENT PRIMARY KEY,
      report_code     VARCHAR(32) NOT NULL UNIQUE,
      report_name     VARCHAR(64) NOT NULL,
      report_type     VARCHAR(16) NOT NULL,
      scheme_id       BIGINT NOT NULL,
      description     TEXT,
      item_count      INT DEFAULT 0,
      status          VARCHAR(16) DEFAULT 'ACTIVE',
      is_deleted      TINYINT(1) DEFAULT 0,
      created_by      BIGINT,
      updated_by      BIGINT,
      created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_type (report_type),
      INDEX idx_scheme (scheme_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报表定义（6 类）'
    """,
    """
    CREATE TABLE IF NOT EXISTS prcp_rpt_item (
      id              BIGINT AUTO_INCREMENT PRIMARY KEY,
      report_id       BIGINT NOT NULL,
      item_code       VARCHAR(32) NOT NULL,
      item_name       VARCHAR(64) NOT NULL,
      parent_id       BIGINT,
      item_level      INT DEFAULT 1,
      data_type       VARCHAR(16) DEFAULT 'DECIMAL',
      formula         TEXT,
      coa_node_ids    JSON,
      path            VARCHAR(255),
      sort_order      INT DEFAULT 0,
      status          VARCHAR(16) DEFAULT 'ACTIVE',
      description     TEXT,
      is_deleted      TINYINT(1) DEFAULT 0,
      created_by      BIGINT,
      updated_by      BIGINT,
      created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_report_code (report_id, item_code),
      INDEX idx_parent (parent_id),
      INDEX idx_report (report_id),
      INDEX idx_path (path)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报表表项（树形）'
    """,
    # ===== 资产负债表 =====
    """
    CREATE TABLE IF NOT EXISTS prcp_data_balance (
      id              BIGINT AUTO_INCREMENT PRIMARY KEY,
      coa_node_id     BIGINT NOT NULL,
      data_date       DATE NOT NULL,
      current_amount  DECIMAL(20,4) DEFAULT 0,
      m1_gap          DECIMAL(20,4) DEFAULT 0,
      m2_gap          DECIMAL(20,4) DEFAULT 0,
      m3_gap          DECIMAL(20,4) DEFAULT 0,
      m4_gap          DECIMAL(20,4) DEFAULT 0,
      m5_gap          DECIMAL(20,4) DEFAULT 0,
      m6_gap          DECIMAL(20,4) DEFAULT 0,
      m7_gap          DECIMAL(20,4) DEFAULT 0,
      m8_gap          DECIMAL(20,4) DEFAULT 0,
      m9_gap          DECIMAL(20,4) DEFAULT 0,
      m10_gap         DECIMAL(20,4) DEFAULT 0,
      m11_gap         DECIMAL(20,4) DEFAULT 0,
      m12_gap         DECIMAL(20,4) DEFAULT 0,
      m13_gap         DECIMAL(20,4) DEFAULT 0,
      m14_gap         DECIMAL(20,4) DEFAULT 0,
      m15_gap         DECIMAL(20,4) DEFAULT 0,
      m16_gap         DECIMAL(20,4) DEFAULT 0,
      m17_gap         DECIMAL(20,4) DEFAULT 0,
      m18_gap         DECIMAL(20,4) DEFAULT 0,
      m19_gap         DECIMAL(20,4) DEFAULT 0,
      m20_gap         DECIMAL(20,4) DEFAULT 0,
      m21_gap         DECIMAL(20,4) DEFAULT 0,
      m22_gap         DECIMAL(20,4) DEFAULT 0,
      m23_gap         DECIMAL(20,4) DEFAULT 0,
      m24_gap         DECIMAL(20,4) DEFAULT 0,
      calc_note       TEXT,
      is_deleted      TINYINT(1) DEFAULT 0,
      created_by      BIGINT,
      updated_by      BIGINT,
      created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_node_date (coa_node_id, data_date),
      INDEX idx_date (data_date),
      INDEX idx_node (coa_node_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资产负债表（24 月缺口）'
    """,
    # ===== 指标管理 =====
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标方案'
    """,
    """
    CREATE TABLE IF NOT EXISTS prcp_kpi_definition (
      id              BIGINT AUTO_INCREMENT PRIMARY KEY,
      scheme_id       BIGINT NOT NULL,
      kpi_code        VARCHAR(32) NOT NULL,
      kpi_name        VARCHAR(64) NOT NULL,
      rpt_id          BIGINT NOT NULL,
      formula         TEXT NOT NULL,
      calc_unit       VARCHAR(16) DEFAULT 'PERCENT',
      formula_desc    TEXT,
      threshold_min   DECIMAL(20,6),
      threshold_max   DECIMAL(20,6),
      status          VARCHAR(16) DEFAULT 'ACTIVE',
      is_deleted      TINYINT(1) DEFAULT 0,
      created_by      BIGINT,
      updated_by      BIGINT,
      created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_scheme_code (scheme_id, kpi_code),
      INDEX idx_rpt (rpt_id),
      INDEX idx_scheme (scheme_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标定义（含公式，引用报表表项）'
    """,
    """
    CREATE TABLE IF NOT EXISTS prcp_kpi_value (
      id              BIGINT AUTO_INCREMENT PRIMARY KEY,
      kpi_id          BIGINT NOT NULL,
      data_date       DATE NOT NULL,
      version         VARCHAR(32) NOT NULL DEFAULT 'V1.0',
      current_value   DECIMAL(20,6),
      prev_value      DECIMAL(20,6),
      prev_year_value DECIMAL(20,6),
      calc_source     VARCHAR(16) DEFAULT 'MANUAL',
      calc_log        LONGTEXT,
      score           DECIMAL(8,2) DEFAULT NULL COMMENT '试算分数',
      is_deleted      TINYINT(1) DEFAULT 0,
      created_by      BIGINT,
      updated_by      BIGINT,
      created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_kpi_date_ver (kpi_id, data_date, version),
      INDEX idx_date (data_date),
      INDEX idx_version (version)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标值（按日期+版本）'
    """,
    """
    CREATE TABLE IF NOT EXISTS prcp_kpi_score_rule (
      id              BIGINT AUTO_INCREMENT PRIMARY KEY,
      scheme_id       BIGINT NOT NULL,
      kpi_id          BIGINT NOT NULL,
      rule_name       VARCHAR(128) NOT NULL,
      calc_method     VARCHAR(16) DEFAULT 'PIECEWISE',
      total_score     DECIMAL(8,2) DEFAULT 100.00,
      higher_is_better TINYINT(1) DEFAULT 1,
      description     TEXT,
      status          VARCHAR(16) DEFAULT 'ACTIVE',
      is_deleted      TINYINT(1) DEFAULT 0,
      created_by      BIGINT,
      updated_by      BIGINT,
      created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_kpi_rule (kpi_id, rule_name, is_deleted),
      INDEX idx_scheme (scheme_id),
      INDEX idx_kpi (kpi_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标评分规则（一个指标可有多套规则）'
    """,
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评分规则的分段区间（min/max → score）'
    """,
]

with engine.begin() as conn:
    for ddl in DDLS:
        conn.execute(text(ddl))
print(f"✅ {len(DDLS)} 张表已就绪")

# 3) 默认 admin
pw_hash = hashlib.sha256(b"admin123").hexdigest()
with engine.begin() as conn:
    row = conn.execute(text("SELECT id FROM sys_user WHERE username='admin'")).first()
    if not row:
        conn.execute(text("""
            INSERT INTO sys_user (username, password_hash, display_name, role, status, created_by, updated_by)
            VALUES ('admin', :p, '系统管理员', 'admin', 1, 1, 1)
        """), {"p": pw_hash})
        print("✅ 默认 admin 账号已创建 (admin/admin123)")
    else:
        print(f"ℹ️ admin 账号已存在 id={row[0]}")

# 4) 演示数据：1 个资金组 + 3 条头寸 + 1 条规则
with engine.begin() as conn:
    if not conn.execute(text("SELECT id FROM prcp_group LIMIT 1")).first():
        conn.execute(text("""
            INSERT INTO prcp_group (group_code, group_name, group_type, currency,
              total_limit, used_limit, status, description, created_by, updated_by)
            VALUES ('GRP_DEMO_001', '人民币资金组', 'INTERNAL', 'CNY',
              100000000, 35000000, 'ACTIVE', '人民币内部资金调度组', 1, 1)
        """))
        print("✅ 演示资金组 GRP_DEMO_001 已创建")

    if not conn.execute(text("SELECT id FROM prcp_rule LIMIT 1")).first():
        conn.execute(text("""
            INSERT INTO prcp_rule (rule_code, rule_name, rule_type, priority,
              source_group, target_group, currency, threshold, action, status,
              description, created_by, updated_by)
            VALUES ('RULE_DEMO_001', '本币内部调拨', 'INTERNAL_TRANSFER', 100,
              'GRP_DEMO_001', 'GRP_DEMO_001', 'CNY', 1000000, 'AUTO_MATCH', 'ACTIVE',
              '人民币内部自动撮合规则（演示）', 1, 1)
        """))
        print("✅ 演示规则 RULE_DEMO_001 已创建")

print(f"🎉 PRCP 初始化完成 → http://127.0.0.1:8006/prcp/api/docs")