"""seed_score_rules_v14.py —— 评分标准 v14 锚点重标定规则落库

来源：C:/银行经营/PRCP/docs/v2/评分标准_v14_锚点重标定.xlsx
生成：C:/银行经营/PRCP/docs/build_score_standard_v14.py（锚点定义唯一真源）

设计要点
--------
1. **单位统一为百分数**（120.0 表示 120%），与线上 v12b 规则及
   prcp_kpi_value.current_value 口径一致（线上 REG_LCR=148.000000 即 148%）。
   Excel 档位表用小数（1.2）+ 0.0000% 数字格式，落库前 ×100 转换。

2. **段序严格递增，不做方向镜像**。L 方向（EVE/IBL）指标的段按
   "红线 → 标杆线 → 过优" 的**语义顺序**编号，区间本身递减。
   引擎按 seg_order 升序取首个命中（闭区间 [min,max]），
   因此段的区间必须是**互不重叠的闭区间序列**，且第一个命中的段
   就是正确的段。
   —— 线上 v12b 的 EVE 规则正是踩了这个坑：段 1=[15,999] 会被
      所有 x>=15 命中，段 2~6 区间倒序且与段 12~16 交错，
      导致 x=8.40 实际命中段 12（480 分）而库里存 440 分。

3. **L 方向用「反向编号」保证闭区间首命中正确**：
   段 1  = 红线区 [a0, +∞)        → 0 分
   段 2-6  = 危险区 (a1,a0] 递减  → 0→150
   段 7-11 = 预警区 (a2,a1] 递减  → 150→300
   段 12-16= 安全区 (a4,a2] 递减 → 300→500
   段 17  = 标杆单点 [a4,a4]      → 500
   段 18-22 = 过优区 (a4-delta,a4) → 500→floor/flat
   段 23  = 极值区 [0, a4-delta)   → floor/flat
   注意：**段 12 的区间上界必须严格小于段 11 的下界**，否则
   x 落在交界处会先命中段 12（seg_order 更小）而拿到高档分。

4. **score / score_min 语义**（对齐 backend/app/routers/kpi.py L778-812）：
   - score     = 该段**区间上界**处的分数
   - score_min = 该段**区间下界**处的分数
   - 段内插值  = score_min + (x-min)/(max-min) × (score-score_min)
   单点段 (min==max) 不插值，直接取 score。

5. 幂等：每次执行软删该 kpi 旧规则+旧段(is_deleted=1)，再建新规则。
"""
import sys
from decimal import Decimal

sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text

DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
eng = create_engine(DB_URL)

# ============== v14 锚点（百分数单位，与 docs/v2/评分标准_v14_锚点重标定.xlsx 一致） ==============
# dir: H=越高越好 / L=越低越好
# over: penalty=过优后扣分 / flat=过优封顶 500
# floor: 极值档下限分（仅 penalty 生效）
IND = {
    "LCR": dict(dir="H", over="penalty", a0=120.0, a1=133.0, a2=139.0, a4=146.0,
                delta=10.0, floor=300.0, w=0.16, act=144.22,
                name="流动性覆盖率", desc="LCR 流动性覆盖率"),
    "NSFR": dict(dir="H", over="penalty", a0=100.0, a1=101.5, a2=102.8, a4=105.2,
                 delta=5.0, floor=300.0, w=0.13, act=104.65,
                 name="净稳定资金比例", desc="NSFR 净稳定资金比例"),
    "EVE": dict(dir="L", over="penalty", a0=170.0, a1=140.0, a2=80.0, a4=60.0,
                delta=40.0, floor=450.0, w=0.12, act=61.3947,
                name="银行账户利率风险", desc="EVE 经济价值变动（IRRBB）"),
    "CET1": dict(dir="H", over="penalty", a0=8.7, a1=9.0, a2=9.2, a4=10.0,
                 delta=2.0, floor=300.0, w=0.16, act=9.48,
                 name="核心一级资本充足率", desc="CET1 核心一级资本充足率"),
    "CAR": dict(dir="H", over="penalty", a0=11.0, a1=11.8, a2=12.2, a4=13.0,
                delta=3.0, floor=300.0, w=0.10, act=12.80,
                name="资本充足率", desc="CAR 资本充足率"),
    "ROE": dict(dir="H", over="flat", a0=6.0, a1=7.5, a2=8.5, a4=12.0,
                delta=3.0, floor=300.0, w=0.12, act=9.39,
                name="净资产收益率", desc="ROE 净资产收益率"),
    "IBL": dict(dir="L", over="flat", a0=33.33, a1=30.0, a2=25.0, a4=20.0,
                delta=3.0, floor=300.0, w=0.11, act=21.60,
                name="同业负债占总负债比例", desc="IBL 同业负债占总负债比例"),
    "LR": dict(dir="H", over="penalty", a0=4.25, a1=5.6, a2=6.3, a4=8.0,
               delta=4.0, floor=300.0, w=0.10, act=7.09,
               name="杠杆率", desc="LR 杠杆率"),
}

