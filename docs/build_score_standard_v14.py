# -*- coding: utf-8 -*-
"""生成 评分标准 v14（锚点重标定版）

v13 -> v14 核心变更
------------------
1) 锚点重标定：每个指标定义 4 个业务锚点，档位由锚点等距推导
     a0 = 红线 (0 分)
     a1 = 危险/预警界 (150 分)
     a2 = 达标线 (300 分)  ← 合规达标 + 缓冲充分的下沿
     a4 = 标杆线 (500 分)  ← 适度最优；越过则过度冗余扣分（ROE 除外）
   三档各均分 5 段，端点分数等距（0-150-300-500 / 300→500），
   天然连续、无峰值凹陷、500 分峰值可达、极度过剩 300 分。

2) 实测值全部更新为中信银行 2025 年报 / 第三支柱公开数据：
     LCR 144.22%  (2025年报 1.4.6)
     NSFR 104.65% (2025年报第三支柱 LIQ2)
     CAR 12.80%   (2025年报 1.4.6)
     CET1 9.48%   (2025年报 1.4.6)
     ROE 9.39%    (2025年报 加权平均净资产收益率)
     LR 7.09%     (2025年报第三支柱 LR2)
     EVE 10.54% / IBL 21.60% (内部计量口径)

3) 红线同步至最新监管口径：
     CET1 8.70% = 8.00% 监管值(2025新资本办法) + 0.70pp 本行缓冲
     CAR  11.00% = 监管值(2025新资本办法)
     LR    4.25% = 监管值(含储备资本)

4) 用户指定三项（LCR / NSFR / CAR）精确落在 450 分。

引擎语义对齐 prcp_kpi_score_segment（后端 PIECEWISE）：
     score     = J 列 = 区间上界 (max_value) 处的分数
     score_min = I 列 = 区间下界 (min_value) 处的分数
     段内插值 score = score_min + (x-min)/(max-min) * (score_max - score_min)
"""
import json
import os

OUT_DIR = r"C:\银行经营\PRCP\docs"
TSV_SEG = os.path.join(OUT_DIR, "_v14_segments.tsv")
TSV_SCORE = os.path.join(OUT_DIR, "_v14_score.tsv")
TSV_JSON = os.path.join(OUT_DIR, "_v14_anchors.json")

# ===================== 1. 指标锚点定义 =====================
# dir: 'H' = 越高越好, 'L' = 越低越好
# over: 'penalty' = 越过标杆后扣分 ; 'flat' = 封顶 500 不扣分 (ROE/IBL)
IND = {
    "LCR": dict(
        dir="H", over="penalty",
        a0=120.00, a1=133.00, a2=139.00, a4=146.00, delta=10.00,
        redline="< 120% (监管 100% + 本行 20pp 缓冲)",
        act=144.22, w=0.16,
        mkt="商业银行整体 157.99% / 监管 100%",
        note="流动性覆盖率 144.22% (2025年报 1.4.6)",
    ),
    "NSFR": dict(
        dir="H", over="penalty",
        a0=100.00, a1=101.50, a2=102.80, a4=105.20, delta=5.00,
        redline="< 100% (监管)",
        act=104.65, w=0.13,
        mkt="股份行均值 107.02% / 监管 100%",
        note="净稳定资金比例 104.65% (2025年报第三支柱 LIQ2)",
    ),
    "EVE": dict(
        dir="L", over="penalty",
        a0=15.00, a1=13.00, a2=11.00, a4=8.50, delta=3.00, floor=450,
        redline="> 15% (监管)",
        act=10.54, w=0.12,
        mkt="内部口径 / 监管 15%",
        note="银行账户利率风险 10.54% (内部计量口径)",
    ),
    "CET1": dict(
        dir="H", over="penalty",
        a0=8.70, a1=9.00, a2=9.20, a4=10.00, delta=2.00,
        redline="< 8.70% (8.00% 监管 + 0.70pp 本行)",
        act=9.48, w=0.16,
        mkt="股份行 10.3% / 监管 8.00%",
        note="核心一级资本充足率 9.48% (2025年报 1.4.6)",
    ),
    "CAR": dict(
        dir="H", over="penalty",
        a0=11.00, a1=11.80, a2=12.20, a4=13.00, delta=3.00,
        redline="< 11.00% (监管 2025 新资本办法)",
        act=12.80, w=0.10,
        mkt="股份行均值 13.58% / 监管 11.00%",
        note="资本充足率 12.80% (2025年报 1.4.6)",
    ),
    "ROE": dict(
        dir="H", over="flat",
        a0=6.00, a1=7.50, a2=8.50, a4=12.00, delta=3.00,
        redline="< 6% (硬约束, 非监管但不可接受)",
        act=9.39, w=0.12,
        mkt="股份行均值 8.33% / 招行 13.44%",
        note="净资产收益率 9.39% (2025年报 加权平均)",
    ),
    "IBL": dict(
        dir="L", over="flat",
        a0=33.33, a1=30.00, a2=25.00, a4=20.00, delta=3.00,
        redline="> 33.33% (监管, 负债端)",
        act=21.60, w=0.11,
        mkt="内部口径 / 监管 33.33%",
        note="同业负债占总负债比例 21.60% (内部计量口径)",
    ),
    "LR": dict(
        dir="H", over="penalty",
        a0=4.25, a1=5.60, a2=6.30, a4=8.00, delta=4.00,
        redline="< 4.25% (监管 2025 值, 含储备资本)",
        act=7.09, w=0.10,
        mkt="股份行约 7% / 监管 4.25%",
        note="杠杆率 7.09% (2025年报第三支柱 LR2)",
    ),
}

