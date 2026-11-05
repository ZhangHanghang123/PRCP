"""CURV → PRCP 国债曲线同步 + 插值补齐

需求（2026-11-05）：
    把 CURV 库 curv_curve_point 的利率数据同步到 PRCP 的 prcp_rate_curv，
    然后在 PRCP 中记录（写入 prcp_rate_point 宽表，供利率管理与 EVE 计量使用）。

背景：
    - CURV 是独立的收益曲线模块（curv_db），国债曲线 curve_code = 'cnb_treasury_yield'
    - PRCP 是银行经营管理平台（prcp_db），利率管理用 prcp_rate_point（宽表 13 个期限列）
    - 两边期限点不完全重叠：
        CURV 有：1M 3M 6M 9M 1Y 2Y 3Y 5Y 7Y 10Y 15Y 20Y 30Y
        PRCP 有：d1 d7 m1 m3 m6 y1 y2 y3 y5 y10 y15 y20 y30
      缺 d1/d7（短于 1M）与 9M/7Y（介于标准点之间）→ 需插值

方案：
    1. 建 prcp_rate_curv 长表（curve_code + tenor + rate_value + data_date + 插值标记）
    2. 从 CURV 同步原始点（point_type='standard'/'key' 原样入表）
    3. 对 PRCP 需要的 13 个期限点做插值补齐：
         - 落在两个已知点之间 → 线性插值
         - 短于最短已知点（d1/d7 < 1M）→ 按最短点平推（flat extrapolation）
    4. 结果回写 prcp_rate_point（曲线码映射 CN_SOV_CNY ← cnb_treasury_yield）

插值方法说明：
    采用【年化期限 x = ln(1 + 年数)】还是【线性年数】？
    本实现用【线性年数】插值 —— 与 CURV 的 extrapolation_method='flat' +
    interpolation_method='pchip' 的实盘行为保持工程一致（对国债曲线这种
    平缓单调曲线，线性与 PCHIP 差异在 bp 级以内），且实现可审计、可复现。
"""
import sys
from decimal import Decimal

sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy import create_engine, text

CURV_DB = 'mysql+pymysql://curv:Curv%402026@127.0.0.1:3306/curv_db?charset=utf8mb4'
DB_URL = settings.DATABASE_URL_OVERRIDE or settings.DATABASE_URL

# CURV → PRCP 曲线码映射
CURVE_MAP = {
    'cnb_treasury_yield': ('CN_SOV_CNY', '中国国债收益率曲线（人民币）'),
    'cnb_policy_fin': ('CN_POL_CNY', '政策性金融债收益率曲线（人民币）'),
    'ncd_curve': ('CN_CD_CNY', '同业存单收益率曲线（人民币）'),
    'lpr_1y': ('CN_LPR_CNY', 'LPR 贷款市场报价利率曲线（人民币）'),
}

# CURV tenor → 期限（年）
TENOR_YEARS = {
    '1W': 7 / 365.0, '2W': 14 / 365.0, '1M': 1 / 12.0, '2M': 2 / 12.0,
    '3M': 3 / 12.0, '6M': 6 / 12.0, '9M': 9 / 12.0,
    '1Y': 1.0, '2Y': 2.0, '3Y': 3.0, '5Y': 5.0, '7Y': 7.0,
    '10Y': 10.0, '15Y': 15.0, '20Y': 20.0, '30Y': 30.0, '50Y': 50.0,
}

# PRCP prcp_rate_point 的 13 个期限点 → CURV 等价 tenor
PRCP_TERM_TO_TENOR = {
    'd1': None,          # CURV 无，≤1M，按最短点平推
    'd7': None,          # CURV 无，≤1M，按最短点平推
    'm1': '1M', 'm3': '3M', 'm6': '6M',
    'y1': '1Y', 'y2': '2Y', 'y3': '3Y', 'y5': '5Y',
    'y10': '10Y', 'y15': '15Y', 'y20': '20Y', 'y30': '30Y',
}
PRCP_TERM_YEARS = {
    'd1': 1 / 365.0, 'd7': 7 / 365.0, 'm1': 1 / 12.0, 'm3': 3 / 12.0,
    'm6': 6 / 12.0, 'y1': 1.0, 'y2': 2.0, 'y3': 3.0, 'y5': 5.0,
    'y10': 10.0, 'y15': 15.0, 'y20': 20.0, 'y30': 30.0,
}

