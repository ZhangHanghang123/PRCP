"""新业务模拟引擎子包 — 注册到全局引擎注册表

此模块导入时自动注册 NewBusinessEngine 实例。
"""
from app.services.calculate_engine.registry import register_engine
from .engine import NewBusinessEngine

# 注册实例（单例）
register_engine(NewBusinessEngine())

__all__ = ["NewBusinessEngine"]
