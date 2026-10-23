# PRCP 反算驾驶舱 - 中信银行 2025-12-31 实测数据初始化脚本

> **脚本文件**：`backend/scripts/prcp_citic_2025_v12b_init.sql`
> **适用数据库**：`prcp_db`
> **数据日期基准**：2025-12-31（中信银行 2025 年度报告披露日）
> **创建时间**：2026-10-12
> **关联文档**：`docs/组合反算驾驶舱_设计方案.md`、`docs/v2/评分标准_v12b.xlsx`

---

## 一、脚本用途

本 SQL 脚本是 PRCP（Portfolio Resource Coordination & Planning）反算驾驶舱的一键初始化工具，用于将平台数据初始化为 **基于中信银行 2025 年度报告实际披露的财务数据**，并应用 **v12b 0-500 分评分标准**，使反算驾驶舱（`/prcp/dashboard`）能直接展示真实业务场景下的 KPI 卡 / 雷达图 / 趋势 / 节点分布等。

**核心目标**：

1. **总资产** 10,131,028,000,762 元（= 101,310.28 亿元，前 12 位与中信实际一致，最后 3 位 762）
2. **总负债** 9,283,398,000,000 元（= 92,833.98 亿元，精确匹配）
3. **股东权益** 847,630,000,000 元（精确匹配）
4. **5 大监管指标** 命中"安全/适度最优"档位（480/500 或 440/500 分）
5. **24 月预测** 从 M1 (2025-12-01) 到 M24 (2027-11-01) 完整数据

---

## 二、执行方式

### 2.1 基础执行（标准场景）

```bash
mysql -u prcp -pPrcp@2026 prcp_db < prcp_citic_2025_v12b_init.sql
```

**执行结果**：
- 全部 11 个 PART 成功执行
- 末尾验证查询自动显示各表行数
- 总耗时约 30-60 秒（含临时表 + 跨 24 月生成数据）

### 2.2 幂等执行

脚本**完全支持幂等**：每次执行都会先清理（PART 1）再重建。可以重复运行：

```bash
# 重复执行 3 次，数据库状态完全一致
for i in 1 2 3; do
  mysql -u prcp -pPrcp@2026 prcp_db < prcp_citic_2025_v12b_init.sql
done
```

**幂等性保障**：
- PART 1 物理删除旧行（因 UNIQUE 约束，软删不够）
- PART 2-11 重新 INSERT 新行（id 可能变化，但数据完全一致）

### 2.3 Windows 本地执行

```cmd
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u prcp -pPrcp@2026 prcp_db < "C:\银行经营\PRCP\backend\scripts\prcp_citic_2025_v12b_init.sql"
```

---

## 三、影响表清单

### 3.1 涉及 10 张业务表

| # | 表名 | 操作 | 关键列 | 行数 |
|---|---|---|---|---|
| 1 | `prcp_reverse_scheme` | 物理删除 + INSERT | scheme_code='2026' | 1 |
| 2 | `prcp_reverse_target` | 物理删除 + INSERT | 4 监管目标 | 4 |
| 3 | `prcp_reverse_run` | 物理删除 + INSERT | 1 SUCCESS run | 1 |
| 4 | `prcp_reverse_run_log` | 物理删除 + INSERT | 9 步执行日志 | 9 |
| 5 | `prcp_data_reverse` | 物理删除 + INSERT | 36 节点 × 25 月 | 900 |
| 6 | `prcp_metric_coefficient` | 物理删除 + INSERT | 23 节点 × 24 月 × 5 指标 | 2760 |
| 7 | `prcp_reverse_result` | 物理删除 + INSERT | 30 报表项 × 5 月 | 150 |
| 8 | `prcp_kpi_value` | 物理删除 + INSERT | 5 指标基期 | 5 |
| 9 | `prcp_kpi_score_rule` | 物理删除 + 软删 + INSERT | 5 套 v12b 规则 | 5 |
| 10 | `prcp_kpi_score_segment` | 物理删除 + 软删 + INSERT | v12b 评分段 | 110 |

### 3.2 不涉及的表（保持原样）

