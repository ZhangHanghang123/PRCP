"""PRCP ESG 算法包纯逻辑测试（不依赖数据库）

在服务器 venv 环境下：
    cd /home/almd/prcp/backend
    ./venv/bin/python tests/test_esg_unit.py
"""
import sys
import os
import tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.esg import (
    SvenssonYieldCurve, YieldCurveGenerator, ScenarioSet,
    validate_paths, validate_factor_loadings, DEFAULT_MATURITIES_MONTHS,
)


def test_1_svensson():
    """Svensson 6 参数曲线还原"""
    print("=== 1. Svensson 公式 ===")
    curve = SvenssonYieldCurve(
        theta0=3.0, theta1=-1.5, theta2=2.0, theta3=-1.0,
        lambda1=2.0, lambda2=5.0,
    )
    y = curve.yields_pct([1, 3, 6, 12, 24, 60, 120])
    print(f"  还原 7 个期限利率: {y.round(3).tolist()}")
    # 业务断言：短端利率应低于长端（θ₁=-1.5 斜率为负 → 短端低、长端高）
    assert y[0] < y[-1], f"短端 {y[0]} 应 < 长端 {y[-1]}"
    print(f"  ✓ 斜率正确（短端 < 长端）")


def test_2_pca_fit():
    """PCA 拟合 + 累计方差"""
    print("\n=== 2. PCA 拟合 ===")
    # 模拟 50 个历史日期的 Svensson 参数（带趋势）
    curve_points = []
    for i in range(50):
        curve_points.append({
            "theta0": 3.0 + 0.5 * np.sin(i / 10),
            "theta1": -1.5 + 0.3 * np.cos(i / 8),
            "theta2": 2.0 + 0.4 * np.sin(i / 15),
            "theta3": -1.0 + 0.2 * np.cos(i / 12),
            "lambda1": 2.0, "lambda2": 5.0,
        })

    gen = YieldCurveGenerator(n_factors=3)
    gen.fit_from_db_params(curve_points)
    print(f"  n_samples={gen.n_samples}, n_maturities={gen.n_maturities}")
    print(f"  explained_var[:5] = {gen.explained_variance_ratio[:5].round(4).tolist()}")
    print(f"  cum[:5] = {gen.cumulative_variance_ratio[:5].round(4).tolist()}")

    assert gen.cumulative_variance_ratio[2] >= 0.90, (
        f"3 因子累计方差 {gen.cumulative_variance_ratio[2]:.4f} 应 >= 90%"
    )
    print(f"  ✓ 3 因子累计方差 {gen.cumulative_variance_ratio[2]:.4f} >= 90%")


def test_3_hjm_paths():
    """HJM 路径生成 + 非负校验"""
    print("\n=== 3. HJM 路径生成 ===")
    curve_points = [
        {
            "theta0": 3.0, "theta1": -1.5, "theta2": 2.0, "theta3": -1.0,
            "lambda1": 2.0, "lambda2": 5.0,
        }
        for _ in range(50)
    ]
    for i, cp in enumerate(curve_points):
        cp["theta0"] += 0.01 * i
    gen = YieldCurveGenerator(n_factors=3)
    gen.fit_from_db_params(curve_points)
    paths = gen.generate_hjm_paths(n_scenarios=200, n_steps=120, seed=42)
    print(f"  shape={paths.shape}, min={paths.min():.4f}, max={paths.max():.4f}")
    assert paths.min() >= 0.0, f"HJM 路径出现负利率 {paths.min():.4f}"
    print(f"  ✓ 利率非负（物理约束满足）")

    v = validate_paths(paths, min_threshold_pct=-0.01)
    print(f"  vol_decaying={v['vol_decaying']}, warnings={v['warnings']}")
    print(f"  vol_per_maturity (前 5 个): {[round(x, 4) for x in v['vol_per_maturity'][:5]]}")


def test_4_factor_loadings():
    """PCA 因子载荷业务校验"""
    print("\n=== 4. 因子载荷校验 ===")
    curve_points = [
        {
            "theta0": 3.0 + 0.01 * i, "theta1": -1.5, "theta2": 2.0, "theta3": -1.0,
            "lambda1": 2.0, "lambda2": 5.0,
        }
        for i in range(30)
    ]
    gen = YieldCurveGenerator(n_factors=3)
    gen.fit_from_db_params(curve_points)
    loadings = gen.get_factor_loadings()
    v = validate_factor_loadings(loadings, gen.maturities)
    print(f"  valid={v['valid']}, pc1_monotonic={v['pc1_monotonic']}, warnings={v['warnings']}")


def test_5_scenario_set():
    """ScenarioSet npz 持久化往返"""
    print("\n=== 5. ScenarioSet npz 持久化 ===")
    curve_points = [
        {
            "theta0": 3.0, "theta1": -1.5, "theta2": 2.0, "theta3": -1.0,
            "lambda1": 2.0, "lambda2": 5.0,
        }
        for _ in range(30)
    ]
    gen = YieldCurveGenerator(n_factors=3)
    gen.fit_from_db_params(curve_points)
    paths = gen.generate_hjm_paths(n_scenarios=50, n_steps=24, seed=42)

    sc = ScenarioSet(
        n_scenarios=50, n_steps=24, n_maturities=13,
        paths=paths,
        maturities_months=gen.maturities,
        initial_yields_pct=np.full(13, 3.0),
        seed=42,
        description="单元测试",
    )
    with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
        fp = f.name
    try:
        sc.save_to_npz(fp)
        print(f"  保存: {os.path.getsize(fp)} bytes")
        sc2 = ScenarioSet.load_from_npz(fp)
        print(f"  读取: shape={sc2.paths.shape}, seed={sc2.seed}, desc='{sc2.description}'")
        assert sc2.paths.shape == paths.shape
        assert np.allclose(sc2.paths, paths)
        print(f"  ✓ 路径数据完全一致")
    finally:
        os.unlink(fp)

    # percentiles 测试
    pct = sc.get_percentiles([10, 50, 90])
    print(f"  p50 终期: {pct['p50'][-1, :].round(4).tolist()}")
    final = sc.get_final_distribution()
    print(f"  终期均值: {final['mean'].round(4).tolist()}")


def test_6_summary():
    """get_summary JSON 序列化测试"""
    print("\n=== 6. Summary JSON ===")
    curve_points = [
        {
            "theta0": 3.0 + 0.01 * i, "theta1": -1.5, "theta2": 2.0, "theta3": -1.0,
            "lambda1": 2.0, "lambda2": 5.0,
        }
        for i in range(30)
    ]
    gen = YieldCurveGenerator(n_factors=3)
    gen.fit_from_db_params(curve_points)
    summary = gen.get_summary()
    print(f"  keys={list(summary.keys())}")
    print(f"  n_samples={summary['n_samples']}, cumulative_3f={summary['cumulative_variance_3f_pct']:.4f}")
    # JSON 可序列化检查
    import json
    json.dumps(summary, default=str)
    print(f"  ✓ summary JSON 可序列化")


if __name__ == "__main__":
    test_1_svensson()
    test_2_pca_fit()
    test_3_hjm_paths()
    test_4_factor_loadings()
    test_5_scenario_set()
    test_6_summary()
    print("\n" + "=" * 50)
    print("✅ ALL UNIT TESTS PASSED")
    print("=" * 50)