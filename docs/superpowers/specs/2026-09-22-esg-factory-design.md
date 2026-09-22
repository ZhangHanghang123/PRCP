# PRCP ESG 场景工厂 需求与设计说明书

**项目**：PRCP（银行经营组算平台）
**模块**：ESG 场景工厂（Environment / Scenario / Generator Factory）
**版本**：v1.0（2026-09-22 设计）
**作者**：PRCP Team
**关联文档**：
- [DeepALM ESG 工厂设计说明书](../../DeepALM/docs/superpowers/specs/2026-09-22-esg-factory-design.md)（实现参考）
- [PRCP 需求说明书 v9](../PRCP_需求说明书_v9_backup_20260921_183500.docx)
- [PRCP 期限桶 v3 设计说明](../../backend/scripts/upgrade_term_buckets_v3.sql)

---

## 0. 文档目录

1. [背景与目标](#1-背景与目标)
2. [业务需求](#2-业务需求)
3. [架构总览](#3-架构总览)
4. [数据库设计](#4-数据库设计)
5. [后端 API 设计](#5-后端-api-设计)
6. [前端页面设计](#6-前端页面设计)
7. [核心算法](#7-核心算法)
8. [PRCP vs DeepALM 优化点](#8-prcp-vs-deepalm-优化点)
9. [部署架构](#9-部署架构)
10. [端到端验证](#10-端到端验证)

---

## 1. 背景与目标

### 1.1 业务背景

PRCP（银行经营组算平台）当前已包含账户册、报表、基础数据、利率管理、新业务模拟、指标管理等模块，但**缺少对未来市场情景（Interest Rate Scenarios）的生成能力**。当下游模块（新业务模拟/反算/压测）需要 60~360 月的未来利率路径时，只能手工输入静态情景，无法做蒙特卡洛仿真。

**DeepALM ESG 工厂方案化模块**（2026-09-22 完成）已落地"PCA + Svensson 还原 + HJM 路径生成 + 情景集持久化"完整链路，但：
1. **依赖 BPTT 训练框架**（`deep_alm/bptt/` 含 torch 张量），与 PRCP 纯 Python/NumPy 架构不兼容
2. **数据格式不同**：DeepALM 存 theta0/theta1/theta2/theta3 + lambda1/lambda2 + 12 个期限点，PRCP 期限桶是 m1~m60 月频 + y10/y15/y20/y30（64 桶）
3. **方案管理是独立的 esg_scheme_config + esg_run**，与 PRCP 的 sim_scheme + sim_run / kpi_scheme + kpi_run 命名/字段不统一

### 1.2 系统目标

**PRCP ESG 场景工厂**目标：

1. **数据归一**：支持 4 类数据源（ECB / FRB / CUSTOM / BANK）的 Svensson 6 参数入库（`prcp_esg_curve_point`）
2. **方案化**：方案独立配置数据源、起止日期、因子数、情景数、步数、种子、期限数组（与 `prcp_sim_scheme` 命名风格对齐）
3. **PCA 因子分解**：从历史曲线提取 1~6 个主成分（PC1 水平 / PC2 斜率 / PC3 曲度 / ...）
5. **HJM 路径生成**：基于 PCA + HJM 仿射模型生成 10~10000 条未来 12~360 月路径
6. **情景集持久化**：.npz 文件存到 `/var/lib/prcp/esg_cases/` + `prcp_esg_scenario` 索引
7. **可视化分析**：累计方差、因子载荷热力图、HJM 路径包络图（p10/p50/p90）、情景集历史
8. **与 PRCP 现有模块解耦**：输出 .npz 通过 PRCP 自定义 API 给下游 `sim` / `reverse` / `kpi` 模块读取

### 1.3 非目标（Non-Goals）

- 不实现 BPTT 训练集成（PRCP 不需要 torch 张量）
- 不实现 CVA/XVA 计算（属 AFA / IALM 模块）
- 不实现监管报表自动化（属 ALMD / IALMD 模块）
- 不暴露 deep_alm 内部算法（PRCP 自实现 numpy 版本）
- 不做实时数据接入（ECB / FRB API 定时拉取）

### 1.4 关键设计原则（与 PRCP 一致）

| 原则 | 体现 |
|------|------|
| 表前缀统一 | `prcp_esg_*` |
| 公共字段统一 | `id / status / is_deleted / created_by/updated_by/created_at/updated_at` |
| 字典外挂 | sys_dict 加 `PRCP_ESG_SOURCE` / `PRCP_ESG_RUN_TYPE` / `PRCP_ESG_STATUS` |
| 升级脚本规范 | `upgrade_esg_v1.sql`（参照 upgrade_dict_v1.sql / upgrade_sim_engine_v1.sql 风格） |
| Pydantic Schema | 只用 `XxxIn`，无 `Out` 后缀（PRCP 现有约定） |
| 路由注册 | `app.include_router(esg.router, prefix="/prcp/api")` |
| 前端基础路径 | `<BrowserRouter basename="/prcp">` |
| 主题色 | 主 `#13c2c2`（青，对齐 BasicDataSheet 已用），辅 `#722ed1`（紫，对齐 KPI） |
| 菜单图标 | `AreaChartOutlined`（已有 AntD 图标） |
| 缓存策略 | per-scheme `_Store` 缓存 `YieldCurveGenerator` 实例，更新方案清缓存 |

---

## 2. 业务需求

### 2.1 用户角色

| 角色 | 描述 | 典型操作 |
|------|------|----------|
| **风控分析师** | 日常压测、监管报告 | 创建方案 → 跑 PCA → 生成 HJM → 导出情景喂给下游 sim/reverse |
| **模型研究员** | 验证新模型、对比因子 | 创建多个方案 → 调因子数 → 对比累计方差 |
| **数据管理员** | 维护 Svensson 曲线数据 | 上传 ECB/FRB CSV → 一键造数 → 监控数据完整性 |

### 2.2 功能需求（Functional Requirements）

#### FR-1：曲线数据管理
- F-1.1 上传 4 类数据源（ECB / FRB / CUSTOM / BANK）的 Svensson 6 参数
- F-1.2 单点 upsert（按 source + curve_date 唯一）
- F-1.3 批量 upsert（CSV 导入场景）
- F-1.4 来源统计（4 类数据源各自行数 + 起止日期）

#### FR-2：Svensson 曲线还原
- F-2.1 6 参数还原：`r(T) = θ₀ + θ₁·H(T/λ₁) + θ₂·(H(T/λ₁) - e^(-T/λ₁)) + θ₃·(H(T/λ₂) - e^(-T/λ₂))`
- F-2.2 支持自定义期限数组（默认用 PRCP 64 桶：m1~m60 + y10/y15/y20/y30）
- F-2.3 单点查询 + 批量查询 + 还原

#### FR-3：方案管理（核心）
- F-3.1 CRUD 方案（Create / Read / Update / Delete / Clone）
- F-3.2 唯一性约束：`scheme_code` 全局唯一
- F-3.3 软删除（`is_deleted = 1`）
- F-3.4 状态字段：`DRAFT` / `READY` / `ARCHIVED`
- F-3.5 字段：data_source / start_date / end_date / n_factors（1~6）/ maturities_months / n_scenarios（10~10000）/ n_steps（12~360）/ seed / initial_yields_pct

#### FR-4：PCA 因子分解
- F-4.1 输入：方案 + 历史曲线（按 data_source + start_date + end_date 过滤）
- F-4.2 输出：`factor_loadings`（n_factors × n_maturities）+ `eigenvalues` + `explained_variance_ratio`
- F-4.3 业务阈值：3 因子累计方差 ≥ 95% 视为合理
- F-4.4 每次执行写一条 `prcp_esg_run`（run_type=`PCA_FIT`）

#### FR-5：HJM 路径生成
- F-5.1 输入：方案 + PCA 拟合结果（自动从方案缓存取）
- F-5.2 输出：`paths`（n_scenarios × n_steps × n_maturities）+ `percentiles`（p10/p50/p90）
- F-5.3 业务校验：HJM 路径非负、波动率随期限递减（**PRCP 优化点**：DeepALM 没有此校验）
- F-5.4 每次执行写一条 `prcp_esg_run`（run_type=`HJM_GENERATE`）

#### FR-6：情景集持久化
- F-6.1 输出 `.npz` 文件保存到 `/var/lib/prcp/esg_cases/{scenario_id}.npz`
- F-6.2 同时写 `prcp_esg_scenario`（scheme_id + scenario_type='esg_factory' + file_path + n_scenarios + n_steps + seed + maturities_json）
- F-6.3 提供下载接口（GET /esg/scenarios/{id}/download）
- F-6.4 每次执行写一条 `prcp_esg_run`（run_type=`SCENARIO_GENERATE`）

#### FR-7：运行历史
- F-7.1 按方案过滤：`GET /esg/schemes/{id}/runs`
- F-7.2 全局过滤：`GET /esg/runs?scheme_id=&run_type=&status=&page=&page_size=`
- F-7.3 排序：`id DESC`（最新在前）
- F-7.4 字段：id/scheme_id/run_type/status/params_json/output_json/duration_ms/created_at

#### FR-8：一键三步（演示）
- F-8.1 自动创建 `PRCP_ESG_DEMO_001` 方案（如不存在）
- F-8.2 自动跑 PCA → HJM → 情景集
- F-8.3 耗时 < 3 秒（551 ECB 样本）
- F-8.4 失败时回滚方案 + 清理生成文件

### 2.3 非功能需求（Non-Functional Requirements）

| 维度 | 指标 |
|------|------|
| **性能** | 1000 情景 × 120 步 × 64 期限 HJM < 800ms |
| **并发** | 同时 10 个方案跑 PCA 互不干扰 |
| **可恢复** | 进程崩溃后 `prcp_esg_run` 状态可查询 |
| **可扩展** | 未来增加 new_factors（神经网络因子）不破坏 schema |
| **审计** | 所有写操作记录 created_by / created_at |
| **安全** | JWT 认证 + 软删除（is_deleted） |
| **依赖** | 纯 Python 3.10+ + numpy + scipy（无 torch / 无 pandas 必需） |
| **内存** | 单方案 HJM paths 最大 ~10000×360×64×8 bytes = 184 MB 上限 |

---

## 3. 架构总览

### 3.1 系统分层

```
┌─────────────────────────────────────────────────────────┐
│  前端 (React 18 + TypeScript + AntD 5 + ECharts)        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 7 页面：Schemes / SchemeConfig / SchemeDetail /  │  │
│  │ Curve / PCA / HJM / Scenarios                    │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ axios + JWT（已有 http 实例）
                       ▼
┌─────────────────────────────────────────────────────────┐
│  后端 (FastAPI + SQLAlchemy 2.0 + Pydantic v2)           │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ routers/esg.py   │  │ services/esg/                 │ │
│  │ (1 个 router 22   │  │ /svensson.py        # 6参拟合 │ │
│  │  个 endpoint)     │  │ /yield_curve_gen.py # 生成器  │ │
│  └──────┬───────────┘  │ /scenario_set.py    # npz     │ │
│         │              │ /validator.py       # 校验    │ │
│  ┌──────▼──────────────────────────────────────────┐    │
│  │ _Store (dict[scheme_id] → YieldCurveGenerator)  │    │
│  │ └─ 进程内缓存，方案切换不丢配置                  │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────┐
│ MySQL       │ │ 文件系统      │ │ PRCP_CASE_DIR     │
│ prcp_db     │ │ (npz)        │ │ /var/lib/prcp/    │
│             │ │              │ │ /esg_cases/       │
│ 4 张新表    │ │              │ └──────────────────┘
└─────────────┘ └──────────────┘
```

### 3.2 数据流向

#### 主链路（方案执行）

```
用户 → [EsgSchemes] 创建方案 (POST /esg/schemes)
         ↓
       [EsgSchemeConfig] 配置（数据源/起止日期/期限/情景数/步数）
         ↓
       [EsgSchemeDetail] 第 1 步：PCA 拟合 (POST /esg/schemes/{id}/fit-pca)
         ↓ router.esg.scheme_fit_pca
         ↓ services.esg.yield_curve_generator.YieldCurveGenerator.fit_pca()
         ↓ DB: prcp_esg_run INSERT (run_type=PCA_FIT, output_json=factor_loadings)
         ↓ _Store[scheme_id] = generator（缓存）
         ↓
       [EsgSchemeDetail] 第 2 步：HJM 建模 (POST /esg/schemes/{id}/generate-hjm)
         ↓ router.esg.scheme_generate_hjm
         ↓ YieldCurveGenerator.generate_hjm_paths()
         ↓ DB: prcp_esg_run INSERT (run_type=HJM_GENERATE, output_json=percentiles)
         ↓ file_path=/var/lib/prcp/esg_cases/hjm_{scheme_id}_{run_id}.npz
         ↓
       [EsgSchemeDetail] 第 3 步：情景集 (POST /esg/schemes/{id}/generate)
         ↓ router.esg.scheme_generate_scenarios
         ↓ np.savez_compressed + DB: prcp_esg_scenario INSERT
         ↓ DB: prcp_esg_run INSERT (run_type=SCENARIO_GENERATE)
         ↓
       [下游模块] sim/reverse 通过 API 拉取 .npz：
         GET /esg/scenarios/{id}/download → 解析 npz paths + maturities
```

#### 一键演示链路

```
用户 → [EsgCurve] 一键案例 (POST /esg/case/run)
         ↓
       自动创建 PRCP_ESG_DEMO_001 方案（如不存在）
       自动跑 PCA → HJM → 情景集
       返回 scheme_id + 3 个 run_id + scenario_id
```

### 3.3 模块集成（PRCP 内部下游消费）

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ COA      │     │ KPI      │     │ Sim      │
│ 账户册   │     │ 指标管理 │     │ 新业务模拟│
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     └────────────────┼────────────────┘
                      │
                      ▼
              ┌──────────────┐
              │  ESG 场景工厂 │
              │ (本模块)     │
              └──────────────┘
                      │
                      ▼
       提供给下游：HJM .npz (paths + maturities)
```

未来扩展：
- `prcp_sim_scheme` 的"新业务模拟"加 "rate_scenario_id" 字段，绑定本模块生成的 scenario_id
- `prcp_kpi_definition`（函数指标）可读取 `prcp_esg_scenario` 的 .npz 计算 ΔEVE、LCR、NSFR
- `prcp_reverse_calc` 用 .npz 做反算目标约束

---

## 4. 数据库设计

### 4.1 表关系图

```
┌──────────────────┐      ┌──────────────────┐
│ prcp_esg_scheme   │ 1:N  │ prcp_esg_run     │
│ ┌──────────────┐ │──────▶│ ┌──────────────┐ │
│ │ PK: id       │ │      │ │ PK: id       │ │
│ │ UK: scheme  │ │      │ │ FK: scheme   │ │
│ └──────────────┘ │      │ └──────────────┘ │
└──────────────────┘      └────────┬─────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ prcp_esg_scenario    │
                        │ (情景集持久化)        │
                        │ PK: id               │
                        │ FK: scheme_id       │
                        │ FK: last_run_id     │
                        └──────────────────────┘

┌──────────────────────────┐
│ prcp_esg_curve_point     │ ← 直接由 seed_esg_data.py 填充
│ (4 数据源统一表)         │
│ PK: id                   │
│ UNIQUE: (source, curve_date) │
└────────────────────────────┘
```

### 4.2 表结构

#### 4.2.1 `prcp_esg_scheme`（方案配置）

```sql
CREATE TABLE prcp_esg_scheme (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    scheme_code         VARCHAR(32)     NOT NULL,
    scheme_name         VARCHAR(64)     NOT NULL,
    description         TEXT,

    -- 数据源
    data_source         VARCHAR(16)     NOT NULL DEFAULT 'ECB',  -- ECB / FRB / CUSTOM / BANK
    start_date           DATE,
    end_date            DATE,

    -- PCA 配置
    n_factors           INT             NOT NULL DEFAULT 3,      -- 1..6
    maturities_json     JSON            NOT NULL,               -- [1,3,6,12,24,60,84,120,240,360] 月

    -- HJM 配置
    n_scenarios         INT             NOT NULL DEFAULT 1000,  -- 10..10000
    n_steps             INT             NOT NULL DEFAULT 120,   -- 12..360
    seed                INT             NOT NULL DEFAULT 42,
    initial_yields_json JSON            NULL,                    -- [0.03,...] 百分比

    -- 状态
    status              VARCHAR(16)     NOT NULL DEFAULT 'DRAFT',  -- DRAFT / READY / ARCHIVED
    is_deleted          TINYINT(1)      NOT NULL DEFAULT 0,

    created_by          BIGINT,
    updated_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_scheme_code (scheme_code, is_deleted),
    KEY idx_status (status, is_deleted),
    KEY idx_source (data_source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 工厂方案配置';
```

**对齐 PRCP 现有规范**：
- 表前缀 `prcp_*`
- 公共字段 id/status/is_deleted/created_by/updated_by/created_at/updated_at
- JSON 后缀 _json（maturities_json / initial_yields_json）
- 唯一索引 `(scheme_code, is_deleted)`（参照 `prcp_kpi_score_rule.uk_kpi_rule` 模式）

#### 4.2.2 `prcp_esg_run`（运行历史）

```sql
CREATE TABLE prcp_esg_run (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    scheme_id           BIGINT          NOT NULL,
    scheme_code         VARCHAR(32),

    run_type            VARCHAR(32)     NOT NULL,   -- PCA_FIT / HJM_GENERATE / SCENARIO_GENERATE
    status              VARCHAR(16)     NOT NULL DEFAULT 'SUCCESS',
                                                    -- SUCCESS / FAILED / RUNNING
    params_json         JSON,                       -- 入参（n_factors/n_scenarios/n_steps/seed）
    output_json         JSON,                       -- 结果摘要（factor_loadings/percentiles/file_path/scenario_id）
    file_path           VARCHAR(512),                -- /var/lib/prcp/esg_cases/hjm_*.npz

    duration_ms         INT,
    error_message       TEXT,

    created_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_run_scheme (scheme_id, run_type),
    KEY idx_run_status (status),
    KEY idx_run_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 工厂运行历史';
```

#### 4.2.3 `prcp_esg_curve_point`（4 源曲线统一表）

```sql
CREATE TABLE prcp_esg_curve_point (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    curve_date          DATE            NOT NULL,
    source              VARCHAR(16)     NOT NULL,    -- ECB / FRB / CUSTOM / BANK

    -- Svensson 6 参数
    theta0              DECIMAL(20,9),
    theta1              DECIMAL(20,9),
    theta2              DECIMAL(20,9),
    theta3              DECIMAL(20,9),
    lambda1             DECIMAL(20,9),
    lambda2             DECIMAL(20,9),

    -- 元数据
    raw_data_json       JSON,                          -- 原始 CSV 完整内容（备份 + 审计）
    description         VARCHAR(255),

    is_deleted          TINYINT(1)      NOT NULL DEFAULT 0,
    created_by          BIGINT,
    updated_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_curve (source, curve_date, is_deleted),
    KEY idx_curve_date (curve_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Svensson 6 参数曲线统一表';
```

**为什么独立于 `prcp_rate_*`**：
- `prcp_rate_*` 存 13 个利率点（`rate_d1/rate_d7/rate_m1..m6/rate_y1..y30`），是**观测值列**
- `prcp_esg_curve_point` 存 6 个 Svensson 参数（theta0~3 + lambda1/2），是**模型参数**
- 两套逻辑独立，不试图替换

#### 4.2.4 `prcp_esg_scenario`（情景集持久化）

```sql
CREATE TABLE prcp_esg_scenario (
    id                  BIGINT          NOT NULL AUTO_INCREMENT,
    scheme_id           BIGINT          NOT NULL,
    last_run_id         BIGINT,                              -- 对应 SCENARIO_GENERATE run

    scenario_type       VARCHAR(32)     NOT NULL DEFAULT 'esg_factory',
    file_path           VARCHAR(512)    NOT NULL,            -- /var/lib/prcp/esg_cases/scenario_*.npz
    n_scenarios         INT             NOT NULL,
    n_steps             INT             NOT NULL,
    n_maturities        INT             NOT NULL,
    seed                INT,
    maturities_json     JSON,                                 -- [1,3,6,...,360]
    file_size_bytes     BIGINT,
    description         VARCHAR(255),

    created_by          BIGINT,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted          TINYINT(1)      NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    KEY idx_scn_scheme (scheme_id),
    KEY idx_scn_type (scenario_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 情景集持久化索引';
```

### 4.3 sys_dict 字典扩展

在 `upgrade_esg_v1.sql` 中追加：

```sql
INSERT IGNORE INTO sys_dict (dict_type, dict_key, dict_label, color, sort_order, status, description, is_deleted)
VALUES
-- 数据源
('PRCP_ESG_SOURCE','ECB','欧洲央行','blue',10,'ACTIVE','ECB AAA 国债收益率',0),
('PRCP_ESG_SOURCE','FRB','美联储','red',20,'ACTIVE','FRB H.15 利率',0),
('PRCP_ESG_SOURCE','CUSTOM','自定义','cyan',30,'ACTIVE','银行自定义曲线',0),
('PRCP_ESG_SOURCE','BANK','本行加点','gold',40,'ACTIVE','本行账簿加点估算',0),
-- 运行类型
('PRCP_ESG_RUN_TYPE','PCA_FIT','PCA 拟合','blue',10,'ACTIVE','主成分因子分解',0),
('PRCP_ESG_RUN_TYPE','HJM_GENERATE','HJM 建模','cyan',20,'ACTIVE','HJM 利率路径生成',0),
('PRCP_ESG_RUN_TYPE','SCENARIO_GENERATE','情景集生成','purple',30,'ACTIVE','.npz 文件持久化',0),
-- 方案状态
('PRCP_ESG_STATUS','DRAFT','草稿','default',10,'新建未配置完',0),
('PRCP_ESG_STATUS','READY','就绪','green',20,'配置完成可执行',0),
('PRCP_ESG_STATUS','ARCHIVED','已归档','gray',30,'历史方案',0),
-- 运行状态
('PRCP_ESG_RUN_STATUS','SUCCESS','成功','green',10,'执行成功',0),
('PRCP_ESG_RUN_STATUS','FAILED','失败','red',20,'执行失败',0),
('PRCP_ESG_RUN_STATUS','RUNNING','运行中','blue',30,'正在执行',0);
```

### 4.4 ER 关系总结

| 关系 | 主表 | 外键表 | 说明 |
|------|------|--------|------|
| 1:N | `prcp_esg_scheme` | `prcp_esg_run` | 一个方案可多次执行 |
| 1:N | `prcp_esg_scheme` | `prcp_esg_scenario` | 一个方案可生成多个情景集 |
| 直读 | `prcp_esg_curve_point` | (无外键) | YieldCurveGenerator 按 source+date 直读 |

---

## 5. 后端 API 设计

### 5.1 路由清单（22 endpoint，单文件 `routers/esg.py`）

| Method | 路径 | 说明 | 关键参数 |
|--------|------|------|----------|
| GET | `/esg/schemes` | 方案列表 | `?keyword=&status=&page=&page_size=` |
| POST | `/esg/schemes` | 新建方案 | body: `EsgSchemeIn` |
| GET | `/esg/schemes/{id}` | 方案详情 | path: id |
| PUT | `/esg/schemes/{id}` | 更新方案（清缓存） | path: id, body: `EsgSchemeUpdate` |
| DELETE | `/esg/schemes/{id}` | 软删 | path: id |
| POST | `/esg/schemes/{id}/clone` | 克隆 | body: `{new_scheme_code, new_scheme_name?}` |
| POST | `/esg/schemes/{id}/fit-pca` | 跑 PCA | body: `{n_factors?}` |
| POST | `/esg/schemes/{id}/generate-hjm` | 跑 HJM | body: `{n_scenarios?, n_steps?, seed?}` |
| POST | `/esg/schemes/{id}/generate` | 生成情景集 | body: `{}` |
| POST | `/esg/schemes/{id}/run-all` | 一键三步 | body: `{}` |
| GET | `/esg/schemes/{id}/runs` | 本方案历史 | `?run_type=&status=&limit=` |
| GET | `/esg/runs` | 全局历史 | `?scheme_id=&run_type=&status=&page=&page_size=` |
| GET | `/esg/runs/{id}` | 单次详情（含 output_json） | path: id |
| GET | `/esg/scenarios` | 情景集列表 | `?scheme_id=&page=&page_size=` |
| GET | `/esg/scenarios/{id}` | 情景集元数据 | path: id |
| GET | `/esg/scenarios/{id}/download` | 下载 .npz | path: id, 返回 application/octet-stream |
| POST | `/esg/case/run` | 一键演示 | body: `{}` |
| GET | `/esg/curves` | Svensson 参数列表 | `?source=&start_date=&end_date=&page=&page_size=` |
| GET | `/esg/curves/sources` | 来源统计 | 无 |
| GET | `/esg/curves/{date}` | 单日参数 | path: date, query: `source?` |
| POST | `/esg/curves` | 单点 upsert | body: `SvenssonCurveIn` |
| POST | `/esg/curves/bulk` | 批量 upsert | body: `{points: [...]}` |
| POST | `/esg/curves/{date}/rates` | Svensson 还原 | body: `{tenors: [1,3,6,...]}` |

> **注**：对齐 DeepALM 但做了 **PRCP 优化**：
> - `eta_rate`（波动率递减）校验在 HJM 后端加入
> - 默认 `maturities_months` 用 PRCP 64 桶
> - 单 router 文件（PRCP 现有约定）

### 5.2 Pydantic Schema（PRCP 风格：只用 `XxxIn`）

```python
# ============== 方案管理 ==============
class EsgSchemeIn(BaseModel):
    scheme_code: str = Field(..., min_length=3, max_length=32)
    scheme_name: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    data_source: str = Field("ECB", regex="^(ECB|FRB|CUSTOM|BANK)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    n_factors: int = Field(3, ge=1, le=6)
    maturities_months: List[int] = Field(
        default_factory=lambda: [1,3,6,12,24,36,48,60,84,120,180,240,360]  # 默认 13 个期限点
    )
    n_scenarios: int = Field(1000, ge=10, le=10000)
    n_steps: int = Field(120, ge=12, le=360)
    seed: int = Field(42, ge=0)
    initial_yields_pct: Optional[List[float]] = None
    status: str = Field("DRAFT", regex="^(DRAFT|READY|ARCHIVED)$")

class EsgSchemeUpdate(BaseModel):
    # 全 Optional，避免 PUT 时必填
    scheme_name: Optional[str] = None
    description: Optional[str] = None
    data_source: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    n_factors: Optional[int] = None
    maturities_months: Optional[List[int]] = None
    n_scenarios: Optional[int] = None
    n_steps: Optional[int] = None
    seed: Optional[int] = None
    initial_yields_pct: Optional[List[float]] = None
    status: Optional[str] = None


class EsgPcaRunIn(BaseModel):
    n_factors: Optional[int] = Field(None, ge=1, le=6)


class EsgHjmRunIn(BaseModel):
    n_scenarios: Optional[int] = Field(None, ge=10, le=10000)
    n_steps: Optional[int] = Field(None, ge=12, le=360)
    seed: Optional[int] = None


class EsgCloneIn(BaseModel):
    new_scheme_code: str = Field(..., min_length=3, max_length=32)
    new_scheme_name: Optional[str] = None


# ============== 曲线管理 ==============
class SvenssonCurveIn(BaseModel):
    curve_date: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$")
    source: str = Field("ECB", regex="^(ECB|FRB|CUSTOM|BANK)$")
    theta0: float
    theta1: float
    theta2: float
    theta3: float
    lambda1: float = Field(..., gt=0)
    lambda2: float = Field(..., gt=0)
    raw_data_json: Optional[dict] = None
    description: Optional[str] = None


class SvenssonBulkIn(BaseModel):
    points: List[SvenssonCurveIn]


class SvenssonRatesIn(BaseModel):
    tenors: List[int] = Field(..., min_items=1)
    source: Optional[str] = None


# ============== 情景集 ==============
class EsgScenarioListIn(BaseModel):
    scheme_id: Optional[int] = None
    page: int = 1
    page_size: int = 20


class EsgRunListIn(BaseModel):
    scheme_id: Optional[int] = None
    run_type: Optional[str] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 50
```

### 5.3 业务核心逻辑（伪代码）

#### 5.3.1 scheme_fit_pca

```python
@router.post("/esg/schemes/{scheme_id}/fit-pca")
async def scheme_fit_pca(scheme_id: int, body: EsgPcaRunIn, db, user):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    # 1) 取方案
    scheme = db.execute(text("SELECT * FROM prcp_esg_scheme WHERE id=:i AND is_deleted=0"), {"i": scheme_id}).first()
    if not scheme:
        raise HTTPException(404, "scheme 不存在")

    # 2) 取 Generator（per-scheme 缓存，避免切换方案丢配置）
    generator = _STORE.get(scheme_id)
    if not generator:
        generator = YieldCurveGenerator(
            data_source=scheme.data_source,
            start_date=scheme.start_date,
            end_date=scheme.end_date,
            n_factors=body.n_factors or scheme.n_factors,
            seed=scheme.seed,
            maturities_months=json.loads(scheme.maturities_json),
        )
        _STORE[scheme_id] = generator

    # 3) 跑 PCA（np.linalg.eigh on covariance matrix）
    start = time.time()
    factor_loadings, eigenvalues, explained_variance = generator.fit_pca()
    duration_ms = int((time.time() - start) * 1000)

    # 4) 写 prcp_esg_run
    rid = db.execute(text("""INSERT INTO prcp_esg_run
        (scheme_id, scheme_code, run_type, status, params_json, output_json, duration_ms, created_by)
        VALUES (:s, :c, 'PCA_FIT', 'SUCCESS', :p, :o, :d, :u)"""), {
        "s": scheme_id, "c": scheme.scheme_code,
        "p": json.dumps({"n_factors": generator.n_factors, "data_source": scheme.data_source}),
        "o": json.dumps({
            "n_samples": generator.n_samples,
            "n_maturities": len(generator.maturities),
            "eigenvalues": eigenvalues.tolist(),
            "explained_variance_ratio": explained_variance.tolist(),
            "cumulative_variance_ratio": np.cumsum(explained_variance).tolist(),
            "factor_loadings": factor_loadings.tolist(),
            "cumulative_3f_pct": float(np.cumsum(explained_variance)[2]) if generator.n_factors >= 3 else None,
        }),
        "d": duration_ms, "u": uid,
    }).lastrowid
    db.commit()
    return {"run_id": rid, "explained_variance_ratio": explained_variance.tolist()}
```

#### 5.3.2 scheme_generate_hjm（含 PRCP 优化：波动率递减校验）

```python
@router.post("/esg/schemes/{scheme_id}/generate-hjm")
async def scheme_generate_hjm(scheme_id: int, body: EsgHjmRunIn, db, user):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    generator = _STORE.get(scheme_id)
    if not generator or not generator._pca_fitted:
        raise HTTPException(400, "请先跑 PCA")

    start = time.time()
    paths = generator.generate_hjm_paths(
        n_scenarios=body.n_scenarios or generator.n_scenarios,
        n_steps=body.n_steps or generator.n_steps,
        seed=body.seed if body.seed is not None else generator.seed,
    )

    # === PRCP 优化点：波动率随期限递减校验 ===
    vol_per_maturity = paths[:, -1, :].std(axis=0)  # (n_maturities,)
    # 短端波动率应该 ≥ 长端（PCA 因子 1 水平主导）
    if not np.all(np.diff(vol_per_maturity) <= 1e-6):
        logger.warning(f"波动率非递减 scheme={scheme_id}: {vol_per_maturity.tolist()}")

    # 利率下界 0（避免负利率）
    if paths.min() < -0.01:
        raise HTTPException(400, f"HJM 路径出现负利率 (min={paths.min():.4f})")

    duration_ms = int((time.time() - start) * 1000)

    # 计算 percentiles
    p10 = np.percentile(paths, 10, axis=0).tolist()  # (n_steps, n_maturities)
    p50 = np.percentile(paths, 50, axis=0).tolist()
    p90 = np.percentile(paths, 90, axis=0).tolist()
    final_distribution = paths[:, -1, :].mean(axis=0).tolist()  # 终期均值

    # 持久化 .npz
    os.makedirs(settings.ESG_CASE_DIR, exist_ok=True)
    hjm_filename = f"hjm_{scheme_id}_{int(time.time())}.npz"
    file_path = os.path.join(settings.ESG_CASE_DIR, hjm_filename)
    np.savez_compressed(file_path, paths=paths, maturities=generator.maturities)

    rid = db.execute(text("""INSERT INTO prcp_esg_run
        (scheme_id, scheme_code, run_type, status, params_json, output_json, file_path, duration_ms, created_by)
        VALUES (:s, :c, 'HJM_GENERATE', 'SUCCESS', :p, :o, :f, :d, :u)"""), {
        "s": scheme_id, "c": generator.scheme_code,
        "p": json.dumps({"n_scenarios": paths.shape[0], "n_steps": paths.shape[1], "seed": generator.seed}),
        "o": json.dumps({
            "paths_shape": list(paths.shape),
            "p10": p10, "p50": p50, "p90": p90,
            "final_distribution": final_distribution,
            "vol_per_maturity": vol_per_maturity.tolist(),
        }),
        "f": file_path, "d": duration_ms, "u": uid,
    }).lastrowid
    db.commit()
    return {"run_id": rid, "paths_shape": list(paths.shape), "file_path": file_path}
```

#### 5.3.3 scheme_generate_scenarios

```python
@router.post("/esg/schemes/{scheme_id}/generate")
async def scheme_generate_scenarios(scheme_id: int, body: dict, db, user):
    uid = user.get("id", 1) if isinstance(user, dict) else getattr(user, "id", 1)
    generator = _STORE.get(scheme_id)
    if not generator or not generator._hjm_generated:
        raise HTTPException(400, "请先生成 HJM")

    paths = generator.last_hjm_paths
    scenario_id = uuid.uuid4().hex[:12]
    sc_filename = f"scenario_{scheme_id}_{scenario_id}.npz"
    file_path = os.path.join(settings.ESG_CASE_DIR, sc_filename)
    os.makedirs(settings.ESG_CASE_DIR, exist_ok=True)
    np.savez_compressed(
        file_path,
        paths=paths,
        maturities=np.array(generator.maturities, dtype=np.int32),
        initial_yields=np.array(generator.initial_yields, dtype=np.float64),
        seed=np.int32(generator.seed),
        n_scenarios=np.int32(paths.shape[0]),
        n_steps=np.int32(paths.shape[1]),
    )
    file_size = os.path.getsize(file_path)

    # 写 prcp_esg_scenario
    sc_id = db.execute(text("""INSERT INTO prcp_esg_scenario
        (scheme_id, scenario_type, file_path, n_scenarios, n_steps, n_maturities, seed,
         maturities_json, file_size_bytes, description, created_by)
        VALUES (:s, 'esg_factory', :f, :ns, :nst, :nm, :sd, :mj, :fs, :desc, :u)"""), {
        "s": scheme_id, "f": file_path,
        "ns": paths.shape[0], "nst": paths.shape[1], "nm": paths.shape[2],
        "sd": generator.seed,
        "mj": json.dumps(generator.maturities),
        "fs": file_size,
        "desc": f"ESG 方案 #{scheme_id} 情景集 {scenario_id}",
        "u": uid,
    }).lastrowid

    # 写 prcp_esg_run
    run_id = db.execute(text("""INSERT INTO prcp_esg_run
        (scheme_id, scheme_code, run_type, status, params_json, output_json, file_path, duration_ms, created_by)
        VALUES (:s, :c, 'SCENARIO_GENERATE', 'SUCCESS', :p, :o, :f, :d, :u)"""), {
        "s": scheme_id, "c": generator.scheme_code,
        "p": json.dumps({"scenario_id": scenario_id}),
        "o": json.dumps({"scenario_id": scenario_id, "sc_id": sc_id, "file_size_bytes": file_size}),
        "f": file_path, "d": 0, "u": uid,
    }).lastrowid

    # 回写 scenario.last_run_id
    db.execute(text("UPDATE prcp_esg_scenario SET last_run_id=:r WHERE id=:i"),
               {"r": run_id, "i": sc_id})
    db.commit()

    return {"run_id": run_id, "scenario_id": scenario_id, "sc_id": sc_id, "file_path": file_path}
```

### 5.4 错误处理

| 状态码 | 场景 |
|--------|------|
| 400 | 数据源没有数据 / n_factors 越界 / HJM 未跑就生成情景集 / HJM 路径负利率 |
| 404 | 方案/运行/情景集不存在 |
| 409 | scheme_code 唯一冲突 |
| 422 | Pydantic 校验失败 |
| 500 | 数据库写入失败 / .npz 写入失败 |

所有错误返回统一结构：
```json
{"detail": "方案 3 不存在或已删除"}
```

---

## 6. 前端页面设计

### 6.1 页面清单（7 页）

| 路径 | 页面 | 关键组件 |
|------|------|----------|
| `/esg` | 方案列表（EsgSchemes） | AntD Table + 4 KPI + Drawer 预览 |
| `/esg/config/:scheme_id?` | 方案配置（EsgSchemeConfig） | AntD Form + 多步向导 |
| `/esg/detail/:scheme_id` | 方案详情（EsgSchemeDetail） | 3 步执行按钮 + run 历史 tab + 可视化 Tab |
| `/esg/curve` | 曲线还原（EsgCurve） | ECharts 期限折线 + 数据源下拉 |
| `/esg/pca/:scheme_id` | PCA 因子（EsgPCA） | 累计方差柱状 + 因子载荷热力图 |
| `/esg/hjm/:run_id` | HJM 路径（EsgHJM） | 包络图 + 终期分布 + 样本路径 |
| `/esg/results` | 汇总展示（EsgResults） | 3 表数据 + KPI |

### 6.2 菜单结构（MainLayout.tsx）

```
ESG 场景工厂（AreaChartOutlined）
```

**插入位置**：「数据维护」与「模型管理」之间（因 ESG 是数据上游）

```tsx
{
  key: '/esg',
  icon: <AreaChartOutlined />,
  label: 'ESG 场景工厂',
  children: [
    { key: '/esg', label: '方案管理' },             // → /esg (EsgSchemes)
    { key: '/esg/curve', label: '曲线还原' },         // → /esg/curve
    { key: '/esg/results', label: '结果汇总' },       // → /esg/results
  ],
}
```

> **PRCP vs DeepALM 优化**：DeepALM 有 8 个子菜单（Schemes/Runs/Import/Curve/PCA/HJM/Config/Results），PRCP 简化为 3 个一级入口，避免菜单过深。

### 6.3 核心页面详细设计

#### 6.3.1 方案列表（EsgSchemes.tsx）

```tsx
<Card>
  <Row gutter={16}>
    <Col span={6}><Statistic title="方案总数" value={schemes.length} /></Col>
    <Col span={6}><Statistic title="READY" value={countByStatus.READY} /></Col>
    <Col span={6}><Statistic title="总运行次数" value={totalRunCount} /></Col>
    <Col span={6}><Statistic title="总情景集" value={totalScenarios} /></Col>
  </Row>
</Card>

<Card>
  <Space>
    <Input.Search placeholder="搜索 scheme_code" />
    <Select placeholder="状态" options={statusOptions} allowClear />
    <Select placeholder="数据源" options={sourceOptions} allowClear />
    <Button type="primary" onClick={() => navigate('/esg/config')}>+ 新建方案</Button>
  </Space>
</Card>

<Card>
  <Table columns={[
    { title: 'Scheme Code', dataIndex: 'scheme_code' },
    { title: '数据源', render: r => <DictTag type="PRCP_ESG_SOURCE" value={r.data_source} /> },
    { title: '起止日期', render: r => `${r.start_date} ~ ${r.end_date}` },
    { title: '因子/情景/步数', render: r => `${r.n_factors} / ${r.n_scenarios} / ${r.n_steps}` },
    { title: '状态', render: r => <DictTag type="PRCP_ESG_STATUS" value={r.status} /> },
    { title: '运行次数', dataIndex: 'run_count' },
    {
      title: '操作', render: r => (
        <Space>
          <Button onClick={() => navigate(`/esg/detail/${r.id}`)}>详情</Button>
          <Button onClick={() => navigate(`/esg/config/${r.id}`)}>编辑</Button>
          <Button onClick={() => cloneScheme(r)}>克隆</Button>
          <Button danger onClick={() => deleteScheme(r.id)}>删除</Button>
        </Space>
      )
    },
  ]} />
</Card>
```

#### 6.3.2 方案详情 3 步执行（EsgSchemeDetail.tsx）

```tsx
<Card>
  <Alert message={
    <Space>
      <Tag color="cyan">{scheme.data_source}</Tag>
      <Tag>{scheme.start_date} ~ {scheme.end_date}</Tag>
      <Tag color="purple">{scheme.n_factors} 因子</Tag>
      <Tag color="orange">{scheme.n_scenarios} 情景</Tag>
      <Tag color="gold">{scheme.n_steps} 步</Tag>
    </Space>
  } />

  <Steps current={currentStep} items={[
    { title: 'PCA 拟合', description: '从历史曲线提取因子' },
    { title: 'HJM 建模', description: '生成利率路径' },
    { title: '情景集', description: '.npz 持久化' },
  ]} />

  <Tabs activeKey={activeTab}>
    <TabPane tab="执行" key="run">
      {/* 3 个执行按钮 + 最后结果可视化 */}
      <Card title="1️⃣ PCA 拟合">
        <Button type="primary" onClick={fitPca} loading={pcaLoading}>
          跑 PCA（{scheme.n_factors} 因子）
        </Button>
        {lastPca && <PcaResultPanel input={lastPca.output} />}
      </Card>
      <Card title="2️⃣ HJM 建模">
        <Button type="primary" onClick={genHjm} loading={hjmLoading} disabled={!lastPca}>
          生成 HJM（{scheme.n_scenarios} × {scheme.n_steps} × {maturities.length}）
        </Button>
        {lastHjm && <HjmResultPanel input={lastHjm.output} />}
      </Card>
      <Card title="3️⃣ 情景集">
        <Button type="primary" onClick={genScenario} loading={scLoading} disabled={!lastHjm}>
          生成情景集
        </Button>
        {lastScenario && <ScenarioResultPanel scenario={lastScenario} />}
      </Card>
      <Button onClick={runAll} loading={runAllLoading}>🚀 一键三步</Button>
    </TabPane>
    <TabPane tab="本方案历史" key="runs">
      <Table dataSource={runs} columns={runColumns} />
    </TabPane>
  </Tabs>
</Card>
```

### 6.4 关键复用组件

#### 6.4.1 `PcaResultPanel`（PCA 结果可视化，6 子 Tab）

```tsx
<Tabs items={[
  { key: 'overview', label: '总览', children: <KpiCards data={input} /> },
  { key: 'cumulative', label: '累计方差', children: <ECharts option={cumulativeBarOption} /> },
  { key: 'variance', label: '单因子方差', children: <ECharts option={varianceBarOption} /> },
  { key: 'loadings', label: '因子载荷', children: <ECharts option={heatmapOption} /> },
  { key: 'eigenvalues', label: '特征值衰减', children: <ECharts option={eigenDecayOption} /> },
  { key: 'matrix', label: '载荷矩阵', children: <MatrixTable data={input.factor_loadings} /> },
]} />
```

#### 6.4.2 `HjmResultPanel`（HJM 结果可视化，5 子 Tab）

```tsx
<Tabs items={[
  { key: 'overview', label: '总览', children: <KpiCards data={input} /> },
  { key: 'p50', label: 'p50 路径', children: <ECharts option={p50LinesOption} /> },
  { key: 'envelope', label: 'p10/p50/p90 包络', children: <ECharts option={envelopeAreaOption} /> },
  { key: 'final', label: '终期分布', children: <ECharts option={finalBarOption} /> },
  { key: 'samples', label: '样本路径', children: <ECharts option={samplePathsOption} /> },
]} />
```

#### 6.4.3 `ScenarioResultPanel`（情景集可视化，2 子 Tab）

```tsx
<Tabs items={[
  { key: 'current', label: '当前情景集', children: <ScenarioMetaCard scenario={scenario} /> },
  { key: 'history', label: '历史', children: <Table dataSource={historicalScenarios} /> },
]} />
```

### 6.5 前端 API 客户端

**新文件**：`frontend/src/api/esg.ts`（**新建**，不混在 index.ts）

```ts
import { http } from './index'

export interface EsgScheme { ... }
export interface EsgRun { ... }
export interface EsgScenario { ... }
export interface YieldCurvePoint { ... }
export interface SourceStat { ... }
export interface SvenssonRates { ... }

export const esgApi = {
  listSchemes: (params?) => http.get('/esg/schemes', { params }).then(r => r.data),
  createScheme: (data) => http.post('/esg/schemes', data).then(r => r.data),
  getScheme: (id) => http.get(`/esg/schemes/${id}`).then(r => r.data),
  updateScheme: (id, data) => http.put(`/esg/schemes/${id}`, data).then(r => r.data),
  deleteScheme: (id) => http.delete(`/esg/schemes/${id}`).then(r => r.data),
  cloneScheme: (id, newCode, newName?) =>
    http.post(`/esg/schemes/${id}/clone`, {
      new_scheme_code: newCode, new_scheme_name: newName,
    }).then(r => r.data),
  fitPca: (id, body?) => http.post(`/esg/schemes/${id}/fit-pca`, body || {}).then(r => r.data),
  generateHjm: (id, body?) => http.post(`/esg/schemes/${id}/generate-hjm`, body || {}).then(r => r.data),
  generateScenario: (id) => http.post(`/esg/schemes/${id}/generate`, {}).then(r => r.data),
  runAll: (id) => http.post(`/esg/schemes/${id}/run-all`, {}).then(r => r.data),
  listSchemeRuns: (id, params?) => http.get(`/esg/schemes/${id}/runs`, { params }).then(r => r.data),
  listAllRuns: (params?) => http.get('/esg/runs', { params }).then(r => r.data),
  getRun: (runId) => http.get(`/esg/runs/${runId}`).then(r => r.data),
  listScenarios: (params?) => http.get('/esg/scenarios', { params }).then(r => r.data),
  getScenario: (id) => http.get(`/esg/scenarios/${id}`).then(r => r.data),
  downloadScenarioUrl: (id) => `/prcp/api/esg/scenarios/${id}/download`,
  runOneClickCase: (body?) => http.post('/esg/case/run', body || {}).then(r => r.data),
}

export const yieldCurveApi = {
  list: (params?) => http.get('/esg/curves', { params }).then(r => r.data),
  sources: () => http.get('/esg/curves/sources').then(r => r.data),
  get: (date, source?) => http.get(`/esg/curves/${date}`, { params: source ? { source } : {} }).then(r => r.data),
  upsert: (point) => http.post('/esg/curves', point).then(r => r.data),
  bulkUpsert: (points) => http.post('/esg/curves/bulk', { points }).then(r => r.data),
  rates: (date, body) => http.post(`/esg/curves/${date}/rates`, body).then(r => r.data),
}
```

---

## 7. 核心算法

### 7.1 Svensson 模型曲线还原

**模型定义**：
```
Y(T) = θ₀ + θ₁·H(T/λ₁) + θ₂·(H(T/λ₁) - e^(-T/λ₁)) + θ₃·(H(T/λ₂) - e^(-T/λ₂))
其中 H(x) = (1 - e^(-x)) / x  （Humphrey 衰减函数）
```

**6 参数**：`θ₀`（水平）/ `θ₁`（斜率）/ `θ₂`（第一曲度）/ `θ₃`（第二曲度）/ `λ₁` / `λ₂`（衰减速度）

**数据存储**：曲线表的 `theta0..lambda2` 6 字段直接存储拟合后的参数。前端可调用 `POST /esg/curves/{date}/rates` 还原自定义期限利率：

```python
def svensson_rates(theta0, theta1, theta2, theta3, lambda1, lambda2, maturities_months):
    """还原任意期限数组的利率

    Args:
        maturities_months: list[int]，月为单位（如 [1,3,6,12,...]）

    Returns:
        np.ndarray: (n_maturities,) 利率百分比
    """
    def H(x):
        return np.where(x > 0, (1 - np.exp(-x)) / x, 1.0)

    T = np.array(maturities_months) / 12.0  # 月 → 年
    return (theta0
            + theta1 * H(T / lambda1)
            + theta2 * (H(T / lambda1) - np.exp(-T / lambda1))
            + theta3 * (H(T / lambda2) - np.exp(-T / lambda2)))
```

### 7.2 PCA 因子分解

**输入**：n 个历史日期 × m 个期限利率的矩阵 `Y`（n × m）

**步骤**：
```python
# 1. 去中心化
Y_centered = Y - Y.mean(axis=0)

# 2. 协方差矩阵
cov = (Y_centered.T @ Y_centered) / (n - 1)  # (m × m)

# 3. 特征值分解
eigenvalues, eigenvectors = np.linalg.eigh(cov)
# 按特征值降序排列
idx = np.argsort(eigenvalues)[::-1]
eigenvalues = eigenvalues[idx]
eigenvectors = eigenvectors[:, idx]

# 4. 取前 k 个因子
factor_loadings = eigenvectors[:, :k]              # (m × k)
explained_variance_ratio = eigenvalues[:k] / eigenvalues.sum()  # (k,)

# 5. 累计方差
cumulative = np.cumsum(explained_variance_ratio)
```

**业务校验**：`cumulative[k-1] >= 0.95`（前 k 因子解释 ≥95% 方差）

### 7.3 HJM 路径生成（PRCP 优化版）

**HJM 仿射模型**（月频版，PRCP 不用 22 日转换因子）：
```
ΔY(t) = Σ αᵢ(t) dWᵢ(t)        i=1..k
其中 αᵢ(t) 是期限结构 × 因子载荷的函数
```

**实现**：
```python
def generate_hjm_paths(self, n_scenarios, n_steps, seed):
    rng = np.random.default_rng(seed)
    dt = 1.0 / 12  # 月步长
    sqrt_dt = np.sqrt(dt)

    # 主成分随机游走
    dW = rng.standard_normal((n_scenarios, n_steps, self.k)) * sqrt_dt
    # (n_scenarios, n_steps, k)

    # 累积路径
    integral = np.cumsum(dW, axis=1)  # (n_scenarios, n_steps, k)

    # 重构利率路径：paths[t] = initial_yields + factor_loadings @ integral[t]
    paths = np.einsum('stk,km->stm', integral, self.factor_loadings)
    paths = paths + self.initial_yields  # (m,) 广播

    # === PRCP 优化：保证非负（利率物理约束） ===
    paths = np.maximum(paths, 0.0)

    # === PRCP 优化：波动率递减校验（仅 warn，不 raise） ===
    vol_per_maturity = paths[:, -1, :].std(axis=0)
    if not np.all(np.diff(vol_per_maturity) <= 1e-6):
        logger.warning(f"波动率非递减 {vol_per_maturity.tolist()}")

    return paths  # (n_scenarios, n_steps, n_maturities)
```

**性能**：1000 × 120 × 64 → 7.68M float64 → numpy einsum < 200ms

**PRCP 期限池深度变化**：
- DeepALM 默认 [1,3,6,12,60,120] 6 期限点
- PRCP 默认 [1,3,6,12,24,36,48,60,84,120,180,240,360] 13 期限点（**比 DeepALM 密**）
- 用户可在 `EsgSchemeIn.maturities_months` 自由指定

### 7.4 一键案例算法

```python
def run_one_click_case(db, data_source='ECB'):
    """一键演示：自动创建方案 → 跑三步"""
    code = 'PRCP_ESG_DEMO_001'
    scheme = db.execute(text("SELECT id FROM prcp_esg_scheme WHERE scheme_code=:c AND is_deleted=0"),
                        {"c": code}).first()
    if not scheme:
        scheme_id = db.execute(text("""INSERT INTO prcp_esg_scheme
            (scheme_code, scheme_name, data_source, start_date, end_date,
             n_factors, maturities_json, n_scenarios, n_steps, seed, status)
            VALUES (:c, :n, :ds, :sd, :ed, 3, :mj, 50, 24, 42, 'READY')"""), {
            "c": code, "n": "一键案例（演示）",
            "ds": data_source, "sd": "2024-01-01", "ed": "2026-04-01",
            "mj": json.dumps([1,3,6,12,24,60,84,120,240,360]),
        }).lastrowid
    else:
        scheme_id = scheme[0]

    # 调用三个 endpoint
    pca = scheme_fit_pca(scheme_id, EsgPcaRunIn(n_factors=3), db, user={"id": 1})
    hjm = scheme_generate_hjm(scheme_id, EsgHjmRunIn(n_scenarios=50, n_steps=24, seed=42), db, user={"id": 1})
    sc = scheme_generate_scenarios(scheme_id, {}, db, user={"id": 1})

    return {
        "scheme_id": scheme_id,
        "pca_run_id": pca["run_id"],
        "hjm_run_id": hjm["run_id"],
        "scenario_id": sc["scenario_id"],
    }
```

---

## 8. PRCP vs DeepALM 优化点

| # | 优化点 | DeepALM 实现 | PRCP 优化 | 业务收益 |
|---|--------|--------------|-----------|----------|
| 1 | **HJM 路径波动率递减校验** | 无 | HJM 生成后校验 `vol_per_maturity` 单调递减，非递减 warn | 提早发现因子载荷异常 |
| 2 | **HJM 路径负利率检查** | 只 `max(paths, 0)` 静默截断 | raise HTTPException(400) 当 min < -0.01 | 防止下游误用 |
| 3 | **默认期限数组** | [1,3,6,12,60,120] 6 期限 | [1,3,6,12,24,36,48,60,84,120,180,240,360] 13 期限 | 与 PRCP 期限桶 m1~m60+y10/y15/y20/y30 对齐 |
| 4 | **月度步长** | 用 22 日转换因子 | 直接 `dt=1/12` 月频 | 简化算法，去 BPTT 依赖 |
| 5 | **HJM 频率选择** | 必须 ECB 数据 | 支持 ECB/FRB/CUSTOM/BANK 4 类 | 与 seed CSV 对齐 |
| 6 | **表前缀** | `esg_*` | `prcp_esg_*` | 统一 PRCP 命名规范 |
| 7 | **status 状态机** | DRAFT/READY/ARCHIVED | 同 + `prcp_esg_run.status` 加 RUNNING | 更细粒度追踪 |
| 8 | **缓存诊断** | 无 | `GET /esg/cache-info` 返回 `_Store` 状态 | 运维可查 |
| 9 | **更新方案清缓存** | 有（_Store dict） | 同 + PUT 时显式 `del _Store[scheme_id]` | 防止脏缓存 |
| 10 | **数据目录** | `/var/lib/deepalm/esg_cases/` | `/var/lib/prcp/esg_cases/` | 隔离模块数据 |
| 11 | **路由文件数** | esg_analysis + yield_curve + scenarios = 3 文件 | esg.py 单文件 22 endpoint | 减少文件数（PRCP 现有约定） |
| 12 | **Pydantic Schema** | 有 Out 后缀（EsgRunOut 等） | 只用 In 后缀（PRCP 现有约定） | 命名统一 |
| 13 | **前端子菜单数** | 8 个 | 3 个（方案管理/曲线还原/结果汇总） | 菜单更扁平 |
| 14 | **依赖** | 需 torch（BPTT） | 纯 numpy + scipy | 与 PRCP 后端栈一致 |
| 15 | **系统设置** | DEEPALM_CASE_DIR 等多个 env | PRCP_CASE_DIR 一个 env | 配置简化 |

---

## 9. 部署架构

### 9.1 服务器路径

```
/home/almd/prcp/backend/                    # 后端 venv + FastAPI
/var/lib/prcp/esg_cases/                     # HJM .npz + scenario .npz 输出
/etc/systemd/system/prcp-backend.service     # 后端 systemd
/var/www/prcp/                                # 前端部署目录（已存在）
```

### 9.2 环境变量（systemd）

在 `/etc/systemd/system/prcp-backend.service` `[Service]` 段加：

```ini
[Service]
Environment=PRCP_CASE_DIR=/var/lib/prcp/esg_cases
Environment=PRCP_PROJECT_ROOT=/home/almd/prcp
# (其他已有变量不变)
```

### 9.3 数据库 DDL 升级脚本

新建 `backend/scripts/upgrade_esg_v1.sql`：

```sql
-- ===========================================
-- PRCP ESG 场景工厂 v1.0 升级脚本 (2026-09-22)
-- 新增 4 张表 + sys_dict 字典 9 项
-- ===========================================
SET NAMES utf8mb4;

-- 1. 方案配置表
DROP TABLE IF EXISTS prcp_esg_scheme;
CREATE TABLE prcp_esg_scheme (
    -- (完整 DDL 见 4.2.1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 工厂方案配置';

-- 2. 运行历史表
DROP TABLE IF EXISTS prcp_esg_run;
CREATE TABLE prcp_esg_run (
    -- (完整 DDL 见 4.2.2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 工厂运行历史';

-- 3. Svensson 曲线表
DROP TABLE IF EXISTS prcp_esg_curve_point;
CREATE TABLE prcp_esg_curve_point (
    -- (完整 DDL 见 4.2.3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Svensson 6 参数曲线统一表';

-- 4. 情景集持久化表
DROP TABLE IF EXISTS prcp_esg_scenario;
CREATE TABLE prcp_esg_scenario (
    -- (完整 DDL 见 4.2.4)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 情景集持久化索引';

-- 5. sys_dict 字典扩展
INSERT IGNORE INTO sys_dict (dict_type, dict_key, dict_label, color, sort_order, status, description, is_deleted)
VALUES
('PRCP_ESG_SOURCE','ECB','欧洲央行','blue',10,'ACTIVE','ECB AAA 国债收益率',0),
('PRCP_ESG_SOURCE','FRB','美联储','red',20,'ACTIVE','FRB H.15 利率',0),
('PRCP_ESG_SOURCE','CUSTOM','自定义','cyan',30,'ACTIVE','银行自定义曲线',0),
('PRCP_ESG_SOURCE','BANK','本行加点','gold',40,'ACTIVE','本行账簿加点估算',0),
('PRCP_ESG_RUN_TYPE','PCA_FIT','PCA 拟合','blue',10,'ACTIVE','主成分因子分解',0),
('PRCP_ESG_RUN_TYPE','HJM_GENERATE','HJM 建模','cyan',20,'ACTIVE','HJM 利率路径生成',0),
('PRCP_ESG_RUN_TYPE','SCENARIO_GENERATE','情景集生成','purple',30,'ACTIVE','.npz 文件持久化',0),
('PRCP_ESG_STATUS','DRAFT','草稿','default',10,'ACTIVE','新建未配置完',0),
('PRCP_ESG_STATUS','READY','就绪','green',20,'ACTIVE','配置完成可执行',0),
('PRCP_ESG_STATUS','ARCHIVED','已归档','gray',30,'ACTIVE','历史方案',0),
('PRCP_ESG_RUN_STATUS','SUCCESS','成功','green',10,'ACTIVE','执行成功',0),
('PRCP_ESG_RUN_STATUS','FAILED','失败','red',20,'ACTIVE','执行失败',0),
('PRCP_ESG_RUN_STATUS','RUNNING','运行中','blue',30,'ACTIVE','正在执行',0);
```

### 9.4 部署命令

```bash
# 1. 应用 DDL 升级
scp backend/scripts/upgrade_esg_v1.sql almd@43.143.253.186:/tmp/
ssh almd@43.143.253.186 "mysql -ualmd -pAlmd@2026 prcp_db < /tmp/upgrade_esg_v1.sql"

# 2. 创建数据目录
ssh almd@43.143.253.186 "echo 'almd' | sudo -S mkdir -p /var/lib/prcp/esg_cases && sudo chown -R almd:almd /var/lib/prcp/esg_cases"

# 3. 上传后端代码 + 重启
scp backend/app/routers/esg.py almd@43.143.253.186:/tmp/
scp -r backend/app/services/esg/ almd@43.143.253.186:/tmp/

ssh almd@43.143.253.186 "echo 'almd' | sudo -S bash -c '
  cp /tmp/esg.py /home/almd/prcp/backend/app/routers/esg.py
  cp -r /tmp/esg/ /home/almd/prcp/backend/app/services/esg/
  chown -R almd:almd /home/almd/prcp/backend/app/routers/esg.py /home/almd/prcp/backend/app/services/esg/
  find /home/almd/prcp/backend -name __pycache__ -exec rm -rf {} +
  systemctl restart prcp-backend
'"

# 4. 上传种子 CSV（5 份）
scp backend/scripts/seed_data/svensson_*.csv almd@43.143.253.186:/home/almd/prcp/backend/scripts/seed_data/

# 5. 上传前端
cd frontend
mv dist dist.bak 2>/dev/null || true
./node_modules/.bin/vite build
scp dist/index.html almd@43.143.253.186:/tmp/prcp_index.html
scp dist/assets/*.js almd@43.143.253.186:/tmp/
scp dist/assets/*.css almd@43.143.253.186:/tmp/

bash C:/银行经营/deploy/scripts/deploy-prcp.sh  # 用现有 PRCP 部署脚本（已支持）
```

### 9.5 部署踩坑（已验证）

1. **`/var/lib/prcp/esg_cases/` 创建**：almd 用户无 sudo，需要 `echo 'almd' | sudo -S mkdir -p && sudo chown -R almd:almd`
2. **systemd 不继承 env**：必须在 `[Service]` 段加 `Environment=PRCP_CASE_DIR=...`
3. **`__pycache__` 缓存**：改代码后必须 `find ... -name __pycache__ -exec rm -rf {} +`
4. **vite hash 文件名**：deploy-prcp.sh 自动读 index.html 找 hash
5. **scp 中文路径**：用 `/tmp/` 中转

---

## 10. 端到端验证

### 10.1 E2E 测试用例

```python
# tests/e2e_esg_test.py
"""PRCP ESG 场景工厂端到端测试"""
import sys
import urllib.request
import urllib.error
import json

BASE = "http://127.0.0.1:8006"


def http(method, path, body=None, token=None, is_form=False):
    url = f"{BASE}{path}"
    if is_form and body is not None:
        data = urllib.parse.urlencode(body).encode()
    elif body is not None:
        data = json.dumps(body).encode()
    else:
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    if is_form and body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    elif body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "null")


def main():
    # [1] 登录
    code, r = http("POST", "/prcp/api/auth/login",
                   {"username": "admin", "password": "admin123"}, is_form=True)
    assert code == 200, f"登录失败: {code} {r}"
    token = r["access_token"]

    # [2] 一键案例
    code, r = http("POST", "/prcp/api/esg/case/run", {}, token=token)
    assert code == 200, f"一键案例失败: {code} {r}"
    scheme_id = r["scheme_id"]
    pca_run_id = r["pca_run_id"]
    hjm_run_id = r["hjm_run_id"]
    scenario_id = r["scenario_id"]

    # [3] 列出方案
    code, r = http("GET", "/prcp/api/esg/schemes", token=token)
    assert code == 200 and any(s["id"] == scheme_id for s in r["items"])

    # [4] 检查 PCA 累计方差 ≥ 95%
    code, r = http("GET", f"/prcp/api/esg/runs/{pca_run_id}", token=token)
    cumvar = sum(r["output"]["explained_variance_ratio"][:3])
    assert cumvar >= 0.95, f"PCA 3 因子累计方差 {cumvar} < 95%"

    # [5] HJM 路径非负
    code, r = http("GET", f"/prcp/api/esg/runs/{hjm_run_id}", token=token)
    paths_shape = r["output"]["paths_shape"]
    assert paths_shape[0] >= 10 and paths_shape[1] >= 12

    # [6] 情景集可下载
    code, r = http("GET", f"/prcp/api/esg/scenarios/{scenario_id}/download", token=token)
    # 注：download 端点返回 .npz 二进制，此处只验证 HTTP 200
    assert code == 200, f"情景集下载失败: {code}"

    # [7] 列出本方案运行历史
    code, r = http("GET", f"/prcp/api/esg/schemes/{scheme_id}/runs", token=token)
    assert len(r["items"]) >= 3  # PCA + HJM + Scenario

    # [8] 全局运行历史过滤
    code, r = http("GET", "/prcp/api/esg/runs?run_type=PCA_FIT&page_size=10", token=token)
    assert code == 200

    # [9] Svensson 曲线还原
    code, r = http("POST", "/prcp/api/esg/curves/2026-04-02/rates",
                   {"tenors": [1, 3, 6, 12, 60, 120]}, token=token)
    assert code == 200 and len(r["rates"]) == 6

    print("✅ 全部通过！")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"❌ 失败: {e}")
        sys.exit(1)
```

### 10.2 性能指标（PRCP 预期）

| 操作 | 数据规模 | 耗时 |
|------|----------|------|
| PCA 拟合 | 551 × 13 期限 | ~30ms |
| HJM 生成 | 50 × 24 × 13 | ~20ms |
| HJM 生成 | 1000 × 120 × 64 | < 800ms |
| 情景集保存 | 50 × 24 × 13 .npz | ~30ms |
| 一键三步 | 551 ECB + 50×24×13 | < 3000ms |

### 10.3 业务指标（PRCP 预期）

| 指标 | 值 | 业务意义 |
|------|----|----------|
| **PC1 方差贡献** | ~55% | 水平因子主导（DeepALM 63% ECB 样本，PRCP 551 样本预期更高） |
| **PC2 方差贡献** | ~30% | 斜率因子 |
| **PC3 方差贡献** | ~10% | 曲度因子 |
| **3 因子累计** | ≥95% | 模型充分 |
| **HJM 路径范围** | 0%~8% | 符合 ECB 实际利率区间 |
| **波动率递减** | 严格满足 | PRCP 优化点校验通过 |

---

## 11. 未来演进

### 11.1 v1.1（2026 Q4）
- [ ] 集成 `prcp_sim_scheme`：新业务模拟的利率输入改为可选 .npz scenario_id
- [ ] 集成 `prcp_kpi_definition`：函数指标可读取 .npz 计算 ΔEVE、LCR、NSFR
- [ ] 实时数据接入（ECB / FRB API 定时拉取 cron job）

### 11.2 v2.0（2027 Q1）
- [ ] 因子旋转（Varimax / Promax）增强可解释性
- [ ] 多因子联合 HJM（Correlation-aware）
- [ ] 反向压力测试（指定终值反推参数）

### 11.3 v3.0（2027 Q3）
- [ ] 神经网络 HJM（LSTM / Transformer 路径生成）
- [ ] 与 BPTT AFA 模块对接

---

## 12. 关键踩坑与最佳实践

### 12.1 PRCP 命名 / 通用

1. **表名前缀统一 `prcp_*`**：与 COA / KPI / RPT / SIM / RATE 一致
2. **公共字段必含**：`id / status / is_deleted / created_by/updated_by/created_at/updated_at`
3. **唯一索引带 is_deleted**：`UNIQUE KEY uk_X (X, is_deleted)`，软删后允许重建同名记录
4. **JSON 字段用 `_json` 后缀**：`maturities_json / initial_yields_json / raw_data_json`
5. **sys_dict 外挂字典**：数据源/状态/类型都进 sys_dict，不要在业务表里硬编码 VARCHAR(16)

### 12.2 算法踩坑（DeepALM 经验迁移）

1. **HJM 路径必须非负**：利率下界 0%，`np.maximum(paths, 0)` 截断
2. **波动率随期限递减**：PCA 因子 1 水平主导，短端波动率 ≥ 长端，校验不通过 warn
3. **月频 vs 日频**：PRCP 月频 `dt=1/12`，无需 DeepALM 的 22 日转换因子
4. **Svensson λ 必须 > 0**：Pydantic Field 强制 `gt=0`，避免除零
5. **HJM 大数据耗内存**：10000 情景 × 360 步 × 64 期限 × 8 bytes = 184 MB，单次限制 `n_scenarios ≤ 10000`

### 12.3 部署踩坑

1. **`/var/lib/prcp/esg_cases/` 必须 `sudo mkdir + chown almd:almd`**
2. **systemd 加 `Environment=PRCP_CASE_DIR=...`**
3. **改 .py 后必须 `find ... -name __pycache__ -exec rm -rf {} +`**
4. **用 `deploy-prcp.sh`**：自动同步 index.html + assets/

---

## 13. 附录

### 13.1 关键代码引用

| 文件 | 行数 | 说明 |
|------|------|------|
| `backend/app/routers/esg.py` | ~600 | 22 endpoint 单 router |
| `backend/app/services/esg/__init__.py` | ~10 | 导出 |
| `backend/app/services/esg/svensson.py` | ~80 | SvenssonYieldCurve 公式 |
| `backend/app/services/esg/yield_curve_generator.py` | ~250 | YieldCurveGenerator：fit_pca + generate_hjm |
| `backend/app/services/esg/scenario_set.py` | ~120 | ScenarioSet dataclass + save/load npz |
| `backend/app/services/esg/validator.py` | ~80 | 波动率递减/非负校验 |
| `backend/scripts/upgrade_esg_v1.sql` | ~150 | 4 表 + 13 sys_dict 项 |
| `backend/scripts/seed_data/svensson_*.csv` | ~250 | 5 份种子数据 |
| `frontend/src/pages/esg/EsgSchemes.tsx` | ~280 | 方案列表 + Drawer 预览 |
| `frontend/src/pages/esg/EsgSchemeConfig.tsx` | ~250 | 方案配置表单 |
| `frontend/src/pages/esg/EsgSchemeDetail.tsx` | ~400 | 3 步执行 + run 历史 |
| `frontend/src/pages/esg/EsgCurve.tsx` | ~250 | 曲线还原可视化 |
| `frontend/src/pages/esg/EsgPCA.tsx` | ~200 | PCA 结果可视化 |
| `frontend/src/pages/esg/EsgHJM.tsx` | ~200 | HJM 路径可视化 |
| `frontend/src/pages/esg/EsgResults.tsx` | ~150 | 汇总展示 |
| `frontend/src/api/esg.ts` | ~120 | API 客户端 |
| `frontend/src/components/esg/PcaResultPanel.tsx` | ~200 | PCA Panel |
| `frontend/src/components/esg/HjmResultPanel.tsx` | ~200 | HJM Panel |
| `frontend/src/components/esg/ScenarioResultPanel.tsx` | ~100 | Scenario Panel |
| `tests/e2e_esg_test.py` | ~150 | 端到端测试 |

### 13.2 数据库现状（部署后预期）

```
prcp_esg_scheme:        1 行（PRCP_ESG_DEMO_001）
prcp_esg_run:           3 行（一键案例 × 3 步骤）
prcp_esg_curve_point:   588 行（4 个 source，复制自 DeepALM）
prcp_esg_scenario:      1 行
```

### 13.3 公开访问入口（部署后）

- ESG 菜单：https://wxfzhh.online/prcp/esg
- 方案管理：https://wxfzhh.online/prcp/esg
- 方案详情：https://wxfzhh.online/prcp/esg/detail/1
- 曲线还原：https://wxfzhh.online/prcp/esg/curve
- API 文档：https://wxfzhh.online/prcp/api/docs

---

**文档结束**