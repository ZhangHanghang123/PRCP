"""指标统一治理 · 回归验证（对照设计文档 §7.1 八项清单）"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"


def _req(method, path, data=None, tok=None, form=False):
    headers = {}
    body = None
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    return json.load(urllib.request.urlopen(r))


d = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
r = urllib.request.Request(BASE + "/auth/login", data=d,
                           headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(r))["access_token"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'✓' if ok else '✗'}] {name}" + (f"  —— {detail}" if detail else ""))


print("=== ① 旧字段仍在（Java 版兼容）===")
snap = _req("GET", "/reverse-dashboard/snapshot?scheme_code=2026&run_id=31&date_offset=24", tok=tok)
check("kpi 旧字段存在", "asset_total" in snap.get("kpi", {}))
check("metric_avg 旧字段存在", "metric_avg" in snap.get("kpi", {}))
check("kpi_scores 旧字段存在", len(snap.get("kpi_scores") or []) > 0,
      f"{len(snap.get('kpi_scores') or [])} 条")

print("\n=== ② 评分结果不变（总分/得分/段位）===")
BASE_SCORES = {"REG_LCR": 449.14, "REG_NSFR": 454.17, "REG_CET1": 370.0, "REG_EVE": 486.05}
for sc in snap.get("kpi_scores") or []:
    if sc["kpi_code"] in BASE_SCORES:
        exp = BASE_SCORES[sc["kpi_code"]]
        got = float(sc.get("score") or 0)
        check(f"{sc['kpi_code']} 得分", abs(got - exp) < 0.02, f"期望 {exp} 实得 {got}")

print("\n=== ③ 非评分指标不进总分 / 不出评分标签 ===")
av = {m["kpi_code"]: m for m in (snap.get("available_metrics") or [])}
bs_codes = [c for c in av if c.startswith("BS_")]
check("BS 类指标 is_scored=False", all(av[c]["is_scored"] is False for c in bs_codes), f"{bs_codes}")
check("BS 类指标 score 为空", all(av[c].get("score") is None for c in bs_codes))
scored_codes = [c for c in av if av[c].get("is_scored")]
check("评分明细仅含 is_scored=1",
      all(any(s["kpi_code"] == c for s in (snap.get("kpi_scores") or [])) for c in scored_codes),
      f"{len(scored_codes)} 个")

print("\n=== ④ available_metrics 与旧字段数值一致 ===")
k = snap["kpi"]
for code, old, scale in [("BS_ASSET_TOTAL", k["asset_total"], 1e8),
                          ("BS_LIAB_TOTAL", k["liability_total"], 1e8),
                          ("BS_EQUITY_TOTAL", k["equity_total"], 1e8)]:
    diff = abs((av[code]["value"] or 0) - old)
    check(f"{code} 一致", diff < 1, f"差 {diff:.6f}")
diff = abs((av["BS_LOAN_RATE"]["value"] or 0) - k["loan_weighted_rate"])
check("BS_LOAN_RATE 一致", diff < 1e-6, f"差 {diff:.9f}")
am = k["metric_avg"]
for code, key in [("REG_ROE", "ROE"), ("REG_CET1", "CET1"), ("REG_LCR", "LCR"),
                  ("REG_NSFR", "NSFR"), ("REG_EVE", "DELTA_EVE")]:
    diff = abs((av[code]["value"] or 0) - (am.get(key) or 0))
    check(f"{code} 一致", diff < 1e-6, f"差 {diff:.9f}")

print("\n=== ⑤ 默认前 8 个 ===")
ds = snap.get("default_selected") or []
check("default_selected 数量 = 8", len(ds) == 8, str(ds))
check("与 available_metrics 顺序一致",
      ds == [m["kpi_code"] for m in snap["available_metrics"][:8]])

print("\n=== ⑥ 指标定义接口 ===")
defs = _req("GET", "/kpi/definitions?scheme_id=1", tok=tok)["items"]
check("返回新字段", all("is_scored" in d and "value_source" in d for d in defs), f"{len(defs)} 条")
bs_defs = [d for d in defs if d["kpi_code"].startswith("BS_")]
check("BS 类指标 source_params 有值",
      all(d.get("source_params") for d in bs_defs), f"{len(bs_defs)} 个")
only_scored = _req("GET", "/kpi/definitions?scheme_id=1&scored=true", tok=tok)["items"]
only_unscored = _req("GET", "/kpi/definitions?scheme_id=1&scored=false", tok=tok)["items"]
check("scored 过滤生效",
      len(only_scored) + len(only_unscored) == len(defs),
      f"scored={len(only_scored)} unscored={len(only_unscored)}")

print("\n=== ⑦ 试算预览接口 ===")
for code in ["BS_ASSET_TOTAL", "BS_LOAN_RATE", "REG_ROE"]:
    did = next(d["id"] for d in defs if d["kpi_code"] == code)
    pv = _req("GET", f"/kpi/definitions/{did}/preview?scheme_code=2026&date_offset=1", tok=tok)
    check(f"{code} 试算有值", pv.get("value") is not None, f"值={pv.get('value')} 告警={pv.get('warnings')}")

print("\n=== ⑧ 组合方案已关联指标方案 ===")
check("kpi_scheme_code 有值", bool(snap.get("kpi_scheme_code")), str(snap.get("kpi_scheme_code")))

print("\n" + "=" * 52)
bad = [n for n, ok, _ in results if not ok]
print(f"回归结果：{len(results) - len(bad)}/{len(results)} 通过" + ("" if not bad else f"，失败: {bad}"))
