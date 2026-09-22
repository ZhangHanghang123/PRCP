"""PRCP ESG · ScenarioSet（npz 持久化）

设计：
    - 内部用 dataclass 封装：paths (n × steps × maturities) + maturities + initial_yields + 元数据
    - save_to_npz: 写入 /var/lib/prcp/esg_cases/scenario_*.npz
    - load_from_npz: 读回（前端 / 下游 sim / reverse 模块用）
    - get_percentiles: 计算 p10/p50/p90（HJM 包络图用）
    - get_final_distribution: 终期分布（每个期限在所有情景下的均值/分位数）
"""
from __future__ import annotations
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class ScenarioSet:
    """HJM 情景集（持久化容器）"""

    n_scenarios: int
    n_steps: int
    n_maturities: int
    paths: np.ndarray                       # (n_scenarios, n_steps, n_maturities) 利率（百分比）
    maturities_months: np.ndarray           # (n_maturities,) 月期限数组
    initial_yields_pct: np.ndarray          # (n_maturities,) 初始利率（百分比）
    seed: int = 42
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 形状校验
        expected_shape = (self.n_scenarios, self.n_steps, self.n_maturities)
        if self.paths.shape != expected_shape:
            raise ValueError(
                f"paths 形状 {self.paths.shape} != 期望 {expected_shape}"
            )
        if len(self.maturities_months) != self.n_maturities:
            raise ValueError(
                f"maturities_months 长度 {len(self.maturities_months)} != n_maturities {self.n_maturities}"
            )
        if len(self.initial_yields_pct) != self.n_maturities:
            raise ValueError(
                f"initial_yields_pct 长度 {len(self.initial_yields_pct)} != n_maturities {self.n_maturities}"
            )

    # ===================== npz 持久化 =====================

    def save_to_npz(self, file_path: str) -> str:
        """保存为 .npz 压缩文件（含元数据 JSON 头）

        npz 内容：
            paths           (n, steps, maturities) float64
            maturities      (maturities,) int32
            initial_yields  (maturities,) float64
            seed            int32
            n_scenarios/n_steps/n_maturities int32
            metadata_json   str（JSON 字符串）
        """
        import os, json as _json

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        np.savez_compressed(
            file_path,
            paths=self.paths.astype(np.float64),
            maturities=self.maturities_months.astype(np.int32),
            initial_yields=self.initial_yields_pct.astype(np.float64),
            seed=np.int32(self.seed),
            n_scenarios=np.int32(self.n_scenarios),
            n_steps=np.int32(self.n_steps),
            n_maturities=np.int32(self.n_maturities),
            metadata_json=np.array(_json.dumps({
                "description": self.description,
                "metadata": self.metadata,
                "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            })),
        )
        file_size = os.path.getsize(file_path)
        logger.info(f"ScenarioSet 已保存: {file_path} ({file_size} bytes, {self.n_scenarios}×{self.n_steps}×{self.n_maturities})")
        return file_path

    @classmethod
    def load_from_npz(cls, file_path: str) -> "ScenarioSet":
        """从 .npz 读取并构造 ScenarioSet"""
        import json as _json

        with np.load(file_path, allow_pickle=False) as f:
            paths = f["paths"]
            maturities = f["maturities"]
            initial_yields = f["initial_yields"]
            seed = int(f["seed"])
            n_scenarios = int(f["n_scenarios"])
            n_steps = int(f["n_steps"])
            n_maturities = int(f["n_maturities"])
            metadata_json = str(f["metadata_json"]) if "metadata_json" in f.files else "{}"

        meta_obj = _json.loads(metadata_json)
        return cls(
            n_scenarios=n_scenarios,
            n_steps=n_steps,
            n_maturities=n_maturities,
            paths=paths,
            maturities_months=maturities,
            initial_yields_pct=initial_yields,
            seed=seed,
            description=meta_obj.get("description", ""),
            metadata=meta_obj.get("metadata", {}),
        )

    # ===================== 派生统计 =====================

    def get_percentiles(self, percentiles: List[int] = None) -> Dict[str, np.ndarray]:
        """计算利率路径的百分位带

        Args:
            percentiles: 默认 [10, 50, 90]

        Returns:
            dict: {"p10": (n_steps, n_maturities), "p50": ..., "p90": ..., ...}
        """
        if percentiles is None:
            percentiles = [10, 50, 90]
        return {
            f"p{p}": np.percentile(self.paths, p, axis=0)
            for p in percentiles
        }

    def get_final_distribution(self) -> Dict[str, np.ndarray]:
        """终期（最后一步）利率分布

        Returns:
            dict: {
                "mean": (n_maturities,),
                "std":  (n_maturities,),
                "min":  (n_maturities,),
                "max":  (n_maturities,),
                "p10":  (n_maturities,),
                "p90":  (n_maturities,),
            }
        """
        final = self.paths[:, -1, :]  # (n_scenarios, n_maturities)
        return {
            "mean": final.mean(axis=0),
            "std": final.std(axis=0),
            "min": final.min(axis=0),
            "max": final.max(axis=0),
            "p10": np.percentile(final, 10, axis=0),
            "p90": np.percentile(final, 90, axis=0),
        }

    def get_volatility_per_maturity(self, step_index: int = -1) -> np.ndarray:
        """每个期限在指定步骤的波动率（标准差，n_maturities,）"""
        if step_index == -1:
            step_index = self.n_steps - 1
        return self.paths[:, step_index, :].std(axis=0)

    def to_summary_json(self) -> Dict[str, Any]:
        """生成摘要（写入 prcp_esg_run.output_json）"""
        percentiles = self.get_percentiles([10, 50, 90])
        final_dist = self.get_final_distribution()
        return {
            "n_scenarios": self.n_scenarios,
            "n_steps": self.n_steps,
            "n_maturities": self.n_maturities,
            "maturities_months": self.maturities_months.tolist(),
            "paths_shape": list(self.paths.shape),
            "p10": percentiles["p10"].tolist(),
            "p50": percentiles["p50"].tolist(),
            "p90": percentiles["p90"].tolist(),
            "final_distribution_mean": final_dist["mean"].tolist(),
            "final_distribution_std": final_dist["std"].tolist(),
            "final_distribution_min": final_dist["min"].tolist(),
            "final_distribution_max": final_dist["max"].tolist(),
            "vol_per_maturity": self.get_volatility_per_maturity().tolist(),
            "paths_min": float(self.paths.min()),
            "paths_max": float(self.paths.max()),
        }


__all__ = ["ScenarioSet"]