"""PRCP 指标计量系数 E2E 测试（11 步）

依赖：本地或服务器 PRCP 后端（8006）+ MySQL 已有账户册方案 + 节点数据。

测试步骤：
1) 健康检查
2) 登录
3) 加载下拉选项
4) 校验账户册方案存在 + 节点存在
5) 创建一条记录（ID = scheme_code_node_code_metric_code_YYYYMMDD）
6) 列出记录
7) 更新记录（修改当前值）
8) 重新列表验证更新
9) 校验 ID 生成规则符合预期
10) 删除记录
11) 校验删除后列表为空

环境变量：
  API_BASE  默认 http://127.0.0.1:8006/prcp/api
  USERNAME  默认 admin
  PASSWORD  默认 admin123
"""
import os
import re
import sys
import time
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8006/prcp/api").rstrip("/")
USERNAME = os.getenv("USERNAME", "admin")
PASSWORD = os.getenv("PASSWORD", "admin123")


def http(method, path, token=None, body=None, raw=False):
    url = f"{API_BASE}{path}"
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, (payload if raw else json.loads(payload)) if payload else (resp.status, None)
    except Exception as e:
        if hasattr(e, "code"):
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        raise


def step(label):
    print(f"\n=== {label} ===")


def expect(cond, msg):
    if not cond:
        print(f"❌ FAIL: {msg}")
        sys.exit(1)
    print(f"✅ {msg}")


def main():
    step("1) 健康检查")
    s, r = http("GET", "/health")
    expect(s == 200, f"health 200: {r}")
    expect(r.get("project") == "PRCP", "project=PRCP")

    step("2) 登录")
    # 用 form 提交
    url = f"{API_BASE}/auth/login"
    from urllib.parse import urlencode
    data = urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        token = body.get("access_token")
    expect(bool(token), "拿到 access_token")

    step("3) 加载下拉选项")
    s, r = http("GET", "/metric-coefficient/options", token=token)
    expect(s == 200, f"options 200: {r}")
    schemes = r.get("schemes", [])
    nodes = r.get("nodes", [])
    metrics = r.get("metric_types", [])
    units = r.get("units", [])
    expect(len(schemes) >= 1, f"至少 1 个方案（拿到 {len(schemes)}）")
    expect(len(nodes) >= 1, f"至少 1 个节点（拿到 {len(nodes)}）")
    expect(len(metrics) >= 5, f"METRIC_TYPE 字典至少 5 项（拿到 {len(metrics)}）")
    expect(len(units) >= 1, f"METRIC_UNIT 字典至少 1 项（拿到 {len(units)}）")
    metric_keys = {m["dict_key"] for m in metrics}
    expect({"ROE", "CET1", "LCR", "NSFR", "DELTA_EVE"} <= metric_keys,
           f"METRIC_TYPE 包含 ROE/CET1/LCR/NSFR/DELTA_EVE: {metric_keys}")

    step("4) 选一个有效节点")
    scheme = schemes[0]
    nodes_in_scheme = [n for n in nodes if n["scheme_id"] == scheme["id"]]
    if not nodes_in_scheme:
        nodes_in_scheme = nodes
        scheme = schemes[0]
    node = nodes_in_scheme[0]
    print(f"   选定：scheme={scheme['scheme_code']} node={node['node_code']}")

    step("5) 创建一条记录")
    dd = "2026-08-31"
    expected_id = f"{scheme['scheme_code']}_{node['node_code']}_ROE_{dd.replace('-', '')}"
    payload = {
        "scheme_id": scheme["id"],
        "scheme_code": scheme["scheme_code"],
        "node_id": node["id"],
        "node_code": node["node_code"],
        "metric_type": "ROE",
        "data_date": dd,
        "current_value": 12.5,
        "y1_value": 13.0, "y2_value": 13.5, "y3_value": 14.0,
        "y4_value": 14.5, "y5_value": 15.0,
        "unit": "PERCENT",
        "description": "E2E 测试创建",
        "status": "ACTIVE",
    }
    s, r = http("POST", "/metric-coefficient", token=token, body=payload)
    expect(s == 200, f"创建 200: {r}")
    expect(r.get("id") == expected_id, f"ID 自动生成正确: {r.get('id')} == {expected_id}")

    step("6) 列出记录（含筛选）")
    s, r = http("GET", f"/metric-coefficient?scheme_id={scheme['id']}&metric_type=ROE&data_date={dd}",
                token=token)
    expect(s == 200, f"list 200: {r}")
    items = r.get("items", [])
    expect(any(x["id"] == expected_id for x in items),
           f"列表里能找到刚创建的记录（找到 {len(items)} 条）")

    step("7) 更新记录（修改当前值 + 备注）")
    s, r = http("PUT", f"/metric-coefficient/{expected_id}", token=token,
                body={"current_value": 99.9, "description": "E2E 更新"})
    expect(s == 200, f"update 200: {r}")

    step("8) 再次列表 + 验证更新生效")
    s, r = http("GET", f"/metric-coefficient?scheme_id={scheme['id']}&metric_type=ROE&data_date={dd}",
                token=token)
    items = r.get("items", [])
    rec = next((x for x in items if x["id"] == expected_id), None)
    expect(rec is not None, "记录仍存在")
    expect(float(rec["current_value"]) == 99.9, f"current_value 已更新为 99.9: {rec['current_value']}")
    expect(rec.get("description") == "E2E 更新", f"description 已更新: {rec.get('description')}")

    step("9) 校验 ID 生成规则")
    pattern = re.compile(r"^[A-Z0-9_]+_[A-Z0-9_]+_[A-Z]+_\d{8}$")
    expect(bool(pattern.match(expected_id)),
           f"ID 匹配规则 [scheme_code]_[node_code]_[metric_code]_[YYYYMMDD]: {expected_id}")

    step("10) 节点↔方案 校验：故意构造错误应被拒绝")
    other_scheme = schemes[1] if len(schemes) >= 2 else scheme
    bad = dict(payload)
    bad["scheme_id"] = other_scheme["id"]
    bad["scheme_code"] = other_scheme["scheme_code"]
    bad["node_id"] = node["id"]  # 节点属于 scheme[0]，不在 other_scheme
    bad["metric_type"] = "LCR"  # 换一个 metric 让 ID 不同
    bad["data_date"] = "2026-09-30"
    s, r = http("POST", "/metric-coefficient", token=token, body=bad)
    expect(s == 400, f"跨方案挂节点应被拒绝（拿到 {s}）: {r}")

    step("11) 删除记录")
    s, r = http("DELETE", f"/metric-coefficient/{expected_id}", token=token)
    expect(s == 200, f"delete 200: {r}")
    # 验证列表里已没有
    s, r = http("GET", f"/metric-coefficient?scheme_id={scheme['id']}&metric_type=ROE&data_date={dd}",
                token=token)
    items = r.get("items", [])
    expect(not any(x["id"] == expected_id for x in items),
           f"删除后列表中已无该条（剩余 {len(items)} 条）")

    print("\n🎉 全部 11 步通过！PRCP 指标计量系数维护功能可用。")


if __name__ == "__main__":
    main()