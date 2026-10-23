# PRCP · 经营计划与资产负债预测平台（Portfolio Resource Coordination Platform）

> 第 6 个模块，专注银行"账户册建模 → 报表模板 → 数据维护 → 指标体系 → 模型训练 → 组合反算 → 新业务模拟"全链路
>
> 版本：v2.0（2026-09-24 重写）　|　上一个版本：v1.0（资金组算版，2026-09 已下架）

---

## 1. 业务定位

PRCP 是银行经营系列平台中的**经营计划与资产负债预测平台**。当前业务链路：

```
账户册建模  →  报表模板  →  数据维护  →  指标体系  →  模型训练  →  组合反算  →  新业务模拟
  (COA)        (RPT)       (DATA×9)     (KPI)       (MODEL)      (REVERSE)    (SIM)
   树形结构     6 类报表    64+64 桶     公式/函数    12 种算法    KPI 链过滤    引擎计量
   父子层级     取数逻辑    24 月现金流    指标文档     超参数模板   未来 24 月    按账户级模拟
   ↑ 基础建模     ↑ 报表模板     ↑ 数据源        ↑ 派生指标       ↑ 训练管理      ↑ 优化求解       ↑ 预测头寸
```

| 模块 | 业务定位 | 上下游关系 |
|---|---|---|
| ALMD | 银行经营分析（监管指标） | 风险约束 |
| ALMT | 业务计划 / 定价策略 | 上游计划输入 |
| CURV | 收益率曲线 | 利率输入 |
| **PRCP** | **经营计划预测 + 资产负债反算** | **执行与优化** |
| IALM | 保险资产负债 | 行业垂直 |
| ZHZC | 智能分析 / 对话 | 智能层 |

---

## 2. 技术栈

