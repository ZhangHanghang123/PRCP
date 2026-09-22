"""引擎计量包 — 系统中所有引擎的统一入口

## 包结构

```
services/calculate_engine/
├── __init__.py            # 本文件：公共 API
├── base.py                # EngineBase 抽象基类
├── registry.py            # 引擎注册表 + 工厂方法
├── new_business/          # 新业务模拟引擎（v1）
│   ├── __init__.py
│   └── engine.py
└── (未来)                 # 反算 / 试算 / 压力测试 / 假设分析 等
    ├── reverse/
    ├── stress/
    └── whatif/
```

## 设计原则

1. **每个引擎独立子包**：算法 + 数据访问 + 配置 都在自己的子包里
2. **基类统一协议**：所有引擎继承 `EngineBase`，对外暴露 `run / get_run / list_runs / list_results`
3. **注册表模式**：新引擎只需在子包 `__init__.py` 调用 `register(...)`，主入口通过 `get_engine(type)` 获取
4. **路由层解耦**：`routers/engines.py` 只负责 HTTP 收发，业务逻辑全部走 Engine 类

## 公共 API

```python
from app.services.calculate_engine import get_engine, list_engine_types

# 按 type 获取引擎实例（单例）
engine = get_engine("new_business")
run_id = engine.run(db, scheme_id=1, user={"id": 1}, month_count=60)

# 查看已注册的引擎类型
types = list_engine_types()  # ["new_business", ...]
```
"""
from app.services.calculate_engine.registry import (
    get_engine,
    list_engine_types,
    register_engine,
)

__all__ = ["get_engine", "list_engine_types", "register_engine"]
