# PRCP 组合反算 · 结果驾驶舱 — 设计文档

> 文档版本: v1.0  |  日期: 2026-09-23  |  作者: PRCP WorkBuddy Agent
> 对应模块: 首页 Dashboard (`/dashboard`)
> 升级前: 原 Dashboard（录入趋势 + 方案分布）

---

## 一、设计目标

打造一个**对标银行级经营驾驶舱**风格的组合反算结果展示页面，要求：

| 维度 | 目标 |
|------|------|
| **数据全链路** | 方案 → Run → 月份 → 节点 × 指标联动 |
| **高端大气** | 12 列 KPI + 5 指标趋势 + 大类分布 + 节点热力图 + Top 10 + 风险预警 |
| **数据驱动** | 100% 来源于 prcp_* 业务表（零硬编码数据） |
| **默认可看** | 默认组合方案 = **2026**，默认 Run = 最新 SUCCESS，默认月份 = M1 |
| **业务友好** | 节点自动按 ZX_A/L/E 前缀分类（资产/负债/权益/表外） |
| **风险预警** | 自动识别 5 大指标超阈值节点（CET1/LCR/NSFR/ROE/ΔEVE） |

---

## 二、页面结构

```
┌──────────────────────────────────────────────────────────────────────┐
│  📊 组合反算 · 结果驾驶舱  [方案▼2026][月份▼M1][🔄][⛶]               │
│  📅 数据日期：2026-01-01  🏷️ 账户册方案：ZXCOA_V1 账户册总表_v7      │
├──────────────────────────────────────────────────────────────────────┤
│  ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭─────╮ ╭──────╮  │
│  │节点 │ │挂指标│ │ 资产 │ │ 负债 │ │ 权益 │ │ ROE │ │CET1 │ │ LCR  │  │
│  ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰─────╯ ╰──────╯  │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────┐                │
│  │ 1️⃣ 5 指标 24 月趋势       │  │ 2️⃣ 大类分布       │   第 1 行      │
│  │ (折线 + 阈值线)          │  │ (饼图 + 柱图)    │                │
│  └──────────────────────────┘  └──────────────────┘                │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────┐  ┌────────────────────────────┐   │
│  │ 3️⃣ 节点 × 5 指标 热力图        │  │ 4️⃣ Top 10 节点（按余额）    │   │
│  │ (切换指标 + 按大类过滤)      │  │ 余额 + 5 指标           │   │
│  └──────────────────────────────┘  └────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│  5️⃣ 风险预警列表（节点 + 指标 + 当前值 + 阈值 + 差值）               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详解

### 3.1 顶部 8 大 KPI 卡

| KPI | 计算 | 数据源 |
|-----|------|--------|
| 节点总数 | `count(prcp_coa_node)` | prcp_coa_node |
| 挂指标节点数 | `count(distinct node_code in metric_coefficient)` | prcp_metric_coefficient |
| 资产总额 | `sum(current_balance where category='ASSET')` | prcp_data_reverse |
| 负债总额 | `sum(...=LIABILITY)` | prcp_data_reverse |
| 权益总额 | `sum(...=EQUITY)` | prcp_data_reverse |
| ROE 均值 | `avg(current_value where metric='ROE')` | prcp_metric_coefficient |
| CET1 均值 | `avg(... where metric='CET1')` | prcp_metric_coefficient |
| LCR 均值 | `avg(... where metric='LCR')` | prcp_metric_coefficient |

> 超阈值 KPI 标红（CE/KPI<阈值时显示向下红色箭头 + 标签）

### 3.2 5 指标 24 月趋势

- X 轴：M1 ~ M24
- Y 轴：每个指标独立纵轴
- 5 条折线（每指标专属颜色 + 阈值线）
- 阈值：
  - CET1: 8.5%
  - LCR: 100%
  - NSFR: 100%
  - ROE: 11%
  - ΔEVE: ±5

### 3.3 大类分布

- 左：余额饼图（4 大类：ASSET / LIABILITY / EQUITY / OFF_BALANCE）
- 右：节点数柱状图（带百分比标签）

### 3.4 节点 × 5 指标热力图

- 行：节点（40 个）
- 列：5 个指标
- 单元格颜色：按指标值映射（蓝绿黄红渐变）
- 顶部下拉：切换显示指标
- 左侧按大类过滤（全部 / 资产 / 负债 / 权益）
- 鼠标悬停：显示节点名 + 指标值 + 阈值状态

### 3.5 Top 10 节点（按余额）

- 表格列：节点编码 + 节点名称 + 大类 + 余额 + 5 指标
- 按余额倒序
- 行级 hover 高亮

### 3.6 风险预警列表

- 自动识别 5 大指标超阈值节点
- 严重度图标（绿/黄/红）
- 列：节点编码 + 节点名称 + 指标 + 当前值 + 阈值 + 差值

---

## 四、API 接口

### 4.1 GET /reverse-dashboard/options

```json
{
  "default": {
    "scheme_code": "2026",
    "run_id": 7,
    "date_offset": 1
  },
  "schemes": [
    {"scheme_code": "2026", "scheme_name": "2026年经营计划反算", "coa_scheme_id": 6, "latest_run_id": 7, "latest_run_status": "SUCCESS"}
  ]
}
```

### 4.2 GET /reverse-dashboard/runs?scheme_code=2026

```json
{
  "items": [
    {"id": 7, "run_code": "RUN_2026_001", "status": "SUCCESS", "start_at": "...", "duration_sec": 12.3, "optimal_value": 0.92}
  ]
}
```

### 4.3 GET /reverse-dashboard/dates?scheme_code=2026&run_id=7

```json
{
  "items": [
    {"date_offset": 1, "data_date": "2026-01-01"},
    ...
    {"date_offset": 24, "data_date": "2027-12-01"}
  ]
}
```

### 4.4 GET /reverse-dashboard/snapshot?scheme_code=2026&run_id=7&date_offset=1

**完整 payload 结构**：

```json
{
  "scheme_code": "2026",
  "scheme_name": "2026年经营计划反算",
  "coa_scheme_code": "ZXCOA_V1",
  "coa_scheme_name": "账户册总表_v7（ZXCOA）",
  "run_id": 7,
  "run_code": "RUN_2026_001",
  "date_offset": 1,
  "data_date": "2026-01-01",
  "base_data_date": "2025-12-31",
  "horizon_months": 24,
  "kpi": {
    "total_nodes": 40,
    "with_metrics": 40,
    "asset_total": 123467.76,
    "liability_total": 79108.85,
    "equity_total": 5232.1,
    "metric_avg": {"ROE": 16.928, "CET1": 11.03, "LCR": 150.2, "NSFR": 108.05, "DELTA_EVE": -2.55}
  },
  "category_distribution": {
    "by_count":   {"ASSET": 25, "LIABILITY": 14, "EQUITY": 1, "OFF_BALANCE": 0},
    "by_balance": {"ASSET": 123467.76, "LIABILITY": 79108.85, "EQUITY": 5232.1, "OFF_BALANCE": 0}
  },
  "trend": {
    "months": ["M1", "M2", ..., "M24"],
    "metrics": {
      "ROE":      [13.84, 13.91, ..., 16.93],
      "CET1":     [11.03, 11.08, ..., 11.62],
      "LCR":      [150.20, 150.45, ..., 153.18],
      "NSFR":     [108.05, 108.13, ..., 109.39],
      "DELTA_EVE": [-2.55, -2.61, ..., -4.55]
    }
  },
  "node_matrix": [
    {"node_code": "ZX_A001", "node_name": "总资产", "category": "ASSET",
     "current_balance": 2139.08, "weighted_rate": 0.035,
     "metric_values": {"ROE": 12.5, "CET1": 11.2, "LCR": 150.0, "NSFR": 108.5, "DELTA_EVE": -3.2}},
    ... 40 行
  ],
  "top_nodes": [...Top 10 by balance...],
  "risk_alert_total": 0,
  "risk_alerts": []
```

---

## 五、数据库表依赖（5 张）

| 表 | 用途 |
|----|------|
| `prcp_reverse_scheme` | 反算方案（rev_id / coa_scheme_id / base_data_date / horizon_months） |
| `prcp_reverse_run` | 运行记录（run_id / status / start_at / duration_sec / optimal_value） |
| `prcp_data_reverse` | 反算结果（current_balance / weighted_rate / 64+64 桶） |
| `prcp_metric_coefficient` | 5 指标值（current_value × 节点 × 月份） |
| `prcp_coa_node` | 节点元数据（node_code / node_name / path） |

---

## 六、风险阈值（可在代码调整）

| 指标 | 阈值 | 监管依据 |
|------|------|----------|
| CET1 | ≥ 8.5% | 银保监 |
| LCR | ≥ 100% | 银保监 |
| NSFR | ≥ 100% | 银保监 |
| ROE | ≥ 11% | 行业参考 |
| \|ΔEVE\| | ≤ 5 | 内部参考 |

---

## 七、部署清单

| 类型 | 文件 |
|------|------|
| Router | `backend/app/routers/reverse_dashboard.py`（4 endpoint） |
| 前端 API | `frontend/src/api/index.ts`（追加 reverseDashboardApi） |
| 前端页面 | `frontend/src/pages/ReverseDashboard.tsx` |
| 前端路由 | `frontend/src/App.tsx`（/dashboard → ReverseDashboard） |
| 前端菜单 | `frontend/src/layouts/MainLayout.tsx`（删除旧 12 项，已升为首页） |
| 演示数据 | `backend/scripts/seed_2026_demo.py`（造 960+4800 行） |

## 八、Bug 修复（部署期间发现）

1. **列名错误**：`prcp_reverse_scheme` 用 `data_date` 不是 `base_data_date`
2. **dict 索引错位**：SELECT 多了列导致 r[] 错位
3. **列名不存在**：`prcp_reverse_run` 没有 `row_count` / `created_at`，改用 `start_at` / `end_at` / `duration_sec`
4. **uvicorn .pyc 缓存**：每次修改必须删 `__pycache__/reverse_dashboard.cpython-312.pyc`
5. **pkill 转义失败**：用 `kill -9 PID` 直接杀
6. **名称反显**：coa_scheme_code + coa_scheme_name 一起显示（v3.1）