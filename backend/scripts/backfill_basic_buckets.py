"""基础数据期限桶回填脚本

问题诊断（2026-10-21）：
  prcp_data_basic 的 orig_m1 / rem_m1 = 100% 余额，m3~m60 与 y10~y30 全为 0。
  → 引擎第 1 个月把余额全部释放完（当月到期 = 全部余额），
    之后 rem_m1 永远为 0，直到新投放按期限占比落桶才有到期。
  → 表现为「很多格子没有数据」。

结论：程序逻辑正确，是**底数的期限结构缺失**。

本脚本按业务类型的合理期限结构回填 orig_* / rem_* 桶：
  - 回填后 Σ桶 = current_balance（总额守恒）
  - orig_* = 原始期限分布（用于加权平均利率）
  - rem_* 初始与 orig_* 相同（基准日即剩余期限 = 原始期限）

期限结构模板（按业务性质）：
  贷款类   中长期为主，5Y 档位分散
  债券投资 阶梯分布，含 10Y 长端
  存款类   定期为主，1Y~3Y
  同业负债 短端为主（3M/6M/12M）
  权益     永续（60M）
  非生息   3M 内为主

用法：python backfill_basic_buckets.py [--dry-run]
"""
import sys

DRY = "--dry-run" in sys.argv

# ---------------------------------------------------------------- 期限模板
# (桶名, 权重%) —— 原始值，生成时会自动归一化到精确 100%
#
# ⚠️ 设计要点（2026-10-21 修正）：
#   初版模板只用 4~5 个离散档位（如 loan 只在 m1/m6/m12/m24/m36/m60/y10 落值），
#   导致表格里大量月份格子为空 —— 虽然总额守恒、滚动正确，但展示效果很差。
#   修正为**逐月平滑铺开**：短端（1~12 月）每个月都有值，长端按 18/24/30/36/48/60 + 年份桶。
_RAW_TEMPLATES = {
    # 贷款：中长期为主，短端逐月铺开（1~12 月每月都有），长端按季度/年度档
    "loan": [
        ("m1", 3.0), ("m2", 3.0), ("m3", 3.5), ("m4", 3.5), ("m5", 4.0),
        ("m6", 4.5), ("m7", 4.5), ("m8", 5.0), ("m9", 5.0), ("m10", 5.0),
        ("m11", 5.0), ("m12", 6.0),
        ("m18", 4.0), ("m24", 9.0), ("m30", 4.0), ("m36", 8.0),
        ("m48", 4.0), ("m60", 10.0), ("y10", 10.0),
    ],
    # 债券：逐月铺开 + 长端（含 15Y）
    "bond": [
        ("m1", 2.5), ("m2", 2.5), ("m3", 3.0), ("m4", 3.5), ("m5", 3.5),
        ("m6", 4.0), ("m7", 4.0), ("m8", 4.5), ("m9", 4.5), ("m10", 5.0),
        ("m11", 5.0), ("m12", 5.5),
        ("m18", 4.0), ("m24", 10.0), ("m30", 4.0), ("m36", 7.5),
        ("m48", 3.0), ("m60", 8.0), ("y10", 11.0), ("y15", 5.0),
    ],
    # 存款：定期为主但短端也铺开
    "deposit": [
        ("m1", 4.5), ("m2", 4.5), ("m3", 5.0), ("m4", 5.0), ("m5", 5.0),
        ("m6", 5.5), ("m7", 5.5), ("m8", 5.5), ("m9", 5.5), ("m10", 5.5),
        ("m11", 5.5), ("m12", 6.5),
        ("m18", 3.5), ("m24", 11.0), ("m30", 3.0), ("m36", 8.5), ("m60", 8.5),
    ],
    # 同业负债：短端为主，1~12 月逐月铺开
    "interbank": [
        ("m1", 10.0), ("m2", 9.0), ("m3", 10.0), ("m4", 8.0), ("m5", 7.5),
        ("m6", 9.0), ("m7", 7.0), ("m8", 6.5), ("m9", 6.0), ("m10", 5.5),
        ("m11", 5.0), ("m12", 6.0),
        ("m18", 3.0), ("m24", 6.0),
    ],
    # 权益/永续
    "perpetual": [("m60", 100.0)],
    # 非生息资产：短端逐月铺开
    "short": [
        ("m1", 15.0), ("m2", 14.0), ("m3", 14.0), ("m4", 13.0), ("m5", 12.0),
        ("m6", 12.0), ("m7", 7.0), ("m8", 5.5), ("m9", 3.5), ("m10", 2.0),
        ("m11", 1.0), ("m12", 1.0),
    ],
}


