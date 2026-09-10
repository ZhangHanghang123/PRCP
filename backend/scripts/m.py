"""迁移 prcp_metric_item 193 条数据 → prcp_rpt_item + 创建 6 个默认报表"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.database import engine

# 1. 给 prcp_rpt_item 加 category 字段（账务/参数/规模/价格/中收/RWA）
with engine.begin() as conn:
    try:
        conn.execute(text("""
            ALTER TABLE prcp_rpt_item
            ADD COLUMN category VARCHAR(32) DEFAULT NULL AFTER report_id,
            ADD INDEX idx_category (category)
        """))
        print("✅ prcp_rpt_item 加 category 字段")
    except Exception as e:
        print(f"⚠️  category 字段已存在或加失败: {e}")

# 2. category 映射：xlsx sheet name → prcp_metric_item.category enum
CATEGORY_MAP = {
    'FINANCIAL': '账务结果',
    'PARAM': '关键参数',
    'SCALE': '规模',
    'PRICE': '价格',
    'FEE': '中收',
    'RWA': '资本与RWA',
}
REPORT_CODE_PREFIX = {
    'FINANCIAL': 'RPT_FIN',
    'PARAM': 'RPT_PARAM',
    'SCALE': 'RPT_SCALE',
    'PRICE': 'RPT_PRICE',
    'FEE': 'RPT_FEE',
    'RWA': 'RPT_RWA',
}
REPORT_NAME = {
    'FINANCIAL': '账务结果报表',
    'PARAM': '关键参数报表',
    'SCALE': '规模报表',
    'PRICE': '价格报表',
    'FEE': '中收报表',
    'RWA': '资本与RWA报表',
}

with engine.begin() as conn:
    # 3. 创建 6 个默认报表（每个 category 一个），记录 ID
    report_ids = {}
    for cat, code in REPORT_CODE_PREFIX.items():
        rcode = code
        rname = REPORT_NAME[cat]
        # 查现有
        row = conn.execute(text("SELECT id FROM prcp_rpt_report WHERE report_code=:c AND is_deleted=0"), {"c": rcode}).first()
        if row:
            report_ids[cat] = row[0]
            print(f"  报表 {rcode} 已存在 id={row[0]}")
        else:
            rid = conn.execute(
                text("""INSERT INTO prcp_rpt_report
                    (report_code, report_name, report_type, scheme_id, description, status, created_by, updated_by)
                    VALUES (:c, :n, 'INDICATOR', 1, :d, 'ACTIVE', 1, 1)"""),
                {"c": rcode, "n": rname, "d": CATEGORY_MAP[cat] + "（来自指标项 xlsx）"},
            ).lastrowid
            report_ids[cat] = rid
            print(f"  ✅ 创建报表 {rcode} id={rid}")

    # 4. 迁移数据
    # 把 prcp_metric_item 的 (cat, code, name, level, parent_code, path) → prcp_rpt_item (report_id, item_code, item_name, item_level, path, category)
    # 注意：同一 category 下 parent_code 来自同一表，parent_id 需二次更新
    rows = conn.execute(text("""
        SELECT id, category, code, name, level, parent_code, path, is_leaf, sort_order
        FROM prcp_metric_item
        WHERE is_deleted=0
        ORDER BY category, path
    """)).fetchall()

    # 按 category 分组
    by_cat: dict = {}
    for r in rows:
        by_cat.setdefault(r[1], []).append(r)

    migrated = 0
    for cat, items in by_cat.items():
        rid = report_ids[cat]
        # 先清空此报表下已有表项（避免重复）
        conn.execute(text("UPDATE prcp_rpt_item SET is_deleted=1 WHERE report_id=:r AND category=:c"),
                      {"r": rid, "c": cat})
        # 建立 (cat, code, name) → new_id 映射（用于设置 parent_id）
        new_ids = {}
        for it in items:
            old_id, _, code, name, level, parent_code, old_path, is_leaf, sort_order = it
            # 新 path 加上 category 前缀避免与原报表其他表项冲突
            # 这里直接用原 path（每个报表独立）
            new_path = old_path if old_path else f"/{code}/"
            new_id = conn.execute(text("""INSERT INTO prcp_rpt_item
                (report_id, item_code, item_name, parent_id, item_level, data_type,
                 coa_node_ids, path, sort_order, status, category, created_by, updated_by)
                VALUES (:r, :c, :n, NULL, :l, 'DECIMAL', '[]', :path, :so, 'ACTIVE', :cat, 1, 1)"""),
                {"r": rid, "c": code, "n": name, "l": level, "path": new_path,
                 "so": sort_order, "cat": cat},
            ).lastrowid
            new_ids[(cat, code, name)] = new_id
            migrated += 1

        # 第二遍：设置 parent_id
        for it in items:
            old_id, _, code, name, level, parent_code, _, _, _ = it
            if parent_code and (cat, parent_code) in [(c, pc) for c, pc, _ in [(k[0], k[1], k[2]) for k in new_ids.keys()]]:
                # 找同名（取第一个 name 为空的 parent）
                parent_new_id = None
                for (pc, pn), nid in [((k[1], k[2]), v) for k, v in new_ids.items()]:
                    if pc == parent_code:
                        parent_new_id = nid
                        break
                if parent_new_id:
                    conn.execute(text("UPDATE prcp_rpt_item SET parent_id=:p WHERE id=:i"),
                                  {"p": parent_new_id, "i": new_ids[(cat, code, name)]})

    print(f"\n✅ 迁移完成：{migrated} 条 → prcp_rpt_item")

    # 5. 验证
    cnt = conn.execute(text("SELECT category, COUNT(*) FROM prcp_rpt_item WHERE is_deleted=0 GROUP BY category")).fetchall()
    print("\n按 category 统计：")
    for r in cnt:
        print(f"  {r[0]}: {r[1]} 条")
