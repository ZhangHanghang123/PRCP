"""PRCP ESG · YieldCurveGenerator（PCA + HJM）

设计（与 DeepALM 简化版）：
    1. 从 prcp_esg_curve_point 表加载 Svensson 6 参数（多日期 × 多期限）
    2. 还原成 n_samples × n_maturities 的利率矩阵
    3. 对每期限做一阶差分 → 去中心化 → 协方差矩阵 → 特征值分解
    4. 取前 n_factors 个主成分
    5. HJM 仿射：用 cumsum(dW) × eigenvectors 模拟利率路径
    6. 月频 dt=1/12（不引入 22 日转换因子）

算法对比：
    - DeepALM: 月频 'ME' 时 factor=1，日频 factor=22
    - PRCP:    始终月频 factor=1（更简化、纯 PRCP 栈）
"""
from __future__ import annotations
import logging
import numpy as np
from typing import List, Optional, Tuple, Dict, Any

from .svensson import SvenssonYieldCurve, svensson_rates

logger = logging.getLogger(__name__)


# PRCP 默认期限数组（13 点，与 PRCP 期限桶 m1~m60 + y10/y15/y20/y30 对齐）
DEFAULT_MATURITIES_MONTHS = [1, 3, 6, 12, 24, 36, 48, 60, 84, 120, 180, 240, 360]


