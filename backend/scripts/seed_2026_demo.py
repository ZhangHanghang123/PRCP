"""为反算方案 2026 造一版演示数据：

1. 创建新 run（SUCCESS）
2. 24 个月 × 40 个节点的 prcp_data_reverse（金额随月份推进：剩余期限桶往前推）
3. 24 个月 × 40 个节点 × 5 个指标的 prcp_metric_coefficient
   - 当前值 = 起始值
   - y1~y5 = 预测值（线性增长/下降）
"""
import sys
from datetime import date, timedelta
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

DB_URL = f"mysql+pymysql://prcp:{quote_plus('Prcp@2026')}@127.0.0.1:3306/prcp_db?charset=utf8mb4"
engine = create_engine(DB_URL)

REV_CODE = "2026"
COA_SCHEME_CODE = "ZXCOA_V1"

# 期限桶：m1~m12 + y10/y15/y20/y30
ORIG_BUCKETS = (
    [f"orig_m{i}" for i in range(1, 13)]
    + ["orig_y10", "orig_y15", "orig_y20", "orig_y30"]
)
REM_BUCKETS = (
    [f"rem_m{i}" for i in range(1, 13)]
    + ["rem_y10", "rem_y15", "rem_y20", "rem_y30"]
)
# 完整 64 桶（与 prcp_data_basic 一致）
FULL_ORIG = ORIG_BUCKETS  # 16 桶？不对
# 实际是 64 桶：m1~m60 + y10/y15/y20/y30 (m13-m60 = m_idx-1)
ALL_ORIG = [f"orig_m{i}" for i in range(1, 61)] + ["orig_y10", "orig_y15", "orig_y20", "orig_y30"]
ALL_REM = [f"rem_m{i}" for i in range(1, 61)] + ["rem_y10", "rem_y15", "rem_y20", "rem_y30"]

METRIC_TYPES = ["ROE", "CET1", "LCR", "NSFR", "DELTA_EVE"]


