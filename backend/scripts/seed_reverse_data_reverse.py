"""Populate prcp_data_reverse with 24 months of data for each scheme."""
import sys
sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text
import random
from datetime import date
from decimal import Decimal

DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
eng = create_engine(DB_URL)
random.seed(42)


def month_end(y, m):
    """Return last day of month y-m"""
    if m == 12:
        return date(y + 1, 1, 1)
    return date(y, m + 1, 1)


def add_months(d: date, n: int) -> date:
    y = d.year + (d.month + n - 1) // 12
    m = (d.month + n - 1) % 12 + 1
    return date(y, m, 1)


def main():
    with eng.begin() as conn:
        # Get active schemes
        schemes = conn.execute(text("""
            SELECT s.id, s.scheme_code, s.coa_scheme_id, s.data_date, s.horizon_months
            FROM prcp_reverse_scheme s WHERE s.is_deleted=0 ORDER BY s.id
        """)).fetchall()
        print(f"[schemes] {len(schemes)}")

        for s in schemes:
            sid, scode, coa_id, base_date, horizon = s
            # The scheme's latest run_id
            run = conn.execute(text(
                "SELECT id FROM prcp_reverse_run WHERE scheme_id=:s AND is_deleted=0 ORDER BY id DESC LIMIT 1"
            ), {"s": sid}).first()
            if not run:
                continue
            run_id = run[0]
            base = base_date if base_date else date(2025, 12, 31)

            # Get nodes
            nodes = conn.execute(text(
                "SELECT id, node_code, node_name, node_level FROM prcp_coa_node "
                "WHERE scheme_id=:s AND is_deleted=0 ORDER BY id"
            ), {"s": coa_id}).fetchall()
            print(f"  [scheme={scode}] run={run_id} base={base} horizon={horizon} nodes={len(nodes)}")

            # First, soft-delete existing data_reverse for this scheme
            conn.execute(text(
                "UPDATE prcp_data_reverse SET is_deleted=1 WHERE run_id=:r"
            ), {"r": run_id})

            # Now insert for each month offset 1..horizon
            inserted = 0
            for mo in range(1, horizon + 1):
                # Compute data_date for this month (end of month, or just 1st day)
                offset_date = add_months(base, mo - 1)
                # 取 base 当前的 balance 作为初始 base_m1
                for n in nodes:
                    nid, ncode, nname, nlevel = n
                    cur = conn.execute(text(
                        """SELECT orig_m1, orig_m12, orig_y10
                           FROM prcp_data_basic WHERE node_code=:nc AND data_date='2025-12-31' AND is_deleted=0 LIMIT 1"""
                    ), {"nc": ncode}).first()
                    base_m1 = float(cur[0]) if cur and cur[0] is not None else 0.0
                    base_m12 = float(cur[1]) if cur and cur[1] is not None else 0.0
                    base_y10 = float(cur[2]) if cur and cur[2] is not None else 0.0

                    # 随月份增长/衰减 + 随机扰动（每 scheme 不同）
                    growth = 1 + (mo / 240.0) * random.uniform(-0.05, 0.10)  # 缓慢增长
                    adj_m1 = round(base_m1 * growth, 4)
                    adj_m12 = round(base_m12 * growth, 4)
                    adj_y10 = round(base_y10 * growth, 4)
                    rate = round(random.uniform(0.02, 0.06), 6)
                    interest = round(adj_m1 * rate, 4)
                    rweight = round(random.uniform(0.0, 1.5), 6)

                    conn.execute(text(
                        """INSERT INTO prcp_data_reverse
                           (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
                            coa_node_id, node_code, node_name, node_level,
                            orig_m1, rem_m1, orig_m12, rem_m12, orig_y10, rem_y10,
                            current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
                            is_deleted, created_by, updated_by)
                           VALUES (:rid, :sc, :r, :coa, :dd, :mo, 'M',
                            :nid, :nc, :nn, :nl,
                            :om1, :rm1, :om12, :rm12, :oy10, :ry10,
                            :cb, :ab, :wr, :ia, :rw,
                            0, 1, 1)"""
                    ), {
                        "rid": f"{ncode}_M{scode}", "sc": scode, "r": run_id, "coa": coa_id,
                        "dd": offset_date, "mo": mo, "nid": nid, "nc": ncode, "nn": nname, "nl": nlevel,
                        "om1": adj_m1, "rm1": adj_m1 * 0.98, "om12": adj_m12, "rm12": adj_m12 * 0.98,
                        "oy10": adj_y10, "ry10": adj_y10 * 0.98,
                        "cb": adj_m1, "ab": adj_m1 * 1.005, "wr": rate,
                        "ia": interest, "rw": rweight,
                    })
                    inserted += 1
            print(f"    inserted: {inserted} rows (24 months × {len(nodes)} nodes)")

        # 验证
        print()
        print("=== Verification ===")
        for tbl in ['prcp_reverse_scheme', 'prcp_reverse_target', 'prcp_reverse_run',
                    'prcp_reverse_result', 'prcp_data_reverse']:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl} WHERE is_deleted=0")).fetchone()[0]
            print(f"  {tbl}: {n} active")
        # 检查每个 scheme 的 date_offset 范围
        print()
        for r in conn.execute(text("""
            SELECT s.scheme_code, COUNT(DISTINCT d.date_offset) AS offsets, MIN(d.data_date) AS first, MAX(d.data_date) AS last
            FROM prcp_data_reverse d
            JOIN prcp_reverse_scheme s ON s.scheme_code=d.scheme_code AND s.is_deleted=0
            WHERE d.is_deleted=0
            GROUP BY s.scheme_code
        """)).fetchall():
            print(f"  {r[0]}: {r[1]} offsets from {r[2]} to {r[3]}")


if __name__ == "__main__":
    main()