# ============== KPI 代码映射（双体系自适应）==================
# 服务器生产库：REG_* 体系（scheme_id=1 SCH_DEFAULT）
#   1 REG_LCR  2 REG_NSFR  3 REG_CET1  4 REG_EVE  5 REG_ROE
# 本地开发库：KPI_PNN_* 体系（scheme_id=3 SCH_PNN_TRAIN）
#   6 KPI_PNN_ROE  7 KPI_PNN_CET1  8 KPI_PNN_LCR  9 KPI_PNN_NSFR  10 KPI_PNN_DEVE
# 新增指标在两套体系各建一份：REG_CAR / KPI_PNN_CAR 等。
KPI_CODE_REG = {
    "LCR": "REG_LCR",
    "NSFR": "REG_NSFR",
    "EVE": "REG_EVE",
    "CET1": "REG_CET1",
    "CAR": "REG_CAR",
    "ROE": "REG_ROE",
    "IBL": "REG_IBL",
    "LR": "REG_LR",
}
KPI_CODE_PNN = {
    "LCR": "KPI_PNN_LCR",
    "NSFR": "KPI_PNN_NSFR",
    "EVE": "KPI_PNN_DEVE",
    "CET1": "KPI_PNN_CET1",
    "CAR": "KPI_PNN_CAR",
    "ROE": "KPI_PNN_ROE",
    "IBL": "KPI_PNN_IBL",
    "LR": "KPI_PNN_LR",
}
ORDER = ["LCR", "NSFR", "EVE", "CET1", "CAR", "ROE", "IBL", "LR"]

# 报表归属：RPT_RWA(19) 承载资本/流动性监管指标
RPT_ID = 19
SCHEME_ID = 1          # SCH_DEFAULT（与线上 v12b 规则一致）


