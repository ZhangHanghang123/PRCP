# PRCP CHANGELOG

> 所有重要改动记录，按时间倒序

## 2026-09-23 — v3.1 / v3.0 / v2.9 三大版本迭代

### v3.1 — 名称反显优化 + 默认查询

| Commit | 类型 | 内容 |
|--------|------|------|
| e351772 | fix(display) | 反算驾驶舱 + 指标计量系数 账户册方案/编码反显为名称 |
| 5d1f3cd | fix(metric-coefficient) | 页面默认查询条件改为 ZXCOA_V1 + ROE + 2026-01-01 |
| 0bc8751 | feat(dashboard) | 用指标反算驾驶舱替换 Dashboard 页 |

**Dashboard 升级**：
- `/dashboard` 路由指向 `pages/ReverseDashboard`
- 删除 `/reverse-dashboard` 路由（被 catch-all 重定向到 `/dashboard`）
- MainLayout.tsx：删除「12. 组合反算 · 结果驾驶舱」菜单项（已升为首页）

**名称反显**：
- `ReverseDashboard.tsx`：账户册方案 Tag 从只显示 code → code + name
- `MetricCoefficient.tsx`：表格列「账户册方案」「账户册编码」改为 Tag + 灰色文字

### v3.0 — 反算指标结果表 + 演示数据 + 驾驶舱

| Commit | 类型 | 内容 |
|--------|------|------|
| c9c372d | feat(reverse-dashboard) | 组合反算 · 结果驾驶舱 v1.0（4 endpoint + 5 KPI + 趋势 + 分布 + 热力图 + Top + 预警） |
| d264fcd | feat(reverse-metric-table) | 数据维护 → 反算指标结果表 v1.0 |
| 60ebc98 | feat(seed) | 反算方案 2026 演示数据生成脚本（960 + 4800 行） |

**4 大新模块/能力**：

| 模块 | 路径 | 关键能力 |
|------|------|----------|
| 组合反算 · 结果驾驶舱 | `/dashboard`（首页） | 8 KPI + 5 指标趋势 + 大类分布 + 节点热力图 + Top 10 + 风险预警 |
| 反算指标结果表 | `/reverse-metric-table` | 行=账户册 × 列=5 指标 × 按月份联动 |
| 指标计量系数维护 | `/metric-coefficient` | 5 指标 × 节点 × 6 期数值 |
| 反算方案 2026 演示数据 | `seed_2026_demo.py` | 40 节点 × 24 月 × 5 指标 |

### v2.9 — 指标计量系数维护

| Commit | 类型 | 内容 |
|--------|------|------|
| e6af9dd | feat(metric-coefficient) | 数据维护 → 指标计量系数维护 v1.0（10 号） |

### v2.8 — ESG 场景工厂

| Commit | 类型 | 内容 |
|--------|------|------|
| 46d61c4 | feat(esg) | ESG 工厂 v1.0（Svensson + PCA + HJM + 情景集，22 endpoint） |
| de3c145 | fix(esg/curve) | sources 加载后不再覆盖默认 source |
| 2a4f2e7 | feat(esg) | v2 schema 升级 - B+D 方案（blob + 9 JSON） |

---

## Bug 修复清单（本次迭代累计）

### ESG 模块
- Pydantic v2 `regex=` → `pattern=`
- 密码 URL 解析 `Almd@2026` → URL-encode `Almd%402026`
- `/scenarios/{id}` 422 → 加 `scenario_code VARCHAR(32) UNIQUE`
- tar 打包 Windows 路径失败 → POSIX 路径 `/c/...` + `tar.exe`
- EsgCurve 2024-06-03 未找到 → useEffect 不再覆盖默认 source
- `scheme_run_all` KeyError → `scenario_id` → `scenario_code`
- Python 3.12 `sys.stdout.reconfigure` 不存在 → 删除
- urllib POST form → 修正 `urlopen(req, data, timeout)`
- dist 删除失败 → `rm -f dist/assets/*.js *.css`

### 指标计量系数
- URL-encode 中文节点名
- 正则识别方案编码下划线 `COA_V6` → `.+`
- DatePicker `picker='month'` → 默认 day
- 默认查询条件补齐
- `from fastapi import ... Query` 漏 import
- `%%Y-%%m-%%d` 转义错误 → 单 `%`

### 反算驾驶舱
- `prcp_reverse_scheme.base_data_date` → `data_date`
- `prcp_reverse_run.row_count` / `created_at` → `start_at` / `end_at` / `duration_sec`
- dict 索引错位
- uvicorn .pyc 缓存导致代码不生效 → 必须 rm `__pycache__/reverse_dashboard.cpython-312.pyc`
- pkill 转义失败 → `kill -9 PID`

### 部署踩坑
- 服务器 `/var/www/prcp/assets/` 是 root:root 拥有 → `sudo -S bash -c` + almd 密码
- scp 上传 dist 必须分两步（先 index，再 assets/*.js）
- 旧 dist 累积 → `rm -f /tmp/prcp_dist/assets/*.js *.css` 再上传

---

## 文档同步更新

| 文档 | 更新 |
|------|------|
| `docs/README.md` | v3.0 → v4.0：加入 9 大模块表 + 5 项 v2.9+ 版本演进 |
| `docs/superpowers/specs/2026-09-23-metric-coefficient-design.md` | 新建（指标计量系数维护） |
| `docs/superpowers/specs/2026-09-23-reverse-metric-table-design.md` | 新建（反算指标结果表） |
| `docs/superpowers/specs/2026-09-23-reverse-dashboard-design.md` | 新建（组合反算驾驶舱） |
| `docs/superpowers/specs/2026-09-23-seed-2026-design.md` | 新建（演示数据生成脚本） |
| `CHANGELOG.md` | 本文档 |

## 部署状态

| 项 | 状态 |
|----|------|
| GitHub 仓库 | `github.com:ZhangHanghang123/PRCP.git` main 分支 |
| 服务器 | https://wxfzhh.online/prcp/（PRCP 后端 8006 + nginx /prcp/） |
| 演示方案 | `2026`（rev_id=5, ZXCOA_V1, 40 节点 × 24 月） |
| 演示 Run | `run_id=7`（SUCCESS） |
| 演示数据 | 960 行反算结果 + 4800 行指标系数 |