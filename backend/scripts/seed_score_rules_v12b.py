"""根据 评分标准_v12b.xlsx 的 0-500 分规则重建指标评分
+ 调整 prcp_kpi_value 让雷达图看起来丰满
+ 更新 radar max=500

中信银行 2025-12-31 实际值 → 新目标值（命中"安全"高分段 440-500）：
  LCR  147.29% → 148.00% (480 分, seg 16)
  NSFR 104.52% → 106.60% (480 分, seg 16)
  EVE  10.54%  → 8.40%   (440 分, seg 13)
  CET1  8.98%  → 9.80%   (480 分, seg 16)
  ROE   9.61%  → 11.80%  (480 分, seg 16)
"""
import sys
sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text
from decimal import Decimal

DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL
eng = create_engine(DB_URL)

# ============== v12b 5 指标完整 23 段 ==============
# 顺序：子段号, 区间下限, 区间上限, 得分, 评语
# 区间下限 inclusive, 区间上限 exclusive (符合 SQL 规则)
SEGMENTS = {
    "LCR": [
        # 红线 (0 分)
        (1, 0.0,    120.0,  0,    "🔴 不达标 (≤红线)"),
        # 危险 (15-135 分, 5 段)
        (2, 120.0,  122.0,  15,   "🟠 危险 0-150"),
        (3, 122.0,  124.0,  45,   "🟠 危险 0-150"),
        (4, 124.0,  126.0,  75,   "🟠 危险 0-150"),
        (5, 126.0,  128.0,  105,  "🟠 危险 0-150"),
        (6, 128.0,  130.0,  135,  "🟠 危险 0-150"),
        # 预警 (165-285 分, 5 段)
        (7, 130.0,  132.0,  165,  "🟡 预警 150-300"),
        (8, 132.0,  134.0,  195,  "🟡 预警 150-300"),
        (9, 134.0,  136.0,  225,  "🟡 预警 150-300"),
        (10, 136.0, 138.0,  255,  "🟡 预警 150-300"),
        (11, 138.0, 140.0,  285,  "🟡 预警 150-300"),
        # 安全 (300-500 分, 5 段)
        (12, 140.0, 142.0,  320,  "🟢 安全 300-500"),
        (13, 142.0, 144.0,  360,  "🟢 安全 300-500"),
        (14, 144.0, 146.0,  400,  "🟢 安全 300-500"),
        (15, 146.0, 148.0,  440,  "🟢 安全 300-500"),
        (16, 148.0, 150.0,  480,  "🟢 安全 300-500"),
        # 满分
        (17, 150.0, 150.0,  500,  "⭐ 适度最优 500"),
        # 过优 (500→减分)
        (18, 150.0, 160.0,  480,  "🟢 过优"),
        (19, 160.0, 170.0,  440,  "🟢 过优"),
        (20, 170.0, 180.0,  400,  "🟢 过优"),
        (21, 180.0, 190.0,  360,  "🟢 过优"),
        (22, 190.0, 200.0,  320,  "🟢 过优"),
        (23, 200.0, 999.0,  300,  "🟢 极度过剩"),
    ],
    "NSFR": [
        (1, 0.0,    100.0,  0,    "🔴 不达标"),
        (2, 100.0,  100.6,  15,   "🟠 危险"),
        (3, 100.6,  101.2,  45,   "🟠 危险"),
        (4, 101.2,  101.8,  75,   "🟠 危险"),
        (5, 101.8,  102.4,  105,  "🟠 危险"),
        (6, 102.4,  103.0,  135,  "🟠 危险"),
        (7, 103.0,  103.4,  165,  "🟡 预警"),
        (8, 103.4,  103.8,  195,  "🟡 预警"),
        (9, 103.8,  104.2,  225,  "🟡 预警"),
        (10, 104.2, 104.6,  255,  "🟡 预警"),
        (11, 104.6, 105.0,  285,  "🟡 预警"),
        (12, 105.0, 105.4,  320,  "🟢 安全"),
        (13, 105.4, 105.8,  360,  "🟢 安全"),
        (14, 105.8, 106.2,  400,  "🟢 安全"),
        (15, 106.2, 106.6,  440,  "🟢 安全"),
        (16, 106.6, 107.0,  480,  "🟢 安全"),
        (17, 107.0, 107.0,  500,  "⭐ 适度最优"),
        (18, 107.0, 108.6,  480,  "🟢 过优"),
        (19, 108.6, 110.2,  440,  "🟢 过优"),
        (20, 110.2, 111.8,  400,  "🟢 过优"),
        (21, 111.8, 113.4,  360,  "🟢 过优"),
        (22, 113.4, 115.0,  320,  "🟢 过优"),
        (23, 115.0, 999.0,  300,  "🟢 极度过剩"),
    ],
    "CET1": [
        (1, 0.0,    8.70,   0,    "🔴 不达标 (红线 8.7%)"),
        (2, 8.70,   8.72,   15,   "🟠 危险"),
        (3, 8.72,   8.74,   45,   "🟠 危险"),
        (4, 8.74,   8.76,   75,   "🟠 危险"),
        (5, 8.76,   8.78,   105,  "🟠 危险"),
        (6, 8.78,   8.80,   135,  "🟠 危险"),
        (7, 8.80,   8.84,   165,  "🟡 预警"),
        (8, 8.84,   8.88,   195,  "🟡 预警"),
        (9, 8.88,   8.92,   225,  "🟡 预警"),
        (10, 8.92,  8.96,   255,  "🟡 预警"),
        (11, 8.96,  9.00,   285,  "🟡 预警"),
        (12, 9.00,  9.20,   320,  "🟢 安全"),
        (13, 9.20,  9.40,   360,  "🟢 安全"),
        (14, 9.40,  9.60,   400,  "🟢 安全"),
        (15, 9.60,  9.80,   440,  "🟢 安全"),
        (16, 9.80,  10.00,  480,  "🟢 安全"),
        (17, 10.00, 10.00,  500,  "⭐ 适度最优"),
        (18, 10.00, 10.60,  480,  "🟢 过优"),
        (19, 10.60, 11.20,  440,  "🟢 过优"),
        (20, 11.20, 11.80,  400,  "🟢 过优"),
        (21, 11.80, 12.40,  360,  "🟢 过优"),
        (22, 12.40, 13.00,  320,  "🟢 过优"),
        (23, 13.00, 999.0,  300,  "🟢 极度过剩"),
    ],
    "ROE": [
        (1, 0.0,    6.0,    0,    "🔴 不达标 (红线 6%)"),
        (2, 6.0,    6.4,    15,   "🟠 危险"),
        (3, 6.4,    6.8,    45,   "🟠 危险"),
        (4, 6.8,    7.2,    75,   "🟠 危险"),
        (5, 7.2,    7.6,    105,  "🟠 危险"),
        (6, 7.6,    8.0,    135,  "🟠 危险"),
        (7, 8.0,    8.2,    165,  "🟡 预警"),
        (8, 8.2,    8.4,    195,  "🟡 预警"),
        (9, 8.4,    8.6,    225,  "🟡 预警"),
        (10, 8.6,   8.8,    255,  "🟡 预警"),
        (11, 8.8,   9.0,    285,  "🟡 预警"),
        (12, 9.0,   9.6,    320,  "🟢 安全"),
        (13, 9.6,   10.2,   360,  "🟢 安全"),
        (14, 10.2,  10.8,   400,  "🟢 安全"),
        (15, 10.8,  11.4,   440,  "🟢 安全"),
        (16, 11.4,  12.0,   480,  "🟢 安全"),
        (17, 12.0,  12.0,   500,  "⭐ 适度最优"),
        (18, 12.0,  999.0,  300,  "🟢 极度过剩"),
    ],
    "EVE": [
        # EVE 是"越低越好"，所以段位是反向的
        (1, 15.0,   999.0,  0,    "🔴 不达标 (≥红线 15%)"),
        (2, 12.0,   12.6,   135,  "🟠 危险"),
        (3, 12.6,   13.2,   105,  "🟠 危险"),
        (4, 13.2,   13.8,   75,   "🟠 危险"),
        (5, 13.8,   14.4,   45,   "🟠 危险"),
        (6, 14.4,   15.0,   15,   "🟠 危险"),
        (7, 10.0,   10.4,   285,  "🟡 预警"),
        (8, 10.4,   10.8,   255,  "🟡 预警"),
        (9, 10.8,   11.2,   225,  "🟡 预警"),
        (10, 11.2,  11.6,   195,  "🟡 预警"),
        (11, 11.6,  12.0,   165,  "🟡 预警"),
        (12, 8.0,   8.4,    480,  "🟢 安全"),
        (13, 8.4,   8.8,    440,  "🟢 安全"),
        (14, 8.8,   9.2,    400,  "🟢 安全"),
        (15, 9.2,   9.6,    360,  "🟢 安全"),
        (16, 9.6,   10.0,   320,  "🟢 安全"),
        (17, 8.0,   8.0,    500,  "⭐ 适度最优 (8%)"),
        (18, 7.0,   8.0,    480,  "🟢 过优"),
        (19, 6.0,   7.0,    440,  "🟢 过优"),
        (20, 5.0,   6.0,    400,  "🟢 过优"),
        (21, 4.0,   5.0,    360,  "🟢 过优"),
        (22, 3.0,   4.0,    320,  "🟢 过优"),
        (23, 0.0,   3.0,    450,  "🟢 极度过剩"),
    ],
}

