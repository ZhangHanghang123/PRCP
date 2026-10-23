"""2026 五年预算方案 — 配置生成器

方案编码：BUDGET_2026_5Y
基准日：2025-12-31 | 预测期：60 月（5 年）

4 种增长方式分配（按中信实际业务特征）：
  type 1 目标增长百分比 → 贷款类（净增长口径，到期回补）
  type 2 目标增长绝对值 → 同业负债类（净增额口径，绝对额管控）
  type 3 增长百分比     → 债券投资类（毛投放口径，到期自然出表）
  type 4 增长值         → 存款类 + 权益类（余额锚定）

每年增长值 ≈ 5%
"""
import sys
from datetime import date

SCHEME_CODE = "BUDGET_2026_5Y"
SCHEME_NAME = "中信银行 2026-2030 五年业务预算方案"
COA_SCHEME_ID = 1
DATA_DATE = "2025-12-31"

# =============================================================================
# 一、节奏模板（12 月权重，和 = 100%）
# =============================================================================
RHYTHM_LINEAR = [round(100 / 12, 4)] * 12          # 线性 8.3333%

RHYTHM_SPRINT = [                                  # 开门红
    18.0, 14.0, 10.0, 8.0, 7.0, 10.0,
    6.0, 6.0, 8.0, 6.0, 5.0, 2.0,
]

RHYTHM_QUARTER = [                                 # 季末冲量
    5.0, 5.0, 15.0, 5.0, 5.0, 15.0,
    5.0, 5.0, 15.0, 5.0, 5.0, 15.0,
]

RHYTHM_STEADY = [                                  # 前低后高（年中发力）
    6.0, 6.0, 8.0, 8.0, 10.0, 10.0,
    10.0, 10.0, 10.0, 10.0, 6.0, 6.0,
]

# =============================================================================
# 二、期限模板（term_value, business_ratio, interest_rate）
# =============================================================================
def term_short(rate_base):
    """短期限为主（流贷/信用卡）"""
    return [(6, 30.0, rate_base), (12, 40.0, rate_base + 0.2),
            (24, 20.0, rate_base + 0.6), (36, 10.0, rate_base + 0.9)]

def term_midlong(rate_base):
    """中长期为主（对公贷款）"""
    return [(12, 20.0, rate_base), (24, 30.0, rate_base + 0.15),
            (36, 25.0, rate_base + 0.3), (60, 25.0, rate_base + 0.5)]

def term_bond(rate_base):
    """债券投资（均匀）"""
    return [(12, 25.0, rate_base), (24, 25.0, rate_base),
            (36, 25.0, rate_base), (60, 25.0, rate_base)]

def term_interbank(rate_base):
    """同业负债（短期限滚动）"""
    return [(3, 40.0, rate_base), (6, 30.0, rate_base + 0.05),
            (12, 30.0, rate_base + 0.1)]

def term_deposit(rate_base):
    """存款（定期为主）"""
    return [(12, 40.0, rate_base), (24, 35.0, rate_base + 0.15),
            (36, 25.0, rate_base + 0.3)]

def term_perpetual(rate_base):
    """权益（永续）"""
    return [(60, 100.0, rate_base)]


# =============================================================================
# 三、节点配置表（37 个末级节点全覆盖）
#
# 字段说明：
#   coa_code   账户册节点编码
#   gt         growth_type（1/2/3/4）
#   years      5 年参数
#   rhythm     节奏模板
#   term       期限模板
#   no_calc    True = 不参与模型测算（存量保持）
#
# year 参数语义随 gt 变化：
#   gt=1 → 年增长率（%）
#   gt=2 → 年新增额（万元）
#   gt=3 → 年增长率（%）
#   gt=4 → 年末目标余额（万元）
# =============================================================================
def pct_years(base=5.0):
    """百分比型 5 年参数（每年约 5%）"""
    return [base, base, round(base - 0.2, 2), round(base - 0.2, 2), base]


