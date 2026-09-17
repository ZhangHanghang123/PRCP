"""Test reverse calc saves to prcp_data_reverse."""
import requests
import time

r = requests.post("https://wxfzhh.online/prcp/api/auth/login",
                   data={"username": "admin", "password": "admin123"}, timeout=10)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

r = requests.get("https://wxfzhh.online/prcp/api/reverse/schemes", headers=H)
scheme = r.json()["items"][0]
print(f"使用方案: {scheme['scheme_code']} (id={scheme['id']})")

r1 = requests.post("https://wxfzhh.online/prcp/api/reverse/runs", headers=H,
    json={"scheme_id": scheme["id"], "description": "落库到 prcp_data_reverse 测试"})
run_id = r1.json()["id"]
print(f"创建 run: id={run_id}")

requests.post(f"https://wxfzhh.online/prcp/api/reverse/runs/{run_id}/start", headers=H)

for i in range(10):
    time.sleep(2)
    r3 = requests.get("https://wxfzhh.online/prcp/api/reverse/runs", headers=H,
                      params={"scheme_id": scheme["id"]})
    run = next((rr for rr in r3.json()["items"] if rr["id"] == run_id), None)
    if run and run["status"] in ("SUCCESS", "FAILED", "CANCELLED"):
        print(f"反算完成: status={run['status']}, opt={run.get('optimal_value')}")
        break