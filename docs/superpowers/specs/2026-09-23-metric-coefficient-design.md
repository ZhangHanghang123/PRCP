# PRCP 指标计量系数维护 — 设计文档

> 文档版本: v1.0  |  日期: 2026-09-23  |  作者: PRCP WorkBuddy Agent
> 对应模块: 数据维护 → 10. 指标计量系数维护 (`/metric-coefficient`)

---

## 一、设计目标

提供一个**数据维护**模块，用于维护每个账户册节点在每个数据日期的 **5 大监管/经营指标**：

| 指标 | 字典 key | 含义 |
|------|----------|------|
| ROE | `ROE` | 净资产收益率（%） |
| 核心一级资本充足率 | `CET1` | Core Equity Tier 1（%） |
| LCR | `LCR` | 流动性覆盖率（%） |
| NSFR | `NSFR` | 净稳定资金比例（%） |
| △EVE | `DELTA_EVE` | 利率冲击下经济价值变动 |

设计要点：

| 维度 | 设计 |
|------|------|
| **粒度** | (账户册方案 × 账户册节点 × 指标类型 × 数据日期) → 1 行 |
| **ID 生成** | `{scheme_code}_{node_code}_{metric_code}_{YYYYMMDD}` |
| **指标类型字典** | `sys_dict` 新增 `METRIC_TYPE`（5 项）+ `METRIC_UNIT`（2 项） |
| **关联性** | 节点必须属于所选账户册方案 |
| **6 期数据** | current_value + y1_value + y2_value + y3_value + y4_value + y5_value |
| **批量导入** | 支持 Excel 批量导入 + 下载导入模板 |

---

## 二、数据库设计

### 2.1 prcp_metric_coefficient 表

```sql
CREATE TABLE prcp_metric_coefficient (
  id              VARCHAR(128) NOT NULL PRIMARY KEY,
  scheme_id       INT          NOT NULL,
  scheme_code     VARCHAR(64)  NOT NULL,
  node_id         INT          NOT NULL,
  node_code       VARCHAR(64)  NOT NULL,
  metric_type     VARCHAR(32)  NOT NULL,
  metric_code     VARCHAR(32)  NOT NULL,
  data_date       DATE         NOT NULL,
  current_value   DECIMAL(20,6) DEFAULT 0,
  y1_value        DECIMAL(20,6) DEFAULT 0,
  y2_value        DECIMAL(20,6) DEFAULT 0,
  y3_value        DECIMAL(20,6) DEFAULT 0,
  y4_value        DECIMAL(20,6) DEFAULT 0,
  y5_value        DECIMAL(20,6) DEFAULT 0,
  unit            VARCHAR(16)  DEFAULT 'PERCENT',
  description     TEXT,
  status          VARCHAR(16)  DEFAULT 'ACTIVE',
  is_deleted      TINYINT(1)   DEFAULT 0,
  created_by      INT,
  updated_by      INT,
  created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uk_uniq (scheme_code, node_code, metric_code, data_date, is_deleted),
  KEY idx_scheme_date (scheme_id, data_date),
  KEY idx_node_date (node_id, data_date),
  KEY idx_metric_type (metric_type, data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.2 字典

```sql
INSERT INTO sys_dict (dict_type, dict_key, dict_label, sort_order, status) VALUES
  ('METRIC_TYPE', 'ROE', '净资产收益率（%）', 1, 'ACTIVE'),
  ('METRIC_TYPE', 'CET1', '核心一级资本充足率（%）', 2, 'ACTIVE'),
  ('METRIC_TYPE', 'LCR', '流动性覆盖率（%）', 3, 'ACTIVE'),
  ('METRIC_TYPE', 'NSFR', '净稳定资金比例（%）', 4, 'ACTIVE'),
  ('METRIC_TYPE', 'DELTA_EVE', '△EVE（百万元）', 5, 'ACTIVE');

INSERT INTO sys_dict (dict_type, dict_key, dict_label, sort_order, status) VALUES
  ('METRIC_UNIT', 'PERCENT', '百分比', 1, 'ACTIVE'),
  ('METRIC_UNIT', 'ABSOLUTE', '绝对值', 2, 'ACTIVE');