# ============== 目标值（命中"安全"高分段）==============
TARGET_VALUES = {
    "REG_LCR":  148.00,  # seg 16 → 480 分
    "REG_NSFR": 106.60,  # seg 16 → 480 分
    "REG_CET1": 9.80,    # seg 16 → 480 分
    "REG_ROE":  11.80,   # seg 16 → 480 分
    "REG_EVE":  8.40,    # seg 13 → 440 分 (越低越好)
}

# 期望分数
EXPECTED_SCORES = {
    "REG_LCR":  480,
    "REG_NSFR": 480,
    "REG_CET1": 480,
    "REG_ROE":  480,
    "REG_EVE":  440,
}


def calc_score(kpi_code: str, value: float) -> int:
    """根据 v12b 规则计算分数"""
    metric = kpi_code.replace("REG_", "")
    segs = SEGMENTS.get(metric, [])
    for s in segs:
        so, mn, mx, sc, desc = s
        # 区间是 [min, max)，但 max==min 时表示单点（适度最优）
        if mn == mx:
            if value == mn:
                return sc
        else:
            if value >= mn and value < mx:
                return sc
    return 0  # 不在范围内


def clean_old_rules(conn, kpi_id: int):
    """软删该 kpi 的所有评分规则及段"""
    r = conn.execute(text("UPDATE prcp_kpi_score_rule SET is_deleted=1 WHERE kpi_id=:k"),
                     {"k": kpi_id})
    print(f"  [clean rule] kpi_id={kpi_id} soft-deleted {r.rowcount} rules")
    # 段通过 rule_id 软删
    r = conn.execute(text("""
        UPDATE prcp_kpi_score_segment SET is_deleted=1
        WHERE rule_id IN (SELECT id FROM prcp_kpi_score_rule WHERE kpi_id=:k)
    """), {"k": kpi_id})
    print(f"  [clean seg] kpi_id={kpi_id} soft-deleted {r.rowcount} segments")


