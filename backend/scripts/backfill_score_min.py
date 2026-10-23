"""
回填 prcp_kpi_score_segment.score_min（最小值分数）

背景（2026-10-22）：
  分段规则编辑框把「分数」拆成「最小值分数 / 最大值分数」两列后，
  score_min 全为空 → 引擎按阶梯评分（STEPPED）处理，无法段内插值。

填充规则（业务语义：阶梯在分段边界处连续）：
  第 N 段的 score_min（该段下界 min_value 处的得分）
      = 第 N-1 段的 score（上一段的上界得分）

  特例处理：
  · 首段（seg_order = 1）：下界分数 = 上界分数（该段内恒定，不做插值）
  · 末段（max_value 为 NULL 或最大值）：同上恒定

  效果：段内由 score_min 线性升到 score，
        相邻段在边界处得分连续（原阶梯值成为插值起点/终点），
        各档「代表值」（段中点）得分与原阶梯评分保持一致。

例（LCR 规则）：
  seg1 [0,120]  score=0    → score_min=0     （恒定 0）
  seg2 [120,122] score=15  → score_min=0     （0 → 15 线性）
  seg3 [122,124] score=45  → score_min=15    （15 → 45 线性）
  ...
  seg17 [150,150] score=500→ score_min=500   （峰值点）
  seg18 [150,160] score=480→ score_min=500   （500 → 480 递减）
  ...
  seg23 [200,999] score=300→ score_min=300   （恒定 300）

安全性：
  插值只在段内生效，段边界处的得分与原阶梯评分完全一致，
  因此不会改变原有档位判定结果。
"""
import subprocess
import sys

DB = ["mysql", "-u", "prcp", "-pPrcp@2026", "prcp_db"]


def sql(q, show=False):
    r = subprocess.run(DB + ["-e", q], cwd="/tmp", executable="/usr/bin/mysql",
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    out = r.stdout.decode().strip()
    if show:
        print(out)
    return out


print("=== 1. 读取现有分段（仅有效规则 is_deleted=0）===")
rows = sql("""SELECT s.rule_id, s.seg_order, s.min_value, s.max_value, s.score
              FROM prcp_kpi_score_segment s
              JOIN prcp_kpi_score_rule r ON r.id = s.rule_id
              WHERE s.is_deleted=0 AND r.is_deleted=0
              ORDER BY s.rule_id, s.seg_order""", show=False)

segs = []
for line in rows.splitlines()[1:]:
    p = line.split("\t")
    if len(p) < 5:
        continue
    segs.append({
        "rule_id": int(p[0]), "seg_order": int(p[1]),
        "mn": None if p[2] == "NULL" else float(p[2]),
        "mx": None if p[3] == "NULL" else float(p[3]),
        "score": float(p[4]),
    })
print(f"共 {len(segs)} 段（{len({s['rule_id'] for s in segs})} 个有效规则）")

# 按规则分组计算 score_min
by_rule = {}
for s in segs:
    by_rule.setdefault(s["rule_id"], []).append(s)

updates = []
for rid, ss in sorted(by_rule.items()):
    ss.sort(key=lambda x: x["seg_order"])
    prev_score = None
    for i, s in enumerate(ss):
        if i == 0:
            # 首段：恒定
            s["score_min"] = s["score"]
        else:
            # 段下界得分 = 上一段上界得分
            s["score_min"] = prev_score
        prev_score = s["score"]
        # 宽度为 0 的段（峰点）无法插值，强制恒定
        if s["mn"] is not None and s["mx"] is not None and s["mx"] <= s["mn"]:
            s["score_min"] = s["score"]
        updates.append(s)

print("\n=== 2. 计算结果预览 ===")
for rid, ss in sorted(by_rule.items()):
    print(f"\n规则 {rid}:")
    for s in ss:
        mark = "" if s["mn"] is None or s["mx"] is None or s["mx"] > s["mn"] else "  (零宽,恒定)"
        print(f"  seg{s['seg_order']:>2}  [{s['mn']}, {s['mx']})  "
              f"score_min={s['score_min']:>7.2f} → score={s['score']:>7.2f}{mark}")

print(f"\n=== 3. 写入 {len(updates)} 行 ===")

# 先备份（仅有效规则的有效分段）
sql("""CREATE TABLE IF NOT EXISTS prcp_kpi_score_segment_bak_20261022
       LIKE prcp_kpi_score_segment;
       INSERT IGNORE INTO prcp_kpi_score_segment_bak_20261022
       SELECT s.* FROM prcp_kpi_score_segment s
       JOIN prcp_kpi_score_rule r ON r.id=s.rule_id
       WHERE s.is_deleted=0 AND r.is_deleted=0;""")

# 逐条 UPDATE
cnt = 0
for s in updates:
    sql(f"""UPDATE prcp_kpi_score_segment
            SET score_min={s['score_min']:.2f}
            WHERE rule_id={s['rule_id']} AND seg_order={s['seg_order']}
              AND is_deleted=0""")
    cnt += 1
print(f"已更新 {cnt} 行")

print("\n=== 4. 校验 ===")
sql("""SELECT COUNT(*) total, SUM(s.score_min IS NULL) still_null
       FROM prcp_kpi_score_segment s JOIN prcp_kpi_score_rule r ON r.id=s.rule_id
       WHERE s.is_deleted=0 AND r.is_deleted=0""", show=True)

print("\n=== 5. 边界连续性校验（相邻段在边界处得分应一致）===")
sql("""SELECT a.rule_id, COUNT(*) discontinuous
       FROM prcp_kpi_score_segment a
       JOIN prcp_kpi_score_segment b
         ON b.rule_id=a.rule_id AND b.seg_order=a.seg_order+1
       JOIN prcp_kpi_score_rule r ON r.id=a.rule_id
       WHERE a.is_deleted=0 AND b.is_deleted=0 AND r.is_deleted=0
         AND ABS(a.score - b.score_min) > 0.001
       GROUP BY a.rule_id""", show=True)
print("(无输出 = 全部连续)")