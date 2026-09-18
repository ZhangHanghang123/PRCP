#!/usr/bin/env python3
"""
从 prcp_data_balance 初始化 prcp_data_basic（基础数据表）

策略：
- 目标日期：2027-01-01（最新一期）
- 字段映射：
  - current_amount → current_balance
  - avg_balance    → avg_balance
  - interest_rate  → weighted_rate
  - interest_amount → interest_amount
  - risk_weight    → risk_weight
  - path → 自动推断 category（资产/负债/表外）
  - node_code/node_name/node_level/parent_code 从 prcp_coa_node JOIN
- 64 个期限桶分配（启发式）：
  - 资产类贷款/投资：原始期限按 1Y/10Y/15Y/30Y 集中；剩余期限 1年内按月均匀 + 长端衰减
  - 负债类存款：原始/剩余期限根据产品类型命名分散
  - 表外：短端为主
- ASF/RSF：负债→ASF，资产→RSF，表外→空
- HQLA 折算：按账户名关键词启发式

v3 改造（2026-09-18）：
  - 期限桶由 17 桶改为 64 桶：5 年内全部按月（m1~m60），长端 y10/y15/y20/y30
  - 删除 y1（因 m12 = 12 月 = 1Y）
"""
import pymysql
import re

DB_CFG = dict(host='127.0.0.1', port=3306, user='almd', password='Almd@2026',
              database='prcp_db', charset='utf8mb4')

# 64 个期限桶顺序：m1~m60（5 年内按月）+ y10, y15, y20, y30
BUCKETS = [f'm{n}' for n in range(1, 61)] + ['y10', 'y15', 'y20', 'y30']
N_BUCKETS = len(BUCKETS)  # 64


# ---------- 期限分配规则 ----------
def _empty():
    return {k: 0.0 for k in BUCKETS}


def _year1_share(n_buckets_in_year1: int = 12):
    """生成 1 年内（m1~m12）的权重，平均分配"""
    each = 1.0 / n_buckets_in_year1
    return {f'm{n}': each for n in range(1, n_buckets_in_year1 + 1)}


def _linear_decay(year: int, max_years: int = 5, base: float = 0.10) -> dict:
    """生成 m(year*12-11) ~ m(year*12) 的权重，随年份线性衰减"""
    start = (year - 1) * 12 + 1
    end = year * 12
    weights = {}
    for n in range(start, end + 1):
        # 距离 year 越近权重越大
        decay = max(0.0, 1 - abs(n - year * 6) / max_years)
        weights[f'm{n}'] = base * decay
    return weights


def distribute_asset_orig(name: str, amt: float) -> dict:
    """资产类原始期限：长期为主"""
    w = _empty()
    # 长端固定桶为主
    w['y10'] = 0.40
    w['y15'] = 0.20
    w['y20'] = 0.10
    w['y30'] = 0.10
    # 1 年内偶有：5%
    w['m6'] = 0.02
    w['m12'] = 0.03
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_asset_rem(name: str, amt: float) -> dict:
    """资产类剩余期限：1 年内按月分布 + 2-5 年衰减 + 长端"""
    w = _empty()
    # 1 年内按月均匀（每 1.5%，合计 18%）
    for m in range(1, 13):
        w[f'm{m}'] = 0.015
    # 2-5 年逐年衰减
    for year, base in [(2, 0.020), (3, 0.015), (4, 0.010), (5, 0.005)]:
        start = (year - 1) * 12 + 1
        end = year * 12
        for n in range(start, end + 1):
            decay = max(0.0, 1 - abs(n - (year - 1) * 12 - 6) / 6)
            w[f'm{n}'] = round(base * decay, 4)
    # 长端
    w['y10'] = 0.08
    w['y15'] = 0.04
    w['y20'] = 0.02
    w['y30'] = 0.02
    # 归一化到 1.0
    total = sum(w.values())
    if total > 0:
        scale = 1.0 / total
        w = {k: round(v * scale, 4) for k, v in w.items()}
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_liab_orig(name: str, amt: float) -> dict:
    """负债类原始期限：分散（不同产品不同）"""
    w = _empty()
    if '活期' in name:
        # 活期：6 个月内均匀分布
        for m in range(1, 7):
            w[f'm{m}'] = 0.10
    elif '短定' in name or '1Y' in name or '≤1' in name:
        # 短定：3-12 月集中
        for m in range(3, 13):
            w[f'm{m}'] = 0.083
    elif '三年' in name or '3年' in name or '3Y' in name:
        # 3 年定期：第 25-36 月集中
        for m in range(25, 37):
            w[f'm{m}'] = 0.083
    elif '五年' in name or '5年' in name or '5Y' in name:
        # 5 年定期：第 49-60 月集中
        for m in range(49, 61):
            w[f'm{m}'] = 0.083
    elif '结构' in name:
        # 结构性存款：1-3 月集中
        for m in range(1, 4):
            w[f'm{m}'] = 0.20
    elif '保证' in name:
        # 保证金：1-6 月集中
        w['m1'] = 0.40
        w['m2'] = 0.30
        w['m3'] = 0.20
        w['m4'] = 0.10
    else:
        # 默认：均匀分散
        for m in range(1, 13):
            w[f'm{m}'] = 0.083
    # 归一化
    total = sum(w.values())
    if total > 0:
        scale = 1.0 / total
        w = {k: round(v * scale, 4) for k, v in w.items()}
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_liab_rem(name: str, amt: float) -> dict:
    """负债类剩余期限：短端为主"""
    w = _empty()
    if '活期' in name:
        w['m1'] = 0.50
        w['m2'] = 0.30
        w['m3'] = 0.20
    elif '短定' in name:
        w['m1'] = 0.20
        w['m2'] = 0.20
        w['m3'] = 0.20
        w['m6'] = 0.10
        w['m12'] = 0.05
    elif '三年' in name or '3年' in name:
        w['m6'] = 0.10
        w['m12'] = 0.20
        for m in range(13, 37):
            w[f'm{m}'] = 0.02
    elif '五年' in name or '5年' in name:
        w['m12'] = 0.10
        for m in range(13, 61):
            w[f'm{m}'] = 0.012
    elif '结构' in name:
        for m in range(1, 7):
            w[f'm{m}'] = 0.10
    elif '保证' in name:
        w['m1'] = 0.50
        w['m2'] = 0.30
        w['m3'] = 0.20
    else:
        w['m1'] = 0.15
        w['m2'] = 0.15
        w['m3'] = 0.10
        for m in range(4, 13):
            w[f'm{m}'] = 0.05
    # 归一化
    total = sum(w.values())
    if total > 0:
        scale = 1.0 / total
        w = {k: round(v * scale, 4) for k, v in w.items()}
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_off_orig(name: str, amt: float) -> dict:
    """表外类原始期限：短端为主"""
    w = _empty()
    for m in range(1, 7):
        w[f'm{m}'] = 0.10
    for m in range(7, 13):
        w[f'm{m}'] = 0.05
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_off_rem(name: str, amt: float) -> dict:
    """表外类剩余期限：集中在 1-3 月"""
    w = _empty()
    w['m1'] = 0.50
    w['m2'] = 0.30
    w['m3'] = 0.20
    return {k: round(amt * v, 4) for k, v in w.items()}