# ============== 段生成 ==============
def build_segments(cfg):
    """生成 23 段。

    返回 [(seg_order, min_value, max_value, score, score_min, desc), ...]
    单位：百分数。score=区间上界分，score_min=区间下界分。

    区间设计保证 **闭区间 [min,max] 互不重叠**，且 seg_order 升序
    遍历时首个命中即正确段（L 方向亦然）。
    """
    d = cfg["dir"]
    a0, a1, a2, a4 = cfg["a0"], cfg["a1"], cfg["a2"], cfg["a4"]
    delta = cfg["delta"]
    floor = cfg["floor"]
    flat = cfg["over"] == "flat"
    segs = []

    if d == "H":
        # ---- 段1 红线 [0, a0] → 0 分 ----
        segs.append((1, 0.0, a0, 0.0, 0.0, "🔴 不达标 (≤红线)"))
        # ---- 段2-6 危险 (a0,a1] → 0→150，每段 30 ----
        step = (a1 - a0) / 5.0
        for i in range(5):
            lo = a0 + step * i
            hi = a0 + step * (i + 1)
            segs.append((2 + i, lo, hi, 30.0 * (i + 1), 30.0 * i, "🟠 危险 0-150"))
        # ---- 段7-11 预警 (a1,a2] → 150→300，每段 30 ----
        step = (a2 - a1) / 5.0
        for i in range(5):
            lo = a1 + step * i
            hi = a1 + step * (i + 1)
            segs.append((7 + i, lo, hi, 150.0 + 30.0 * (i + 1), 150.0 + 30.0 * i, "🟡 预警 150-300"))
        # ---- 段12-16 安全 (a2,a4] → 300→500，每段 40 ----
        step = (a4 - a2) / 5.0
        for i in range(5):
            lo = a2 + step * i
            hi = a2 + step * (i + 1)
            segs.append((12 + i, lo, hi, 300.0 + 40.0 * (i + 1), 300.0 + 40.0 * i, "🟢 安全 300-500"))
        # ---- 段17 标杆单点 [a4,a4] → 500 ----
        segs.append((17, a4, a4, 500.0, 500.0, "⭐ 适度最优 500 分"))
        # ---- 段18-22 过优 (a4, a4+delta] → 500→floor，每段 (500-floor)/5 ----
        if flat:
            for i in range(5):
                lo = a4 + delta / 5.0 * i
                hi = a4 + delta / 5.0 * (i + 1)
                segs.append((18 + i, lo, hi, 500.0, 500.0, "🟢 过优封顶 500 分"))
        else:
            step = (500.0 - floor) / 5.0
            for i in range(5):
                lo = a4 + delta / 5.0 * i
                hi = a4 + delta / 5.0 * (i + 1)
                segs.append((18 + i, lo, hi, 500.0 - step * (i + 1), 500.0 - step * i, "🟢 过优 500→减分"))
        # ---- 段23 极值 (a4+delta, +∞) ----
        # flat 模式：继续封顶 500（Excel 档位表口径，段23 的 J/I 列均为 500）
        # penalty 模式：落到 floor 分
        if flat:
            segs.append((23, a4 + delta, 999.0, 500.0, 500.0, "🟢 过优封顶 500 分"))
        else:
            segs.append((23, a4 + delta, 999.0, floor, floor,
                         "🟢 极度过剩 %g 分" % floor))
    else:
        # ================= L 方向（越低越好）=================
        # 段1 红线 [a0, +∞) → 0 分
        segs.append((1, a0, 999.0, 0.0, 0.0, "🔴 不达标 (≥红线)"))
        # 段2-6 危险 (a1,a0] 递减：区间上界分从 0 升到 150
        #   注意：区间递减 ⇒ score 必须挂在【区间上界】(=较小端)，因此
        #   段2 区间 [a1+step, a0]，score=0（在上界 a0 处为 0 分）… 等等，
        #   实际上 L 方向危险区内，x 越大越接近红线越差 → 分数越低。
        #   为保证闭区间首命中正确且插值方向一致，这里统一用：
        #   段 k 的区间 [b_k, b_{k-1}]（b 递减），score = 该段【较小端】的分数…
        #   —— 引擎按 (x-min)/(max-min) 插值，min 恒 < max，因此
        #      段内 x 增大 → 分数增大（score-score_min>0）。
        #      对 L 方向这是反的！故 L 方向段的 score 必须 < score_min，
        #      才能让 x 增大 → 分数减小。
        #   实现：段 k 的 [min,max]=[b_k, b_{k-1}]，min_value=b_k（更小的值端）
        #        score_min = 该段在 min_value 处的分数（较高分）
        #        score     = 该段在 max_value 处的分数（较低分）
        #   语义顺序：段2 最靠近标杆（最高分端），段6 最靠近红线。
        #   —— 引擎取首个命中：x 在 (a1,a0] 只会命中段2~6 之一，
        #      因为段1 是 [a0,999] 且 a0 与段6 的 max 重合，
        #      段6 的 max=a0 与段1 的 min=a0 重合，闭区间下 x=a0
        #      会先命中段1（seg_order 更小）→ 0 分，符合红线语义。✅
        step = (a0 - a1) / 5.0
        for i in range(5):
            # 段 k(2..6) 的区间 = [a1+(4-i)*step, a1+(5-i)*step]，即 seg_order
            # 升序 = 数值降序（段2 数值最高、最靠近红线）。
            # 分数：较小值端(lo)得分高、较大值端(hi)得分低，
            #       保证引擎插值 (x-min)/(max-min) 下 x 增大 → 分数减小。
            lo2 = a1 + (4 - i) * step
            hi2 = a1 + (5 - i) * step
            hi_score = 30.0 * i              # 段2:0, 段3:30, 段4:60, 段5:90, 段6:120
            lo_score = 30.0 * (i + 1)        # 段2:30, 段3:60, 段4:90, 段5:120, 段6:150
            segs.append((2 + i, lo2, hi2, hi_score, lo_score, "🟠 危险 0-150"))
        # ---- 段7-11 预警 (a2,a1] 递减 → 150→300 ----
        step = (a1 - a2) / 5.0
        for i in range(5):
            # 段7 最靠近 a1（分高 300 侧），段11 最靠近 a2（分低 150 侧）
            hi2 = a1 - step * i
            lo2 = hi2 - step
            hi_score = 150.0 + 30.0 * i        # 段7:150, 段8:180 ... 段11:270
            lo_score = 150.0 + 30.0 * (i + 1)  # 段7:180 ... 段11:300
            segs.append((7 + i, lo2, hi2, hi_score, lo_score, "🟡 预警 150-300"))
        # ---- 段12-16 安全 (a4,a2] 递减 → 300→500 ----
        step = (a2 - a4) / 5.0
        for i in range(5):
            hi2 = a2 - step * i
            lo2 = hi2 - step
            hi_score = 300.0 + 40.0 * i        # 段12:300 ... 段16:460
            lo_score = 300.0 + 40.0 * (i + 1)  # 段12:340 ... 段16:500
            segs.append((12 + i, lo2, hi2, hi_score, lo_score, "🟢 安全 300-500"))
        # ---- 段17 标杆单点 [a4,a4] → 500 ----
        segs.append((17, a4, a4, 500.0, 500.0, "⭐ 适度最优 500 分"))
        # ---- 段18-22 过优 (a4-delta, a4) → 500→floor / flat ----
        # 语义顺序：段18 最靠近 a4（分高），段22 最远（分低）
        if flat:
            for i in range(5):
                hi2 = a4 - delta / 5.0 * i
                lo2 = hi2 - delta / 5.0
                segs.append((18 + i, lo2, hi2, 500.0, 500.0, "🟢 过优封顶 500 分"))
        else:
            step = (500.0 - floor) / 5.0
            for i in range(5):
                hi2 = a4 - delta / 5.0 * i
                lo2 = hi2 - delta / 5.0
                # 段18 最靠近 a4：hi 端 500，lo 端 500-step
                hi_score = 500.0 - step * i
                lo_score = 500.0 - step * (i + 1)
                segs.append((18 + i, lo2, hi2, hi_score, lo_score, "🟢 过优 500→减分"))
        # ---- 段23 极值 [0, a4-delta) ----
        # flat 模式：继续封顶 500（Excel 档位表口径，段23 的 J/I 列均为 500）
        # penalty 模式：落到 floor 分
        if flat:
            segs.append((23, 0.0, a4 - delta, 500.0, 500.0, "🟢 过优封顶 500 分"))
        else:
            segs.append((23, 0.0, a4 - delta, floor, floor,
                         "🟢 极度过剩 %g 分" % floor))

    # ---- 闭区间重叠处理 ----
    # 引擎用闭区间 [min,max] 且按 seg_order 升序取首个命中。
    # 若相邻两段共享端点 E，则 x=E 会被两段覆盖，先命中 seg_order 小者。
    #   H 方向：段k.max=E（高分端）先命中 → 得段k的上界分（正确，且 = 段k+1下界分）
    #   L 方向：段k.max=E 是【大值端=低分端】先命中 → 得段k的低分端分（也正确）
    # 因此 H/L 两方向下"前段先命中"恰好都给出该边界的正确分数。
    # 唯一例外是单点标杆段(段17)与段16/段18 在 a4 处三重覆盖：
    #   x=a4 时段16(seg小)先命中，得段16上界分=500 ✅ 与段17一致。
    # 故无需 EPS 微调，保持与 Excel 档位表端点完全一致。
    return segs


