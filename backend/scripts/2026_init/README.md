# PRCP 2026 初始化 - 指标/模型/测算/铺底数据

> 数据库: `prcp_db` (MySQL 8.0, InnoDB, utf8mb4)
> 数据日期基期: 2025-12-31 (中信银行 2025 年度披露日)
> 创建时间: 2026-10-20

## 📋 目录结构

```
2026_init/
├── 00_setup_schema.sql              # 建表语句 (10 张表)
├── 01_seed_kpi_scheme_2026.sql     # 指标管理 (SCH_REG_2026)
├── 02_seed_models.sql              # 模型管理 (DNN_REG/ACO_OPT/NLS_REG)
├── 03_seed_sim_scheme.sql          # 测算方案 (SCS_2026) + 铺底 (5 指标 × 16 月)
├── seed_all.py                      # Python 一键执行入口
├── build_config_template.py         # 生成 Excel 配置模版
└── PRCP_2026_配置模版.xlsx          # 配置 Excel 模版 (6 Sheets)
```

## 🚀 快速开始

### 1. 一键执行所有 SQL

```bash
cd C:\银行经营\PRCP\backend\scripts\2026_init
python seed_all.py
```

可选参数：
- `--dry-run`: 仅打印 SQL，不执行
- `--only 00 01 02`: 只执行指定编号
- `--skip-verify`: 跳过验证步骤

### 2. 单文件执行

```bash
# 仅建表
mysql -u prcp -pPrcp@2026 prcp_db < 00_setup_schema.sql

# 仅导入指标方案
mysql -u prcp -pPrcp@2026 prcp_db < 01_seed_kpi_scheme_2026.sql
```

### 3. 重新生成配置模版

```bash
python build_config_template.py
```

## 📊 内容概览

### 一、指标管理 (SCH_REG_2026)
- 5 大监管指标: LCR / NSFR / EVE / CET1 / ROE
- 每个指标 v12b 23 段评分规则 (0-500 分制)
- 评分段位: 红线(0分) + 危险/安全 + 过优减分 + 适度最优(500分)

### 二、模型管理
| 模型代码 | 算法 | 业务域 | 参数数 |
|---|---|---|---|
| DNN_REG | 深度神经网络 | 监管资本 | 13 |
| ACO_OPT | 蚁群优化 | 资产负债 | 12 |
| NLS_REG | 非线性求解 | 定价估值 | 12 |

### 三、测算方案 (SCS_2026)
- 关联账户册方案: ZX_COA (中信银行 2025)
- 15 末级节点 (12 资产 + 3 负债)
- 24 月滚动测算
- 默认模型: NLS_REG (V1_BASELINE)

### 四、铺底数据
- 5 指标 × 15 节点 × 16 月 (示例: 80 条, 完整: 1200 条)
- 包含基期值 + 未来 1-5 年预测值
- 数据日期: 2025-12-31 ~ 2027-03-31

## 🔗 关联关系

```
prcp_kpi_scheme (SCH_REG_2026)
    ├── prcp_kpi_definition (5 个 REG_*)
    │       └── prcp_kpi_score_rule (5 套 v12b 规则)
    │               └── prcp_kpi_score_segment (5 × 23 = 115 段)
    └── prcp_kpi_value (基期实测值)

prcp_model (DNN_REG/ACO_OPT/NLS_REG)
    └── prcp_model_version (V1_BASELINE)
            └── prcp_model_param (12-13 个参数)

prcp_coa_scheme (ZX_COA)
    └── prcp_coa_node (57 节点)

prcp_sim_scheme (SCS_2026)
    ├── prcp_sim_scheme_node (15 配置)
    └── prcp_sim_run (24 月滚动)

prcp_metric_coefficient (铺底数据)
    └── 关联 scheme_code + node_code + metric_code
```

## 📈 验证

`seed_all.py` 会在最后打印各表行数验证：

| 表名 | 期望行数 |
|---|---|
| 指标方案 | 1 |
| KPI 定义 | 5 |
| 评分规则 | 5 |
| 评分段位 | 115 |
| 模型总数 | 3 |
| 模型版本 | 3 |
| 参数明细 | 37 |
| 账户册方案 | 1 |
| 账户册节点 | 15 (示例) |
| 测算方案 | 1 |
| 测算节点 | 15 |
| 铺底系数 | 80 (示例) |

## ⚠️ 注意事项

1. **幂等性**: 所有 SQL 都支持重复执行 (UPDATE/INSERT IGNORE)
2. **数据日期**: 2025-12-31 是基期，铺底覆盖 2025-12-31 ~ 2027-03-31 (16 月)
3. **FK 约束**: sim_scheme → coa_scheme, kpi_scheme → kpi_definition
4. **软删除**: 默认 `is_deleted=0`，删除改为 1
5. **硬编码 scheme_id=1**: SCH_REG_2026 默认为 id=1，修改需同步所有 SQL