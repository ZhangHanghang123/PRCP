"""根据 ZXCOA.xlsx 生成账户册方案，插入 prcp_db

设计：
- scheme_code='ZXCOA_V1', scheme_name='账户册总表_v7（ZXCOA）'
- 树形结构：
    L1 (5个汇总行): 总资产 / 生息资产 / 总负债 / 计息负债 / 所有者权益
    L2: (一)人民币/(二)外币 币种分组
    L3: 1./2./3. 业务大类
    L4: 1.1./1.2./... 业务小类
    L5: 1.1.1/2.1.1/... 子类
- node_code 用 ZX_<category><seq> 形式
- path 用 /L1_xxx/L2_xxx/.../ 格式（与 COA_V6 一致）
"""
import re
import pymysql

DB = dict(host='127.0.0.1', port=3306, user='almd', password='Almd@2026',
          database='prcp_db', charset='utf8mb4', autocommit=False)

# ZXCOA.xlsx 解析结果（按 row 顺序）
# (name, category, caliber)
ZXCOA_ROWS = [
    ('总资产', 'ASSET', None),
    ('生息资产', 'ASSET', None),
    ('(一)人民币小计', 'ASSET', '1.境内人民币各项贷款'),
    ('1.境内人民币各项贷款', 'ASSET', '1.1.对公一般贷款'),
    ('1.1.对公一般贷款', 'ASSET', '121、122、123、124、141、142'),
    ('1.2.个人贷款', 'ASSET', '131、132、133、134、135'),
    ('1.3.信用卡贷款', 'ASSET', '136'),
    ('1.4.票据贴现', 'ASSET', '125、126'),
    ('1.5.非银贷款', 'ASSET', '115、116(剔除11602)'),
    ('2.人民币非信贷类业务', 'ASSET', '2 . 1 . 债券投资'),
    ('2.1.债券投资', 'ASSET', '151、152'),
    ('2.1.1金市自营债券', 'ASSET', '区分金市自营和司库债券条件用投资组合\nINVES   COMB区分，其中司库债券的投资组合'),
    ('2.1.2司库债券', 'ASSET', None),
    ('2.2.结构化融资', 'ASSET', '155'),
    ('2.3.同业资产(不含拆放非银)', 'ASSET', '112、113、114、119、150、11602'),
    ('2.4.存款准备金', 'ASSET', '110'),
    ('3.人民币非生息资产', 'ASSET', '3 . 1 .FV TPL类资产'),
    ('3.1.FVTPL类资产', 'ASSET', '154、156'),
    ('3.2.其他非生息资产', 'ASSET', '总资产-1.境内人民币各项贷款-2.人民币非'),
    ('(二)外币小计(美元)', 'ASSET', '1.外币贷款'),
    ('1.外币贷款', 'ASSET', '121、122、123、124、141、142'),
    ('2.外币非信贷资产', 'ASSET', '2 . 1 . 外币债券'),
    ('2.1.外币债券', 'ASSET', '151、152'),
    ('2.2.同业资产', 'ASSET', '112、113、114、119、150、11602'),
    ('3.外币非生息资产', 'ASSET', None),
    ('总负债', 'LIABILITY', '报表获取'),
    ('计息负债', 'LIABILITY', None),
    ('(一)人民币小计', 'LIABILITY', '汇总：'),
    ('1.境内人民币自营存款', 'LIABILITY', '汇总：'),
    ('1.1.对公存款', 'LIABILITY', '汇总：'),
    ('1.1.1对公活期存款', 'LIABILITY', '201金融机构活期存款'),
    ('1.1.2对公定期存款', 'LIABILITY', '202金融机构通知存款'),
    ('1.2.零售存款', 'LIABILITY', '汇总：'),
    ('1.2.1零售活期存款', 'LIABILITY', '221个人活期存款'),
    ('1.2.2零售定期存款', 'LIABILITY', '222个人通知存款'),
    ('2.人民币市场化负债', 'LIABILITY', None),
    ('(二)外币小计(美元)', 'LIABILITY', '汇总：且币种为外币折美元'),
    ('1.外币存款', 'LIABILITY', None),
    ('2.外币市场化负债', 'LIABILITY', None),
    ('所有者权益', 'EQUITY', '总资产-总负债'),
]

# 推断层级（基于名称前缀规则）
def infer_level(name: str) -> int:
    """根据名称前缀规则推断 ZXCOA 节点层级"""
    s = name.strip()
    # 1.1.1 / 2.1.1 / 1.1.2 → L5（4 个层级点 + 子级 = 3 个点）
    # L5 = 3 个点: 1.1.1xxx
    # L4 = 2 个点: 1.1.xxx
    # L3 = 1 个点: 1.xxx
    # L2 = (一)/(二) → 中间分组
    # L1 = 汇总行（总资产/生息资产/总负债/计息负债/所有者权益）
    if re.match(r'^[(（]', s):
        return 2  # (一)/(二) 币种分组
    if re.match(r'^\d+\.\d+\.\d+\.\d+', s):
        return 6
    if re.match(r'^\d+\.\d+\.\d+', s):  # 1.1.1 / 2.1.1
        return 5
    if re.match(r'^\d+\.\d+', s):  # 1.1 / 1.2 / 2.1
        return 4
    if re.match(r'^\d+\.', s):  # 1. / 2. / 3.
        return 3
    return 1  # 汇总行：总资产/生息资产/总负债/计息负债/所有者权益