# ============== KPI 定义（新增指标） ==============
NEW_KPIS = {
    "CAR": dict(name="资本充足率", unit="PERCENT"),
    "IBL": dict(name="同业负债占总负债比例", unit="PERCENT"),
    "LR": dict(name="杠杆率", unit="PERCENT"),
}



def engine_score(segs, x):
    """复刻 backend/app/routers/kpi.py PIECEWISE（闭区间，首个命中）。

    segs 支持两种元组长度：
      6 元组 (seg_order, min, max, score, score_min, desc) —— build_segments 输出
      5 元组 (seg_order, min, max, score, score_min)      —— 从数据库回读的段
    """
    for s in segs:
        so, mn, mx, sc, smin = s[0], s[1], s[2], s[3], s[4]
        if mn is not None and x < mn:
            continue
        if mx is not None and x > mx:
            continue
        if smin is not None and mn is not None and mx is not None and mx > mn:
            ratio = (x - mn) / (mx - mn)
            return smin + ratio * (sc - smin)
        return sc
    return None


def theory_score(cfg, x):
    """解析分数函数 T(x)，与 build_score_standard_v14.py 一致。"""
    d = cfg["dir"]
    a0, a1, a2, a4 = cfg["a0"], cfg["a1"], cfg["a2"], cfg["a4"]
    delta = cfg["delta"]
    floor = cfg["floor"]
    if d == "H":
        if x <= a0:
            return 0.0
        if x <= a1:
            return (x - a0) / (a1 - a0) * 150.0
        if x <= a2:
            return 150.0 + (x - a1) / (a2 - a1) * 150.0
        if x <= a4:
            return 300.0 + (x - a2) / (a4 - a2) * 200.0
        if cfg["over"] == "flat":
            return 500.0
        if x >= a4 + delta:
            return floor
        return 500.0 - (x - a4) / delta * (500.0 - floor)
    else:
        if x >= a0:
            return 0.0
        if x >= a1:
            return (a0 - x) / (a0 - a1) * 150.0
        if x >= a2:
            return 150.0 + (a1 - x) / (a1 - a2) * 150.0
        if x >= a4:
            return 300.0 + (a2 - x) / (a2 - a4) * 200.0
        if cfg["over"] == "flat":
            return 500.0
        if x <= a4 - delta:
            return floor
        return 500.0 - (a4 - x) / delta * (500.0 - floor)


