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
    # 指标项（6 类指标通用表：账务/参数/规模/价格/中收/RWA）
    """
    CREATE TABLE IF NOT EXISTS prcp_metric_item (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      category VARCHAR(20) NOT NULL COMMENT 'FINANCIAL/PARAM/SCALE/PRICE/FEE/RWA',
      code VARCHAR(50) NOT NULL COMMENT '原始指标编码（可能重复）',
      name VARCHAR(200) NOT NULL COMMENT '指标名称',
      level INT NOT NULL DEFAULT 1 COMMENT '层级 1-5',
      parent_code VARCHAR(50) COMMENT '父指标编码',
      path VARCHAR(500) COMMENT '物化路径 /001/001001/...',
      is_leaf TINYINT(1) DEFAULT 0 COMMENT '是否叶子节点',
      sort_order INT DEFAULT 0 COMMENT '同级排序',
      description TEXT,
      is_deleted TINYINT(1) DEFAULT 0,
      created_by BIGINT, updated_by BIGINT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_cat_code (category, code),
      INDEX idx_cat_parent (category, parent_code),
      INDEX idx_cat_level (category, level)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='6 类指标项定义'
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