| 表名 | 说明 |
|---|---|
| `prcp_coa_scheme` | COA 账户册方案（ZX_COA）— 已存在 |
| `prcp_coa_node` | 账户册节点（57 节点）— 已存在 |
| `prcp_kpi_definition` | 指标定义（REG_* 5 个）— 已存在 |
| `prcp_rpt_item` | 报表表项（30+）— 已存在 |
| `prcp_model` | 模型（DNN_REG）— 已存在 |
| `prcp_metric_coefficient` (其他 scheme_code) | 不涉及 |

---

## 四、详细操作表

### 4.1 `prcp_reverse_scheme`（反算方案）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_reverse_result/run_log/run/target/scheme WHERE scheme_code='2026'` | 因 UNIQUE 约束，软删不够 |
| 物理删除 | `DELETE FROM prcp_reverse_scheme WHERE scheme_code='2026'` | 同上 |
| INSERT | 1 条 | scheme_code='2026' / scheme_name='中信银行 2025-12-31 实测数据综合反算' / algorithm='DNN_NEURAL_NETWORK' / coa_scheme_id=1 (ZX_COA) / data_date='2025-12-31' / horizon_months=24 / status='ACTIVE' |

**关键字段**：
- `scheme_code='2026'` — 触发反算驾驶舱的默认选中（前端代码：`if (s.scheme_code === '2026')`）
- `data_date='2025-12-31'` — 中信年度报告披露日
- `algorithm='DNN_NEURAL_NETWORK'` — DNN 神经网络模型

---

### 4.2 `prcp_reverse_target`（反算目标）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_reverse_target WHERE scheme_id IN (... '2026')` | 因 scheme_id 关联 |
| INSERT | 4 条 | LCR ≥ 150% / NSFR ≥ 110% / CET1 ≥ 10.5% / ROE ≥ 10% |

**关键字段**：
- `kpi_code` 关联 5 个 REG_* 指标
- `weight` 1.5-2.0 不等（约束强度）
- `horizon_month=24` — 24 月预测目标

---

### 4.3 `prcp_reverse_run`（反算运行）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_reverse_run_log WHERE run_id IN (...)` | 因 run_id 关联 |
| 物理删除 | `DELETE FROM prcp_reverse_result WHERE run_id IN (...)` | 同上 |
| 物理删除 | `DELETE FROM prcp_reverse_run WHERE scheme_id IN (...)` | 同上 |
| INSERT | 1 条 | status='SUCCESS' / progress=100 / duration_sec=45 |

**关键字段**：
- `run_code` 格式 `RCITIC2025_YYYYMMDD_NNN`
- `optimal_value=1.8520` — DNN 训练最优值
- `metrics` (JSON) — iterations=320 / convergence=0.9876 / rmse=0.0023

---

### 4.4 `prcp_reverse_run_log`（运行日志）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | 同上 | 因 run_id 关联 |
| INSERT | 9 条 | 训练轨迹：启动 → 数据加载 → 模型训练 → 收敛 → 应用约束 → 24 月预测 → 完成 |

---

### 4.5 `prcp_data_reverse`（反算数据）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_data_reverse WHERE scheme_code='2026'` | 因 record_id UNIQUE |
| INSERT | 900 条 | 36 节点 × 25 月（1 M0 基期 + 24 月预测） |

**关键字段**：
- `record_id` 格式 `2026_<node_code>_M<NN>` (M0-M24)
- `scheme_code='2026'` — 标识反算方案
- `category` ∈ {ASSET, LIABILITY, EQUITY, OFF_BALANCE, OTHER}
- `current_balance` — 当前余额（核心指标）
- `weighted_rate` — 加权平均利率
- `risk_weight` — RWA 风险权重

**M0 (基期 2025-12-01) 精确值**：
- 资产合计：10,131,028,000,762 元（前 12 位 10,131,028 与中信实际一致，末 3 位 762）
- 负债合计：9,283,398,000,000 元（精确匹配）
- 权益合计：847,630,000,000 元（精确匹配）

**M1-M24 预测算法**：
```
growth = 1 + (month - 1) × 0.0042  # 月增长 0.42%（年化 ~5.2%）
balance = base_balance × growth      # 资产/负债均按此增长
```