# ============== 落库主流程 ==============
def detect_systems(conn):
    """探测本库使用哪套 KPI 代码体系。

    返回 {体系名: [(指标, kpi_code, kpi_id, scheme_id), ...]}：
      'REG'  → 服务器生产库：REG_*，scheme_id=1
      'PNN'  → 本地开发库：KPI_PNN_*，scheme_id=3
    """
    found = {}
    for sysname, table in (('REG', KPI_CODE_REG), ('PNN', KPI_CODE_PNN)):
        codes = []
        for key in ORDER:
            row = conn.execute(text(
                "SELECT id, scheme_id FROM prcp_kpi_definition "
                "WHERE kpi_code=:c AND is_deleted=0 LIMIT 1"
            ), {"c": table[key]}).fetchone()
            if row:
                codes.append((key, table[key], row[0], row[1]))
        if codes:
            found[sysname] = codes
            print("  检测到体系 %-4s: %d 个已存在指标（%s ...）"
                  % (sysname, len(codes), codes[0][1]))
    if not found:
        raise RuntimeError("未检测到任何 KPI 代码体系（REG_* / KPI_PNN_*）")
    return found


def ensure_kpi_defs(conn, systems):
    """确保 8 个指标定义在每套体系中齐全。返回 {体系: {指标: kpi_id}}。"""
    ids = {}
    for sysname, table in (('REG', KPI_CODE_REG), ('PNN', KPI_CODE_PNN)):
        if sysname not in systems:
            continue
        ids[sysname] = {}
        existing = {k: (cid, sid) for (k, _c, cid, sid) in systems[sysname]}
        scheme_id = SCHEME_ID
        for _k, (_cid, sid) in existing.items():
            scheme_id = sid
            break
        for key in ORDER:
            code = table[key]
            if key in existing:
                ids[sysname][key] = existing[key][0]
                print("  [kpi] %-4s %-16s 存在 id=%s" % (sysname, code, existing[key][0]))
                continue
            meta = NEW_KPIS.get(key)
            if not meta:
                raise RuntimeError("指标 %s (%s) 不存在且未定义新增元数据" % (key, code))
            rid = conn.execute(text("""
                INSERT INTO prcp_kpi_definition
                (scheme_id, indicator_type, kpi_code, kpi_name, rpt_id, formula,
                 calc_unit, formula_desc, status, is_deleted, created_by, updated_by)
                VALUES (:s, 2, :c, :n, :r, NULL, :u, :d, 'ACTIVE', 0, 1, 1)
            """), {
                "s": scheme_id, "c": code, "n": meta["name"],
                "r": RPT_ID, "u": meta["unit"],
                "d": "2025年报 1.4.6 / 第三支柱 LIQ2 公开披露值",
            }).lastrowid
            ids[sysname][key] = rid
            print("  [kpi] %-4s %-16s 新建 id=%s" % (sysname, code, rid))
    return ids