# ---------- category 推断 ----------
def infer_category(path: str) -> str:
    if 'L1_资产' in path or 'L1_ASSET' in path:
        return 'ASSET'
    if 'L1_负债' in path or 'L1_LIABILITY' in path:
        return 'LIABILITY'
    if 'L1_权益' in path or 'L1_EQUITY' in path:
        return 'EQUITY'
    if 'L1_表外' in path or 'L1_OFF_BALANCE' in path:
        return 'OFF_BALANCE'
    return 'ASSET'


# ---------- ASF/RSF & HQLA ----------
def infer_asf_rsf(category: str) -> str:
    if category == 'LIABILITY':
        return 'ASF'
    if category == 'ASSET':
        return 'RSF'
    return ''


def infer_hqla(name: str) -> float:
    if '现金' in name or '存放中央银行' in name:
        return 1.0
    if '国债' in name or '政策性金融债' in name:
        return 1.0
    if '信用债' in name or '企业债' in name:
        return 0.85
    if '贷款' in name:
        return 0.50
    return 0.0


def main():
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()
    # 清空 prcp_data_basic（避免重复）
    cur.execute("DELETE FROM prcp_data_basic")
    print(f"清空 prcp_data_basic 完成")

    # 取 prcp_data_balance + prcp_coa_node 联表
    sql = """
        SELECT b.id, b.coa_node_id, b.data_date, b.current_amount, b.avg_balance,
               b.interest_rate, b.interest_amount, b.risk_weight, n.path
        FROM prcp_data_balance b
        JOIN prcp_coa_node n ON n.id = b.coa_node_id AND n.is_deleted = 0
        WHERE b.is_deleted = 0
    """
    cur.execute(sql)
    rows = cur.fetchall()
    print(f"取到 {len(rows)} 条 balance 记录")

    insert_cols = ['coa_node_id', 'data_date', 'date_offset', 'offset_unit', 'category'] + \
                  [f'orig_{b}' for b in BUCKETS] + [f'rem_{b}' for b in BUCKETS] + \
                  ['asf_rsf', 'hqla_factor', 'current_balance', 'avg_balance',
                   'weighted_rate', 'interest_amount', 'risk_weight', 'is_deleted']

    batch = []
    insert_sql = f"INSERT INTO prcp_data_basic ({', '.join(insert_cols)}) VALUES " + \
                 "(" + ", ".join(["%s"] * len(insert_cols)) + ")"

    for row in rows:
        bal_id, coa_node_id, data_date, cur_amt, avg_bal, rate, interest, risk_w, path = row
        category = infer_category(path)
        name = ''
        cur.execute("SELECT node_name FROM prcp_coa_node WHERE id=%s AND is_deleted=0", (coa_node_id,))
        nr = cur.fetchone()
        if nr: name = nr[0]

        if category == 'ASSET':
            orig = distribute_asset_orig(name, cur_amt)
            rem = distribute_asset_rem(name, cur_amt)
        elif category == 'LIABILITY':
            orig = distribute_liab_orig(name, cur_amt)
            rem = distribute_liab_rem(name, cur_amt)
        elif category == 'OFF_BALANCE':
            orig = distribute_off_orig(name, cur_amt)
            rem = distribute_off_rem(name, cur_amt)
        else:
            orig = _empty()
            rem = _empty()

        asf = infer_asf_rsf(category)
        hqla = infer_hqla(name)

        values = [coa_node_id, data_date, 0, 'D', category]
        for b in BUCKETS:
            values.append(orig.get(b, 0))
        for b in BUCKETS:
            values.append(rem.get(b, 0))
        values += [asf, hqla, cur_amt, avg_bal, rate, interest, risk_w, 0]

        batch.append(values)

        if len(batch) >= 500:
            cur.executemany(insert_sql, batch)
            conn.commit()
            batch = []

    if batch:
        cur.executemany(insert_sql, batch)
        conn.commit()

    cur.execute("SELECT COUNT(*) FROM prcp_data_basic")
    print(f"✅ 写入 {cur.fetchone()[0]} 条 prcp_data_basic 记录（64 桶结构）")
    conn.close()


if __name__ == '__main__':
    main()