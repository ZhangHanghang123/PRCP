"""实测多轮轮次记录：建 HEURISTIC 方案 → 启动 → 轮询 progress → 校验轮次"""
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

# 1. 建一个 HEURISTIC 方案（多轮算法）
schemes = req("GET", "/reverse/schemes", tok=tok)["items"]
h = [s for s in schemes if s.get("algorithm") == "HEURISTIC"]
if h:
    sid = h[0]["id"]
    print(f"复用已有 HEURISTIC 方案 id={sid} code={h[0]['scheme_code']}")
else:
    coa = req("GET", "/coa/schemes", tok=tok)["items"]
    coa_id = next((c["id"] for c in coa if c["scheme_code"] == "ZX_COA"), coa[0]["id"])
    targets = req("GET", f"/reverse/targets?scheme_id={schemes[0]['id']}", tok=tok)["items"]
    t0 = targets[0]
    new = req("POST", "/reverse/schemes", {
        "scheme_code": "HEUR_RND_TEST", "scheme_name": "启发式多轮验证",
        "scheme_type": "OPTIMIZE", "algorithm": "HEURISTIC",
        "coa_scheme_id": coa_id, "data_date": "2025-12-31", "horizon_months": 24,
        "status": "DRAFT",
    }, tok=tok)
    sid = new["id"]
    print(f"新建 HEURISTIC 方案 id={sid}")
    for t in targets:
        req("POST", "/reverse/targets", {
            "scheme_id": sid, "kpi_id": t.get("kpi_id"), "kpi_code": t.get("kpi_code"),
            "target_name": t.get("target_name"), "target_value": t.get("target_value"),
            "constraint_type": t.get("constraint_type"), "weight": t.get("weight"),
            "horizon_month": t.get("horizon_month"), "sort_order": t.get("sort_order", 0),
        }, tok=tok)
    print(f"  复制 {len(targets)} 条目标约束")

# 2. 建 run 并启动
run = req("POST", "/reverse/runs", {"scheme_id": sid}, tok=tok)
rid = run["id"]
print(f"run_id={rid} status={run.get('status')}")
req("POST", f"/reverse/runs/{rid}/start", tok=tok)

# 3. 轮询 progress（模拟前端实时刷新）
print("\n--- 实时轮询 progress ---")
for i in range(40):
    time.sleep(1.5)
    pg = req("GET", f"/reverse/runs/{rid}/progress", tok=tok)
    print(f"  [{i+1:>2}] status={pg['status']:<10} done={str(pg['done']):<5} "
          f"percent={pg['percent']:>6.2f} stage={str(pg['stage']):<14} "
          f"round={str(pg['round_no']):<4} rounds={len(pg['rounds'])} "
          f"logs={pg['history_count']}")
    if pg["done"]:
        break

# 4. 轮次清单
rounds = req("GET", f"/reverse/runs/{rid}/rounds", tok=tok)
print(f"\n--- 轮次清单（{rounds['total_rounds']} 轮）---")
for r in rounds["items"]:
    print(f"  第{r['round_no']}轮 {r['algo']:<12} {r['status']:<8} "
          f"score={r['score']} opt={r['optimal_value']} "
          f"hit={r['target_hit']} {r['duration_sec']}s  {r['message']}")

# 5. 日志（结构化）
logs = req("GET", f"/reverse/runs/{rid}/logs?since_id=0&limit=200", tok=tok)
print(f"\n--- 日志（{logs['count']} 条，抽样）---")
for l in logs["items"]:
    print(f"  {l['created_at'][11:19]} [R{l['round_no']}] [{l['stage']}] "
          f"[{l['log_level']}] {l['log_message'][:60]}")

stages = sorted({l["stage"] for l in logs["items"] if l["stage"]})
print(f"\n出现的阶段: {stages}")
print(f"带轮次的日志条数: {sum(1 for l in logs['items'] if l['round_no'] is not None)}")
