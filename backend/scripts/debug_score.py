"""本地复现 score-calc 500：直接查库 + 跑插值逻辑"""
import subprocess

DB = ["mysql", "-u", "prcp", "-pPrcp@2026", "prcp_db"]


def sql(q):
    r = subprocess.run(DB + ["-N", "-B", "-e", q], cwd="/tmp",
                       executable="/usr/bin/mysql",
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return r.stdout.decode().strip()


print("=== 规则 51 的 segs（模拟 score_calc 的查询）===")
rows = sql("""SELECT id, min_value, max_value, score, score_min, segment_desc, seg_order
              FROM prcp_kpi_score_segment
              WHERE rule_id=51 AND is_deleted=0 ORDER BY seg_order""")
segs = []
for line in rows.splitlines():
    p = line.split("\t")
    segs.append(p)
    if len(segs) <= 5:
        print(f"  {p}")

print(f"\n共 {len(segs)} 段，列数检查: {[len(s) for s in segs[:3]]}")

print("\n=== 模拟 PIECEWISE 匹配 + 插值 ===")


def to_f(v):
    return None if v == "NULL" else float(v)


for val in [0, 60, 110, 121, 123, 150, 160, 200, 300]:
    matched = None
    for s in segs:
        sid, mn, mx, sc, sc_min, desc, so = s
        mn, mx, sc, sc_min = to_f(mn), to_f(mx), float(sc), to_f(sc_min)
        ok = True
        if mn is not None and val < mn:
            ok = False
        if mx is not None and val > mx:
            ok = False
        if ok:
            mode = "STEPPED"
            final = sc
            if sc_min is not None and mn is not None and mx is not None and mx > mn:
                ratio = (val - mn) / (mx - mn)
                final = round(sc_min + ratio * (sc - sc_min), 2)
                mode = "INTERPOLATED"
            matched = (final, mode, desc)
            break
    if matched:
        print(f"  值 {val:>5} → {matched[0]:>7} | {matched[1]:<13} | {matched[2]}")
    else:
        print(f"  值 {val:>5} → 未匹配")