def abs_years(bal_yi, base_pct=5.0):
    """绝对额型 5 年参数（按 5% 复合增长，单位万元）

    gt=2 → 当年新增额：第 1 年 = 余额 × 5%，后续年 = 上年余额 × 5%
    gt=4 → 年末目标余额：第 1 年 = 余额 × 1.05，逐年复合
    """
    out = []
    bal = bal_yi * 1e4            # 亿元 → 万元
    for i in range(5):
        add = bal * base_pct / 100
        out.append(round(add, 2))       # 当年新增额（万元）
        bal = bal + add
    return out


def target_years(bal_yi, base_pct=5.0):
    """gt=4 用：年末目标余额（万元），按 5% 复合"""
    out = []
    bal = bal_yi * 1e4
    for i in range(5):
        bal = bal * (1 + base_pct / 100)
        out.append(round(bal, 2))
    return out


# (coa_code, 节点名, 余额亿, gt, years, rhythm, term, no_calc)
NODE_CFG = [
    # ============ 资产 · 贷款类 → type 1 目标增长百分比（净增长口径）============
    ("S010101010000", "1.1.对公一般贷款",       29452.72, 1, pct_years(5.0),    RHYTHM_LINEAR,   term_midlong(3.20), False),
    ("S010101020000", "1.2.个人贷款",           18281.87, 1, pct_years(5.2),    RHYTHM_SPRINT,   term_midlong(3.80), False),
    ("S010101030000", "1.3.信用卡贷款",          4445.26, 1, pct_years(6.0),    RHYTHM_SPRINT,   term_short(7.00),   False),
    ("S010101040000", "1.4.票据贴现",            2013.40, 1, pct_years(4.0),    RHYTHM_LINEAR,   term_short(1.50),   False),
    ("S010101050000", "1.5.非银贷款",            3484.78, 1, pct_years(5.5),    RHYTHM_STEADY,   term_midlong(3.60), False),

    # ============ 资产 · 债券投资 → type 3 增长百分比（毛投放口径）============
    ("S010102010101", "2.1.1.1AC",              5439.80, 3, pct_years(5.5),    RHYTHM_QUARTER,  term_bond(2.60),    False),
    ("S010102010102", "2.1.1.2FVOCI",           6404.02, 3, pct_years(5.0),    RHYTHM_QUARTER,  term_bond(2.70),    False),
    ("S010102010103", "2.1.1.3FVTPL",            500.00, 3, pct_years(5.0),    RHYTHM_QUARTER,  term_bond(2.90),    False),
    ("S010102010201", "2.1.2.1AC",              5663.51, 3, pct_years(5.5),    RHYTHM_QUARTER,  term_bond(2.60),    False),
    ("S010102010202", "2.1.2.2FVOCI",            436.67, 3, pct_years(5.0),    RHYTHM_QUARTER,  term_bond(2.70),    False),
    ("S010102010203", "2.1.2.3FVTPL",            300.00, 3, pct_years(5.0),    RHYTHM_QUARTER,  term_bond(2.90),    False),

    # ============ 资产 · 其他 → type 1 / type 4 混合 ============
    ("S010102020000", "2.2.结构化融资",          2051.72, 1, pct_years(5.0),    RHYTHM_LINEAR,   term_midlong(3.40), False),
    ("S010102030000", "2.3.同业资产",            2481.18, 1, pct_years(4.5),    RHYTHM_STEADY,   term_interbank(2.00), False),
    ("S010102040000", "2.4.存款准备金",          3653.55, 1, pct_years(3.0),    RHYTHM_LINEAR,   term_short(1.50),   False),
    ("S010103010000", "3.1.FVTPL类资产",         6402.62, 3, pct_years(5.0),    RHYTHM_QUARTER,  term_bond(2.80),    False),
    ("S010103020100", "3.2.1.现金",              1275.17, 1, pct_years(5.0),    RHYTHM_LINEAR,   term_short(0.00),   False),
    ("S010103020200", "3.2.2.其它",              1000.00, 1, pct_years(5.0),    RHYTHM_LINEAR,   term_short(0.00),   False),

    # ============ 外币资产 → type 1 ============
    ("S010201000000", "1.外币贷款",               800.00, 1, pct_years(5.0),    RHYTHM_LINEAR,   term_midlong(4.00), False),
    ("S010202010000", "2.1.外币债券",             350.00, 3, pct_years(5.0),    RHYTHM_QUARTER,  term_bond(2.50),    False),
    ("S010202020000", "2.2.外币同业资产",         250.00, 1, pct_years(5.0),    RHYTHM_LINEAR,   term_interbank(2.20), False),
    ("S010203000000", "3.外币非生息资产",         100.00, 0, [],                 RHYTHM_LINEAR,   term_short(0.00),   True),

    # ============ 负债 · 存款 → type 4 增长值（余额锚定）============
    ("S020101010100", "1.1.1对公活期存款",     24862.12, 4, target_years(24862.12, 5.0), RHYTHM_LINEAR,   term_deposit(0.85), False),
    ("S020101010200", "1.1.2对公定期存款",     17364.70, 4, target_years(17364.70, 5.2), RHYTHM_STEADY,   term_deposit(2.05), False),
    ("S020101020100", "1.2.1零售活期存款",      4348.67, 4, target_years(4348.67, 5.0),  RHYTHM_SPRINT,   term_deposit(0.50), False),
    ("S020101020200", "1.2.2零售定期存款",     17345.64, 4, target_years(17345.64, 5.2), RHYTHM_SPRINT,   term_deposit(2.00), False),

    # ============ 负债 · 同业 → type 2 目标增长绝对值（净增额口径）============
    ("S020102010100", "2.2.1.1同业拆入",        329.88,  2, abs_years(329.88, 5.0),     RHYTHM_LINEAR,   term_interbank(1.80), False),
    ("S020102010200", "2.2.1.2债券回购",        958.75,  2, abs_years(958.75, 5.0),     RHYTHM_QUARTER,  term_interbank(1.85), False),
    ("S020102010300", "2.2.1.3同业存单NCD",     9322.38,  2, abs_years(9322.38, 5.0),    RHYTHM_QUARTER,  term_interbank(2.00), False),
    ("S020102010400", "2.2.1.4同业存款",        9156.05,  2, abs_years(9156.05, 5.0),    RHYTHM_STEADY,   term_interbank(1.50), False),
    ("S020102010500", "2.2.1.5票据转贴现回购",    10.00,  2, abs_years(10.00, 5.0),      RHYTHM_LINEAR,   term_interbank(1.60), False),
    ("S020102020100", "2.2.2.1公开市场回购",     3538.88,  2, abs_years(3538.88, 5.0),    RHYTHM_QUARTER,  term_interbank(1.70), False),
    ("S020102020200", "2.2.2.2 MLF",            1603.70,  2, abs_years(1603.70, 5.0),    RHYTHM_LINEAR,   term_interbank(2.50), False),
    ("S020102020300", "2.2.2.3结构性货币工具",    422.12,  2, abs_years(422.12, 5.0),     RHYTHM_STEADY,   term_interbank(1.50), False),
    ("S020102020400", "2.2.2.4票据再贴现回购",     15.25,  2, abs_years(15.25, 5.0),      RHYTHM_LINEAR,   term_interbank(1.30), False),

    # ============ 外币负债 → type 4 ============
    ("S020201000000", "1.外币存款",              1500.00, 4, target_years(1500.00, 5.0),  RHYTHM_LINEAR,   term_deposit(1.50), False),
    ("S020202000000", "2.外币市场化负债",         800.00, 4, target_years(800.00, 5.0),   RHYTHM_LINEAR,   term_deposit(1.85), False),

    # ============ 权益 → type 4（永续，不到期）============
    ("S030000000000", "所有者权益",              7862.17, 4, target_years(7862.17, 5.0),  RHYTHM_LINEAR,   term_perpetual(0.00), False),
]