| 层 | 技术 |
|---|---|
| **前端** | React 18 + TypeScript 5 + Vite + AntD 5 + ECharts + dayjs + axios |
| **后端** | FastAPI 0.110+ + SQLAlchemy 2 + PyMySQL + Pydantic 2 + python-jose + passlib |
| **数据库** | MySQL 8 `prcp_db`（用户 `prcp / Prcp@2026`） |
| **部署** | 端口 **8006** + 子路径 `/prcp/api`（nginx 反代） |
| **前端部署路径** | `/var/www/prcp/`（assets/ 目录 root:root 拥有，scp 后需 sudo cp + chown） |
| **后端部署路径** | `/home/almd/prcp/backend/`（非 `/opt/prcp`） |
| **服务名** | `prcp-backend`（systemd），前端 `index.html` + assets/*.js |
| **统一风格** | 蓝紫渐变 `#667eea → #764ba2` + 鼎形"组算"图标 |
| **登录账号** | `admin / admin123`（默认） |

---

## 3. 业务模块（8 大模块 + 1 新业务模拟）

> v1.0 时代的"资金组 / 头寸 / 组算规则 / 组算任务"4 个旧模块已**下架**。当前 PRCP 重心转向"账户册 + 报表 + 数据 + 指标 + 模型 + 反算 + 新业务模拟"完整业务链路。

### 3.1 一级菜单总览

| 一级菜单 | 路由 | 二级菜单 | 模块性质 |
|---|---|---|---|
| **Dashboard** | `/dashboard` | 12 卡片 KPI + 趋势 + 排行 | 总览 |
| **账户册维护** | `/coa` | 账户册方案 + 结构树 + Excel 导入 | 基础建模 |
| **报表表项管理** | `/rpt` | 报表定义 + 表项结构 + 取数逻辑 | 报表模板 |
| **数据维护** | `/basic` | 9 类数据（见下） | 数据源 |
| **指标管理** | `/kpi` | 指标方案 + 定义 + 评分 + 维护 + 试算 | 派生指标 |
| **模型管理** | `/model` | 算法字典 + 参数模板 + 版本 + 训练 | 训练管理 |
| **组合反算** | `/reverse` | 反算方案 + 目标 + 运行 + 结果查询 | 优化求解 |
| **新业务模拟方案** | `/sim` | 方案 + 节点配置 + 期限占比 + 引擎计量 + 结果 | 业务预测 |
| **系统管理** | `/system` | 用户 / 角色 / 字典 / 菜单 | 基础 |

### 3.2 数据维护 9 类细分

| # | 名称 | 关键字段 | 桶数 |
|---|---|---|---|
| 1 | 账务结果指标 | 公式定义 | — |
| 2 | 关键参数指标 | 公式定义 | — |
| 3 | 规模指标 | 公式定义 | — |
| 4 | 价格指标 | 公式定义 | — |
| 5 | 中收指标 | 公式定义 | — |
| 6 | 资本与 RWA 假设指标 | 公式定义 | — |
| 7 | 资产负债表 | balance + 24 月现金流 | 24 |
| 8 | **基础数据表** | 64+64 桶 + ASF/RSF + HQLA + 度量 | **64+64** |
| 9 | 反算结果查询 | reverse-table + 5 指标（ROE/CET1/LCR/NSFR/DELTA_EVE） | — |

### 3.3 核心业务流程

```
1) 账户册建模       上传 Excel（如 中信银行账户册结构.xlsx）→ 生成 38 节点方案 ZX_CITIC_2026
   ↓
2) 报表模板         定义 6 类报表 + 表项树 + 取数逻辑（账户册节点引用）
   ↓
3) 数据维护         按方案 + 数据日期录入：
                     - 基础数据表（64+64 桶分布：m1~m60 + y10/y15/y20/y30）
                     - 资产负债表（24 月现金流）
   ↓
4) 指标体系         定义指标方案 + KPI 公式（公式指标 / 脚本函数指标）
                     指标试算验证公式正确性
   ↓
5) 模型训练         模型版本 + 12 种算法 + 6 类 18 项超参数模板
                     训练状态监控 + 训练记录
   ↓
6) 组合反算         选定账户册方案 + 计量模型 + KPI 方案
                     新增反算方案 + 多个 KPI 目标（自动生成 target_name）
                     点击反算 → CVXPY QP 求解 → 24 月 × N 节点预测
                     结果表按账户册节点 × 5 指标（ROE/CET1/LCR/NSFR/DELTA_EVE）展示
   ↓
7) 新业务模拟       按账户级配置：起始月 + 增长率 + 期限占比 + 新业务利率
                     引擎计量：64+64 桶往前推演 + 主指标重算
                     引擎包架构：calculate_engine/new_business/ 可扩展多引擎
```

---

## 4. 数据架构

### 4.1 期限桶 v3（64+64）

```python
# 后端 backend/app/services/buckets.py
ORIG_FRONT_COLS = ['orig_m1', ...'orig_m60', 'orig_y10', 'orig_y15', 'orig_y20', 'orig_y30']   # 64 桶
REM_FRONT_COLS  = ['rem_m1', ...'rem_y30']                                                     # 64 桶
```

- **原始期限（orig）**：业务开始时的合同期限
- **剩余期限（rem）**：当前到到期日的剩余期限
- 5 年内按月 m1~m60，长端按 y10/y15/y20/y30（自循环衰减）

### 4.2 关键数据表

| 表名 | 模块 | 关键字段 |
|---|---|---|
| `prcp_coa_scheme` | 账户册 | id, scheme_code, scheme_name, node_count, status |
| `prcp_coa_node` | 账户册 | id, scheme_id, node_code, node_name, parent_id, node_level, node_type, path, sort_order |
| `prcp_data_basic` | 基础数据 | coa_node_id, data_date, orig_m1~orig_y30, rem_m1~rem_y30, asf_rsf, hqla_factor, weighted_rate, risk_weight |
| `prcp_data_balance` | 资产负债表 | coa_node_id, data_date, balance, m1~m24 cashflow |
| `prcp_data_reverse` | 反算结果 | coa_node_id, run_id, date_offset(1~24) |
| `prcp_rpt_item` | 报表表项 | id, rpt_code, item_code, item_name, parent_id, node_level |
| `prcp_kpi_scheme` | 指标方案 | id, scheme_code, scheme_name |
| `prcp_kpi_definition` | 指标定义 | id, kpi_code, formula / script_path / script_name / indicator_type |
| `prcp_model` | 模型 | id, model_code, kpi_scheme_id, algorithm |
| `prcp_model_param` | 模型参数 | id, model_id, param_code, param_value |
| `prcp_reverse_scheme` | 反算方案 | id, scheme_code, coa_scheme_id, model_id, horizon_months |
| `prcp_reverse_target` | 反算目标 | id, scheme_id, kpi_id, target_value, constraint_type(GE/LE/EQ), weight, horizon_month |
| `prcp_reverse_run` | 反算执行 | id, scheme_id, status, optimal_value, end_at |
| `prcp_metric_coefficient` | 指标计量系数 | coa_scheme_code, node_code, metric_type, data_date, value |
| `prcp_sim_scheme` | 新业务模拟方案 | id, scheme_code, data_date(模拟起始月) |
| `prcp_sim_node_config` | 模拟节点配置 | id, scheme_id, coa_node_id, growth_rate, current_balance |
| `prcp_sim_term_ratio` | 期限占比 | id, scheme_id, node_id, term_type, ratio, interest_rate |
| `prcp_sim_run` | 模拟执行 | id, scheme_id, status, run_at |
| `prcp_sim_result` | 模拟结果 | id, run_id, coa_node_id, sim_scheme_code, date_offset, 64+64 桶 + 主指标 |
| `prcp_sim_engine_type` | 引擎类型注册表 | engine_type, engine_name, package |
| `sys_dict` | 字典 | dict_type, dict_code, dict_label, color |

> 完整字段定义见 `docs/PRCP数据库数据字典.xlsx`

---

## 5. 引擎架构（v3.5 重构）

```
backend/app/services/calculate_engine/
├── __init__.py           # 公共 API（get_engine / list_engine_types / register_engine）
├── base.py               # EngineBase 抽象基类（run / get_run / list_runs / list_results）
├── registry.py           # 线程安全注册表 + 工厂方法
└── new_business/         # 新业务模拟引擎
    ├── __init__.py       # 自动注册
    └── engine.py         # NewBusinessEngine（5 步：JOIN → 计算新业务 → 期限分布 → 桶往前推 → 主指标重算）
```

**调用示例**：
```python
from app.services.calculate_engine import get_engine
engine = get_engine("new_business")
run_id = engine.run(db, scheme_id=1, user={"id": 1}, month_count=60)
```

**新增引擎流程**：
1. 创建 `calculate_engine/<engine_type>/__init__.py` 和 `engine.py`
2. 类继承 `EngineBase` 设置 `engine_type / engine_name`
3. 子包 `__init__.py` 调 `register_engine()`
4. 在 `main.py` 加 import 触发注册

---

## 6. 目录结构

```
PRCP/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py / database.py / auth.py / models.py
│   │   ├── routers/             # auth/dashboard/coa/rpt/basic/kpi/model/reverse/sim/engines/system/dict
│   │   ├── services/
│   │   │   ├── buckets.py              # 64+64 桶共享定义
│   │   │   ├── kpi_function_runner.py # 函数指标执行器（白名单+importlib+热重载）
│   │   │   ├── reverse_calc_engine.py # 反算引擎（CVXPY QP + 64 桶 INSERT）
│   │   │   ├── formula_engine.py      # 公式解析 + 计算
│   │   │   ├── tree_builder.py        # 树形构建 + 拖拽排序
│   │   │   ├── excel_importer.py      # Excel 解析 + 校验
│   │   │   └── calculate_engine/      # 可扩展引擎包（v3.5 新增）
│   │   └── scripts/kpi_functions/     # 用户自定义函数指标
│   ├── scripts/                      # 初始化 / 迁移 / 数据生成脚本
│   ├── venv/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/index.ts              # 统一 axios 封装 + JWT 拦截器
│   │   ├── components/               # DictSelect / DictTag / Charts 等
│   │   ├── constants/buckets.ts      # 64+64 桶定义（与后端同步）
│   │   ├── layouts/MainLayout.tsx
│   │   ├── pages/                    # Dashboard/Coa/Rpt/Basic/Kpi/Model/Reverse/Sim/System
│   │   └── main.tsx
│   ├── public/prcp_icon.svg
│   └── vite.config.ts                # base=/prcp/ + /prcp/api proxy
└── docs/
    ├── README.md (本文件)
    ├── 产品原型设计_v4.md
    ├── 技术架构_v4.md
    ├── 数据库设计_v3.md
    ├── PRCP_需求说明书_v12_final.docx
    ├── PRCP数据库数据字典.xlsx
    ├── 产品功能菜单.xlsx
    └── … 旧版/分模块设计文档
```

---

## 7. 部署

### 7.1 本地启动

```bash
git clone git@github.com:ZhangHanghang123/PRCP.git
cd PRCP/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py     # 建库 + 建表 + admin
uvicorn app.main:app --host 0.0.0.0 --port 8006
```

### 7.2 服务器部署

```bash
# 后端
ssh almd@server
cd /home/almd/prcp
git pull origin main
echo 'almd' | sudo -S cp backend/app/routers/<file>.py /home/almd/prcp/backend/app/routers/<file>.py
echo 'almd' | sudo -S rm -f /home/almd/prcp/backend/app/routers/__pycache__/<file>.cpython-*.pyc
# kill 旧 PID（无 systemd；用 ps aux | grep 8006 查 PID）
PID=$(ps aux | grep 8006 | grep -v grep | awk '{print $2}' | head -1); kill $PID
cd /home/almd/prcp/backend && setsid nohup ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8006 --workers 1 --log-level info > /tmp/prcp_backend.log 2>&1 < /dev/null & disown

# 前端
cd frontend && npm run build
scp dist/index.html dist/assets/index-<hash>.js dist/assets/index-<hash>.css almd@server:/tmp/prcp_dist/
echo 'almd' | sudo -S bash -c 'rm -f /var/www/prcp/assets/index-*.js /var/www/prcp/assets/index-*.css
                                cp /tmp/prcp_dist/index.html /var/www/prcp/index.html
                                cp /tmp/prcp_dist/assets/* /var/www/prcp/assets/
                                chown root:root /var/www/prcp/index.html /var/www/prcp/assets/*'
rm -f /tmp/prcp_dist/*
```

### 7.3 公网访问

`https://wxfzhh.online/prcp/`

### 7.4 部署踩坑速查

| 现象 | 原因 | 解决 |
|---|---|---|
| vite build failed: safe-delete dist/prcp_icon.svg | IDE 占用 | `npx vite build --emptyOutDir=false` |
| deploy 后 404 index-XXXX.js | hash 漂移只复制了 index.html | 一定要 scp 当前 hash 的 js/css 全套 |
| 服务器 rm/cp assets/* 报 Permission denied | `/var/www/prcp/assets/` 是 root:root 拥有 | `echo 'almd' \| sudo -S bash -c '...'` |
| restart backend 失败 (bind address in use) | 旧 PID 没 kill | `kill <PID>` 后 setsid nohup 启动 |

---

## 8. 公网入口与演示数据

- **入口**：`https://wxfzhh.online/prcp/`
- **演示账户册方案**：`ZX_CITIC_2026`（中信银行账户册，38 节点，2026-09 新增）
- **演示基础数据**：`ZX_CITIC_2026 / 2025-12-31`（中信银行 2025 年报模拟，38 行 × 145 列）

---

## 9. 后续规划

- 接入 ALMT 的业务计划作为头寸输入（自动同步到 PRCP 资产负债表）
- 接入 CURV 的收益率曲线作为 FTP 定价依据（自动同步到 PRCP 利率管理）
- 接入 ALMD 的流动性指标作为限额约束（LCR/NSFR 试算）
- 引擎包扩展：组合反演、压力测试、缺口预测 等 3 个新引擎
- 规则引擎升级：图规则 + 优先级调度（历史 v1 时代的资金组算规则，保留为可复用引擎之一）

---

## 10. 文档索引

| 文档 | 说明 |
|---|---|
| `docs/PRCP_需求说明书_v12_final.docx` | 业务需求（最近定版） |
| `docs/产品原型设计_v4.md` | 产品原型（v4 含新业务模拟） |
| `docs/技术架构_v4.md` | 技术架构（v4 含引擎包） |
| `docs/数据库设计_v3.md` | 数据库设计（v3 含 sim_* 表） |
| `docs/PRCP数据库数据字典.xlsx` | 36 张表 × 全字段说明 |
| `docs/产品功能菜单.xlsx` | 21 行功能菜单矩阵 |
| `docs/新业务模拟_*.md` | 新业务模拟子模块设计 |
| `docs/利率管理模块设计.md` | 利率采集与曲线管理 |
| `docs/模型管理模块设计.md` | 模型版本 + 训练 |
| `docs/指标计量系数维护_设计文档.md` | 5 大指标体系（ROE/CET1/LCR/NSFR/DELTA_EVE） |
| `docs/PRCP_需求问题清单与优化建议_快速上线版.md` | 71 页需求 vs 50 项问题清单 |
| `docs/反算结果展示_设计说明.md` | 反算结果表展示设计 |