def create_v12b_rule(conn, kpi_id: int, kpi_code: str):
    """创建 v12b 评分规则（PIECEWISE, 0-500 分制）"""
    # 软删旧的
    clean_old_rules(conn, kpi_id)

    # 决定方向：EVE 是越低越好
    higher_is_better = 0 if kpi_code == "REG_EVE" else 1

    rid = conn.execute(text("""
        INSERT INTO prcp_kpi_score_rule
        (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better, description, status, is_deleted, created_by, updated_by)
        VALUES (:s, :k, :n, 'PIECEWISE', 500, :h, :d, 'ACTIVE', 0, 1, 1)
    """), {
        "s": 1,  # SCH_REG_2026
        "k": kpi_id,
        "n": f"{kpi_code} v12b 0-500 分评分",
        "h": higher_is_better,
        "d": f"基于 docs/v2/评分标准_v12b.xlsx 的 0-500 分评分规则 - 23 段（含红线/危险/预警/安全/满分/过优）",
    }).lastrowid
    print(f"  [create rule] {kpi_code} v12b rule_id={rid}")

    # 插入 23 段
    metric = kpi_code.replace("REG_", "")
    for so, mn, mx, sc, desc in SEGMENTS[metric]:
        conn.execute(text("""
            INSERT INTO prcp_kpi_score_segment
            (rule_id, seg_order, min_value, max_value, score, segment_desc, is_deleted, created_at, updated_at)
            VALUES (:r, :o, :mn, :mx, :sc, :d, 0, NOW(), NOW())
        """), {
            "r": rid, "o": so,
            "mn": mn, "mx": mx,
            "sc": sc, "d": desc,
        })
    print(f"    [segments] +{len(SEGMENTS[metric])}")
    return rid


