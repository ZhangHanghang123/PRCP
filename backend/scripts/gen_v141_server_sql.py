"""生成服务器 v14.1 评分规则的 INSERT SQL。

从 docs/_v14_segments.tsv（Excel 档位表真源）读取 184 段，
生成 prcp_kpi_score_rule / prcp_kpi_score_segment / prcp_kpi_value 的 INSERT。

单位换算：TSV 是小数单位（1.4422 = 144.22%），落库用百分数（144.22）。
"""
import csv, io, sys
from decimal import Decimal

sys.path.insert(0, r'C:/银行经营/PRCP/backend/scripts')
sys.stdout.reconfigure(encoding='utf-8')

from seed_score_rules_v14 import (IND, ORDER, KPI_CODE_REG, build_segments,
                                   engine_score, theory_score)

OUT = r'C:/银行经营/PRCP/backend/scripts/_v141_rules_server.sql'

# ---------- 1. 读 Excel 档位表（真源），做交叉校验 ----------
TSV = r'C:/银行经营/PRCP/docs/_v14_segments.tsv'
rows = list(csv.reader(io.open(TSV, encoding='utf-8-sig'), delimiter='\t'))
cur = None
excel = {}
for r in rows:
    rr = list(r)
    if rr[0].strip():
        cur = rr[0].strip()
    rr[0] = cur
    excel.setdefault(cur, []).append({
        'seg': int(rr[2]),
        'lo': float(rr[3]) * 100.0,
        'hi': float(rr[4]) * 100.0,
        'score': float(rr[9]),
        'score_min': float(rr[8]),
        'desc': rr[7],
    })
for k in excel:
    excel[k].sort(key=lambda s: s['seg'])

# ---------- 2. 与生成器结果交叉校验 ----------
for key in ORDER:
    segs = build_segments(IND[key])
    ex = excel[key]
    assert len(segs) == len(ex) == 23, (key, len(segs), len(ex))
    for (so, mn, mx, sc, smin, _d), e in zip(segs, ex):
        assert so == e['seg'], (key, so, e['seg'])
        assert abs(mn - e['lo']) < 1e-6, (key, so, mn, e['lo'])
        assert abs(mx - e['hi']) < 1e-6, (key, so, mx, e['hi'])
        assert abs(sc - e['score']) < 0.01, (key, so, sc, e['score'])
        assert abs(smin - e['score_min']) < 0.01, (key, so, smin, e['score_min'])
print('✓ 184 段与 Excel 档位表交叉校验通过')

# ---------- 3. 实测得分 ----------
scores = {}
for key in ORDER:
    cfg = IND[key]
    e = engine_score(build_segments(cfg), cfg['act'])
    t = theory_score(cfg, cfg['act'])
    assert abs(e - t) < 1e-6, (key, e, t)
    scores[key] = (cfg['act'], round(e, 2))
    print('  %-6s 实测 %-9s 得分 %-8.2f' % (key, cfg['act'], e))

total = sum(IND[k]['w'] * scores[k][1] for k in ORDER)
print('  加权总分 = %.2f / 500   /100 = %.2f' % (total, total / 5.0))

# ---------- 4. 生成 SQL ----------
def q(v):
    if v is None:
        return 'NULL'
    return "'%s'" % str(v).replace("'", "''")


lines = []
W = lines.append
W('-- ' + '=' * 74)
W('-- PRCP 评分标准 v14.1 · 8 指标 0-500 分规则落库（服务器 REG_* 体系）')
W('-- 生成: backend/scripts/gen_v141_server_sql.py')
W('-- 数据源: docs/_v14_segments.tsv（= docs/v2/评分标准_v14.1_EVE口径修正.xlsx 档位表）')
W('-- 单位: 百分数（144.22 表示 144.22%%）')
W('-- 引擎: prcp_kpi_score_segment.score=区间上界分, score_min=区间下界分')
W('-- 前置: fix_eve_server_20261105.sql（负债标记 + 新增KPI + v12b归档）')
W('-- ' + '=' * 74)
W('')
W('USE prcp_db;')
W('')
W('SET @uid := 1;')
W('SET @today := NOW();')
W('')
W('-- ' + '-' * 74)
W('-- 步骤 1：软删各 REG_* 现存有效规则')
W('--   ⚠ 唯一索引 uk_kpi_rule=(kpi_id, rule_name, is_deleted)，同名只能存在一条')
W('--     故先改写 rule_name 为归档名再置 is_deleted=1')
W('-- ' + '-' * 74)
W('UPDATE prcp_kpi_score_rule')
W('SET rule_name = CONCAT(rule_name, \' #archived@\', DATE_FORMAT(NOW(), \'%Y%m%d%H%i%s\')),')
W('    is_deleted = 1, updated_by = @uid, updated_at = NOW()')
W('WHERE is_deleted = 0 AND rule_name LIKE \'%v14%\';')
W('')
W('UPDATE prcp_kpi_score_segment s')
W('JOIN prcp_kpi_score_rule r ON r.id = s.rule_id')
W('SET s.is_deleted = 1, s.updated_at = NOW()')
W('WHERE r.is_deleted = 1 AND s.is_deleted = 0 AND r.rule_name LIKE \'%v14%\';')
W('')

