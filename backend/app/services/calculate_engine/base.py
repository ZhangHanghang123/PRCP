"""引擎抽象基类 — 所有引擎必须实现的统一协议

## 设计目的

虽然不同引擎的算法和结果表结构差异很大（prcp_sim_run vs prcp_reverse_run），
但从 HTTP API 视角看，它们都暴露同一套接口：

    POST /<prefix>/schemes/{sid}/run     → 触发引擎执行
    GET  /<prefix>/runs/{rid}            → 查询执行状态
    GET  /<prefix>/runs                  → 列出所有执行
    GET  /<prefix>/results               → 查询结果快照

为了路由层能统一调度，定义 EngineBase 抽象基类：

    engine_type: str         # 引擎类型标识（如 "new_business"）
    engine_name: str         # 人类可读名称（如 "新业务模拟引擎"）

    run(...)                 # 执行
    get_run(...)             # 状态
    list_runs(...)           # 历史
    list_results(...)        # 快照
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class EngineBase(ABC):
    """引擎抽象基类

    子类必须实现：
      - engine_type / engine_name：元数据
      - run / get_run / list_runs / list_results：业务方法

    子类可选覆盖：
      - run_table_name / result_table_name：用于默认日志
    """

    # ===== 元数据（子类必须设置） =====
    engine_type: str = ""
    engine_name: str = ""

    # ===== 业务接口（子类必须实现） =====

    @abstractmethod
    def run(
        self,
        db,
        scheme_id: int,
        user: Any,
        **params,
    ) -> int:
        """执行引擎，返回 run_id

        参数:
            db: SQLAlchemy Session
            scheme_id: 业务方案 id（关联到具体业务表）
            user: 当前登录用户 dict（如 {"id": 1, "username": "admin"}）
            **params: 引擎特定参数（如 month_count）
        """

    @abstractmethod
    def get_run(self, db, run_id: int) -> Optional[Dict]:
        """查询单次执行的详细状态

        返回 dict 含 status / progress / total_nodes / duration_ms 等
        """

    @abstractmethod
    def list_runs(self, db, **filters) -> List[Dict]:
        """列出执行历史（支持按 scheme_id/status 等过滤）"""

    @abstractmethod
    def list_results(self, db, **filters) -> List[Dict]:
        """查询结果快照（按 run_id / date_offset / coa_node_id 过滤）"""

    # ===== 辅助方法（子类可直接复用） =====

    def info(self) -> Dict:
        """返回引擎元信息"""
        return {
            "engine_type": self.engine_type,
            "engine_name": self.engine_name,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.engine_type!r}>"
