"""PRCP 端到端测试 — 创建 PNN训练指标方案 + 5 个函数指标 + recalc 验证

完整流程：
  1. 登录拿 token
  2. GET /reports/ 拿一个 ACTIVE 报表作为 rpt_id（PNN 函数指标的 rpt 绑定）
  3. POST /kpi/schemes 建 PNN训练指标方案
  4. GET /kpi/functions/scripts 验证 5 个 PNN 函数脚本都被扫到
  5. POST /kpi/definitions × 5 建 5 个函数指标（KPI_ROE/CET1/LCR/NSFR/DELTA_EVE）
  6. GET /kpi/definitions?scheme_id=S 验证 5 个都建好
  7. POST /kpi/recalc?kpi_id=X&data_date=... × 5 触发函数指标计算
  8. GET /kpi/values?scheme_id=S&... 验证 5 个 value 都被写入

用法：
  在 PRCP 服务器 venv 环境下：
    cd /home/almd/prcp/backend
    ./venv/bin/python tests/e2e_pnn_scheme_test.py
"""
import json
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlencode

BASE = "http://127.0.0.1:8006"


def http(method: str, path: str, body: dict = None, token: str = None, is_form: bool = False):
    """HTTP helper. 默认 JSON body；如果 is_form=True 用 urlencoded form（用于登录）"""
    url = f"{BASE}{path}"
    if is_form and body is not None:
        data = urlencode(body).encode()
    elif body is not None:
        data = json.dumps(body).encode()
    else:
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    if is_form and body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    elif body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "null")


