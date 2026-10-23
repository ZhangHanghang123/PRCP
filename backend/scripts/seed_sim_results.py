"""Seed new business simulation: 3 schemes × 1 SUCCESS run × 24 months × 57 nodes
   让"新业务模拟结果表"有内容展示"""
import sys, random, json
from datetime import date, timedelta
from decimal import Decimal
sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text

DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
eng = create_engine(DB_URL)

random.seed(42)

SCHEMES = [
    {
        'scheme_code': 'SIM_LOAN_PERSONAL',
        'scheme_name': '个人贷款新业务模拟',
        'description': '个人住房/消费贷款新增业务，按年增长 8%-15%，期限 5/10/20/30 年',
        'horizon': 24,
        'growth_range': (0.08, 0.15),
        'rates': {'5Y': 0.0405, '10Y': 0.0435, '20Y': 0.0485, '30Y': 0.0510},
    },
    {
        'scheme_code': 'SIM_DEPOSIT_CORP',
        'scheme_name': '对公存款新业务模拟',
        'description': '对公活期/定期存款新增业务，活期 1.5% / 1Y 2.1% / 3Y 2.85%',
        'horizon': 24,
        'growth_range': (0.05, 0.10),
        'rates': {'1Y': 0.0210, '3Y': 0.0285, '5Y': 0.0310},
    },
    {
        'scheme_code': 'SIM_BOND_INTERBANK',
        'scheme_name': '债券与同业资产负债模拟',
        'description': '国债 + 政策性金融债 + 同业拆借，期限 3M / 6M / 1Y / 3Y',
        'horizon': 24,
        'growth_range': (0.03, 0.08),
        'rates': {'3M': 0.0195, '6M': 0.0210, '1Y': 0.0240, '3Y': 0.0275},
    },
]


