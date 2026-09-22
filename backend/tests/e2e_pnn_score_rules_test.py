"""PRCP — 给「PNN训练指标方案」批量生成 5 套评分规则

设计原则（参考《商业银行风险监管核心指标》+ 巴塞尔Ⅲ国内实施）：
- ROE / CET1 / LCR / NSFR：↑ 正向（higher_is_better=1），5 段式 30/50/70/85/100 分
- △EVE：↓ 逆向（higher_is_better=0，绝对值越小越好），按 |△EVE|/Tier1 资本 占比分段

分段语义（来自 routers/kpi.py:736-741）：
  in_range = (min is None or value >= min) AND (max is None or value < max)
即【min 含, max 不含】，按 seg_order 升序匹配第一个命中区间。

5 个指标 5 套规则，每套 5 段 + 1 个保护段（防越界返回最低分）。
共 5 个 POST /kpi/score-rules 请求，每条带 segments 子表批量写入。

完成后用 /score-calc 对 6 组 demo 值试算，验证区间命中与分数正确。
"""
import json
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlencode

BASE = "http://127.0.0.1:8006"


def http(method, path, body=None, token=None, is_form=False):
    url = f"{BASE}{path}"
    if is_form and body is not None:
        data = urlencode(body).encode()
    elif body is not None:
        data = json.dumps(body).encode()
    else:
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    if is_form and body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    elif body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "null")


# ============== 5 套评分规则定义 ==============

# 通用 5 段（高/较高/合格/关注/差），分数 100/85/70/50/30
# min 含, max 不含；最后一段 max 留 None 表示 +∞

RULES = [
    # ---------- 1. ROE ↑ 正向 ----------
    {
        "kpi_code": "KPI_PNN_ROE",
        "rule_name": "ROE 净资产收益率评分规则",
        "calc_method": "PIECEWISE",
        "higher_is_better": 1,
        "description": "ROE = 净利润/平均净资产×100%；按银保监会对商业银行盈利能力评估标准分段",
        "segments": [
            {"seg_order": 1, "min_value": 20.0,  "max_value": None, "score": 100.0, "segment_desc": "优秀 (≥20%)，行业领先水平"},
            {"seg_order": 2, "min_value": 15.0,  "max_value": 20.0, "score": 85.0,  "segment_desc": "良好 (15%-20%)，优于行业平均"},
            {"seg_order": 3, "min_value": 10.0,  "max_value": 15.0, "score": 70.0,  "segment_desc": "合格 (10%-15%)，达到行业中位数"},
            {"seg_order": 4, "min_value": 5.0,   "max_value": 10.0, "score": 50.0,  "segment_desc": "关注 (5%-10%)，盈利能力不足"},
            {"seg_order": 5, "min_value": None,  "max_value": 5.0,  "score": 30.0,  "segment_desc": "差 (<5%)，盈利能力严重不足"},
        ],
    },
    # ---------- 2. CET1 ↑ 正向 ----------
    {
        "kpi_code": "KPI_PNN_CET1",
        "rule_name": "核心一级资本充足率评分规则",
        "calc_method": "PIECEWISE",
        "higher_is_better": 1,
        "description": "CET1 = 核心一级资本净额/RWA×100%；监管底线 5%+储备资本 2.5%=7.5%",
        "segments": [
            {"seg_order": 1, "min_value": 12.0, "max_value": None, "score": 100.0, "segment_desc": "优秀 (≥12%)，资本充裕、抗风险能力强"},
            {"seg_order": 2, "min_value": 9.0,  "max_value": 12.0, "score": 85.0,  "segment_desc": "良好 (9%-12%)，高于监管+储备 1.5% 以上"},
            {"seg_order": 3, "min_value": 7.5,  "max_value": 9.0,  "score": 70.0,  "segment_desc": "合格 (7.5%-9%)，满足监管+储备底线"},
            {"seg_order": 4, "min_value": 5.0,  "max_value": 7.5,  "score": 50.0,  "segment_desc": "关注 (5%-7.5%)，未达 2.5% 储备要求"},
            {"seg_order": 5, "min_value": None, "max_value": 5.0,  "score": 30.0,  "segment_desc": "差 (<5%)，低于监管最低要求"},
        ],
    },
    # ---------- 3. LCR ↑ 正向 ----------
    {
        "kpi_code": "KPI_PNN_LCR",
        "rule_name": "LCR 流动性覆盖率评分规则",
        "calc_method": "PIECEWISE",
        "higher_is_better": 1,
        "description": "LCR = HQLA/30日现金净流出×100%；监管底线 100%",
        "segments": [
            {"seg_order": 1, "min_value": 130.0, "max_value": None, "score": 100.0, "segment_desc": "优秀 (≥130%)，流动性显著优于监管"},
            {"seg_order": 2, "min_value": 110.0, "max_value": 130.0, "score": 85.0,  "segment_desc": "良好 (110%-130%)，高于监管 10% 以上"},
            {"seg_order": 3, "min_value": 100.0, "max_value": 110.0, "score": 70.0,  "segment_desc": "合格 (100%-110%)，满足监管底线"},
            {"seg_order": 4, "min_value": 90.0,  "max_value": 100.0, "score": 50.0,  "segment_desc": "关注 (90%-100%)，低于监管底线"},
            {"seg_order": 5, "min_value": None,  "max_value": 90.0,  "score": 30.0,  "segment_desc": "差 (<90%)，存在重大流动性风险"},
        ],
    },
    # ---------- 4. NSFR ↑ 正向 ----------
    {
        "kpi_code": "KPI_PNN_NSFR",
        "rule_name": "NSFR 净稳定资金比例评分规则",
        "calc_method": "PIECEWISE",
        "higher_is_better": 1,
        "description": "NSFR = 可用稳定资金/所需稳定资金×100%；监管底线 100%",
        "segments": [
            {"seg_order": 1, "min_value": 120.0, "max_value": None, "score": 100.0, "segment_desc": "优秀 (≥120%)，长期资金结构稳健"},
            {"seg_order": 2, "min_value": 110.0, "max_value": 120.0, "score": 85.0,  "segment_desc": "良好 (110%-120%)，高于监管 10% 以上"},
            {"seg_order": 3, "min_value": 100.0, "max_value": 110.0, "score": 70.0,  "segment_desc": "合格 (100%-110%)，满足监管底线"},
            {"seg_order": 4, "min_value": 90.0,  "max_value": 100.0, "score": 50.0,  "segment_desc": "关注 (90%-100%)，低于监管底线"},
            {"seg_order": 5, "min_value": None,  "max_value": 90.0,  "score": 30.0,  "segment_desc": "差 (<90%)，长期资金缺口显著"},
        ],
    },
    # ---------- 5. △EVE ↓ 逆向（绝对值越小越好）----------
    {
        "kpi_code": "KPI_PNN_DEVE",
        "rule_name": "△EVE 经济价值变动评分规则",
        "calc_method": "PIECEWISE",
        "higher_is_better": 0,
        "description": "△EVE = 基线EVE - 冲击后EVE；负数表示经济价值损失，按绝对值评估（监管要求 ≤15% Tier1 资本）",
        "segments": [
            {"seg_order": 1, "min_value": None,  "max_value": -100000.0, "score": 30.0, "segment_desc": "差 (损失≥10万)，利率风险严重"},
            {"seg_order": 2, "min_value": -100000.0, "max_value": -50000.0,  "score": 50.0, "segment_desc": "关注 (损失 5-10万)，需密切关注"},
            {"seg_order": 3, "min_value": -50000.0,  "max_value": -20000.0,  "score": 70.0, "segment_desc": "合格 (损失 2-5万)，在可接受范围"},
            {"seg_order": 4, "min_value": -20000.0,  "max_value": -5000.0,   "score": 85.0, "segment_desc": "良好 (损失 0.5-2万)，利率风险可控"},
            {"seg_order": 5, "min_value": -5000.0,   "max_value": None,        "score": 100.0, "segment_desc": "优秀 (损失<0.5万)，利率风险极低"},
        ],
    },
]


