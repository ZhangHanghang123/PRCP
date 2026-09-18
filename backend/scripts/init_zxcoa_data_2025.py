"""根据 ZXCOA_V1 账户册方案（scheme_id=6）造 2025-12-31 一版资产负债表 + 基础数据表数据

数据规模参考：中信银行 2024 年末数据
- 总资产 ~9.5 万亿
- 总负债 ~8.7 万亿
- 所有者权益 ~8000 亿
"""
import pymysql

DB = dict(host='127.0.0.1', port=3306, user='almd', password='Almd@2026',
          database='prcp_db', charset='utf8mb4', autocommit=False)
DATA_DATE = '2025-12-31'
SCHEME_ID = 6  # ZXCOA_V1

# 业务规模数据（亿元）参考中信银行 2024 年末
# 字段：current_amount, avg_balance, interest_rate(年化%), risk_weight
# avg_balance 取 current_amount 的 95-100%（年末时点）
# interest_amount = avg_balance × rate / 100（年化利息）
NODE_DATA = {
    # L1 汇总行（用子节点加总，先填 0，最后 UPDATE）
    'ZX_A001': (None, None, None, None),  # 总资产
    'ZX_A002': (None, None, None, None),  # 生息资产（按子节点中计息项加总）
    'ZX_L003': (None, None, None, None),  # 总负债
    'ZX_L004': (None, None, None, None),  # 计息负债
    'ZX_E005': (8000, 7800, 0.0, 0.0),  # 所有者权益

    # L2 币种分组（也按子节点加总，先填 0）
    'ZX_A006': (None, None, None, None),  # (一)人民币小计
    'ZX_A007': (None, None, None, None),  # (二)外币小计
    'ZX_L008': (None, None, None, None),
    'ZX_L009': (None, None, None, None),

    # L3 业务大类
    'ZX_A010': (57000, 56500, 4.5, 75),  # 1.境内人民币各项贷款
    'ZX_A016': (28000, 27800, 3.2, 10),  # 2.人民币非信贷类业务（债券+同业+存款准备金）
    'ZX_A023': (5000, 4900, 0.0, 50),  # 3.人民币非生息资产（不计息，权重取中间值）
    'ZX_A026': (2000, 1950, 4.8, 80),  # 1.外币贷款
    'ZX_A027': (2500, 2400, 3.5, 15),  # 2.外币非信贷资产
    'ZX_A030': (500, 480, 0.0, 60),  # 3.外币非生息资产
    'ZX_L031': (55000, 54500, 1.8, 0),  # 1.境内人民币自营存款
    'ZX_L038': (28000, 27800, 2.8, 0),  # 2.人民币市场化负债
    'ZX_L039': (3000, 2950, 1.5, 0),  # 1.外币存款
    'ZX_L040': (1000, 980, 3.0, 0),  # 2.外币市场化负债

    # L4 业务小类
    'ZX_A011': (32000, 31800, 4.2, 75),  # 对公一般贷款
    'ZX_A012': (18000, 17800, 4.8, 60),  # 个人贷款
    'ZX_A013': (5000, 4900, 8.5, 75),  # 信用卡贷款
    'ZX_A014': (1000, 950, 2.5, 100),  # 票据贴现
    'ZX_A015': (1000, 1000, 4.5, 100),  # 非银贷款
    'ZX_A017': (22000, 21800, 3.2, 5),  # 债券投资（综合）
    'ZX_A020': (2000, 1950, 5.0, 100),  # 结构化融资
    'ZX_A021': (1500, 1450, 2.0, 25),  # 同业资产
    'ZX_A022': (2500, 2500, 1.5, 0),  # 存款准备金
    'ZX_A024': (2500, 2400, 0.0, 50),  # FVTPL 类资产
    'ZX_A025': (2500, 2500, 0.0, 50),  # 其他非生息资产
    'ZX_A028': (2000, 1950, 3.3, 5),  # 外币债券
    'ZX_A029': (500, 450, 2.5, 25),  # 外币同业
    'ZX_L032': (38000, 37600, 1.8, 0),  # 对公存款
    'ZX_L035': (17000, 16900, 2.0, 0),  # 零售存款

    # L5 子类
    'ZX_A018': (10000, 9900, 3.2, 5),  # 金市自营债券
    'ZX_A019': (12000, 11900, 3.2, 5),  # 司库债券
    'ZX_L033': (15000, 14800, 0.5, 0),  # 对公活期存款
    'ZX_L034': (23000, 22800, 2.3, 0),  # 对公定期存款
    'ZX_L036': (5000, 4900, 0.3, 0),  # 零售活期存款
    'ZX_L037': (12000, 12000, 2.5, 0),  # 零售定期存款
}

