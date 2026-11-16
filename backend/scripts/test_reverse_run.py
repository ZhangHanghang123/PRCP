"""验证根因修复：跑一次真实反算，检查余额是否为真实值（非全 0）"""
import json
import time
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


tok = _req("POST", "/auth/login", {"username": "admin", "password": "admin123"}, form=True)["access_token"]
schemes = _req("GET", "/reverse/schemes", tok=tok)["items"]
sid = next(s["id"] for s in schemes if s["scheme_code"] == "2026")

run = _req("POST", "/reverse/runs", {"scheme_id": sid}, tok=tok)
rid = run["id"]
print(f"新建 run id={rid}")
_req("POST", f"/reverse/runs/{rid}/start", {}, tok=tok)

for _ in range(50):
    time.sleep(1.5)
    pg = _req("GET", f"/reverse/runs/{rid}/progress", tok=tok)
    if pg["done"]:
        print(f"状态={pg['status']}  错误={pg.get('error_message')}")
        break

rounds = _req("GET", f"/reverse/runs/{rid}/rounds", tok=tok)
for rr in rounds["items"]:
    print(f"第{rr['round_no']}轮 {rr['algo']} {rr['status']} 得分={rr['score']} opt={rr['optimal_value']} "
          f"预计总耗时={rr['eta_total_sec']}s")
    for code, d in (rr.get("score_details") or {}).items():
        print(f"    {code:<12} 目标={d['target']:>8.2f} 实测={d['actual']:>8.2f} "
              f"达成度={d['ratio']*100:>6.1f}% 得分={d['score']}")

# 检查该 run 写入的余额是否为真实值
snap = _req("GET", f"/reverse-dashboard/snapshot?scheme_code=2026&run_id={rid}"
                   f"&date_offset={max(1, pg['percent'] and 1)}", tok=tok)
print(f"\n该 run 的资产余额 = {snap['kpi']['asset_total']/1e8:,.2f} 亿  "
      f"（0.00 说明仍在写全 0 结果）")
print(f"清理：软删除 run {rid}")
print(rid)
