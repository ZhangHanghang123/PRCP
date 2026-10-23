# PRCP 功能清单（按钮级） — 供 Java 版本功能映射参考

> **目的**：列出 PRCP 前端每个页面、所有按钮/操作的入口、功能说明与关键 API，方便 Java 版做 1:1 功能映射。
>
> **生成日期**：2026-09-26
> **前端栈**：React 18 + TS + AntD 5 + ECharts
> **后端栈**：FastAPI + SQLAlchemy + MySQL 8
> **服务端口**：8006 / 子路径 `/prcp/api` / 公网 `https://wxfzhh.online/prcp/`

---

## 0. 总体模块清单

| # | 一级模块 | 路由 | 子页面 | 关键页面 |
|---|---|---|---|---|
| 1 | 登录 | `/login` | — | Login |
| 2 | Dashboard | `/dashboard` | — | ReverseDashboard |
| 3 | 账户册维护 | `/coa` | 方案 / 节点 | COA |
| 4 | 报表表项 | `/rpt` | 报表 / 表项 | Reports |
| 5 | 数据维护 | `/basic` `/data` `/balance` | 9 类数据 | DataMaint / BasicDataSheet / BalanceSheet |
| 6 | 指标管理 | `/kpi` | 方案/定义/试算 | KPI / KpiScore |
| 7 | 模型管理 | `/model` | 模型/版本/参数/训练 | ModelManage |
| 8 | 指标计量系数 | `/metric-coefficient` | — | MetricCoefficient |
| 9 | 组合反算 | `/reverse` | 方案/目标/运行 | ReverseCalc |
| 10 | 反算驾驶舱 | `/dashboard` | — | ReverseDashboard |
| 11 | 反算结果查询 | `/reverse-result` | — | ReverseResult |
| 12 | 反算指标结果表 | `/reverse-metric-table` | — | ReverseMetricTable |
| 13 | 新业务模拟 | `/sim` | 列表/配置/结果 | SimSchemeList / SimConfigPage / SimResultPage |
| 14 | 利率管理 | `/rate` | 曲线/期限/利率 | RateCurve |
| 15 | 系统管理 | `/system` | 用户/角色/字典 | System |
| 16 | ESG | `/esg/*` | 方案/曲线/结果 | EsgSchemes / EsgCurve / EsgResults |

---

## 1. 登录（Login）

### 1.1 页面元素
| # | 类型 | 名称 / 字段 | 功能说明 |
|---|---|---|---|
| 1.1.1 | 输入框 | 用户名（admin） | 登录账号 |
| 1.1.2 | 输入框 | 密码（admin123） | 登录密码 |
| 1.1.3 | 按钮 | **登录** | POST `/auth/login` → JWT token，存 localStorage + 跳转 `/dashboard` |
| 1.1.4 | 按钮 | **重置** | 清空用户名/密码输入 |

---

## 2. 账户册维护（COA）

### 2.1 账户册方案（顶部列表）
| # | 按钮 / 操作 | 功能说明 | 触发 API |
|---|---|---|---|
| 2.1.1 | 表格列：方案树（Code + Name） | 展示所有账户册方案（scheme_code · scheme_name） | GET `/coa/schemes` |
| 2.1.2 | 表格列：节点数 | 显示每方案的总节点数 | — |
| 2.1.3 | **🆕 新增方案** 按钮 | 弹出 Modal：填 `scheme_code` / `scheme_name` / `description`，提交新建 | POST `/coa/schemes` |
| 2.1.4 | 操作列：**编辑** | Modal 修改方案名/描述 | PUT `/coa/schemes/{id}` |
| 2.1.5 | 操作列：**删除** | 软删当前方案（级联软删节点） | DELETE `/coa/schemes/{id}` |