# L5 期限桶分配（与之前的 init_basic_from_balance.py 类似规则）
# 1. 资产类按账户特征分配
# 2. 负债类按产品（活期/定期）分配
# 3. 表外→空

# orig_*: 原始期限（17 桶：m1~m12 + y1/y10/y15/y20/y30）
# rem_*: 剩余期限（同 17 桶）
# v2 改造（2026-09-18）：去掉 d1/d7、1 年内由 m1/m3/m6 拆为 m1~m12、删除 y2/y3/y5
BUCKETS = [f'm{n}' for n in range(1, 61)] + ['y10', 'y15', 'y20', 'y30']

# 各节点的期限分布（占总金额比例，总和 = 1.0）
# 分配策略：基于业务特征 + 真实银行期限结构
ORIG_DIST = {
    # 资产
    'ZX_A011': {'y1': 0.15, 'y2': 0.25, 'y3': 0.30, 'y5': 0.20, 'y10': 0.10},  # 对公贷款
    'ZX_A012': {'y2': 0.20, 'y3': 0.30, 'y5': 0.30, 'y10': 0.15, 'y15': 0.05},  # 个人贷款
    'ZX_A013': {'d1': 0.10, 'd7': 0.20, 'm1': 0.30, 'm3': 0.20, 'm6': 0.10, 'y1': 0.10},  # 信用卡（短期循环）
    'ZX_A014': {'m1': 0.30, 'm3': 0.50, 'm6': 0.15, 'y1': 0.05},  # 票据贴现（短期）
    'ZX_A015': {'y1': 0.20, 'y2': 0.30, 'y3': 0.30, 'y5': 0.20},  # 非银贷款
    'ZX_A018': {'y1': 0.10, 'y2': 0.20, 'y3': 0.30, 'y5': 0.25, 'y10': 0.10, 'y15': 0.05},  # 金市自营债券
    'ZX_A019': {'y1': 0.15, 'y2': 0.20, 'y3': 0.30, 'y5': 0.20, 'y10': 0.10, 'y15': 0.05},  # 司库债券
    'ZX_A020': {'y1': 0.20, 'y2': 0.30, 'y3': 0.30, 'y5': 0.20},  # 结构化融资
    'ZX_A021': {'d1': 0.10, 'd7': 0.30, 'm1': 0.30, 'm3': 0.20, 'm6': 0.10},  # 同业
    'ZX_A022': {'d1': 0.40, 'm1': 0.30, 'm3': 0.30},  # 存款准备金（短期）
    'ZX_A024': {'y1': 0.20, 'y3': 0.30, 'y5': 0.30, 'y10': 0.20},  # FVTPL
    'ZX_A025': {'d1': 0.40, 'm1': 0.30, 'm3': 0.30},  # 其他非生息
    'ZX_A026': {'y1': 0.20, 'y2': 0.30, 'y3': 0.30, 'y5': 0.20},  # 外币贷款
    'ZX_A028': {'y1': 0.10, 'y2': 0.20, 'y3': 0.30, 'y5': 0.25, 'y10': 0.15},  # 外币债券
    'ZX_A029': {'d7': 0.30, 'm1': 0.30, 'm3': 0.30, 'm6': 0.10},  # 外币同业
    'ZX_A030': {'d1': 0.50, 'm1': 0.30, 'm3': 0.20},  # 外币非生息

    # 负债
    'ZX_L033': {'d1': 0.80, 'd7': 0.15, 'm1': 0.05},  # 对公活期
    'ZX_L034': {'m1': 0.05, 'm3': 0.15, 'm6': 0.20, 'y1': 0.30, 'y2': 0.20, 'y3': 0.10},  # 对公定期
    'ZX_L036': {'d1': 0.85, 'd7': 0.10, 'm1': 0.05},  # 零售活期
    'ZX_L037': {'m1': 0.05, 'm3': 0.15, 'm6': 0.20, 'y1': 0.25, 'y2': 0.15, 'y3': 0.20},  # 零售定期
}

