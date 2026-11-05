"""监管指标 · EVE 经济价值变动（IRRBB）—— 现金流现值法（生产口径）

口径（v14.1 评分标准一致）：
    行内 ΔEVE = |ΔEVE| / 一级资本 × 100   （单位：%，越小越好）

计算式（巴塞尔 IRRBB SRP31.90-93 六情景，简化实现）：
    对每个末级账户的期限桶现金流（orig_m1..m60 + rem_m1..rem_m60）：
        资产PV = Σ CF_t / (1 + r_asset(t))^t
        负债PV = Σ CF_t / (1 + r_liab(t))^t
        负债利率 r_liab = 基准 + (资产冲击后利率 − 基准) × β
    EVE      = 资产PV − 负债PV
    ΔEVE     = EVE_冲击 − EVE_基准
    行内ΔEVE% = |ΔEVE| / Tier1 × 100

数据源（全部来自 PRCP 库）：
    - prcp_data_basic：末级账户(is_leaf=1) 期限桶现金流 + 当前余额
    - prcp_rate_curv / prcp_rate_point：国债收益率曲线 CN_SOV_CNY（自 CURV 同步并插值补齐）
    - prcp_eve_param：账户资产/负债属性(is_asset / is_liability)
    - prcp_data_basic S030000000000：一级资本（所有者权益）

情景与冲击：
    steepener      变陡峭   长端(>1Y) 每年 +100bp，β=0.5
    parallel_up    平行上移  全期限 +250bp
    parallel_down  平行下移  全期限 −250bp
    基准情景        无冲击

默认取【变陡峭】作为行内监控情景 —— 与 v3 计量模版一致
（v3 模版实测 |ΔEVE|/Tier1 = 61.39%，评分标准实测值来源）。

⚠ 与 scripts/kpi_functions/reg_eve.py（久期缺口近似法）的关系：
    久期法用加权平均久期近似，忽略期限分布，算出的 |ΔEVE|/Tier1 约 0.87%，
    明显低估（现值法能捕捉长端期限错配）。本脚本为评分标准对应的口径。
"""
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


DB_URL = f"mysql+pymysql://prcp:{quote_plus('Prcp@2026')}@127.0.0.1:3306/prcp_db?charset=utf8mb4"
CURVE_CODE = "CN_SOV_CNY"
TIER1_NODE = "S030000000000"
BETA = 0.5          # 存款利率传导系数（负债端）
SHORT_YEAR = 1.0    # 短端/长端分界（年）
SCENARIO = "steepener"
SHOCK_BP = {"steepener": 100.0, "parallel_up": 250.0, "parallel_down": 250.0}

# 期限桶 → 年数
BUCKETS = ([('m%d' % m, m / 12.0) for m in range(1, 61)] +
           [('y%d' % y, float(y)) for y in (10, 15, 20, 30)])

# 曲线标准期限键 → 年数
CURVE_KEYS = [('d1', 1 / 365.), ('d7', 7 / 365.), ('m1', 1 / 12.), ('m3', .25),
              ('m6', .5), ('y1', 1.), ('y2', 2.), ('y3', 3.), ('y5', 5.),
              ('y10', 10.), ('y15', 15.), ('y20', 20.), ('y30', 30.)]


def _rate_at(pts, years):
    """按年数从曲线取利率（线性插值 + flat 外推）"""
    if not pts:
        return 0.0
    ys = [p[0] for p in pts]
    rs = [p[1] for p in pts]
    if years <= ys[0]:
        return rs[0]
    if years >= ys[-1]:
        return rs[-1]
    for i in range(len(ys) - 1):
        if ys[i] <= years <= ys[i + 1]:
            t = (years - ys[i]) / (ys[i + 1] - ys[i])
            return rs[i] + t * (rs[i + 1] - rs[i])
    return rs[-1]


def _scenario_rate(base_r, years, scenario, amp):
    if scenario == 'parallel_up':
        return base_r + amp / 100.0
    if scenario == 'parallel_down':
        return max(0.0, base_r - amp / 100.0)
    if scenario == 'steepener':
        return base_r if years <= SHORT_YEAR else base_r + min(amp / 100.0, 1.0)
    return base_r


