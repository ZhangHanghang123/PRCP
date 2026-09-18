"""PRCP 函数指标执行器

ctx 字典模式：
- 脚本路径：相对 backend/ 根，如 ``scripts/render_nim.py``
- 函数签名：``def calc(ctx: dict) -> float``
- ctx 结构：
  {
    "scheme_id": 2,
    "data_date": "2026-08-31",
    "kpi": {"id": 10, "code": "KPI_NIM", "name": "净息差"},
    "rpt_items": {        # 当前报表所有叶子表项的最新指标值
      "001001001001": 1234.5,
      "001001001002": 56.7,
      ...
    },
    "kpi_values": {      # 同方案其他 KPI 当前值（按 kpi_code）
      "KPI_A": 1.0,
      "KPI_B": 2.0,
    },
    "ctx_extra": {...},  # 前端调用时传入的自定义参数（可选）
  }

安全策略：
- 脚本目录白名单：``backend/scripts/kpi_functions`` 与 ``backend/app/services/kpi_functions``
- 每次调用都用独立 importlib 模块实例，避免全局副作用污染
- 函数必须返回 float/int，失败抛 ValueError
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional


# ============== 配置 ==============

# backend/ 根目录（runner.py 同级上两级：app/services/ -> app/ -> backend/）
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

# 函数指标脚本白名单目录（必须在这两个目录下）
ALLOWED_DIRS = [
    BACKEND_ROOT / "scripts" / "kpi_functions",
    BACKEND_ROOT / "app" / "services" / "kpi_functions",
]

# 执行超时（秒）
EXEC_TIMEOUT = 10


class FunctionKpiError(Exception):
    pass


def _resolve_script_path(script_path: str) -> Path:
    """把用户填写的脚本路径解析成绝对路径，并校验目录白名单"""
    if not script_path:
        raise FunctionKpiError("未配置 script_path")
    # 去除前导 ./
    sp = script_path.strip().lstrip("./").replace("\\", "/")
    p = (BACKEND_ROOT / sp).resolve()
    # 必须落在白名单目录里
    for allowed in ALLOWED_DIRS:
        allowed.mkdir(parents=True, exist_ok=True)
        try:
            p.relative_to(allowed.resolve())
            return p
        except ValueError:
            continue
    raise FunctionKpiError(
        f"脚本路径 {script_path} 不在白名单目录内（仅允许 {ALLOWED_DIRS}）"
    )


def _load_module(script_abs: Path, mod_name: str):
    """动态加载脚本为 module，文件修改会自动 reload"""
    spec = importlib.util.spec_from_file_location(mod_name, script_abs)
    if spec is None or spec.loader is None:
        raise FunctionKpiError(f"无法加载脚本 {script_abs}")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        raise FunctionKpiError(f"脚本 {script_abs.name} 加载异常: {e}")
    return mod


def run_function_kpi(
    script_path: str,
    script_name: str = "calc",
    *,
    scheme_id: int,
    data_date: str,
    kpi_info: Dict[str, Any],
    rpt_items: Dict[str, float],
    kpi_values: Dict[str, float],
    ctx_extra: Optional[Dict[str, Any]] = None,
) -> float:
    """执行函数指标脚本，返回计算结果（float）。失败抛 FunctionKpiError"""
    script_abs = _resolve_script_path(script_path)
    if not script_abs.exists():
        raise FunctionKpiError(f"脚本文件不存在: {script_abs}")

    fn_name = (script_name or "calc").strip()
    # 用绝对路径 + mtime 做唯一 mod 标识，避免 reload 缓存冲突
    mod_key = f"_prcp_kpi_func_{int(script_abs.stat().st_mtime)}_{abs(hash(str(script_abs)))}"
    mod = _load_module(script_abs, mod_key)
    if not hasattr(mod, fn_name):
        raise FunctionKpiError(
            f"脚本 {script_abs.name} 中找不到函数 {fn_name}()，"
            f"请定义 def {fn_name}(ctx: dict) -> float"
        )
    fn = getattr(mod, fn_name)
    if not callable(fn):
        raise FunctionKpiError(f"{fn_name} 不是可调用对象")

    ctx = {
        "scheme_id": scheme_id,
        "data_date": data_date,
        "kpi": kpi_info,
        "rpt_items": dict(rpt_items or {}),
        "kpi_values": dict(kpi_values or {}),
        "ctx_extra": dict(ctx_extra or {}),
    }
    t0 = time.time()
    try:
        result = fn(ctx)
    except Exception as e:
        tb = traceback.format_exc(limit=5)
        raise FunctionKpiError(
            f"函数 {fn_name}() 抛出异常: {e}\n{tb}"
        )
    elapsed = (time.time() - t0) * 1000
    if elapsed > EXEC_TIMEOUT * 1000:
        raise FunctionKpiError(
            f"函数 {fn_name}() 执行超时 ({elapsed:.0f}ms > {EXEC_TIMEOUT}s)"
        )
    try:
        return float(result)
    except (TypeError, ValueError):
        raise FunctionKpiError(
            f"函数 {fn_name}() 必须返回数字（float/int），实际返回 {type(result).__name__}={result!r}"
        )


def list_available_scripts() -> list[dict]:
    """扫描白名单目录，列出可用的脚本文件，供前端【脚本下拉】使用"""
    out_list = []
    for allowed in ALLOWED_DIRS:
        allowed.mkdir(parents=True, exist_ok=True)
        for p in sorted(allowed.rglob("*.py")):
            if p.name.startswith("_"):
                continue
            try:
                rel = p.relative_to(BACKEND_ROOT)
                out_list.append({
                    "path": str(rel).replace("\\", "/"),
                    "name": p.stem,
                    "size": p.stat().st_size,
                })
            except ValueError:
                continue
    return out_list