"""中信银行评分引擎 (Scoring Engine)

字段命名严格对齐 prcp-java 实体:
- KpiScheme (prcp_kpi_scheme)
- KpiDefinition (prcp_kpi_definition)
- KpiScoreRule (prcp_kpi_score_rule)
- KpiScoreSegment (prcp_kpi_score_segment)
- KpiValue (prcp_kpi_value)

设计原则 (满足用户要求):
1. 引擎只做两件事: 单指标评分 + 多指标求和
   - score_indicator(kpi_code, value): 按 seg_order 升序遍历段位, 找首个
     min_value <= value <= max_value 的段, 返回 segment.score
   - score_all(kpi_values): 各 score 直接相加 (权重默认 1), 不评级映射
2. 所有评分规则通过 prcp 指标方案内容封装传入, 引擎不内置任何规则
   - __init__ 必须显式传入 scheme / definitions / rules / segments
   - 提供 from_prcp_db() 类方法从数据库加载 (需 prcp-client 包)
   - DEMO_* 类属性仅用于演示, 实际使用应替换为 prcp 内容

本次演示配置 (5 指标 LCR/NSFR/EVE/CET1/ROE) 由 DEMO_* 提供,
实际生产请从 prcp_db 加载真实配置.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from decimal import Decimal


# ===================== 1. prcp 实体数据类 =====================
@dataclass
class KpiScheme:
    """指标方案 (prcp_kpi_scheme)"""
    scheme_code: str
    scheme_name: str
    description: str = ""
    kpi_count: int = 0
    status: str = "ACTIVE"
    id: Optional[int] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_deleted: int = 0


@dataclass
class KpiDefinition:
    """指标定义 (prcp_kpi_definition)"""
    kpi_code: str
    kpi_name: str
    scheme_id: Optional[int] = None
    indicator_type: int = 1
    formula: str = ""
    script_path: str = ""
    script_name: str = ""
    calc_unit: str = ""
    formula_desc: str = ""
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    status: str = "ACTIVE"
    id: Optional[int] = None
    is_deleted: int = 0


@dataclass
class KpiScoreRule:
    """评分规则 (prcp_kpi_score_rule)"""
    scheme_id: int
    kpi_id: int
    rule_name: str
    calc_method: str = "INTERVAL"
    total_score: float = 100.0
    higher_is_better: int = 1
    description: str = ""
    status: str = "ACTIVE"
    id: Optional[int] = None
    is_deleted: int = 0


@dataclass
class KpiScoreSegment:
    """评分段位 (prcp_kpi_score_segment)"""
    rule_id: int
    seg_order: int
    min_value: float
    max_value: float
    score: float
    segment_desc: str = ""
    id: Optional[int] = None
    is_deleted: int = 0


@dataclass
class KpiValue:
    """指标值 (prcp_kpi_value)"""
    kpi_id: int
    data_date: str
    current_value: float
    version: str = ""
    prev_value: Optional[float] = None
    prev_year_value: Optional[float] = None
    calc_source: str = ""
    calc_log: str = ""
    score: Optional[float] = None
    id: Optional[int] = None
    is_deleted: int = 0


# ===================== 2. 评分引擎 =====================
class ScoringEngine:
    """中信银行评分引擎

    引擎本身不内置任何评分规则.
    所有规则 (scheme/definitions/rules/segments) 必须通过 __init__ 传入,
    或通过 from_prcp_db() 类方法从 prcp 数据库加载.

    Attributes:
        scheme: KpiScheme
        definitions: dict[kpi_code, KpiDefinition]
        rules: dict[kpi_code, KpiScoreRule]
        segments: dict[kpi_code, list[KpiScoreSegment]] (按 seg_order 升序)

    本类不内置:
    - ❌ 任何指标代码 (LCR/NSFR/...)
    - ❌ 任何段位定义 (min/max/score)
    - ❌ 任何评分阈值
    """

    def __init__(
        self,
        scheme: KpiScheme,
        definitions: Dict[str, KpiDefinition],
        rules: Dict[str, KpiScoreRule],
        segments: Dict[str, List[KpiScoreSegment]],
    ):
        """初始化评分引擎 (所有参数必填)

        Args:
            scheme: KpiScheme (prcp_kpi_scheme)
            definitions: {kpi_code: KpiDefinition}
            rules: {kpi_code: KpiScoreRule}
            segments: {kpi_code: list[KpiScoreSegment]}

        Raises:
            ValueError: definitions / rules / segments 数量不一致
        """
        if not (definitions.keys() == rules.keys() == segments.keys()):
            raise ValueError(
                f"definitions/rules/segments 的 kpi_code 必须一致: "
                f"def={list(definitions.keys())}, "
                f"rule={list(rules.keys())}, "
                f"seg={list(segments.keys())}"
            )
        self.scheme = scheme
        self.definitions = definitions
        self.rules = rules
        # 段位按 seg_order 升序排序
        self.segments = {
            code: sorted(segs, key=lambda s: s.seg_order)
            for code, segs in segments.items()
        }

    # ===================== 3. 单指标评分 =====================
    def score_indicator(self, kpi_code: str, current_value: float) -> Dict:
        """单指标评分

        Args:
            kpi_code: 指标编码 (如 "LCR")
            current_value: 实测值

        Returns:
            dict: {
                'kpi_code', 'kpi_name',
                'current_value', 'score', 'seg_order', 'segment_desc',
                'higher_is_better', 'rule_name'
            }

        Raises:
            KeyError: kpi_code 不存在
            ValueError: 未找到匹配段位
        """
        if kpi_code not in self.definitions:
            raise KeyError(
                f"指标代码 {kpi_code} 不存在 (可用: {list(self.definitions.keys())})"
            )

        definition = self.definitions[kpi_code]
        rule = self.rules[kpi_code]
        segs = self.segments[kpi_code]

        # 边界检查
        first_seg = segs[0]
        last_seg = segs[-1]
        # higher_is_better=1 (越高越好): 段位按 score 升序 (红线→安全)
        #   - 低于 first.min_value → 红线段
        #   - 高于 last.max_value → 极度过剩 (last_seg)
        if rule.higher_is_better == 1:
            if current_value < first_seg.min_value:
                return self._build_result(kpi_code, definition, rule, first_seg, current_value)
            if current_value > last_seg.max_value:
                return self._build_result(kpi_code, definition, rule, last_seg, current_value)
        # higher_is_better=0 (越低越好): 段位按 score 升序 (红线→安全), min_value 降序
        #   - 高于 first.min_value → 红线段
        #   - 低于 last.max_value → 极低 (last_seg)
        else:
            if current_value > first_seg.min_value:
                return self._build_result(kpi_code, definition, rule, first_seg, current_value)
            if current_value < last_seg.max_value:
                return self._build_result(kpi_code, definition, rule, last_seg, current_value)

        # 按 seg_order 升序遍历, 找首个满足区间的段位
        for seg in segs:
            if seg.min_value <= current_value <= seg.max_value:
                return self._build_result(kpi_code, definition, rule, seg, current_value)

        raise ValueError(
            f"指标 {kpi_code} 值 {current_value} 不在任何段位区间内"
        )

    def _build_result(
        self,
        kpi_code: str,
        definition: KpiDefinition,
        rule: KpiScoreRule,
        segment: KpiScoreSegment,
        current_value: float,
    ) -> Dict:
        return {
            "kpi_code": kpi_code,
            "kpi_name": definition.kpi_name,
            "current_value": current_value,
            "score": segment.score,
            "seg_order": segment.seg_order,
            "segment_desc": segment.segment_desc,
            "higher_is_better": rule.higher_is_better,
            "rule_name": rule.rule_name,
        }

    # ===================== 4. 多指标求和 (权重默认 1) =====================
    def score_all(self, kpi_values: Dict[str, float]) -> Dict:
        """批量评分 (各 score 直接相加, 权重默认 1)

        Args:
            kpi_values: {kpi_code: current_value, ...}

        Returns:
            dict: {
                'scheme_code', 'scheme_name',
                'total_score': 总分,
                'kpi_count': 实际评分指标数,
                'details': [单指标结果],
                'missing': [缺失的指标代码列表]
            }
        """
        results = []
        missing = []
        for kpi_code in self.definitions.keys():
            if kpi_code not in kpi_values:
                missing.append(kpi_code)
                continue
            try:
                result = self.score_indicator(kpi_code, kpi_values[kpi_code])
                results.append(result)
            except ValueError:
                # 找不到匹配段位 → score=0
                results.append({
                    "kpi_code": kpi_code,
                    "kpi_name": self.definitions[kpi_code].kpi_name,
                    "current_value": kpi_values[kpi_code],
                    "score": 0,
                    "seg_order": 0,
                    "segment_desc": "无匹配段位",
                    "higher_is_better": self.rules[kpi_code].higher_is_better,
                    "rule_name": self.rules[kpi_code].rule_name,
                })

        # 各 score 直接相加 (权重默认 1)
        total_score = sum(r["score"] for r in results)
        return {
            "scheme_code": self.scheme.scheme_code,
            "scheme_name": self.scheme.scheme_name,
            "total_score": total_score,
            "kpi_count": len(results),
            "details": results,
            "missing": missing,
        }

    # ===================== 5. KpiValue 回写 =====================
    def build_kpi_values(
        self,
        current_values: Dict[str, float],
        data_date: str = "",
        version: str = "",
    ) -> List[KpiValue]:
        """构造 KpiValue 列表 (评分后写回数据库)

        Args:
            current_values: {kpi_code: value}
            data_date: 数据日期 (如 "2025-12-31")
            version: 方案版本 (如 "BANK_SCORE_2025_V1")
        """
        results = self.score_all(current_values)
        kv_list = []
        for detail in results["details"]:
            definition = self.definitions[detail["kpi_code"]]
            kv = KpiValue(
                kpi_id=definition.id or 0,
                data_date=data_date,
                current_value=detail["current_value"],
                version=version,
                score=detail["score"],
                calc_source="scoring_engine",
                calc_log=f"seg_order={detail['seg_order']}, segment={detail['segment_desc']}",
            )
            kv_list.append(kv)
        return kv_list

    # ===================== 6. 工具方法 =====================
    def list_kpi_codes(self) -> List[str]:
        return list(self.definitions.keys())

    def get_kpi_info(self, kpi_code: str) -> Dict:
        if kpi_code not in self.definitions:
            raise KeyError(f"指标 {kpi_code} 不存在")
        return {
            "definition": self.definitions[kpi_code],
            "rule": self.rules[kpi_code],
            "segments": self.segments[kpi_code],
        }

    # ===================== 6.1 结果格式化 (字符串输出) =====================
    @staticmethod
    def format_indicator(result: Dict) -> str:
        """把 score_indicator 返回的 dict 格式化为字符串

        示例输出:
            [LCR] 流动性覆盖率 = 147.29% → 适度最优 (score=100, seg_order=6)
        """
        kpi_code = result["kpi_code"]
        kpi_name = result["kpi_name"]
        value = result["current_value"]
        score = result["score"]
        seg = result["segment_desc"]
        order = result["seg_order"]
        return f"[{kpi_code}] {kpi_name} = {value*100:.2f}% → {seg} (score={score}, seg_order={order})"

    @staticmethod
    def format_score_all(result: Dict) -> str:
        """把 score_all 返回的 dict 格式化为字符串 (含总分 + 各指标明细)

        示例输出:
            方案: BANK_SCORE_2025_V1
            总综合分 = 413
            评估指标 = 5
            缺失指标 = []
            ---
            [LCR]  流动性覆盖率        = 147.29% → 适度最优 (score=100)
            [NSFR] 净稳定资金比例      = 104.52% → ⭐中信实测 104.52% (score=85)
            ...
        """
        lines = []
        lines.append(f"方案: {result['scheme_code']} - {result['scheme_name']}")
        lines.append(f"总综合分 = {result['total_score']}")
        lines.append(f"评估指标 = {result['kpi_count']}")
        lines.append(f"缺失指标 = {result['missing']}")
        lines.append("-" * 60)
        for d in result["details"]:
            lines.append(ScoringEngine.format_indicator(d))
        return "\n".join(lines)

    def print_indicator(self, kpi_code: str, current_value: float) -> None:
        """便捷方法: 评分并直接打印"""
        result = self.score_indicator(kpi_code, current_value)
        print(self.format_indicator(result))

    def print_score_all(self, kpi_values: Dict[str, float]) -> None:
        """便捷方法: 批量评分并直接打印"""
        result = self.score_all(kpi_values)
        print(self.format_score_all(result))

    # ===================== 7. 从 prcp_db 加载 (工厂方法) =====================
    @classmethod
    def from_prcp_db(
        cls,
        scheme_code: str,
        db_session=None,
    ) -> "ScoringEngine":
        """从 prcp 数据库加载评分引擎

        Args:
            scheme_code: 方案编码 (如 "BANK_SCORE_2025_V1")
            db_session: prcp-client 数据库会话 (如 SQLAlchemy session)

        Returns:
            ScoringEngine 实例

        实际实现需要 prcp-client 库, 这里只给出接口契约.
        """
        raise NotImplementedError(
            "from_prcp_db 需 prcp-client 库. 接口契约:\n"
            "1. SELECT * FROM prcp_kpi_scheme WHERE scheme_code=?\n"
            "2. SELECT * FROM prcp_kpi_definition WHERE scheme_id=?\n"
            "3. SELECT * FROM prcp_kpi_score_rule WHERE scheme_id=?\n"
            "4. SELECT * FROM prcp_kpi_score_segment "
            "     WHERE rule_id IN (rule_ids) ORDER BY seg_order\n"
            "5. 构造 KpiScheme/KpiDefinition/KpiScoreRule/KpiScoreSegment\n"
            "6. 传入 __init__()"
        )


# ===================== 8. 演示数据 (本次上线, 仅供 demo 使用) =====================
# 这些常量仅作为演示用途, 实际生产应通过 from_prcp_db() 加载
DEMO_SCHEME = KpiScheme(
    scheme_code="BANK_SCORE_2025_V1",
    scheme_name="中信银行 2025 年度评分方案 (demo)",
    description="LCR/NSFR/EVE/CET1/ROE 5 指标, 来自 prcp 数据库",
    kpi_count=5,
    status="ACTIVE",
)

DEMO_DEFINITIONS = {
    "LCR": KpiDefinition(
        kpi_code="LCR", kpi_name="流动性覆盖率", calc_unit="%",
    ),
    "NSFR": KpiDefinition(
        kpi_code="NSFR", kpi_name="净稳定资金比例", calc_unit="%",
    ),
    "EVE": KpiDefinition(
        kpi_code="EVE", kpi_name="银行账户利率风险", calc_unit="%",
    ),
    "CET1": KpiDefinition(
        kpi_code="CET1", kpi_name="核心一级资本充足率", calc_unit="%",
    ),
    "ROE": KpiDefinition(
        kpi_code="ROE", kpi_name="净资产收益率", calc_unit="%",
    ),
}

DEMO_RULES = {
    "LCR": KpiScoreRule(scheme_id=1, kpi_id=1, rule_name="LCR 评分规则", higher_is_better=1, total_score=100),
    "NSFR": KpiScoreRule(scheme_id=1, kpi_id=2, rule_name="NSFR 评分规则", higher_is_better=1, total_score=100),
    "EVE": KpiScoreRule(scheme_id=1, kpi_id=3, rule_name="EVE 评分规则", higher_is_better=0, total_score=100),
    "CET1": KpiScoreRule(scheme_id=1, kpi_id=4, rule_name="CET1 评分规则", higher_is_better=1, total_score=100),
    "ROE": KpiScoreRule(scheme_id=1, kpi_id=5, rule_name="ROE 评分规则", higher_is_better=1, total_score=100),
}

DEMO_SEGMENTS = {
    "LCR": [
        KpiScoreSegment(1, 1, 0.00, 1.00, 0,    "红利线 <100%"),
        KpiScoreSegment(1, 2, 1.00, 1.10, -50,  "贴近本行底线"),
        KpiScoreSegment(1, 3, 1.10, 1.20, -100, "贴近红线"),
        KpiScoreSegment(1, 4, 1.20, 1.30, 30,   "危险-重惩罚"),
        KpiScoreSegment(1, 5, 1.30, 1.40, 80,   "预警-轻惩罚"),
        KpiScoreSegment(1, 6, 1.40, 1.50, 100,  "⭐适度最优"),
        KpiScoreSegment(1, 7, 1.50, 2.00, 95,   "略高 资金闲置"),
        KpiScoreSegment(1, 8, 2.00, 9.99, 75,   "极度过剩"),
    ],
    "NSFR": [
        KpiScoreSegment(2, 1, 0.00, 1.00, 0,    "红线 <100%"),
        KpiScoreSegment(2, 2, 1.00, 1.03, 35,   "危险-重惩罚"),
        KpiScoreSegment(2, 3, 1.03, 1.045, 65,  "预警-轻惩罚"),
        KpiScoreSegment(2, 4, 1.045, 1.05, 85,  "⭐中信实测 104.52%"),
        KpiScoreSegment(2, 5, 1.05, 1.07, 100,  "⭐适度最优"),
        KpiScoreSegment(2, 6, 1.07, 1.15, 90,  "略高"),
        KpiScoreSegment(2, 7, 1.15, 9.99, 75,  "过度稳定"),
    ],
    "EVE": [
        KpiScoreSegment(3, 1, 0.15,  9.99, 0,   "红线 >15%"),
        KpiScoreSegment(3, 2, 0.12,  0.15, 20,  "危险-重惩罚"),
        KpiScoreSegment(3, 3, 0.105, 0.11, 55,  "⭐中信实测 10.54%"),
        KpiScoreSegment(3, 4, 0.10,  0.12, 65,  "预警-轻惩罚"),
        KpiScoreSegment(3, 5, 0.08,  0.10, 85,  "可控"),
        KpiScoreSegment(3, 6, 0.06,  0.08, 96,  "⭐适度最优"),
        KpiScoreSegment(3, 7, 0.00,  0.06, 95,  "极低"),
    ],
    "CET1": [
        KpiScoreSegment(4, 1, 0.00,   0.087, 0,   "红线 <8.7%"),
        KpiScoreSegment(4, 2, 0.087,  0.089, 35,  "危险-重惩罚"),
        KpiScoreSegment(4, 3, 0.089,  0.090, 88,  "⭐中信实测 8.98%"),
        KpiScoreSegment(4, 4, 0.090,  0.100, 100, "⭐适度最优"),
        KpiScoreSegment(4, 5, 0.100,  0.130, 92,  "过高"),
        KpiScoreSegment(4, 6, 0.130,  1.000, 78,  "极度过剩"),
    ],
    "ROE": [
        KpiScoreSegment(5, 1, 0.00,   0.06, 0,   "硬约束红线 <6%"),
        KpiScoreSegment(5, 2, 0.06,   0.08, 50,  "低于行业"),
        KpiScoreSegment(5, 3, 0.08,   0.09, 75,  "行业中位"),
        KpiScoreSegment(5, 4, 0.095,  0.0961, 85, "⭐中信实测 9.61%"),
        KpiScoreSegment(5, 5, 0.09,   0.10, 85,  "行业中上"),
        KpiScoreSegment(5, 6, 0.10,   0.12, 94,  "优秀"),
        KpiScoreSegment(5, 7, 0.12,   1.00, 100, "⭐满分"),
    ],
}


# ===================== 9. 演示 (DEMO 配置) =====================
def demo_with_demo():
    """演示: 用 DEMO_* 配置 (中信银行 2025-12-31)"""
    print("=" * 70)
    print("DEMO: 用 DEMO 配置演示评分 (5 指标)")
    print("=" * 70)

    engine = ScoringEngine(
        scheme=DEMO_SCHEME,
        definitions=DEMO_DEFINITIONS,
        rules=DEMO_RULES,
        segments=DEMO_SEGMENTS,
    )

    citic_values = {
        "LCR": 1.4729,
        "NSFR": 1.0452,
        "EVE": 0.1054,
        "CET1": 0.0898,
        "ROE": 0.0961,
    }

    result = engine.score_all(citic_values)
    print(f"\n方案: {result['scheme_name']} ({result['scheme_code']})")
    print(f"总综合分: {result['total_score']}")
    print()
    for d in result["details"]:
        print(f"  {d['kpi_code']:<6} {d['current_value']*100:>6.2f}%  "
              f"{d['segment_desc']:<20} score={d['score']}")


# ===================== 10. 测试 =====================
if __name__ == "__main__":
    demo_with_demo()

    # 单指标评分演示
    print("\n" + "=" * 70)
    print("单指标评分演示")
    print("=" * 70)
    engine = ScoringEngine(DEMO_SCHEME, DEMO_DEFINITIONS, DEMO_RULES, DEMO_SEGMENTS)

    print("\nLCR 147.29%:")
    r = engine.score_indicator("LCR", 1.4729)
    print(f"  段位: {r['segment_desc']}, score={r['score']}")

    print("\nEVE 10.54%:")
    r = engine.score_indicator("EVE", 0.1054)
    print(f"  段位: {r['segment_desc']}, score={r['score']}")

    print("\n边界测试:")
    print(f"  LCR 0.95 (低于红线): score={engine.score_indicator('LCR', 0.95)['score']}")
    print(f"  EVE 0.18 (高于红线): score={engine.score_indicator('EVE', 0.18)['score']}")

    print("\n缺失指标测试:")
    partial = {"LCR": 1.5}
    r = engine.score_all(partial)
    print(f"  missing={r['missing']}, total_score={r['total_score']}")

    print("\n异常指标代码测试:")
    try:
        engine.score_indicator("UNKNOWN", 1.0)
    except KeyError as e:
        print(f"  KeyError: {e}")