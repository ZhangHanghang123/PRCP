"""验证指定 run 在驾驶舱全链路的表现（大类分布 / 余额走势 / KPI）"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"
RID = 40


def _req(path, tok=None):
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    r = urllib.request.Request(BASE + path, headers=headers)
    return json.load(urllib.request.urlopen(r))


d = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
r = urllib.request.Request(BASE + "/auth/login", data=d,
                           headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(r))["access_token"]

snap = _req(f"/reverse-dashboard/snapshot?scheme_code=2026&run_id={RID}&date_offset=24", tok)
k = snap["kpi"]
print(f"=== run {RID} snapshot ===")
print(f"  资产余额 {k['asset_total']/1e8:>12,.2f} 亿")
print(f"  负债余额 {k['liability_total']/1e8:>12,.2f} 亿")
print(f"  权益     {k['equity_total']/1e8:>12,.2f} 亿")
print(f"  表外     {k['off_balance']/1e8:>12,.2f} 亿")
print(f"  贷款加权利率 {(k['loan_weighted_rate'] or 0)*100:.2f} %")

cd = snap.get("category_distribution", {})
print("\n=== 大类分布 ===")
for mode in ("by_balance", "by_balance_forecast"):
    src = cd.get(mode) or {}
    vals = src.get("by_balance") or src
    if isinstance(vals, dict) and vals:
        tot = sum(abs(float(v or 0)) for v in vals.values())
        detail = " ".join(f"{k2}={float(v or 0)/1e8:,.0f}亿" for k2, v in list(vals.items())[:5])
        print(f"  {mode:<22} 合计={tot/1e8:>12,.2f} 亿   {detail}")
print(f"  balance_date={cd.get('balance_date')} balance_source={cd.get('balance_source')}")

nm = snap.get("node_matrix") or []
leaves = [n for n in nm if n.get("is_leaf")]
print(f"\n=== 节点矩阵 ===  总 {len(nm)} 个，其中末级 {len(leaves)} 个")
if leaves:
    s = sum(float(n.get("base_balance") or 0) for n in leaves)
    print(f"  末级基准余额合计 = {s/1e8:,.2f} 亿")

bt = _req(f"/reverse-dashboard/balance-trend?scheme_code=2026&run_id={RID}", tok)
print(f"\n=== 末级账户册余额走势 ===")
print(f"  月份 {len(bt.get('months') or [])}  大类 {len(bt.get('categories') or [])}  节点 {len(bt.get('nodes') or [])}")
for c in (bt.get("categories") or [])[:3]:
    v = c.get("values") or []
    nz = sum(1 for x in v if x)
    print(f"  {str(c.get('name') or c.get('code')):<16} {len(v)} 月，非零 {nz}，首月 {v[0] if v else None}")
