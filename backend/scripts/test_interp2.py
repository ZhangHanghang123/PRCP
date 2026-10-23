"""创建独立的插值测试规则并验证"""
import json
import subprocess
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"
PWD = open("/tmp/pwd.txt").read().strip()

MYSQL = [
    "DELETE FROM prcp_kpi_score_segment WHERE rule_id=9001",
    "DELETE FROM prcp_kpi_score_rule WHERE id=9001",
    """INSERT INTO prcp_kpi_score_rule
       (id,scheme_id,kpi_id,rule_name,calc_method,total_score,higher_is_better,status,is_deleted)
       SELECT 9001, scheme_id, kpi_id, 'TEST_插值验证', 'PIECEWISE', 100, 1, 'INACTIVE', 0
       FROM prcp_kpi_score_rule WHERE id=51 LIMIT 1""",
    """INSERT INTO prcp_kpi_score_segment
       (rule_id,seg_order,min_value,max_value,score,score_min,segment_desc)
       VALUES
    (9001, 1, 0,    100, 100, 60,   '插值段: 0→60分, 100→100分'),
       (9001, 2, 100, 200, 100, 100,  '阶梯段: 恒定100分'),
       (9001, 3, 200, NULL, 80, NULL, '阶梯段: 恒定80分(兼容旧行为)')""",
]
for sql in MYSQL:
    subprocess.run(
        ["mysql", "-u", "prcp", "-pPrcp@2026", "prcp_db", "-e", sql],
        cwd="/tmp", executable="/usr/bin/mysql",
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
print("测试规则 9001 已创建\n")


def login():
    data = urllib.parse.urlencode({"username": "admin", "password": PWD}).encode()
    req = urllib.request.Request(
        BASE + "/auth/login", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r).get("access_token")


def calc(tok, v):
    req = urllib.request.Request(
        BASE + "/kpi/score-calc",
        data=json.dumps({"rule_id": 9001, "value": v}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
        method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


tok = login()
CASES = [
    ("插值段 [0,100] 60~100 分", [0, 5, 50, 100],
     lambda v: round(60 + v / 100.0 * 40, 2)),
    ("阶梯段 [100,200] score_min==score_max 恒100", [120, 150, 200],
     lambda v: 100),
    ("阶梯段 [200,+∞) score_min=NULL 恒80（旧行为）", [250, 999], lambda v: 80),
]
allok = True
for title, vals, fn in CASES:
    print(f"=== {title} ===")
    for v in vals:
        d = calc(tok, v)
        m = d.get("matched_range", {})
        got, exp = d.get("score"), fn(v)
        ok = got == exp
        allok &= ok
        print(f"  输入 {v:>5} → {got:>6} | {m.get('interpolate_mode'):<13} | "
              f"{m.get('segment_desc')} | 期望 {exp} {'OK' if ok else 'MISMATCH'}")
    print()

# 清理
for sql in ["DELETE FROM prcp_kpi_score_segment WHERE rule_id=9001",
            "DELETE FROM prcp_kpi_score_rule WHERE id=9001"]:
    subprocess.run(["mysql", "-u", "prcp", "-pPrcp@2026", "prcp_db", "-e", sql],
                   cwd="/tmp", executable="/usr/bin/mysql",
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("测试数据已清理 |", "全部通过" if allok else "存在不符")