def main():
    print("=" * 70)
    print("PRCP E2E — PNN训练指标方案 + 5 函数指标")
    print("=" * 70)

    # [1/8] 登录
    print("\n[1/8] 登录...")
    code, r = http("POST", "/prcp/api/auth/login",
                   {"username": "admin", "password": "admin123"},
                   is_form=True)
    assert code == 200, f"登录失败: {code} {r}"
    token = r["access_token"]
    print(f"  ✓ 登录成功, token 前 20 字: {token[:20]}...")

    # [2/8] 取一个 ACTIVE 报表作为 rpt_id
    print("\n[2/8] 取 rpt_id...")
    code, r = http("GET", "/prcp/api/reports/?status=ACTIVE&limit=5", token=token)
    assert code == 200 and r.get("items"), f"无报表: {r}"
    rpt = r["items"][0]
    rpt_id = rpt["id"]
    print(f"  ✓ 用报表: {rpt['report_code']} (id={rpt_id}, type={rpt['report_type']})")

    # [3/8] 创建 PNN 方案
    print("\n[3/8] 创建 PNN 方案...")
    ts = int(time.time())
    code, r = http("POST", "/prcp/api/kpi/schemes", {
        "scheme_code": f"SCH_PNN_TRAIN_{ts}",
        "scheme_name": "PNN训练指标方案",
        "description": "PNN 神经网络训练用 5 个监管/经营指标（ROE/CET1/LCR/NSFR/ΔEVE），均为函数指标",
        "status": "ACTIVE",
    }, token=token)
    assert code == 200, f"建方案失败: {code} {r}"
    scheme_id = r["id"]
    scheme_code = r["scheme_code"]
    print(f"  ✓ 方案建好: id={scheme_id}, code={scheme_code}")

    # [4/8] 验证 5 个 PNN 函数脚本都被 listFunctionScripts 扫到
    print("\n[4/8] 验证 5 个 PNN 函数脚本被扫描到...")
    code, r = http("GET", "/prcp/api/kpi/functions/scripts", token=token)
    assert code == 200, f"扫脚本失败: {code} {r}"
    paths = [x["path"] for x in r.get("items", [])]
    expected = [f"scripts/kpi_functions/pnn_{x}.py" for x in
                ["roe", "cet1", "lcr", "nsfr", "deve"]]
    missing = [p for p in expected if p not in paths]
    assert not missing, f"缺失脚本: {missing}\n已扫到: {paths}"
    print(f"  ✓ 5 个 PNN 函数脚本全部被扫到: {expected}")

    # [5/8] 创建 5 个函数指标
    print("\n[5/8] 创建 5 个函数指标...")
    kpis = [
        {"code": "KPI_PNN_ROE",  "name": "ROE 净资产收益率",       "unit": "PERCENT", "script": "pnn_roe",  "desc": "ROE = 净利润 / 平均净资产 × 100"},
        {"code": "KPI_PNN_CET1", "name": "核心一级资本充足率",   "unit": "PERCENT", "script": "pnn_cet1", "desc": "CET1 = 核心一级资本净额 / 风险加权资产 × 100"},
        {"code": "KPI_PNN_LCR",  "name": "LCR 流动性覆盖率",       "unit": "PERCENT", "script": "pnn_lcr",  "desc": "LCR = 合格优质流动性资产 / 30日现金净流出 × 100"},
        {"code": "KPI_PNN_NSFR", "name": "NSFR 净稳定资金比例",   "unit": "PERCENT", "script": "pnn_nsfr", "desc": "NSFR = 可用稳定资金 / 所需稳定资金 × 100"},
        {"code": "KPI_PNN_DEVE", "name": "△EVE 经济价值变动",     "unit": "AMOUNT",  "script": "pnn_deve", "desc": "△EVE = 基线EVE - 冲击后EVE（±200bp 基线）"},
    ]
    created = {}
    for kpi in kpis:
        code, r = http("POST", "/prcp/api/kpi/definitions", {
            "scheme_id": scheme_id,
            "kpi_code": kpi["code"],
            "kpi_name": kpi["name"],
            "rpt_id": rpt_id,
            "indicator_type": 2,  # 函数指标
            "formula": None,
            "script_path": f"scripts/kpi_functions/{kpi['script']}.py",
            "script_name": "calc",
            "calc_unit": kpi["unit"],
            "formula_desc": kpi["desc"],
            "status": "ACTIVE",
        }, token=token)
        assert code == 200, f"建 {kpi['code']} 失败: {code} {r}"
        created[kpi["code"]] = r["id"]
        print(f"  ✓ {kpi['code']:15s} -> id={r['id']:>3}  {kpi['name']}")

    # [6/8] listDefs 验证
    print("\n[6/8] listDefs 验证...")
    code, r = http("GET", f"/prcp/api/kpi/definitions?scheme_id={scheme_id}", token=token)
    assert code == 200, f"listDefs 失败: {code} {r}"
    listed = {x["kpi_code"]: x for x in r.get("items", [])}
    for kpi in kpis:
        assert kpi["code"] in listed, f"{kpi['code']} 不在 listDefs 结果中"
        d = listed[kpi["code"]]
        assert d["indicator_type"] == 2, f"{kpi['code']} indicator_type 应为 2"
        assert d["script_path"] == f"scripts/kpi_functions/{kpi['script']}.py"
        print(f"  ✓ {kpi['code']:15s} type={d['indicator_type']} script={d['script_path']}")

    # [7/8] recalc × 5
    print("\n[7/8] 触发 5 个函数指标 recalc...")
    data_date = "2026-08-31"
    results = {}
    for kpi in kpis:
        kid = created[kpi["code"]]
        code, r = http("POST", f"/prcp/api/kpi/recalc?kpi_id={kid}&data_date={data_date}",
                       token=token)
        assert code == 200, f"recalc {kpi['code']} 失败: {code} {r}"
        results[kpi["code"]] = r
        print(f"  ✓ {kpi['code']:15s} value={r['value']:>12.4f}  action={r['action']}")

    # [8/8] listValues 验证
    print("\n[8/8] listValues 验证 5 个 value 都被写入 prcp_kpi_value...")
    code, r = http("GET", f"/prcp/api/kpi/values?scheme_id={scheme_id}&data_date={data_date}&version=V1.0",
                   token=token)
    assert code == 200, f"listValues 失败: {code} {r}"
    vals = {x["kpi_code"]: x for x in r.get("items", [])}
    for kpi in kpis:
        assert kpi["code"] in vals, f"{kpi['code']} value 未写入"
        v = vals[kpi["code"]]
        print(f"  ✓ {kpi['code']:15s} current_value={v['current_value']:>12.4f}  calc_source={v['calc_source']}")

    print("\n" + "=" * 70)
    print(f"✅ 全部通过！scheme_id={scheme_id} 5 个函数指标正常工作")
    print(f"   方案编码: {scheme_code}")
    print(f"   数据日期: {data_date}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    rc = 0
    try:
        rc = main()
    except AssertionError as e:
        print(f"\n❌ 失败: {e}")
        rc = 1
    except Exception as e:
        print(f"\n💥 异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        rc = 2
    sys.exit(rc or 0)
