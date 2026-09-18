"""Verify new bucket structure."""
import pymysql
conn = pymysql.connect(host="43.143.253.186", port=3306, user="almd",
                       password="Almd@2026", database="prcp_db")
cur = conn.cursor()

cur.execute("SHOW COLUMNS FROM prcp_data_basic LIKE 'orig_%'")
cols = [r[0] for r in cur.fetchall()]
print(f"orig_* columns: {len(cols)}")
print(f"  {cols[:5]}")
print(f"  ...")
print(f"  {cols[-5:]}")

cur.execute("SHOW COLUMNS FROM prcp_data_basic LIKE 'rem_%'")
cols = [r[0] for r in cur.fetchall()]
print(f"\nrem_* columns: {len(cols)}")
print(f"  {cols[:5]}")
print(f"  ...")
print(f"  {cols[-5:]}")

cur.execute("SELECT COUNT(*) FROM prcp_data_basic")
print(f"\nprcp_data_basic rows: {cur.fetchone()[0]}")

conn.close()