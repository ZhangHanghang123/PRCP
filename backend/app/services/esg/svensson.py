"""PRCP ESG · Svensson 6 参数收益率曲线

公式：
    Y(T) = θ₀ + θ₁·H(T/λ₁) + θ₂·(H(T/λ₁) - e^(-T/λ₁)) + θ₃·(H(T/λ₂) - e^(-T/λ₂))
    H(x) = (1 - e^(-x)) / x  (Humphrey 衰减函数)

与 DeepALM 的差异：
    - 参数命名 θ₀..θ₃ 而非 β₀..β₃（对齐 PRCP 数据库字段 theta0..3）
    - 输入/输出统一为「月期限 + 百分比利率」（如 5.41 表示 5.41%）
    - 利率以百分点形式（pct）存储，不除以 100，避免 ECB/PCT/decimal 转换混乱
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Union


@dataclass
class SvenssonYieldCurve:
    """Svensson 6 参数收益率曲线（百分比利率）"""

    theta0: float  # 水平（pct）
    theta1: float  # 斜率（pct）
    theta2: float  # 第一曲度（pct）
    theta3: float  # 第二曲度（pct）
    lambda1: float  # 第一衰减时间（年）
    lambda2: float  # 第二衰减时间（年）

    def __post_init__(self):
        if self.lambda1 <= 0 or self.lambda2 <= 0:
            raise ValueError(
                f"lambda1/lambda2 必须 > 0（避免除零），got lambda1={self.lambda1}, lambda2={self.lambda2}"
            )

    @classmethod
    def from_dict(cls, params: Dict[str, float]) -> "SvenssonYieldCurve":
        """从 dict 创建（key 用 theta0/theta1/theta2/theta3/lambda1/lambda2）"""
        return cls(
            theta0=float(params["theta0"]),
            theta1=float(params["theta1"]),
            theta2=float(params["theta2"]),
            theta3=float(params["theta3"]),
            lambda1=float(params["lambda1"]),
            lambda2=float(params["lambda2"]),
        )

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def yields_pct(self, maturities_months: Union[List[int], np.ndarray]) -> np.ndarray:
        """还原指定期限（数组）的利率（百分比，如 3.5 表示 3.5%）

        Args:
            maturities_months: 期限数组（月），如 [1, 3, 6, 12, 60, 120]

        Returns:
            np.ndarray: (n_maturities,) 利率（百分比）
        """
        maturities_months = np.asarray(maturities_months, dtype=float)
        T = maturities_months / 12.0  # 月 → 年

        # H(x) = (1 - exp(-x)) / x (避免 x=0 用 eps 替代)
        eps = 1e-12
        x1 = np.where(T > eps, T / self.lambda1, eps)
        x2 = np.where(T > eps, T / self.lambda2, eps)
        exp1 = np.exp(-x1)
        exp2 = np.exp(-x2)
        H1 = np.where(x1 > eps, (1.0 - exp1) / x1, 1.0)  # H(0)=1 limit
        H2 = np.where(x2 > eps, (1.0 - exp2) / x2, 1.0)

        yields = (
            self.theta0
            + self.theta1 * H1
            + self.theta2 * (H1 - exp1)
            + self.theta3 * (H2 - exp2)
        )
        return yields

    def yields_decimal(self, maturities_months: Union[List[int], np.ndarray]) -> np.ndarray:
        """还原利率（小数形式，如 0.035 表示 3.5%）"""
        return self.yields_pct(maturities_months) / 100.0

    def discount_factor(self, maturity_years: float) -> float:
        """单点折现因子：D(T) = exp(-T · Y(T) / 100)"""
        y_pct = float(self.yields_pct([maturity_years * 12])[0])
        return float(np.exp(-maturity_years * y_pct / 100.0))


def svensson_rates(
    theta0: float, theta1: float, theta2: float, theta3: float,
    lambda1: float, lambda2: float,
    maturities_months: Union[List[int], np.ndarray],
) -> np.ndarray:
    """便捷函数：直接用 6 参数 + 期限数组还原利率（百分比）"""
    curve = SvenssonYieldCurve(theta0, theta1, theta2, theta3, lambda1, lambda2)
    return curve.yields_pct(maturities_months)


__all__ = ["SvenssonYieldCurve", "svensson_rates"]