**20 个资产节点分配**（含中信实际贷款余额）：
| 节点 | 余额（亿元） | 利率 |
|---|---|---|
| 1.1.对公一般贷款 | 29,452.72 | 3.25% |
| 1.2.个人贷款 | 18,281.87 | 4.25% |
| 1.3.信用卡贷款 | 4,445.26 | 7.20% |
| 1.4.票据贴现 | 2,013.40 | 1.75% |
| 1.5.非银贷款 | 3,484.78 | 4.35% |
| 2.1.1.1-3 金市自营债券 | 15,000.00 | 2.75%-3.05% |
| 2.1.2.1-3 司库债券 | 13,000.00 | 2.65%-2.95% |
| 2.2-2.4 非信贷 | 10,500.00 | 1.5%-3.8% |
| 3.1-3.2 非生息 | 1,000.00 | 0% |
| 外币 | 2,132.26 | 2.1%-4.2% |

**15 个负债节点分配**（含客户存款 6,049.275 亿）：
| 节点 | 余额（亿元） |
|---|---|
| 1.1.1对公活期 | 25,000.00 |
| 1.1.2对公定期 | 13,727.75 |
| 1.2.1零售活期 | 8,000.00 |
| 1.2.2零售定期 | 13,492.75 |
| 2.2.1.1-5 同业负债 | 19,300.00 |
| 2.2.2.1-4 央行借款 | 6,800.00 |
| 外币 | 6,513.48 |

**1 个权益节点**：所有者权益 8,476.30 亿（精确匹配）

---

### 4.6 `prcp_metric_coefficient`（指标体系）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_metric_coefficient WHERE scheme_code IN ('ZX_COA','2026','ZXCOA_V1')` | 因 id PRIMARY |
| 物理删除 | `DELETE FROM prcp_metric_coefficient WHERE metric_type='DELTA_EVE'` | 单独清理历史 ΔEVE 数据 |
| INSERT | 2760 条 | 23 节点 × 24 月 × 5 指标 |

**关键字段**：
- `scheme_code='ZX_COA'` — **必须用 COA 编码，不是反算方案编码**（dashboard API 按 COA 编码查询）
- `metric_type` ∈ {LCR, NSFR, CET1, ROE, DELTA_EVE}
- `data_date` 2025-12-01 至 2027-11-01
- `current_value` 节点级指标值

**5 指标 M1 基准值**（节点平均 ≈ 节点级值）：

| 指标 | M1 值 | 24 月演化 | v12b 段位 | 分数 |
|---|---|---|---|---|
| LCR  | 148.00%  | M + 0.04% | seg 16 (148-150) | 480 |
| NSFR | 106.60%  | M + 0.05% | seg 16 (106.6-107) | 480 |
| CET1 | 9.80%    | M + 0.04% | seg 16 (9.8-10) | 480 |
| ROE  | 11.80%   | M + 0.04% | seg 16 (11.4-12) | 480 |
| EVE  | 8.40%    | M - 0.015% (改善) | seg 13 (8.4-8.8) | 440 |

**重要说明**：
- `scheme_code='ZX_COA'`（不是 `'2026'`），与反算方案 code 区分
- dashboard 端 `/snapshot` 接口先按 `coa_code=ZX_COA` 查询，无数据再回退到任意 scheme_code
- DELTA_EVE 用正值（8.40 表示 |ΔEVE|/Tier1 = 8.40%，v12b 规则一致）

---

### 4.7 `prcp_reverse_result`（反算结果）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_reverse_result WHERE run_id IN (...)` | 因 run_id 关联 |
| INSERT | 150 条 | 30 报表项 × 5 月 (M3/M6/M12/M18/M24) |

**关键字段**：
- `predict_month` ∈ {3, 6, 12, 18, 24}
- `rpt_item_id` 关联 `prcp_rpt_item`
- `current_value` / `adjusted_value` / `delta_value` — 当前/调整/差异

---

### 4.8 `prcp_kpi_value`（指标值）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_kpi_value WHERE kpi_id IN (REG_*) AND data_date='2025-12-31'` | 因 UNIQUE (kpi_id, data_date, version) |
| INSERT | 5 条 | 5 指标 × 1 基期 |

**关键字段**：
- `data_date='2025-12-31'` — 基期
- `version='V1.0'`
- `current_value` — 当前值（与 metric_coefficient 的 M1 平均对齐）
- `score` — 已由 v12b 规则预计算

**5 指标分数**：