### 2.2 账户册节点（左侧树 + 右侧详情）
| # | 按钮 / 操作 | 功能说明 | 触发 API |
|---|---|---|---|
| 2.2.1 | DirectoryTree | L1~L5 多级树形（编码 + 名称 + 节点数 Tag） | GET `/coa/nodes/tree?scheme_id=` |
| 2.2.2 | 选中节点 → 右侧详情 | 显示 `node_code` / `node_name` / `node_level` / `parent_code` / `category` / `sort_order` | GET `/coa/nodes/{id}` |
| 2.2.3 | **🆕 新增根节点** | 在 L1 末尾添加新节点 | POST `/coa/nodes` |
| 2.2.4 | **🆕 新增子节点** | 在当前选中节点下添加子节点（parent 自动绑定） | POST `/coa/nodes` |
| 2.2.5 | 右侧表单：编辑 | 改 `node_name` / `sort_order` / `category` | PUT `/coa/nodes/{id}` |
| 2.2.6 | **删除** 按钮 | 软删当前节点（递归删除所有子节点） | DELETE `/coa/nodes/{id}` |
| 2.2.7 | **📥 导入 Excel** | 弹上传对话框，列：编码/名称/层级/父级编码/末级 → 批量 POST | POST `/coa/import` |
| 2.2.8 | **📤 导出 Excel** | 导出当前方案全量节点 | GET `/coa/export?scheme_id=` |
| 2.2.9 | **刷新** | 重载树 + 列表 | GET `/coa/nodes/tree` |

---

## 3. 报表表项管理（Reports）

### 3.1 报表定义（列表）
| # | 按钮 | 功能说明 | 触发 API |
|---|---|---|---|
| 3.1.1 | 报表列表（card 切换） | 切换不同报表（账务结果/关键参数/规模/价格/中收/RWA 等） | GET `/rpt/reports` |
| 3.1.2 | **🆕 新增报表** | Modal：填 `report_code` / `report_name` / `category` | POST `/rpt/reports` |
| 3.1.3 | **编辑** | 修改报表名/类别 | PUT `/rpt/reports/{id}` |
| 3.1.4 | **删除** | 软删报表 | DELETE `/rpt/reports/{id}` |

### 3.2 报表表项（树 + 详情）
| # | 按钮 | 功能说明 | 触发 API |
|---|---|---|---|
| 3.2.1 | DirectoryTree | 报表表项树（item_code · item_name） | GET `/rpt/items?report_id=` |
| 3.2.2 | **🆕 新增根表项** | L1 表项 | POST `/rpt/items` |
| 3.2.3 | **🆕 新增子表项** | 当前节点下添加子表项 | POST `/rpt/items` |
| 3.2.4 | **编辑** | 改 item_name / 取数逻辑（公式 / COA 节点引用） | PUT `/rpt/items/{id}` |
| 3.2.5 | **删除** | 软删表项（递归删除子表项） | DELETE `/rpt/items/{id}` |
| 3.2.6 | **📥 导入** | Excel 上传 → 批量 POST | POST `/rpt/items/import` |
| 3.2.7 | **📤 导出** | 当前报表全量表项 | GET `/rpt/items/export` |

---

## 4. 数据维护（DataMaint · 9 类数据统一面板）

| # | 类型卡 | 功能说明 | API |
|---|---|---|---|
| 4.1 | **账务结果指标** | 按方案+数据日期录入账务结果（取数逻辑：COA 节点引用） | GET/POST/PUT/DELETE `/data/account-result` |
| 4.2 | **关键参数指标** | 同上，参数类（折算率、税率等） | `/data/key-param` |
| 4.3 | **规模指标** | 余额类（资产/负债/贷款/存款规模） | `/data/scale` |
| 4.4 | **价格指标** | 利率/价格类 | `/data/price` |
| 4.5 | **中收指标** | 中间业务收入（手续费、佣金） | `/data/fee` |
| 4.6 | **资本与 RWA 假设指标** | 风险加权资产假设 | `/data/rwa` |
| 4.7 | **按月出指标** | 计算 6 类指标 = f(基础数据表 + 报表表项) | POST `/data/calc-monthly` |

### 4.1~4.6 通用数据面板按钮
| # | 按钮 | 功能说明 |
|---|---|---|
| 4.X.1 | **📥 导入 Excel** | 上传 9 类指标的 Excel 模板 |
| 4.X.2 | **📤 导出 Excel** | 当前数据日期+方案的全量数据 |
| 4.X.3 | **刷新** | 重载表格 |
| 4.X.4 | **🆕 新增记录** | Modal：选 COA 节点 + 录入数据 + 取数逻辑 |
| 4.X.5 | 操作列：**编辑** | 修改数据 |
| 4.X.6 | 操作列：**删除** | 软删 |