```

---

## 三、API 接口

| Method | Path | 说明 |
|--------|------|------|
| GET | `/prcp/api/metric-coefficient` | 列表（带筛选：scheme_id / node_id / metric_type / data_date / keyword） |
| GET | `/prcp/api/metric-coefficient/options` | 下拉选项（账户册方案 / 节点 / 指标类型 / 单位） |
| GET | `/prcp/api/metric-coefficient/nodes-by-scheme` | 按方案过滤节点 |
| POST | `/prcp/api/metric-coefficient` | 创建（含 ID 自动生成） |
| PUT | `/prcp/api/metric-coefficient/{id}` | 更新 |
| DELETE | `/prcp/api/metric-coefficient/{id}` | 软删 |
| POST | `/prcp/api/metric-coefficient/import` | Excel 批量导入（multipart） |
| GET | `/prcp/api/metric-coefficient/export-template` | 下载导入模板 |
| GET | `/prcp/api/metric-coefficient/reverse-table` | 反算指标结果表（11 号） |

---

## 四、前端页面设计

### 4.1 顶部 KPI 区（4 个统计卡片）

```
┌────────────┬────────────┬────────────┬────────────┐
│ 记录总数    │ 覆盖方案数  │ 覆盖节点数  │ 覆盖指标类型│
│   40      │     1      │    40      │    5      │
└────────────┴────────────┴────────────┴────────────┘
```

### 4.2 筛选条

```
┌─────────────────┬─────────────────┬─────────────────┬──────────┐
│ 账户册方案 [▼]   │ 指标类型 [▼]    │ 数据日期 [📅]   │ 关键字    │
│ ZXCOA_V1         │ ROE             │ 2026-01-01     │ 资产     │
└─────────────────┴─────────────────┴─────────────────┴──────────┘
[🔍 查询] [🔄 重置] [+ 新增] [📥 导入] [📤 导出模板]
```

### 4.3 表格列

| 列 | 宽度 | 内容 | 显示样式 |
|----|------|------|----------|
| ID | 280 | `{scheme_code}_{node_code}_{metric_code}_{YYYYMMDD}` | code 字体 |
| 账户册方案 | 220 | `Tag(blue)` + 灰色 name | Tag + 灰色文字 |
| 账户册编码 | 200 | `Tag(geekblue)` + 灰色 name | Tag + 灰色文字 |
| 指标类型 | 100 | 字典值 | Tag(colored) |
| 数据日期 | 110 | yyyy-mm-dd | 文本 |
| 当前值 | 90 | 数值 | 数字 |
| y1_value | 90 | 数值 | 数字 |
| y2_value | 90 | 数值 | 数字 |
| y3_value | 90 | 数值 | 数字 |
| y4_value | 90 | 数值 | 数字 |
| y5_value | 90 | 数值 | 数字 |
| 操作 | 150 | 编辑 / 删除 | 按钮 |

### 4.4 新增 / 编辑 Modal

- 账户册方案（联动节点下拉）
- 账户册节点（按方案过滤）
- 指标类型（字典下拉）
- 数据日期（DatePicker）
- 6 期数值（InputNumber，addonAfter="%"/"万元"）
- 单位（字典下拉）
- 描述（TextArea）

**Banner 提示**：顶部说明 ID 自动生成规则

---

## 五、E2E 测试（11 步）

```
1) 健康检查 ✅
2) 登录 ✅
3) 加载下拉选项（2 方案 / 101 节点 / 5 指标 / 2 单位） ✅
4) 选择有效节点 ✅
5) 创建一条记录（ID = COA_V6_L1_资产_ROE_20260831） ✅
6) 列表查询（含筛选） ✅
7) 更新记录 ✅
8) 验证更新生效 ✅
9) 校验 ID 生成规则 ✅
10) 跨方案挂节点校验（拒绝 400） ✅
11) 删除记录 ✅
🎉 全部 11 步通过！
```

---

## 六、部署清单

| 类型 | 文件 |
|------|------|
| SQL | `backend/scripts/upgrade_metric_coefficient.sql` |
| Router | `backend/app/routers/metric_coefficient.py`（8 endpoint） |
| 前端 API | `frontend/src/api/index.ts`（追加 metricCoefficientApi） |
| 前端页面 | `frontend/src/pages/MetricCoefficient.tsx` |
| 前端路由 | `frontend/src/App.tsx` |
| 前端菜单 | `frontend/src/layouts/MainLayout.tsx` |
| E2E | `backend/tests/e2e_metric_coefficient_test.py` |
| 演示数据 | `backend/scripts/seed_metric_coefficient_demo.sql`（可选） |

## 七、Bug 修复（部署期间发现）

1. **URL-encode 中文节点名**：测试脚本 `urllib.request` 路径需 `quote()` URL 编码
2. **正则识别方案编码下划线**：`COA_V6` 含下划线，原正则 `[^_]+` 失败 → 改为 `.+`
3. **DatePicker 模式**：原 `picker='month'` 但后端精确匹配 DATE → 改为默认 day 模式
4. **默认查询**：filterSchemeId 默认为 undefined → 自动选 ZXCOA_V1 + ROE + 2026-01-01
5. **重置按钮**：原只清空 keyword → 改为恢复默认 3 个查询条件