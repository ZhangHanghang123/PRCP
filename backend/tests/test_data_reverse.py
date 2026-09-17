"""Test data_reverse APIs."""
import requests
import json

r = requests.post("https://wxfzhh.online/prcp/api/auth/login",
                   data={"username": "admin", "password": "admin123"}, timeout=10)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

print("=== schemes ===")
r = requests.get("https://wxfzhh.online/prcp/api/data-reverse/schemes", headers=H)
d = r.json()
for s in d["items"]:
    print(f"  {s['scheme_code']} {s['scheme_name']}: {s['run_count']} runs, {s['total_rows']} rows")

print("\n=== matrix (default latest SUCCESS run, M=1) ===")
r = requests.get("https://wxfzhh.online/prcp/api/data-reverse/by-scheme-matrix",
                 params={"scheme_code": "REV_GROWTH", "date_offset": 1}, headers=H)
d = r.json()
print(f"  run_id={d['run_id']}, nodes={len(d['nodes'])}, matrix keys={len(d['matrix'])}, months={len(d['months_list'])}")
print(f"  categories: {list(d['categories'].keys())}")
print(f"  first matrix entry: {list(d['matrix'].values())[0]['node_code']} current={list(d['matrix'].values())[0]['current_balance']}")

print("\n=== matrix (M=12) ===")
r = requests.get("https://wxfzhh.online/prcp/api/data-reverse/by-scheme-matrix",
                 params={"scheme_code": "REV_GROWTH", "date_offset": 12}, headers=H)
d = r.json()
print(f"  matrix keys={len(d['matrix'])}, sample: {list(d['matrix'].values())[0]['data_date']}")

print("\n=== dates list ===")
r = requests.get("https://wxfzhh.online/prcp/api/data-reverse/dates",
                 params={"scheme_code": "REV_GROWTH"}, headers=H)
d = r.json()
print(f"  total months: {d['total']}")
print(f"  first 3: {d['items'][:3]}")

print("\n=== export xlsx ===")
r = requests.get("https://wxfzhh.online/prcp/api/data-reverse/export-xlsx",
                 params={"scheme_code": "REV_GROWTH"}, headers=H)
print(f"  status: {r.status_code}, size: {len(r.content)} bytes, headers: {dict(r.headers)}")