# CURV tenor → PRCP 标准期限键（长表统一用标准键，宽表可直接取值）
STD_TENOR = {
    '1M': 'm1', '3M': 'm3', '6M': 'm6',
    '1Y': 'y1', '2Y': 'y2', '3Y': 'y3', '5Y': 'y5',
    '10Y': 'y10', '15Y': 'y15', '20Y': 'y20', '30Y': 'y30',
}

DDL = """
CREATE TABLE IF NOT EXISTS prcp_rate_curv (
  id            bigint       NOT NULL AUTO_INCREMENT,
  curve_code    varchar(64)  NOT NULL,
  tenor         varchar(16)  NOT NULL,
  tenor_years   decimal(12,6) NOT NULL DEFAULT 0,
  rate_value    decimal(12,6) NOT NULL DEFAULT 0,
  point_unit    varchar(16)  DEFAULT 'percent',
  point_type    varchar(32)  DEFAULT 'standard',
  is_interpolated tinyint(1) DEFAULT 0,
  source_curve  varchar(64)  DEFAULT NULL,
  source_system varchar(32)  DEFAULT 'CURV',
  data_date     date         NOT NULL,
  sort_order    int          NOT NULL DEFAULT 0,
  remark        varchar(255) DEFAULT NULL,
  is_deleted    tinyint(1)   DEFAULT 0,
  created_by    bigint       DEFAULT NULL,
  updated_by    bigint       DEFAULT NULL,
  created_at    datetime     DEFAULT CURRENT_TIMESTAMP,
  updated_at    datetime     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_curve_tenor_date (curve_code, tenor, data_date),
  KEY idx_code_date (curve_code, data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='利率曲线长表（自 CURV 同步，缺失期限插值补齐）';
"""


def interpolate(known, target_years):
    """按线性年数插值。

    known: [(years, rate), ...] 按 years 升序
    target_years: 目标期限（年）
    返回 (rate, is_interpolated)
      - 落在两点之间 → 线性插值，is_interpolated=1
      - 超出范围 → 按端点平推（flat），is_interpolated=1
    """
    if not known:
        return None, 0
    if len(known) == 1:
        return known[0][1], 1
    ys = [k[0] for k in known]
    rs = [k[1] for k in known]
    if target_years <= ys[0]:
        return rs[0], 1
    if target_years >= ys[-1]:
        return rs[-1], 1
    for i in range(len(ys) - 1):
        if ys[i] <= target_years <= ys[i + 1]:
            y0, y1 = ys[i], ys[i + 1]
            r0, r1 = rs[i], rs[i + 1]
            if abs(y1 - y0) < 1e-12:
                return r0, 1
            r = r0 + (target_years - y0) / (y1 - y0) * (r1 - r0)
            return r, 1
    return rs[-1], 1