def main():
    with engine.connect() as conn:
        # 1. 查方案
        row = conn.execute(text("""
            SELECT s.id AS rev_id, s.coa_scheme_id, s.data_date AS base_date, s.horizon_months
            FROM prcp_reverse_scheme s
            WHERE s.scheme_code=:sc AND s.is_deleted=0
        """), {"sc": REV_CODE}).first()
        if not row:
            print(f"未找到方案 {REV_CODE}"); sys.exit(1)
        rev_id, coa_scheme_id, base_date, horizon = row
        print(f"方案 {REV_CODE}: rev_id={rev_id}, coa_scheme_id={coa_scheme_id}, base={base_date}, horizon={horizon}")

        # 2. 查节点
        nodes = conn.execute(text("""
            SELECT id, node_code, node_name, node_level, parent_id, path
            FROM prcp_coa_node
            WHERE scheme_id=:s AND is_deleted=0
            ORDER BY path, sort_order
        """), {"s": coa_scheme_id}).fetchall()
        print(f"节点数: {len(nodes)}")
        node_codes = [n[1] for n in nodes]

        # 3. 创建一个新 run
        # 先清理已有的 SUCCESS run 演示数据（幂等）
        conn.execute(text("""
            DELETE rd FROM prcp_data_reverse rd
            JOIN prcp_reverse_run r ON r.id=rd.run_id
            WHERE rd.scheme_code=:sc
        """), {"sc": REV_CODE})
        conn.execute(text("""
            DELETE FROM prcp_reverse_run WHERE scheme_id=:sid
        """), {"sid": rev_id})
        conn.execute(text("""
            DELETE FROM prcp_metric_coefficient
            WHERE scheme_code=:sc AND data_date BETWEEN :d1 AND :d2
        """), {"sc": COA_SCHEME_CODE,
               "d1": date(2026, 1, 1), "d2": date(2027, 12, 31)})
        conn.commit()

        run_id = conn.execute(text("""
            INSERT INTO prcp_reverse_run
              (scheme_id, status, start_at, end_at, optimal_value,
               created_by, updated_by)
            VALUES (:sid, 'SUCCESS', NOW(), NOW(), 1, 1, 1)
        """), {"sid": rev_id}).lastrowid
        print(f"创建新 run_id={run_id}")

        # 4. 生成 prcp_data_reverse（24 月 × 40 节点）
        # 简化：每个节点每月按节点 code hash 分配金额，剩余期限桶随月份往前推
        total_inserted = 0
        for month_i in range(1, 25):
            # data_date = base_date + month_i 月
            year_offset = (base_date.month + month_i - 1) // 12
            month = (base_date.month + month_i - 1) % 12 + 1
            data_date = date(base_date.year + year_offset, month, 1)

            for n in nodes:
                nid, ncode, nname, nlevel, parent_id, path = n
                # 按节点 code 算初始金额（确定性随机）
                base_amount = (abs(hash(ncode)) % 100000) / 10.0 * (1 + 0.01 * month_i)
                # 剩余期限桶：第 month_i 月，rem_m_j 表示还剩 j 个月到期的金额
                # j 从 1 到 60-y10（最远按年分摊）
                # 简化：均匀分布到前 12 个月，每月等量
                rem_buckets = {}
                rem_per = base_amount / 12.0
                for j in range(1, 13):
                    rem_buckets[f"rem_m{j}"] = round(rem_per * (1 + 0.05 * (12 - j)), 2)
                # rem_m13~m60 + y10/y15/y20/y30 = 0
                for col in ALL_REM:
                    rem_buckets.setdefault(col, 0)

                # orig_buckets 64 桶全填
                orig_buckets = {}
                orig_per = base_amount / 64.0
                for col in ALL_ORIG:
                    orig_buckets[col] = round(orig_per, 2)

                # 构造 INSERT
                cols = (["record_id", "scheme_code", "run_id", "coa_scheme_id",
                         "data_date", "date_offset", "offset_unit",
                         "coa_node_id", "node_code", "node_name", "node_level",
                         "parent_code", "is_leaf", "category", "current_balance",
                         "avg_balance", "weighted_rate", "interest_amount",
                         "risk_weight", "calc_note"]
                        + ALL_ORIG + ALL_REM)

                vals = {
                    "record_id": f"{REV_CODE}_{run_id}_{ncode}_M{month_i}",
                    "scheme_code": REV_CODE,
                    "run_id": run_id,
                    "coa_scheme_id": coa_scheme_id,
                    "data_date": data_date,
                    "date_offset": month_i,
                    "offset_unit": "M",
                    "coa_node_id": nid,
                    "node_code": ncode,
                    "node_name": nname,
                    "node_level": nlevel,
                    "parent_code": "",
                    "is_leaf": 1,
                    "category": "OTHER",
                    "current_balance": round(base_amount, 2),
                    "avg_balance": round(base_amount, 2),
                    "weighted_rate": 0.035,
                    "interest_amount": round(base_amount * 0.035 / 12, 2),
                    "risk_weight": 1.0,
                    "calc_note": f"演示数据 M{month_i}",
                }
                for col, v in orig_buckets.items():
                    vals[col] = v
                for col in ALL_REM:
                    vals[col] = rem_buckets.get(col, 0)

                placeholders = ",".join([f":{c}" for c in cols])
                cols_sql = ",".join(cols)
                conn.execute(
                    text(f"INSERT INTO prcp_data_reverse ({cols_sql}) VALUES ({placeholders})"),
                    vals
                )
                total_inserted += 1

            if month_i % 6 == 0:
                conn.commit()
                print(f"  M{month_i} 完成（{data_date}）")

        conn.commit()
        print(f"prcp_data_reverse 插入 {total_inserted} 行")

        # 5. 生成 prcp_metric_coefficient（40 节点 × 5 指标 × 24 月 = 4800 行）
        metric_inserted = 0
        for month_i in range(1, 25):
            year_offset = (base_date.month + month_i - 1) // 12
            month = (base_date.month + month_i - 1) % 12 + 1
            data_date = date(base_date.year + year_offset, month, 1)

            for n in nodes:
                nid, ncode, nname, nlevel, parent_id, path = n
                # 节点基础值
                base_v = (abs(hash(ncode)) % 1000) / 10.0
                for mt in METRIC_TYPES:
                    if mt == "ROE":
                        current_v = round(base_v / 10 + 12.0 + 0.05 * month_i, 4)
                    elif mt == "CET1":
                        current_v = round(11.0 + 0.03 * month_i, 4)
                    elif mt == "LCR":
                        current_v = round(150.0 + 0.2 * month_i, 4)
                    elif mt == "NSFR":
                        current_v = round(108.0 + 0.05 * month_i, 4)
                    elif mt == "DELTA_EVE":
                        current_v = round(-2.5 - 0.05 * month_i, 4)
                    y1 = round(current_v + 0.3, 4)
                    y2 = round(current_v + 0.6, 4)
                    y3 = round(current_v + 0.9, 4)
                    y4 = round(current_v + 1.2, 4)
                    y5 = round(current_v + 1.5, 4)

                    rec_id = f"{COA_SCHEME_CODE}_{ncode}_{mt}_{data_date.strftime('%Y%m%d')}"
                    conn.execute(text("""
                        INSERT INTO prcp_metric_coefficient
                          (id, scheme_id, scheme_code, node_id, node_code,
                           metric_type, metric_code, data_date,
                           current_value, y1_value, y2_value, y3_value, y4_value, y5_value,
                           unit, description, status, created_by, updated_by)
                        VALUES
                          (:id, :sid, :sc, :nid, :nc,
                           :mt, :mc, :dd,
                           :cv, :y1, :y2, :y3, :y4, :y5,
                           'PERCENT', :desc, 'ACTIVE', 1, 1)
                    """), {
                        "id": rec_id,
                        "sid": coa_scheme_id, "sc": COA_SCHEME_CODE,
                        "nid": nid, "nc": ncode,
                        "mt": mt, "mc": mt,
                        "dd": data_date,
                        "cv": current_v, "y1": y1, "y2": y2, "y3": y3, "y4": y4, "y5": y5,
                        "desc": f"演示数据 {REV_CODE} M{month_i}",
                    })
                    metric_inserted += 1

            if month_i % 6 == 0:
                conn.commit()
                print(f"  metric M{month_i} 完成")

        conn.commit()
        print(f"prcp_metric_coefficient 插入 {metric_inserted} 行")

        # 6. 验证
        r1 = conn.execute(text("""
            SELECT COUNT(*) FROM prcp_data_reverse WHERE scheme_code=:sc AND run_id=:rid
        """), {"sc": REV_CODE, "rid": run_id}).scalar()
        r2 = conn.execute(text("""
            SELECT COUNT(*) FROM prcp_metric_coefficient
            WHERE scheme_code=:sc
        """), {"sc": COA_SCHEME_CODE}).scalar()
        print(f"\n=== 验证 ===")
        print(f"prcp_data_reverse（方案 2026）: {r1} 行")
        print(f"prcp_metric_coefficient（ZXCOA_V1 全部）: {r2} 行")


if __name__ == "__main__":
    main()