class YieldCurveGenerator:
    """HJM-PCA 收益率曲线生成器

    用法：
        gen = YieldCurveGenerator(n_factors=3)
        gen.fit_from_db_params(curve_points, maturities)
        paths = gen.generate_hjm_paths(n_scenarios=1000, n_steps=120, seed=42)
    """

    def __init__(
        self,
        n_factors: int = 3,
        maturities_months: Optional[List[int]] = None,
        seed: int = 42,
    ):
        self.n_factors = n_factors
        self.maturities = np.asarray(
            maturities_months if maturities_months is not None else DEFAULT_MATURITIES_MONTHS,
            dtype=int,
        )
        self.n_maturities = len(self.maturities)
        self.seed = seed

        # PCA 拟合结果
        self.mu: Optional[np.ndarray] = None            # (n_maturities,)
        self.eigenvalues: Optional[np.ndarray] = None  # (n_maturities,) 降序
        self.eigenvectors: Optional[np.ndarray] = None  # (n_maturities, n_maturities) 列=特征向量
        self.explained_variance_ratio: Optional[np.ndarray] = None
        self.cumulative_variance_ratio: Optional[np.ndarray] = None

        # 拟合上下文
        self.n_samples: int = 0
        self._pca_fitted: bool = False
        self._hjm_generated: bool = False

        # HJM 最近一次输出（供 scenario_set.py 复用）
        self.last_hjm_paths: Optional[np.ndarray] = None

    # ===================== PCA 拟合 =====================

    def fit_from_db_params(
        self,
        curve_points: List[Dict[str, Any]],
        maturities_months: Optional[List[int]] = None,
    ) -> "YieldCurveGenerator":
        """从数据库加载的 Svensson 参数拟合 PCA

        Args:
            curve_points: list of dict, 每个含 theta0..theta3 + lambda1/lambda2 + curve_date,
                          按 curve_date 升序
            maturities_months: 期限数组（月），None 用 self.maturities

        Returns:
            self
        """
        if maturities_months is not None:
            self.maturities = np.asarray(maturities_months, dtype=int)
            self.n_maturities = len(self.maturities)

        if len(curve_points) < 2:
            raise ValueError(
                f"PCA 拟合至少需要 2 个历史日期（实际 {len(curve_points)}），"
                f"请调整方案的 start_date / end_date 范围"
            )

        n_points = len(curve_points)
        yields = np.zeros((n_points, self.n_maturities), dtype=np.float64)

        for i, pt in enumerate(curve_points):
            curve = SvenssonYieldCurve(
                theta0=pt["theta0"], theta1=pt["theta1"],
                theta2=pt["theta2"], theta3=pt["theta3"],
                lambda1=pt["lambda1"], lambda2=pt["lambda2"],
            )
            yields[i, :] = curve.yields_pct(self.maturities)

        # 去中心化（每期限减均值）
        Y_centered = yields - yields.mean(axis=0)
        # 协方差矩阵 (n_maturities × n_maturities)
        cov = (Y_centered.T @ Y_centered) / max(n_points - 1, 1)
        # 特征值分解（eigh 返回升序）
        eigvals, eigvecs = np.linalg.eigh(cov)
        # 降序排列
        idx = np.argsort(eigvals)[::-1]
        eigvals = eigvals[idx]
        eigvecs = eigvecs[:, idx]

        # 一阶差分的均值（HJM drift）
        delta = np.diff(yields, axis=0)
        self.mu = delta.mean(axis=0)  # (n_maturities,)

        self.eigenvalues = eigvals
        self.eigenvectors = eigvecs
        total_var = float(eigvals.sum()) if eigvals.sum() > 0 else 1.0
        self.explained_variance_ratio = eigvals / total_var
        self.cumulative_variance_ratio = np.cumsum(self.explained_variance_ratio)
        self.n_samples = n_points
        self._pca_fitted = True

        cum3 = float(self.cumulative_variance_ratio[min(2, self.n_maturities - 1)])
        logger.info(
            f"PCA 拟合完成: n_samples={n_points}, n_maturities={self.n_maturities}, "
            f"n_factors={self.n_factors}, PC1-3 累计方差={cum3:.4f}"
        )
        return self

    def set_default_params(self) -> "YieldCurveGenerator":
        """设置默认参数（无历史数据时冷启动用）

        默认特征值（基于 30 年国债历史经验）：
            PC1 (水平): 1e-3   → 月波动 ~3 bp
            PC2 (斜率): 3e-4   → 月波动 ~1.7 bp
            PC3 (曲度): 1e-4   → 月波动 ~1 bp
            其余:        5e-5
        """
        self.mu = np.zeros(self.n_maturities)
        # 确保至少 n_maturities 个特征值
        base = [1e-3, 3e-4, 1e-4] + [5e-5] * (self.n_maturities - 3)
        self.eigenvalues = np.array(base[:self.n_maturities])
        self.eigenvectors = np.eye(self.n_maturities)
        total_var = float(self.eigenvalues.sum())
        self.explained_variance_ratio = self.eigenvalues / total_var
        self.cumulative_variance_ratio = np.cumsum(self.explained_variance_ratio)
        self.n_samples = 0
        self._pca_fitted = True
        logger.warning(
            "YieldCurveGenerator 使用默认参数（无历史数据），HJM 路径将不准确，仅供演示"
        )
        return self

    # ===================== HJM 路径生成 =====================

    def generate_hjm_paths(
        self,
        n_scenarios: int,
        n_steps: int,
        seed: Optional[int] = None,
        initial_yields_pct: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """HJM 仿射模型批量生成利率路径

        Args:
            n_scenarios: 情景数
            n_steps: 月步数
            seed: 随机种子（None 用 self.seed）
            initial_yields_pct: 初始利率曲线（百分比），None 用最近 PCA 拟合均值

        Returns:
            np.ndarray: (n_scenarios, n_steps, n_maturities) 利率路径（百分比）

        公式（简化 HJM）：
            dW ~ N(0, dt)  (dt = 1/12 月步长)
            integral = cumsum(dW, axis=1)
            paths[t] = initial + factor_loadings @ integral[t]
            利率非负截断: paths = max(paths, 0)
        """
        if not self._pca_fitted:
            raise RuntimeError("YieldCurveGenerator 未拟合，请先调 fit_from_db_params 或 set_default_params")

        if n_scenarios < 1 or n_steps < 1:
            raise ValueError(f"n_scenarios/n_steps 必须 >= 1, got ({n_scenarios}, {n_steps})")

        if seed is None:
            seed = self.seed
        rng = np.random.default_rng(seed)

        if initial_yields_pct is None:
            # 默认初始利率 = 历史均值（中心化前的 Y）
            # 没有 Y 时退化为零 + 默认水平（3%）
            initial_yields_pct = np.full(self.n_maturities, 3.0)
        initial = np.asarray(initial_yields_pct, dtype=np.float64)

        dt = 1.0 / 12.0
        sqrt_dt = np.sqrt(dt)
        k = min(self.n_factors, self.n_maturities)

        # 主成分标准差（sqrt(eigenvalues)）
        factor_std = np.sqrt(np.maximum(self.eigenvalues[:k], 0.0))  # (k,)

        # (n_scenarios, n_steps, k) 的布朗运动增量
        dW = rng.standard_normal((n_scenarios, n_steps, k)) * sqrt_dt
        # 累积路径
        integral = np.cumsum(dW, axis=1)  # (n_scenarios, n_steps, k)

        # 各期限的因子载荷 = eigenvectors[:, :k] × factor_std (n_maturities, k)
        factor_loadings = self.eigenvectors[:, :k] * factor_std[np.newaxis, :]

        # 重构利率路径: (n_scenarios, n_steps, n_maturities) = integral @ loadings.T
        paths = np.einsum("stk,mk->stm", integral, factor_loadings)
        # 加初始利率
        paths = paths + initial[np.newaxis, np.newaxis, :]

        # 利率非负截断（物理约束）
        paths = np.maximum(paths, 0.0)

        self._hjm_generated = True
        self.last_hjm_paths = paths

        logger.info(
            f"HJM 路径生成完成: scenarios={n_scenarios}, steps={n_steps}, "
            f"shape={paths.shape}, min={paths.min():.4f}, max={paths.max():.4f}"
        )
        return paths

    # ===================== 元数据 =====================

    def get_factor_loadings(self) -> np.ndarray:
        """返回前 n_factors 个因子载荷矩阵 (n_maturities × n_factors)"""
        if not self._pca_fitted:
            raise RuntimeError("PCA 未拟合")
        return self.eigenvectors[:, :self.n_factors]

    def get_summary(self) -> Dict[str, Any]:
        """生成器状态摘要（用于写入 prcp_esg_run.output_json）"""
        return {
            "n_samples": self.n_samples,
            "n_maturities": self.n_maturities,
            "maturities_months": self.maturities.tolist(),
            "n_factors": self.n_factors,
            "eigenvalues": self.eigenvalues.tolist() if self.eigenvalues is not None else None,
            "explained_variance_ratio": self.explained_variance_ratio.tolist() if self.explained_variance_ratio is not None else None,
            "cumulative_variance_ratio": self.cumulative_variance_ratio.tolist() if self.cumulative_variance_ratio is not None else None,
            "cumulative_variance_3f_pct": (
                float(self.cumulative_variance_ratio[2])
                if self.cumulative_variance_ratio is not None and len(self.cumulative_variance_ratio) >= 3
                else None
            ),
            "factor_loadings": self.get_factor_loadings().tolist() if self._pca_fitted else None,
            "pca_fitted": self._pca_fitted,
        }

    def __repr__(self) -> str:
        return (
            f"YieldCurveGenerator(n_factors={self.n_factors}, "
            f"n_maturities={self.n_maturities}, n_samples={self.n_samples}, "
            f"pca_fitted={self._pca_fitted})"
        )


__all__ = ["YieldCurveGenerator", "DEFAULT_MATURITIES_MONTHS"]