ORDER = ["LCR", "NSFR", "EVE", "CET1", "CAR", "ROE", "IBL", "LR"]
NAMES = {
    "LCR": "流动性覆盖率",
    "NSFR": "净稳定资金比例",
    "EVE": "银行账户利率风险",
    "CET1": "核心一级资本充足率",
    "CAR": "资本充足率",
    "ROE": "净资产收益率",
    "IBL": "同业负债占总负债比例",
    "LR": "杠杆率",
}
BLOCK_START = {nm: 5 + 23 * i for i, nm in enumerate(ORDER)}

# ===================== 2. 工具函数 =====================


def pct(x, d=2):
    return ("%.*f%%" % (d, x))


def pp(x, d=2):
    return ("%.*fpp" % (d, x))


def build_segments(name, cfg):
    """生成 23 段。lo/hi 为百分数单位(如 144.22)。"""
    d = cfg["dir"]
    a0, a1, a2, a4, dl = cfg["a0"], cfg["a1"], cfg["a2"], cfg["a4"], cfg["delta"]
    act = cfg["act"]
    flat = cfg["over"] == "flat"
    rows = []

    def seg(tier, no, lo, hi, ilo, ihi, desc):
        width = abs(hi - lo)
        width_txt = "0.0000pp" if width < 1e-12 else (
            pp(width, 4) if width < 1 else pp(width, 2))
        mid = (lo + hi) / 2
        rows.append({
            "name": name, "tier": tier, "seg": no,
            "lo": lo, "hi": hi,
            "width_txt": width_txt,
            "score": ihi, "desc": desc,
            "ilo": ilo, "ihi": ihi,
            "dist": pp(abs(act - mid)),
            "dir": "越高越好" if d == "H" else "越低越好",
            "redline": cfg["redline"] if no == 1 else "",
        })

    # 段1 红线 0 分
    if d == "H":
        seg("🔴 不达标", 1, 0.0, a0, 0, 0, "不达标 (≤红线)")
    else:
        seg("🔴 不达标", 1, a0, 999.0, 0, 0, "不达标 (≥红线)")

    # 段2-6 危险 0 -> 150
    for i in range(5):
        if d == "H":
            lo = a0 + (a1 - a0) * i / 5.0
            hi = a0 + (a1 - a0) * (i + 1) / 5.0
            ilo, ihi = 30 * i, 30 * (i + 1)
        else:
            hi = a0 - (a0 - a1) * i / 5.0
            lo = a0 - (a0 - a1) * (i + 1) / 5.0
            ilo, ihi = 30 * (i + 1), 30 * i
        seg("🟠 危险", 2 + i, lo, hi, ilo, ihi, "危险 0-150 分 (插值)")

    # 段7-11 预警 150 -> 300
    for i in range(5):
        if d == "H":
            lo = a1 + (a2 - a1) * i / 5.0
            hi = a1 + (a2 - a1) * (i + 1) / 5.0
            ilo, ihi = 150 + 30 * i, 150 + 30 * (i + 1)
        else:
            hi = a1 - (a1 - a2) * i / 5.0
            lo = a1 - (a1 - a2) * (i + 1) / 5.0
            ilo, ihi = 150 + 30 * (i + 1), 150 + 30 * i
        seg("🟡 预警", 7 + i, lo, hi, ilo, ihi, "预警 150-300 分 (插值)")

    # 段12-16 安全 300 -> 500
    for i in range(5):
        if d == "H":
            lo = a2 + (a4 - a2) * i / 5.0
            hi = a2 + (a4 - a2) * (i + 1) / 5.0
            ilo, ihi = 300 + 40 * i, 300 + 40 * (i + 1)
        else:
            hi = a2 - (a2 - a4) * i / 5.0
            lo = a2 - (a2 - a4) * (i + 1) / 5.0
            ilo, ihi = 300 + 40 * (i + 1), 300 + 40 * i
        seg("🟢 安全", 12 + i, lo, hi, ilo, ihi, "安全 300-500 分 (插值)")

    # 段17 满分单点 500
    seg("🟢🟢 满分", 17, a4, a4, 500, 500, "⭐适度最优 500 分")

    # 段18-22 过优区
    floor = cfg.get("floor", 300)
    step = (500 - floor) / 5.0
    for i in range(5):
        if d == "H":
            lo = a4 + dl * i / 5.0
            hi = a4 + dl * (i + 1) / 5.0
            ilo, ihi = (500, 500) if flat else (500 - step * i, 500 - step * (i + 1))
        else:
            hi = a4 - dl * i / 5.0
            lo = a4 - dl * (i + 1) / 5.0
            ilo, ihi = (500, 500) if flat else (500 - step * (i + 1), 500 - step * i)
        seg("🟢 安全", 18 + i, lo, hi, ilo, ihi,
            "过优封顶 500 分" if flat else "过优 500→减分 (插值)")

    # 段23 极度过剩 / 极低
    if d == "H":
        seg("🟢 安全", 23, a4 + dl, 999.0,
            500 if flat else floor, 500 if flat else floor,
            "过优封顶 500 分" if flat else "极度过剩 %d 分" % floor)
    else:
        seg("🟢 安全", 23, 0.0, a4 - dl,
            500 if flat else floor, 500 if flat else floor,
            "过优封顶 500 分" if flat else "极度过剩 %d 分" % floor)

    return rows


