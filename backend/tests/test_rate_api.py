"""Test rate management API."""
import requests
import json

r = requests.post("https://wxfzhh.online/prcp/api/auth/login",
                   data={"username": "admin", "password": "admin123"}, timeout=10)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

print("=== schemes ===")
r = requests.get("https://wxfzhh.online/prcp/api/rate/schemes", headers=H)
d = r.json()
for s in d["items"]:
    print(f"  {s['curve_code']:14s} {s['curve_type']:10s} pts={s['point_count']:3d} latest={s['latest_date']} y10={s['latest_y10']}")

print("\n=== points (CN_SOV_CNY) ===")
r = requests.get("https://wxfzhh.online/prcp/api/rate/points",
                 params={"curve_code": "CN_SOV_CNY"}, headers=H)
d = r.json()
for p in d["items"][:3]:
    print(f"  {p['data_date']}: y1={p['rates']['y1']}, y10={p['rates']['y10']}, slope={p['curve_slope']}")

print("\n=== upsert (CN_LPR_CNY 2026-09-17) ===")
r = requests.post("https://wxfzhh.online/prcp/api/rate/points", headers=H,
    json={
        "curve_code": "CN_LPR_CNY", "data_date": "2026-09-17",
        "ccy": "CNY",
        "rates": {"d1": 1.5, "d7": 1.7, "m1": 2.0, "m3": 2.2, "m6": 2.3,
                  "y1": 2.4, "y2": 2.5, "y3": 2.6, "y5": 2.8,
                  "y10": 3.0, "y15": 3.1, "y20": 3.2, "y30": 3.3},
        "remark": "LPR 9 月报价"
    })
print(f"  status: {r.status_code}, {r.json()}")

print("\n=== compare (CN_SOV_CNY) ===")
r = requests.get("https://wxfzhh.online/prcp/api/rate/compare",
                 params={"curve_code": "CN_SOV_CNY"}, headers=H)
d = r.json()
print(f"  total: {d['total']}, sample: {d['items'][:1]}")

print("\n=== lookup ===")
r = requests.get("https://wxfzhh.online/prcp/api/rate/lookup",
                 params={"curve_code": "CN_SOV_CNY", "data_date": "2026-09-17",
                         "term": "y10"}, headers=H)
print(f"  {r.json()}")

print("\n=== export xlsx ===")
r = requests.get("https://wxfzhh.online/prcp/api/rate/export-xlsx",
                 params={"curve_code": "CN_SOV_CNY"}, headers=H)
print(f"  status: {r.status_code}, size: {len(r.content)} bytes")