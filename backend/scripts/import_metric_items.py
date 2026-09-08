"""解析 docs/报表表项.xlsx，生成 prcp_metric_item 的 SQL 文件
- 6 个 sheet 各对应一类指标（账务/参数/规模/价格/中收/RWA）
- 每行 (code, name, level, parent_code) 构成树形
- 计算物化路径 path（同类下唯一）
- 重复 (cat, code) 视为同节点，保留首次出现
"""
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

# 路径：脚本在 backend/scripts/，xlsx 在 docs/
ROOT = Path(__file__).resolve().parent.parent.parent
XLSX = ROOT / "docs" / "报表表项.xlsx"
OUT_SQL = ROOT / "docs" / "metric_items_seed.sql"

# sheet 名 → category 编码
SHEET2CAT = {
    "1-账务结果指标": "FINANCIAL",
    "2-关键参数指标": "PARAM",
    "3-规模指标": "SCALE",
    "4-价格指标": "PRICE",
    "5-中收指标": "FEE",
    "6-资本与RWA假设指标": "RWA",
}


def parse_xlsx():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    rows = []
    for sn in wb.sheetnames:
        cat = SHEET2CAT.get(sn)
        if not cat:
            print(f"  [warn] 未知 sheet: {sn}（跳过）")
            continue
        ws = wb[sn]
        # 表头：编码 | 名称 | 层级 | 父编码
        for i, row in enumerate(ws.iter_rows(values_only=True), 1):
            if i == 1:
                continue  # 跳过表头
            if not row or all(v is None for v in row):
                continue
            code = (row[0] or "").strip() if row[0] else ""
            name = (row[1] or "").strip() if row[1] else ""
            level = row[2] or 1
            parent = (row[3] or "").strip() if row[3] else ""
            if not code or not name:
                continue
            # 根节点（parent 为空，level=1）也保留
            try:
                level = int(level)
            except (ValueError, TypeError):
                level = 1
            rows.append({
                "category": cat,
                "code": code,
                "name": name,
                "level": level,
                "parent_code": parent,
            })
        print(f"  ✅ {sn} → {cat}: 解析 {sum(1 for r in rows if r['category']==cat)} 条")
    print(f"  📊 总计: {len(rows)} 条")
    return rows


def dedup(rows):
    """去重：(category, code, name) 三元组视为唯一业务节点
    注：xlsx 中 sheet 6 的 (一)段和 (二)段都用了 001001 编码，但 name 不同，
    应作为两个独立指标项保留。
    """
    seen = set()
    unique = []
    for r in rows:
        key = (r["category"], r["code"], r["name"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    print(f"  🔁 去重后: {len(unique)} 条（原始 {len(rows)}，重复 {len(rows)-len(unique)}）")
    return unique


def build_path(rows):
    """对每行计算物化路径 path = /<cat>/<parent_code>/<code>/
    xlsx 中存在 (cat, code) 重复项（如 sheet 6 的 001001 出现两次），
    物化路径用 (cat, code, name) 区分，保证每个独立节点 path 唯一。
    """
    idx = {}  # (cat, code, name) -> path
    for r in rows:
        cat = r["category"]
        key = (cat, r["code"], r["name"])
        if r["level"] == 1 or not r["parent_code"]:
            p = f"/{cat}/{r['code']}/"
        else:
            # 找父节点的 path——同 cat 下 name 不一定唯一，但同 (cat, parent_code, name) 唯一
            parent_path = None
            for rr in rows:
                if (rr["category"] == cat
                    and rr["code"] == r["parent_code"]
                    and rr["level"] == r["level"] - 1):
                    parent_path = idx.get((cat, rr["code"], rr["name"]))
                    if parent_path:
                        break
            if parent_path is None:
                # 兜底：拼成 /cat/parent_code/code/
                p = f"/{cat}/{r['parent_code']}/{r['code']}/"
            else:
                p = f"{parent_path}{r['code']}/"
        r["path"] = p
        idx[key] = p
    return rows


def gen_sql(rows):
    """生成 SQL（清空 + 批量插入）"""
    lines = [
        "-- prcp_metric_item 种子数据（6 类指标项，~191 条）",
        "-- 来源：C:\\银行经营\\PRCP\\docs\\报表表项.xlsx",
        "-- 由 backend/scripts/import_metric_items.py 自动生成",
        "",
        "DELETE FROM prcp_metric_item WHERE 1=1;",
        "",
    ]
    for r in rows:
        is_leaf = 1 if r["level"] >= 4 else 0  # 4-5 级视为叶子（最深层）
        # 简化：把 >=4 的视为叶子，4 级以下视为分支
        name = r["name"].replace("'", "''")
        path = r["path"].replace("'", "''")
        lines.append(
            f"INSERT INTO prcp_metric_item "
            f"(category, code, name, level, parent_code, path, is_leaf, sort_order, created_by, updated_by) "
            f"VALUES ("
            f"'{r['category']}', '{r['code']}', '{name}', {r['level']}, "
            f"'{r['parent_code'] or ''}', '{path}', {is_leaf}, 0, 1, 1);"
        )
    OUT_SQL.write_text("\n".join(lines), encoding="utf-8")
    print(f"  📝 SQL 已生成: {OUT_SQL} ({len(lines)} 行, {OUT_SQL.stat().st_size} bytes)")


def main():
    print(f"📖 读取 {XLSX.name}")
    rows = parse_xlsx()
    rows = dedup(rows)
    rows = build_path(rows)
    gen_sql(rows)
    print("✅ 完成")


if __name__ == "__main__":
    main()
