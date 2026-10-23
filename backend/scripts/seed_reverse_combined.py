"""Clean reverse data + create new combined reverse schemes based on current coa + models + kpis"""
import sys
sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text
import json
import random
from datetime import date, datetime, time
from decimal import Decimal

DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
eng = create_engine(DB_URL)

random.seed(42)


def clean_all(conn):
    """Soft-delete all existing reverse data"""
    print("[clean] reverse tables...")
    for tbl in ['prcp_reverse_result', 'prcp_reverse_run', 'prcp_reverse_target',
                'prcp_reverse_scheme', 'prcp_data_reverse']:
        r = conn.execute(text(f"UPDATE {tbl} SET is_deleted=1 WHERE is_deleted=0"))
        print(f"  {tbl}: soft-deleted {r.rowcount} rows")
    # prcp_reverse_run_log 没有 is_deleted 列，直接物理清空
    r = conn.execute(text("DELETE FROM prcp_reverse_run_log"))
    print(f"  prcp_reverse_run_log: deleted {r.rowcount} rows")


def create_schemes(conn):
    """Create 3 reverse schemes, one per model algorithm"""
    # Get ZX_COA scheme
    coa = conn.execute(text(
        "SELECT id, scheme_code FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0 LIMIT 1"
    )).first()
    coa_id = coa[0] if coa else None
    print(f"[coa] ZX_COA id={coa_id}")

    # Get 3 models
    models = conn.execute(text(
        "SELECT id, model_code, model_name, model_type FROM prcp_model "
        "WHERE is_deleted=0 AND model_type IN ('DNN_NEURAL_NETWORK','ANT_COLONY','NONLINEAR_SOLVER') "
        "ORDER BY id"
    )).fetchall()
    print(f"[models] {[m[1] for m in models]}")

    # Map algorithm → model_id
    algo_map = {m[3]: (m[0], m[1], m[2]) for m in models}

    # Get 5 REG KPIs
    kpis = conn.execute(text(
        "SELECT id, kpi_code, kpi_name FROM prcp_kpi_definition "
        "WHERE is_deleted=0 AND kpi_code LIKE 'REG_%' ORDER BY id"
    )).fetchall()
    print(f"[kpis] {[k[1] for k in kpis]}")

    # 3 schemes
    SCHEMES = [
        {
            "code": "REV_DNN_REG",
            "name": "DNN 神经网络综合反算",
            "algo": "DNN_NEURAL_NETWORK",
            "scheme_type": "COMBINED",
            "horizon": 24,
            "description": "基于 DNN_REG 模型对监管指标 + 规模指标做 24 月综合反算",
            "targets": [
                ("REG_LCR",  "≥150%",       "150.0", "GE", 1.5),
                ("REG_NSFR", "≥110%",       "110.0", "GE", 1.5),
                ("REG_CET1", "≥10.5%",      "10.5",  "GE", 2.0),
                ("REG_ROE",  "≥10%",        "10.0",  "GE", 1.0),
            ],
        },
        {
            "code": "REV_ANT_REG",
            "name": "蚁群算法资产负债优化反算",
            "algo": "ANT_COLONY",
            "scheme_type": "OPTIMIZATION",
            "horizon": 24,
            "description": "基于 ACO_OPT 模型对资产/负债结构做 24 月蚁群优化反算",
            "targets": [
                ("REG_NSFR", "≥105%",       "105.0", "GE", 2.0),
                ("REG_EVE",  "≥-5亿（损失≤5亿）", "-500.0", "GE", 2.5),
                ("REG_ROE",  "≥8%",         "8.0",   "GE", 1.0),
            ],
        },
        {
            "code": "REV_NLS_REG",
            "name": "非线性求解 IRRBB 反算",
            "algo": "NONLINEAR_SOLVER",
            "scheme_type": "CALIBRATION",
            "horizon": 12,
            "description": "基于 NLS_REG 模型求解 IRRBB/EVE 的隐含波动率与风险参数",
            "targets": [
                ("REG_LCR",  "≥120%",       "120.0", "GE", 2.0),
                ("REG_EVE",  "≥-3亿（损失≤3亿）", "-300.0", "GE", 3.0),
                ("REG_CET1", "≥9%",         "9.0",   "GE", 2.0),
                ("REG_NSFR", "≥108%",       "108.0", "GE", 1.5),
            ],
        },
    ]

    scheme_ids = []
    for s in SCHEMES:
        algo_code = s["algo"]
        mid, mcode, mname = algo_map.get(algo_code, (None, None, None))

        # 软删旧同名 scheme 防止 UNIQUE 冲突
        ex = conn.execute(text(
            "SELECT id FROM prcp_reverse_scheme WHERE scheme_code=:c AND is_deleted=0"
        ), {"c": s["code"]}).first()
        if ex:
            conn.execute(text("UPDATE prcp_reverse_scheme SET is_deleted=1 WHERE id=:id"), {"id": ex[0]})

        rid = conn.execute(text(
            """INSERT INTO prcp_reverse_scheme
               (scheme_code, scheme_name, scheme_type, coa_scheme_id, data_date, horizon_months,
                algorithm, model_id, description, status, created_by, updated_by)
               VALUES (:c, :n, :st, :coa, :dd, :h, :algo, :mid, :d, 'ACTIVE', 1, 1)"""
        ), {
            "c": s["code"], "n": s["name"], "st": s["scheme_type"], "coa": coa_id,
            "dd": "2025-12-31", "h": s["horizon"],
            "algo": algo_code, "mid": mid, "d": s["description"],
        }).lastrowid
        scheme_ids.append(rid)
        print(f"[create-scheme] {s['code']} id={rid} model_id={mid}")

        # 软删旧 targets for this scheme
        conn.execute(text("UPDATE prcp_reverse_target SET is_deleted=1 WHERE scheme_id=:s"),
                     {"s": rid})

        # Insert targets
        for idx, (kc, tname, tval, ctype, weight) in enumerate(s["targets"], 1):
            kpi = next((k for k in kpis if k[1] == kc), None)
            if not kpi:
                continue
            tid = conn.execute(text(
                """INSERT INTO prcp_reverse_target
                   (scheme_id, kpi_id, kpi_code, target_name, target_value, constraint_type,
                    weight, horizon_month, sort_order, description, created_by, updated_by)
                   VALUES (:s, :k, :kc, :tn, :tv, :ct, :w, :hm, :so, :d, 1, 1)"""
            ), {
                "s": rid, "k": kpi[0], "kc": kc, "tn": tname, "tv": tval,
                "ct": ctype, "w": weight, "hm": s["horizon"], "so": idx,
                "d": f"{s['name']} - {kpi[2]} 目标",
            }).lastrowid
        print(f"  [targets] +{len(s['targets'])}")
    return scheme_ids, [s["code"] for s in SCHEMES]


