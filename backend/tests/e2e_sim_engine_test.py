"""引擎计量端到端测试（服务器端）"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8006/prcp/api"

def req(method, path, data=None, token=None):
    url = BASE + path
    headers = {}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


# 1. 登录
print("=== 1. 登录 ===")
body = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
r = urllib.request.Request(BASE + "/auth/login", data=body, method="POST")
with urllib.request.urlopen(r) as resp:
    token = json.loads(resp.read())["access_token"]
print(f"  token len={len(token)}")

# 2. 方案列表
print("\n=== 2. 方案列表 ===")
code, d = req("GET", "/sim/schemes", token=token)
for s in d['items']:
    print(f"  id={s['id']} code={s['scheme_code']} coa_scheme_id={s['coa_scheme_id']} data_date={s['data_date']} configs={s['config_node_count']}")

scheme_id = d['items'][0]['id']
scheme_code = d['items'][0]['scheme_code']
print(f"\n  使用方案: {scheme_code} (id={scheme_id})")

# 3. 节点配置
print("\n=== 3. 节点配置（取第一个配置） ===")
code, d = req("GET", f"/sim/node-config?scheme_id={scheme_id}&coa_node_id=236", token=token)
print(f"  status={code} exists={d.get('exists')}")
if d.get('exists'):
    print(f"  growth_rate={d.get('config', {}).get('annual_growth_rate')}")
    for r in d.get('ratios', []):
        print(f"    - term={r['term_value']}月 ratio={r['business_ratio']}% rate={r['interest_rate']}%")

# 4. 检查 ZXCOA_V1 是否有 prcp_data_basic 数据
print("\n=== 4. 检查 prcp_data_basic 数据（ZXCOA_V1 + 2026-09-01） ===")
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='prcp', password='Prcp@2026', database='prcp_db', charset='utf8mb4')
cur = conn.cursor()
cur.execute("""
    SELECT coa_node_id, current_balance, avg_balance, weighted_rate, data_date, date_offset
    FROM prcp_data_basic
    WHERE coa_node_id IN (
        SELECT n.id FROM prcp_coa_node n
        JOIN prcp_coa_scheme s ON s.id = n.scheme_id
        WHERE s.scheme_code='ZXCOA_V1' AND n.is_deleted=0
    )
    AND data_date='2026-09-01' AND is_deleted=0
    LIMIT 5
""")
rows = cur.fetchall()
print(f"  找到 {len(rows)} 行 ZXCOA_V1 + 2026-09-01 的 prcp_data_basic 数据")
for r in rows:
    print(f"    node_id={r[0]} current={r[1]} avg={r[2]} rate={r[3]} date={r[4]} offset={r[5]}")
conn.close()

# 5. 触发引擎
print("\n=== 5. 触发引擎 ===")
code, d = req("POST", f"/sim/schemes/{scheme_id}/run?month_count=3", token=token)
print(f"  status={code}")
print(f"  {d}")
if code != 200:
    print("  引擎失败，跳过后续验证")
    exit(1)
run_id = d['run_id']

# 6. 查询 run 状态
print(f"\n=== 6. 查询 run #{run_id} 状态 ===")
code, d = req("GET", f"/sim/runs/{run_id}", token=token)
print(f"  status={code}")
for k in ['id', 'sim_scheme_code', 'month_count', 'status', 'progress', 'total_nodes', 'processed_nodes', 'duration_ms']:
    print(f"    {k}={d.get(k)}")

# 7. 查询结果
print(f"\n=== 7. 查询结果（run_id={run_id}） ===")
code, d = req("GET", f"/sim/results?run_id={run_id}", token=token)
print(f"  status={code} count={len(d['items'])}")
for r in d['items'][:5]:
    print(f"    M{r['date_offset']:2d} {r['data_date']} {r['node_code']} current={r['current_balance']:.2f} avg={r['avg_balance']:.2f} rate={r['weighted_rate']:.4f}% interest={r['interest_amount']:.2f}")

# 8. 按月份分组
print(f"\n=== 8. 按月份统计 ===")
from collections import Counter
months = Counter(r['date_offset'] for r in d['items'])
print(f"  月份分布: {dict(sorted(months.items()))}")
print(f"  总节点数: {len(set(r['coa_node_id'] for r in d['items']))}")

# 9. 算法正确性验证（取一个节点 3 月趋势）
print(f"\n=== 9. 算法验证：单节点 3 月趋势 ===")
target_node = d['items'][0]['coa_node_id']
print(f"  节点 id={target_node}")
monthly_data = [r for r in d['items'] if r['coa_node_id'] == target_node]
monthly_data.sort(key=lambda x: x['date_offset'])
for r in monthly_data:
    print(f"    M{r['date_offset']:2d} {r['data_date']} current={r['current_balance']:12.2f} avg={r['avg_balance']:12.2f} rate={r['weighted_rate']:7.4f}% interest={r['interest_amount']:10.2f}")

# 10. DB 直查验证
print(f"\n=== 10. DB 直查 prcp_sim_result 数据 ===")
conn = pymysql.connect(host='127.0.0.1', port=3306, user='prcp', password='Prcp@2026', database='prcp_db', charset='utf8mb4')
cur = conn.cursor()
cur.execute(f"SELECT COUNT(*) FROM prcp_sim_result WHERE run_id={run_id}")
print(f"  prcp_sim_result 总行数: {cur.fetchone()[0]}")
cur.execute(f"SELECT date_offset, COUNT(*) FROM prcp_sim_result WHERE run_id={run_id} GROUP BY date_offset ORDER BY date_offset")
print(f"  按月分布: {cur.fetchall()}")
cur.execute(f"SELECT id, sim_scheme_code, run_id, status, progress, total_nodes, processed_nodes, duration_ms FROM prcp_sim_run WHERE id={run_id}")
r = cur.fetchone()
print(f"  prcp_sim_run: id={r[0]} code={r[1]} run={r[2]} status={r[3]} progress={r[4]} total={r[5]} processed={r[6]} duration={r[7]}ms")
conn.close()

print("\n✅ 引擎端到端测试完成")