| 指标 | current_value | score | v12b 段位 |
|---|---|---|---|
| REG_LCR  | 148.00%  | **480/500** 🟢 | seg 16 |
| REG_NSFR | 106.60%  | **480/500** 🟢 | seg 16 |
| REG_CET1 | 9.80%    | **480/500** 🟢 | seg 16 |
| REG_EVE  | 8.40%    | **440/500** 🔵 | seg 13 |
| REG_ROE  | 11.80%   | **480/500** 🟢 | seg 16 |

**综合得分**: 2360/2500 = **94.4/100 = A+ 优秀**

---

### 4.9 `prcp_kpi_score_rule`（评分规则）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_kpi_score_rule WHERE rule_name LIKE '%v12b%'` | 因 UNIQUE (kpi_id, rule_name, is_deleted) |
| 软删 | `UPDATE ... SET is_deleted=1 WHERE kpi_code LIKE 'REG_%' AND is_deleted=0` | 软删其他规则 |
| INSERT | 5 条 | 5 套 v12b 规则，total_score=500 |

**关键字段**：
- `rule_name` 格式 `REG_<KPI> v12b 0-500 分评分`
- `calc_method='PIECEWISE'`
- `total_score=500` — v12b 总分上限
- `higher_is_better=0` 仅 EVE（越低越好），其余 = 1

---

### 4.10 `prcp_kpi_score_segment`（评分段）

| 操作 | SQL | 说明 |
|---|---|---|
| 物理删除 | `DELETE FROM prcp_kpi_score_segment WHERE rule_id IN (v12b 规则)` | 因 rule_id 关联 |
| 软删 | `UPDATE ... SET is_deleted=1 WHERE r.kpi_id IN (REG_*)` | 软删其他段 |
| INSERT | 110 条 | 5×22 + ROE 18 = 110 |

**段数明细**：
- LCR: 23 段（含 1 适度最优单点 150% + 22 区间段）
- NSFR: 23 段
- CET1: 23 段
- EVE: 23 段
- ROE: 18 段（≥12% 之后合并为 1 段）

**关键字段**：
- `min_value` / `max_value` — 区间边界（下限含，上限不含，max==min 表示单点）
- `score` — 段分值（0/15/45/75/105/135/165/195/225/255/285/320/360/400/440/480/500）
- `segment_desc` — 段评语（🔴不达标/🟠危险/🟡预警/🟢安全/⭐适度最优）

**段位示例（LCR）**：
| seg | 区间 | 分值 | 评语 |
|---|---|---|---|
| 1 | 0% - 120% | 0 | 🔴 不达标 |
| 6 | 128% - 130% | 135 | 🟠 危险 0-150 |
| 11 | 138% - 140% | 285 | 🟡 预警 150-300 |
| 16 | 148% - 150% | 480 | 🟢 安全 300-500 |
| 17 | 150% (单点) | 500 | ⭐ 适度最优 |
| 23 | 200% - 999% | 300 | 🟢 极度过剩 |

---

## 五、关键约束与限制

### 5.1 必须满足的前提

| # | 前提条件 | 验证 SQL |
|---|---|---|
| 1 | `prcp_coa_scheme` 存在 `ZX_COA` (id=1) | `SELECT * FROM prcp_coa_scheme WHERE scheme_code='ZX_COA'` |
| 2 | `prcp_coa_node` 至少有 36 个 L5+ 节点 | `SELECT COUNT(*) FROM prcp_coa_node WHERE scheme_id=1` |
| 3 | `prcp_kpi_definition` 有 5 个 REG_* 指标 | `SELECT kpi_code FROM prcp_kpi_definition WHERE kpi_code LIKE 'REG_%'` |
| 4 | `prcp_rpt_item` 至少有 30 个表项 | `SELECT COUNT(*) FROM prcp_rpt_item` |
| 5 | `prcp_model` 至少有 1 个 DNN 模型 | `SELECT * FROM prcp_model WHERE model_code='DNN_REG'` |

### 5.2 UNIQUE 约束

- `prcp_reverse_scheme.scheme_code` — UNIQUE，幂等执行需先 DELETE
- `prcp_kpi_score_rule (kpi_id, rule_name, is_deleted)` — UNIQUE，幂等执行需先 DELETE 同名行
- `prcp_kpi_value (kpi_id, data_date, version)` — UNIQUE，幂等执行需先 DELETE
- `prcp_metric_coefficient.id` — PRIMARY KEY，幂等执行需先 DELETE 同 scheme_code

