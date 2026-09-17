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
- 13+13 期限桶分配（启发式）：
  - 资产类贷款/投资：原始期限按 1Y(15%)/3Y(30%)/5Y(35%)/10Y(20%) 集中
  - 负债类存款：剩余期限集中在短端（活期给 d1/d7，定期按命名）
  - 表外：剩余期限集中在 d7
- ASF/RSF：负债→ASF，资产→RSF，表外→空
- HQLA 折算：按账户名关键词启发式
"""
import pymysql
import re

DB_CFG = dict(host='127.0.0.1', port=3306, user='almd', password='Almd@2026',
              database='prcp_db', charset='utf8mb4')

# 13 个期限桶顺序：d1, d7, m1, m3, m6, y1, y2, y3, y5, y10, y15, y20, y30
BUCKETS = ['d1', 'd7', 'm1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y10', 'y15', 'y20', 'y30']

# ---------- 期限分配规则 ----------
def distribute_asset_orig(name: str, amt: float) -> dict:
    """资产类原始期限：长期为主"""
    weights = [0] * 13
    weights[5] = 0.10   # 1Y
    weights[6] = 0.20   # 2Y
    weights[7] = 0.30   # 3Y
    weights[8] = 0.20   # 5Y
    weights[9] = 0.15   # 10Y
    weights[10] = 0.05  # 15Y
    return {k: round(amt * w, 4) for k, w in zip(BUCKETS, weights)}

def distribute_asset_rem(name: str, amt: float) -> dict:
    """资产类剩余期限：平均分布"""
    weights = [0.05, 0.05, 0.05, 0.10, 0.15, 0.20, 0.10, 0.10, 0.10, 0.05, 0.025, 0.025, 0.025]
    return {k: round(amt * w, 4) for k, w in zip(BUCKETS, weights)}

def distribute_liab_orig(name: str, amt: float) -> dict:
    """负债类原始期限：分散（不同产品不同）"""
    weights = [0] * 13
    if '活期' in name:
        weights = [0.40, 0.30, 0.10, 0.10, 0.05, 0.05] + [0] * 7
    elif '短定' in name or '1Y' in name or '≤1' in name:
        weights[3] = 0.30; weights[4] = 0.30; weights[5] = 0.40
    elif '三年' in name or '3年' in name or '3Y' in name:
        weights[5] = 0.10; weights[6] = 0.10; weights[7] = 0.50; weights[8] = 0.30
    elif '结构' in name:
        weights = [0.05, 0.05, 0.10, 0.15, 0.20, 0.20, 0.05, 0.05, 0.10, 0.05] + [0]*3
    elif '保证' in name:
        weights[0] = 0.50; weights[1] = 0.30; weights[2] = 0.20
    elif '外币' in name:
        weights[3] = 0.30; weights[4] = 0.30; weights[5] = 0.40
    else:
        weights = [0.10, 0.10, 0.10, 0.15, 0.15, 0.15, 0.10, 0.05, 0.05, 0.05] + [0]*3
    return {k: round(amt * w, 4) for k, w in zip(BUCKETS, weights)}

def distribute_liab_rem(name: str, amt: float) -> dict:
    """负债类剩余期限：短端为主"""
    weights = [0] * 13
    if '活期' in name:
        weights[0] = 0.80; weights[1] = 0.20
    elif '短定' in name:
        weights[2] = 0.30; weights[3] = 0.30; weights[4] = 0.30; weights[5] = 0.10
    elif '三年' in name or '3年' in name:
        weights[3] = 0.10; weights[4] = 0.10; weights[5] = 0.20; weights[6] = 0.20; weights[7] = 0.30; weights[8] = 0.10
    elif '结构' in name:
        weights = [0.05, 0.05, 0.10, 0.15, 0.20, 0.20, 0.10, 0.05, 0.05, 0.05] + [0]*3
    elif '保证' in name:
        weights[0] = 0.50; weights[1] = 0.30; weights[2] = 0.20
    else:
        weights = [0.15, 0.15, 0.10, 0.10, 0.10, 0.15, 0.10, 0.10, 0.05] + [0]*4
    return {k: round(amt * w, 4) for k, w in zip(BUCKETS, weights)}

def distribute_off_orig(name: str, amt: float) -> dict:
    """表外类原始期限：短端为主"""
    weights = [0.10, 0.30, 0.20, 0.20, 0.10, 0.10] + [0] * 7
    return {k: round(amt * w, 4) for k, w in zip(BUCKETS, weights)}

def distribute_off_rem(name: str, amt: float) -> dict:
    """表外类剩余期限：极短"""
    weights = [0.30, 0.50, 0.15, 0.05] + [0] * 9
    return {k: round(amt * w, 4) for k, w in zip(BUCKETS, weights)}

# ---------- ASF/RSF + HQLA 启发式 ----------
def get_asf_rsf(category: str) -> str:
    if category == '负债': return 'ASF'
    if category == '资产': return 'RSF'
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

        # 大类
        if path and '/L1_资产/' in path: category = '资产'
        elif path and '/L1_负债/' in path: category = '负债'
        elif path and '/L1_表外/' in path: category = '表外'
        else: category = ''

        # 跳过空余额的 L1/L2 父节点（避免生成无效记录）
        if not current_amount or current_amount <= 0:
            skipped += 1
            continue

        # 期限桶分配
        current_amount = float(current_amount or 0)
        if category == '资产':
            orig = distribute_asset_orig(node_name, current_amount)
            rem = distribute_asset_rem(node_name, current_amount)
        elif category == '负债':
            orig = distribute_liab_orig(node_name, current_amount)
            rem = distribute_liab_rem(node_name, current_amount)
        elif category == '表外':
            orig = distribute_off_orig(node_name, current_amount)
            rem = distribute_off_rem(node_name, current_amount)
        else:
            orig = {k: 0 for k in BUCKETS}
            rem = {k: 0 for k in BUCKETS}

        # ASF/RSF + HQLA
        asf_rsf = get_asf_rsf(category)
        hqla = get_hqla_factor(node_name)

        # 字段映射
        cur.execute("""
            INSERT INTO prcp_data_basic
              (data_date, coa_node_id, node_code, node_name, node_level, parent_code,
               category, date_offset, offset_unit,
               orig_d1, orig_d7, orig_m1, orig_m3, orig_m6,
               orig_y1, orig_y2, orig_y3, orig_y5, orig_y10, orig_y15, orig_y20, orig_y30,
               rem_d1, rem_d7, rem_m1, rem_m3, rem_m6,
               rem_y1, rem_y2, rem_y3, rem_y5, rem_y10, rem_y15, rem_y20, rem_y30,
               asf_rsf, hqla_factor,
               current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,
               is_deleted, created_by, updated_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,
                    %s,%s,%s,%s,%s,
                    0,1,1)
        """, (
            '2027-01-01', node_id, node_code, node_name, node_level, parent_code,
            category, 0, 'D',
            *[orig[k] for k in BUCKETS],
            *[rem[k] for k in BUCKETS],
            asf_rsf, hqla,
            float(current_amount or 0), float(avg_balance or 0),
            float(interest_rate or 0), float(interest_amount or 0),
            float(risk_weight or 0),
        ))
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