"""PRCP ESG 场景工厂 — 算法包

模块分层（自下而上）：
    1. svensson.py            SvenssonYieldCurve（6 参数曲线还原）
    2. yield_curve_generator.py  YieldCurveGenerator（PCA 拟合 + HJM 路径生成）
    3. scenario_set.py        ScenarioSet（npz 持久化）
    4. validator.py           校验器（波动率递减 / 非负利率）

调用模式：
    from app.services.esg import SvenssonYieldCurve, YieldCurveGenerator, ScenarioSet

设计原则（PRCP 风格）：
    - 月频 dt=1/12（不引入 DeepALM 的 22 日转换因子）
    - 默认 13 个期限点 [1,3,6,12,24,36,48,60,84,120,180,240,360]
    - 纯 numpy + scipy（无 torch）
    - 与 PRCP 现有 prcp_* 数据库 schema 字段命名对齐（theta0~3 而非 beta0~3）
"""
from .svensson import SvenssonYieldCurve
from .yield_curve_generator import YieldCurveGenerator, DEFAULT_MATURITIES_MONTHS
from .scenario_set import ScenarioSet
from .validator import validate_paths, validate_factor_loadings

__all__ = [
    "SvenssonYieldCurve",
    "YieldCurveGenerator",
    "ScenarioSet",
    "validate_paths",
    "validate_factor_loadings",
    "DEFAULT_MATURITIES_MONTHS",
]