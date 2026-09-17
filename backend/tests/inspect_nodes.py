"""Inspect ZXCOA nodes"""
import os
os.environ["MYSQL_USER"] = "almd"
os.environ["MYSQL_PASSWORD"] = "Almd@2026"
os.environ["MYSQL_DB"] = "prcp_db"
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
rows = db.execute(text("""SELECT id, node_code, node_name, node_level, path, sort_order
                        FROM prcp_coa_node
                        WHERE scheme_id=6 AND is_deleted=0
                        ORDER BY sort_order LIMIT 50""")).fetchall()
for r in rows:
    print(f"id={r[0]:3} L{r[3] or 1}  {r[1]:8s}  {r[2]:30s}  path={r[4]:50s}  sort={r[5]}")
print(f"\n共 {len(rows)} 行")
db.close()