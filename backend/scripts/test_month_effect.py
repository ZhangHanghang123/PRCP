"""切换预测月份后，驾驶舱各区块数据是否变化 —— 全面对账"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"
PWD = open("/tmp/pwd.txt").read().strip()

d = urllib.parse.urlencode({"username": "admin", "password": PWD}).encode()
req = urllib.request.Request(BASE + "/auth/login", data=d,
    headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
tok = json.load(urllib.request.urlopen(req))["access_token"]


def snap(off):
    req = urllib.request.Request(
        BASE + f"/reverse-dashboard/snapshot?scheme_code=2026&date_offset={off}",
        headers={"Authorization": f"Bearer {tok}"})
    return json.load(urllib.request.urlopen(req))


OFFS = [1, 6, 12, 18, 24]
S = {o: snap(o) for o in OFFS}
base = S[1]


def sig(v):
    """把嵌套结构压成可比较的字符串"""
    return json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)


print("=" * 72)
print("区块级：切换预测月份（M1 → M24）后是否变化")
print("=" * 72)

CHECKS = [
    ("KPI 卡（资产/负债总额等）", lambda s: s["kpi"]),
    ("KPI 指标均值 metric_avg", lambda s: s["kpi"]["metric_avg"]),
    ("趋势图 5 指标 24 月", lambda s: s["trend"]),
    ("分布卡 · 基准日当前余额 by_balance", lambda s: s["category_distribution"]["by_balance"]),
    ("分布卡 · 当月预测余额 by_balance_forecast", lambda s: s["category_distribution"]["by_balance_forecast"]),
    ("分布卡 · 基准日标签 balance_date", lambda s: s["category_distribution"]["balance_date"]),
    ("分布卡 · 预测月标签 forecast_date", lambda s: s["category_distribution"]["forecast_date"]),
    ("节点柱状图 · base_balance（末级）", lambda s: sorted(
        [(n["node_code"], n["base_balance"]) for n in s["node_matrix"] if n.get("is_leaf")])),
    ("节点柱状图 · current_balance（末级）", lambda s: sorted(
        [(n["node_code"], n["current_balance"]) for n in s["node_matrix"] if n.get("is_leaf")])),
    ("Top 10 节点", lambda s: s["top_nodes"]),
    ("风险预警 risk_alerts", lambda s: s["risk_alerts"]),
    ("节点矩阵 metric_values（5 指标）", lambda s: [
        (n["node_code"], n["metric_values"]) for n in s["node_matrix"]]),
]

for name, fn in CHECKS:
    vals = [sig(fn(S[o])) for o in OFFS]
    changed = sum(1 for i in range(1, len(vals)) if vals[i] != vals[0])
    flag = "变" if changed else "不变"
    mark = "✅ 随月份变化" if changed else "⬜ 静态"
    print(f"  {mark}  {name:<42} ({changed}/{len(OFFS)-1} 个切换点有差异)")

print()
print("=" * 72)
print("具体数值：预测月口径的逐月变化")
print("=" * 72)
print(f"{'月份':<6}{'预测月日期':<14}{'基准日标签':<14}{'预测资产':>10}{'预测负债':>10}"
      f"{'预测权益':>10}{'预测合计':>12}{'基准日合计':>12}")
for o in OFFS:
    s = S[o]
    cd = s["category_distribution"]
    bf, bb = cd["by_balance_forecast"], cd["by_balance"]
    fs = (bf["ASSET"] + bf["LIABILITY"] + bf["EQUITY"]) / 1e12
    bs = (bb["ASSET"] + bb["LIABILITY"] + bb["EQUITY"]) / 1e12
    print(f"M{o:<5}{cd['forecast_date']:<14}{cd['balance_date']:<14}"
          f"{bf['ASSET']/1e12:>10.2f}{bf['LIABILITY']/1e12:>10.2f}{bf['EQUITY']/1e12:>10.2f}"
          f"{fs:>12.2f}{bs:>12.2f}")

print()
print("=" * 72)
print("节点级：末级节点余额在两种口径下的逐月差异")
print("=" * 72)
for o in OFFS:
    s = S[o]
    leaves = [n for n in s["node_matrix"] if n.get("is_leaf")]
    d_base = sum(1 for n in leaves if n["base_balance"] != base_leaves_base(n, base))
    print(f"  M{o:<3} 末级节点 {len(leaves)} 个　"
          f"base_balance 合计 {sum(n['base_balance'] for n in leaves)/1e12:>6.2f}万亿　"
          f"current_balance 合计 {sum(n['current_balance'] for n in leaves)/1e12:>6.2f}万亿")


def base_leaves_base(n, b):
    for m in b["node_matrix"]:
        if m["node_code"] == n["node_code"]:
            return m["base_balance"]
    return None


print()
print("=" * 72)
print("结论")
print("=" * 72)
print("  基准日当前余额口径：")
print("    · balance_date 恒为 2025-12-31（方案基准日，与预测月无关）")
print("    · by_balance / base_balance 恒定 → 分布卡 + 柱状图数值不变")
print("  当月预测余额口径：")
print("    · forecast_date 随预测月变化")
print("    · by_balance_forecast / current_balance 随预测月变化 → 分布卡 + 柱状图数值变化")