# -*- coding: utf-8 -*-
"""
根据 LCR.xlsx 的当前余额数据，生成 prcp_data_basic 基础数据表 INSERT SQL。
- 数据日期：2025/12/31
- 方案：ZX_COA（scheme_id=1，57 节点）
- 桶分配原则（LCR 是 30 天到期流动性指标）：
  * 有余额的节点：orig_m1 = current_balance，rem_m1 = current_balance，其余桶 = 0
  * 无余额的汇总节点：current_balance = 0，所有桶 = 0
- 字段映射：
  * category：A/L/E（资产/负债/权益，按编码前缀判断）
  * hqla_factor：来自 LCR "分子折算系数"
  * asf_rsf：来自 LCR "分母折算系数"
  * calc_note：来自 LCR "LCR 规则说明"
  * parent_code：从 prcp_coa_node.path 解析上一层节点编码
"""
import openpyxl
import json
import sys

LCR_FILE = r'C:/银行经营/PRCP/docs/LCR.xlsx'
DATA_DATE = '2025-12-31'
SCHEME_ID = 1  # ZX_COA
OUTPUT_SQL = r'C:/银行经营/PRCP/docs/insert_basic_data_from_lcr.sql'


def load_nodes():
    """从 JSON 缓存读取 ZX_COA 节点（脚本生成的）"""
    import subprocess
    sql = "SELECT id, node_code, node_name, node_level, parent_id, path FROM prcp_coa_node WHERE scheme_id=1 AND is_deleted=0 ORDER BY sort_order"
    # 我们直接用 subprocess + ssh 调用 mysql
    # 但因为直接用 cat | ssh mysql 模式更可靠，这里返回 SQL 让外部执行
    return sql


def rate_for_node(code: str, name: str, hqla_factor, asf_rsf, category: str) -> float:
    """根据节点编码和 LCR 业务属性，返回年化加权平均利率（小数）
    - 资产/负债/权益分别有不同利率
    - LCR 30 天内到期 → 月化利息 = balance × rate / 12
    - 所有者权益/不计息资产 = 0
    """
    # 所有者权益
    if code.startswith('S03'):
        return 0.0
    # 现金类/非生息/公允计价（FVTPL）→ 不计息
    if '现金' in name or '非生息' in name or 'FVTPL类资产' in name:
        return 0.0
    # ---------- 资产端利率（A 类） ----------
    if category == 'A':
        # 国债/政策性金融债 AC（hqla_factor=1.0）
        if code in ('S010102010101', 'S010102010102', 'S010102010201', 'S010102010202'):
            return 0.025     # 2.5%
        # 公司债 FVTPL（hqla_factor=0.85）
        if code in ('S010102010103', 'S010102010203'):
            return 0.038     # 3.8%
        # 存款准备金（hqla_factor=1.0）
        if code == 'S010102040000':
            return 0.015     # 1.5%
        # 库存现金
        if code == 'S010103020100':
            return 0.0       # 0% (现金不计息)
        # 3.2.2 其它非生息
        if code == 'S010103020200':
            return 0.0
        # 对公一般贷款（流入 100%）
        if code == 'S010101010000':
            return 0.045     # 4.5%
        # 个人贷款
        if code == 'S010101020000':
            return 0.058     # 5.8%
        # 信用卡
        if code == 'S010101030000':
            return 0.150     # 15%
        # 票据贴现
        if code == 'S010101040000':
            return 0.032     # 3.2%
        # 非银贷款
        if code == 'S010101050000':
            return 0.048     # 4.8%
        # 结构化融资
        if code == 'S010102020000':
            return 0.050     # 5.0%
        # 同业资产（不含拆放非银）
        if code == 'S010102030000':
            return 0.035     # 3.5%
        # 外币贷款
        if code == 'S010201000000':
            return 0.055     # 5.5%
        # 外币债券
        if code == 'S010202010000':
            return 0.040     # 4.0%
        # 外币同业
        if code == 'S010202020000':
            return 0.045     # 4.5%
        # 外币非生息资产
        if code == 'S010203000000':
            return 0.0
        # FVTPL公司债不计入（HQLA=NULL 且 asf_rsf=NULL）
        if hqla_factor is None and asf_rsf is None and code == 'S010102010103':
            return 0.0
        # 汇总节点（level ≤ 3 无余额）→ 默认 0
        return 0.0
    # ---------- 负债端利率（L 类） ----------
    if category == 'L':
        # 对公活期存款（流出 48.5%）
        if code == 'S020101010100':
            return 0.005     # 0.5%
        # 对公定期存款（流出 100%）
        if code == 'S020101010200':
            return 0.022     # 2.2%
        # 零售活期存款（流出 8%）
        if code == 'S020101020100':
            return 0.003     # 0.3%
        # 零售定期存款（流出 100%）
        if code == 'S020101020200':
            return 0.018     # 1.8%
        # 同业活期拆入
        if code == 'S020102010100':
            return 0.018     # 1.8%
        # 货币市场债券回购（流出 25%）
        if code == 'S020102010200':
            return 0.025     # 2.5%
        # 同业存单 NCD
        if code == 'S020102010300':
            return 0.022     # 2.2%
        # 同业存款
        if code == 'S020102010400':
            return 0.019     # 1.9%
        # 票据转贴现回购
        if code == 'S020102010500':
            return 0.020     # 2.0%
        # 公开市场回购（买断，流出 0%）
        if code == 'S020102020100':
            return 0.015     # 1.5%
        # MLF
        if code == 'S020102020200':
            return 0.025     # 2.5%
        # 结构性货币政策工具
        if code == 'S020102020300':
            return 0.018     # 1.8%
        # 票据再贴现回购
        if code == 'S020102020400':
            return 0.015     # 1.5%
        # 外币存款
        if code == 'S020201000000':
            return 0.045     # 4.5%
        # 外币市场化负债
        if code == 'S020202000000':
            return 0.040     # 4.0%
        # 汇总节点（level ≤ 3 无余额）→ 默认 0
        return 0.0
    return 0.0


