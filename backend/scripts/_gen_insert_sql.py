"""根据 Excel 生成 INSERT SQL 文件（推送服务器用）"""
import openpyxl
from pathlib import Path

EXCEL = Path(r"C:\银行经营\PRCP\docs\中信银行账户册结构.xlsx")
OUTPUT = Path(r"C:\银行经营\PRCP\backend\scripts\zx_citic_2026_insert.sql")

wb = openpyxl.load_workbook(EXCEL, data_only=True)
ws = wb["中信银行账户册"]

rows = []
for row in ws.iter_rows(min_row=3, values_only=True):
    if not row or not row[0]:
        continue
    code, name, level, parent_code, parent_name, is_leaf = row[:6]
    if not isinstance(code, str) or not code.startswith("S"):
        continue
    rows.append(dict(
        node_code=code.strip(),
        node_name=name.strip().replace("'", "''"),
        node_level=int(level),
        parent_code=parent_code.strip() if isinstance(parent_code, str) and parent_code else None,
        is_leaf=str(is_leaf).strip(),
    ))


def categorize(code, is_leaf):
    if code.startswith("S01"):
        prefix = "ASSET"
    elif code.startswith("S02"):
        prefix = "LIAB"
    elif code.startswith("S03"):
        prefix = "EQUITY"
    else:
        prefix = "OTHER"
    leaf = "LEAF" if is_leaf == "是" else "GROUP"
    return f"{prefix}_{leaf}"


rows.sort(key=lambda r: (r["node_level"], r["node_code"]))

lines = []
lines.append("-- PRCP 中信银行账户册 ZX_CITIC_2026 数据同步脚本（服务器端）")
lines.append("-- 由 backend/scripts/gen_citic_coa_scheme.py 同源生成")
lines.append("-- 用法：mysql -uprcp -pPrcp@2026 prcp_db < zx_citic_2026_insert.sql")
lines.append("")
lines.append("SET NAMES utf8mb4;")
lines.append("SET @scheme_id := NULL;")
lines.append("")
lines.append("-- 0) 幂等检查：若方案已存在则中止")
lines.append("SELECT id INTO @existing_id FROM prcp_coa_scheme WHERE scheme_code='ZX_CITIC_2026' AND is_deleted=0 LIMIT 1;")
lines.append("SELECT IF(@existing_id IS NOT NULL, CONCAT('ABORT:id=', @existing_id), 'CONTINUE') AS __step0;")
lines.append("")
lines.append("-- 1) 创建方案")
lines.append("INSERT INTO prcp_coa_scheme (scheme_code, scheme_name, description, status, node_count, created_by, updated_by)")
lines.append("VALUES ('ZX_CITIC_2026', '中信银行账户册 2026',")
lines.append("        '依据中信银行账户册结构整理：资产/负债/权益三大类，5 级层级，38 个节点。',")
lines.append("        'ACTIVE', 0, 1, 1);")
lines.append("")
lines.append("SET @scheme_id := LAST_INSERT_ID();")
lines.append("SELECT @scheme_id AS scheme_id;")
lines.append("")
lines.append("-- 2) 节点表（创建临时 code→id 映射表用于回填 parent_id）")
lines.append("DROP TEMPORARY TABLE IF EXISTS _tmp_node_id_map;")
lines.append("CREATE TEMPORARY TABLE _tmp_node_id_map (")
lines.append("  code VARCHAR(32) PRIMARY KEY,")
lines.append("  id BIGINT NOT NULL")
lines.append(") ENGINE=MEMORY;")
lines.append("")
lines.append("-- Level 1 节点（parent 顶级）")
for r in rows:
    if r["node_level"] != 1:
        continue
    code = r["node_code"]
    name = r["node_name"]
    node_type = categorize(code, r["is_leaf"])
    path = f"/{code}/"
    lines.append(f"INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)")
    lines.append(f"VALUES (@scheme_id, '{code}', '{name}', NULL, 1, '{node_type}', '{path}', 0, 'ACTIVE', NULL, 1, 1);")
    lines.append(f"INSERT INTO _tmp_node_id_map (code, id) VALUES ('{code}', LAST_INSERT_ID());")
    lines.append("")
lines.append("")

# 2~5 级，逐级回填
for target_level in range(2, 6):
    level_rows = [r for r in rows if r["node_level"] == target_level]
    if not level_rows:
        continue
    lines.append(f"-- Level {target_level} 节点")
    for r in level_rows:
        code = r["node_code"]
        name = r["node_name"]
        parent_code = r["parent_code"]
        node_type = categorize(code, r["is_leaf"])
        lines.append(f"SELECT m.id, n.path INTO @pid, @ppath FROM _tmp_node_id_map m")
        lines.append(f"  JOIN prcp_coa_node n ON n.id = m.id")
        lines.append(f"  WHERE m.code='{parent_code}' LIMIT 1;")
        lines.append(f"SET @path := CONCAT(@ppath, '{code}', '/');")
        lines.append(f"INSERT INTO prcp_coa_node (scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order, status, description, created_by, updated_by)")
        lines.append(f"VALUES (@scheme_id, '{code}', '{name}', @pid, {target_level}, '{node_type}', @path, 0, 'ACTIVE', NULL, 1, 1);")
        lines.append(f"INSERT INTO _tmp_node_id_map (code, id) VALUES ('{code}', LAST_INSERT_ID());")
        lines.append("")
    lines.append("")

lines.append("-- 3) 回填方案 node_count")
lines.append("UPDATE prcp_coa_scheme")
lines.append("SET node_count = (SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id=@scheme_id AND is_deleted=0)")
lines.append("WHERE id=@scheme_id;")
lines.append("")
lines.append("-- 4) 验证")
lines.append("SELECT id, scheme_code, scheme_name, node_count, status FROM prcp_coa_scheme WHERE id=@scheme_id;")
lines.append("SELECT node_level, COUNT(*) AS cnt FROM prcp_coa_node WHERE scheme_id=@scheme_id AND is_deleted=0 GROUP BY node_level ORDER BY node_level;")
lines.append("SELECT node_type, COUNT(*) AS cnt FROM prcp_coa_node WHERE scheme_id=@scheme_id AND is_deleted=0 GROUP BY node_type ORDER BY node_type;")
lines.append("")
lines.append("-- 5) 清理临时表")
lines.append("DROP TEMPORARY TABLE IF EXISTS _tmp_node_id_map;")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8")
print(f"生成 SQL 文件：{OUTPUT}")
print(f"文件大小：{OUTPUT.stat().st_size} 字节")
print(f"节点数：{len(rows)}")