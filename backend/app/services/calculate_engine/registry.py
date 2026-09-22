"""引擎注册表 — 单例工厂 + 自动发现

## 用法

### 注册新引擎（在子包 __init__.py 中）
```python
from app.services.calculate_engine.registry import register_engine
from .engine import NewBusinessEngine

register_engine(NewBusinessEngine())
```

### 在路由层获取引擎
```python
from app.services.calculate_engine import get_engine

engine = get_engine("new_business")
run_id = engine.run(db, scheme_id, user, month_count=60)
```

### 列出所有已注册引擎
```python
from app.services.calculate_engine import list_engine_types
print(list_engine_types())  # ["new_business"]
```
"""
from threading import Lock
from typing import Dict, List

from app.services.calculate_engine.base import EngineBase


# ===== 全局注册表 =====
_REGISTRY: Dict[str, EngineBase] = {}
_LOCK = Lock()


def register_engine(engine: EngineBase) -> None:
    """注册一个引擎实例（线程安全）

    Args:
        engine: 继承自 EngineBase 的实例

    Raises:
        ValueError: engine_type 为空或重复注册
    """
    if not isinstance(engine, EngineBase):
        raise TypeError(f"必须是 EngineBase 子类，实际 {type(engine)}")
    if not engine.engine_type:
        raise ValueError(f"{type(engine).__name__} 必须设置 engine_type")
    with _LOCK:
        if engine.engine_type in _REGISTRY:
            raise ValueError(
                f"引擎类型 {engine.engine_type!r} 已被 "
                f"{type(_REGISTRY[engine.engine_type]).__name__} 注册"
            )
        _REGISTRY[engine.engine_type] = engine


def get_engine(engine_type: str) -> EngineBase:
    """获取引擎实例

    Args:
        engine_type: 引擎类型标识

    Returns:
        EngineBase 实例

    Raises:
        KeyError: 未注册的类型
    """
    with _LOCK:
        if engine_type not in _REGISTRY:
            available = list(_REGISTRY.keys())
            raise KeyError(
                f"引擎类型 {engine_type!r} 未注册；已注册的: {available}"
            )
        return _REGISTRY[engine_type]


def list_engine_types() -> List[str]:
    """列出所有已注册的引擎类型"""
    with _LOCK:
        return sorted(_REGISTRY.keys())


def is_registered(engine_type: str) -> bool:
    """检查引擎类型是否已注册"""
    with _LOCK:
        return engine_type in _REGISTRY


def unregister_engine(engine_type: str) -> None:
    """取消注册（测试用）"""
    with _LOCK:
        _REGISTRY.pop(engine_type, None)
