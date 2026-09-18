"""共享期限桶定义 — 17 列（v2 改造 2026-09-18）

新结构（17 列）：
  1年内按月    12 列：m1, m2, ..., m12
  关键期限     1 列：y1
  长端固定桶   4 列：y10, y15, y20, y30

变更点：
  - 去掉 1日 (d1) / 7日 (d7) 桶
  - 一年内由 m1/m3/m6 (3 桶) 拆为 m1~m12 (12 桶)
  - 删除未填充的死列 m13~m60（DB 同步升级，见 upgrade_term_buckets_v2.sql）
"""
from typing import List, Dict


def _build_buckets() -> List[Dict[str, str]]:
    """构建 17 个期限桶"""
    monthly_year1 = [
        {"key": f"m{n}", "name": f"{n}M", "col": f"M{n}"}
        for n in range(1, 13)
    ]
    long = [
        {"key": "y1",  "name": "1Y",   "col": "Y1"},
        {"key": "y10", "name": "10Y",  "col": "Y10"},
        {"key": "y15", "name": "15Y",  "col": "Y15"},
        {"key": "y20", "name": "20Y",  "col": "Y20"},
        {"key": "y30", "name": "30Y",  "col": "Y30"},
    ]
    return monthly_year1 + long


BUCKETS: List[Dict[str, str]] = _build_buckets()
KEYS: List[str] = [b["key"] for b in BUCKETS]
NAMES: Dict[str, str] = {b["key"]: b["name"] for b in BUCKETS}

# 数据库列名（按 BUCKETS 顺序）
ORIG_COLS: List[str] = [f"orig_{b['key']}" for b in BUCKETS]
REM_COLS: List[str] = [f"rem_{b['key']}" for b in BUCKETS]
ALL_BUCKET_COLS: List[str] = ORIG_COLS + REM_COLS


def orig_select_sql(prefix: str = "") -> str:
    """生成 SELECT 中 orig_* 列名片段（可带表别名前缀，如 'b.'）"""
    return ", ".join(f"{prefix}{c}" for c in ORIG_COLS)


def rem_select_sql(prefix: str = "") -> str:
    """生成 SELECT 中 rem_* 列名片段（可带表别名前缀）"""
    return ", ".join(f"{prefix}{c}" for c in REM_COLS)


def all_select_sql(prefix: str = "") -> str:
    """生成 SELECT 中 orig_* + rem_* 列名片段"""
    return orig_select_sql(prefix) + ", " + rem_select_sql(prefix)


# 1 年内按月 / 关键期限 / 长端桶（用于布局分组）
YEAR1_MONTHLY_KEYS = {f"m{n}" for n in range(1, 13)}
KEY_KEYS = {"y1"}
LONG_KEYS = {"y10", "y15", "y20", "y30"}