---

## 5. 基础数据表（BasicDataSheet）

### 5.1 主表格（64+64 桶矩阵）
| # | 按钮 / 操作 | 功能说明 | API |
|---|---|---|---|
| 5.1.1 | Select：账户册方案 | 切换账户册方案（默认 ZX_CITIC_2026） | GET `/coa/schemes?status=ACTIVE` |
| 5.1.2 | DatePicker：数据日期 | 选择 `data_date`（默认 2025-12-31） | — |
| 5.1.3 | Select：偏移月 | `date_offset`（0/1/3/6/12） | — |
| 5.1.4 | 表格：账户册矩阵 | 行：L1~L3 节点，列：原始·1M~30Y + 剩余·1M~30Y + 度量 | GET `/basic/by-scheme-matrix?scheme_id&data_date&date_offset` |
| 5.1.5 | **📤 导出 Excel** | 145 列 xlsx，3 行表头（L1 浅蓝 / L2 更浅蓝 / L3+ 普通） | GET `/basic/export-xlsx` |
| 5.1.6 | **📥 导入 Excel** | 上传批量数据 | POST `/basic/import` |
| 5.1.7 | **刷新** | 重载矩阵 | — |
| 5.1.8 | **🆕 新增记录** | Modal：节点+64+64 桶+度量 | POST `/basic/` |

---

## 6. 资产负债表（BalanceSheet）

| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 6.1 | Select：账户册方案 | 切换方案 | GET `/coa/schemes?status=ACTIVE` |
| 6.2 | DatePicker：数据日期 | 选择日期 | — |
| 6.3 | Select：偏移月 | 0~24 月 | — |
| 6.4 | 表格：24 月现金流 | 行：节点，列：M0~M24 现金流缺口 + balance | GET `/balance/by-scheme-matrix` |
| 6.5 | **📤 导出 Excel** | 多 Sheet 导出 | GET `/balance/export-xlsx` |
| 6.6 | **📥 导入 Excel** | 批量导入 | POST `/balance/import` |
| 6.7 | **🆕 新增月度数据** | Modal：选节点+月份+金额 | POST `/balance/` |
| 6.8 | **刷新** | — | — |

---

## 7. 指标管理（KPI）

### 7.1 指标方案（顶部 Tab）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 7.1.1 | Tab 切换：方案 | 切换指标方案 | GET `/kpi/schemes` |
| 7.1.2 | **🆕 新增方案** | Modal：scheme_code/scheme_name | POST `/kpi/schemes` |
| 7.1.3 | 操作：**编辑** / **删除** | 方案 CRUD | PUT/DELETE `/kpi/schemes/{id}` |

### 7.2 指标定义（公式 + 函数双指标）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 7.2.1 | **🆕 新增指标** | Modal：kpi_code/kpi_name/indicator_type/formula/script | POST `/kpi/definitions` |
| 7.2.2 | **编辑** | 修改公式/脚本 | PUT `/kpi/definitions/{id}` |
| 7.2.3 | **删除** | 软删 | DELETE `/kpi/definitions/{id}` |
| 7.2.4 | 公式编辑器工具栏 | 函数按钮：`ABS / AVG / COUNT / IF / MAX / MIN / ROUND / SUM / == / >=` + 退格 + 清空 | — |
| 7.2.5 | **试算** | 选数据日期 → 实时计算指标值 | GET `/kpi/score-calc` |

### 7.3 指标值维护
| # | 按钮 | 功能说明 |
|---|---|---|
| 7.3.1 | **🆕 新增指标值** | 选方案+指标+日期，录入版本与值 |
| 7.3.2 | **重算** | 重算所有指标 |
| 7.3.3 | **编辑 / 删除** | 指标值 CRUD |

---

## 8. 评分规则（KpiScore）

| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 8.1 | Select：评分方案 | 切换 | GET `/kpi/score-rules?scheme_id` |
| 8.2 | **🆕 新增规则** | Modal：rule_code/min_value/max_value/grade/description | POST `/kpi/score-rules` |
| 8.3 | 操作：**编辑 / 删除** | 规则 CRUD | PUT/DELETE `/kpi/score-rules/{id}` |
| 8.4 | **添加段** | 给规则加分段（min/max + grade） | POST `/kpi/score-segments` |
| 8.5 | **刷新** | — | — |

