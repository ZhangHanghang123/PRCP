"""Inspect prcp_data_basic and related tables."""
from sqlalchemy import text
from app.database import SessionLocal

db = SessionLocal()

print("=== prcp_data_basic ===")
for r in db.execute(text("DESCRIBE prcp_data_basic")).fetchall():
    print(f"  {r[0]:25s}  {r[1]:30s}  {r[2]}")

print("\n=== prcp_reverse_result ===")
for r in db.execute(text("DESCRIBE prcp_reverse_result")).fetchall():
    print(f"  {r[0]:25s}  {r[1]:30s}  {r[2]}")

print("\n=== prcp_data_basic sample (1 row) ===")
for r in db.execute(text("SELECT * FROM prcp_data_basic LIMIT 1")).fetchall():
    print(f"  columns: {list(r._mapping.keys())}")

print("\n=== prcp_data_basic total rows ===")
print(f"  {db.execute(text('SELECT COUNT(*) FROM prcp_data_basic')).scalar()}")

print("\n=== sample row (current_amount, current_balance etc) ===")
for r in db.execute(text("""SELECT data_date, coa_node_id, date_offset, offset_unit,
                          orig_d1, orig_d7, orig_d1m, current_balance, avg_balance,
                          weighted_rate, interest_amount, risk_weight
                          FROM prcp_data_basic LIMIT 3""")).fetchall():
    print(f"  {r}")

db.close()