"""验证大类当前余额分布"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"
PWD = open("/tmp/pwd.txt").read().strip()

d = urllib.parse.urlencode({"username": "admin", "password": PWD}).encode()
req = urllib.request.Request(BASE + "/auth/login", data=d,
    headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(req))["access_token"]


def get(path):
    req = urllib.request.Request(BASE + path,
                                 headers={"Authorization": f"Bearer {tok}"})
    return json.load(urllib.request.urlopen(req))


for sc in ["2026", "REV_NLS_REG", "REV_DNN_REG", "REV_ANT_REG"]:
    try:
        r = get(f"/reverse-dashboard/snapshot?scheme_code={sc}&date_offset=1")
        cd = r.get("category_distribution", {})
        bb = cd.get("by_balance", {})
        print(f"=== {sc} ===")
        print(f"  基准日: {cd.get('balance_date')}　来源: {cd.get('balance_source')}")
        print(f"  by_balance: " + "　".join(
            f"{k}={v/1e12:.2f}万亿" for k, v in bb.items() if v))
        print(f"  by_count  : " + "　".join(
            f"{k}={v}" for k, v in cd.get("by_count", {}).items() if v))
        # 与 KPI 卡片对比
        print(f"  KPI 资产总额: {r.get('asset_total',0)/1e12:.2f}万亿"
              f"　负债: {r.get('liability_total',0)/1e12:.2f}万亿"
              f"　权益: {r.get('equity_total',0)/1e12:.2f}万亿")
        print()
    except Exception as e:
        print(f"=== {sc} === 失败: {e}\n")