---

## 9. 模型管理（ModelManage）

### 9.1 模型列表
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 9.1.1 | **🆕 新建模型** | Modal：model_code/model_name/algorithm/kpi_scheme_id | POST `/model` |
| 9.1.2 | 操作：**编辑 / 删除** | 模型 CRUD | PUT/DELETE `/model/{id}` |
| 9.1.3 | **参数** | 跳转模型参数页 | `/model/params/{id}` |
| 9.1.4 | **结果** | 跳转训练结果页 | `/model/results/{id}` |
| 9.1.5 | **日志** | 弹出 Drawer：训练日志（轮询） | GET `/model/{id}/logs` |

### 9.2 模型版本
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 9.2.1 | **🆕 新建版本** | Modal：version_code/version_name/parent_id | POST `/model/versions` |
| 9.2.2 | **复制** | 从父版本复制参数 | POST `/model/versions/copy` |
| 9.2.3 | **管理 / 取消** | 激活/停用版本 | PUT `/model/versions/{id}` |

### 9.3 模型训练
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 9.3.1 | **启动** | 选版本+数据日期+超参数 → 启动训练 | POST `/model/{id}/train` |
| 9.3.2 | **取消** | 中断训练 | POST `/model/train/cancel` |

### 9.4 模型参数
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 9.4.1 | **🆕 新增参数** | Modal：param_code/param_value/data_type/category | POST `/model/params` |
| 9.4.2 | 操作：**编辑 / 删除 / 复制** | — | — |

---

## 10. 指标计量系数维护（MetricCoefficient）

| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 10.1 | Select：账户册方案 | 默认 ZX_CITIC_2026 | GET `/coa/schemes` |
| 10.2 | Select：指标类型 | ROE / CET1 / LCR / NSFR / DELTA_EVE | — |
| 10.3 | DatePicker：数据日期 | 默认 2025-12-31 | — |
| 10.4 | 表格：5 指标 × 节点 × 多期数值 | 显示按方案+指标的矩阵 | GET `/metric-coefficient/list` |
| 10.5 | **📥 导入 Excel** | 批量导入 | POST `/metric-coefficient/import` |
| 10.6 | **重置** | 清空筛选 | — |
| 10.7 | 操作：**编辑 / 删除** | 单条 CRUD | PUT/DELETE `/metric-coefficient/{id}` |

---

## 11. 组合反算（ReverseCalc）

### 11.1 反算方案列表
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 11.1.1 | **🆕 新建方案** | Modal：scheme_code/scheme_name/coa_scheme_id（动态下拉）/algorithm/model_id/horizon_months | POST `/reverse/schemes` |
| 11.1.2 | **编辑** | 方案 CRUD | PUT `/reverse/schemes/{id}` |
| 11.1.3 | **删除** | 软删 | DELETE `/reverse/schemes/{id}` |
| 11.1.4 | **结果** | 跳转到反算结果查询 | `/reverse-result` |
| 11.1.5 | 操作：**启动** | 启动反算（CVXPY QP 求解） | POST `/reverse/runs` |
| 11.1.6 | 操作：**日志** | Drawer 轮询训练日志 | GET `/reverse/runs/{id}/logs` |
| 11.1.7 | 操作：**取消** | 中断 | POST `/reverse/runs/{id}/cancel` |

### 11.2 目标配置
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 11.2.1 | **🆕 新增目标** | Modal：scheme_id（自动锁定）/kpi_id/target_value/constraint_type/weight/horizon_month（target_name 自动生成） | POST `/reverse/targets` |
| 11.2.2 | 操作：**编辑 / 删除** | 目标 CRUD | PUT/DELETE `/reverse/targets/{id}` |

---

## 12. 反算驾驶舱（ReverseDashboard）

> 首页（`/dashboard` 路由指向 ReverseDashboard）

