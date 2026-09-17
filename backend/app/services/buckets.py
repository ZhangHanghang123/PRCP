"""共享期限桶定义 — 5 年内按月拆分，5 年后保持
新结构（58 列）：
  短端固定桶 5 列：d1, d7, m1, m3, m6
  关键期限   1 列：y1
  中端按月   48 列：m13, m14, ..., m60（13 月到 60 月）
  长端固定桶 4 列：y10, y15, y20, y30
"""
from typing import List, Dict


def _build_buckets() -> List[Dict[str, str]]:
    """构建 58 个期限桶"""
    short = [
        {"key": "d1",  "name": "1日",  "col": "D1"},
        {"key": "d7",  "name": "7日",  "col": "D7"},
        {"key": "m1",  "name": "1M",   "col": "M1"},
        {"key": "m3",  "name": "3M",   "col": "M3"},
        {"key": "m6",  "name": "6M",   "col": "M6"},
    ]
    monthly_buckets = [
        {"key": f"m{n}", "name": f"{n}M", "col": f"M{n}"}
        for n in range(13, 61)
    ]
    long = [
        {"key": "y1",  "name": "1Y",   "col": "Y1"},
        {"key": "y10", "name": "10Y",  "col": "Y10"},
        {"key": "y15", "name": "15Y",  "col": "Y15"},
        {"key": "y20", "name": "20Y",  "col": "Y20"},
        {"key": "y30", "name": "30Y",  "col": "Y30"},
    ]
    return short + monthly_buckets + long


BUCKETS: List[Dict[str, str]] = _build_buckets()
KEYS: List[str] = [b["key"] for b in BUCKETS]
NAMES: Dict[str, str] = {b["key"]: b["name"] for b in BUCKETS}

# 数据库列名（按 BUCKETS 顺序）
ORIG_COLS: List[str] = [f"orig_{b['key']}" for b in BUCKETS]
REM_COLS: List[str] = [f"rem_{b['key']}" for b in BUCKETS]
ALL_BUCKET_COLS: List[str] = ORIG_COLS + REM_COLS


def orig_select_sql() -> str:
    """生成 SELECT 中 orig_* 列名片段"""
    return ", ".join(ORIG_COLS)


def rem_select_sql() -> str:
    """生成 SELECT 中 rem_* 列名片段"""
    return ", ".join(REM_COLS)


def all_select_sql() -> str:
    """生成 SELECT 中 orig_* + rem_* 列名片段"""
    return orig_select_sql() + ", " + rem_select_sql()


# 短端 / 长端桶索引（用于布局分组）
SHORT_KEYS = {"d1", "d7", "m1", "m3", "m6"}
KEY_KEYS = {"y1"}
MONTHLY_KEYS = {f"m{n}" for n in range(13, 61)}
LONG_KEYS = {"y10", "y15", "y20", "y30"}