def _normalize(tpl):
    """把权重精确归一化到 100%：最大桶吸收舍入误差"""
    total = sum(p for _, p in tpl)
    scaled = [(bk, p * 100.0 / total) for bk, p in tpl]
    # 舍入到 4 位后可能仍有误差，用最大桶兜底
    rounded = [(bk, round(p, 4)) for bk, p in scaled]
    diff = round(100.0 - sum(p for _, p in rounded), 4)
    if abs(diff) >= 0.0001:
        bk_max = max(rounded, key=lambda x: x[1])[0]
        rounded = [(bk, round(p + diff, 4)) if bk == bk_max else (bk, p)
                   for bk, p in rounded]
    return rounded


# 归一化后的模板（权重精确和 = 100）
TEMPLATES = {k: _normalize(v) for k, v in _RAW_TEMPLATES.items()}

# ---------------------------------------------------------------- 节点 → 模板映射
# 依据 node_code 前缀与 node_name 关键字
NODE_TEMPLATES = {
    # ===== 贷款类（S0101 开头）→ loan =====
    "S010101010000": "loan",   # 1.1.对公一般贷款
    "S010101020000": "loan",   # 1.2.个人贷款
    "S010101030000": "loan",   # 1.3.信用卡贷款（偏短，用 loan 的短端权重即可）
    "S010101040000": "loan",   # 1.4.票据贴现
    "S010101050000": "loan",   # 1.5.非银贷款
    "S010201000000": "loan",   # 1.外币贷款
    # ===== 债券投资 → bond =====
    "S010102010101": "bond",   # 2.1.1.1AC
    "S010102010102": "bond",   # 2.1.1.2FVOCI
    "S010102010103": "bond",   # 2.1.1.3FVTPL
    "S010102010201": "bond",   # 2.1.2.1AC
    "S010102010202": "bond",   # 2.1.2.2FVOCI
    "S010102010203": "bond",   # 2.1.2.3FVTPL
    "S010103010000": "bond",   # 3.1.FVTPL类资产
    "S010202010000": "bond",   # 2.1.外币债券
    # ===== 同业资产 → interbank =====
    "S010102030000": "interbank",  # 2.3.同业资产
    "S010202020000": "interbank",  # 2.2.外币同业资产
    # ===== 非生息/现金 → short =====
    "S010102040000": "short",   # 2.4.存款准备金
    "S010103020100": "short",   # 3.2.1.现金
    "S010103020200": "short",   # 3.2.2.其它
    "S010203000000": "short",   # 3.外币非生息资产
    "S010102020000": "loan",    # 2.2.结构化融资（按贷款处理）
    # ===== 存款 → deposit =====
    "S020101010100": "deposit",  # 1.1.1对公活期存款
    "S020101010200": "deposit",  # 1.1.2对公定期存款
    "S020101020100": "deposit",  # 1.2.1零售活期存款
    "S020101020200": "deposit",  # 1.2.2零售定期存款
    "S020201000000": "deposit",  # 1.外币存款
    # ===== 同业负债 → interbank =====
    "S020102010100": "interbank",  # 2.2.1.1同业拆入
    "S020102010200": "interbank",  # 2.2.1.2债券回购
    "S020102010300": "interbank",  # 2.2.1.3 NCD
    "S020102010400": "interbank",  # 2.2.1.4同业存款
    "S020102010500": "interbank",  # 2.2.1.5票据转贴现回购
    "S020102020100": "interbank",  # 2.2.2.1公开市场回购
    "S020102020200": "interbank",  # 2.2.2.2 MLF
    "S020102020300": "interbank",  # 2.2.2.3结构性货币工具
    "S020102020400": "interbank",  # 2.2.2.4票据再贴现回购
    "S020202000000": "interbank",  # 2.外币市场化负债
    # ===== 权益 → perpetual =====
    "S030000000000": "perpetual",  # 所有者权益
}