# 规则
W('-- ' + '-' * 74)
W('-- 步骤 2：创建 v14.1 规则')
W('-- ' + '-' * 74)
rule_ids = {}
for i, key in enumerate(ORDER):
    code = KPI_CODE_REG[key]
    cfg = IND[key]
    higher = 1 if cfg['dir'] == 'H' else 0
    rname = '%s v14.3 锚点重标定+EVE区间重设 0-500 分评分' % code
    W('')
    W('-- %s (higher_is_better=%s, %s方向, over=%s)'
      % (code, higher, '越高越好' if cfg['dir'] == 'H' else '越低越好', cfg['over']))
    W('INSERT INTO prcp_kpi_score_rule')
    W(' (scheme_id, kpi_id, rule_name, calc_method, total_score, higher_is_better,')
    W('  description, status, is_deleted, created_by, updated_by, created_at, updated_at)')
    W('SELECT 1, d.id, %s, \'PIECEWISE\', 500, %d,' % (q(rname), higher))
    W('  %s,' % q('基于 docs/v2/评分标准_v14.3_EVE区间重设.xlsx - 锚点推导 23 段'
                  '（红线→危险→预警→安全→适度最优→过优），段内线性插值'))
    W('  \'ACTIVE\', 0, @uid, @uid, @today, @today')
    W('FROM prcp_kpi_definition d')
    W('WHERE d.kpi_code = %s AND d.is_deleted = 0 LIMIT 1;' % q(code))
    W('')
    # 显式取 kpi_id → rule_id 映射，避免依赖「INSERT 后回查」在个别驱动下读不到
    W('SET @kid_%s := (SELECT id FROM prcp_kpi_definition' % key)
    W('  WHERE kpi_code = %s AND is_deleted = 0 LIMIT 1);' % q(code))
    W('SET @rid_%s := (SELECT id FROM prcp_kpi_score_rule' % key)
    W('  WHERE kpi_id = @kid_%s AND is_deleted = 0 ORDER BY id DESC LIMIT 1);' % key)
    W('')

    # 段
    W('INSERT INTO prcp_kpi_score_segment')
    W(' (rule_id, seg_order, min_value, max_value, score, score_min, segment_desc,')
    W('  is_deleted, created_at, updated_at)')
    W('VALUES')
    segs = build_segments(cfg)
    vals = []
    for (so, mn, mx, sc, smin, desc) in segs:
        vals.append('  (@rid_%s, %d, %s, %s, %s, %s, %s, 0, NOW(), NOW())'
                    % (key, so,
                       Decimal(str(round(mn, 6))), Decimal(str(round(mx, 6))),
                       Decimal(str(round(sc, 2))), Decimal(str(round(smin, 2))),
                       q(desc)))
    W(',\n'.join(vals) + ';')
    W('')

# 指标值
W('-- ' + '-' * 74)
W('-- 步骤 3：刷新 2025-12-31 指标值（公开披露实测量）')
W('-- ' + '-' * 74)
for key in ORDER:
    code = KPI_CODE_REG[key]
    act, sc = scores[key]
    W('')
    W('DELETE FROM prcp_kpi_value')
    W('WHERE kpi_id = (SELECT id FROM prcp_kpi_definition WHERE kpi_code = %s AND is_deleted = 0)'
      % q(code))
    W('  AND data_date = \'2025-12-31\';')
    W('')
    W('INSERT INTO prcp_kpi_value')
    W(' (kpi_id, data_date, version, current_value, prev_value, prev_year_value,')
    W('  calc_source, score, is_deleted, created_by, updated_by, created_at, updated_at)')
    W('SELECT d.id, \'2025-12-31\', \'V1.0\', %s, NULL, NULL, \'MODEL\', %s,'
      % (Decimal(str(act)), Decimal(str(sc))))
    W('  0, @uid, @uid, @today, @today')
    W('FROM prcp_kpi_definition d')
    W('WHERE d.kpi_code = %s AND d.is_deleted = 0 LIMIT 1;' % q(code))

W('')
W('-- ' + '-' * 74)
W('-- 步骤 4：校验')
W('-- ' + '-' * 74)
W('SELECT d.kpi_code, r.id AS rule_id, r.total_score, r.higher_is_better,')
W('  (SELECT COUNT(*) FROM prcp_kpi_score_segment s')
W('    WHERE s.rule_id = r.id AND s.is_deleted = 0) AS seg_count')
W('FROM prcp_kpi_score_rule r')
W('JOIN prcp_kpi_definition d ON d.id = r.kpi_id AND d.is_deleted = 0')
W('WHERE r.is_deleted = 0 AND r.rule_name LIKE \'%v14%\'')
W('ORDER BY d.kpi_code;')
W('')
W('SELECT d.kpi_code, v.data_date, v.current_value, v.score')
W('FROM prcp_kpi_value v')
W('JOIN prcp_kpi_definition d ON d.id = v.kpi_id AND d.is_deleted = 0')
W('WHERE v.is_deleted = 0 AND v.data_date = \'2025-12-31\'')
W('  AND d.kpi_code IN (\'REG_LCR\',\'REG_NSFR\',\'REG_EVE\',\'REG_CET1\',')
W('                    \'REG_CAR\',\'REG_ROE\',\'REG_IBL\',\'REG_LR\')')
W('ORDER BY d.kpi_code;')

io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('\n已生成: %s' % OUT)
print('行数: %d' % len(lines))
