"""验证分段评分插值（密码从 /tmp/pwd.txt 读，避开 shell 转义）"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8006/prcp/api"
PWD = open("/tmp/pwd.txt").read().strip()


def post_json(path, body, token=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def login():
    # 登录用 OAuth2PasswordRequestForm（form-data），不是 JSON
    data = urllib.parse.urlencode({"username": "admin", "password": PWD}).encode()
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r).get("access_token")


tok = login()
print("token ok\n")


def show(title, values, expect_fn=None):
    print(f"=== {title} ===")
    for v in values:
        d = post_json("/kpi/score-calc", {"rule_id": 51, "value": v}, tok)
        m = d.get("matched_range", {})
        got = d.get("score")
        line = f"  输入 {v:>6} → 得分 {got} | {m.get('interpolate_mode')} | {m.get('segment_desc')}"
        if expect_fn:
            exp = expect_fn(v)
            line += f" | 期望 {exp} {'OK' if got == exp else 'MISMATCH'}"
        print(line)
    print()


show("插值段 [0,100] → 60分~100分",
     [0, 5, 50, 100],
     lambda v: round(60 + (v - 0) / 100.0 * (100 - 60), 2))

show("阶梯段 [100,200] score_min==score_max → 恒定 100 分",
     [120, 150, 199],
     lambda v: 100)

show("原有阶梯段（score_min=NULL）应保持原行为",
     [50, 121, 123])