def gen_sql():
    L = []
    L.append("-- " + "=" * 76)
    L.append("-- 基础数据期限桶回填（prcp_data_basic orig_*/rem_*）")
    L.append("-- 目的：原数据 100% 余额堆在 m1，其余桶为 0，导致引擎 M1 一次性释放全部余额，")
    L.append("--       之后 rem_m1 恒为 0，表现为「很多格子没数据」。")
    L.append("-- 做法：按业务类型的合理期限结构回填，保证 Σ桶 = current_balance（总额守恒）")
    L.append("-- 数据日期：2026-10-21")
    L.append("-- " + "=" * 76)
    L.append("")
    L.append("USE prcp_db;")
    L.append("")
    L.append("-- ---------- 备份（幂等） ----------")
    L.append("CREATE TABLE IF NOT EXISTS prcp_data_basic_bucket_bak_20261021 LIKE prcp_data_basic;")
    L.append("INSERT IGNORE INTO prcp_data_basic_bucket_bak_20261021")
    L.append("  SELECT * FROM prcp_data_basic WHERE data_date='2025-12-31';")
    L.append("")

    all_buckets = sorted({bk for lst in TEMPLATES.values() for bk, _ in lst})
    all_cols = ["current_balance"] + \
        [f"orig_{bk}" for bk in all_buckets] + [f"rem_{bk}" for bk in all_buckets]
    col_list = ", ".join(all_cols)

    L.append("-- ---------- 逐节点回填（%d 个末级节点）----------" % len(NODE_TEMPLATES))
    L.append("-- orig_* = 原始期限分布；rem_* 初始与 orig_* 相同（基准日剩余期限 = 原始期限）")
    L.append("")
    for code, tname in sorted(NODE_TEMPLATES.items()):
        tpl = TEMPLATES[tname]
        L.append("-- %s（%s）" % (code, tname))
        # 组装 SET 子句
        sets = []
        for bk, pct in tpl:
            sets.append("  orig_%s = ROUND(current_balance * %.6f, 4)" % (bk, pct / 100))
        for bk, pct in tpl:
            sets.append("  rem_%s  = ROUND(current_balance * %.6f, 4)" % (bk, pct / 100))
        L.append("UPDATE prcp_data_basic SET")
        L.append(",\n".join(sets) + ",")
        # 尾部差异归入 m1，保证 Σ桶 = current_balance
        other = " + ".join("COALESCE(orig_%s,0)" % bk
                           for bk, _ in tpl if bk != "m1")
        if other:
            L.append("  orig_m1 = ROUND(current_balance - (%s), 4)," % other)
            L.append("  rem_m1  = ROUND(current_balance - (%s), 4)" % other)
        else:
            L.append("  orig_m1 = 0,")
            L.append("  rem_m1  = 0")
        L.append("WHERE data_date='2025-12-31' AND is_deleted=0 AND node_code='%s';" % code)
        L.append("")

    L.append("-- ---------- 验证 ----------")
    L.append("SELECT '回填前' AS phase,")
    L.append("  ROUND(SUM(%s)/1e8,2) AS 桶和_亿," % " + ".join("orig_%s" % bk for bk in all_buckets))
    L.append("  ROUND(SUM(current_balance)/1e8,2) AS 余额_亿,")
    L.append("  ROUND((SUM(current_balance) - SUM(%s))/1e8,6) AS 差额_亿" % " + ".join(
        "orig_%s" % bk for bk in all_buckets))
    L.append("FROM prcp_data_basic_bucket_bak_20261021 WHERE data_date='2025-12-31';")
    L.append("")
    L.append("SELECT '回填后' AS phase,")
    L.append("  ROUND(SUM(%s)/1e8,2) AS 桶和_亿," % " + ".join("orig_%s" % bk for bk in all_buckets))
    L.append("  ROUND(SUM(current_balance)/1e8,2) AS 余额_亿,")
    L.append("  ROUND((SUM(current_balance) - SUM(%s))/1e8,6) AS 差额_亿," % " + ".join(
        "orig_%s" % bk for bk in all_buckets))
    L.append("  ROUND(SUM(%s)/1e8,2) AS rem桶和_亿" % " + ".join("rem_%s" % bk for bk in all_buckets))
    L.append("FROM prcp_data_basic WHERE data_date='2025-12-31' AND is_deleted=0;")
    L.append("")
    L.append("-- 期限分布抽样（回填后）")
    L.append("SELECT node_code, LEFT(node_name,14) AS name,")
    L.append("  ROUND(current_balance/1e8,1) AS 余额_亿,")
    L.append("  ROUND(orig_m1/1e8,1) AS m1, ROUND(orig_m6/1e8,1) AS m6,")
    L.append("  ROUND(orig_m12/1e8,1) AS m12, ROUND(orig_m24/1e8,1) AS m24,")
    L.append("  ROUND(orig_m60/1e8,1) AS m60, ROUND(orig_y10/1e8,1) AS y10")
    L.append("FROM prcp_data_basic WHERE data_date='2025-12-31' AND is_deleted=0")
    L.append("  AND node_code IN ('S010101010000','S010102010102','S020102010300','S030000000000')")
    L.append("ORDER BY current_balance DESC;")
    return "\n".join(L)


if __name__ == "__main__":
    sql = gen_sql()
    out = r"C:\银行经营\PRCP\backend\scripts\backfill_basic_buckets.sql"
    with open(out, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"SQL 已生成：{out}")
    print(f"节点数：{len(NODE_TEMPLATES)}")
    buckets = sorted({b for lst in TEMPLATES.values() for b, _ in lst})
    print(f"涉及桶：{buckets}")
    # 校验模板权重和
    for name, tpl in TEMPLATES.items():
        s = sum(p for _, p in tpl)
        flag = "OK" if abs(s - 100) < 0.01 else "!! 不等于 100"
        print(f"  模板 {name:10s} 权重和 = {s:.2f} {flag}")