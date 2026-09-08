"""改唯一键 + 检查状态"""
from sqlalchemy import text
from app.database import engine

with engine.begin() as conn:
    # 软删残留
    n = conn.execute(text("UPDATE prcp_rpt_item SET is_deleted=1 WHERE 1")).rowcount
    print(f"软删 prcp_rpt_item: {n} 条")

    try:
        conn.execute(text("ALTER TABLE prcp_rpt_item DROP INDEX uk_report_code"))
        print("✅ DROP old unique key")
    except Exception as e:
        print(f"DROP error: {e}")
    try:
        conn.execute(text("ALTER TABLE prcp_rpt_item ADD UNIQUE KEY uk_report_code_name (report_id, code, name)"))
        print("✅ ADD new unique key (report_id, code, name)")
    except Exception as e:
        print(f"ADD error: {e}")

    # 检查现状
    r = conn.execute(text("SELECT id, report_code, report_name FROM prcp_rpt_report WHERE is_deleted=0")).fetchall()
    print("\nprcp_rpt_report:")
    for x in r:
        print(f"  id={x[0]} {x[1]} {x[2]}")
    r = conn.execute(text("SELECT category, COUNT(*) FROM prcp_metric_item WHERE is_deleted=0 GROUP BY category")).fetchall()
    print("\nprcp_metric_item:")
    for x in r:
        print(f"  {x[0]}: {x[1]}")
