"""共享期限桶定义 — 64 列（v3 改造 2026-09-18）

新结构（64 列）：
  5年内按月      60 列：m1, m2, ..., m60
  长端固定桶      4 列：y10, y15, y20, y30

变更点：
  - 5 年内全部按月拆分（m1~m60）
  - 删除 y1（因 m12 = 12 月 = 1Y）
  - 长端固定 y10/y15/y20/y30 不变
  - DB 同步升级，见 upgrade_term_buckets_v3.sql
"""
from typing import List, Dict


def _build_buckets() -> List[Dict[str, str]]:
    """构建 64 个期限桶"""
    monthly_5y = [
        {"key": f"m{n}", "name": f"{n}M", "col": f"M{n}"}
        for n in range(1, 61)
    ]
    long = [
        {"key": "y10", "name": "10Y",  "col": "Y10"},
        {"key": "y15", "name": "15Y",  "col": "Y15"},
        {"key": "y20", "name": "20Y",  "col": "Y20"},
        {"key": "y30", "name": "30Y",  "col": "Y30"},
    ]
    return monthly_5y + long


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


# 桶分组（用于布局/分组聚合）
YEAR1_KEYS = {f"m{n}" for n in range(1, 13)}    # 1-12月
YEAR2_KEYS = {f"m{n}" for n in range(13, 25)}   # 13-24月
YEAR3_KEYS = {f"m{n}" for n in range(25, 37)}   # 25-36月
YEAR4_KEYS = {f"m{n}" for n in range(37, 49)}   # 37-48月
YEAR5_KEYS = {f"m{n}" for n in range(49, 61)}   # 49-60月
LONG_KEYS = {"y10", "y15", "y20", "y30"}