| # | 元素 | 功能说明 | API |
|---|---|---|---|
| 12.1 | 8 大 KPI 卡片 | ROE/CET1/LCR/NSFR/NIM/NPL/IRR/DELTA_EVE 当前值 | GET `/reverse/dashboard/summary` |
| 12.2 | 5 指标趋势图（ECharts LineChart） | 24 月指标变化趋势 | GET `/reverse/dashboard/trend` |
| 12.3 | 大类分布图（PieChart） | 资产/负债/权益占比 | GET `/reverse/dashboard/category` |
| 12.4 | 节点热力图（Heatmap） | 节点 × 指标的取值热度 | GET `/reverse/dashboard/heatmap` |
| 12.5 | Top 10 表格 | 最优/最差节点 | GET `/reverse/dashboard/top` |
| 12.6 | 风险预警列表 | 超阈值指标告警 | GET `/reverse/dashboard/alert` |

---

## 13. 反算结果查询（ReverseResult）

| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 13.1 | Select：反算方案 | 切换（默认 ZXCOA_V1 / 2026） | GET `/data-reverse/schemes` |
| 13.2 | Select：Run | 自动从方案拉取 SUCCESS runs | GET `/data-reverse/runs?scheme_code=` |
| 13.3 | DatePicker：数据日期 | 选择日期 | — |
| 13.4 | DatePicker：偏移月 | 1~24 | — |
| 13.5 | 表格：未来 24 月 × N 节点预测值 | 大表展示 | GET `/data-reverse/by-scheme-matrix` |
| 13.6 | **📤 导出 Excel** | 全量数据 | GET `/data-reverse/export-xlsx` |
| 13.7 | **刷新** | 重载 | — |

---

## 14. 反算指标结果表（ReverseMetricTable）

| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 14.1 | Select：反算方案 | 切换 | GET `/data-reverse/schemes` |
| 14.2 | Select：Run | 自动从方案拉 SUCCESS（useMemo derive 避免 stale） | GET `/data-reverse/runs` |
| 14.3 | Select：月份（M1~M24） | 切换预测月 | GET `/data-reverse/dates` |
| 14.4 | 表格：行=账户册节点 × 列=5 指标 | ROE / CET1 / LCR / NSFR / DELTA_EVE | GET `/metric-coefficient/reverse-table` |
| 14.5 | **📤 导出 CSV** | — | GET `/metric-coefficient/reverse-table?format=csv` |
| 14.6 | **刷新** | — | — |

---

## 15. 新业务模拟（SimSchemeList + SimConfigPage + SimResultPage）

### 15.1 方案列表（SimSchemeList）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 15.1.1 | **🆕 新建方案** | Modal：scheme_code/scheme_name/data_date/description | POST `/sim/schemes` |
| 15.1.2 | 操作：**编辑 / 删除** | 方案 CRUD（delete 级联软删节点+占比） | PUT/DELETE `/sim/schemes/{id}` |
| 15.1.3 | **参数配置** | 跳转到配置页（选账户册节点+增长率+期限占比+利率） | `/sim/config/{id}` |
| 15.1.4 | **🚀 引擎计量** | 启动引擎（disabled when config_node_count=0） | POST `/engines/run` |
| 15.1.5 | **📊 查看结果** | 跳转到结果页（已运行过的方案可点） | `/sim/result/{id}` |
| 15.1.6 | **重置 / 刷新** | — | — |

### 15.2 配置页（SimConfigPage）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 15.2.1 | DirectoryTree：账户册节点 | 选节点 → 自动添加进方案 | GET `/sim/tree?scheme_id=` |
| 15.2.2 | 已配置节点列表（表格） | 展示：node_code · node_name · current_balance · growth_rate · effective_month | GET `/sim/schemes/{id}/nodes/{nid}` |
| 15.2.3 | **🆕 新增行** | 添加节点配置（选 COA 节点 + 余额 + 增长率） | POST `/sim/schemes/{id}/save` |
| 15.2.4 | **保存** | 批量保存节点配置 + 期限占比 | POST `/sim/schemes/{id}/save` |
| 15.2.5 | **校验** | 校验期限占比合计 = 100%（失败回滚） | POST `/sim/schemes/{id}/validate` |
| 15.2.6 | 期限占比编辑（每节点 4 行） | SHORT / MID / LONG / STRUCT × ratio × interest_rate | POST `/sim/term-ratios` |
| 15.2.7 | **重置 / 删除** | — | — |