def soft_delete_old(conn, kpi_id):
    """软删该 kpi 的现有规则。

    ⚠ 唯一索引 uk_kpi_rule = (kpi_id, rule_name, is_deleted)，
    同名规则只能存在一条 —— 若历史已留有同名软删记录，
    直接再软删会撞 Duplicate entry。故先把旧规则名改写为归档名
    （带时间戳）再置 is_deleted=1，腾出键位给新规则。
    """
    # 先把现存有效规则改名归档
    conn.execute(text("""
        UPDATE prcp_kpi_score_rule
        SET rule_name = CONCAT(rule_name, ' #archived@', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'))
        WHERE kpi_id = :k AND is_deleted = 0
    """), {"k": kpi_id})
    r = conn.execute(text(
        "UPDATE prcp_kpi_score_rule SET is_deleted=1 WHERE kpi_id=:k AND is_deleted=0"
    ), {"k": kpi_id})
    n1 = r.rowcount
    r = conn.execute(text("""
        UPDATE prcp_kpi_score_segment SET is_deleted=1
        WHERE rule_id IN (SELECT id FROM prcp_kpi_score_rule WHERE kpi_id=:k) AND is_deleted=0
    """), {"k": kpi_id})
    n2 = r.rowcount
    return n1, n2


def create_rule(conn, kpi_id, key, code, scheme_id):
    cfg = IND[key]
    higher = 1 if cfg["dir"] == "H" else 0
    rid = conn.execute(text("""
        INSERT INTO prcp_kpi_score_rule
        (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,
         description, status, is_deleted, created_by, updated_by)
        VALUES (:s, :k, :n, 'PIECEWISE', 500, :h, :d, 'ACTIVE', 0, 1, 1)
    """), {
        "s": scheme_id, "k": kpi_id,
        "n": "%s v14.1 锚点重标定+EVE口径修正 0-500 分评分" % code,
        "h": higher,
        "d": "基于 docs/v2/评分标准_v14_锚点重标定.xlsx - 锚点推导 23 段"
             "（红线→危险→预警→安全→适度最优→过优），段内线性插值",
    }).lastrowid

    segs = build_segments(cfg)
    for (so, mn, mx, sc, smin, desc) in segs:
        conn.execute(text("""
            INSERT INTO prcp_kpi_score_segment
            (rule_id, seg_order, min_value, max_value, score, score_min,
             segment_desc, is_deleted, created_at, updated_at)
            VALUES (:r, :o, :mn, :mx, :sc, :smin, :d, 0, NOW(), NOW())
        """), {
            "r": rid, "o": so,
            "mn": Decimal(str(round(mn, 6))),
            "mx": Decimal(str(round(mx, 6))),
            "sc": Decimal(str(round(sc, 2))),
            "smin": Decimal(str(round(smin, 2))),
            "d": desc,
        })
    print("  [rule] %-16s rule_id=%-4s 段数=%d dir=%s over=%s"
          % (code, rid, len(segs), cfg["dir"], cfg["over"]))
    return rid


def refresh_values(conn, ids, base="2025-12-31"):
    """按公开披露实测量重算并写入 prcp_kpi_value。"""
    total_w = 0.0
    total_s = 0.0
    print("\n  --- 指标值刷新 (%s) ---" % base)
    for key in ORDER:
        cfg = IND[key]
        kpi_id = ids[key]
        val = cfg["act"]
        score = engine_score(build_segments(cfg), val)
        t = theory_score(cfg, val)
        if abs(score - t) > 1e-6:
            raise RuntimeError("%s 引擎分 %.4f != 解析分 %.4f" % (key, score, t))
        # 物理删除后重插（uk_kpi_date_ver 唯一键，软删不足）
        conn.execute(text(
            "DELETE FROM prcp_kpi_value WHERE kpi_id=:k AND data_date=:d"
        ), {"k": kpi_id, "d": base})
        conn.execute(text("""
            INSERT INTO prcp_kpi_value
            (kpi_id, data_date, version, current_value, prev_value, prev_year_value,
             calc_source, score, is_deleted, created_by, updated_by)
            VALUES (:k, :d, 'V1.0', :v, NULL, NULL, 'MODEL', :sc, 0, 1, 1)
        """), {"k": kpi_id, "d": base, "v": Decimal(str(val)),
              "sc": Decimal(str(round(score, 2)))})
        total_w += cfg["w"]
        total_s += cfg["w"] * score
        print("    %-6s %-9s 得分 %-7.2f 权重 %d%%"
              % (key, val, score, round(cfg["w"] * 100)))
    print("  权重合计 = %.2f   加权总分 = %.2f / 500   /100 = %.2f"
          % (total_w, total_s, total_s / 5.0))
    return total_s


