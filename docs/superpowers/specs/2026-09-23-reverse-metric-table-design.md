# PRCP 反算指标结果表 — 设计文档

> 文档版本: v1.0  |  日期: 2026-09-23  |  作者: PRCP WorkBuddy Agent
> 对应模块: 数据维护 → 11. 反算指标结果表 (`/reverse-metric-table`)

---

## 一、设计目标

把**反算方案 × Run × 预测月份**对应的**每个账户册**上挂的**5 个指标值**（来自 prcp_metric_coefficient）以表格形式集中展示。

| 维度 | 设计 |
|------|------|
| **查询条件** | 复用 9 号反算结果查询（反算方案 + Run + 预测月份） |
| **数据来源** | 节点列表（prcp_coa_node）+ 5 指标值（prcp_metric_coefficient）+ 数据日期（prcp_data_reverse） |
| **行** | 反算方案绑定的账户册节点（40 个） |
| **列** | 账户册编码 / 账户册名称 / 大类 / **5 个指标列** + 底部合计行 |
| **联动** | 指标类型可选（缺省 5 个：ROE / CET1 / LCR / NSFR / ΔEVE） |
| **导出** | 一键 CSV 导出 |

---

## 二、数据来源联动

```
prcp_reverse_scheme
    ↓ coa_scheme_id
prcp_coa_node           (40 个节点)
    ↓ node_code, scheme_code
prcp_metric_coefficient (5 指标 × 当前期值)
    ↓ data_date
prcp_data_reverse (scheme_code, run_id, date_offset → data_date)
```

**核心逻辑**：根据反算方案 + Run + 月份，从 `prcp_data_reverse` 取 data_date，再从 `prcp_metric_coefficient` 取该日期下每节点的 5 指标值。

---

## 三、API 接口

### GET /prcp/api/metric-coefficient/reverse-table

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scheme_code` | string | ✅ | 反算方案编码 |
| `run_id` | int | ❌ | 缺省取最新 SUCCESS |
| `date_offset` | int | ❌ | 预测月份（M1..M24，默认 1） |
| `metric_types` | string | ❌ | 逗号分隔的指标类型 key，缺省 = ROE/CET1/LCR/NSFR/DELTA_EVE |

**返回**：

```json
{
  "scheme_code": "2026",
  "scheme_name": "2026年经营计划反算",
  "coa_scheme_code": "ZXCOA_V1",
  "coa_scheme_name": "账户册总表_v7（ZXCOA）",
  "run_id": 7,
  "data_date": "2026-01-01",
  "date_offset": 1,
  "metric_types": ["ROE", "CET1", "LCR", "NSFR", "DELTA_EVE"],
  "metric_units": {"ROE": "PERCENT", "CET1": "PERCENT", ...},
  "total_nodes": 40,
  "total_with_metrics": 40,
  "rows": [
    {
      "coa_node_id": 1,
      "node_code": "ZX_A001",
      "node_name": "总资产",
      "node_level": 1,
      "category": "ASSET",
      "metric_values": {"ROE": 12.5, "CET1": 11.2, "LCR": 150.0, "NSFR": 108.5, "DELTA_EVE": -3.2},
      "metric_ids": {"ROE": "ZXCOA_V1_ZX_A001_ROE_20260101", ...}
    }
  ]
}
```

**节点分类规则**（依据 node_code 前缀）：

| 前缀 | 分类 |
|------|------|
| ZX_A | ASSET（资产） |
| ZX_L | LIABILITY（负债） |
| ZX_E | EQUITY（权益） |
| ZX_OB / 路径含 /L1_表外 | OFF_BALANCE（表外） |
| 其他 | OTHER |

---

## 四、前端页面设计

### 4.1 顶部筛选条（与 9 号一致）

```
┌──────────────────┬──────────────────┬──────────────────┐
│ 反算方案 [▼ 2026] │ 运行记录 [▼ Run7] │ 预测月份 [▼ M1]  │
└──────────────────┴──────────────────┴──────────────────┘
[🔍 查询] [📤 导出 CSV]
```

### 4.2 信息条（5 个 Tag）

```
📅 数据日期: 2026-01-01   🏷️ 账户册方案: ZXCOA_V1 账户册总表_v7（ZXCOA）
📊 覆盖节点: 40/40   ✅ 已挂指标: 40/40
```

### 4.3 5 个指标小卡片（顶部）

```
┌────────┬────────┬────────┬────────┬────────┐
│   ROE  │  CET1  │  LCR   │  NSFR  │  ΔEVE  │
│ 13.84% │ 11.03% │ 150.2% │ 108.05%│ -2.55  │
│ 40/40 │ 40/40 │ 40/40  │ 40/40  │ 40/40  │
└────────┴────────┴────────┴────────┴────────┘
```

每卡片显示：当前月份 5 个节点的平均值 + 覆盖节点数 / 总节点数

### 4.4 主表格

| 列 | 宽度 | 内容 |
|----|------|------|
| 账户册编码 | 150 | code（按节点层级颜色） |
| 账户册名称 | 180 | name |
| 大类 | 80 | Tag（按分类着色） |
| ROE | 100 | 数值（绿色/红色） |
| CET1 | 100 | 数值 |
| LCR | 100 | 数值 |
| NSFR | 100 | 数值 |
| ΔEVE | 100 | 数值（负值红色） |
| 数据日期 | 110 | yyyy-mm-dd |
| ID | 280 | {scheme_code}_{node_code}_{metric_code}_{YYYYMMDD} |

### 4.5 底部合计行（5 指标平均）

```
合计 | —— | —— | 13.84 | 11.03 | 150.20 | 108.05 | -2.55
```

---

## 五、E2E 验证

公网实测：

```
scheme=2026 coa_scheme=ZXCOA_V1
M1 (2026-01-01): total_nodes=40, with_metrics=40
M12 (2026-12-01): total_nodes=40, with_metrics=40
ROE M1=13.84% → M12=14.39%（递增）
ΔEVE M1=-2.55 → M12=-3.10（负向加深）
```

---

## 六、部署清单

| 类型 | 文件 |
|------|------|
| Router | `backend/app/routers/metric_coefficient.py`（追加 GET /reverse-table） |
| 前端 API | `frontend/src/api/index.ts`（追加 metricCoefficientApi.reverseTable） |
| 前端页面 | `frontend/src/pages/ReverseMetricTable.tsx` |
| 前端路由 | `frontend/src/App.tsx` |
| 前端菜单 | `frontend/src/layouts/MainLayout.tsx`（11 号项） |
| 演示数据 | `backend/scripts/seed_metric_coefficient_demo.sql` |

## 七、Bug 修复

1. **URL-encode 中文 ID**（已在 e2e 阶段修复）
2. **STR_TO_DATE 转义**：原用 `%%Y-%%m-%%d` 在 SQLAlchemy text() 里被双重转义成 `%%%%`，改为单 `%`