def build_sql():
    """构建 INSERT SQL（无密码，无连接），纯文件输出"""
    # 1. 读 LCR.xlsx
    wb = openpyxl.load_workbook(LCR_FILE, data_only=True)
    ws = wb['LCR项目明细']
    lcr_map = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        code = row[0]
        if not code:
            continue
        lcr_map[code] = {
            'name': row[1],
            'is_leaf': (row[2] == '是'),
            'current_balance': float(row[3]) if row[3] is not None else 0.0,
            'hqla_factor': float(row[5]) if isinstance(row[5], (int, float)) else None,
            'asf_rsf_factor': float(row[8]) if isinstance(row[8], (int, float)) else None,
            'calc_note': row[13] or None,
        }
    print(f'LCR 明细读取: {len(lcr_map)} 条')

    # 2. 加载 ZX_COA 节点（TSV 由外部生成）
    nodes_raw = []
    with open(r'C:/银行经营/PRCP/docs/zx_coa_nodes.tsv', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    header = lines[0].rstrip('\n').split('\t')
    for line in lines[1:]:
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 6:
            continue
        nodes_raw.append({
            'id': int(parts[0]),
            'node_code': parts[1],
            'node_name': parts[2],
            'node_level': int(parts[3]),
            'parent_id': int(parts[4]) if parts[4] != 'NULL' else None,
            'path': parts[5],
        })

    # 解析 parent_code
    id_to_code = {n['id']: n['node_code'] for n in nodes_raw}
    for n in nodes_raw:
        n['parent_code'] = id_to_code.get(n['parent_id']) if n['parent_id'] else None

    print(f'ZX_COA 节点数: {len(nodes_raw)}')

    # 3. 桶列表（**必须按表的实际列顺序**）
    # 表中的实际顺序：orig_m1..orig_m12, orig_y10, orig_y15, orig_y20, orig_y30, orig_m13..orig_m60
    #                   rem_m1..rem_m12,   rem_y10,  rem_y15,  rem_y20,  rem_y30,  rem_m13..rem_m60
    def make_bucket_order(prefix):
        cols = []
        # 前 12 个月桶
        for i in range(1, 13):
            cols.append(f'{prefix}_m{i}')
        # 4 个长端桶
        for y in (10, 15, 20, 30):
            cols.append(f'{prefix}_y{y}')
        # 后 48 个月桶
        for i in range(13, 61):
            cols.append(f'{prefix}_m{i}')
        return cols

    orig_cols = make_bucket_order('orig')   # 64 列
    rem_cols  = make_bucket_order('rem')    # 64 列
    all_bucket_cols = orig_cols + rem_cols  # 128 列

    # 元数据列（不含 id, created_at, updated_at）
    meta_cols = [
        'data_date', 'coa_node_id', 'node_code', 'node_name', 'node_level',
        'parent_code', 'is_leaf', 'category',
        'date_offset', 'offset_unit',
        'asf_rsf', 'hqla_factor', 'current_balance', 'avg_balance',
        'weighted_rate', 'interest_amount', 'risk_weight', 'calc_note',
        'is_deleted', 'created_by', 'updated_by',
    ]
    all_cols = meta_cols + all_bucket_cols
    print(f'总列数: {len(all_cols)} (元数据 {len(meta_cols)} + 桶列 {len(all_bucket_cols)})')
    print(f'  元数据列: {meta_cols}')
    print(f'  orig 列首 5: {orig_cols[:5]} ... 末 5: {orig_cols[-5:]}')
    print(f'  rem  列首 5: {rem_cols[:5]} ... 末 5: {rem_cols[-5:]}')

    # 4. 生成 SQL
    sql_lines = []
    sql_lines.append("-- ============================================================")
    sql_lines.append("-- prcp_data_basic 基础数据（基于 LCR.xlsx 当前余额）")
    sql_lines.append(f"-- 数据日期: {DATA_DATE}")
    sql_lines.append(f"-- 方案: ZX_COA (scheme_id={SCHEME_ID})")
    sql_lines.append(f"-- 节点数: {len(nodes_raw)}")
    sql_lines.append("-- 桶分配：当前余额 → orig_m1 + rem_m1（30 天内到期）")
    sql_lines.append("-- ============================================================")
    sql_lines.append("")
    sql_lines.append("SET NAMES utf8mb4;")
    sql_lines.append(f"DELETE FROM prcp_data_basic WHERE data_date = '{DATA_DATE}';")
    sql_lines.append("")

    col_list = ', '.join([f'`{c}`' for c in all_cols])
    sql_lines.append(f"INSERT INTO prcp_data_basic ({col_list}) VALUES")

    value_rows = []
    for n in nodes_raw:
        lcr = lcr_map.get(n['node_code'])
        if lcr is None:
            print(f'WARN: 节点 {n["node_code"]} 在 LCR 中未找到，跳过')
            continue

        # category
        prefix2 = n['node_code'][1:3]
        if prefix2 == '01':
            category = 'A'
        elif prefix2 == '02':
            category = 'L'
        elif prefix2 == '03':
            category = 'E'
        else:
            category = 'X'

        asf_rsf = lcr['asf_rsf_factor']
        hqla_f = lcr['hqla_factor']
        balance = lcr['current_balance']

        # 加权利率（基于 LCR 业务规则推断）
        rate = rate_for_node(n['node_code'], n['node_name'], hqla_f, asf_rsf, category)
        # 利息收支（月化）：
        #   - 资产 → 利息收入（正数）
        #   - 负债 → 利息支出（负数）
        #   - 权益 → 0
        # LCR 30 天内到期 → 月化利息 = balance × rate / 12
        if category == 'A':
            interest = balance * rate / 12.0
        elif category == 'L':
            interest = -(balance * rate / 12.0)   # 负数表示支出
        else:
            interest = 0.0
        # 风险权重（资产 100%/50%/0%，负债/权益 0%）
        # Level 1 HQLA（国债/政策性金融债/准备金/现金）风险权重 0；其他资产 1.0
        level1_codes = {
            'S010102010101', 'S010102010102',  # 国债/政金 AC + FVOCI
            'S010102010201', 'S010102010202',
            'S010102040000',                       # 存款准备金
            'S010103020100',                       # 库存现金
        }
        if category == 'A':
            risk_weight = 0.0 if n['node_code'] in level1_codes else 1.0
        else:
            risk_weight = 0.0

        # 构建值列表
        vals = []
        vals.append(f"'{DATA_DATE}'")           # data_date
        vals.append(str(n['id']))                # coa_node_id
        vals.append(f"'{n['node_code']}'")       # node_code
        vals.append(f"'{n['node_name']}'")       # node_name
        vals.append(str(n['node_level']))        # node_level
        if n.get('parent_code'):
            vals.append(f"'{n['parent_code']}'")
        else:
            vals.append("NULL")
        vals.append('1' if lcr['is_leaf'] else '0')  # is_leaf
        vals.append(f"'{category}'")             # category
        vals.append('0')                          # date_offset
        vals.append("'D'")                       # offset_unit
        vals.append(str(asf_rsf) if asf_rsf is not None else 'NULL')  # asf_rsf
        vals.append(str(hqla_f) if hqla_f is not None else 'NULL')    # hqla_factor
        vals.append(f"{balance:.4f}")            # current_balance
        vals.append(f"{balance:.4f}")            # avg_balance
        vals.append(f"{rate:.6f}")               # weighted_rate（6 位小数）
        vals.append(f"{interest:.4f}")           # interest_amount
        vals.append(f"{risk_weight:.6f}")        # risk_weight
        note = (lcr['calc_note'] or '').replace("'", "\\'")
        vals.append(f"'{note}'" if note else "NULL")  # calc_note
        vals.append('0')                          # is_deleted
        vals.append('1')                          # created_by
        vals.append('1')                          # updated_by

        # 桶 128 列（按 orig_cols + rem_cols 顺序）
        for col in all_bucket_cols:
            # col 是 'orig_m1' 或 'rem_m1' 等
            # 只在 m1 上放余额
            bucket_name = col.split('_', 1)[1]  # 'm1' or 'y10'
            if bucket_name == 'm1':
                vals.append(f"{balance:.4f}")
            else:
                vals.append('0.0000')

        value_rows.append('  (' + ', '.join(vals) + ')')

    sql_lines.append(',\n'.join(value_rows) + ';')
    sql_lines.append("")

    # 5. 验证查询
    sql_lines.append("-- ============================================================")
    sql_lines.append("-- 验证")
    sql_lines.append("-- ============================================================")
    sql_lines.append(f"SELECT COUNT(*) AS total_cnt, SUM(current_balance) AS total_balance")
    sql_lines.append(f"FROM prcp_data_basic WHERE data_date = '{DATA_DATE}';")
    sql_lines.append("")
    sql_lines.append(f"SELECT category, COUNT(*) AS cnt, SUM(current_balance) AS total")
    sql_lines.append(f"FROM prcp_data_basic WHERE data_date = '{DATA_DATE}' GROUP BY category;")
    sql_lines.append("")
    sql_lines.append(f"SELECT node_level, COUNT(*) AS cnt, SUM(current_balance) AS total")
    sql_lines.append(f"FROM prcp_data_basic WHERE data_date = '{DATA_DATE}' GROUP BY node_level ORDER BY node_level;")
    sql_lines.append("")
    sql_lines.append(f"SELECT node_code, node_name, is_leaf, current_balance, hqla_factor, asf_rsf")
    sql_lines.append(f"FROM prcp_data_basic WHERE data_date = '{DATA_DATE}' AND current_balance > 0")
    sql_lines.append("ORDER BY node_code LIMIT 10;")

    # 写入
    with open(OUTPUT_SQL, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_lines))

    print(f'\nSQL 已生成: {OUTPUT_SQL}')
    print(f'INSERT 行数: {len(value_rows)}')
    print(f'文件大小: {sum(len(s) for s in sql_lines):,} 字节')


if __name__ == '__main__':
    build_sql()