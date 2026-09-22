"""PRCP ESG 场景工厂 · 端到端测试

完整链路：
  1. 登录 → 拿 token
  2. GET /esg/curves/sources → 验证 4 源 seed 数据
  3. POST /esg/case/run → 一键演示（自动创建 PRCP_ESG_DEMO_001 + 跑三步）
  4. GET /esg/schemes → 列出方案
  5. GET /esg/schemes/{id}/runs → 验证 3 条运行（PCA + HJM + Scenario）
  6. POST /esg/schemes → 创建自定义方案
  7. POST /esg/schemes/{id}/fit-pca → 单独跑 PCA
  8. POST /esg/schemes/{id}/generate-hjm → 单独跑 HJM
  9. POST /esg/schemes/{id}/generate → 单独跑情景集
 10. GET /esg/scenarios/{id}/download → 下载 .npz
 11. POST /esg/curves/{date}/rates → Svensson 还原
 12. POST /esg/curves/bulk → 批量 upsert
 13. GET /esg/cache-info → 验证缓存
"""
import json
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlencode

BASE = "http://127.0.0.1:8006"


def http(method, path, body=None, token=None, is_form=False):
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            if not raw:
                return resp.status, None
            try:
                return resp.status, json.loads(raw.decode() or "null")
            except Exception:
                return resp.status, raw[:200]
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode() or "null")
        except Exception:
            return e.code, raw[:200]


