"""驾驶舱数据完整性检查（KPI / 大类分布 / 余额走势 / 目标达成）"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"


def _req(path, tok=None):
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    r = urllib.request.Request(BASE + path, headers=headers)
    return json.load(urllib.request.urlopen(r))


d = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
r = urllib.request.Request(BASE + "/auth/login", data=d,
                           headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(r))["access_token"]

opt = _req("/reverse-dashboard/options", tok)
dflt = opt["default"]
print(f"默认方案={dflt['scheme_code']}  默认 run={dflt['run_id']}  默认月份=M{dflt['date_offset']}")

snap = _req(f"/reverse-dashboard/snapshot?scheme_code={dflt['scheme_code']}"
            f"&run_id={dflt['run_id']}&date_offset={dflt['date_offset']}", tok)
k = snap["kpi"]
print("\n--- KPI ---")
print(f"  资产余额      {k['asset_total']/1e8:>12,.2f} 亿")
print(f"  负债余额      {k['liability_total']/1e8:>12,.2f} 亿")
print(f"  权益          {k['equity_total']/1e8:>12,.2f} 亿")
print(f"  贷款加权利率  {(k['loan_weighted_rate'] or 0)*100:>12.2f} %")
for m in ["ROE", "CET1", "LCR", "NSFR", "DELTA_EVE"]:
    v = k["metric_avg"].get(m)
    print(f"  {m:<12} {v if v is not None else '-'}")

cd = snap.get("category_distribution", {})
print("\n--- 大类分布 ---")
for mode in ("by_balance", "by_balance_forecast"):
    vals = (cd.get(mode) or {})
    if vals:
        tot = sum(abs(float(v or 0)) for v in vals.values())
        detail = "  ".join(f"{a}={float(b or 0)/1e8:,.0f}亿" for a, b in vals.items())
        print(f"  {mode:<22} 合计={tot/1e8:>12,.2f} 亿   {detail}")
print(f"  balance_date={cd.get('balance_date')}  source={cd.get('balance_source')}")

nm = snap.get("node_matrix") or []
leaves = [n for n in nm if n.get("is_leaf")]
s = sum(float(n.get("base_balance") or 0) for n in leaves)
print(f"\n--- 节点矩阵 ---  总 {len(nm)} 个，末级 {len(leaves)} 个，末级基准余额合计 {s/1e8:,.2f} 亿")

bt = _req(f"/reverse-dashboard/balance-trend?scheme_code={dflt['scheme_code']}"
          f"&run_id={dflt['run_id']}", tok)
print(f"\n--- 末级账户册余额走势 ---  月份 {len(bt.get('months') or [])}  "
      f"大类 {len(bt.get('categories') or [])}  节点 {len(bt.get('nodes') or [])}")
for c in (bt.get("categories") or []):
    v = c.get("values") or []
    nz = sum(1 for x in v if x)
    head = f"{v[0]/1e8:,.0f}亿" if v and v[0] else "-"
    print(f"  {str(c.get('key')):<14} {len(v)} 月，非零 {nz:<3} 首月 {head}")

print("\n--- 目标达成 ---")
for t in snap.get("targets", []):
    print(f"  {t['kpi_code']:<12} 目标 {t['target_value']:>8.2f} 实际 {t['current_value']:>8.2f} "
          f"完成率 {t['current_rate']}%  M12完成率 {t['m12_rate']}%")
