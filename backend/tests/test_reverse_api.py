"""Reverse calc API end-to-end test"""
import requests
import time

r = requests.post("https://wxfzhh.online/prcp/api/auth/login",
                   data={"username": "admin", "password": "admin123"}, timeout=10)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

# 1. 算法
r = requests.get("https://wxfzhh.online/prcp/api/reverse/algorithms", headers=H)
print("Algorithms:", r.status_code, [a['code'] for a in r.json()["items"]])

# 2. 方案
r = requests.get("https://wxfzhh.online/prcp/api/reverse/schemes", headers=H)
schemes = r.json()["items"]
print(f"\nSchemes: {len(schemes)}")
for s in schemes:
    print(f"  - id={s['id']} {s['scheme_code']} {s['scheme_name']}")

# 3. 目标
r = requests.get("https://wxfzhh.online/prcp/api/reverse/targets", headers=H)
targets = r.json()["items"]
print(f"\nTargets: {len(targets)}")
for t in targets:
    print(f"  - {t['target_name']} {t['constraint_type']} {t['target_value']}")

# 4. KPI 选项
r = requests.get("https://wxfzhh.online/prcp/api/reverse/kpi-options", headers=H)
kpi_items = r.json()["items"]
print(f"\nKPI Options: {len(kpi_items)}")

# 5. 创建目标
if schemes and kpi_items:
    target_resp = requests.post("https://wxfzhh.online/prcp/api/reverse/targets", headers=H,
        json={"scheme_id": schemes[0]["id"], "kpi_id": kpi_items[0]["id"],
              "kpi_code": kpi_items[0]["kpi_code"],
              "target_name": "NIM ≥ 2.8% 测试",
              "target_value": 2.8, "constraint_type": "GE", "weight": 1.0,
              "horizon_month": 0, "sort_order": 1, "description": "API 端到端测试"})
    print(f"\nCreated target: {target_resp.status_code} {target_resp.json()}")

# 6. 创建反算 + 启动
if schemes:
    r1 = requests.post("https://wxfzhh.online/prcp/api/reverse/runs", headers=H,
        json={"scheme_id": schemes[0]["id"], "description": "API 端到端测试"})
    run_id = r1.json()["id"]
    print(f"\nCreate Run: {r1.json()}")
    r2 = requests.post(f"https://wxfzhh.online/prcp/api/reverse/runs/{run_id}/start", headers=H)
    print(f"Start: {r2.status_code}")

    # 等待完成
    for i in range(15):
        time.sleep(2)
        r3 = requests.get("https://wxfzhh.online/prcp/api/reverse/runs", headers=H,
                          params={"scheme_id": schemes[0]["id"]})
        run = next((x for x in r3.json()["items"] if x["id"] == run_id), None)
        if run:
            print(f"  [{i+1}] status={run['status']}, progress={run['progress']}%, opt={run.get('optimal_value')}")
            if run["status"] in ("SUCCESS", "FAILED", "CANCELLED"):
                break

    # 结果
    r5 = requests.get(f"https://wxfzhh.online/prcp/api/reverse/runs/{run_id}/result", headers=H)
    result = r5.json()
    print(f"\nResult: status={result['run']['status']}, predicted_items={len(result['items'])}")
    print(f"  metrics.status: {result['run'].get('metrics', {}).get('status')}")
    print(f"  kpi_actual: {list(result['run'].get('metrics', {}).get('kpi_actual', {}).keys())}")
    for item in result['items'][:6]:
        cv = item.get('current_value') or 0
        av = item.get('adjusted_value') or 0
        dv = item.get('delta_value') or 0
        print(f"  M{item['predict_month']} {item['rpt_item_code']}: {cv:.2f} -> {av:.2f} (delta {dv:+.2f})")