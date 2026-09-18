#!/usr/bin/env python3
"""
从 prcp_data_balance 初始化 prcp_data_basic（基础数据表）

策略：
- 目标日期：2027-01-01（最新一期）
- 110 个 (coa_node_id, data_date) 记录全部映射
- 字段映射：
  - current_amount → current_balance
  - avg_balance    → avg_balance
  - interest_rate  → weighted_rate
  - interest_amount → interest_amount
  - risk_weight    → risk_weight
  - path → 自动推断 category（资产/负债/表外）
  - node_code/node_name/node_level/parent_code 从 prcp_coa_node JOIN
- 17 个期限桶分配（启发式）：
  - 资产类贷款/投资：原始期限按 1Y(15%)/3Y(30%)/5Y(35%)/10Y(20%) 集中
  - 负债类存款：剩余期限集中在短端（活期给 m1/m2，定期按命名）
  - 表外：剩余期限集中在 m1
- ASF/RSF：负债→ASF，资产→RSF，表外→空
- HQLA 折算：按账户名关键词启发式

v2 改造（2026-09-18）：
  - 期限桶由 13 桶改为 17 桶：去掉 d1/d7、1 年内由 m1/m3/m6 拆为 m1~m12
  - 删除未填充的 y2/y3/y5 字段写入（原 DB 也没有这些列）
"""
import pymysql
import re

DB_CFG = dict(host='127.0.0.1', port=3306, user='almd', password='Almd@2026',
              database='prcp_db', charset='utf8mb4')

# 17 个期限桶顺序：m1~m12（1 年内按月）+ y1, y10, y15, y20, y30
BUCKETS = ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12',
           'y1', 'y10', 'y15', 'y20', 'y30']
N_BUCKETS = len(BUCKETS)  # 17


# ---------- 期限分配规则 ----------
def _empty():
    return {k: 0.0 for k in BUCKETS}


def distribute_asset_orig(name: str, amt: float) -> dict:
    """资产类原始期限：长期为主"""
    w = _empty()
    w['y1'] = 0.10    # 1Y
    w['y10'] = 0.15    # 10Y
    w['y15'] = 0.05    # 15Y
    # 短端留 0（资产类无 1 年内原始期限）
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_asset_rem(name: str, amt: float) -> dict:
    """资产类剩余期限：1 年内按月分布 + 长端衰减"""
    w = _empty()
    # 1 年内 12 月均匀分布（每月 5%）
    for m in range(1, 13):
        w[f'm{m}'] = 0.05
    w['y1'] = 0.20    # 1Y
    w['y10'] = 0.10   # 10Y
    w['y15'] = 0.05   # 15Y
    w['y20'] = 0.025
    w['y30'] = 0.025
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_liab_orig(name: str, amt: float) -> dict:
    """负债类原始期限：分散（不同产品不同）"""
    w = _empty()
    if '活期' in name:
        for k in ['m1', 'm2', 'm3', 'm4', 'm5', 'm6']:
            w[k] = 0.10
        w['y1'] = 0.20
    elif '短定' in name or '1Y' in name or '≤1' in name:
        for k in ['m4', 'm5', 'm6']: w[k] = 0.10
        w['y1'] = 0.30
    elif '三年' in name or '3年' in name or '3Y' in name:
        w['y1'] = 0.10
        w['y10'] = 0.30
        w['y15'] = 0.05
    elif '结构' in name:
        for k in ['m1', 'm2', 'm3']: w[k] = 0.05
        for k in ['m4', 'm5', 'm6']: w[k] = 0.10
        w['y1'] = 0.20
    elif '保证' in name:
        w['m1'] = 0.40
        w['m2'] = 0.30
        w['m3'] = 0.20
    elif '外币' in name:
        for k in ['m4', 'm5', 'm6']: w[k] = 0.10
        w['y1'] = 0.30
    else:
        for k in ['m1', 'm2', 'm3', 'm4', 'm5', 'm6']: w[k] = 0.05
        w['y1'] = 0.15
        w['y10'] = 0.05
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_liab_rem(name: str, amt: float) -> dict:
    """负债类剩余期限：短端为主"""
    w = _empty()
    if '活期' in name:
        w['m1'] = 0.50
        w['m2'] = 0.30
    elif '短定' in name:
        w['m1'] = 0.20
        w['m2'] = 0.20
        w['m3'] = 0.20
        w['m6'] = 0.10
        w['y1'] = 0.05
    elif '三年' in name or '3年' in name:
        w['m6'] = 0.10
        w['y1'] = 0.20
        w['y10'] = 0.20
        w['y15'] = 0.05
    elif '结构' in name:
        for k in ['m1', 'm2', 'm3']: w[k] = 0.05
        for k in ['m4', 'm5', 'm6']: w[k] = 0.10
        w['y1'] = 0.20
    elif '保证' in name:
        w['m1'] = 0.50
        w['m2'] = 0.30
        w['m3'] = 0.20
    else:
        w['m1'] = 0.15
        w['m2'] = 0.15
        w['m3'] = 0.10
        w['m6'] = 0.10
        w['y1'] = 0.15
        w['y10'] = 0.05
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_off_orig(name: str, amt: float) -> dict:
    """表外类原始期限：短端为主"""
    w = _empty()
    for k in ['m1', 'm2', 'm3', 'm4', 'm5', 'm6']:
        w[k] = 0.10
    w['y1'] = 0.10
    return {k: round(amt * v, 4) for k, v in w.items()}