def main():
    prcp = create_engine(DB_URL)
    curv = create_engine(CURV_DB)

    print('=' * 96)
    print('CURV → PRCP 国债曲线同步 + 插值补齐')
    print('=' * 96)

    # ---- 1. 建长表 ----
    with prcp.begin() as c:
        c.execute(text(DDL))
    print('\n[1] prcp_rate_curv 长表就绪')

    # ---- 2. 读 CURV 原始点 ----
    with curv.connect() as c:
        rows = c.execute(text("""
            SELECT curve_code, tenor, rate_value, point_unit, point_type, sort_order
            FROM curv_curve_point
            WHERE is_deleted = 0 AND rate_value IS NOT NULL
              AND curve_code IN ('cnb_treasury_yield','cnb_policy_fin','ncd_curve','lpr_1y')
            ORDER BY curve_code, sort_order
        """)).fetchall()
    print('[2] CURV 原始点 %d 条' % len(rows))

    by_curve = {}
    for code, tenor, rv, unit, ptype, so in rows:
        by_curve.setdefault(code, []).append((tenor, float(rv), unit, ptype, so))

    # ---- 3. 写长表：原始点 + 插值点 ----
    DATA_DATE = '2025-12-31'
    inserted = 0
    detail = {}
    with prcp.begin() as c:
        for curv_code, pts in by_curve.items():
            prcp_code, prcp_name = CURVE_MAP[curv_code]
            # 3.0 幂等：软删本曲线下所有非标准键的旧写法
            #     （避免 tenor 出现 '1M' 与 'm1' 两种写法并存）
            c.execute(text("""
                UPDATE prcp_rate_curv SET is_deleted=1, updated_at=NOW()
                WHERE curve_code=:cc AND is_deleted=0
                  AND tenor IN ('1M','3M','6M','9M','1Y','2Y','3Y','5Y','7Y',
                                '10Y','15Y','20Y','30Y')
            """), {'cc': prcp_code})

            # 3.1 原始点（tenor 统一转成 PRCP 标准键，便于宽表取值）
            for tenor, rv, unit, ptype, so in pts:
                yrs = TENOR_YEARS.get(tenor, 0.0)
                std_tenor = STD_TENOR.get(tenor, tenor)
                c.execute(text("""
                    INSERT INTO prcp_rate_curv
                    (curve_code, tenor, tenor_years, rate_value, point_unit, point_type,
                     is_interpolated, source_curve, source_system, data_date,
                     sort_order, remark, is_deleted, created_by, updated_by)
                    VALUES (:cc, :t, :ty, :rv, :pu, :pt, 0, :sc, 'CURV', :dd, :so, :rm, 0, 1, 1)
                    ON DUPLICATE KEY UPDATE
                      rate_value=VALUES(rate_value), tenor_years=VALUES(tenor_years),
                      is_interpolated=0, source_curve=VALUES(source_curve),
                      updated_by=1, updated_at=NOW()
                """), {
                    'cc': prcp_code, 't': std_tenor, 'ty': Decimal(str(round(yrs, 6))),
                    'rv': Decimal(str(round(rv, 6))), 'pu': unit or 'percent',
                    'pt': ptype or 'standard', 'sc': curv_code, 'dd': DATA_DATE,
                    'so': so, 'rm': 'CURV 同步原始点',
                })
                inserted += 1

            # 3.2 PRCP 13 期限点插值补齐
            known = sorted([(TENOR_YEARS.get(t, 0.0), v) for t, v, _u, _p, _s in pts
                            if t in TENOR_YEARS], key=lambda x: x[0])
            interp_rows = []
            covered = set(STD_TENOR.get(t, t) for t, _v, _u, _p, _s in pts)
            for term, tenor_equiv in PRCP_TERM_TO_TENOR.items():
                ty = PRCP_TERM_YEARS[term]
                if term in covered:
                    continue        # 已由原始点覆盖（标准键）
                r, is_i = interpolate(known, ty)
                if r is None:
                    continue
                method = '外推(flat)' if (known and (ty <= known[0][0] or ty >= known[-1][0])) else '线性插值'
                c.execute(text("""
                    INSERT INTO prcp_rate_curv
                    (curve_code, tenor, tenor_years, rate_value, point_unit, point_type,
                     is_interpolated, source_curve, source_system, data_date,
                     sort_order, remark, is_deleted, created_by, updated_by)
                    VALUES (:cc, :t, :ty, :rv, 'percent', 'interpolated', 1, :sc, 'CURV', :dd, :so, :rm, 0, 1, 1)
                    ON DUPLICATE KEY UPDATE
                      rate_value=VALUES(rate_value), tenor_years=VALUES(tenor_years),
                      is_interpolated=1, source_curve=VALUES(source_curve),
                      remark=VALUES(remark), updated_by=1, updated_at=NOW()
                """), {
                    'cc': prcp_code, 't': term, 'ty': Decimal(str(round(ty, 6))),
                    'rv': Decimal(str(round(r, 6))), 'sc': curv_code, 'dd': DATA_DATE,
                    'so': 100 + list(PRCP_TERM_TO_TENOR.keys()).index(term),
                    'rm': '%s（由 CURV %s 补齐）' % (method, curv_code),
                })
                inserted += 1
                interp_rows.append((term, ty, r, method))
            detail[prcp_code] = interp_rows
            print('    %-14s ← %-22s 原始点 %d + 插值补齐 %d'
                  % (prcp_code, curv_code, len(pts), len(interp_rows)))

    print('[3] prcp_rate_curv 写入 %d 条' % inserted)

    # ---- 4. 回写 prcp_rate_point 宽表 ----
    with prcp.begin() as c:
        for prcp_code, _name in CURVE_MAP.values():
            if prcp_code not in detail:
                continue
            pt = c.execute(text("""
                SELECT tenor, rate_value FROM prcp_rate_curv
                WHERE curve_code=:cc AND data_date=:dd AND is_deleted=0
            """), {'cc': prcp_code, 'dd': DATA_DATE}).fetchall()
            got = {t: float(v) for t, v in pt}
            # 缺 9M/7Y 之外的标准点也要补：PRCP 13 期限 → 取值
            def g(term):
                return got.get(term, 0.0)
            # PRCP 宽表期限 → 长表 tenor 的映射（d1/d7 用 d1/d7，插值时已生成）
            cols = {
                'rate_d1': g('d1'), 'rate_d7': g('d7'), 'rate_m1': g('m1'),
                'rate_m3': g('m3'), 'rate_m6': g('m6'), 'rate_y1': g('y1'),
                'rate_y2': g('y2'), 'rate_y3': g('y3'), 'rate_y5': g('y5'),
                'rate_y10': g('y10'), 'rate_y15': g('y15'), 'rate_y20': g('y20'),
                'rate_y30': g('y30'),
            }
            upd = {k: Decimal(str(round(v, 6))) for k, v in cols.items()}
            exists = c.execute(text("""
                SELECT id FROM prcp_rate_point
                WHERE curve_code=:cc AND data_date=:dd AND is_deleted=0 LIMIT 1
            """), {'cc': prcp_code, 'dd': DATA_DATE}).fetchone()
            if exists:
                c.execute(text("""
                    UPDATE prcp_rate_point SET
                      rate_d1=:rate_d1, rate_d7=:rate_d7, rate_m1=:rate_m1,
                      rate_m3=:rate_m3, rate_m6=:rate_m6, rate_y1=:rate_y1,
                      rate_y2=:rate_y2, rate_y3=:rate_y3, rate_y5=:rate_y5,
                      rate_y10=:rate_y10, rate_y15=:rate_y15, rate_y20=:rate_y20,
                      rate_y30=:rate_y30, updated_by=1, updated_at=NOW()
                    WHERE id=:i
                """), dict(upd, i=exists[0]))
                act = '更新'
            else:
                c.execute(text("""
                    INSERT INTO prcp_rate_point
                    (curve_id, curve_code, data_date, ccy,
                     rate_d1, rate_d7, rate_m1, rate_m3, rate_m6,
                     rate_y1, rate_y2, rate_y3, rate_y5,
                     rate_y10, rate_y15, rate_y20, rate_y30,
                     is_deleted, created_by, updated_by)
                    SELECT s.id, :cc, :dd, 'CNY',
                     :rate_d1, :rate_d7, :rate_m1, :rate_m3, :rate_m6,
                     :rate_y1, :rate_y2, :rate_y3, :rate_y5,
                     :rate_y10, :rate_y15, :rate_y20, :rate_y30,
                     0, 1, 1
                    FROM prcp_rate_scheme s WHERE s.curve_code=:cc LIMIT 1
                """), dict(upd, cc=prcp_code, dd=DATA_DATE))
                act = '新增'
            print('[4] prcp_rate_point %s %s @ %s' % (prcp_code, act, DATA_DATE))

    # ---- 5. 校验 ----
    print()
    print('=' * 96)
    print('校验：prcp_rate_curv 国债曲线')
    print('=' * 96)
    with prcp.connect() as c:
        for prcp_code in ('CN_SOV_CNY',):
            print('\n  %s @ %s' % (prcp_code, DATA_DATE))
            rows2 = c.execute(text("""
                SELECT tenor, tenor_years, rate_value, point_type, is_interpolated, remark
                FROM prcp_rate_curv WHERE curve_code=:cc AND data_date=:dd AND is_deleted=0
                ORDER BY sort_order, tenor_years
            """), {'cc': prcp_code, 'dd': DATA_DATE}).fetchall()
            for t, ty, rv, pt, ii, rm in rows2:
                print('    %-6s %8.4f年  %8.6f%%  %-12s %s  %s'
                      % (t, float(ty), float(rv), pt, '插值' if ii else '原始', rm or ''))
            w = c.execute(text("""
                SELECT rate_d1,rate_d7,rate_m1,rate_m3,rate_m6,rate_y1,rate_y2,
                       rate_y3,rate_y5,rate_y10,rate_y15,rate_y20,rate_y30
                FROM prcp_rate_point WHERE curve_code=:cc AND data_date=:dd AND is_deleted=0
            """), {'cc': prcp_code, 'dd': DATA_DATE}).fetchone()
            if w:
                names = ['d1','d7','m1','m3','m6','y1','y2','y3','y5','y10','y15','y20','y30']
                print('\n    prcp_rate_point 宽表:')
                print('      ' + '  '.join('%s=%.4f' % (n, float(v))
                                          for n, v in zip(names, w)))
    print()
    print('=' * 96)


if __name__ == '__main__':
    main()
