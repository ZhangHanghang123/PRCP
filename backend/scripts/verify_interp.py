"""验证 5 个真实规则的插值效果"""
import json, urllib.parse, urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"
PWD = open("/tmp/pwd.txt").read().strip()

d = urllib.parse.urlencode({"username": "admin", "password": PWD}).encode()
req = urllib.request.Request(BASE + "/auth/login", data=d,
    headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(req))["access_token"]

def calc(rid, v):
    req = urllib.request.Request(BASE + "/kpi/score-calc",
        data=json.dumps({"rule_id": rid, "value": v}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
        method="POST")
    return json.load(urllib.request.urlopen(req))

CASES = [
    (51, "LCR 流动性覆盖率", [0, 60, 119, 121, 123, 125, 130, 149, 151, 170, 250]),
    (52, "NSFR 净稳定资金比例", [0, 101, 102, 110, 150, 250]),
    (53, "CET1 资本充足率", [0, 8, 9, 11, 14, 20]),
    (54, "EVE 逆向(越高越差)", [0, 3, 6, 9, 11, 30]),
    (55, "ROE 净资产收益率", [0, 11, 15, 25, 50]),
]
for rid, nm, vals in CASES:
    print(f"=== 规则 {rid} {nm} ===")
    for v in vals:
        r = calc(rid, v)
        m = r.get("matched_range", {})
        print(f"  值 {v:>5} → 得分 {str(r.get('score')):>7} | "
              f"{m.get('interpolate_mode','-'):<13} | "
              f"[{m.get('min_value')}, {m.get('max_value')}) | {m.get('segment_desc','')}")
    print()