# 推断 L1 大类（按 category 顺序）
# 资产 → 10, 负债 → 20, 权益 → 30
def category_to_root_sort(category: str, idx_in_category: int) -> int:
    """返回 (root_sort_order, parent_name)
    总资产=10, 生息资产=11, 总负债=20, 计息负债=21, 所有者权益=30
    """
    return {'ASSET': 10, 'LIABILITY': 20, 'EQUITY': 30}.get(category, 99) + idx_in_category


def build_tree():
    """构建 ZXCOA 树形节点列表"""
    # 1. 标记 L1（汇总行）
    # 总资产、生息资产 在 category=资产 里按顺序 10、11
    # 总负债、计息负债 在 category=负债 里按顺序 20、21
    # 所有者权益 = 30
    nodes = []  # (name, category, level, parent_idx_or_None, sort_in_level, caliber)
    # 第一次扫描：识别所有 L1 汇总行（按 category + 顺序）
    cat_l1_seq = {}  # category -> 当前序号
    cat_summary_count = {'ASSET': 0, 'LIABILITY': 0, 'EQUITY': 0}

    # 第一遍：识别 L1
    l1_nodes = []
    l1_by_name = {}
    for i, (name, cat, caliber) in enumerate(ZXCOA_ROWS):
        lvl = infer_level(name)
        if lvl == 1:
            cat_summary_count[cat] += 1
            sort_order = {'ASSET': 10, 'LIABILITY': 20, 'EQUITY': 30}[cat] + cat_summary_count[cat]
            l1_nodes.append({
                'idx': i, 'name': name, 'category': cat, 'level': 1,
                'parent_idx': None, 'sort_order': sort_order, 'caliber': caliber,
            })
            l1_by_name[name] = len(l1_nodes) - 1

    # 第二遍：识别 L2（(一)/(二) 中间分组）
    # L2 的 parent 是同 category 的第一个 L1 汇总行
    # 资产：(一)人民币 → 总资产, (二)外币 → 总资产
    # 负债：(一)人民币 → 总负债, (二)外币 → 总负债
    l2_nodes = []
    for i, (name, cat, caliber) in enumerate(ZXCOA_ROWS):
        lvl = infer_level(name)
        if lvl == 2:
            # 找父级：同 category 的总资产/总负债
            parent_name = '总资产' if cat == 'ASSET' else ('总负债' if cat == 'LIABILITY' else None)
            parent_idx = None
            for ln in l1_nodes:
                if ln['name'] == parent_name and ln['category'] == cat:
                    parent_idx = ln['idx']
                    break
            l2_nodes.append({
                'idx': i, 'name': name, 'category': cat, 'level': 2,
                'parent_idx': parent_idx,
                'sort_order': 1 if '一' in name else 2,  # 人民币=1, 外币=2
                'caliber': caliber,
            })

    # 第三遍：识别 L3/L4/L5（按 数字+点 规则）
    # L3 (1./2./3.) → 父级 = 当前 category 的上一个 L2
    # L4 (1.1./2.1.) → 父级 = 当前 category 上一个 L3
    # L5 (1.1.1/2.1.1) → 父级 = 当前 category 上一个 L4
    detail_nodes = []
    last_l2_idx = {'ASSET': None, 'LIABILITY': None}
    last_l3_idx = {'ASSET': None, 'LIABILITY': None}
    last_l4_idx = {'ASSET': None, 'LIABILITY': None}
    for i, (name, cat, caliber) in enumerate(ZXCOA_ROWS):
        lvl = infer_level(name)
        if lvl >= 3:
            if lvl == 3:
                parent_idx = last_l2_idx[cat]
                last_l3_idx[cat] = i
                last_l4_idx[cat] = None
                m = re.match(r'^(\d+)\.', name)
                sort_order = int(m.group(1)) if m else 99
            elif lvl == 4:
                parent_idx = last_l3_idx[cat]
                last_l4_idx[cat] = i
                m = re.match(r'^\d+\.(\d+)\.', name)
                sort_order = int(m.group(1)) if m else 99
            elif lvl == 5:
                parent_idx = last_l4_idx[cat]
                m = re.match(r'^\d+\.\d+\.(\d+)', name)
                sort_order = int(m.group(1)) if m else 99
            else:
                parent_idx = None
                sort_order = 99
            detail_nodes.append({
                'idx': i, 'name': name, 'category': cat, 'level': lvl,
                'parent_idx': parent_idx, 'sort_order': sort_order, 'caliber': caliber,
            })
        elif lvl == 2:
            last_l2_idx[cat] = i
            last_l3_idx[cat] = None
            last_l4_idx[cat] = None

    all_nodes = l1_nodes + l2_nodes + detail_nodes
    return all_nodes