def calc(ctx: dict) -> float:
    """返回行内 ΔEVE = |ΔEVE| / Tier1 × 100 （%）"""
    data_date = ctx.get("data_date", "2025-12-31")
    scenario = (ctx.get("ctx_extra") or {}).get("eve_scenario", SCENARIO)
    amp = SHOCK_BP.get(scenario, SHOCK_BP[SCENARIO])

    engine = create_engine(DB_URL, echo=False)
    with engine.begin() as conn:
        # ---- 国债曲线 ----
        curve = {}
        for t, v in conn.execute(text("""
            SELECT tenor, rate_value FROM prcp_rate_curv
            WHERE curve_code=:cc AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d')
              AND is_deleted=0
        """), {'cc': CURVE_CODE, 'dd': data_date}).fetchall():
            curve[t] = float(v or 0)
        if not curve:
            # 回退到宽表
            row = conn.execute(text("""
                SELECT rate_d1,rate_d7,rate_m1,rate_m3,rate_m6,rate_y1,rate_y2,
                       rate_y3,rate_y5,rate_y10,rate_y15,rate_y20,rate_y30
                FROM prcp_rate_point
                WHERE curve_code=:cc AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d')
                  AND is_deleted=0 LIMIT 1
            """), {'cc': CURVE_CODE, 'dd': data_date}).fetchone()
            if row:
                for k, v in zip([k for k, _ in CURVE_KEYS], row):
                    curve[k] = float(v or 0)
        pts = sorted([(y, curve[k]) for k, y in CURVE_KEYS if k in curve],
                     key=lambda x: x[0])
        if not pts:
            return 0.0

        # ---- 末级账户现金流 ----
        bucket_cols = ','.join(['orig_%s, rem_%s' % (b, b) for b, _y in BUCKETS])
        rows = conn.execute(text(
            'SELECT d.node_code, d.current_balance, ' + bucket_cols +
            ' FROM prcp_data_basic d '
            'WHERE d.data_date=STR_TO_DATE(:dd,\'%Y-%m-%d\') '
            'AND d.is_deleted=0 AND d.is_leaf=1'
        ), {'dd': data_date}).fetchall()

        # ---- 资产/负债属性 ----
        amap = {}
        for nc, ia, il in conn.execute(text("""
            SELECT node_code, is_asset, is_liability FROM prcp_eve_param
            WHERE scheme_code='ZX_COA' AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d')
              AND is_deleted=0
        """), {'dd': data_date}).fetchall():
            amap[nc] = (int(ia or 0), int(il or 0))

        tier1 = float(conn.execute(text("""
            SELECT current_balance FROM prcp_data_basic
            WHERE node_code=:n AND data_date=STR_TO_DATE(:dd,'%Y-%m-%d')
              AND is_deleted=0
        """), {'n': TIER1_NODE, 'dd': data_date}).scalar() or 0)

    if tier1 <= 0:
        return 0.0

    def pv(scen):
        apv = lpv = 0.0
        for r in rows:
            nc = r[0]
            ia, il = amap.get(nc, (0, 0))
            if not (ia or il):
                continue
            for bi, (_bk, years) in enumerate(BUCKETS):
                cf = float(r[2 + bi * 2] or 0) + float(r[3 + bi * 2] or 0)
                if cf == 0:
                    continue
                base_r = _rate_at(pts, years)
                a_rate = _scenario_rate(base_r, years, scen, amp)
                l_rate = base_r + (a_rate - base_r) * BETA
                a_df = 1.0 / (1 + a_rate / 100.0) ** years
                l_df = 1.0 / (1 + l_rate / 100.0) ** years
                if ia:
                    apv += cf * a_df
                else:
                    lpv += cf * l_df
        return apv, lpv

    b_apv, b_lpv = pv('baseline')
    base_eve = b_apv - b_lpv
    s_apv, s_lpv = pv(scenario)
    dev = (s_apv - s_lpv) - base_eve
    return round(abs(dev) / tier1 * 100.0, 4)