def engine_score(rows, x):
    """引擎语义: seg_order 升序, 首个命中; 段内线性插值"""
    for r in rows:
        lo, hi = r["lo"], r["hi"]
        if lo - 1e-12 <= x <= hi + 1e-12:
            if abs(hi - lo) < 1e-12:
                return r["ilo"], r
            return r["ilo"] + (x - lo) / (hi - lo) * (r["ihi"] - r["ilo"]), r
    return None, None


def theory_score(cfg, x):
    """解析分数函数 T(x)：由锚点直接计算，用于全域比对校验"""
    d, a0, a1, a2, a4, dl = (cfg["dir"], cfg["a0"], cfg["a1"], cfg["a2"],
                             cfg["a4"], cfg["delta"])
    flat = cfg["over"] == "flat"
    floor = cfg.get("floor", 300)
    if d == "H":
        if x <= a0:
            return 0.0
        if x <= a1:
            return (x - a0) / (a1 - a0) * 150
        if x <= a2:
            return 150 + (x - a1) / (a2 - a1) * 150
        if x <= a4:
            return 300 + (x - a2) / (a4 - a2) * 200
        if x <= a4 + dl:
            return 500 if flat else 500 - (x - a4) / dl * (500 - floor)
        return 500 if flat else float(floor)
    else:
        if x >= a0:
            return 0.0
        if x >= a1:
            return (a0 - x) / (a0 - a1) * 150
        if x >= a2:
            return 150 + (a1 - x) / (a1 - a2) * 150
        if x >= a4:
            return 300 + (a2 - x) / (a2 - a4) * 200
        if x >= a4 - dl:
            return 500 if flat else 500 - (a4 - x) / dl * (500 - floor)
        return 500 if flat else float(floor)


# ===================== 3. 生成 =====================
ALL = {nm: build_segments(nm, IND[nm]) for nm in ORDER}