def distribute_off_rem(name: str, amt: float) -> dict:
    """表外类剩余期限：极短"""
    w = _empty()
    w['m1'] = 0.50
    w['m2'] = 0.30
    w['m3'] = 0.15
    return {k: round(amt * v, 4) for k, v in w.items()}


# ---------- ASF/RSF + HQLA 启发式 ----------
def get_asf_rsf(category: str) -> str:
    """根据资产负债分类返回 ASF/RSF（码值国际化后）"""
    if category == 'LIABILITY': return 'ASF'
    if category == 'ASSET': return 'RSF'
    return ''


def get_hqla_factor(node_name: str) -> float:
    n = node_name.lower()
    if '现金' in n: return 1.0
    if '国债' in n or '央行' in n: return 0.95
    if '政策性金融' in n: return 0.85
    if '地方政府' in n: return 0.80
    if '公司债' in n or '商业' in n: return 0.50
    return 0.0


def main():
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()

    # 1) 读取 2027-01-01 的所有 balance 记录
    print('读取 2027-01-01 balance 数据...')
    cur.execute("""
        SELECT n.id, n.node_code, n.node_name, n.node_level, n.path,
                   n.parent_id, np.node_code AS parent_code,
                   b.current_amount, b.avg_balance, b.interest_rate,
                   b.interest_amount, b.capital_ratio, b.risk_weight
            FROM prcp_data_balance b
            JOIN prcp_coa_node n ON n.id=b.coa_node_id
            LEFT JOIN prcp_coa_node np ON np.id=n.parent_id
            WHERE b.is_deleted=0 AND b.data_date='2027-01-01'
            ORDER BY n.path
        """)
    rows = cur.fetchall()
    print(f'  共 {len(rows)} 条记录')

    # 2) 清空 prcp_data_basic（避免重复）
    print('清空 prcp_data_basic 旧数据...')
    cur.execute('DELETE FROM prcp_data_basic')

    # 3) 逐条映射 + INSERT
    inserted = 0
    skipped = 0
    for r in rows:
        (node_id, node_code, node_name, node_level, path,
         parent_id, parent_code, current_amount, avg_balance,
         interest_rate, interest_amount, capital_ratio, risk_weight) = r

        # 大类（从 path 推导，码值用国际化后的英文）
        if path and '/L1_ASSET/' in path: category = 'ASSET'
        elif path and '/L1_LIABILITY/' in path: category = 'LIABILITY'
        elif path and '/L1_OFF_BALANCE/' in path: category = 'OFF_BALANCE'
        else: category = ''

        # 跳过空余额的 L1/L2 父节点（避免生成无效记录）
        if not current_amount or current_amount <= 0:
            skipped += 1
            continue

        # 期限桶分配
        current_amount = float(current_amount or 0)
        if category == 'ASSET':
            orig = distribute_asset_orig(node_name, current_amount)
            rem = distribute_asset_rem(node_name, current_amount)
        elif category == 'LIABILITY':
            orig = distribute_liab_orig(node_name, current_amount)
            rem = distribute_liab_rem(node_name, current_amount)
        elif category == 'OFF_BALANCE':
            orig = distribute_off_orig(node_name, current_amount)
            rem = distribute_off_rem(node_name, current_amount)
        else:
            orig = {k: 0 for k in BUCKETS}
            rem = {k: 0 for k in BUCKETS}

        # ASF/RSF + HQLA
        asf_rsf = get_asf_rsf(category)
        hqla = get_hqla_factor(node_name)

        # 字段映射（17 列 × 2 = 34 个期限桶列）
        # SQL 占位符顺序必须与 BUCKETS 一致（先 orig_* 再 rem_*）
        cols = ', '.join(f'{p}_{b}' for p in ('orig', 'rem') for b in BUCKETS)
        placeholders = ', '.join(['%s'] * (N_BUCKETS * 2))
        sql = f"""
            INSERT INTO prcp_data_basic
              (data_date, coa_node_id, node_code, node_name, node_level, parent_code,
               category, date_offset, offset_unit,
               {cols},
               asf_rsf, hqla_factor,
               current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
               is_deleted, created_by, updated_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    {placeholders},
                    %s,%s,
                    %s,%s,%s,%s,%s,
                    0,1,1)
        """
        params = [
            '2027-01-01', node_id, node_code, node_name, node_level, parent_code,
            category, 0, 'D',
            *[orig[k] for k in BUCKETS],
            *[rem[k] for k in BUCKETS],
            asf_rsf, hqla,
            float(current_amount or 0), float(avg_balance or 0),
            float(interest_rate or 0), float(interest_amount or 0),
            float(risk_weight or 0),
        ]
        cur.execute(sql, params)
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f'✓ 完成：插入 {inserted} 条，跳过 {skipped} 条空记录')

    # 4) 校验汇总
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()
    cur.execute("""
        SELECT category, COUNT(*) AS cnt, SUM(current_balance) AS total
        FROM prcp_data_basic WHERE is_deleted=0
        GROUP BY category
    """)
    print('\n=== 校验（按大类） ===')
    for row in cur.fetchall():
        print(f'  {row[0]:<6}  {row[1]:>3} 账户册  余额合计 {row[2]:>14,.2f}')
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()