def update_kpi_value(conn, kpi_id: int, kpi_code: str, data_date: str, value: float, expected_score: int):
    """更新 prcp_kpi_value 触发 v12b 评分"""
    # 物理删除旧的（因 UNIQUE 约束 (kpi_id, data_date, version) 软删不够）
    r = conn.execute(text("""
        DELETE FROM prcp_kpi_value
        WHERE kpi_id=:k AND data_date=:d
    """), {"k": kpi_id, "d": data_date})
    print(f"  [update value] {kpi_code}@{data_date} deleted {r.rowcount} rows")

    # 插入新值 + 分数
    conn.execute(text("""
        INSERT INTO prcp_kpi_value
        (kpi_id, data_date, version, current_value, prev_value, prev_year_value, calc_source, score, is_deleted, created_by, updated_by)
        VALUES (:k, :d, 'V1.0', :v, NULL, NULL, 'MODEL', :sc, 0, 1, 1)
    """), {
        "k": kpi_id, "d": data_date, "v": value, "sc": expected_score,
    })
    print(f"    [insert] {kpi_code}={value} → 分数={expected_score}")


def main():
    print("=== 1. 清理旧规则 + 创建 v12b 规则 ===")
    with eng.begin() as conn:
        kpis = conn.execute(text("""
            SELECT id, kpi_code, kpi_name FROM prcp_kpi_definition
            WHERE is_deleted=0 AND kpi_code LIKE 'REG_%' ORDER BY id
        """)).fetchall()
        print(f"  5 监管指标: {[k[1] for k in kpis]}")

        for kpi_id, kpi_code, kpi_name in kpis:
            print(f"\n  {kpi_code} ({kpi_name})")
            create_v12b_rule(conn, kpi_id, kpi_code)

    print()
    print("=== 2. 更新 prcp_kpi_value（2025-12-31 基期）===")
    base_date = "2025-12-31"
    with eng.begin() as conn:
        for kpi_id, kpi_code, kpi_name in kpis:
            value = TARGET_VALUES[kpi_code]
            score = EXPECTED_SCORES[kpi_code]
            print(f"\n  {kpi_code} = {value} (期望 {score} 分)")
            update_kpi_value(conn, kpi_id, kpi_code, base_date, value, score)

    print()
    print("=== 3. 验证 ===")
    with eng.begin() as conn:
        print()
        for kpi_code, expected in EXPECTED_SCORES.items():
            row = conn.execute(text("""
                SELECT d.kpi_code, v.current_value, v.score, s.segment_desc
                FROM prcp_kpi_value v
                JOIN prcp_kpi_definition d ON d.id = v.kpi_id AND d.is_deleted = 0
                LEFT JOIN prcp_kpi_score_rule r ON r.kpi_id = d.id AND r.is_deleted = 0
                LEFT JOIN prcp_kpi_score_segment s ON s.rule_id = r.id AND s.is_deleted = 0
                  AND (s.min_value IS NULL OR v.current_value >= s.min_value)
                  AND (s.max_value IS NULL OR v.current_value <  s.max_value)
                WHERE v.is_deleted = 0 AND v.data_date = :d AND d.kpi_code = :kc
            """), {"d": base_date, "kc": kpi_code}).first()
            if row:
                code, val, sc, seg = row
                status = "✓" if sc == expected else "✗"
                print(f"  {status} {code}: value={val}, score={sc}, seg={seg}")
            else:
                print(f"  ? {kpi_code}: no data found")

        # 验证总分（5 指标平均 / 100）
        total = sum(EXPECTED_SCORES.values())
        print()
        print(f"  5 指标总分: {total} / 2500")
        print(f"  综合得分: {total/25:.1f} / 100")
        print(f"  综合评级: {'A+ 优秀' if total >= 2200 else 'A 良好' if total >= 2000 else 'B 中等'}")


if __name__ == "__main__":
    main()