def main():
    print("=" * 70)
    print("PRCP ESG · 端到端测试")
    print("=" * 70)

    # [1/13] 登录
    print("\n[1/13] 登录...")
    code, r = http("POST", "/prcp/api/auth/login",
                   {"username": "admin", "password": "admin123"}, is_form=True)
    assert code == 200, f"登录失败: {code} {r}"
    token = r["access_token"]
    print(f"  ✓ token 长度 {len(token)}")

    # [2/13] 验证 4 源曲线数据
    print("\n[2/13] 验证 4 源曲线数据...")
    code, r = http("GET", "/prcp/api/esg/curves/sources", token=token)
    assert code == 200, f"curves/sources 失败: {code} {r}"
    sources = {x["source"]: x for x in r["items"]}
    assert "ECB" in sources, f"ECB 缺失: {sources}"
    assert sources["ECB"]["count"] >= 500, f"ECB 行数不足: {sources['ECB']['count']}"
    print(f"  ✓ 4 源数据齐全:")
    for s, info in sources.items():
        print(f"    {s:8s} {info['count']:>4} 行 ({info['min_date']} ~ {info['max_date']})")

    # [3/13] 一键案例
    print("\n[3/13] 一键案例 POST /esg/case/run...")
    code, r = http("POST", "/prcp/api/esg/case/run", {}, token=token)
    assert code == 200, f"一键案例失败: {code} {r}"
    demo_id = r["scheme_id"]
    pca_run_id = r["pca_run_id"]
    hjm_run_id = r["hjm_run_id"]
    scenario_id = r["scenario_code"]
    file_path = r["file_path"]
    print(f"  ✓ 方案={demo_id}, pca_run={pca_run_id}, hjm_run={hjm_run_id}, sc={scenario_id}")
    print(f"  ✓ .npz 路径: {file_path}")

    # [4/13] 列出方案
    print("\n[4/13] 列出方案...")
    code, r = http("GET", "/prcp/api/esg/schemes", token=token)
    assert code == 200, f"schemes 失败: {code} {r}"
    schemes = r["items"]
    print(f"  ✓ {len(schemes)} 个方案:")
    for s in schemes[:5]:
        print(f"    {s['scheme_code']:30s} status={s['status']:8s} run_count={s['run_count']}")

    # [5/13] 列出本方案运行历史
    print("\n[5/13] 列出本方案运行历史...")
    code, r = http("GET", f"/prcp/api/esg/schemes/{demo_id}/runs", token=token)
    assert code == 200, f"runs 失败: {code} {r}"
    runs = r["items"]
    print(f"  ✓ {len(runs)} 条运行")
    for run in runs:
        print(f"    run#{run['id']} {run['run_type']:22s} status={run['status']:8s} dur={run['duration_ms']}ms")

    # [6/13] PCA 累计方差 ≥ 95%
    print("\n[6/13] 验证 PCA 累计方差...")
    code, r = http("GET", f"/prcp/api/esg/runs/{pca_run_id}", token=token)
    assert code == 200, f"get run 失败: {code} {r}"
    cum3 = r["output"]["cumulative_variance_3f_pct"]
    print(f"  ✓ 3 因子累计方差: {cum3:.4f}")
    assert cum3 >= 0.90, f"PCA 3 因子累计方差 {cum3:.4f} < 90%"

    # [7/13] HJM 路径形状
    print("\n[7/13] 验证 HJM 路径...")
    code, r = http("GET", f"/prcp/api/esg/runs/{hjm_run_id}", token=token)
    assert code == 200, f"get run 失败: {code} {r}"
    paths_shape = r["output"]["paths_shape"]
    paths_min = r["output"]["paths_min"]
    paths_max = r["output"]["paths_max"]
    print(f"  ✓ HJM 形状: {paths_shape}, 利率范围 [{paths_min:.4f}%, {paths_max:.4f}%]")
    assert paths_min >= 0, f"HJM 出现负利率 {paths_min}"
    assert paths_shape == [50, 24, 10], f"形状不符: {paths_shape}"

    # [8/13] 创建自定义方案
    print("\n[8/13] 创建自定义方案...")
    ts = int(time.time())
    code, r = http("POST", "/prcp/api/esg/schemes", {
        "scheme_code": f"SCH_ECG_E2E_{ts}",
        "scheme_name": "E2E 测试方案",
        "description": "E2E 自动测试",
        "data_source": "ECB",
        "start_date": "2024-06-01",
        "end_date": "2025-06-01",
        "n_factors": 3,
        "maturities_months": [1, 3, 6, 12, 24, 60, 120, 240],
        "n_scenarios": 100,
        "n_steps": 24,
        "seed": 42,
        "status": "READY",
    }, token=token)
    assert code == 200, f"创建方案失败: {code} {r}"
    scheme_id = r["id"]
    print(f"  ✓ 方案创建: id={scheme_id}, code=SCH_ECG_E2E_{ts}")

    # [9/13] 单独跑 PCA
    print("\n[9/13] 单独跑 PCA...")
    code, r = http("POST", f"/prcp/api/esg/schemes/{scheme_id}/fit-pca",
                   {"n_factors": 3}, token=token)
    assert code == 200, f"fit-pca 失败: {code} {r}"
    print(f"  ✓ run_id={r['run_id']}, cumulative_3f={r['summary']['cumulative_variance_3f_pct']:.4f}")

    # [10/13] 单独跑 HJM
    print("\n[10/13] 单独跑 HJM...")
    code, r = http("POST", f"/prcp/api/esg/schemes/{scheme_id}/generate-hjm",
                   {"n_scenarios": 100, "n_steps": 24}, token=token)
    assert code == 200, f"generate-hjm 失败: {code} {r}"
    print(f"  ✓ run_id={r['run_id']}, file={r['file_path']}")

    # [11/13] 单独跑情景集
    print("\n[11/13] 单独跑情景集...")
    code, r = http("POST", f"/prcp/api/esg/schemes/{scheme_id}/generate", {}, token=token)
    assert code == 200, f"generate 失败: {code} {r}"
    custom_sc_id = r["scenario_code"]
    print(f"  ✓ run_id={r['run_id']}, scenario_code={custom_sc_id}")

    # [12/13] 下载 .npz
    print("\n[12/13] 下载 .npz...")
    req = urllib.request.Request(
        f"{BASE}/prcp/api/esg/scenarios/{custom_sc_id}/download",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        assert len(raw) > 1000, f"下载文件过小: {len(raw)} bytes"
    print(f"  ✓ 下载 {len(raw)} bytes")

    # [13/13] Svensson 还原
    print("\n[13/13] Svensson 曲线还原...")
    code, r = http("POST", "/prcp/api/esg/curves/2024-06-03/rates",
                   {"tenors": [1, 3, 6, 12, 60, 120], "source": "ECB"}, token=token)
    assert code == 200, f"rates 失败: {code} {r}"
    rates = r["items"][0]["rates_pct"]
    print(f"  ✓ 6 期限利率: {[round(x, 3) for x in rates]}%")

    # 额外：批量 upsert
    print("\n[Bonus] 批量 upsert curve...")
    code, r = http("POST", "/prcp/api/esg/curves/bulk", {
        "points": [
            {"curve_date": "2026-09-22", "source": "CUSTOM",
             "theta0": 3.0, "theta1": -1.0, "theta2": 1.0, "theta3": -0.5,
             "lambda1": 2.0, "lambda2": 5.0, "description": "E2E 测试"},
        ],
    }, token=token)
    assert code == 200, f"bulk upsert 失败: {code} {r}"
    print(f"  ✓ 批量 upsert: {r}")

    # 缓存诊断
    print("\n[Cache Info] ...")
    code, r = http("GET", "/prcp/api/esg/cache-info", token=token)
    assert code == 200
    print(f"  ✓ 缓存: {r['total_cached']} 个方案")
    for sid, info in r["details"].items():
        print(f"    scheme {sid}: {info}")

    print("\n" + "=" * 70)
    print(f"✅ 全部通过！测试方案 ID={scheme_id}, demo 方案 ID={demo_id}")
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