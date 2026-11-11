"""实测：剩余轮次 / 预计耗时 / 每轮指标与评分"""
import json
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"


def req(method, path, data=None, tok=None, form=False):
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


tok = req("POST", "/auth/login", {"username": "admin", "password": "admin123"}, form=True)["access_token"]

# 找一个 HEURISTIC 方案
schemes = req("GET", "/reverse/schemes", tok=tok)["items"]
sid = next(s["id"] for s in schemes if s.get("algorithm") == "HEURISTIC")
run = req("POST", "/reverse/runs", {"scheme_id": sid}, tok=tok)
rid = run["id"]
req("POST", f"/reverse/runs/{rid}/start", tok=tok)
print(f"run_id={rid}")

print("\n--- ① 剩余轮次 + ② 时间 ---")
for i in range(30):
    time.sleep(1.2)
    pg = req("GET", f"/reverse/runs/{rid}/progress", tok=tok)
    print(f"  [{i+1:>2}] {pg['status']:<8} 轮次={pg['round_no']}/{pg['total_rounds']} "
          f"还剩={pg['rounds_remaining']} | 已用={pg['elapsed_sec']}s "
          f"预计={pg['eta_total_sec']}s 剩余={pg['eta_remaining_sec']}s | "
          f"percent={pg['percent']:.0f} rounds={len(pg['rounds'])}")
    if pg["done"]:
        break

print("\n--- ③ 每轮指标与评分 ---")
for r in req("GET", f"/reverse/runs/{rid}/rounds", tok=tok)["items"]:
    print(f"\n  第{r['round_no']}轮 {r['algo']} {r['status']} 得分={r['score']} "
          f"耗时={r['duration_sec']}s 预计总={r['eta_total_sec']}s")
    for code, d in (r.get("score_details") or {}).items():
        print(f"      {code:<12} 目标={d['target']:>8.2f} 实测={d['actual']:>8.2f} "
              f"达成度={d['ratio']*100:>6.1f}% 得分={d['score']} 段位={d['segment_desc']}")