def seed():
    with eng.begin() as conn:
        # 1. 清理现有数据（prcp_sim_run 没有 is_deleted，需硬删）
        for t in ['prcp_sim_result', 'prcp_sim_node_config', 'prcp_sim_term_ratio',
                  'prcp_sim_scheme']:
            r = conn.execute(text(f"UPDATE {t} SET is_deleted=1 WHERE is_deleted=0"))
            print(f"[clean] {t}: {r.rowcount}")
        r = conn.execute(text("DELETE FROM prcp_sim_run"))
        print(f"[clean] prcp_sim_run: {r.rowcount}")

        # 2. 拿 ZX_COA 节点
        nodes = conn.execute(text(
            "SELECT id, node_code, node_name, node_level, path FROM prcp_coa_node "
            "WHERE scheme_id=1 AND is_deleted=0 ORDER BY node_level, id"
        )).fetchall()
        if not nodes:
            raise RuntimeError("ZX_COA 节点为空，请先初始化账户册")
        coa_scheme_id = conn.execute(text(
            "SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZX_COA' AND is_deleted=0 LIMIT 1"
        )).fetchone()[0]
        print(f"[info] {len(nodes)} nodes, coa_scheme_id={coa_scheme_id}")

        # 3. 给每个 scheme 创建 scheme + run + result
        for sc in SCHEMES:
            sid = conn.execute(text(
                "INSERT INTO prcp_sim_scheme (scheme_code, scheme_name, coa_scheme_id, "
                "description, status, is_deleted, config_node_count, data_date, "
                "created_by, updated_by) VALUES (:sc, :sn, :cs, :d, 'ACTIVE', 0, :cn, "
                "STR_TO_DATE('2025-12-31','%Y-%m-%d'), 1, 1)"
            ), {
                'sc': sc['scheme_code'], 'sn': sc['scheme_name'], 'cs': coa_scheme_id,
                'd': sc['description'], 'cn': 0,
            }).lastrowid
            print(f"[scheme] {sc['scheme_code']} id={sid}")

            # Run
            base = date(2025, 12, 31)
            rid = conn.execute(text(
                "INSERT INTO prcp_sim_run (sim_scheme_id, sim_scheme_code, "
                "base_data_date, month_count, target_data_date, status, progress, "
                "total_nodes, configured_node_count, rolled_node_count, "
                "aggregated_node_count, processed_nodes, duration_ms, "
                "started_at, finished_at, created_by) "
                "VALUES (:sid, :sc, :bd, :mc, :td, 'SUCCESS', 100, "
                ":tn, :cn, :rn, :an, :pn, :dur, NOW(), NOW(), 1)"
            ), {
                'sid': sid, 'sc': sc['scheme_code'],
                'bd': base, 'mc': sc['horizon'],
                'td': date(base.year + sc['horizon'] // 12,
                           base.month, base.day),
                'tn': len(nodes), 'cn': len(nodes), 'rn': len(nodes),
                'an': 0, 'pn': len(nodes), 'dur': random.randint(3000, 12000),
            }).lastrowid
            print(f"[run] id={rid} months={sc['horizon']}")

            # Result: 每个月 × 每个节点
            for mo in range(1, sc['horizon'] + 1):
                # 月份日期
                year_off = mo // 12
                month_off = mo % 12 or 12
                data_date = date(base.year + year_off, month_off, 1)

                for n in nodes:
                    nid, ncode, nname, nlevel, path = n
                    cat = 'ASSET' if ncode.startswith('S01') else \
                          'LIABILITY' if ncode.startswith('S02') else \
                          'EQUITY' if ncode.startswith('S03') else \
                          'OFF_BALANCE' if ncode.startswith('S04') else 'OTHER'

                    # 当前余额：基期 + 月度增长（增长率随方案）
                    base_bal = random.uniform(1e9, 8e11)
                    growth = random.uniform(*sc['growth_range'])
                    cur_bal = base_bal * (1 + growth) ** (mo / 12)

                    # 加权平均利率：按方案利率 ± 随机扰动
                    rate_key = random.choice(list(sc['rates'].keys()))
                    base_rate = sc['rates'][rate_key]
                    rate = base_rate + random.uniform(-0.005, 0.005)

                    avg_bal = cur_bal * random.uniform(0.98, 1.02)
                    interest = avg_bal * rate / 12  # 月息
                    risk_weight = random.uniform(0.20, 1.50)

                    is_configured = random.random() > 0.3
                    is_aggregated = nlevel > 3 and not is_configured

                    conn.execute(text(
                        "INSERT INTO prcp_sim_result ("
                        "sim_scheme_code, sim_scheme_id, run_id, data_date, date_offset, "
                        "coa_scheme_id, coa_node_id, node_code, node_name, node_level, "
                        "category, is_configured, is_aggregated, "
                        "current_balance, avg_balance, weighted_rate, interest_amount, "
                        "risk_weight, is_deleted, created_by) "
                        "VALUES (:sc, :sid, :rid, :dd, :do, :cs, :nid, :nc, :nn, :nl, "
                        ":cat, :ic, :ia, :cb, :ab, :wr, :ia2, :rw, 0, 1)"
                    ), {
                        'sc': sc['scheme_code'], 'sid': sid, 'rid': rid,
                        'dd': data_date, 'do': mo, 'cs': coa_scheme_id,
                        'nid': nid, 'nc': ncode, 'nn': nname, 'nl': nlevel,
                        'cat': cat,
                        'ic': 1 if is_configured else 0,
                        'ia': 1 if is_aggregated else 0,
                        'cb': cur_bal, 'ab': avg_bal,
                        'wr': rate, 'ia2': interest, 'rw': risk_weight,
                    })

            # 更新 config_node_count
            conn.execute(text(
                "UPDATE prcp_sim_scheme SET config_node_count=:cn WHERE id=:id"
            ), {'cn': len(nodes), 'id': sid})

        # 4. 验证
        print()
        print("=== Verification ===")
        for tbl in ['prcp_sim_scheme', 'prcp_sim_result']:
            n = conn.execute(text(
                f"SELECT COUNT(*) FROM {tbl} WHERE is_deleted=0"
            )).fetchone()[0]
            print(f"  {tbl}: {n} active")
        n = conn.execute(text("SELECT COUNT(*) FROM prcp_sim_run")).fetchone()[0]
        print(f"  prcp_sim_run: {n} (no is_deleted)")


if __name__ == '__main__':
    seed()
    print("[done] sim results seeded")