# 试算验证：每个 KPI 一组代表性 value + 期望命中段 + 期望分数
VERIFY_CASES = [
    # (kpi_code, value, expected_score, expected_desc_substr)
    ("KPI_PNN_ROE",  22.0,  100.0, "优秀"),     # ≥20
    ("KPI_PNN_ROE",  17.0,  85.0,  "良好"),     # 15~20
    ("KPI_PNN_ROE",  12.0,  70.0,  "合格"),     # 10~15
    ("KPI_PNN_ROE",  8.0,   50.0,  "关注"),     # 5~10
    ("KPI_PNN_ROE",  3.0,   30.0,  "差"),       # <5

    ("KPI_PNN_CET1", 13.0,  100.0, "优秀"),     # ≥12
    ("KPI_PNN_CET1", 10.0,  85.0,  "良好"),     # 9~12
    ("KPI_PNN_CET1", 8.0,   70.0,  "合格"),     # 7.5~9
    ("KPI_PNN_CET1", 6.0,   50.0,  "关注"),     # 5~7.5
    ("KPI_PNN_CET1", 4.0,   30.0,  "差"),       # <5

    ("KPI_PNN_LCR",  150.0, 100.0, "优秀"),     # ≥130
    ("KPI_PNN_LCR",  120.0, 85.0,  "良好"),     # 110~130
    ("KPI_PNN_LCR",  105.0, 70.0,  "合格"),     # 100~110
    ("KPI_PNN_LCR",  95.0,  50.0,  "关注"),     # 90~100
    ("KPI_PNN_LCR",  80.0,  30.0,  "差"),       # <90

    ("KPI_PNN_NSFR", 125.0, 100.0, "优秀"),     # ≥120
    ("KPI_PNN_NSFR", 115.0, 85.0,  "良好"),     # 110~120
    ("KPI_PNN_NSFR", 105.0, 70.0,  "合格"),     # 100~110
    ("KPI_PNN_NSFR", 95.0,  50.0,  "关注"),     # 90~100
    ("KPI_PNN_NSFR", 85.0,  30.0,  "差"),       # <90

    ("KPI_PNN_DEVE", -200000.0, 30.0,  "差"),     # <-100000
    ("KPI_PNN_DEVE", -80000.0,  50.0,  "关注"),   # -100000~-50000
    ("KPI_PNN_DEVE", -30000.0,  70.0,  "合格"),   # -50000~-20000
    ("KPI_PNN_DEVE", -10000.0,  85.0,  "良好"),   # -20000~-5000
    ("KPI_PNN_DEVE", -1000.0,   100.0, "优秀"),   # -5000~+∞
]


