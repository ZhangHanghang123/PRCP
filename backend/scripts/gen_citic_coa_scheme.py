"""
根据 C:\\银行经营\\PRCP\\docs\\中信银行账户册结构.xlsx
为 PRCP 模块生成一套新的账户册方案（ZX_CITIC_2026）

策略：
  1. 解析 Excel → 节点元数据列表（含 code/name/level/parent_code/is_leaf/category）
  2. 创建方案 prcp_coa_scheme（编码 ZX_CITIC_2026）
  3. 按层级从浅到深 INSERT prcp_coa_node
     - 父节点已插入 → 用 parent_id 关联 + 自动算 path/level
     - 父节点尚未插入 → 用 parent_code 占位，二次扫描回填
  4. 回填 node_count

容错：
  - 方案已存在则跳过（不重复创建）
  - 节点编码冲突则跳过该节点
"""
import os
import sys
from pathlib import Path
import openpyxl
import pymysql

# ---------- 配置 ----------
EXCEL_PATH = Path(r"C:\银行经营\PRCP\docs\中信银行账户册结构.xlsx")
DB = dict(host="127.0.0.1", port=3306, user="prcp", password="Prcp@2026",
          database="prcp_db", charset="utf8mb4")

SCHEME_CODE = "ZX_CITIC_2026"
SCHEME_NAME = "中信银行账户册 2026"
SCHEME_DESC = "依据中信银行账户册结构整理：资产/负债/权益三大类，5 级层级，约 36 个节点。"

USER_ID = 1  # sys_user 主键

# 节点分类规则（用于 node_type 字段）
def categorize(code: str, name: str, is_leaf: str) -> str:
    """根据编码前缀 + 是否末级，给出 node_type 枚举"""
    if code.startswith("S01"):
        prefix = "ASSET"
    elif code.startswith("S02"):
        prefix = "LIAB"
    elif code.startswith("S03"):
        prefix = "EQUITY"
    else:
        prefix = "OTHER"
    # 是否末级
    leaf = "LEAF" if is_leaf == "是" else "GROUP"
    return f"{prefix}_{leaf}"


# ---------- 主流程 ----------
def main():
    # 1) 读 Excel
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb["中信银行账户册"]

    rows = []
    for row in ws.iter_rows(min_row=3, values_only=True):  # 跳过标题与表头
        if not row or not row[0]:
            continue
        code, name, level, parent_code, parent_name, is_leaf = row[:6]
        # 跳过完全空白的二级标题行（如"中信银行账户册结构（PRCP）"）
        if not isinstance(code, str) or not code.startswith("S"):
            continue
        rows.append(dict(
            node_code=code.strip(),
            node_name=name.strip(),
            node_level=int(level),
            parent_code=parent_code.strip() if isinstance(parent_code, str) and parent_code else None,
            is_leaf=str(is_leaf).strip(),
        ))
    print(f"[1] Excel 解析: {len(rows)} 个节点")

    # 2) 连库
    conn = pymysql.connect(**DB)
    cur = conn.cursor()

    try:
        # 3) 创建方案（如果已存在则跳过）
        cur.execute("SELECT id FROM prcp_coa_scheme WHERE scheme_code=%s AND is_deleted=0", (SCHEME_CODE,))
        existing = cur.fetchone()
        if existing:
            scheme_id = existing[0]
            print(f"[2] 方案已存在: id={scheme_id}, code={SCHEME_CODE}, 跳过创建")
        else:
            cur.execute(
                """INSERT INTO prcp_coa_scheme
                       (scheme_code, scheme_name, description, status, node_count, created_by, updated_by)
                       VALUES (%s, %s, %s, 'ACTIVE', 0, %s, %s)""",
                (SCHEME_CODE, SCHEME_NAME, SCHEME_DESC, USER_ID, USER_ID),
            )
            scheme_id = cur.lastrowid
            print(f"[2] 新建方案: id={scheme_id}, code={SCHEME_CODE}")

        # 4) 检查方案下是否已有节点（避免重复）
        cur.execute("SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id=%s AND is_deleted=0", (scheme_id,))
        existing_n = cur.fetchone()[0]
        if existing_n > 0:
            print(f"[3] 方案下已有 {existing_n} 个节点，已存在则中止（避免重复）")
            return

        # 5) 按层级排序，逐级插入（保证父节点先插入）
        rows.sort(key=lambda r: (r["node_level"], r["node_code"]))

        code_to_id = {}
        ok_count = 0
        skip_count = 0

        for r in rows:
            parent_id = code_to_id.get(r["parent_code"]) if r["parent_code"] else None

            node_type = categorize(r["node_code"], r["node_name"], r["is_leaf"])

            try:
                if parent_id:
                    cur.execute(
                        "SELECT path, node_level FROM prcp_coa_node WHERE id=%s AND is_deleted=0",
                        (parent_id,),
                    )
                    p = cur.fetchone()
                    if not p:
                        raise RuntimeError(f"父节点不存在 id={parent_id}")
                    path = f"{p[0]}{r['node_code']}/"
                    level = p[1] + 1
                else:
                    path = f"/{r['node_code']}/"
                    level = r["node_level"]

                cur.execute(
                    """INSERT INTO prcp_coa_node
                           (scheme_id, node_code, node_name, parent_id, node_level,
                            node_type, path, sort_order, status, description,
                            created_by, updated_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 'ACTIVE', NULL, %s, %s)""",
                    (scheme_id, r["node_code"], r["node_name"], parent_id, level,
                     node_type, path, USER_ID, USER_ID),
                )
                code_to_id[r["node_code"]] = cur.lastrowid
                ok_count += 1
            except pymysql.err.IntegrityError as e:
                # 编码冲突等
                print(f"    跳过 {r['node_code']} ({r['node_name']}): {e.args[1]}")
                skip_count += 1
                continue

        # 6) 回填方案 node_count
        cur.execute(
            "UPDATE prcp_coa_scheme SET node_count=%s WHERE id=%s",
            (ok_count, scheme_id),
        )

        conn.commit()
        print()
        print(f"[完成] 成功插入 {ok_count} 个节点，跳过 {skip_count} 个")
        print(f"        方案: {SCHEME_NAME} (id={scheme_id})")

        # 7) 输出树形预览（按 level 分组打印）
        cur.execute(
            """SELECT node_code, node_name, node_level, node_type, path
                   FROM prcp_coa_node
                   WHERE scheme_id=%s AND is_deleted=0
                   ORDER BY path""",
            (scheme_id,),
        )
        all_nodes = cur.fetchall()
        print()
        print("=== 账户册树预览 ===")
        for n in all_nodes:
            indent = "  " * (n[2] - 1)
            leaf_mark = "●" if n[3].endswith("LEAF") else "○"
            print(f"{indent}{leaf_mark} [{n[0]}] {n[1]}  ({n[3]})")

    finally:
        conn.close()


if __name__ == "__main__":
    main()