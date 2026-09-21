"""新业务模拟 API 端到端测试"""
import json
import urllib.request
import urllib.parse
import urllib.error

BASE = "http://127.0.0.1:8006/prcp/api"

def req(method, path, data=None, token=None):
    url = BASE + path
    body = None
    headers = {}
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
_, d = req("POST", "/auth/login")
# form-data
body = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
r = urllib.request.Request(BASE + "/auth/login", data=body, method="POST")
with urllib.request.urlopen(r) as resp:
    token = json.loads(resp.read())["access_token"]
print(f"  token len={len(token)}")

# 2. 方案列表（应该已经创建了 1 个）
print("\n=== 2. 方案列表 ===")
code, d = req("GET", "/sim/schemes", token=token)
print(f"  status={code} 方案数={len(d['items'])}")
for s in d['items']:
    print(f"    id={s['id']} code={s['scheme_code']} name={s['scheme_name']} coa={s['coa_scheme_code']} configs={s['config_node_count']}")

# 3. 账户册方案下拉
print("\n=== 3. 账户册方案下拉 ===")
code, d = req("GET", "/sim/coa-schemes", token=token)
print(f"  status={code}")
for s in d['items']:
    print(f"    id={s['id']} {s['scheme_code']} | {s['scheme_name']} ({s['node_count']} 节点)")

# 4. 账户册树
print("\n=== 4. 账户册树 ===")
code, d = req("GET", "/sim/coa-tree?coa_scheme_id=1", token=token)
def walk(ns, indent=0):
    for n in ns:
        print(" " * indent + f"- {n['title']} (id={n['id']} L{n['level']} leaf={n.get('isLeaf')})")
        if n.get('children'): walk(n['children'], indent+2)
walk(d['items'])

# 5. 节点基础信息
print("\n=== 5. 节点基础信息 (L3_LOAN_1) ===")
code, d = req("GET", "/sim/node-info/3", token=token)
print(f"  {d['node_code']} | {d['node_name']} | 余额={d['current_balance_amount']} ({d['current_balance_date']})")

# 6. 保存节点配置（占比之和=100，应成功）
print("\n=== 6. 保存节点配置（节点 3 + 求和=100） ===")
code, d = req("POST", "/sim/node-config?scheme_id=1",
              data={"coa_node_id": 3, "annual_growth_rate": 8.5, "term_unit": "MONTH",
                    "ratios": [
                      {"term_value": 3,  "term_unit": "MONTH", "business_ratio": 20.0},
                      {"term_value": 6,  "term_unit": "MONTH", "business_ratio": 15.0},
                      {"term_value": 12, "term_unit": "MONTH", "business_ratio": 25.0},
                      {"term_value": 24, "term_unit": "MONTH", "business_ratio": 30.0},
                      {"term_value": 36, "term_unit": "MONTH", "business_ratio": 10.0},
                    ]},
              token=token)
print(f"  status={code}  detail={d}")

# 7. 校验：占比之和≠100 应被拒绝
print("\n=== 7. 拒绝求和≠100 ===")
code, d = req("POST", "/sim/node-config?scheme_id=1",
              data={"coa_node_id": 4, "annual_growth_rate": 5.0, "term_unit": "MONTH",
                    "ratios": [
                      {"term_value": 3, "term_unit": "MONTH", "business_ratio": 30.0},
                      {"term_value": 6, "term_unit": "MONTH", "business_ratio": 30.0},
                    ]},
              token=token)
print(f"  status={code}  detail={d}")

# 8. 校验：term_unit=YEAR 应被拒绝
print("\n=== 8. 拒绝 term_unit != MONTH ===")
code, d = req("POST", "/sim/node-config?scheme_id=1",
              data={"coa_node_id": 5, "annual_growth_rate": 5.0, "term_unit": "YEAR",
                    "ratios": [
                      {"term_value": 3, "term_unit": "YEAR", "business_ratio": 100.0},
                    ]},
              token=token)
print(f"  status={code}  detail={d}")

# 9. 拉回已保存的节点配置
print("\n=== 9. 拉回已保存的节点配置（节点 3） ===")
code, d = req("GET", "/sim/node-config?scheme_id=1&coa_node_id=3", token=token)
print(f"  status={code}")
print(f"  exists={d['exists']} config_id={(d.get('config') or {}).get('id')} growth={(d.get('config') or {}).get('annual_growth_rate')}")
print(f"  ratios:")
for r in d.get('ratios', []):
    print(f"    - {r['term_value']}月: {r['business_ratio']}%")

# 10. 方案列表 config_node_count 应变 1
print("\n=== 10. 方案 config_node_count 更新 ===")
code, d = req("GET", "/sim/schemes", token=token)
for s in d['items']:
    print(f"  id={s['id']} {s['scheme_code']} config_node_count={s['config_node_count']}")

# 11. 软删方案
print("\n=== 11. 软删方案 ===")
code, d = req("DELETE", "/sim/schemes/1", token=token)
print(f"  status={code} detail={d}")

# 12. 软删后列表应空
print("\n=== 12. 软删后列表 ===")
code, d = req("GET", "/sim/schemes", token=token)
print(f"  剩余方案数={len(d['items'])}")

# 13. 数据库级验证（直接查 mysql 软删状态）
print("\n=== 13. DB 验证软删状态 ===")
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='prcp', password='Prcp@2026', database='prcp_db', charset='utf8mb4')
cur = conn.cursor()
cur.execute("SELECT id, scheme_code, is_deleted FROM prcp_sim_scheme")
print("  prcp_sim_scheme:")
for r in cur.fetchall():
    print(f"    id={r[0]} code={r[1]} is_deleted={r[2]}")
cur.execute("SELECT id, scheme_id, coa_node_id, is_deleted FROM prcp_sim_node_config")
print("  prcp_sim_node_config:")
for r in cur.fetchall():
    print(f"    id={r[0]} scheme={r[1]} node={r[2]} is_deleted={r[2] if False else r[3]}")
cur.execute("SELECT COUNT(*) FROM prcp_sim_term_ratio WHERE is_deleted=0")
print(f"  prcp_sim_term_ratio (未删除) = {cur.fetchone()[0]}")
conn.close()

print("\n✅ 端到端测试完成")