def create_runs(conn, scheme_ids):
    """Create SUCCESS runs for each scheme + prcp_reverse_result rows"""
    print()
    print("[runs] creating scenario runs...")

    # Get report items (rpt_item) - we use prcp_rpt_item
    items = conn.execute(text("""
        SELECT ri.id, ri.item_code, ri.item_name, ri.report_id, ri.sort_order
        FROM prcp_rpt_item ri
        WHERE ri.is_deleted = 0
        ORDER BY ri.report_id, ri.sort_order, ri.id
        LIMIT 30
    """)).fetchall()
    if not items:
        # fallback: use coa leaf nodes
        items = conn.execute(text("""
            SELECT n.id, n.node_code, n.node_name, 0 AS rpt_id, n.node_level AS sort_order
            FROM prcp_coa_node n
            JOIN prcp_coa_scheme s ON s.id = n.scheme_id
            WHERE s.scheme_code = 'ZX_COA' AND n.is_deleted = 0 AND n.is_leaf = 1
            ORDER BY n.id LIMIT 30
        """)).fetchall()
    print(f"[rpt_items] {len(items)}")

    run_ids = []
    for i, sid in enumerate(scheme_ids):
        # 软删旧 runs
        conn.execute(text("UPDATE prcp_reverse_run SET is_deleted=1 WHERE scheme_id=:s"), {"s": sid})
        # 旧 logs（无 is_deleted）— 清空
        conn.execute(text(
            "DELETE FROM prcp_reverse_run_log WHERE run_id IN (SELECT id FROM prcp_reverse_run WHERE scheme_id=:s AND is_deleted=1)"
        ), {"s": sid})
        conn.execute(text("UPDATE prcp_reverse_result SET is_deleted=1 WHERE run_id IN (SELECT id FROM prcp_reverse_run WHERE scheme_id=:s AND is_deleted=1)"),
                     {"s": sid})

        run_code = f"R{datetime.now().strftime('%Y%m%d')}_{sid:02d}{random.randint(0, 999):03d}"
        rid = conn.execute(text(
            """INSERT INTO prcp_reverse_run
               (run_code, scheme_id, status, progress, start_at, end_at, duration_sec,
                optimal_value, metrics, description, created_by, updated_by)
               VALUES (:c, :s, 'SUCCESS', 100, NOW(), NOW(), 30, :opt, :m, :desc, 1, 1)
            """
        ), {
            "c": run_code, "s": sid,
            "opt": Decimal(str(round(random.uniform(0.5, 5.0), 4))),
            "m": json.dumps({
                "iterations": random.randint(50, 500),
                "convergence": round(random.uniform(0.95, 0.99), 4),
                "rmse": round(random.uniform(0.001, 0.05), 6),
                "objective": round(random.uniform(0.5, 5.0), 4),
            }, ensure_ascii=False),
            "desc": f"种子数据：{run_code} - 综合反算求解",
        }).lastrowid
        run_ids.append(rid)

        # 日志（写入后 is_deleted=0 标志活跃）
        logs = [
            (0, "INFO", "反算开始..."),
            (12, "INFO", "加载账户册数据：57 个节点"),
            (25, "INFO", f"加载 {random.randint(3, 5)} 个目标约束"),
            (50, "INFO", "开始求解..."),
            (80, "INFO", "求解完成"),
            (95, "INFO", "保存反算结果..."),
            (100, "INFO", "反算完成"),
        ]
        for p, lvl, msg in logs:
            conn.execute(text(
                """INSERT INTO prcp_reverse_run_log (run_id, log_level, log_message, progress)
                   VALUES (:r, :l, :m, :p)"""
            ), {"r": rid, "l": lvl, "m": msg, "p": p})

        # prcp_reverse_result: per item per predict_month
        n_results = 0
        for item in items[:20]:  # 最多 20 个报表项
            for month in [3, 6, 12, 18, 24]:
                base = random.uniform(1000, 100000)
                adjusted = base * random.uniform(0.85, 1.25)
                # predict_date = data_date + month
                predict_date = date(2026, 1, 1)
                from datetime import timedelta as td
                # 用 1 月 1 日 + month 月
                # 简单实现：年份偏移
                predict_year = 2026 + month // 12
                predict_month_in_year = month % 12 or 12
                predict_date = date(predict_year, predict_month_in_year, 1)
                cur_v = round(base, 4)
                adj_v = round(adjusted, 4)
                delta_v = round(adj_v - cur_v, 4)
                conn.execute(text(
                    """INSERT INTO prcp_reverse_result
                       (run_id, predict_month, predict_date, rpt_item_id, rpt_item_code,
                        current_value, adjusted_value, delta_value)
                       VALUES (:r, :m, :pd, :iid, :ic, :cv, :av, :dv)"""
                ), {
                    "r": rid, "m": month, "pd": predict_date,
                    "iid": item[0], "ic": item[1],
                    "cv": cur_v, "av": adj_v, "dv": delta_v,
                })
                n_results += 1
        print(f"  [run] {run_code} scheme={sid} run={rid} items={min(20,len(items))}*5months={n_results} results")
    return run_ids