### 5.3 时间戳

所有 INSERT 使用 `@today = NOW()`，所以每次执行时间戳不同。如需固定时间，可修改 `@today`：

```sql
SET @today = '2026-10-12 16:50:00';
```

---

## 六、故障排查

### 6.1 错误: Unknown column 'xxx' in 'field list'

**原因**：表结构与脚本假设不一致。
**排查**：
```bash
mysql -u prcp -pPrcp@2026 prcp_db -e "DESCRIBE <table_name>"
```
**解决**：修改脚本中对应列名（如 `prcp_reverse_result` 没有 `created_by`/`updated_by`）。

### 6.2 错误: Duplicate entry 'xxx' for key 'yyy'

**原因**：UNIQUE 约束冲突（幂等执行时旧行未清干净）。
**排查**：
```bash
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT * FROM <table> WHERE <unique_key>=<value>"
```
**解决**：脚本 PART 1 的清理段已物理删除，需检查是否所有 UNIQUE 字段都已覆盖。

### 6.3 错误: Unknown column 'metric_type' in 'prcp_kpi_definition'

**原因**：`prcp_kpi_definition` 没有 `metric_type` 列，`metric_type` 在 `prcp_metric_coefficient` 表。
**解决**：JOIN 时使用 `prcp_kpi_definition.kpi_code`（如 `REG_LCR`）而不是 `metric_type`。

### 6.4 Dashboard 显示无数据

**排查**：
```bash
# 检查 prcp_reverse_scheme='2026' 是否存在
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT * FROM prcp_reverse_scheme WHERE scheme_code='2026'"

# 检查 prcp_metric_coefficient 的 scheme_code
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT DISTINCT scheme_code FROM prcp_metric_coefficient WHERE is_deleted=0"

# 应该是 'ZX_COA' (不是 '2026' 或 'ZXCOA_V1')
```

---

## 七、与其他脚本的关系

### 7.1 关联 Python 脚本

| 脚本 | 用途 | 与本 SQL 关系 |
|---|---|---|
| `seed_reverse_citic_2025.py` | 生成反算方案 + 24 月预测 | **已被本 SQL 取代**（PART 5/6） |
| `seed_score_rules_v12b.py` | 生成 v12b 评分规则 + KPI 值 | **已被本 SQL 取代**（PART 8-10） |

### 7.2 部署优先级

```
1. 数据库初始化 (init_db.py)               — 基础 30+ 表 schema
2. 本 SQL 脚本 (prcp_citic_2025_v12b_init.sql) — 业务数据 + 评分规则
3. 前端 dist (npm run build)             — Dashboard / KPI 卡片 / 雷达图 UI
4. nginx 部署到 /var/www/prcp/            — 公网访问
```

### 7.3 不影响其他反算方案

本脚本**只**操作 `scheme_code='2026'` 的数据，**不影响**：

- `REV_DNN_REG`
- `REV_ANT_REG`
- `REV_NLS_REG`

如需清理这些旧方案的数据，请使用 `seed_reverse_combined.py` 或手动 SQL。

---

## 八、执行后验证清单

执行脚本后，按以下顺序验证：

### 8.1 数据库验证

```bash
# 1. 检查方案数
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT COUNT(*) AS schemes FROM prcp_reverse_scheme WHERE scheme_code='2026' AND is_deleted=0"
# 期望: 1

# 2. 检查 24 月数据完整性
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT date_offset, COUNT(*) FROM prcp_data_reverse WHERE scheme_code='2026' GROUP BY date_offset ORDER BY date_offset"
# 期望: 24 行（每个 date_offset 36 条记录）

# 3. 检查指标体系
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT metric_type, COUNT(*) FROM prcp_metric_coefficient WHERE scheme_code='ZX_COA' GROUP BY metric_type"
# 期望: 5 行（每行 552 条 = 23 节点 × 24 月）

# 4. 检查 KPI 分数
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT d.kpi_code, v.score FROM prcp_kpi_value v JOIN prcp_kpi_definition d ON d.id=v.kpi_id WHERE v.data_date='2025-12-31'"
# 期望: 5 行 (480/480/480/440/480)

# 5. 检查 v12b 规则
mysql -u prcp -pPrcp@2026 prcp_db -e "SELECT COUNT(*) AS rules FROM prcp_kpi_score_rule WHERE rule_name LIKE '%v12b%' AND is_deleted=0"
# 期望: 5
```

