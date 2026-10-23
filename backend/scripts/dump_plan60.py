"""dump M1 行完整 60 格排期（run#20）用于文档核对"""
import subprocess

COLS = [f"rem_m{i}" for i in range(1, 61)] + ["rem_y10"]
parts = []
for c in COLS:
    parts.append(
        f"SELECT '{c}' AS col, ROUND({c}/1e8,4) AS v "
        f"FROM prcp_sim_result WHERE run_id=20 AND node_code='S010101010000' AND date_offset=1"
    )
sql = " UNION ALL ".join(parts) + " ORDER BY FIELD(col," + \
      ",".join(f"'{c}'" for c in COLS) + ")"

out = subprocess.run(
    ["mysql", "-N", "-B", "-u", "prcp", "-pPrcp@2026", "prcp_db", "-e", sql],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd="/tmp",
    executable="/usr/bin/mysql",
).stdout.decode().strip()

rows = [r.split("\t") for r in out.splitlines() if r]
print(f"共 {len(rows)} 格\n")
for i in range(0, len(rows), 5):
    chunk = rows[i:i + 5]
    print("  ".join(f"{c:9s}={v:>10s}" for c, v in chunk))

# Markdown 表格（4 列一组）
print("\n\n| 到期月 | 金额（亿） | 到期月 | 金额（亿） | 到期月 | 金额（亿） |")
print("|---|---|---|---|---|---|")
n = len(rows)
for i in range(0, n, 3):
    cells = []
    for j in range(3):
        if i + j < n:
            c, v = rows[i + j]
            cells += [c, v]
        else:
            cells += ["", ""]
    print(f"| {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} | {cells[5]} |")