def gen_node_code(node, idx_in_scheme):
    """生成 node_code：ZX_<category><seq>"""
    cat_prefix = {'ASSET': 'A', 'LIABILITY': 'L', 'EQUITY': 'E'}[node['category']]
    return f"ZX_{cat_prefix}{idx_in_scheme:03d}"


def insert_to_db():
    conn = pymysql.connect(**DB)
    cur = conn.cursor()

    # 1. 创建方案
    cur.execute("SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZXCOA_V1' AND is_deleted=0")
    if cur.fetchone():
        print('方案 ZXCOA_V1 已存在，跳过创建')
        cur.execute("SELECT id FROM prcp_coa_scheme WHERE scheme_code='ZXCOA_V1' AND is_deleted=0")
        scheme_id = cur.fetchone()[0]
    else:
        cur.execute(
            """INSERT INTO prcp_coa_scheme (scheme_code, scheme_name, description, status, node_count)
               VALUES ('ZXCOA_V1', '账户册总表_v7（ZXCOA）', 'ZXCOA.xlsx 导入，5 层结构（L1汇总行/L2币种/L3业务大类/L4业务小类/L5子类），共 41 节点', 'ACTIVE', 0)""",
        )
        scheme_id = cur.lastrowid
        print(f'创建方案 ZXCOA_V1, id={scheme_id}')

    # 2. 清空旧节点（idempotent）
    cur.execute("DELETE FROM prcp_coa_node WHERE scheme_id=%s", (scheme_id,))
    print(f'清空 scheme_id={scheme_id} 的旧节点')

    # 3. 构建树
    nodes = build_tree()
    print(f'解析得到 {len(nodes)} 个节点')

    # 4. 先插入所有节点，拿到 id，然后建立 parent 关系
    id_map = {}  # row_idx_in_zxcoa -> node_id
    for seq, n in enumerate(nodes, start=1):
        node_code = gen_node_code(n, seq)
        cur.execute(
            """INSERT INTO prcp_coa_node
               (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description)
               VALUES (%s, %s, %s, %s, %s, %s, '', %s, 'ACTIVE', %s)""",
            (scheme_id, node_code, n['name'], None, n['level'],
             'SUMMARY' if n['level'] <= 2 else 'BUSINESS',
             n['sort_order'], n['caliber']),
        )
        id_map[n['idx']] = cur.lastrowid

    # 5. 第二遍：更新 parent_id 和 path
    for n in nodes:
        parent_id = id_map.get(n['parent_idx']) if n['parent_idx'] is not None else None
        cur.execute(
            "UPDATE prcp_coa_node SET parent_id=%s WHERE id=%s",
            (parent_id, id_map[n['idx']]),
        )

    # 6. 重建 path（用 node_code 路径，类似 COA_V6）
    # 第一遍：更新 L1（parent_id=NULL）的 path
    cur.execute("SELECT id, node_code FROM prcp_coa_node WHERE scheme_id=%s AND parent_id IS NULL", (scheme_id,))
    for nid, code in cur.fetchall():
        cur.execute("UPDATE prcp_coa_node SET path=%s WHERE id=%s", (f"/L1_{code}/", nid))

    # 反复迭代直到所有 path 都有值（最多迭代 10 层）
    # 关键：每遍只处理 "parent.path 已经有完整值" 的节点
    for _ in range(10):
        cur.execute("""
            SELECT n.id, n.node_code, p.path
            FROM prcp_coa_node n
            JOIN prcp_coa_node p ON n.parent_id = p.id
            WHERE n.scheme_id=%s AND (n.path IS NULL OR n.path='')
              AND p.path IS NOT NULL AND p.path != ''
        """, (scheme_id,))
        rows = cur.fetchall()
        if not rows:
            break
        for nid, code, ppath in rows:
            cur.execute("UPDATE prcp_coa_node SET path=%s WHERE id=%s", (f"{ppath}{code}/", nid))
        print(f'  path iteration: {len(rows)} nodes updated')

    # 7. 更新 node_count
    cur.execute("UPDATE prcp_coa_scheme SET node_count=%s WHERE id=%s", (len(nodes), scheme_id))

    conn.commit()
    print(f'✓ 提交成功，方案 ZXCOA_V1 (id={scheme_id}) 共 {len(nodes)} 个节点')

    # 8. 验证
    cur.execute("""
        SELECT node_level, COUNT(*) FROM prcp_coa_node
        WHERE scheme_id=%s AND is_deleted=0 GROUP BY node_level ORDER BY node_level
    """, (scheme_id,))
    print('层级分布:')
    for lvl, cnt in cur.fetchall():
        print(f'  L{lvl}: {cnt} 个')

    cur.execute("""
        SELECT n.node_code, n.node_name, n.node_level, n.path, n.parent_id
        FROM prcp_coa_node n
        WHERE n.scheme_id=%s AND n.is_deleted=0
        ORDER BY n.sort_order, n.path LIMIT 50
    """, (scheme_id,))
    print()
    print('前 20 节点:')
    for r in cur.fetchall()[:20]:
        print(f'  {r[0]:<15} {r[1][:25]:<27} L{r[2]} parent={r[4]} path={r[3]}')

    cur.close()
    conn.close()


if __name__ == '__main__':
    insert_to_db()