# 剩余期限分布（一般比原始期限短）
REM_DIST = {
    'ZX_A011': {'y1': 0.30, 'y2': 0.30, 'y3': 0.25, 'y5': 0.15},  # 对公
    'ZX_A012': {'y1': 0.20, 'y2': 0.25, 'y3': 0.30, 'y5': 0.20, 'y10': 0.05},
    'ZX_A013': {'d1': 0.30, 'd7': 0.40, 'm1': 0.20, 'm3': 0.10},
    'ZX_A014': {'m1': 0.50, 'm3': 0.40, 'm6': 0.10},
    'ZX_A015': {'y1': 0.30, 'y2': 0.30, 'y3': 0.30, 'y5': 0.10},
    'ZX_A018': {'y1': 0.25, 'y2': 0.25, 'y3': 0.25, 'y5': 0.15, 'y10': 0.10},
    'ZX_A019': {'y1': 0.20, 'y2': 0.25, 'y3': 0.30, 'y5': 0.15, 'y10': 0.10},
    'ZX_A020': {'y1': 0.30, 'y2': 0.30, 'y3': 0.30, 'y5': 0.10},
    'ZX_A021': {'d1': 0.20, 'd7': 0.40, 'm1': 0.30, 'm3': 0.10},
    'ZX_A022': {'d1': 0.50, 'm1': 0.30, 'm3': 0.20},
    'ZX_A024': {'y1': 0.30, 'y3': 0.30, 'y5': 0.25, 'y10': 0.15},
    'ZX_A025': {'d1': 0.50, 'm1': 0.30, 'm3': 0.20},
    'ZX_A026': {'y1': 0.30, 'y2': 0.30, 'y3': 0.25, 'y5': 0.15},
    'ZX_A028': {'y1': 0.25, 'y2': 0.25, 'y3': 0.30, 'y5': 0.20},
    'ZX_A029': {'d7': 0.40, 'm1': 0.30, 'm3': 0.30},
    'ZX_A030': {'d1': 0.60, 'm1': 0.30, 'm3': 0.10},
    'ZX_L033': {'d1': 0.95, 'd7': 0.05},
    'ZX_L034': {'m1': 0.10, 'm3': 0.20, 'm6': 0.25, 'y1': 0.30, 'y2': 0.10, 'y3': 0.05},
    'ZX_L036': {'d1': 0.95, 'd7': 0.05},
    'ZX_L037': {'m1': 0.10, 'm3': 0.20, 'm6': 0.25, 'y1': 0.30, 'y2': 0.10, 'y3': 0.05},
}

# ASF/RSF 标记
ASF_RSF = {
    'asset_default': 'RSF',
    'liab_default': 'ASF',
    'ZX_A022': 'RSF',  # 存款准备金作为 RSF
    'ZX_A024': 'RSF',  # FVTPL
    'ZX_A025': 'RSF',  # 其他非生息
    'ZX_E005': None,   # 权益不计
}

