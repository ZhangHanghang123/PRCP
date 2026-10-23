"""scoring_engine.py 单元测试

测试数据基于中信银行 2025-12-31 实测:
- LCR: 147.29% (1.4729)
- NSFR: 104.52% (1.0452)
- EVE: 10.54% (0.1054)
- CET1: 8.98% (0.0898)
- ROE: 9.61% (0.0961)

运行: python -m unittest test_scoring_engine.py -v
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scoring_engine import (
    KpiScheme,
    KpiDefinition,
    KpiScoreRule,
    KpiScoreSegment,
    KpiValue,
    ScoringEngine,
    DEMO_SCHEME,
    DEMO_DEFINITIONS,
    DEMO_RULES,
    DEMO_SEGMENTS,
)


# ===================== 测试数据 =====================
CITIC_VALUES = {
    "LCR": 1.4729,    # 147.29%
    "NSFR": 1.0452,   # 104.52%
    "EVE": 0.1054,    # 10.54%
    "CET1": 0.0898,   # 8.98%
    "ROE": 0.0961,    # 9.61% (2026 H1)
}


def make_engine():
    """创建测试用引擎 (使用 DEMO 配置)"""
    return ScoringEngine(
        scheme=DEMO_SCHEME,
        definitions=DEMO_DEFINITIONS,
        rules=DEMO_RULES,
        segments=DEMO_SEGMENTS,
    )


# ===================== 1. 数据类测试 =====================
class TestDataClasses(unittest.TestCase):
    """prcp 实体数据类测试"""

    def test_kpi_scheme_creation(self):
        """KpiScheme 创建"""
        s = KpiScheme(scheme_code="BANK_SCORE_2025_V1", scheme_name="测试方案")
        self.assertEqual(s.scheme_code, "BANK_SCORE_2025_V1")
        self.assertEqual(s.scheme_name, "测试方案")
        self.assertEqual(s.status, "ACTIVE")  # 默认值
        self.assertEqual(s.kpi_count, 0)  # 默认值

    def test_kpi_definition_creation(self):
        """KpiDefinition 创建"""
        d = KpiDefinition(kpi_code="LCR", kpi_name="流动性覆盖率", calc_unit="%")
        self.assertEqual(d.kpi_code, "LCR")
        self.assertEqual(d.calc_unit, "%")
        self.assertEqual(d.indicator_type, 1)  # 默认 1=公式

    def test_kpi_score_rule_creation(self):
        """KpiScoreRule 创建"""
        r = KpiScoreRule(scheme_id=1, kpi_id=1, rule_name="LCR 规则", higher_is_better=1)
        self.assertEqual(r.higher_is_better, 1)
        self.assertEqual(r.total_score, 100.0)  # 默认
        self.assertEqual(r.calc_method, "INTERVAL")  # 默认

    def test_kpi_score_segment_creation(self):
        """KpiScoreSegment 创建"""
        s = KpiScoreSegment(rule_id=1, seg_order=1, min_value=0, max_value=1.0,
                            score=0, segment_desc="红线")
        self.assertEqual(s.seg_order, 1)
        self.assertEqual(s.min_value, 0)
        self.assertEqual(s.score, 0)

    def test_kpi_value_creation(self):
        """KpiValue 创建"""
        kv = KpiValue(kpi_id=1, data_date="2025-12-31", current_value=1.4729)
        self.assertEqual(kv.data_date, "2025-12-31")
        self.assertEqual(kv.current_value, 1.4729)
        self.assertIsNone(kv.score)


# ===================== 2. 评分引擎初始化测试 =====================
class TestScoringEngineInit(unittest.TestCase):
    """ScoringEngine 初始化测试"""

    def test_default_init(self):
        """默认初始化使用 5 指标"""
        engine = make_engine()
        self.assertEqual(engine.scheme.scheme_code, "BANK_SCORE_2025_V1")
        self.assertEqual(len(engine.list_kpi_codes()), 5)
        self.assertIn("LCR", engine.definitions)
        self.assertIn("NSFR", engine.definitions)
        self.assertIn("EVE", engine.definitions)
        self.assertIn("CET1", engine.definitions)
        self.assertIn("ROE", engine.definitions)

    def test_segments_sorted(self):
        """段位按 seg_order 升序排列"""
        engine = make_engine()
        for kpi_code, segs in engine.segments.items():
            seg_orders = [s.seg_order for s in segs]
            self.assertEqual(seg_orders, sorted(seg_orders),
                             f"{kpi_code} 段位未按 seg_order 升序")

    def test_custom_init(self):
        """自定义初始化"""
        custom_scheme = KpiScheme(scheme_code="CUSTOM", scheme_name="自定义")
        # 用 DEMO 配置 + 自定义 scheme
        engine = ScoringEngine(
            scheme=custom_scheme,
            definitions=DEMO_DEFINITIONS,
            rules=DEMO_RULES,
            segments=DEMO_SEGMENTS,
        )
        self.assertEqual(engine.scheme.scheme_code, "CUSTOM")
        self.assertEqual(engine.scheme.scheme_name, "自定义")
        # 其他配置不变
        self.assertEqual(len(engine.list_kpi_codes()), 5)

    def test_inconsistent_keys_raises(self):
        """definitions/rules/segments 不一致抛 ValueError"""
        with self.assertRaises(ValueError):
            ScoringEngine(
                scheme=DEMO_SCHEME,
                definitions=DEMO_DEFINITIONS,
                rules=DEMO_RULES,
                segments={},  # 空 segments, 与 definitions 不一致
            )


# ===================== 3. 单指标评分测试 =====================
class TestScoreIndicator(unittest.TestCase):
    """单指标评分测试"""

    def setUp(self):
        self.engine = make_engine()

    def test_lcr_optimal(self):
        """LCR 适度最优 (147.29%)"""
        r = self.engine.score_indicator("LCR", 1.4729)
        self.assertEqual(r["score"], 100)
        self.assertIn("适度最优", r["segment_desc"])

    def test_lcr_red_line(self):
        """LCR 红利线 (<100%)"""
        r = self.engine.score_indicator("LCR", 0.95)
        self.assertEqual(r["score"], 0)
        self.assertIn("红利线", r["segment_desc"])

    def test_ceti_red_line(self):
        """CET1 红线 (<8.7%)"""
        r = self.engine.score_indicator("CET1", 0.08)
        self.assertEqual(r["score"], 0)
        self.assertIn("红线", r["segment_desc"])

    def test_lcr_upper_bound(self):
        """LCR 极度过剩 (250%)"""
        r = self.engine.score_indicator("LCR", 2.50)
        # 应该落到 (2.00, 9.99) 段位, score=75
        self.assertEqual(r["score"], 75)
        self.assertIn("极度过剩", r["segment_desc"])

    def test_eve_lower_better(self):
        """EVE 越低越好 (10.54%)"""
        r = self.engine.score_indicator("EVE", 0.1054)
        # EVE seg_order 3 (0.105, 0.11) score=55
        self.assertEqual(r["score"], 55)
        self.assertIn("⭐中信实测", r["segment_desc"])

    def test_eve_red_line(self):
        """EVE 触发红线 (>15%)"""
        r = self.engine.score_indicator("EVE", 0.18)
        self.assertEqual(r["score"], 0)
        self.assertIn("红线", r["segment_desc"])

    def test_eve_extreme_low(self):
        """EVE 极低 (<6%)"""
        r = self.engine.score_indicator("EVE", 0.03)
        # EVE seg_order 7 (0.00, 0.06) score=95
        self.assertEqual(r["score"], 95)
        self.assertIn("极低", r["segment_desc"])

    def test_nsfr_citic(self):
        """NSFR 中信实测 (104.52%)"""
        r = self.engine.score_indicator("NSFR", 1.0452)
        # NSFR seg_order 4 (1.045, 1.05) score=85
        self.assertEqual(r["score"], 85)

    def test_ceti_citic(self):
        """CET1 中信实测 (8.98%)"""
        r = self.engine.score_indicator("CET1", 0.0898)
        # CET1 seg_order 3 (0.089, 0.090) score=88
        self.assertEqual(r["score"], 88)
        self.assertIn("⭐中信实测", r["segment_desc"])

    def test_ceti_red_line(self):
        """CET1 红线 (<8.7%)"""
        r = self.engine.score_indicator("CET1", 0.08)
        self.assertEqual(r["score"], 0)
        self.assertIn("红线", r["segment_desc"])

    def test_roe_citic(self):
        """ROE 中信实测 (9.61%)"""
        r = self.engine.score_indicator("ROE", 0.0961)
        # ROE seg_order 4 (0.095, 0.0961) score=85
        self.assertEqual(r["score"], 85)
        self.assertIn("⭐中信实测", r["segment_desc"])

    def test_roe_red_line(self):
        """ROE 硬约束红线 (<6%)"""
        r = self.engine.score_indicator("ROE", 0.05)
        self.assertEqual(r["score"], 0)

    def test_unknown_kpi_raises(self):
        """未知指标抛 KeyError"""
        with self.assertRaises(KeyError):
            self.engine.score_indicator("UNKNOWN", 1.0)

    def test_result_structure(self):
        """结果 dict 包含所有必要字段"""
        r = self.engine.score_indicator("LCR", 1.5)
        for key in ["kpi_code", "kpi_name", "current_value", "score",
                    "seg_order", "segment_desc", "higher_is_better", "rule_name"]:
            self.assertIn(key, r)


# ===================== 4. 多指标评分测试 =====================
class TestScoreAll(unittest.TestCase):
    """批量评分测试"""

    def setUp(self):
        self.engine = make_engine()

    def test_score_all_5_indicators(self):
        """5 指标完整评分"""
        result = self.engine.score_all(CITIC_VALUES)
        self.assertEqual(result["kpi_count"], 5)
        self.assertEqual(len(result["missing"]), 0)
        # 5 个分数相加: LCR 100 + NSFR 85 + EVE 55 + CET1 88 + ROE 85 = 413
        self.assertEqual(result["total_score"], 100 + 85 + 55 + 88 + 85)

    def test_score_all_partial(self):
        """部分指标 (缺指标)"""
        partial = {"LCR": 1.4729, "NSFR": 1.0452}
        result = self.engine.score_all(partial)
        self.assertEqual(result["kpi_count"], 2)
        self.assertEqual(len(result["missing"]), 3)
        self.assertIn("EVE", result["missing"])
        self.assertIn("CET1", result["missing"])
        self.assertIn("ROE", result["missing"])

    def test_score_all_empty(self):
        """空字典"""
        result = self.engine.score_all({})
        self.assertEqual(result["kpi_count"], 0)
        self.assertEqual(result["total_score"], 0)
        self.assertEqual(len(result["missing"]), 5)

    def test_score_all_citic_expected(self):
        """中信实测总分"""
        result = self.engine.score_all(CITIC_VALUES)
        # 期望总分
        self.assertGreater(result["total_score"], 400)
        self.assertLess(result["total_score"], 500)


# ===================== 5. KpiValue 构建测试 =====================
class TestBuildKpiValues(unittest.TestCase):
    """KpiValue 回写测试"""

    def setUp(self):
        self.engine = make_engine()

    def test_build_kpi_values(self):
        """构造 KpiValue 列表"""
        kv_list = self.engine.build_kpi_values(
            CITIC_VALUES,
            data_date="2025-12-31",
            version="BANK_SCORE_2025_V1",
        )
        self.assertEqual(len(kv_list), 5)
        for kv in kv_list:
            self.assertIsInstance(kv, KpiValue)
            self.assertEqual(kv.data_date, "2025-12-31")
            self.assertEqual(kv.version, "BANK_SCORE_2025_V1")
            self.assertIsNotNone(kv.score)
            self.assertIn("scoring_engine", kv.calc_source)
            self.assertIn("seg_order=", kv.calc_log)

    def test_build_kpi_values_empty(self):
        """空字典构造"""
        kv_list = self.engine.build_kpi_values({})
        self.assertEqual(len(kv_list), 0)


# ===================== 6. 工具方法测试 =====================
class TestUtilityMethods(unittest.TestCase):
    """工具方法测试"""

    def setUp(self):
        self.engine = make_engine()

    def test_list_kpi_codes(self):
        """列出所有指标"""
        codes = self.engine.list_kpi_codes()
        self.assertEqual(len(codes), 5)
        self.assertEqual(codes[0], "LCR")
        self.assertEqual(codes[-1], "ROE")

    def test_get_kpi_info(self):
        """获取指标完整信息"""
        info = self.engine.get_kpi_info("LCR")
        self.assertIn("definition", info)
        self.assertIn("rule", info)
        self.assertIn("segments", info)
        self.assertEqual(info["definition"].kpi_code, "LCR")
        self.assertEqual(len(info["segments"]), 8)  # LCR 有 8 段

    def test_get_kpi_info_unknown(self):
        """未知指标抛 KeyError"""
        with self.assertRaises(KeyError):
            self.engine.get_kpi_info("UNKNOWN")


# ===================== 7. 边界条件测试 =====================
class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.engine = make_engine()

    def test_boundary_min_segment(self):
        """段位下限边界"""
        # LCR 段 1: (0, 1.0) score=0
        r = self.engine.score_indicator("LCR", 0.0)
        self.assertEqual(r["score"], 0)

    def test_boundary_max_segment(self):
        """段位上限边界"""
        # LCR 段 1: (0, 1.0) score=0
        r = self.engine.score_indicator("LCR", 1.0)
        self.assertEqual(r["score"], 0)
        # LCR 段 2: (1.0, 1.1) score=-50
        r = self.engine.score_indicator("LCR", 1.1)
        self.assertEqual(r["score"], -50)

    def test_boundary_over_upper_extreme(self):
        """上限之外 (LCR 极度过剩)"""
        # LCR 上限 9.99, 9.99 落在 seg 8 (2.0, 9.99) score=75
        r = self.engine.score_indicator("LCR", 9.99)
        self.assertEqual(r["score"], 75)

    def test_boundary_under_lower_eve(self):
        """EVE 极低 (低于 0.06)"""
        r = self.engine.score_indicator("EVE", 0.0)
        # EVE seg_order 7 (0.00, 0.06) score=95
        self.assertEqual(r["score"], 95)


# ===================== 8. 回归测试 =====================
class TestRegression(unittest.TestCase):
    """回归测试 (固定结果对比)"""

    def setUp(self):
        self.engine = make_engine()

    def test_citic_full_score(self):
        """中信实测完整评分"""
        result = self.engine.score_all(CITIC_VALUES)
        # 固定结果: LCR 100 + NSFR 85 + EVE 55 + CET1 88 + ROE 85 = 413
        self.assertEqual(result["total_score"], 413)

    def test_each_kpi_independently(self):
        """每个指标独立验证"""
        cases = [
            ("LCR", 1.4729, 100),
            ("NSFR", 1.0452, 85),
            ("EVE", 0.1054, 55),
            ("CET1", 0.0898, 88),
            ("ROE", 0.0961, 85),
        ]
        for code, value, expected_score in cases:
            r = self.engine.score_indicator(code, value)
            self.assertEqual(r["score"], expected_score,
                             f"{code}={value} 期望 {expected_score}, 实际 {r['score']}")


# ===================== 测试入口 =====================
if __name__ == "__main__":
    print("=" * 70)
    print("prcp 评分引擎单元测试")
    print("=" * 70)
    print(f"测试数据: 中信银行 2025-12-31 实测")
    print(f"指标: LCR/NSFR/EVE/CET1/ROE 5 项")
    print()
    unittest.main(verbosity=2)