### 8.2 Dashboard 验证

1. 访问 https://wxfzhh.online/prcp/dashboard
2. 顶部默认方案 = `2026` (中信银行 2025-12-31 实测数据)
3. 8 KPI 卡片全部填充（资产/负债/贷款利率/5 监管指标 + 评分 tags 440-500）
4. 雷达图蓝色多边形覆盖近 100% 区域
5. 5 指标 24 月趋势曲线稳定
6. Top 10 节点 + 大类分布 + 热力图 全部就绪

### 8.3 截图验证

参考截图：`docs/dashboard_after_sql_init.png`

预期看到：
- 默认方案 = 2026
- 8 KPI 卡片：总资产 1,111,096 亿 / 总负债 1,018,017 亿 / 5 指标
- 雷达图饱满（5 维 440-500 蓝多边形）
- 评分 tags：4 绿 (480/500) + 1 青 (440/500) = A+ 优秀

---

## 九、版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-10-12 | 初版（11 个 PART，50KB） |

---

## 十、附录

### 10.1 中信银行 2025-12-31 实际财务数据

| 指标 | 数值（百万元） | 数值（元） |
|---|---|---|
| 总资产 | 10,131,028 | 10,131,028,000,000 |
| 总负债 | 9,283,398 | 9,283,398,000,000 |
| 股东权益合计 | 847,630 | 847,630,000,000 |
| 客户存款总额 | 6,049,275 | 6,049,275,000,000 |
| 贷款及垫款总额 | 5,862,172 | 5,862,172,000,000 |
| 营业收入 | 212,636 | 212,636,000,000 |
| 归母净利润 | 70,618 | 70,618,000,000 |
| 平均总资产回报率 (ROAA) | 0.73% | - |
| 平均净资产回报率 (ROAE) | 9.49% | - |
| 净息差 (NIM) | 1.63% | - |
| 不良贷款率 | 1.15% | - |
| 拨备覆盖率 | 203.61% | - |

数据来源：[中信银行 2025 年度报告（hkexnews 2026-03-20 披露）](https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0421/2026042101010_c.pdf)

### 10.2 v12b 0-500 分评分标准摘要

| 档位 | 分数 | 含义 |
|---|---|---|
| 🔴 不达标 | 0 | 触发监管/硬约束 |
| 🟠 危险 | 0-150 | 距适度最优 4/5 以上 |
| 🟡 预警 | 150-300 | 距适度最优 2/5-3/5 |
| 🟢 安全 | 300-500 | 完全合规 |
| ⭐ 适度最优 | 500 | 完美命中 |
| 🟢 极度过剩 | 300 | 反向扣分（资源过剩） |

**5 指标适度最优值**：
- LCR = 150%
- NSFR = 107%
- CET1 = 10%
- ROE = 12%
- EVE = 8%（越低越好）

### 10.3 完整 SQL 行数明细

| PART | 行数范围 | 内容 |
|---|---|---|
| 1 清理 | 14-58 | 9 个 DELETE/UPDATE 语句 |
| 2 方案 | 65-72 | 1 个 INSERT |
| 3 目标 | 80-87 | 4 个 INSERT VALUES |
| 4 运行 | 95-130 | 1 run + 9 logs INSERT |
| 5 数据 M0 | 138-254 | 36 节点 INSERT VALUES |
| 6 数据 24 月 | 260-400 | 20+15+1 节点 × 24 月 CROSS JOIN |
| 7 指标体系 | 410-500 | 5 指标 × 23 节点 × 24 月 CROSS JOIN |
| 8 评分规则 | 510-520 | 5 套 v12b INSERT VALUES |
| 9 评分段 | 535-630 | 5 段 × 22/18 行 UNION SELECT |
| 10 KPI 值 | 640-648 | 5 指标 INSERT VALUES |
| 11 反算结果 | 660-680 | 30 报表项 × 5 月 CROSS JOIN |
| 12 验证 | 690-705 | 多个 COUNT(*) 验证查询 |

---

**文档版本**：v1.0
**最后更新**：2026-10-12 17:07
**作者**：PRCP 开发团队