# HQLA 折算系数
HQLA_FACTOR = {
    'ZX_A022': 1.0,  # 存款准备金 = 现金等价物
    'ZX_A018': 0.95,  # 国债/政策性金融债
    'ZX_A019': 0.85,  # 司库债券（部分政策性金融）
    'ZX_A017': 0.50,  # 债券投资综合
    'ZX_A028': 0.50,  # 外币债券
}


def distribute(amount, dist):
    """按 dist 字典分配 amount 到各期限桶"""
    if amount is None or amount == 0:
        return {b: 0.0 for b in BUCKETS}
    return {b: round(amount * dist.get(b, 0), 4) for b in BUCKETS}


def get_asf_rsf(code):
    """根据 node_code 推断 ASF/RSF"""
    if code in ASF_RSF:
        return ASF_RSF[code]
    if code.startswith('ZX_A') or code.startswith('ZX_L008_') and False:
        return 'RSF'
    if code.startswith('ZX_L'):
        return 'ASF'
    if code.startswith('ZX_E'):
        return None
    return None


def insert_balance_data(cur, node_id_map):
    """插入 prcp_data_balance"""
    print('--- prcp_data_balance ---')

    # 1. 先清空 ZXCOA_V1 + 2025-12-31 的旧数据（通过 coa_node_id 间接过滤 scheme_id）
    cur.execute("""DELETE FROM prcp_data_balance
                WHERE data_date=%s
                  AND coa_node_id IN (
                    SELECT id FROM prcp_coa_node WHERE scheme_id=%s
                  )""",
                (DATA_DATE, SCHEME_ID))
    print(f'清空 scheme_id={SCHEME_ID}, date={DATA_DATE} 旧数据 ({cur.rowcount} 条)')

    # 2. 插入所有节点的初始数据（先填业务规模，部分汇总行 None）
    rows = []
    for code, data in NODE_DATA.items():
        node_id = node_id_map.get(code)
        if not node_id:
            continue
        cur_amt, avg_bal, rate, rw = data
        if cur_amt is None:
            # 汇总行先填 0，后续 UPDATE
            cur_amt = 0
            avg_bal = 0
            rate = 0
            rw = 0
        interest = round((avg_bal * rate / 100), 6) if rate else 0
        rows.append({
            'coa_node_id': node_id,
            'data_date': DATA_DATE,
            'current_amount': cur_amt,
            'begin_balance': cur_amt * 0.98,  # 期初略低于期末（模拟增长）
            'avg_balance': avg_bal,
            'interest_rate': rate / 100 if rate else 0,  # 转为小数
            'interest_amount': interest,
            'capital_ratio': 8.0,  # 默认 8% 资本占用率
            'risk_weight': rw / 100 if rw else 0,  # 转为小数
            'm1_gap': 0, 'm2_gap': 0, 'm3_gap': 0, 'm4_gap': 0, 'm5_gap': 0, 'm6_gap': 0,
            'm7_gap': 0, 'm8_gap': 0, 'm9_gap': 0, 'm10_gap': 0, 'm11_gap': 0, 'm12_gap': 0,
            'm13_gap': 0, 'm14_gap': 0, 'm15_gap': 0, 'm16_gap': 0, 'm17_gap': 0, 'm18_gap': 0,
            'm19_gap': 0, 'm20_gap': 0, 'm21_gap': 0, 'm22_gap': 0, 'm23_gap': 0, 'm24_gap': 0,
            'is_deleted': 0,
        })

    cols = ['coa_node_id', 'data_date', 'current_amount', 'begin_balance', 'avg_balance',
            'interest_rate', 'interest_amount', 'capital_ratio', 'risk_weight',
            'm1_gap', 'm2_gap', 'm3_gap', 'm4_gap', 'm5_gap', 'm6_gap',
            'm7_gap', 'm8_gap', 'm9_gap', 'm10_gap', 'm11_gap', 'm12_gap',
            'm13_gap', 'm14_gap', 'm15_gap', 'm16_gap', 'm17_gap', 'm18_gap',
            'm19_gap', 'm20_gap', 'm21_gap', 'm22_gap', 'm23_gap', 'm24_gap',
            'is_deleted']
    for r in rows:
        vals = [r[c] for c in cols]
        placeholders = ','.join(['%s'] * len(cols))
        cur.execute(
            f"INSERT INTO prcp_data_balance ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
    print(f'插入 {len(rows)} 行业务数据')

    # 3. 按层级汇总（自底向上，Python 端循环避免 MySQL 子查询引用更新表）
    def aggregate_to_parent(parent_code):
        """把 parent_code 的子节点聚合到 parent 节点"""
        cur.execute("""
            SELECT n.id, n.node_code
            FROM prcp_coa_node n
            WHERE n.scheme_id=%s AND n.parent_id=%s AND n.is_deleted=0
        """, (SCHEME_ID, node_id_map[parent_code]))
        children = cur.fetchall()
        if not children:
            return
        child_ids = [c[0] for c in children]
        placeholders = ','.join(['%s'] * len(child_ids))
        cur.execute(f"""
            SELECT IFNULL(SUM(current_amount), 0),
                   IFNULL(SUM(avg_balance), 0),
                   IFNULL(SUM(interest_amount), 0)
            FROM prcp_data_balance
            WHERE data_date=%s AND coa_node_id IN ({placeholders})
              AND is_deleted=0
        """, [DATA_DATE] + child_ids)
        sum_cur, sum_avg, sum_int = cur.fetchone()
        cur.execute("""
            UPDATE prcp_data_balance
            SET current_amount=%s, avg_balance=%s, interest_amount=%s,
                begin_balance=%s * 0.98
            WHERE coa_node_id=%s AND data_date=%s
        """, (sum_cur, sum_avg, sum_int, sum_cur,
              node_id_map[parent_code], DATA_DATE))

    # L4 → L3（业务大类）
    for code in ['ZX_A010', 'ZX_A016', 'ZX_A023', 'ZX_A026', 'ZX_A027', 'ZX_A030',
                  'ZX_L031']:
        aggregate_to_parent(code)
    print('L4 → L3 汇总完成')

    # L3 → L2（币种分组）
    for code in ['ZX_A006', 'ZX_A007', 'ZX_L008', 'ZX_L009']:
        aggregate_to_parent(code)
    print('L3 → L2 汇总完成')

    # L2 → L1（汇总行）
    for code in ['ZX_A001', 'ZX_L003']:
        aggregate_to_parent(code)
    print('L2 → L1 汇总完成')

    # 3.4 生息资产 = 总资产 - 非生息项
    # 非生息：ZX_A023(3.人民币非生息资产) + ZX_A030(3.外币非生息资产)
    cur.execute("""
        SELECT current_amount FROM prcp_data_balance
        WHERE coa_node_id=%s AND data_date=%s
    """, (node_id_map['ZX_A001'], DATA_DATE))
    total_asset = cur.fetchone()[0] or 0
    cur.execute("""
        SELECT IFNULL(SUM(current_amount), 0) FROM prcp_data_balance b2
        JOIN prcp_coa_node n2 ON n2.id=b2.coa_node_id
        WHERE n2.node_code IN ('ZX_A023', 'ZX_A030')
          AND b2.data_date=%s
    """, (DATA_DATE,))
    non_interest_asset = cur.fetchone()[0] or 0
    interest_asset = total_asset - non_interest_asset
    cur.execute("""
        UPDATE prcp_data_balance
        SET current_amount=%s, avg_balance=%s * 0.98
        WHERE coa_node_id=%s AND data_date=%s
    """, (interest_asset, interest_asset, node_id_map['ZX_A002'], DATA_DATE))

    # 计息负债 = 总负债 - 不计息项（这里没显式"非计息负债"节点，计息负债 = 总负债）
    cur.execute("""
        SELECT current_amount FROM prcp_data_balance
        WHERE coa_node_id=%s AND data_date=%s
    """, (node_id_map['ZX_L003'], DATA_DATE))
    total_liab = cur.fetchone()[0] or 0
    cur.execute("""
        UPDATE prcp_data_balance
        SET current_amount=%s, avg_balance=%s * 0.98
        WHERE coa_node_id=%s AND data_date=%s
    """, (total_liab, total_liab, node_id_map['ZX_L004'], DATA_DATE))
    print('生息资产/计息负债 单独计算')

    # 4. 验证
    cur.execute("""
        SELECT n.node_code, n.node_name, n.node_level, b.current_amount, b.interest_rate, b.risk_weight
        FROM prcp_data_balance b
        JOIN prcp_coa_node n ON n.id=b.coa_node_id
        WHERE n.scheme_id=%s AND b.data_date=%s AND b.is_deleted=0
        ORDER BY n.node_level, n.sort_order
    """, (SCHEME_ID, DATA_DATE))
    print()
    print(f'验证 balance 节点数: {cur.rowcount}')
    for row in cur.fetchall():
        code, name, level, amt, rate, rw = row
        amt_s = f'{amt:>14,.2f}' if amt else '            0'
        rate_s = f'{rate*100:.2f}%' if rate else '  0%'
        rw_s = f'{rw*100:.0f}%' if rw else ' 0%'
        print(f'  L{level} {code:<10} {name[:25]:<27} 余额={amt_s} 利率={rate_s:<7} 风险权重={rw_s}')


def insert_basic_data(cur, node_id_map):
    """插入 prcp_data_basic"""
    print()
    print('--- prcp_data_basic ---')

    # 1. 清空
    cur.execute("""DELETE FROM prcp_data_basic
                WHERE data_date=%s
                  AND coa_node_id IN (
                    SELECT id FROM prcp_coa_node WHERE scheme_id=%s
                  )""",
                (DATA_DATE, SCHEME_ID))
    print(f'清空 scheme_id={SCHEME_ID}, date={DATA_DATE} 旧数据 ({cur.rowcount} 条)')

    # 2. 插入数据（仅 L4+ 叶子节点有 orig/rem 分配）
    rows = []
    for code, data in NODE_DATA.items():
        node_id = node_id_map.get(code)
        if not node_id:
            continue
        cur_amt, avg_bal, rate, rw = data
        if cur_amt is None:
            cur_amt = 0
            avg_bal = 0
            rate = 0
            rw = 0
        interest = round((avg_bal * rate / 100), 6) if rate else 0
        cur_amt_f = float(cur_amt or 0)
        avg_bal_f = float(avg_bal or 0)
        # 期限桶
        orig_dist = ORIG_DIST.get(code, {})
        rem_dist = REM_DIST.get(code, {})
        orig_buckets = distribute(cur_amt_f, orig_dist)
        rem_buckets = distribute(cur_amt_f, rem_dist)

        rows.append({
            'coa_node_id': node_id,
            'data_date': DATA_DATE,
            'date_offset': 0,
            'offset_unit': 'D',
            **{f'orig_{b}': orig_buckets[b] for b in BUCKETS},
            **{f'rem_{b}': rem_buckets[b] for b in BUCKETS},
            'asf_rsf': get_asf_rsf(code),
            'hqla_factor': HQLA_FACTOR.get(code),
            'current_balance': cur_amt_f,
            'avg_balance': avg_bal_f,
            'weighted_rate': rate / 100 if rate else 0,
            'interest_amount': interest,
            'risk_weight': rw / 100 if rw else 0,
            'is_deleted': 0,
        })

    cols = ['coa_node_id', 'data_date', 'date_offset', 'offset_unit',
            ] + [f'orig_{b}' for b in BUCKETS] + [f'rem_{b}' for b in BUCKETS] + [
            'asf_rsf', 'hqla_factor', 'current_balance', 'avg_balance',
            'weighted_rate', 'interest_amount', 'risk_weight', 'is_deleted']
    for r in rows:
        vals = [r[c] for c in cols]
        placeholders = ','.join(['%s'] * len(cols))
        cur.execute(
            f"INSERT INTO prcp_data_basic ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
    print(f'插入 {len(rows)} 行 basic 数据')

    # 2.5 按层级聚合（自底向上，**必须在 INSERT 之后执行**）
    def aggregate_basic_to_parent(parent_code):
        cur.execute("""
            SELECT n.id, n.node_code
            FROM prcp_coa_node n
            WHERE n.scheme_id=%s AND n.parent_id=%s AND n.is_deleted=0
        """, (SCHEME_ID, node_id_map[parent_code]))
        children = cur.fetchall()
        if not children:
            return
        child_ids = [c[0] for c in children]
        placeholders = ','.join(['%s'] * len(child_ids))

        # SUM 数值字段
        sum_fields = ['current_balance', 'avg_balance', 'interest_amount',
                       ] + [f'orig_{b}' for b in BUCKETS] + [f'rem_{b}' for b in BUCKETS]
        sum_select = ', '.join([f'IFNULL(SUM({f}), 0)' for f in sum_fields])
        cur.execute(f"""
            SELECT {sum_select}
            FROM prcp_data_basic
            WHERE data_date=%s AND coa_node_id IN ({placeholders})
              AND is_deleted=0
        """, [DATA_DATE] + child_ids)
        sums = cur.fetchone()

        # 加权平均
        cur.execute(f"""
            SELECT IFNULL(SUM(weighted_rate * current_balance), 0) AS wr_sum,
                   IFNULL(SUM(risk_weight * current_balance), 0) AS rw_sum,
                   IFNULL(SUM(current_balance), 0) AS total
            FROM prcp_data_basic
            WHERE data_date=%s AND coa_node_id IN ({placeholders})
              AND is_deleted=0
        """, [DATA_DATE] + child_ids)
        wr_sum, rw_sum, total = cur.fetchone()
        wr_avg = (wr_sum / total) if total else 0
        rw_avg = (rw_sum / total) if total else 0

        asf_rsf_val = 'ASF' if parent_code.startswith('ZX_L') else ('RSF' if parent_code.startswith('ZX_A') else None)

        set_clause = ', '.join([f'{f}=%s' for f in sum_fields])
        update_sql = f"""
            UPDATE prcp_data_basic
            SET {set_clause},
                weighted_rate=%s, risk_weight=%s,
                asf_rsf=%s, hqla_factor=%s,
                date_offset=0, offset_unit='D'
            WHERE coa_node_id=%s AND data_date=%s
        """
        params = list(sums) + [wr_avg, rw_avg, asf_rsf_val, None,
                                node_id_map[parent_code], DATA_DATE]
        cur.execute(update_sql, params)

    # L4 → L3（业务大类）
    for code in ['ZX_A010', 'ZX_A016', 'ZX_A023', 'ZX_A026', 'ZX_A027', 'ZX_A030',
                  'ZX_L031']:
        aggregate_basic_to_parent(code)
    print('L4 → L3 basic 汇总完成')

    # L3 → L2（币种分组）
    for code in ['ZX_A006', 'ZX_A007', 'ZX_L008', 'ZX_L009']:
        aggregate_basic_to_parent(code)
    print('L3 → L2 basic 汇总完成')

    # L2 → L1（汇总行）
    for code in ['ZX_A001', 'ZX_L003']:
        aggregate_basic_to_parent(code)
    print('L2 → L1 汇总完成（总资产/总负债）')

    # 生息资产（ZX_A002）= 总资产 - 非生息项
    cur.execute("""
        SELECT current_balance FROM prcp_data_basic
        WHERE coa_node_id=%s AND data_date=%s
    """, (node_id_map['ZX_A001'], DATA_DATE))
    total_asset_basic = cur.fetchone()[0] or 0
    cur.execute("""
        SELECT IFNULL(SUM(b2.current_balance), 0) FROM prcp_data_basic b2
        JOIN prcp_coa_node n2 ON n2.id=b2.coa_node_id
        WHERE n2.node_code IN ('ZX_A023', 'ZX_A030')
          AND b2.data_date=%s
    """, (DATA_DATE,))
    non_interest_basic = cur.fetchone()[0] or 0
    interest_asset_basic = total_asset_basic - non_interest_basic
    cur.execute("""
        UPDATE prcp_data_basic
        SET current_balance=%s, avg_balance=%s * 0.98
        WHERE coa_node_id=%s AND data_date=%s
    """, (interest_asset_basic, interest_asset_basic, node_id_map['ZX_A002'], DATA_DATE))

    # 计息负债（ZX_L004）= 总负债（无显式"非计息负债"节点）
    cur.execute("""
        SELECT current_balance FROM prcp_data_basic
        WHERE coa_node_id=%s AND data_date=%s
    """, (node_id_map['ZX_L003'], DATA_DATE))
    total_liab_basic = cur.fetchone()[0] or 0
    cur.execute("""
        UPDATE prcp_data_basic
        SET current_balance=%s, avg_balance=%s * 0.98
        WHERE coa_node_id=%s AND data_date=%s
    """, (total_liab_basic, total_liab_basic, node_id_map['ZX_L004'], DATA_DATE))
    print('生息资产/计息负债 basic 单独计算完成')

    # 3. 验证
    cur.execute("""
        SELECT n.node_code, n.node_name, n.node_level,
               b.current_balance, b.weighted_rate, b.risk_weight,
               b.asf_rsf, b.hqla_factor,
               (b.orig_m1 + b.orig_m2 + b.orig_m3 + b.orig_m6 + b.orig_m12) AS orig_short,
               (b.rem_m1 + b.rem_m2 + b.rem_m3 + b.rem_m6 + b.rem_m12) AS rem_short
        FROM prcp_data_basic b
        JOIN prcp_coa_node n ON n.id=b.coa_node_id
        WHERE n.scheme_id=%s AND b.data_date=%s AND b.date_offset=0 AND b.is_deleted=0
        ORDER BY n.node_level, n.sort_order
    """, (SCHEME_ID, DATA_DATE))
    print()
    print(f'验证 basic 节点数: {cur.rowcount}')
    for row in cur.fetchall():
        code, name, level, cb, wr, rw, asf, hqla, oshort, rshort = row
        cb_s = f'{cb:>12,.2f}' if cb else '           0'
        wr_s = f'{wr*100:.2f}%' if wr else '  0%'
        rw_s = f'{rw*100:.0f}%' if rw else ' 0%'
        print(f'  L{level} {code:<10} {name[:20]:<22} 余额={cb_s} 利率={wr_s:<7} RW={rw_s:<4} '
              f'ASF/RSF={asf or "-":<4} HQLA={hqla if hqla is not None else "-"} '
              f'短端orig={oshort:.0f} 短端rem={rshort:.0f}')


def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor()

    # 0. 读 ZXCOA_V1 节点 → id 映射
    cur.execute("""
        SELECT id, node_code FROM prcp_coa_node
        WHERE scheme_id=%s AND is_deleted=0
    """, (SCHEME_ID,))
    node_id_map = {code: nid for nid, code in cur.fetchall()}
    print(f'ZXCOA_V1 节点映射: {len(node_id_map)} 条')

    # 1. 插入 balance
    insert_balance_data(cur, node_id_map)

    # 2. 插入 basic
    insert_basic_data(cur, node_id_map)

    conn.commit()
    print()
    print('✓ 提交成功')

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
