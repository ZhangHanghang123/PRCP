"""执行 KPI schema 升级"""
from sqlalchemy import text
from app.database import engine

with engine.begin() as conn:
    # 1. 创建 prcp_kpi_scheme
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS prcp_kpi_scheme (
          id BIGINT AUTO_INCREMENT PRIMARY KEY,
          scheme_code VARCHAR(32) NOT NULL UNIQUE,
          scheme_name VARCHAR(64) NOT NULL,
          description TEXT,
          kpi_count INT DEFAULT 0,
          status VARCHAR(16) DEFAULT 'ACTIVE',
          is_deleted TINYINT(1) DEFAULT 0,
          created_by BIGINT,
          updated_by BIGINT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标方案'
    """))
    print("✅ prcp_kpi_scheme 表已就绪")

    # 2. prcp_kpi_definition 加 scheme_id
    cols = conn.execute(text("SHOW COLUMNS FROM prcp_kpi_definition")).fetchall()
    col_names = [c[0] for c in cols]
    if 'scheme_id' not in col_names:
        conn.execute(text("ALTER TABLE prcp_kpi_definition ADD COLUMN scheme_id BIGINT NULL AFTER id"))
        conn.execute(text("ALTER TABLE prcp_kpi_definition ADD INDEX idx_scheme (scheme_id)"))
        print("✅ prcp_kpi_definition 加 scheme_id 字段")
    else:
        print("  scheme_id 字段已存在")

    # 3. 改唯一键 (kpi_code) → (scheme_id, kpi_code)
    indexes = conn.execute(text("SHOW INDEX FROM prcp_kpi_definition")).fetchall()
    idx_names = set(r[2] for r in indexes)
    if 'kpi_code' in idx_names:
        conn.execute(text("ALTER TABLE prcp_kpi_definition DROP INDEX kpi_code"))
        print("✅ DROP old unique key kpi_code")
    if 'uk_scheme_code' not in idx_names:
        conn.execute(text("ALTER TABLE prcp_kpi_definition ADD UNIQUE KEY uk_scheme_code (scheme_id, kpi_code)"))
        print("✅ ADD unique key (scheme_id, kpi_code)")
    else:
        print("  unique key uk_scheme_code 已存在")

    # 4. 创建默认方案
    row = conn.execute(text("SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_DEFAULT'")).first()
    if not row:
        conn.execute(text("""INSERT INTO prcp_kpi_scheme
            (scheme_code, scheme_name, description, status, created_by, updated_by)
            VALUES ('SCH_DEFAULT', '默认指标方案', '系统默认指标方案，可基于此扩展', 'ACTIVE', 1, 1)"""))
        print("✅ 创建默认方案 SCH_DEFAULT")
    else:
        print(f"  SCH_DEFAULT 已存在 id={row[0]}")

    # 5. 迁移现有 definition 到默认方案
    n = conn.execute(text("UPDATE prcp_kpi_definition SET scheme_id=(SELECT id FROM prcp_kpi_scheme WHERE scheme_code='SCH_DEFAULT' AND is_deleted=0 LIMIT 1) WHERE scheme_id IS NULL OR scheme_id=0")).rowcount
    print(f"✅ 迁移 {n} 条 definition 到默认方案")

    # 6. 验证
    r1 = conn.execute(text("SELECT COUNT(*) FROM prcp_kpi_scheme WHERE is_deleted=0")).first()
    r2 = conn.execute(text("SELECT COUNT(*) FROM prcp_kpi_definition WHERE is_deleted=0")).first()
    r3 = conn.execute(text("SELECT COUNT(*) FROM prcp_kpi_definition WHERE scheme_id IS NULL OR scheme_id=0")).first()
    print(f"\n现状：")
    print(f"  方案数：{r1[0]}")
    print(f"  指标定义数：{r2[0]}")
    print(f"  孤儿定义数（无方案）：{r3[0]}")