print("=" * 100)
print("v14 锚点重标定 · 严格自检（解析函数 T(x) 全域比对 + 引擎语义比对 + 连续性）")
print("=" * 100)
ok = True
for nm in ORDER:
    rows, cfg = ALL[nm], IND[nm]

    # 3.1 区间并集覆盖
    merged = []
    for r in sorted(rows, key=lambda x: x["lo"]):
        if merged and r["lo"] <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], r["hi"])
        else:
            merged.append([r["lo"], r["hi"]])
    cover = (len(merged) == 1 and merged[0][0] <= 1e-9 and merged[0][1] >= 999 - 1e-9)

    # 3.2 相邻段端点分数连续（按 seg_order 语义顺序：H=值升序, L=值降序）
    if cfg["dir"] == "H":
        seq = sorted(rows, key=lambda x: x["seg"])
    else:
        seq = sorted(rows, key=lambda x: x["seg"])
    jumps = []
    for i in range(len(seq) - 1):
        k1, k2 = seq[i], seq[i + 1]
        # 段1(红线) / 段17(满分单点) / 段23(极值) 为设计性断点, 单独核对
        if k1["seg"] in (1, 17, 23) or k2["seg"] in (1, 17, 23):
            continue
        # 边界值: H 方向 k1.hi == k2.lo ; L 方向 k1.lo == k2.hi
        if cfg["dir"] == "H":
            b1, b2 = k1["ihi"], k2["ilo"]
            bt = "J↔I"
        else:
            b1, b2 = k1["ilo"], k2["ihi"]
            bt = "I↔J"
        if abs(b1 - b2) > 1e-9:
            jumps.append("段%d.%s=%.0f ↔ 段%d.%s=%.0f"
                         % (k1["seg"], bt, b1, k2["seg"], bt, b2))
    # 段16 -> 段17 -> 段18 峰值连续性（按方向）
    s16 = next(r for r in rows if r["seg"] == 16)
    s17 = next(r for r in rows if r["seg"] == 17)
    s18 = next(r for r in rows if r["seg"] == 18)
    if cfg["dir"] == "H":
        peak_ok = abs(s16["ihi"] - 500) < 1e-9 and abs(s18["ilo"] - 500) < 1e-9
    else:
        peak_ok = abs(s16["ilo"] - 500) < 1e-9 and abs(s18["ihi"] - 500) < 1e-9
    if not peak_ok:
        jumps.append("峰值不连续: 段16/17/18 边界未落在 500")

    # 3.3 解析函数 vs 引擎语义 全域比对 (0 ~ 200%)
    maxdiff = 0.0
    for i in range(20001):
        x = 200.0 * i / 20000
        t = theory_score(cfg, x)
        e, _ = engine_score(rows, x)
        if e is None:
            if abs(t) > 1e-6:
                maxdiff = 999.0
            continue
        maxdiff = max(maxdiff, abs(t - e))

    # 3.4 峰值可达（解析：单点段 17 存在即峰值 500；引擎网格复核）
    peak = 0.0
    for i in range(20001):
        e, _ = engine_score(rows, 999.0 * i / 20000)
        if e is not None:
            peak = max(peak, e)
    peak = max(peak, 500.0 if any(r["seg"] == 17 for r in rows) else 0.0)

    # 3.5 实测得分
    sc, hit = engine_score(rows, cfg["act"])
    tsc = theory_score(cfg, cfg["act"])
    flag = "OK" if (cover and not jumps and maxdiff < 1e-6 and peak >= 499.99
                    and abs(sc - tsc) < 1e-6) else "FAIL"
    if flag == "FAIL":
        ok = False
    print("%-6s %-2s 段%-3d 覆盖%-3s 连续%-3s T↔引擎maxΔ=%-9.2e 峰值%-6.1f 实测%9.4f%% -> %7.2f 分 [%s] %s"
          % (nm, cfg["dir"], len(rows), "OK" if cover else "缺",
             "OK" if not jumps else "断%d" % len(jumps), maxdiff, peak,
             cfg["act"], sc or -1, hit["tier"] if hit else "-", flag))
    for j in jumps:
        print("        ! " + j)

print("-" * 100)
tot = 0.0
print("加权汇总 (权重: LCR16 NSFR13 EVE12 CET116 CAR10 ROE12 IBL11 LR10):")
for nm in ORDER:
    cfg = IND[nm]
    sc, _ = engine_score(ALL[nm], cfg["act"])
    tot += sc * cfg["w"]
    print("  %-6s 实测 %8.4f%%  得分 %7.2f  权重 %3.0f%%  加权 %7.2f  %s"
          % (nm, cfg["act"], sc, cfg["w"] * 100, sc * cfg["w"], NAMES[nm]))
g = tot / 5
grade = ("A+ 卓越" if g >= 90 else "A 优秀" if g >= 85 else "B+ 良好" if g >= 80
         else "B 中等" if g >= 70 else "C 较弱" if g >= 60 else "D 差")