# =============================================================================
# 四、节奏 → rhythm_type 判定（线性模板 → 1，自定义 → 2）
# =============================================================================
def rhythm_type_of(weights):
    return 1 if weights == RHYTHM_LINEAR else 2


# =============================================================================
# 五、生成 SQL
# =============================================================================
def gen_sql():
    L = []
    L.append("-- " + "=" * 76)
    L.append("-- PRCP 2026-2030 五年业务预算方案（BUDGET_2026_5Y）")
    L.append("-- 基准日 2025-12-31 | 预测期 60 月（5 年）")
    L.append("-- 37 个末级节点全覆盖 | 4 种增长方式全覆盖 | 每年增长约 5%")
    L.append("--")
    L.append("-- growth_type 分配策略（按中信实际业务特征）：")
    L.append("--   1 目标增长百分比 → 贷款类（净增长口径，到期回补保证达标）")
    L.append("--   2 目标增长绝对值 → 同业负债（净增额口径，绝对额管控）")
    L.append("--   3 增长百分比     → 债券投资（毛投放口径，到期自然出表）")
    L.append("--   4 增长值         → 存款 + 权益（余额锚定，可为负）")
    L.append("--")
    L.append("-- 节奏：线性（均衡）/ 开门红 / 季末冲量 / 前低后高")
    L.append("-- " + "=" * 76)
    L.append("")
    L.append("USE prcp_db;")
    L.append("SET @uid = 1;")
    L.append("")

    # ---------- 1. 清理 ----------
    L.append("-- " + "-" * 76)
    L.append("-- PART 1 清理（幂等）")
    L.append("-- " + "-" * 76)
    L.append("SET @sid := (SELECT id FROM prcp_sim_scheme WHERE scheme_code='%s' AND is_deleted=0 LIMIT 1);" % SCHEME_CODE)
    L.append("SET @sid := IFNULL(@sid, 0);")
    L.append("")
    L.append("DELETE FROM prcp_sim_result WHERE run_id IN (SELECT id FROM prcp_sim_run WHERE sim_scheme_id=@sid);")
    L.append("DELETE FROM prcp_sim_run WHERE sim_scheme_id=@sid;")
    L.append("DELETE FROM prcp_sim_growth_config WHERE scheme_id=@sid;")
    L.append("DELETE FROM prcp_sim_rhythm WHERE config_id IN (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid);")
    L.append("DELETE FROM prcp_sim_term_ratio WHERE config_id IN (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid);")
    L.append("DELETE FROM prcp_sim_node_config WHERE scheme_id=@sid;")
    L.append("DELETE FROM prcp_sim_scheme WHERE id=@sid;")
    L.append("")

    # ---------- 2. 方案 ----------
    L.append("-- " + "-" * 76)
    L.append("-- PART 2 新建方案")
    L.append("-- " + "-" * 76)
    L.append("INSERT INTO prcp_sim_scheme")
    L.append("  (scheme_code, scheme_name, coa_scheme_id, data_date, description, config_node_count, status, is_deleted, created_by, updated_by)")
    L.append("VALUES (")
    L.append("  '%s', '%s', %d, '%s'," % (SCHEME_CODE, SCHEME_NAME, COA_SCHEME_ID, DATA_DATE))
    L.append("  '中信银行 2026-2030 五年业务预算方案。基准日 2025-12-31（对齐 prcp_data_basic 基础数据），预测期 60 月（5 年）。',")
    L.append("  %d, 'ACTIVE', 0, @uid, @uid);" % len(NODE_CFG))
    L.append("")
    L.append("SET @sid := LAST_INSERT_ID();")
    L.append("")

    # ---------- 3. node_config + growth_config ----------
    L.append("-- " + "-" * 76)
    L.append("-- PART 3 节点配置（%d 个末级节点）+ 增长配置（5 年参数）" % len(NODE_CFG))
    L.append("-- " + "-" * 76)
    L.append("INSERT INTO prcp_sim_node_config")
    L.append("  (scheme_id, coa_node_id, coa_node_code, annual_growth_rate, term_unit, term_count,")
    L.append("   is_model_calc, rhythm_type, remark, is_deleted, created_by, updated_by)")
    L.append("VALUES")

    cfgs = []
    for code, name, bal, gt, years, rhythm, term, no_calc in NODE_CFG:
        imc = 2 if no_calc else 1
        rt = rhythm_type_of(rhythm)
        # legacy annual_growth_rate 只在 type 1/3（百分比）时有值
        legacy = years[0] if (gt in (1, 3) and years) else 0
        cfgs.append(
            "  (@sid, (SELECT id FROM prcp_coa_node WHERE node_code='%s' AND scheme_id=%d AND is_deleted=0 LIMIT 1),"
            "\n   '%s', %s, 'MONTH', %d, %d, %d, '%s', 0, @uid, @uid)"
            % (code, COA_SCHEME_ID, code, legacy, len(term), imc, rt,
               "存量保持（不参与模型测算）" if no_calc else "参与模型测算")
        )
    L.append(",\n".join(cfgs) + ";")
    L.append("")
    L.append("-- 回填 term_count（按实际占比行数）")
    L.append("")

    # growth_config
    L.append("-- 增长配置（growth_type + 5 年参数 + 单位）")
    L.append("INSERT INTO prcp_sim_growth_config")
    L.append("  (scheme_id, scheme_code, scheme_name, coa_node_id, coa_node_code, coa_node_name,")
    L.append("   config_id, growth_type, year1_value, year2_value, year3_value, year4_value, year5_value,")
    L.append("   unit, amount_unit, remark, is_deleted, created_by, updated_by)")
    L.append("SELECT")
    L.append("  @sid, '%s', '%s', c.coa_node_id, c.coa_node_code," % (SCHEME_CODE, SCHEME_NAME))
    L.append("  (SELECT n.node_name FROM prcp_coa_node n WHERE n.id = c.coa_node_id),")
    L.append("  c.id, t.gt, t.y1, t.y2, t.y3, t.y4, t.y5,")
    L.append("  t.unit, t.amt_unit, t.rmk, 0, @uid, @uid")
    L.append("FROM prcp_sim_node_config c")
    L.append("JOIN (")
    grows = []
    for code, name, bal, gt, years, rhythm, term, no_calc in NODE_CFG:
        if no_calc or not years:
            continue
        y = years + [0, 0, 0, 0, 0][len(years):]
        unit = "%" if gt in (1, 3) else "ABS"
        amt = "NULL" if gt in (1, 3) else "'WAN'"
        grows.append(
            "  SELECT '%s' AS code, %d AS gt, %.4f AS y1, %.4f AS y2, %.4f AS y3, %.4f AS y4, %.4f AS y5,"
            "\n         '%s' AS unit, %s AS amt_unit, '%s' AS rmk"
            % (code, gt, y[0], y[1], y[2], y[3], y[4], unit, amt,
               ("%s，%s，5 年复合增长" % (name, {1: "净增长口径", 2: "净增额口径", 3: "毛投放口径", 4: "余额锚定"}[gt])))
        )
    L.append("\n  UNION ALL\n".join(grows))
    L.append(") t ON t.code = c.coa_node_code")
    L.append("WHERE c.scheme_id = @sid;")
    L.append("")

    # ---------- 4. rhythm ----------
    L.append("-- " + "-" * 76)
    L.append("-- PART 4 节奏配置（12 个月权重）")
    L.append("-- " + "-" * 76)
    L.append("INSERT INTO prcp_sim_rhythm")
    L.append("  (config_id, scheme_id, coa_node_id, month_no, month_label, weight, sort_order, remark, is_deleted, created_by, updated_by)")
    L.append("SELECT c.id, @sid, c.coa_node_id, t.mo, CONCAT(t.mo, '月'), t.w, t.mo, NULL, 0, @uid, @uid")
    L.append("FROM prcp_sim_node_config c")
    L.append("JOIN (")
    rhy = []
    for code, name, bal, gt, years, rhythm, term, no_calc in NODE_CFG:
        if no_calc:
            continue
        for i, w in enumerate(rhythm, start=1):
            rhy.append("  SELECT '%s' AS code, %d AS mo, %.4f AS w" % (code, i, w))
    L.append("\n  UNION ALL\n".join(rhy))
    L.append(") t ON t.code = c.coa_node_code")
    L.append("WHERE c.scheme_id = @sid;")
    L.append("")

    # ---------- 5. term_ratio ----------
    L.append("-- " + "-" * 76)
    L.append("-- PART 5 期限占比（按业务类型的期限结构）")
    L.append("-- " + "-" * 76)
    L.append("INSERT INTO prcp_sim_term_ratio")
    L.append("  (config_id, term_value, term_unit, business_ratio, interest_rate, sort_order, remark, is_deleted, created_by, updated_by)")
    L.append("SELECT c.id, t.tv, 'MONTH', t.br, t.ir, t.so, NULL, 0, @uid, @uid")
    L.append("FROM prcp_sim_node_config c")
    L.append("JOIN (")
    tr = []
    for code, name, bal, gt, years, rhythm, term, no_calc in NODE_CFG:
        if no_calc:
            continue
        for i, (tv, br, ir) in enumerate(term, start=1):
            tr.append("  SELECT '%s' AS code, %d AS tv, %.2f AS br, %.4f AS ir, %d AS so"
                      % (code, tv, br, ir, i))
    L.append("\n  UNION ALL\n".join(tr))
    L.append(") t ON t.code = c.coa_node_code")
    L.append("WHERE c.scheme_id = @sid;")
    L.append("")

    # ---------- 6. 更新计数 ----------
    L.append("-- " + "-" * 76)
    L.append("-- PART 6 回填计数")
    L.append("-- " + "-" * 76)
    L.append("UPDATE prcp_sim_node_config c SET")
    L.append("  term_count = (SELECT COUNT(*) FROM prcp_sim_term_ratio t")
    L.append("                  WHERE t.config_id = c.id AND t.is_deleted = 0)")
    L.append("WHERE c.scheme_id = @sid;")
    L.append("")
    L.append("UPDATE prcp_sim_scheme s SET")
    L.append("  config_node_count = (SELECT COUNT(*) FROM prcp_sim_node_config c")
    L.append("                      WHERE c.scheme_id = s.id AND c.is_deleted = 0)")
    L.append("WHERE s.id = @sid;")
    L.append("")

    # ---------- 7. 验证 ----------
    L.append("-- " + "-" * 76)
    L.append("-- PART 7 验证")
    L.append("-- " + "-" * 76)
    L.append("SELECT '====== 方案初始化完成 ======' AS status;")
    L.append("SELECT id, scheme_code, scheme_name, data_date, config_node_count, status")
    L.append("FROM prcp_sim_scheme WHERE id = @sid;")
    L.append("")
    L.append("-- growth_type 分布")
    L.append("SELECT g.growth_type AS gt, d.dict_label AS 名称, COUNT(*) AS 节点数")
    L.append("FROM prcp_sim_growth_config g")
    L.append("LEFT JOIN sys_dict d ON d.dict_type='PRCP_GROWTH_TYPE' AND d.dict_key=g.growth_type")
    L.append("WHERE g.scheme_id = @sid AND g.is_deleted = 0")
    L.append("GROUP BY g.growth_type, d.dict_label ORDER BY g.growth_type;")
    L.append("")
    L.append("-- rhythm_type 分布")
    L.append("SELECT rhythm_type, COUNT(*) AS 节点数 FROM prcp_sim_node_config")
    L.append("WHERE scheme_id = @sid AND is_deleted = 0 GROUP BY rhythm_type ORDER BY rhythm_type;")
    L.append("")
    L.append("-- 是否模型测算分布")
    L.append("SELECT is_model_calc, COUNT(*) AS 节点数 FROM prcp_sim_node_config")
    L.append("WHERE scheme_id = @sid AND is_deleted = 0 GROUP BY is_model_calc ORDER BY is_model_calc;")
    L.append("")
    L.append("-- 配置完整性检查")
    L.append("SELECT")
    L.append("  (SELECT COUNT(*) FROM prcp_sim_node_config WHERE scheme_id=@sid AND is_deleted=0) AS node_cfg,")
    L.append("  (SELECT COUNT(*) FROM prcp_sim_growth_config WHERE scheme_id=@sid AND is_deleted=0) AS growth_cfg,")
    L.append("  (SELECT COUNT(DISTINCT config_id) FROM prcp_sim_rhythm WHERE config_id IN")
    L.append("     (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid) AND is_deleted=0) AS rhythm_cfg,")
    L.append("  (SELECT COUNT(DISTINCT config_id) FROM prcp_sim_term_ratio WHERE config_id IN")
    L.append("     (SELECT id FROM prcp_sim_node_config WHERE scheme_id=@sid) AND is_deleted=0) AS term_cfg;")
    L.append("")
    L.append("-- 权重和校验（应全部 = 100）")
    L.append("SELECT r.config_id, c.coa_node_code, ROUND(SUM(r.weight),4) AS 权重和, COUNT(*) AS 月数")
    L.append("FROM prcp_sim_rhythm r")
    L.append("JOIN prcp_sim_node_config c ON c.id = r.config_id")
    L.append("WHERE c.scheme_id = @sid AND r.is_deleted = 0")
    L.append("GROUP BY r.config_id, c.coa_node_code")
    L.append("HAVING ROUND(SUM(r.weight),4) <> 100.0000 OR COUNT(*) <> 12;")
    L.append("-- （无输出 = 全部通过）")
    L.append("")
    L.append("-- 占比和校验（应全部 = 100）")
    L.append("SELECT t.config_id, c.coa_node_code, ROUND(SUM(t.business_ratio),4) AS 占比和, COUNT(*) AS 行数")
    L.append("FROM prcp_sim_term_ratio t")
    L.append("JOIN prcp_sim_node_config c ON c.id = t.config_id")
    L.append("WHERE c.scheme_id = @sid AND t.is_deleted = 0")
    L.append("GROUP BY t.config_id, c.coa_node_code")
    L.append("HAVING ROUND(SUM(t.business_ratio),4) <> 100.0000;")
    L.append("-- （无输出 = 全部通过）")
    L.append("")

    return "\n".join(L)


if __name__ == "__main__":
    sql = gen_sql()
    out = r"C:\银行经营\PRCP\backend\scripts\init_budget_2026_5y.sql"
    with open(out, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"SQL 已生成：{out}")
    print(f"节点数：{len(NODE_CFG)}")
    # 统计分布
    from collections import Counter
    gt_cnt = Counter(c[3] for c in NODE_CFG)
    rt_cnt = Counter(rhythm_type_of(c[5]) for c in NODE_CFG)
    print(f"growth_type 分布：{dict(sorted(gt_cnt.items()))}")
    print(f"rhythm_type 分布：{dict(sorted(rt_cnt.items()))}")
    no_calc = sum(1 for c in NODE_CFG if c[7])
    print(f"不参与测算：{no_calc} 个 | 参与测算：{len(NODE_CFG)-no_calc} 个")
