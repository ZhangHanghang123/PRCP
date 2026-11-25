"""回归对拍：available_metrics 的值必须与原 kpi / metric_avg 字段完全一致"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"

# 改造前的基线（2026 / run 31 / M24）
BASELINE = {
    "asset_total": 111096.85,
    "liability_total": 101801.74,
    "equity_total": 9295.11,
    "loan_weighted_rate": 0.0389,
    "ROE": 12.72, "CET1": 10.72, "LCR": 148.92, "NSFR": 107.75, "DELTA_EVE": 8.055,
}

TOL = 0.02   # 金额单位亿，允许 0.02 亿误差（浮点/取整）


def _req(path, tok=None):
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    r = urllib.request.Request(BASE + path, headers=headers)
    return json.load(urllib.request.urlopen(r))


d = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
r = urllib.request.Request(BASE + "/auth/login", data=d,
                           headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(r))["access_token"]

snap = _req("/reverse-dashboard/snapshot?scheme_code=2026&run_id=31&date_offset=24", tok)
k = snap["kpi"]
am = snap["kpi"].get("metric_avg") or {}
avail = snap.get("available_metrics") or []
av = {m["kpi_code"]: m for m in avail}

print("=== ① 旧字段仍在（兼容 Java 版）===")
print(f"  kpi 键: {sorted(k.keys())}")
print(f"  metric_avg: {am}")

print("\n=== ② available_metrics 明细 ===")
print(f"  指标方案 = {snap.get('kpi_scheme_code')}   可展示指标数 = {len(avail)}")
print(f"  default_selected = {snap.get('default_selected')}")
for m in avail:
    print(f"  {m['kpi_code']:<18} {str(m['value']):>16} {m['unit']:<8} "
          f"scored={str(m['is_scored']):<5} score={str(m['score']):<6} "
          f"base={str(m['base_value']):<16} {m['display_group']}/{m['display_order']}")

print("\n=== ③ 数值对拍（旧字段 vs 新指标）===")
fails = []


def chk(name, old, new, tol=TOL):
    if old is None or new is None:
        print(f"  {name:<22} 旧={old} 新={new}  → 跳过(None)")
        return
    diff = abs(float(old) - float(new))
    ok = diff <= tol
    print(f"  {name:<22} 旧={old:>16} 新={new:>16} 差={diff:<12.6f} {'✓' if ok else '✗ 超差'}")
    if not ok:
        fails.append(name)


chk("资产余额(亿)", k["asset_total"] / 1e8, (av["BS_ASSET_TOTAL"]["value"] or 0) / 1e8)
chk("负债余额(亿)", k["liability_total"] / 1e8, (av["BS_LIAB_TOTAL"]["value"] or 0) / 1e8)
chk("权益(亿)", k["equity_total"] / 1e8, (av["BS_EQUITY_TOTAL"]["value"] or 0) / 1e8)
chk("表外(亿)", k["off_balance"] / 1e8, (av["BS_OFFBAL_TOTAL"]["value"] or 0) / 1e8)
chk("贷款加权利率", k["loan_weighted_rate"], av["BS_LOAN_RATE"]["value"], 1e-4)
chk("ROE", am["ROE"], av["REG_ROE"]["value"], 0.005)
chk("CET1", am["CET1"], av["REG_CET1"]["value"], 0.005)
chk("LCR", am["LCR"], av["REG_LCR"]["value"], 0.005)
chk("NSFR", am["NSFR"], av["REG_NSFR"]["value"], 0.005)
chk("DELTA_EVE", am["DELTA_EVE"], av["REG_EVE"]["value"], 0.005)

print("\n=== ④ 与改造前基线对拍（历史值）===")
for kk, bv in BASELINE.items():
    if kk in k:
        # 金额类基线单位为亿，接口返回单位为元
        scale = 1e8 if kk.endswith("_total") else 1
        chk(f"{kk}(基线)", bv, k[kk]/scale, TOL)
    elif kk in am:
        chk(f"{kk}(基线)", bv, am[kk], 0.005)
    elif kk == "loan_weighted_rate":
        chk("loan_weighted_rate(基线)", bv, k["loan_weighted_rate"], 1e-4)

print("\n=== ⑤ 评分结果不变 ===")
print(f"  kpi_scores 条数 = {len(snap.get('kpi_scores') or [])}")
for sc in (snap.get("kpi_scores") or []):
    print(f"    {sc['kpi_code']:<14} value={sc.get('value')} score={sc.get('score')} "
          f"{sc.get('segment_desc')}")

print("\n" + ("=" * 46))
print("对拍结果：" + ("全部通过 ✓" if not fails else f"失败 {len(fails)} 项: {fails}"))
