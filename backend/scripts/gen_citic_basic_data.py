#!/usr/bin/env python3
"""
为 PRCP 方案 ZX_CITIC_2026 生成 prcp_data_basic 基础数据
（中信银行 2026 H1 模拟数据）

策略：
  1. 节点规模：参考中信银行 2026 H1 公开数据（总资产 ~10.8 万亿）
  2. 利率/风险权重：按业务类型给定（参考 LPR + Basel III）
  3. 64+64 桶分布：复用 init_basic_from_balance.py 的 distribute_* 函数
  4. ASF/RSF：负债 ASF、资产 RSF
  5. HQLA：按节点名启发式

输出：
  - gen_citic_basic_2026h1.sql（INSERT 语句）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from init_basic_from_balance import (
    BUCKETS, distribute_asset_orig, distribute_asset_rem,
    distribute_liab_orig, distribute_liab_rem,
    _empty, infer_asf_rsf, infer_hqla,
)

# ---- 中信银行 2026 H1 节点定义 ----
# 单位：金额（亿元，人民币）、年化利率（%）、风险权重（0~1.5）、是否末级
# 基于中信银行 2025 年报 + 2026 H1 估算

NODE_DEFS = [
    # ===== 资产侧 =====
    ("S01000000000000", "总资产", 1080000, 3.40, 0.00, 0, "ASSET",  ""),       # 集团聚合，不参与计算
    ("S01010000000000", "（一）人民币小计", 1000000, 3.45, 0.00, 0, "ASSET", ""),
    ("S01010100000000", "1. 境内人民币各项贷款", 550000, 4.30, 0.00, 0, "ASSET", ""),
    ("S01010101000000", "1.1. 对公一般贷款", 245000, 4.10, 1.00, 1, "ASSET", ""),       # 普通对公：RW 100%
    ("S01010102000000", "1.2. 个人贷款", 175000, 3.95, 0.55, 1, "ASSET", ""),           # 含按揭 50% + 消费贷 75%
    ("S01010103000000", "1.3. 信用卡贷款", 48000, 12.0, 0.75, 1, "ASSET", ""),           # 信用卡：RW 75%
    ("S01010104000000", "1.4. 票据贴现", 32000, 2.50, 1.00, 1, "ASSET", ""),             # 普通承兑
    ("S01010105000000", "1.5. 非银贷款", 50000, 4.50, 1.00, 1, "ASSET", ""),             # 非银金融机构
    ("S01010200000000", "2. 人民币非信贷类业务", 400000, 2.80, 0.00, 0, "ASSET", ""),
    ("S01010201000000", "2.1. 债券投资", 250000, 2.65, 0.00, 0, "ASSET", ""),
    ("S010102010100", "2.1.1 金市自营债券", 150000, 2.55, 0.00, 1, "ASSET", ""),         # 国债+政策性
    ("S010102010200", "2.1.2 司库债券", 100000, 2.85, 0.25, 1, "ASSET", ""),             # 信用债
    ("S01010202000000", "2.2. 结构化融资", 50000, 3.80, 1.00, 1, "ASSET", ""),
    ("S01010203000000", "2.3. 同业资产（不含拆放非银）", 70000, 2.30, 0.20, 1, "ASSET", ""),
    ("S01010204000000", "2.4. 存款准备金", 30000, 1.62, 0.00, 1, "ASSET", ""),           # 法定存款准备金
    ("S01010300000000", "3. 人民币非生息资产", 50000, 0.00, 0.00, 0, "ASSET", ""),
    ("S01010301000000", "3.1. FVTPL类资产", 30000, 3.20, 1.00, 1, "ASSET", ""),          # FVTPL
    ("S01010302000000", "3.2. 其他非生息资产", 20000, 0.00, 0.50, 1, "ASSET", ""),
    ("S01020000000000", "（二）外币小计（美元）", 80000, 4.20, 0.00, 0, "ASSET", ""),
    ("S01020100000000", "1. 外币贷款", 40000, 4.80, 1.00, 1, "ASSET", ""),
    ("S01020200000000", "2. 外币非信贷资产", 30000, 3.80, 0.00, 0, "ASSET", ""),
    ("S01020201000000", "2.1. 外币债券", 20000, 3.50, 0.50, 1, "ASSET", ""),
    ("S01020202000000", "2.2. 同业资产", 10000, 4.30, 0.20, 1, "ASSET", ""),
    ("S01020300000000", "3. 外币非生息资产", 10000, 0.00, 0.50, 1, "ASSET", ""),
    # ===== 负债侧 =====
    ("S02000000000000", "总负债", 980000, 1.85, 0.00, 0, "LIAB",    ""),
    ("S02010000000000", "（一）人民币小计", 920000, 1.82, 0.00, 0, "LIAB", ""),
    ("S02010100000000", "1. 境内人民币自营存款", 800000, 1.65, 0.00, 0, "LIAB", ""),
    ("S02010101000000", "1.1. 对公存款", 480000, 1.55, 0.00, 0, "LIAB", ""),
    ("S020101010100", "1.1.1 对公活期存款", 260000, 0.20, 0.00, 1, "LIAB", ""),
    ("S020101010200", "1.1.2 对公定期存款", 220000, 1.85, 0.00, 1, "LIAB", ""),
    ("S02010102000000", "1.2. 零售存款", 320000, 1.50, 0.00, 0, "LIAB", ""),
    ("S020101020100", "1.2.1 零售活期存款", 120000, 0.20, 0.00, 1, "LIAB", ""),
    ("S020101020200", "1.2.2 零售定期存款", 200000, 1.95, 0.00, 1, "LIAB", ""),
    ("S02010200000000", "2. 人民币市场化负债", 120000, 2.50, 0.00, 1, "LIAB", ""),
    ("S02020000000000", "（二）外币小计（美元）", 60000, 2.40, 0.00, 0, "LIAB", ""),
    ("S02020100000000", "1. 外币存款", 40000, 1.80, 0.00, 1, "LIAB", ""),
    ("S02020200000000", "2. 外币市场化负债", 20000, 3.50, 0.00, 1, "LIAB", ""),
    # ===== 权益侧 =====
    ("S03000000000000", "所有者权益", 100000, 0.00, 0.00, 1, "EQUITY", ""),
]

DATA_DATE = "2026-06-30"   # 中信银行 2026 H1 报告日
USER_ID = 1

# 总金额合计校验（应近似匹配上面数据，单位亿元）
# 资产侧期望 ≈ 4.5 万亿元 ≈ 450,000 亿元；负债侧期望 ≈ 100 万亿元
total_asset_yi = sum(amt for code, _, amt, *_ in NODE_DEFS if code.startswith("S01"))
total_liab_yi = sum(amt for code, _, amt, *_ in NODE_DEFS if code.startswith("S02"))
assert total_asset_yi > 1_000_000, f"资产侧金额异常: {total_asset_yi} 亿元"
assert total_liab_yi > 800_000, f"负债侧金额异常: {total_liab_yi} 亿元"

# 集团父节点（is_leaf=0）的金额 = 子节点合计（脚本层校验）
def validate_totals():
    """打印每个父节点的子节点合计，便于人工对照"""
    by_parent = {}
    for code, name, amt, rate, rw, is_leaf, cat, _ in NODE_DEFS:
        if code.startswith("S01") and len(code) > 14:
            parent_code = code[:12] + "00000000" if len(code) == 14 else code[:14] + "000000"
            # 简化：取前 4 段
            pc = code[:4] + "000000000000"
            by_parent.setdefault(pc, []).append((code, amt))
    return by_parent


def build_basic_for_node(code: str, name: str, amt_yi: float, rate_pct: float,
                         risk_w: float, is_leaf: int, category: str):
    """为一个节点构造 64+64 桶 + 元数据"""
    # 单位换算：亿元 → 元
    amt_yuan = amt_yi * 1e8

    # 桶分配
    if category == "ASSET":
        if is_leaf:
            orig = distribute_asset_orig(name, amt_yuan)
            rem = distribute_asset_rem(name, amt_yuan)
        else:
            # 父节点：合计为子节点，桶分布也用启发式
            orig = distribute_asset_orig(name, amt_yuan)
            rem = distribute_asset_rem(name, amt_yuan)
    elif category == "LIAB":
        if is_leaf:
            orig = distribute_liab_orig(name, amt_yuan)
            rem = distribute_liab_rem(name, amt_yuan)
        else:
            orig = distribute_liab_orig(name, amt_yuan)
            rem = distribute_liab_rem(name, amt_yuan)
    else:
        # EQUITY 权益无期限分布
        orig = _empty()
        rem = _empty()

    asf_rsf = infer_asf_rsf(category) if is_leaf else ""
    hqla_factor = infer_hqla(name) if is_leaf else 0.0

    # interest_amount：年化利率 × 余额 / 12（单月利息近似）
    monthly_interest = round(amt_yuan * rate_pct / 100 / 12, 4)

    return {
        "orig": orig,
        "rem": rem,
        "asf_rsf": asf_rsf,
        "hqla_factor": hqla_factor,
        "current_balance": round(amt_yuan, 4),
        "avg_balance": round(amt_yuan, 4),
        "weighted_rate": rate_pct / 100,   # 存为小数（0.041 = 4.1%）
        "interest_amount": monthly_interest,
        "risk_weight": risk_w,
    }


def main():
    lines = []
    lines.append("-- PRCP ZX_CITIC_2026 prcp_data_basic 数据")
    lines.append(f"-- 中信银行 2026 H1 模拟数据（{DATA_DATE}）")
    lines.append("-- 38 个节点 × 1 月 = 38 行")
    lines.append("")
    lines.append("SET NAMES utf8mb4;")
    import os
    target_scheme_id = int(os.environ.get('CITIC_SCHEME_ID', 8))
    lines.append(f"SET @scheme_id := {target_scheme_id};")
    lines.append("")
    lines.append("-- 0) 幂等检查 + 清理已存在数据")
    lines.append("SELECT IF(COUNT(*)>0, CONCAT('EXISTS:', COUNT(*)), 'OK') AS status")
    lines.append("FROM prcp_data_basic b")
    lines.append("JOIN prcp_coa_node n ON b.coa_node_id=n.id")
    lines.append("WHERE n.scheme_id=@scheme_id AND b.is_deleted=0;")
    lines.append("")
    lines.append("DELETE b FROM prcp_data_basic b")
    lines.append("JOIN prcp_coa_node n ON b.coa_node_id=n.id")
    lines.append("WHERE n.scheme_id=@scheme_id AND b.data_date='2026-06-30';")
    lines.append("")
    lines.append("-- 1) 取 38 个节点的 prcp_coa_node.id")
    lines.append("DROP TEMPORARY TABLE IF EXISTS _citic_nodes;")
    lines.append("CREATE TEMPORARY TABLE _citic_nodes (")
    lines.append("  code VARCHAR(32) PRIMARY KEY,")
    lines.append("  name VARCHAR(64),")
    lines.append("  id BIGINT NOT NULL,")
    lines.append("  level INT,")
    lines.append("  is_leaf INT,")
    lines.append("  category VARCHAR(16),")
    lines.append("  parent_code VARCHAR(32)")
    lines.append(") ENGINE=MEMORY;")
    lines.append("")
    lines.append("INSERT INTO _citic_nodes (code, name, id, level, is_leaf, category, parent_code)")
    lines.append("SELECT n.node_code, n.node_name, n.id, n.node_level,")
    lines.append("       IF(n.node_type LIKE '%LEAF', 1, 0),")
    lines.append("       IF(n.node_type LIKE 'ASSET%', 'ASSET', IF(n.node_type LIKE 'LIAB%', 'LIAB', IF(n.node_type LIKE 'EQUITY%', 'EQUITY', 'OTHER'))),")
    lines.append("       (SELECT p.node_code FROM prcp_coa_node p WHERE p.id=n.parent_id AND p.is_deleted=0 LIMIT 1)")
    lines.append("FROM prcp_coa_node n")
    lines.append("WHERE n.scheme_id=@scheme_id AND n.is_deleted=0;")
    lines.append("")
    lines.append("-- 2) 循环 INSERT 每节点")
    lines.append("DROP TEMPORARY TABLE IF EXISTS _citic_basic;")
    lines.append("CREATE TEMPORARY TABLE _citic_basic (")
    lines.append("  coa_node_id BIGINT NOT NULL,")
    lines.append("  data_date DATE NOT NULL,")
    lines.append("  node_code VARCHAR(32), node_name VARCHAR(64), node_level INT, parent_code VARCHAR(32),")
    lines.append("  is_leaf INT, category VARCHAR(16),")
    lines.append("  date_offset INT DEFAULT 0, offset_unit VARCHAR(2) DEFAULT 'D',")
    lines.append("  orig_m1 DECIMAL(20,4) DEFAULT 0, orig_m2 DECIMAL(20,4) DEFAULT 0,")
    for i in range(3, 61):
        lines.append(f"  orig_m{i} DECIMAL(20,4) DEFAULT 0,")
    lines.append("  orig_y10 DECIMAL(20,4) DEFAULT 0, orig_y15 DECIMAL(20,4) DEFAULT 0,")
    lines.append("  orig_y20 DECIMAL(20,4) DEFAULT 0, orig_y30 DECIMAL(20,4) DEFAULT 0,")
    lines.append("  rem_m1 DECIMAL(20,4) DEFAULT 0, rem_m2 DECIMAL(20,4) DEFAULT 0,")
    for i in range(3, 61):
        lines.append(f"  rem_m{i} DECIMAL(20,4) DEFAULT 0,")
    lines.append("  rem_y10 DECIMAL(20,4) DEFAULT 0, rem_y15 DECIMAL(20,4) DEFAULT 0,")
    lines.append("  rem_y20 DECIMAL(20,4) DEFAULT 0, rem_y30 DECIMAL(20,4) DEFAULT 0,")
    lines.append("  asf_rsf VARCHAR(8), hqla_factor DECIMAL(8,4),")
    lines.append("  current_balance DECIMAL(20,4), avg_balance DECIMAL(20,4),")
    lines.append("  weighted_rate DECIMAL(10,6), interest_amount DECIMAL(20,4),")
    lines.append("  risk_weight DECIMAL(10,6), calc_note VARCHAR(255),")
    lines.append("  is_deleted INT DEFAULT 0, created_by BIGINT DEFAULT 1, updated_by BIGINT DEFAULT 1")
    lines.append(") ENGINE=MEMORY;")
    lines.append("")

    # 现在每节点一条 INSERT 进 _citic_basic
    for code, name, amt_yi, rate_pct, risk_w, is_leaf, cat, _ in NODE_DEFS:
        basic = build_basic_for_node(code, name, amt_yi, rate_pct, risk_w, is_leaf, cat)

        cols = ["coa_node_id", "data_date", "node_code", "node_name", "node_level",
                "parent_code", "is_leaf", "category",
                "date_offset", "offset_unit"]
        for b in BUCKETS:
            cols.append(f"orig_{b}")
        for b in BUCKETS:
            cols.append(f"rem_{b}")
        cols += ["asf_rsf", "hqla_factor", "current_balance", "avg_balance",
                 "weighted_rate", "interest_amount", "risk_weight",
                 "calc_note", "is_deleted", "created_by", "updated_by"]

        # VALUES
        vals = [0, f"'{DATA_DATE}'", f"'{code}'", f"'{name}'", 0, "NULL", is_leaf, f"'{cat}'",
                0, "'D'"]
        for b in BUCKETS:
            vals.append(basic["orig"].get(b, 0))
        for b in BUCKETS:
            vals.append(basic["rem"].get(b, 0))
        asf = basic["asf_rsf"]
        vals.append(f"'{asf}'" if asf else "NULL")
        vals.append(basic["hqla_factor"])
        vals.append(basic["current_balance"])
        vals.append(basic["avg_balance"])
        vals.append(basic["weighted_rate"])
        vals.append(basic["interest_amount"])
        vals.append(basic["risk_weight"])
        vals.append(f"'{name} {amt_yi}亿元 @ {rate_pct}%'")
        vals.append(0)
        vals.append(USER_ID)
        vals.append(USER_ID)

        # 用 _citic_nodes 查 coa_node_id / node_level
        lines.append(f"SET @nid := (SELECT id FROM _citic_nodes WHERE code='{code}' LIMIT 1);")
        lines.append(f"SET @nl := (SELECT level FROM _citic_nodes WHERE code='{code}' LIMIT 1);")
        lines.append(f"SET @pc := (SELECT parent_code FROM _citic_nodes WHERE code='{code}' LIMIT 1);")
        # 把 coa_node_id / node_level / parent_code 换成变量
        # 简化：直接构造 SET 后的 INSERT
        vals[0] = "@nid"
        vals[4] = "@nl"
        vals[5] = "IFNULL(@pc, NULL)"

        cols_sql = ", ".join(cols)
        vals_sql = ", ".join(str(v) for v in vals)
        lines.append(f"INSERT INTO _citic_basic ({cols_sql}) VALUES ({vals_sql});")
        lines.append("")

    lines.append("INSERT INTO prcp_data_basic (")
    lines.append("  coa_node_id, data_date, node_code, node_name, node_level, parent_code,")
    lines.append("  is_leaf, category, date_offset, offset_unit,")
    lines.append("  orig_m1, orig_m2, orig_m3, orig_m4, orig_m5, orig_m6, orig_m7, orig_m8, orig_m9, orig_m10, orig_m11, orig_m12,")
    lines.append("  orig_y10, orig_y15, orig_y20, orig_y30,")
    lines.append("  rem_m1, rem_m2, rem_m3, rem_m4, rem_m5, rem_m6, rem_m7, rem_m8, rem_m9, rem_m10, rem_m11, rem_m12,")
    lines.append("  rem_y10, rem_y15, rem_y20, rem_y30,")
    lines.append("  asf_rsf, hqla_factor, current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,")
    lines.append("  calc_note, is_deleted, created_by, updated_by)")
    lines.append("SELECT coa_node_id, data_date, node_code, node_name, node_level, parent_code,")
    lines.append("  is_leaf, category, date_offset, offset_unit,")
    lines.append("  orig_m1, orig_m2, orig_m3, orig_m4, orig_m5, orig_m6, orig_m7, orig_m8, orig_m9, orig_m10, orig_m11, orig_m12,")
    lines.append("  orig_y10, orig_y15, orig_y20, orig_y30,")
    lines.append("  rem_m1, rem_m2, rem_m3, rem_m4, rem_m5, rem_m6, rem_m7, rem_m8, rem_m9, rem_m10, rem_m11, rem_m12,")
    lines.append("  rem_y10, rem_y15, rem_y20, rem_y30,")
    lines.append("  asf_rsf, hqla_factor, current_balance, avg_balance, weighted_rate, interest_amount, risk_weight,")
    lines.append("  calc_note, is_deleted, created_by, updated_by")
    lines.append("FROM _citic_basic;")
    lines.append("")
    lines.append("-- 4) 验证")
    lines.append("SELECT category, COUNT(*) AS cnt,")
    lines.append("       ROUND(SUM(current_balance)/1e8, 0) AS total_yi")
    lines.append("FROM prcp_data_basic b")
    lines.append("JOIN prcp_coa_node n ON n.id=b.coa_node_id")
    lines.append("WHERE n.scheme_id=@scheme_id AND b.is_deleted=0")
    lines.append("GROUP BY category;")
    lines.append("")
    lines.append("SELECT is_leaf, COUNT(*) AS cnt")
    lines.append("FROM prcp_data_basic b")
    lines.append("JOIN prcp_coa_node n ON n.id=b.coa_node_id")
    lines.append("WHERE n.scheme_id=@scheme_id AND b.is_deleted=0")
    lines.append("GROUP BY is_leaf;")
    lines.append("")
    lines.append("DROP TEMPORARY TABLE IF EXISTS _citic_nodes;")
    lines.append("DROP TEMPORARY TABLE IF EXISTS _citic_basic;")

    OUT = Path(r"C:\银行经营\PRCP\backend\scripts\citic_basic_2026h1_insert.sql")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"SQL 文件：{OUT}")
    print(f"文件大小：{OUT.stat().st_size} 字节")
    print(f"节点数：{len(NODE_DEFS)}")
    # 校验合计
    s_assets = sum(amt for code, _, amt, *_ in NODE_DEFS if code.startswith("S01") and len(code) > 14) / 1e4
    s_liab = sum(amt for code, _, amt, *_ in NODE_DEFS if code.startswith("S02") and len(code) > 14) / 1e4
    s_equity = sum(amt for code, _, amt, *_ in NODE_DEFS if code.startswith("S03")) / 1e4
    print(f"\n子节点金额合计：")
    print(f"  资产子节点（剔除总资产/小计）：{s_assets:.0f} 亿元")
    print(f"  负债子节点（剔除总负债/小计）：{s_liab:.0f} 亿元")
    print(f"  权益：{s_equity:.0f} 亿元")


if __name__ == "__main__":
    main()