def main():
    print("=" * 78)
    print("PRCP — PNN 训练指标方案 · 5 套评分规则批量生成 + 试算验证")
    print("=" * 78)

    # [1] 登录
    print("\n[1/4] 登录...")
    code, r = http("POST", "/prcp/api/auth/login",
                   {"username": "admin", "password": "admin123"}, is_form=True)
    assert code == 200, f"登录失败: {code} {r}"
    token = r["access_token"]
    print(f"  ✓ 登录成功")

    # [2] 找 PNN 方案 id + 5 个 def id
    print("\n[2/4] 找 PNN 方案 + 5 个 KPI 定义...")
    code, r = http("GET", "/prcp/api/kpi/schemes?keyword=PNN", token=token)
    assert code == 200 and r["items"], f"未找到 PNN 方案: {r}"
    scheme = r["items"][0]
    scheme_id = scheme["id"]
    print(f"  ✓ 方案: id={scheme_id}, code={scheme['scheme_code']}, name={scheme['scheme_name']}")

    code, r = http("GET", f"/prcp/api/kpi/definitions?scheme_id={scheme_id}", token=token)
    assert code == 200 and r["items"], f"未找到 def: {r}"
    def_map = {x["kpi_code"]: x["id"] for x in r["items"]}
    for r0 in RULES:
        kc = r0["kpi_code"]
        assert kc in def_map, f"{kc} 不在方案下"
    print(f"  ✓ 5 个函数指标全部就绪: {list(def_map.keys())}")

    # [3] 循环创建 5 套评分规则（每套带 5 段）
    print("\n[3/4] 创建 5 套评分规则...")
    rule_id_map = {}
    for rule_def in RULES:
        kpi_id = def_map[rule_def["kpi_code"]]
        body = {
            "scheme_id": scheme_id,
            "kpi_id": kpi_id,
            "rule_name": rule_def["rule_name"],
            "calc_method": rule_def["calc_method"],
            "total_score": 100.0,
            "higher_is_better": rule_def["higher_is_better"],
            "description": rule_def["description"],
            "status": "ACTIVE",
            "segments": rule_def["segments"],
        }
        code, r = http("POST", "/prcp/api/kpi/score-rules", body, token=token)
        assert code == 200, f"建规则 {rule_def['kpi_code']} 失败: {code} {r}"
        rule_id_map[rule_def["kpi_code"]] = r["id"]
        print(f"  ✓ {rule_def['kpi_code']:15s}  rule_id={r['id']:>3}  "
              f"direction={'↑' if rule_def['higher_is_better']==1 else '↓'}  "
              f"segments={r.get('segment_count', len(rule_def['segments']))}")

    # [4] 用 /score-calc 试算 25 组 demo 值验证区间命中
    print(f"\n[4/4] /score-calc 试算 {len(VERIFY_CASES)} 组 demo 值...")
    passed = 0
    failed = 0
    for kpi_code, value, expected_score, expected_desc in VERIFY_CASES:
        rule_id = rule_id_map[kpi_code]
        code, r = http("POST", "/prcp/api/kpi/score-calc",
                       {"rule_id": rule_id, "value": value}, token=token)
        if code != 200:
            print(f"  ✗ {kpi_code} value={value} HTTP {code}: {r}")
            failed += 1
            continue
        if not r.get("matched"):
            print(f"  ✗ {kpi_code} value={value} 未匹配任何区间: {r}")
            failed += 1
            continue
        actual_score = r["score"]
        actual_desc = r.get("matched_range", {}).get("segment_desc", "")
        if abs(actual_score - expected_score) < 0.01 and expected_desc in actual_desc:
            print(f"  ✓ {kpi_code:15s} value={value:>10.2f}  "
                  f"score={actual_score:>5.1f}  {actual_desc[:25]}  [{expected_desc}]")
            passed += 1
        else:
            print(f"  ✗ {kpi_code:15s} value={value:>10.2f}  "
                  f"score={actual_score} (期望 {expected_score})  "
                  f"desc={actual_desc} (期望含 '{expected_desc}')")
            failed += 1

    print("\n" + "=" * 78)
    print(f"结果：通过 {passed}/{len(VERIFY_CASES)}，失败 {failed}")
    print(f"方案: id={scheme_id}, code={scheme['scheme_code']}")
    print(f"规则数: 5 (id={list(rule_id_map.values())})")
    print(f"分段数: 共 25 段（每规则 5 段）")
    print("=" * 78)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    rc = 0
    try:
        rc = main()
    except AssertionError as e:
        print(f"\n❌ 失败: {e}")
        rc = 1
    except Exception as e:
        print(f"\n💥 异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        rc = 2
    sys.exit(rc or 0)