### 15.3 结果页（SimResultPage）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 15.3.1 | DirectoryTree + 节点 Tag | 已运行节点显示紫色「⚡ 已模拟」 | GET `/sim/tree` |
| 15.3.2 | 节点结果（表格） | date_offset × 64+64 桶 × 主指标 | GET `/engines/results` |
| 15.3.3 | **刷新** | — | — |

---

## 16. 利率管理（RateCurve）

### 16.1 曲线方案
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 16.1.1 | Select：曲线方案 | 切换 | GET `/rate/curves` |
| 16.1.2 | **🆕 新建曲线** | Modal：curve_code/curve_name/curve_type | POST `/rate/curves` |
| 16.1.3 | 操作：**编辑 / 删除 / 复制** | 曲线 CRUD | — |

### 16.2 期限点
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 16.2.1 | **🆕 新增日期** | Modal：数据日期 + 利率值矩阵（13/64 期限点） | POST `/rate/values` |
| 16.2.2 | **编辑** | 改利率 | PUT `/rate/values/{id}` |
| 16.2.3 | **查看** | Drawer：折线图 + 利差 | GET `/rate/values/{id}` |
| 16.2.4 | **📤 导出** | 下载 csv | GET `/rate/export` |
| 16.2.5 | **保存** | 批量保存 | — |

### 16.3 算法引擎（页面隐藏入口）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 16.3.1 | Svensson 拟合 | 6 参数拟合曲线 | POST `/rate/svensson` |
| 16.3.2 | NS / NSS 拟合 | Nelson-Siegel / Nelson-Siegel-Svensson | POST `/rate/ns` / `/rate/nss` |
| 16.3.3 | lookup_rate | 任意期限插值 | POST `/rate/lookup` |
| 16.3.4 | compare_curves | 多曲线对比 | POST `/rate/compare` |

---

## 17. 系统管理（System）

### 17.1 用户管理
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 17.1.1 | **🆕 新增用户** | Modal：username/password/role_id/email | POST `/system/users` |
| 17.1.2 | 操作：**编辑 / 重置密码 / 删除** | 用户 CRUD | PUT/POST/DELETE `/system/users/{id}` |

### 17.2 角色管理
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 17.2.1 | **🆕 新增角色** | Modal：role_code/role_name/permission_ids | POST `/system/roles` |
| 17.2.2 | 操作：**编辑 / 删除** | 角色 CRUD | — |

### 17.3 字典管理
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 17.3.1 | Select：字典分类 | 切换 dict_type | GET `/dict/items?dict_type=` |
| 17.3.2 | **🆕 新增字典项** | Modal：dict_code/dict_label/color | POST `/dict/items` |
| 17.3.3 | 操作：**编辑 / 删除** | 字典项 CRUD | PUT/DELETE `/dict/items/{id}` |

---

## 18. ESG（环境-社会-治理压力测试）

### 18.1 方案列表（EsgSchemes）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 18.1.1 | **🆕 新建方案** | Modal：scheme_code/scenario_type（PHYSICAL/TRANSITION） | POST `/esg/schemes` |
| 18.1.2 | **重置 / 刷新** | — | — |

### 18.2 方案详情（EsgSchemeDetail）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 18.2.1 | 曲线配置（运行场景参数） | 填入：碳价路径 / 政策强度 / 物理灾害发生率 | PUT `/esg/schemes/{id}/curve` |
| 18.2.2 | **下载 .npz** | 训练样本下载 | GET `/esg/schemes/{id}/sample` |

### 18.3 曲线管理（EsgCurve）
| # | 元素 | 功能说明 | API |
|---|---|---|---|
| 18.3.1 | ECharts 折线图 | 多场景曲线叠加 | GET `/esg/curves/{scheme_id}` |

### 18.4 结果展示（EsgResults）
| # | 按钮 | 功能说明 | API |
|---|---|---|---|
| 18.4.1 | 表格：节点 × 期 × EAD/EL/UL | 三类指标 | GET `/esg/results` |
| 18.4.2 | **下载** | CSV 下载 | GET `/esg/results/export` |
| 18.4.3 | 操作：**详情** | Drawer：节点级明细 | GET `/esg/results/{id}` |
| 18.4.4 | **刷新** | — | — |

