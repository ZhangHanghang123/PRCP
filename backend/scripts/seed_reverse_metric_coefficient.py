"""Populate prcp_metric_coefficient with metric data for each reverse scheme.
Uses ZX_COA node codes (S01/S02/S03/S04...) so the reverse dashboard can find them.
"""
import sys
sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text
import random
from datetime import date

DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
eng = create_engine(DB_URL)
random.seed(42)

# 5 metric types with realistic ranges
METRIC_RANGES = {
    "ROE":       (8.0, 14.0, "%"),       # 净资产收益率
    "CET1":      (8.0, 13.0, "%"),       # 核心一级资本充足率
    "LCR":       (90.0, 180.0, "%"),     # 流动性覆盖率
    "NSFR":      (95.0, 130.0, "%"),     # 净稳定资金比例
    "DELTA_EVE": (-3.0, 3.0, "%"),       # 利率风险经济价值变动
}


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

        # Get leaf nodes (level 5+) from ZX_COA
        nodes = conn.execute(text(
            "SELECT id, node_code, node_name FROM prcp_coa_node "
            "WHERE scheme_id=1 AND is_deleted=0 AND node_level >= 5 ORDER BY id"
        )).fetchall()
        print(f"[nodes] {len(nodes)} leaf nodes (level 5+)")

        for s in schemes:
            sid, scode, coa_id, base_date, horizon = s
            base = base_date if base_date else date(2025, 12, 31)

            # Wipe existing metric_coefficient for this scheme_code (soft-delete)
            r = conn.execute(text(
                "UPDATE prcp_metric_coefficient SET is_deleted=1 WHERE scheme_code=:s"
            ), {"s": scode})
            print(f"  [scheme={scode}] cleared {r.rowcount} old rows")

            inserted = 0
            for mo in range(1, horizon + 1):
                offset_date = add_months(base, mo - 1)
                for n in nodes:
                    nid, ncode, nname = n
                    for metric_type, (lo, hi, unit) in METRIC_RANGES.items():
                        # 节点级波动 + 月份趋势
                        base_val = random.uniform(lo, hi)
                        # DELTA_EVE 用绝对值
                        if metric_type == "DELTA_EVE":
                            base_val = random.uniform(-abs(hi), abs(hi))
                        val = round(base_val, 4)

                        rid = f"{scode}_{ncode}_{metric_type}_M{mo}"
                        try:
                            conn.execute(text(
                                """INSERT INTO prcp_metric_coefficient
                                   (id, scheme_id, scheme_code, node_id,
                                    node_code, metric_type, metric_code,
                                    data_date, current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
                                    unit, description, status, is_deleted, created_by, updated_by)
                                   VALUES (:rid, :sid, :sc, :nid, :nc, :mt, :mc,
                                    :dd, :cv, :y1, :y2, :y3, :y4, :y5,
                                    :cu, :d, 'ACTIVE', 0, 1, 1)"""
                            ), {
                                "rid": rid, "sid": coa_id, "sc": scode, "nid": nid,
                                "nc": ncode, "mt": metric_type, "mc": metric_type,
                                "dd": offset_date, "cv": val,
                                "y1": val * 0.98, "y2": val * 1.02,
                                "y3": val * 1.04, "y4": val * 1.06, "y5": val * 1.08,
                                "cu": unit, "d": f"{scode} 节点级 {metric_type}",
                            })
                            inserted += 1
                        except Exception as e:
                            # 软删除行复活逻辑
                            conn.execute(text(
                                """UPDATE prcp_metric_coefficient SET
                                   is_deleted=0, current_value=:cv, y1_value=:y1,
                                   y2_value=:y2, y3_value=:y3, y4_value=:y4, y5_value=:y5,
                                   updated_by=1, updated_at=NOW()
                                   WHERE id=:rid AND is_deleted=1"""
                            ), {
                                "rid": rid, "cv": val,
                                "y1": val * 0.98, "y2": val * 1.02,
                                "y3": val * 1.04, "y4": val * 1.06, "y5": val * 1.08,
                            })
            print(f"  [scheme={scode}] inserted: {inserted} rows ({horizon} months × {len(nodes)} nodes × 5 metrics)")

        # 验证
        print()
        print("=== Verification ===")
        n = conn.execute(text("SELECT COUNT(*) FROM prcp_metric_coefficient WHERE is_deleted=0")).fetchone()[0]
        print(f"  prcp_metric_coefficient active: {n}")
        for r in conn.execute(text("""
            SELECT scheme_code, COUNT(DISTINCT node_code) AS ndc, COUNT(DISTINCT data_date) AS ndd, COUNT(*) AS rc
            FROM prcp_metric_coefficient WHERE is_deleted=0
            GROUP BY scheme_code ORDER BY scheme_code
        """)).fetchall():
            print(f"  {r[0]}: nodes={r[1]} dates={r[2]} rows={r[3]}")


if __name__ == "__main__":
    main()