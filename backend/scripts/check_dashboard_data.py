"""验证驾驶舱数据是否恢复：资产/负债余额、贷款加权利率、余额走势"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"


def req(path, tok=None):
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    r = urllib.request.Request(BASE + path, headers=headers)
    return json.load(urllib.request.urlopen(r))


d = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
r = urllib.request.Request(BASE + "/auth/login", data=d,
                           headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(r))["access_token"]

opt = req("/reverse-dashboard/options", tok)
dflt = opt["default"]
print(f"默认方案={dflt['scheme_code']}  默认 run={dflt['run_id']}  默认月份=M{dflt['date_offset']}")

snap = req(f"/reverse-dashboard/snapshot?scheme_code={dflt['scheme_code']}"
           f"&run_id={dflt['run_id']}&date_offset={dflt['date_offset']}", tok)
k = snap["kpi"]
print("\n--- KPI ---")
print(f"  资产余额      {k['asset_total']/1e8:>12,.2f} 亿")
print(f"  负债余额      {k['liability_total']/1e8:>12,.2f} 亿")
print(f"  权益          {k['equity_total']/1e8:>12,.2f} 亿")
print(f"  贷款加权利率  {(k['loan_weighted_rate']*100 if k['loan_weighted_rate'] else 0):>12.2f} %")
for m in ["ROE", "CET1", "LCR", "NSFR", "DELTA_EVE"]:
    v = k["metric_avg"].get(m)
    print(f"  {m:<12} {v if v is not None else '-'}")

print("\n--- 末级账户册余额走势 ---")
bt = req(f"/reverse-dashboard/balance-trend?scheme_code={dflt['scheme_code']}"
         f"&run_id={dflt['run_id']}", tok)
print(f"  月份数={len(bt.get('months') or [])}  大类数={len(bt.get('categories') or [])}  "
      f"节点数={len(bt.get('nodes') or [])}")
if bt.get("categories"):
    c0 = bt["categories"][0]
    print(f"  示例大类 {c0.get('name') or c0.get('code')}: "
          f"{len(c0.get('values') or [])} 个月，首月={c0.get('values', [None])[0]}")
if bt.get("nodes"):
    n0 = bt["nodes"][0]
    print(f"  示例节点 {n0.get('name') or n0.get('code')}: "
          f"{len(n0.get('values') or [])} 个月，首月={n0.get('values', [None])[0]}")

print("\n--- 目标达成 ---")
for t in snap.get("targets", []):
    print(f"  {t['kpi_code']:<12} 目标 {t['target_value']:>8.2f} 实际 {t['current_value']:>8.2f} "
          f"完成率 {t['current_rate']}%  M12完成率 {t['m12_rate']}%")


print("\n--- 验证根因修复：跑一次真实反算 ---")
run = req2 = None
import urllib.request as _u
def _post(path, payload, tok):
    r = _u.Request(BASE + path, data=json.dumps(payload).encode(),
                   headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"}, method="POST")
    return json.load(_u.urlopen(r))
schemes = req("/reverse/schemes", tok) if False else None
import urllib.request as _u2
r2 = _u2.Request(BASE + "/reverse/schemes", headers={"Authorization": f"Bearer {tok}"})
schemes = json.load(_u2.urlopen(r2))["items"]
sid = next(s["id"] for s in schemes if s["scheme_code"] == "2026")
run = _post("/reverse/runs", {"scheme_id": sid}, tok)
print(f"  新建 run id={run['id']}")
_post(f"/reverse/runs/{run['id']}/start", {}, tok)
import time
for i in range(40):
    time.sleep(1.5)
    pg = req(f"/reverse/runs/{run['id']}/progress", tok)
    if pg["done"]:
        print(f"  状态={pg['status']} 错误={pg.get('error_message')}")
        break
rounds = req(f"/reverse/runs/{run['id']}/rounds", tok)
for rr in rounds["items"]:
    print(f"  第{rr['round_no']}轮 {rr['algo']} {rr['status']} 得分={rr['score']} opt={rr['optimal_value']}")
    for code, d in (rr.get("score_details") or {}).items():
        print(f"      {code:<12} 目标={d['target']:>8.2f} 实测={d['actual']:>8.2f} 得分={d['score']}")
print(f"  清理: 软删除 run {run['id']}")


print("
--- 验证根因修复：跑一次真实反算 ---")
run = req2 = None
import urllib.request as _u
def _post(path, payload, tok):
    r = _u.Request(BASE + path, data=json.dumps(payload).encode(),
                   headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"}, method="POST")
    return json.load(_u.urlopen(r))
schemes = req("/reverse/schemes", tok) if False else None
import urllib.request as _u2
r2 = _u2.Request(BASE + "/reverse/schemes", headers={"Authorization": f"Bearer {tok}"})
schemes = json.load(_u2.urlopen(r2))["items"]
sid = next(s["id"] for s in schemes if s["scheme_code"] == "2026")
run = _post("/reverse/runs", {"scheme_id": sid}, tok)
print(f"  新建 run id={run['id']}")
_post(f"/reverse/runs/{run['id']}/start", {}, tok)
import time
for i in range(40):
    time.sleep(1.5)
    pg = req(f"/reverse/runs/{run['id']}/progress", tok)
    if pg["done"]:
        print(f"  状态={pg['status']} 错误={pg.get('error_message')}")
        break
rounds = req(f"/reverse/runs/{run['id']}/rounds", tok)
for rr in rounds["items"]:
    print(f"  第{rr['round_no']}轮 {rr['algo']} {rr['status']} 得分={rr['score']} opt={rr['optimal_value']}")
    for code, d in (rr.get("score_details") or {}).items():
        print(f"      {code:<12} 目标={d['target']:>8.2f} 实测={d['actual']:>8.2f} 得分={d['score']}")
print(f"  清理: 软删除 run {run['id']}")