---

## 19. 全局通用按钮（跨页面）

| 按钮 | 出现页面 | 功能说明 |
|---|---|---|
| **刷新** | 几乎所有列表页 | 重新拉取 GET API |
| **重置** | 所有带筛选的页面 | 清空 Select / DatePicker / Input |
| **📥 导入 Excel** | COA、RPT、BasicData、BalanceSheet、MetricCoefficient、DataMaint×6 | 上传 Excel 模板 → 批量 POST |
| **📤 导出 Excel/CSV** | BasicData、BalanceSheet、ReverseResult、ReverseMetricTable | 下载全量数据 |
| **🔍 编辑** | 所有 CRUD 列表 | 弹出 Modal 编辑当前行 |
| **🗑 删除** | 所有 CRUD 列表 | 软删（多带 confirm Popconfirm） |
| **🆕 新增** | 所有 CRUD 列表 | 弹出 Modal 新增记录 |

---

## 20. 关键 API 路径汇总（供 Java 后端 1:1 实现）

```
认证
POST   /auth/login                        JWT 登录
POST   /auth/logout                       登出

账户册
GET    /coa/schemes                       方案列表
POST   /coa/schemes                       新建
PUT    /coa/schemes/{id}
DELETE /coa/schemes/{id}
GET    /coa/nodes/tree?scheme_id=         节点树
GET    /coa/nodes?scheme_id=              节点列表
POST   /coa/nodes
PUT    /coa/nodes/{id}
DELETE /coa/nodes/{id}
POST   /coa/import                        Excel 导入
GET    /coa/export?scheme_id=             Excel 导出

报表
GET    /rpt/reports                       报表列表
POST   /rpt/reports
GET    /rpt/items?report_id=              表项树
POST   /rpt/items
PUT    /rpt/items/{id}
DELETE /rpt/items/{id}
POST   /rpt/items/import

数据维护（9 类）
GET/POST/PUT/DELETE /data/{category}      account-result / key-param / scale / price / fee / rwa
POST   /data/calc-monthly                 按月出指标

基础数据
GET    /basic/by-scheme-matrix            矩阵
GET    /basic/export-xlsx                 导出
POST   /basic/import
POST   /basic/                            CRUD
DELETE /basic/{id}
GET    /basic/dates?scheme_id=            已录入日期列表

资产负债表
GET    /balance/by-scheme-matrix
GET    /balance/export-xlsx
POST   /balance/import
POST   /balance/

指标
GET    /kpi/schemes
POST   /kpi/schemes
PUT    /kpi/schemes/{id}
DELETE /kpi/schemes/{id}
GET    /kpi/definitions?scheme_id=
POST   /kpi/definitions
PUT    /kpi/definitions/{id}
DELETE /kpi/definitions/{id}
GET    /kpi/values?scheme_id=&data_date=
POST   /kpi/values
POST   /kpi/score-calc                    试算

评分
GET    /kpi/score-rules
POST   /kpi/score-rules
PUT    /kpi/score-rules/{id}
DELETE /kpi/score-rules/{id}
POST   /kpi/score-segments
DELETE /kpi/score-segments/{id}

模型
GET    /model                             模型列表
POST   /model
PUT    /model/{id}
DELETE /model/{id}
GET    /model/versions?model_id=
POST   /model/versions
POST   /model/versions/copy
GET    /model/params?model_id=
POST   /model/params
POST   /model/{id}/train                  启动训练
POST   /model/train/cancel
GET    /model/{id}/logs                   训练日志（轮询）
GET    /model/results?model_id=

指标计量系数
GET    /metric-coefficient/list
GET    /metric-coefficient/reverse-table  5 指标矩阵
POST   /metric-coefficient/
PUT    /metric-coefficient/{id}
DELETE /metric-coefficient/{id}
POST   /metric-coefficient/import

组合反算
GET    /reverse/schemes
POST   /reverse/schemes
PUT    /reverse/schemes/{id}
DELETE /reverse/schemes/{id}
GET    /reverse/targets?scheme_id=
POST   /reverse/targets
PUT    /reverse/targets/{id}
DELETE /reverse/targets/{id}
POST   /reverse/runs                      启动反算
GET    /reverse/runs/{id}                 Run 详情
GET    /reverse/runs?scheme_id=
POST   /reverse/runs/{id}/cancel
GET    /reverse/runs/{id}/logs
GET    /reverse/model-options
GET    /reverse/kpi-options

数据反算
GET    /data-reverse/schemes
GET    /data-reverse/runs?scheme_code=
GET    /data-reverse/by-scheme-matrix
GET    /data-reverse/dates?scheme_code=
GET    /data-reverse/export-xlsx

仪表盘
GET    /reverse/dashboard/summary
GET    /reverse/dashboard/trend
GET    /reverse/dashboard/category
GET    /reverse/dashboard/heatmap
GET    /reverse/dashboard/top
GET    /reverse/dashboard/alert

新业务模拟
GET    /sim/schemes
POST   /sim/schemes
PUT    /sim/schemes/{id}
DELETE /sim/schemes/{id}
GET    /sim/tree?scheme_id=               账户册树
GET    /sim/schemes/{id}/nodes/{nid}
POST   /sim/schemes/{id}/save             批量保存配置
POST   /sim/schemes/{id}/validate         校验占比
GET    /sim/term-ratios?scheme_id=
POST   /sim/term-ratios
PUT    /sim/term-ratios/{id}

引擎
GET    /engines
GET    /engines/run-types                 引擎类型列表
POST   /engines/run                       启动
GET    /engines/runs/{id}                 执行状态
GET    /engines/runs                      执行列表
GET    /engines/results                   结果查询

利率
GET    /rate/curves
POST   /rate/curves
PUT    /rate/curves/{id}
GET    /rate/values?curve_id=&date=
POST   /rate/values
PUT    /rate/values/{id}
POST   /rate/svensson
POST   /rate/ns
POST   /rate/nss
POST   /rate/lookup
POST   /rate/compare
GET    /rate/export

系统
GET    /system/users
POST   /system/users
PUT    /system/users/{id}
POST   /system/users/{id}/reset-password
DELETE /system/users/{id}
GET    /system/roles
POST   /system/roles
GET    /system/permissions

字典
GET    /dict/types
GET    /dict/items?dict_type=
POST   /dict/items
PUT    /dict/items/{id}
DELETE /dict/items/{id}

ESG
GET    /esg/schemes
POST   /esg/schemes
PUT    /esg/schemes/{id}
GET    /esg/curves/{scheme_id}
GET    /esg/results?scheme_id=
GET    /esg/results/{id}
GET    /esg/results/export
```