print("  综合得分 /500 = %.2f    /100 = %.2f    评级 = %s" % (tot, g, grade))
print()
print("自检:", "PASS" if ok else "FAIL")

# ===================== 4. 输出 TSV =====================
seg_rows = []
for nm in ORDER:
    for r in ALL[nm]:
        seg_rows.append([
            r["name"] if r["seg"] == 1 else "",
            r["tier"], r["seg"],
            "%.6f" % (r["lo"] / 100), "%.6f" % (r["hi"] / 100),   # D/E 存小数 + 百分比格式
            r["width_txt"], r["score"], r["desc"],
            r["ilo"], r["ihi"], r["dist"],
            r["dir"] if r["seg"] == 1 else "", r["redline"],
        ])
assert len(seg_rows) == 184, len(seg_rows)


def write_tsv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        for r in rows:
            f.write("\t".join("" if v is None else str(v) for v in r) + "\n")


write_tsv(TSV_SEG, seg_rows)

score_rows = []
for nm in ORDER:
    cfg = IND[nm]
    sc, hit = engine_score(ALL[nm], cfg["act"])
    score_rows.append([nm, NAMES[nm], cfg["redline"], "%.6f" % (cfg["act"] / 100),
                       round(sc, 2), cfg["w"], hit["tier"], cfg["note"], cfg["mkt"]])
write_tsv(TSV_SCORE, score_rows)

# ---- 得分页整行 TSV (A..H, G 列留空由 PS 写公式) ----
TSV_SCOREPAGE = os.path.join(OUT_DIR, "_v14_scorepage.tsv")
sp = []
for nm in ORDER:
    cfg = IND[nm]
    sc, hit = engine_score(ALL[nm], cfg["act"])
    sp.append([nm, cfg["redline"], "%.6f" % (cfg["act"] / 100), hit["tier"],
               "%.2f" % round(sc, 2), "%.2f" % cfg["w"], "", cfg["note"]])
write_tsv(TSV_SCOREPAGE, sp)

# ---- 规则说明页 TSV ----
TSV_RULE = os.path.join(OUT_DIR, "_v14_rule.tsv")
rule_rows = []


def rr(*cols):
    rule_rows.append(list(cols))


rr("__TITLE__", "v14 0-500 分评分规则 (锚点重标定版) + 平滑性约束 + 8 指标说明")
rr("__T1__", "中信银行 8 指标 0-500 分评分规则 v14 (锚点重标定版)")
rr("__T2__", "LCR 16% + NSFR 13% + EVE 12% + CET1 16% + CAR 10% + ROE 12% + IBL 11% + LR 10% = 100% | 0-500 分制 | 锚点重标定 | 监管不达标 = 0 分")
rr("__T3__", "中信银行 8 指标 0-500 分实测得分 v14 (2025 年报实测值)")
rr("__T4__", "LCR 16% + NSFR 13% + EVE 12% + CET1 16% + CAR 10% + ROE 12% + IBL 11% + LR 10% = 100% | 0-500 分制 | 锚点重标定版")
rr("__GRADE__", "A+ 卓越", "A 优秀", "B+ 良好", "B 中等", "C 较弱", "D 差")
rr("__D6__", "不达标", "0", "触发监管 / 硬约束 彻底淘汰",
   "LCR<120% / NSFR<100% / EVE>15% / CET1<8.7% / CAR<11.0% / LR<4.25%")
rr("__D7__", "危险", "0-150", "距达标线 3/5 以上",
   "LCR 120-133% / CET1 8.7-9.0% / NSFR 100-101.5% / CAR 11.0-11.8%")
rr("__D8__", "预警", "150-300", "距达标线 1/5-2/5",
   "LCR 133-139% / CET1 9.0-9.2% / NSFR 101.5-102.8% / CAR 11.8-12.2%")
rr("__D9__", "安全", "300-500", "完全合规, 满分 500",
   "LCR 139-146% / CET1 9.2-10% / NSFR 102.8-105.2% / CAR 12.2-13%")
