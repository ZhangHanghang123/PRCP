# PRCP · 组算平台（Portfolio Resource Coordination Platform）

PRCP 是银行经营系列平台中的**第 6 个模块**，专注"资金组算与头寸调度"业务链路。

## 1. 业务定位

PRCP 与现有 5 模块（ALMD / IALMD / ALMT / CURV / IALM / ZHZC）形成互补闭环：

| 模块 | 核心 | 关系 |
|------|------|------|
| ALMT | 资产负债管理 / 业务分摊 | 上游（生成业务计划） |
| ALMD | 资本充足 / 流动性 | 风险约束 |
| IALM | 保险资产负债 | 行业垂直 |
| CURV | 收益率曲线 | 利率输入 |
| **PRCP** | **资金组算 / 头寸调度** | **执行层** |
| ZHZC | 智能分析 / 对话 | 智能层 |

## 2. 技术栈

- **后端**：FastAPI + SQLAlchemy 2 + PyMySQL + JWT（8006 端口，子路径 `/prcp/api`）
- **前端**：React 18 + TypeScript + Vite + AntD 5 + ECharts
- **数据库**：MySQL `prcp_db`，账号 `prcp / Prcp@2026`
- **统一风格**：蓝紫渐变 `#667eea → #764ba2` + 鼎形"组算"图标
- **登录**：默认 `admin / admin123`

## 3. 业务模块

| 路由 | 模块 | 关键实体 |
|------|------|----------|
| `/dashboard` | 总览 | KPI / 任务趋势 / 币种分布 |
| `/groups` | 资金组管理 | `prcp_group`（头寸组 / 限额组 / 调度组） |
| `/positions` | 头寸管理 | `prcp_position`（IN/OUT 头寸 + 缺口分析） |
| `/rules` | 组算规则 | `prcp_rule`（内部调拨 / 同业拆借 / 回购等） |
| `/tasks` | 组算任务 | `prcp_task` + `prcp_task_log`（撮合执行 + 流水） |

## 4. 核心业务流

```
[资金组] → 维护头寸组、限额组
   ↓
[头寸] → 录入待调度的调入/调出头寸
   ↓
[规则] → 配置撮合规则（阈值、优先级、动作）
   ↓
[任务] → 新建组算任务 → 执行 → 自动撮合 → 写流水
   ↓
[流水] → 逐任务保存执行结果（JSON），可回溯
```

## 5. 目录结构

```
PRCP/
├── backend/
│   ├── app/
│   │   ├── config.py            # 配置（DB/JWT）
│   │   ├── database.py          # SQLAlchemy 引擎
│   │   ├── auth.py              # JWT + 密码哈希
│   │   ├── main.py              # FastAPI 入口
│   │   └── routers/             # auth/dashboard/groups/positions/rules/tasks
│   ├── scripts/init_db.py       # 一键建库 + 建表 + 演示数据
│   ├── run.sh                   # uvicorn 启动
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/                 # axios 封装 + token 拦截器
    │   ├── layouts/MainLayout.tsx
    │   ├── pages/               # Login/Dashboard/Groups/Positions/Rules/Tasks
    │   ├── index.css            # 蓝紫渐变主题
    │   └── main.tsx
    ├── public/prcp_icon.svg     # 鼎形"组算"图标
    └── vite.config.ts           # base=/prcp/ + /prcp/api proxy
```

## 6. 部署

```bash
# 本地
git clone git@github.com:ZhangHanghang123/PRCP.git
cd PRCP

# 后端
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py   # 建库 + 建表 + 演示数据 + admin
uvicorn app.main:app --host 0.0.0.0 --port 8006

# 前端
cd ../frontend && npm install && npm run build
# dist 部署到 /var/www/prcp/
```

线上访问：`https://wxfzhh.online/prcp/`

## 7. 后续规划

- 接入 ALMT 的业务计划作为头寸输入
- 接入 CURV 的收益率曲线作为 FTP 定价依据
- 接入 ALMD 的流动性指标作为限额约束
- 规则引擎升级：图规则 + 优先级调度