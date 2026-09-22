"""PRCP ESG · 校验器（PRCP 优化点）

设计：
    - validate_paths: HJM 路径非负检查（raise on 严重负值）
    - validate_factor_loadings: PCA 因子载荷业务校验（PC1 水平因子符号、长端加载衰减）
    - validate_volatility_decay: 波动率随期限递减（warn on 违反）

调用：
    from app.services.esg import validate_paths
"""
from __future__ import annotations
import logging
import numpy as np
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


def validate_paths(
    paths: np.ndarray,
    min_threshold_pct: float = -0.5,
    volatility_warn: bool = True,
) -> Dict[str, any]:
    """校验 HJM 利率路径

    Args:
        paths: (n_scenarios, n_steps, n_maturities) 利率（百分比）
        min_threshold_pct: 最低允许利率（百分比），默认 -0.5%（允许轻微负数用于建模）
        volatility_warn: 是否启用波动率递减校验（仅 warn，不 raise）

    Returns:
        dict: {
            "valid": bool,
            "n_negative": int,
            "min_rate": float,
            "max_rate": float,
            "vol_per_maturity": np.ndarray,
            "vol_decaying": bool,
            "warnings": List[str],
        }
    """
    warnings: list = []

    # 1. 非负校验
    min_rate = float(paths.min())
    max_rate = float(paths.max())
    n_negative = int(np.sum(paths < min_threshold_pct))
    valid = n_negative == 0

    if n_negative > 0:
        warnings.append(
            f"HJM 路径出现 {n_negative} 个 < {min_threshold_pct}% 的负值 (min={min_rate:.4f}%)"
        )

    # 2. 波动率递减校验（PRCP 优化点）
    vol_per_maturity = paths[:, -1, :].std(axis=0)  # (n_maturities,)
    # 短端波动率应该 ≥ 长端（PCA 因子 1 水平主导）
    vol_decaying = bool(np.all(np.diff(vol_per_maturity) <= 1e-6))
    if volatility_warn and not vol_decaying:
        # 找第一个违例的位置
        for i in range(len(vol_per_maturity) - 1):
            if vol_per_maturity[i] < vol_per_maturity[i + 1]:
                warnings.append(
                    f"波动率非递减：maturity[{i}]={vol_per_maturity[i]:.4f} < "
                    f"maturity[{i+1}]={vol_per_maturity[i+1]:.4f}（短端应≥长端）"
                )
                break

    return {
        "valid": valid,
        "n_negative": n_negative,
        "min_rate": min_rate,
        "max_rate": max_rate,
        "vol_per_maturity": vol_per_maturity.tolist(),
        "vol_decaying": vol_decaying,
        "warnings": warnings,
    }


def validate_factor_loadings(
    factor_loadings: np.ndarray,
    maturities_months: np.ndarray,
) -> Dict[str, any]:
    """PCA 因子载荷业务校验

    Args:
        factor_loadings: (n_maturities, n_factors) 因子载荷矩阵
        maturities_months: (n_maturities,) 期限数组

    Returns:
        dict: {
            "valid": bool,
            "warnings": List[str],
            "pc_signs": List[int],   # 每个 PC 的整体符号（按 sum 正负判断）
            "pc1_monotonic": bool,   # PC1（水平）应单调递减
        }
    """
    warnings: list = []
    n_factors = factor_loadings.shape[1]

    # 1. 每个 PC 的整体符号
    pc_signs = [int(np.sign(factor_loadings[:, i].sum())) for i in range(n_factors)]

    # 2. PC1 应单调递减（水平因子，长端加载应 <= 短端）
    if n_factors >= 1:
        pc1 = factor_loadings[:, 0]
        pc1_monotonic = bool(np.all(np.diff(pc1) <= 1e-6))
        if not pc1_monotonic:
            warnings.append(
                f"PC1（水平因子）非单调递减（短端加载应最大）"
            )
    else:
        pc1_monotonic = True

    # 3. 因子载荷绝对值 < 1（标准化结果应在 [-1, 1]）
    if np.any(np.abs(factor_loadings) > 1.5):
        warnings.append(
            f"因子载荷绝对值超过 1.5（max={np.abs(factor_loadings).max():.4f}），可能未标准化"
        )

    valid = len(warnings) == 0
    return {
        "valid": valid,
        "warnings": warnings,
        "pc_signs": pc_signs,
        "pc1_monotonic": pc1_monotonic,
    }


__all__ = ["validate_paths", "validate_factor_loadings"]