def create_data_reverse(conn, scheme_ids):
    """Populate prcp_data_reverse for 2025-12-31 - just current vs adjusted"""
    print()
    print("[data_reverse] creating...")

    # Get current scheme
    coa_scheme = conn.execute(text(
        "SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0 LIMIT 1"
    )).first()
    coa_id = coa_scheme[0] if coa_scheme else None

    # Get leaf nodes
    nodes = conn.execute(text(
        """SELECT id, node_code, node_name, node_level, node_type, path
           FROM prcp_coa_node WHERE scheme_id=:s AND is_deleted=0 ORDER BY id"""),
        {"s": coa_id}
    ).fetchall()
    print(f"[data_reverse] {len(nodes)} nodes")

    for sid in scheme_ids:
        run_id = None
        latest = conn.execute(text(
            "SELECT id FROM prcp_reverse_run WHERE scheme_id=:s AND is_deleted=0 ORDER BY id DESC LIMIT 1"
        ), {"s": sid}).first()
        run_id = latest[0] if latest else None

        for n in nodes:
            # build record_id
            record_id = f"{n[1]}_REV_{sid:03d}"
            # orig = current snapshot from data_basic; rem = adjusted (random +/- 10%)
            cur = conn.execute(text(
                """SELECT orig_m1, rem_m1, orig_m12, rem_m12, orig_y10, rem_y10
                   FROM prcp_data_basic WHERE node_code=:nc AND data_date='2025-12-31' AND is_deleted=0 LIMIT 1"""
            ), {"nc": n[1]}).first()
            base_m1 = float(cur[0]) if cur and cur[0] is not None else 0.0
            adj_m1 = base_m1 * random.uniform(0.9, 1.1)
            base_m12 = float(cur[2]) if cur and cur[2] is not None else 0.0
            adj_m12 = base_m12 * random.uniform(0.9, 1.1)
            base_y10 = float(cur[4]) if cur and cur[4] is not None else 0.0
            adj_y10 = base_y10 * random.uniform(0.9, 1.1)

            conn.execute(text(
                """INSERT INTO prcp_data_reverse
                   (record_id, scheme_code, run_id, coa_scheme_id, data_date, date_offset, offset_unit,
                    coa_node_id, node_code, node_name, node_level,
                    orig_m1, rem_m1, orig_m12, rem_m12, orig_y10, rem_y10,
                    current_balance, is_deleted, created_by, updated_by)
                   VALUES (:rid, :sc, :run, :coa, :dd, 0, 'M', :nid, :nc, :nn, :nl,
                    :om1, :rm1, :om12, :rm12, :oy10, :ry10, :cb, 0, 1, 1)"""
            ), {
                "rid": record_id, "sc": f"SCHEME_{sid}", "run": run_id, "coa": coa_id,
                "dd": "2025-12-31", "nid": n[0], "nc": n[1], "nn": n[2], "nl": n[3],
                "om1": base_m1, "rm1": adj_m1, "om12": base_m12, "rm12": adj_m12,
                "oy10": base_y10, "ry10": adj_y10, "cb": base_m1,
            })
        print(f"  [data_reverse] scheme={sid} +{len(nodes)} records")


def main():
    with eng.begin() as conn:
        clean_all(conn)
        scheme_ids, codes = create_schemes(conn)
        create_runs(conn, scheme_ids)
        create_data_reverse(conn, scheme_ids)

    print()
    print("=== Verification ===")
    with eng.begin() as conn:
        for tbl in ['prcp_reverse_scheme', 'prcp_reverse_target', 'prcp_reverse_run',
                    'prcp_reverse_result', 'prcp_data_reverse']:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl} WHERE is_deleted=0")).fetchone()[0]
            print(f"  {tbl}: {n} active")
        # run_log 没有 is_deleted
        n = conn.execute(text("SELECT COUNT(*) FROM prcp_reverse_run_log")).fetchone()[0]
        print(f"  prcp_reverse_run_log: {n} total (no is_deleted)")


if __name__ == "__main__":
    main()