---

## 21. Java 版本映射建议

| 类型 | Python (FastAPI) | Java (Spring Boot 2.7 + MyBatis-Plus) |
|---|---|---|
| 路由 | `@router.get(...)` | `@GetMapping(...)` |
| ORM | SQLAlchemy 2 + pymysql | MyBatis-Plus 3.5.5 + Druid |
| 校验 | Pydantic 2 | Jakarta Bean Validation + Hibernate Validator |
| 认证 | python-jose + passlib | JJWT + BCryptPasswordEncoder |
| 异步 | FastAPI 协程 | Spring `@Async` + WebFlux / 同步 |
| 桶定义 | `buckets.py` 常量数组 | `Buckets.java` 常量数组（`orig_m1...orig_y30`） |
| 树形 | 物化路径 + LIKE | 物化路径 + 递归 CTE（PostgreSQL/H2）/ 或 path LIKE |
| 软删除 | `is_deleted=1` | `@TableLogic` MyBatis-Plus 注解 |
| 字典 | sys_dict + DictProvider | 注入 `@ConfigurationProperties` |
| 反算求解 | `cvxpy` + `QP` | `JOptimizer` / `ojAlgo` / `EJC` |
| 文件上传 | `python-multipart` | Spring MultipartFile |
| 时间 | `dayjs` | `day.js`（前端同款） |

---

## 22. 文档版本

- v1.0（2026-09-26）— 初版，按当前前端 pages/*.tsx 抓取所有按钮 + API
- 总功能模块：16 个 + 全局通用 7 类按钮
- 总 API 端点：约 130 个（按 prefix 分类）
- 配套 Excel 输出：`docs/PRCP功能清单_按钮级.xlsx`（可选后续生成）