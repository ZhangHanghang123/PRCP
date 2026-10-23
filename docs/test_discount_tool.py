"""discount_tool.py 单元测试

测试数据基于 prcp_basic_20251231_v4.xlsx:
- 曲线日期: 2025-12-31
- 国债收益率曲线 (中债登 10 个关键期限)
- R7 (1.1.对公一般贷款) 现金流分布

运行: python -m unittest test_discount_tool.py -v
或: python test_discount_tool.py
"""

import unittest
import sys
from datetime import date
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from discount_tool import (
    TenorUnit,
    parse_tenor,
    tenor_to_years,
    build_curve_interpolator,
    discount_factor,
    discount_one,
    discount_cashflows_batch,
    DiscountResult,
    CashflowResult,
    demo_from_excel,
)


# ===================== 测试数据 (基于 prcp_basic_20251231_v4.xlsx) =====================
CURVE_DATE = date(2025, 12, 31)

# 2025-12-31 国债收益率曲线 (中债登 10 个关键期限)
CURVE_POINTS = ["3M", "6M", "9M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "30Y"]
CURVE_RATES = [1.27, 1.30, 1.32, 1.3372, 1.3605, 1.3830, 1.6309, 1.7359, 1.8473, 2.2674]

# R7 (1.1.对公一般贷款) 现金流分布
R7_CASHFLOWS = [
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


# ===================== 1. TenorUnit 枚举测试 =====================
class TestTenorUnit(unittest.TestCase):
    """期限单位枚举测试"""

    def test_enum_values(self):
        """枚举值正确"""
        self.assertEqual(TenorUnit.DAY.value, "D")
        self.assertEqual(TenorUnit.MONTH.value, "M")
        self.assertEqual(TenorUnit.YEAR.value, "Y")

    def test_chinese_property(self):
        """中文名称属性正确"""
        self.assertEqual(TenorUnit.DAY.chinese, "日")
        self.assertEqual(TenorUnit.MONTH.chinese, "月")
        self.assertEqual(TenorUnit.YEAR.chinese, "年")

    def test_enum_uniqueness(self):
        """枚举值唯一"""
        values = [t.value for t in TenorUnit]
        self.assertEqual(len(values), len(set(values)))


# ===================== 2. parse_tenor 测试 =====================
class TestParseTenor(unittest.TestCase):
    """期限字符串解析测试"""

    def test_day(self):
        """日单位解析"""
        num, unit = parse_tenor("30D")
        self.assertEqual(num, 30.0)
        self.assertEqual(unit, TenorUnit.DAY)

    def test_day_single(self):
        """单日解析"""
        num, unit = parse_tenor("1D")
        self.assertEqual(num, 1.0)
        self.assertEqual(unit, TenorUnit.DAY)

    def test_month(self):
        """月单位解析"""
        num, unit = parse_tenor("3M")
        self.assertEqual(num, 3.0)
        self.assertEqual(unit, TenorUnit.MONTH)

    def test_year(self):
        """年单位解析"""
        num, unit = parse_tenor("1Y")
        self.assertEqual(num, 1.0)
        self.assertEqual(unit, TenorUnit.YEAR)

    def test_decimal_year(self):
        """小数年限解析"""
        num, unit = parse_tenor("2.5Y")
        self.assertEqual(num, 2.5)
        self.assertEqual(unit, TenorUnit.YEAR)

    def test_lowercase(self):
        """小写输入 (应自动转大写)"""
        num, unit = parse_tenor("3m")
        self.assertEqual(num, 3.0)
        self.assertEqual(unit, TenorUnit.MONTH)

    def test_empty_raises(self):
        """空字符串抛异常"""
        with self.assertRaises(ValueError):
            parse_tenor("")

    def test_invalid_unit_raises(self):
        """未知单位抛异常"""
        with self.assertRaises(ValueError):
            parse_tenor("3X")

    def test_invalid_number_raises(self):
        """非数字抛异常"""
        with self.assertRaises(ValueError):
            parse_tenor("abM")


# ===================== 3. tenor_to_years 测试 =====================
class TestTenorToYears(unittest.TestCase):
    """期限转年数测试"""

    def test_day(self):
        """1 天 ≈ 1/365 年"""
        result = tenor_to_years("1D")
        self.assertAlmostEqual(result, 1/365, places=6)

    def test_30_days(self):
        """30 天 ≈ 30/365 年"""
        result = tenor_to_years("30D")
        self.assertAlmostEqual(result, 30/365, places=6)

    def test_month(self):
        """1 月 = 1/12 年"""
        result = tenor_to_years("1M")
        self.assertAlmostEqual(result, 1/12, places=6)

    def test_3_months(self):
        """3 月 = 0.25 年"""
        result = tenor_to_years("3M")
        self.assertAlmostEqual(result, 0.25, places=6)

    def test_6_months(self):
        """6 月 = 0.5 年"""
        result = tenor_to_years("6M")
        self.assertAlmostEqual(result, 0.5, places=6)

    def test_year(self):
        """1 年 = 1 年"""
        result = tenor_to_years("1Y")
        self.assertEqual(result, 1.0)

    def test_5_years(self):
        """5 年 = 5 年"""
        result = tenor_to_years("5Y")
        self.assertEqual(result, 5.0)

    def test_30_years(self):
        """30 年 = 30 年"""
        result = tenor_to_years("30Y")
        self.assertEqual(result, 30.0)


# ===================== 4. build_curve_interpolator 测试 =====================
class TestBuildCurveInterpolator(unittest.TestCase):
    """曲线插值器测试"""

    def setUp(self):
        """每个测试前的初始化"""
        self.interpolator = build_curve_interpolator(
            CURVE_DATE, CURVE_POINTS, CURVE_RATES
        )

    def test_exact_points(self):
        """在已知曲线点上插值精确"""
        # 3M = 1.27
        self.assertAlmostEqual(self.interpolator("3M"), 1.27, places=3)
        # 6M = 1.30
        self.assertAlmostEqual(self.interpolator("6M"), 1.30, places=3)
        # 1Y = 1.3372
        self.assertAlmostEqual(self.interpolator("1Y"), 1.3372, places=3)
        # 30Y = 2.2674
        self.assertAlmostEqual(self.interpolator("30Y"), 2.2674, places=3)

    def test_interpolation_between(self):
        """两点之间线性插值正确"""
        # 1Y=1.3372, 2Y=1.3605 → 18M=1.34885
        result = self.interpolator(1.5)
        self.assertAlmostEqual(result, (1.3372 + 1.3605) / 2, places=4)

    def test_accepts_year_number(self):
        """接受年数输入"""
        result = self.interpolator(1.0)  # 1Y
        self.assertAlmostEqual(result, 1.3372, places=3)

        result = self.interpolator(0.25)  # 3M
        self.assertAlmostEqual(result, 1.27, places=3)

    def test_extrapolation(self):
        """超出曲线范围的外推 (linear)"""
        # < 3M 外推 (按 3M-6M 趋势)
        result = self.interpolator(0.1)
        # 应该小于 1.27 (因为 < 3M 外推会延 0 的方向)
        self.assertLess(result, 1.27)

        # > 30Y 外推
        result = self.interpolator(50.0)
        # 应该大于 2.2674
        self.assertGreater(result, 2.2674)

    def test_different_methods(self):
        """不同插值方法"""
        for method in ["linear", "cubic", "previous", "slinear"]:
            f = build_curve_interpolator(
                CURVE_DATE, CURVE_POINTS, CURVE_RATES, method=method
            )
            # 所有方法在已知点上结果相同
            self.assertAlmostEqual(f("3M"), 1.27, places=3)
            self.assertAlmostEqual(f("30Y"), 2.2674, places=3)

    def test_length_mismatch_raises(self):
        """期限点和利率数量不匹配抛异常"""
        with self.assertRaises(ValueError):
            build_curve_interpolator(
                CURVE_DATE, CURVE_POINTS, CURVE_RATES + [3.0]
            )

    def test_empty_raises(self):
        """空列表抛异常"""
        with self.assertRaises(ValueError):
            build_curve_interpolator(CURVE_DATE, [], [])

    def test_cubic_requires_4_points(self):
        """三次样条需要 ≥4 个点"""
        with self.assertRaises(ValueError):
            build_curve_interpolator(
                CURVE_DATE, ["1Y", "2Y", "3Y"], [1.0, 1.5, 2.0], method="cubic"
            )


# ===================== 5. discount_factor 测试 =====================
class TestDiscountFactor(unittest.TestCase):
    """折现因子测试"""

    def test_annual_compounding(self):
        """年复利折现"""
        # DF = 1/(1+r)^t
        # r=1.5%, t=1
        df = discount_factor("1Y", 1.5, "annual")
        self.assertAlmostEqual(df, 1/1.015, places=6)

    def test_continuous_compounding(self):
        """连续复利折现"""
        # DF = e^(-r*t)
        import math
        df = discount_factor("1Y", 1.5, "continuous")
        self.assertAlmostEqual(df, math.exp(-0.015), places=6)

    def test_zero_tenor(self):
        """零期限 DF = 1"""
        self.assertEqual(discount_factor(0, 5), 1.0)
        self.assertEqual(discount_factor("0Y", 5), 1.0)

    def test_high_rate(self):
        """高利率折现"""
        df = discount_factor("10Y", 10.0)
        # 10% 10年 = 1/1.1^10 ≈ 0.3855
        self.assertAlmostEqual(df, 1/1.1**10, places=6)

    def test_low_rate(self):
        """低利率折现 (DF 接近 1)"""
        df = discount_factor("1Y", 0.01)
        # 0.01% 1年 ≈ 0.9999
        self.assertAlmostEqual(df, 1/1.0001, places=6)

    def test_year_input(self):
        """直接传入年数"""
        df = discount_factor(0.5, 1.30)  # 0.5 年, 1.30%
        self.assertAlmostEqual(df, 1/(1.0130)**0.5, places=6)

    def test_unknown_compounding_raises(self):
        """未知复利方式抛异常"""
        with self.assertRaises(ValueError):
            discount_factor("1Y", 1.5, "monthly")


# ===================== 6. discount_one 测试 =====================
class TestDiscountOne(unittest.TestCase):
    """单条折现测试"""

    def test_known_value(self):
        """已知值测试"""
        result = discount_one("1Y", 1000, CURVE_DATE, CURVE_POINTS, CURVE_RATES)
        self.assertEqual(result['tenor'], "1Y")
        self.assertAlmostEqual(result['tenor_years'], 1.0, places=6)
        self.assertAlmostEqual(result['rate'], 1.3372, places=3)
        self.assertAlmostEqual(result['df'], 0.9868, places=3)
        self.assertAlmostEqual(result['amount'], 1000)
        # PV = 1000 * 0.9868 ≈ 986.8
        self.assertAlmostEqual(result['pv'], 986.8, places=1)

    def test_long_tenor(self):
        """长期限测试"""
        result = discount_one("30Y", 1000, CURVE_DATE, CURVE_POINTS, CURVE_RATES)
        # 30Y 利率 2.2674%
        self.assertAlmostEqual(result['rate'], 2.2674, places=3)
        # PV 约为 1000 * 0.510 = 510
        self.assertAlmostEqual(result['pv'], 510.4, places=1)

    def test_negative_amount(self):
        """负金额 (流出)"""
        result = discount_one("1Y", -1000, CURVE_DATE, CURVE_POINTS, CURVE_RATES)
        self.assertEqual(result['amount'], -1000)
        self.assertAlmostEqual(result['pv'], -986.8, places=1)


# ===================== 7. discount_cashflows_batch 测试 =====================
class TestDiscountCashflowsBatch(unittest.TestCase):
    """批量折现测试"""

    def setUp(self):
        """每个测试前的初始化"""
        self.result = discount_cashflows_batch(
            R7_CASHFLOWS, CURVE_DATE, CURVE_POINTS, CURVE_RATES
        )

    def test_result_count(self):
        """结果数量等于现金流数量"""
        self.assertEqual(len(self.result.results), len(R7_CASHFLOWS))

    def test_result_type(self):
        """结果类型正确"""
        self.assertIsInstance(self.result, DiscountResult)
        for r in self.result.results:
            self.assertIsInstance(r, CashflowResult)

    def test_curve_date(self):
        """曲线日期正确"""
        self.assertEqual(self.result.curve_date, CURVE_DATE)

    def test_method(self):
        """默认插值方法"""
        self.assertEqual(self.result.method, "linear")

    def test_total_pv(self):
        """总 PV = 各 PV 之和"""
        sum_pv = sum(r.pv for r in self.result.results)
        self.assertAlmostEqual(self.result.total_pv, sum_pv, places=4)

    def test_first_cashflow(self):
        """第一条现金流正确 (R7 1M = 2450 亿)"""
        first = self.result.results[0]
        self.assertEqual(first.tenor, "1M")
        self.assertEqual(first.amount, 2450000000000)
        # PV 应该 ≈ 2450 * 0.999 = 2448 亿
        self.assertGreater(first.pv, 2440e9)
        self.assertLess(first.pv, 2450e9)

    def test_30y_cashflow(self):
        """30Y 现金流折现"""
        last = self.result.results[-1]
        self.assertEqual(last.tenor, "30Y")
        # 30Y DF ≈ 0.5104
        self.assertAlmostEqual(last.df, 0.5104, places=3)
        # PV = 7644 亿 * 0.5104 ≈ 3901 亿
        expected_pv = last.amount * last.df
        self.assertAlmostEqual(last.pv, expected_pv, places=4)

    def test_to_dataframe(self):
        """转为 DataFrame"""
        try:
            import pandas as pd
            df = self.result.to_dataframe()
            self.assertIsInstance(df, pd.DataFrame)
            self.assertEqual(len(df), len(R7_CASHFLOWS))
            # 检查列名
            for col in ['期限', '年数', '利率(%)', '折现因子', '现金流', '现值']:
                self.assertIn(col, df.columns)
        except ImportError:
            self.skipTest("pandas 不可用, 跳过 DataFrame 测试")

    def test_compounding(self):
        """不同复利方式"""
        result_annual = discount_cashflows_batch(
            R7_CASHFLOWS, CURVE_DATE, CURVE_POINTS, CURVE_RATES,
            compounding="annual"
        )
        result_continuous = discount_cashflows_batch(
            R7_CASHFLOWS, CURVE_DATE, CURVE_POINTS, CURVE_RATES,
            compounding="continuous"
        )
        # 年复利总 PV 应该大于连续复利 (因为 e^(-rt) < (1+r)^(-t))
        self.assertGreater(result_annual.total_pv, result_continuous.total_pv)
        # 差异应该 < 5%
        diff_ratio = (result_annual.total_pv - result_continuous.total_pv) / result_annual.total_pv
        self.assertLess(diff_ratio, 0.05)


# ===================== 8. 集成测试 (基于 R7 Excel 数据) =====================
class TestR7Integration(unittest.TestCase):
    """R7 (1.1.对公一般贷款) 集成测试"""

    def setUp(self):
        self.result = discount_cashflows_batch(
            R7_CASHFLOWS, CURVE_DATE, CURVE_POINTS, CURVE_RATES
        )

    def test_total_pv_in_yi(self):
        """总 PV 在亿元单位下的值"""
        total_yi = self.result.total_pv / 1e8
        # 期望值约 124,000 亿 (用 10 个曲线点)
        self.assertGreater(total_yi, 120000)
        self.assertLess(total_yi, 130000)

    def test_consistency_with_excel(self):
        """与 Excel (prcp_basic_20251231_v4.xlsx) 计算结果一致"""
        # Excel R7 PV = 129,571.31 亿 (使用 64 个期限点)
        # Python 用 10 个关键点 ≈ 124,065 亿 (差异源于插值密度)
        # 验证数量级正确
        excel_value = 129571.31e8  # 12,957,131,000,000 元
        python_value = self.result.total_pv
        # 误差应在 10% 以内 (插值差异)
        diff_ratio = abs(python_value - excel_value) / excel_value
        self.assertLess(diff_ratio, 0.10,
                       f"差异 {diff_ratio*100:.1f}% 超过 10%")

    def test_year_consistency(self):
        """年期一致性"""
        # 1M = 12 * 1M
        # 1Y = 12 * 1M (在数值上)
        self.assertAlmostEqual(
            tenor_to_years("1Y"),
            tenor_to_years("12M"),
            places=6
        )

    def test_curve_date_match(self):
        """曲线日期一致"""
        self.assertEqual(self.result.curve_date, CURVE_DATE)


# ===================== 9. 边界条件测试 =====================
class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""

    def test_empty_cashflows(self):
        """空现金流列表"""
        result = discount_cashflows_batch(
            [], CURVE_DATE, CURVE_POINTS, CURVE_RATES
        )
        self.assertEqual(len(result.results), 0)
        self.assertEqual(result.total_pv, 0.0)

    def test_zero_amount(self):
        """零金额现金流"""
        result = discount_cashflows_batch(
            [("1Y", 0)], CURVE_DATE, CURVE_POINTS, CURVE_RATES
        )
        self.assertEqual(result.total_pv, 0.0)

    def test_very_long_tenor(self):
        """超长期限 (100Y)"""
        result = discount_one("100Y", 1000, CURVE_DATE, CURVE_POINTS, CURVE_RATES)
        # 100Y 远超 30Y, 应该外推
        # DF 应该很小 (接近 0)
        self.assertLess(result['df'], 0.5)

    def test_very_short_tenor(self):
        """超短期限 (1D)"""
        result = discount_one("1D", 1000, CURVE_DATE, CURVE_POINTS, CURVE_RATES)
        # 1D DF 接近 1
        self.assertGreater(result['df'], 0.999)
        self.assertLess(result['df'], 1.000)


# ===================== 10. 回归测试 =====================
class TestRegression(unittest.TestCase):
    """回归测试 (固定结果对比)"""

    def test_known_discount_1y_1pct(self):
        """已知值: 1Y 1% DF"""
        df = discount_factor("1Y", 1.0)
        self.assertAlmostEqual(df, 1/1.01, places=8)

    def test_known_discount_5y_2pct(self):
        """已知值: 5Y 2% DF"""
        df = discount_factor("5Y", 2.0)
        self.assertAlmostEqual(df, 1/1.02**5, places=8)
        # 5Y 2% = 0.90573...
        self.assertAlmostEqual(df, 0.905731, places=6)

    def test_known_discount_continuous(self):
        """已知值: 连续复利 5% 1年"""
        import math
        df = discount_factor("1Y", 5.0, "continuous")
        self.assertAlmostEqual(df, math.exp(-0.05), places=8)

    def test_known_cashflow(self):
        """已知现金流: 100 元 1Y 1.5%"""
        result = discount_one("1Y", 100, CURVE_DATE, CURVE_POINTS, CURVE_RATES)
        # 1Y 1.3372% DF ≈ 0.9868
        # PV ≈ 98.68
        self.assertAlmostEqual(result['pv'], 98.68, places=1)


# ===================== 测试入口 =====================
if __name__ == "__main__":
    print("=" * 70)
    print("折现工具测试 (基于 prcp_basic_20251231_v4.xlsx)")
    print("=" * 70)
    print(f"测试用例数: 10 个测试类")
    print(f"测试数据: 2025-12-31 国债收益率曲线")
    print(f"参考文档: R7 (1.1.对公一般贷款) 现金流")
    print()
    unittest.main(verbosity=2)