def self_check(conn, ids, codes, scheme_id, base="2025-12-31"):
    """落库后回读校验：段数、引擎复算、实测得分一致性。"""
    ok = True
    for key in ORDER:
        code = codes[key]
        row = conn.execute(text("""
            SELECT r.id FROM prcp_kpi_score_rule r
            JOIN prcp_kpi_definition d ON d.id=r.kpi_id AND d.is_deleted=0
            WHERE d.kpi_code=:c AND r.is_deleted=0 AND r.calc_method='PIECEWISE'
              AND r.scheme_id=:s
        """), {"c": code, "s": scheme_id}).fetchall()
        if len(row) != 1:
            print("  x %-16s 有效规则数=%d（应为 1）" % (code, len(row)))
            ok = False
            continue
        rid = row[0][0]
        segs = conn.execute(text("""
            SELECT seg_order, min_value, max_value, score, score_min
            FROM prcp_kpi_score_segment WHERE rule_id=:r AND is_deleted=0 ORDER BY seg_order
        """), {"r": rid}).fetchall()
        if len(segs) != 23:
            print("  x %-16s 段数=%d（应为 23）" % (code, len(segs)))
            ok = False
        db_segs = [(int(s[0]), float(s[1]), float(s[2]), float(s[3]), float(s[4]))
                   for s in segs]
        vrow = conn.execute(text("""
            SELECT current_value, score FROM prcp_kpi_value
            WHERE kpi_id=:k AND data_date=:d AND is_deleted=0
        """), {"k": ids[key], "d": base}).fetchone()
        if not vrow:
            print("  x %-16s 无 %s 指标值" % (code, base))
            ok = False
            continue
        x = float(vrow[0])
        e = engine_score(db_segs, x)
        t = theory_score(IND[key], x)
        stored = float(vrow[1])
        dmax = max(abs(e - t), abs(e - stored))
        st = "OK" if dmax < 0.02 else "x"
        if dmax >= 0.02:
            ok = False
        print("  %-3s %-16s 段=%d 值=%-9s 引擎=%-8.2f 解析=%-8.2f 库存=%-8.2f d=%.4f"
              % (st, code, len(segs), x, e, t, stored, dmax))
    return ok


def main():
    print("=" * 100)
    print("评分标准 v14 锚点重标定 · 规则落库")
    print("=" * 100)

    with eng.connect() as conn:
        print("\n=== 0. KPI 代码体系探测 ===")
        systems = detect_systems(conn)

    all_ok = True
    for sysname in systems:
        table = KPI_CODE_REG if sysname == 'REG' else KPI_CODE_PNN
        print("\n" + "=" * 100)
        print("体系 %s" % sysname)
        print("=" * 100)

        with eng.begin() as conn:
            print("\n=== 1. KPI 定义 ===")
            all_ids = ensure_kpi_defs(conn, systems)
            ids = all_ids[sysname]
            scheme_id = conn.execute(text(
                "SELECT scheme_id FROM prcp_kpi_definition WHERE id=:i"
            ), {"i": ids[ORDER[0]]}).scalar()

        with eng.begin() as conn:
            print("\n=== 2. 评分规则 + 23 段 ===")
            for key in ORDER:
                n1, n2 = soft_delete_old(conn, ids[key])
                print("  %-16s (软删 rule -%d, segment -%d)" % (table[key], n1, n2))
                create_rule(conn, ids[key], key, table[key], scheme_id)

        with eng.begin() as conn:
            print("\n=== 3. 指标值刷新 ===")
            refresh_values(conn, ids)

        with eng.begin() as conn:
            print("\n=== 4. 落库回读校验 ===")
            ok = self_check(conn, ids, table, scheme_id)
            print("  体系 %s 校验: %s" % (sysname, "PASS" if ok else "FAIL"))
            all_ok = all_ok and ok

    print("\n" + "=" * 100)
    print("结果: %s" % ("PASS —— v14 已落库" if all_ok else "FAIL"))
    print("=" * 100)
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