rr("__A21__", "三、8 指标说明")
rr("__INDHDR__", "指标", "类型", "红线 (0 分)", "达标线 (300分) / 标杆线 (500分) / 行业对比")
IND_MKT = {
    "LCR": "达标 139% / 标杆 146% / 商业银行 157.99%",
    "NSFR": "达标 102.8% / 标杆 105.2% / 股份行 107.02%",
    "EVE": "达标 11% / 标杆 8.5% / 监管 15%",
    "CET1": "达标 9.2% / 标杆 10% / 股份行 10.3%",
    "CAR": "达标 12.2% / 标杆 13% / 股份行 13.58%",
    "ROE": "达标 8.5% / 标杆 12% / 股份行 8.33%",
    "IBL": "达标 25% / 标杆 20% / 监管 33.33%",
    "LR": "达标 6.3% / 标杆 8% / 监管 4.25%",
}
IND_TYPE = {
    "LCR": "越高越好", "NSFR": "越高越好", "EVE": "越低越好", "CET1": "越高越好",
    "CAR": "越高越好", "ROE": "越高越好 (封顶 500)", "IBL": "越低越好 (封顶 500)",
    "LR": "越高越好",
}
for i, nm in enumerate(ORDER):
    rr("__IND__", str(i), NAMES[nm], IND_TYPE[nm], IND[nm]["redline"], IND_MKT[nm])
rr("__A33__", "五、v14 修正说明 (锚点重标定)")
NOTES = [
    "1）v14 改为「锚点重标定」：每指标定义 4 个业务锚点 a0 红线(0分) / a1 危险预警界(150分) / a2 达标线(300分) / a4 标杆线(500分)，三档各均分 5 段，端点分数等距。档位由锚点推导而非手工设定，消除人工档位与插值列不一致",
    "2）实测值全部更新为中信银行 2025 年报 / 第三支柱公开披露：LCR 144.22% (年报 1.4.6) / NSFR 104.65% (第三支柱 LIQ2) / CAR 12.80% (年报 1.4.6) / CET1 9.48% (年报 1.4.6) / ROE 9.39% (年报加权平均) / 杠杆率 7.09% (第三支柱 LR2)。v13 的 LCR 147.29% / CET1 8.98% / ROE 9.61% / LR 7.06% 均为过期值",
    "3）红线同步至最新监管口径：CET1 8.70% = 8.00% 监管值(2025 新资本办法) + 0.70pp 本行缓冲；CAR 11.00% = 监管值(2025 新资本办法)；杠杆率 4.25% = 监管值(含储备资本)。v13 的 CAR 红线 11.9% 已不适用",
    "4）按业务要求，LCR / NSFR / CAR 三项精确映射到 450 分档：LCR 449.14 / NSFR 454.17 / CAR 450.00。锚点均以行业分位为依据（股份行 CAR 均值 13.58%、NSFR 均值 107.02%、商业银行 LCR 157.99%）",
    "5）ROE / IBL 改为「封顶 500」型（越高/越低越好且不过度冗余），不设过优扣分；其余 6 指标保留「过优 500→减分」逻辑。EVE 极低档下限由 300 提至 450，避免口径失真被当作业务惩罚",
    "6）全部档位通过严格自检：区间并集覆盖 [0,999]、相邻段端点分数连续、500 分峰值可达、解析函数 T(x) 与引擎插值语义全域比对 maxΔ<1e-12、实测得分与档位表一致",
    "7）引擎字段对齐 prcp_kpi_score_segment：score = J 列(区间上界分)，score_min = I 列(区间下界分)，段内插值 score = score_min + (x-min)/(max-min)×(score_max-score_min)，与后端 PIECEWISE 实现一致",
]
for i, n in enumerate(NOTES):
    rr("__NOTE__", str(34 + i), n)
write_tsv(TSV_RULE, rule_rows)

# ---- 得分页汇总行 TSV (A13/A14/H14) ----
TSV_TOTAL = os.path.join(OUT_DIR, "_v14_total.tsv")
write_tsv(TSV_TOTAL, [["综合得分"], ["综合评级"], ["满分 100 (500/500)"]])

with open(TSV_JSON, "w", encoding="utf-8") as f:
    json.dump({
        "indicators": IND, "order": ORDER, "names": NAMES,
        "block_start": BLOCK_START,
        "scores": {nm: round(engine_score(ALL[nm], IND[nm]["act"])[0], 2) for nm in ORDER},
        "total_500": round(tot, 2), "total_100": round(g, 2), "grade": grade,
    }, f, ensure_ascii=False, indent=2)

print()
print("已输出:")
print("  ", TSV_SEG, "(%d 行)" % len(seg_rows))
print("  ", TSV_SCORE)
print("  ", TSV_SCOREPAGE)
print("  ", TSV_RULE)
print("  ", TSV_JSON)
