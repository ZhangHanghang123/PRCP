"""折现工具脚本

提供以下功能:
1. 期限单位枚举 (日/月/年)
2. 曲线插值方法 (传入数据日期, 期限点, 利率值)
3. 折现因子计算方法
4. 现金流 + 曲线折现方法
5. 批量折现方法 (先插值期限, 再算折现因子, 最后批量折现)

案例参考: docs/v2/prcp_basic_20251231_v4.xlsx
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Tuple, Callable, Dict, Optional, Union
import numpy as np
from scipy.interpolate import interp1d


# ===================== 1. 期限单位枚举 =====================
class TenorUnit(Enum):
    """期限单位枚举"""
    DAY = "D"
    MONTH = "M"
    YEAR = "Y"

    @property
    def chinese(self) -> str:
        return {"D": "日", "M": "月", "Y": "年"}[self.value]


# ===================== 2. 期限解析与转换 =====================
def parse_tenor(tenor: str) -> Tuple[float, TenorUnit]:
    """
    解析期限字符串, 如 "30D", "3M", "1Y", "2.5Y"
    返回 (数值, 单位)

    Examples:
        >>> parse_tenor("3M")
        (3.0, <TenorUnit.MONTH: 'M'>)
    """
    tenor = tenor.strip().upper()
    if not tenor:
        raise ValueError("期限字符串不能为空")
    unit_char = tenor[-1]
    try:
        num = float(tenor[:-1])
    except ValueError:
        raise ValueError(f"期限数值解析失败: {tenor}")
    if unit_char == "D":
        return num, TenorUnit.DAY
    elif unit_char == "M":
        return num, TenorUnit.MONTH
    elif unit_char == "Y":
        return num, TenorUnit.YEAR
    else:
        raise ValueError(f"未知期限单位 '{unit_char}', 支持 D/M/Y")


def tenor_to_years(tenor: str) -> float:
    """
    期限字符串转为年数 (用于插值和折现计算)

    - 1D = 1/365 年
    - 1M = 1/12 年
    - 1Y = 1 年

    Examples:
        >>> round(tenor_to_years("1Y"), 4)
        1.0
    """
    num, unit = parse_tenor(tenor)
    if unit == TenorUnit.DAY:
        return num / 365.0
    elif unit == TenorUnit.MONTH:
        return num / 12.0
    else:
        return num


# ===================== 3. 曲线插值器 =====================
def build_curve_interpolator(
    curve_date: Union[date, str],
    curve_points: List[str],
    curve_rates: List[float],
    method: str = "linear"
) -> Callable[[float], float]:
    """
    构建曲线插值函数 (返回利率 %)

    Args:
        curve_date: 曲线数据日期
        curve_points: 曲线期限点列表, 如 ["3M", "6M", "1Y", "2Y", "3Y", "5Y"]
        curve_rates: 对应期限点的利率值 (%), 如 [1.27, 1.30, 1.3372, 1.3605, 1.383, 1.6309]
        method: 插值方法
            - "linear": 线性插值 (推荐)
            - "cubic": 三次样条插值
            - "zero" / "nearest" / "slinear" 等 scipy 选项

    Returns:
        callable: 接受年限数 (float), 返回利率值 (%) 的函数

    Examples:
        >>> f = build_curve_interpolator(date(2025,12,31), ["1Y","2Y","5Y"], [1.3372,1.3605,1.6309])
        >>> f(3.0)  # 3Y 插值
        1.4623...
    """
    if len(curve_points) != len(curve_rates):
        raise ValueError(
            f"期限点 ({len(curve_points)}) 和利率 ({len(curve_rates)}) 数量不匹配"
        )
    if not curve_points:
        raise ValueError("曲线点列表不能为空")

    # 期限字符串 → 年数
    tenors_years = np.array([tenor_to_years(t) for t in curve_points])
    rates = np.array(curve_rates, dtype=float)

    if method == "linear":
        f = interp1d(tenors_years, rates, kind='linear',
                    bounds_error=False, fill_value='extrapolate')
    elif method == "cubic":
        if len(curve_points) < 4:
            raise ValueError("三次样条插值至少需要 4 个曲线点")
        f = interp1d(tenors_years, rates, kind='cubic',
                    bounds_error=False, fill_value='extrapolate')
    elif method == "previous":  # 前一个值 (step function)
        def _step(x):
            idx = np.searchsorted(tenors_years, x, side='right') - 1
            idx = np.clip(idx, 0, len(rates) - 1)
            return rates[idx]
        f = _step
    else:
        # 其他 scipy 选项
        f = interp1d(tenors_years, rates, kind=method,
                    bounds_error=False, fill_value='extrapolate')

    # 包装: 接受 tenor 字符串或年数
    def interpolator(x):
        if isinstance(x, str):
            x = tenor_to_years(x)
        return float(f(x))

    return interpolator


# ===================== 4. 折现因子计算 =====================
def discount_factor(
    tenor: Union[str, float],
    rate_pct: float,
    compounding: str = "annual"
) -> float:
    """
    计算折现因子 DF = 1/(1+r)^t

    Args:
        tenor: 期限 (字符串 "1Y"/"3M"/"30D" 或年数 float)
        rate_pct: 利率 (%), 如 1.5 表示 1.5%
        compounding: 复利方式
            - "annual": 复利 DF = 1/(1+r)^t
            - "continuous": 连续复利 DF = e^(-r*t)

    Returns:
        float: 折现因子 (0 < DF ≤ 1)

    Examples:
        >>> round(discount_factor("1Y", 1.5), 4)
        0.9852
    """
    if isinstance(tenor, str):
        t = tenor_to_years(tenor)
    else:
        t = float(tenor)

    if t <= 0:
        return 1.0

    r = rate_pct / 100.0

    if compounding == "annual":
        return 1 / ((1 + r) ** t)
    elif compounding == "continuous":
        return np.exp(-r * t)
    else:
        raise ValueError(f"未知复利方式: {compounding}, 支持 annual/continuous")


# ===================== 5. 单条折现 (现金流 + 曲线) =====================
def discount_one(
    tenor: str,
    amount: float,
    curve_date: Union[date, str],
    curve_points: List[str],
    curve_rates: List[float],
    method: str = "linear",
    compounding: str = "annual"
) -> Dict[str, float]:
    """
    对一条现金流按曲线折现

    Args:
        tenor: 期限字符串
        amount: 现金流金额
        curve_date: 曲线数据日期
        curve_points: 曲线期限点
        curve_rates: 利率值
        method: 插值方法
        compounding: 复利方式

    Returns:
        dict: {
            'tenor': 期限,
            'tenor_years': 年数,
            'rate': 插值利率 (%, 已四舍五入),
            'df': 折现因子,
            'amount': 现金流,
            'pv': 现值
        }
    """
    interpolator = build_curve_interpolator(curve_date, curve_points, curve_rates, method)
    t_years = tenor_to_years(tenor)
    rate = interpolator(t_years)
    df = discount_factor(t_years, rate, compounding)
    pv = amount * df

    return {
        'tenor': tenor,
        'tenor_years': t_years,
        'rate': rate,
        'df': df,
        'amount': amount,
        'pv': pv
    }


# ===================== 6. 批量折现 =====================
@dataclass
class CashflowResult:
    """单条现金流折现结果"""
    tenor: str
    tenor_years: float
    rate: float  # %
    df: float
    amount: float
    pv: float


@dataclass
class DiscountResult:
    """批量折现汇总"""
    curve_date: Union[date, str]
    method: str
    compounding: str
    results: List[CashflowResult] = field(default_factory=list)
    total_pv: float = 0.0

    def to_dataframe(self):
        """转为 pandas DataFrame"""
        try:
            import pandas as pd
            return pd.DataFrame([
                {
                    '期限': r.tenor,
                    '年数': r.tenor_years,
                    '利率(%)': r.rate,
                    '折现因子': r.df,
                    '现金流': r.amount,
                    '现值': r.pv
                }
                for r in self.results
            ])
        except ImportError:
            return None


def discount_cashflows_batch(
    cashflows: List[Tuple[str, float]],
    curve_date: Union[date, str],
    curve_points: List[str],
    curve_rates: List[float],
    method: str = "linear",
    compounding: str = "annual"
) -> DiscountResult:
    """
    批量折现 (先插值期限, 再算折现因子, 最后批量折现)

    这是核心批量折现方法, 流程:
    1. 构建曲线插值器 (一次性)
    2. 对每条现金流: 期限 → 年数 → 插值利率 → 折现因子 → 现值

    Args:
        cashflows: 现金流列表 [(tenor, amount), ...]
                  例: [("1M", 2450e9), ("2M", 573e9), ...]
        curve_date: 曲线数据日期
        curve_points: 曲线期限点列表
        curve_rates: 对应利率值 (%)
        method: 插值方法 (linear/cubic/previous/...)
        compounding: 复利方式 (annual/continuous)

    Returns:
        DiscountResult: 包含每条现金流结果 + 总 PV

    Examples:
        >>> cashflows = [("1M", 1000), ("3M", 2000), ("1Y", 5000)]
        >>> curve_points = ["3M", "6M", "1Y", "2Y", "5Y"]
        >>> curve_rates = [1.27, 1.30, 1.3372, 1.3605, 1.6309]
        >>> result = discount_cashflows_batch(cashflows, date(2025,12,31), curve_points, curve_rates)
        >>> result.total_pv
    """
    # 1. 构建曲线插值器
    interpolator = build_curve_interpolator(
        curve_date, curve_points, curve_rates, method
    )

    # 2. 批量处理: 期限 → 年数 → 插值利率 → 折现因子 → 现值
    result = DiscountResult(
        curve_date=curve_date,
        method=method,
        compounding=compounding,
    )

    for tenor_str, amount in cashflows:
        # 期限 → 年数
        t_years = tenor_to_years(tenor_str)
        # 插值利率
        rate = float(interpolator(t_years))
        # 折现因子
        df = discount_factor(t_years, rate, compounding)
        # 现值
        pv = amount * df

        result.results.append(CashflowResult(
            tenor=tenor_str,
            tenor_years=t_years,
            rate=rate,
            df=df,
            amount=amount,
            pv=pv,
        ))
        result.total_pv += pv

    return result


# ===================== 7. 演示 (基于 prcp_basic_20251231_v4.xlsx) =====================
def demo_from_excel():
    """
    基于 prcp_basic_20251231_v4.xlsx 的演示
    模拟 R7 (1.1.对公一般贷款) 的折现
    """
    from datetime import date

    print("=" * 70)
    print("折现工具演示 - 基于 prcp_basic_20251231_v4.xlsx")
    print("=" * 70)

    # 国债收益率曲线 (2025-12-31)
    curve_date = date(2025, 12, 31)
    curve_points = [
        "3M", "6M", "9M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "30Y"
    ]
    curve_rates = [
        1.27, 1.30, 1.32, 1.3372, 1.3605, 1.3830, 1.6309, 1.7359, 1.8473, 2.2674
    ]

    # R7 (1.1.对公一般贷款) 的现金流分布
    cashflows = [
        ("1M", 2450000000000),
        ("2M", 573300000000),
        ("3M", 573300000000),
        ("4M", 573300000000),
        ("5M", 573300000000),
        ("6M", 573300000000),
        ("7M", 573300000000),
        ("8M", 573300000000),
        ("9M", 573300000000),
        ("10M", 573300000000),
        ("11M", 573300000000),
        ("12M", 573300000000),
        ("15Y", 3062500000000),
        ("20Y", 1531250000000),
        ("30Y", 764400000000),
    ]

    print(f"\n曲线日期: {curve_date}")
    print(f"曲线点 ({len(curve_points)} 个): {curve_points}")
    print(f"现金流数量: {len(cashflows)} 条")
    print()

    # 1. 折现因子辅助计算
    print("=" * 70)
    print("1. 折现因子计算 (DF = 1/(1+r)^t)")
    print("=" * 70)
    print(f"{'期限':<6}{'年数':<10}{'利率(%)':<10}{'折现因子':<12}")
    for t in ["1M", "3M", "6M", "9M", "1Y", "2Y", "5Y", "10Y", "30Y"]:
        df = discount_factor(t, 1.0)  # 占位, 实际通过曲线算
    interpolator = build_curve_interpolator(curve_date, curve_points, curve_rates)
    for t in ["1M", "3M", "6M", "9M", "1Y", "2Y", "5Y", "10Y", "30Y"]:
        t_y = tenor_to_years(t)
        rate = interpolator(t_y)
        df = discount_factor(t_y, rate)
        print(f"{t:<6}{t_y:<10.4f}{rate:<10.4f}{df:<12.6f}")

    # 2. 批量折现
    print()
    print("=" * 70)
    print("2. 批量折现 R7 (1.1.对公一般贷款)")
    print("=" * 70)
    result = discount_cashflows_batch(cashflows, curve_date, curve_points, curve_rates)
    print(f"{'期限':<6}{'年数':<10}{'利率(%)':<10}{'折现因子':<12}{'现金流(亿)':<14}{'现值(亿)':<14}")
    print("-" * 70)
    for r in result.results:
        print(f"{r.tenor:<6}{r.tenor_years:<10.4f}{r.rate:<10.4f}"
              f"{r.df:<12.6f}{r.amount/1e8:<14.2f}{r.pv/1e8:<14.2f}")
    print("-" * 70)
    print(f"{'总现值:':<48}{result.total_pv/1e8:<14.2f} 亿元")

    return result


# ===================== 8. 测试 =====================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("运行演示 (基于 prcp_basic_20251231_v4.xlsx)")
    print("=" * 70)
    result = demo_from_excel()

    print()
    print("=" * 70)
    print("✅ 折现工具测试完成")
    print("=" * 70)
    print(f"R7 总现值: {result.total_pv/1e8:.2f} 亿元")
