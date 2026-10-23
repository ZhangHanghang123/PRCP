# PRCP 部署指南

## 标准流程

```
本地改代码 → bash deploy/release.sh -m "feat(x): 说明"
                          ↓
              git commit + push origin main
                          ↓
        服务器 git pull → 语法自检 → 重启后端 → 构建前端 → 健康检查
```

一条命令完成发布。

## 脚本说明

| 脚本 | 位置 | 用途 |
|---|---|---|
| `release.sh` | 本地 | 一键发布：提交 → 推送 → 触发服务器部署 |
| `deploy.sh` | 服务器 | 实际部署：拉代码 → 重启后端 → 构建前端 |

## 用法

### 本地发布（最常用）

```bash
# 正常发布
bash deploy/release.sh -m "feat(sim): 新增分期限占比配置"

# 只部署不提交（工作区须干净，或明确知道服务器会拉旧代码）
bash deploy/release.sh --no-commit

# 修上次提交（漏了文件 / 说明写错）
bash deploy/release.sh --amend -m "feat(sim): 新增分期限占比配置"
```

### 服务器单独操作

```bash
ssh almd@43.143.253.186
cd /home/almd/prcp

bash deploy/deploy.sh                # 完整部署
bash deploy/deploy.sh --pull         # 只拉代码
bash deploy/deploy.sh --backend      # 只重启后端
bash deploy/deploy.sh --frontend     # 只构建前端
```

### 排查

```bash
# 后端状态
systemctl status prcp-backend

# 后端日志（实时）
journalctl -u prcp-backend -f

# 后端日志（最近 5 分钟的报错）
journalctl -u prcp-backend --since '5 min ago' --no-pager | grep -A 30 'Exception'

# 当前代码版本
git log --oneline -3

# 是否有未提交改动（部署脚本会拒绝执行）
git status --short
```

## 环境信息

| 项 | 值 |
|---|---|
| 服务器 | `43.143.253.186`（Ubuntu 24.04） |
| 应用目录 | `/home/almd/prcp` |
| 后端服务 | `prcp-backend`（systemd），端口 8006 |
| 前端目录 | `/var/www/prcp` |
| 访问地址 | `https://wxfzhh.online/prcp/` |
| 数据库 | `prcp_db`，用户 `prcp` |
| SSH | `almd` / `almd`（sudo 密码同） |

## 安全设计

部署脚本内置四道保护：

1. **拒绝脏工作区** —— 服务器有未提交改动时直接中止，避免 `git pull` 覆盖线上代码
2. **语法自检** —— 后端 `compileall`、前端 `vite build` 失败即中止，不发布坏代码
3. **安全删除** —— `rm -rf "${FRONT_DIR:?}"/*`，变量为空时不会误删根目录
4. **强制快进** —— 只允许 `--ff-only` 合并，杜绝服务器产生分叉提交

## 数据库变更

DDL 脚本统一放 `backend/scripts/`，命名规范：

- `add_xxx.sql` —— 新增字段/表
- `upgrade_xxx.sql` —— 修改已有结构
- `backfill_xxx.sql` —— 历史数据回填
- `seed_xxx.sql` —— 业务数据初始化

执行方式（部署脚本不会自动跑 DDL，避免误操作）：

```bash
ssh almd@43.143.253.186
mysql -u prcp -p prcp_db < /home/almd/prcp/backend/scripts/add_xxx.sql
```

## 常见问题

### 部署脚本报「服务器存在未提交改动」

说明服务器上有手工改动（可能是临时调试）。处理方式：

```bash
ssh almd@43.143.253.186 "cd /home/almd/prcp && git status --short"

# 如果是误改，直接丢弃
ssh almd@43.143.253.186 "cd /home/almd/prcp && git checkout -- <文件>"

# 如果要保留，先 stash
ssh almd@43.143.253.186 "cd /home/almd/prcp && git stash"
```

### 合并冲突

```bash
ssh almd@43.143.253.186 "cd /home/almd/prcp && git fetch origin && git merge origin/main"
# 手动解决后
ssh almd@43.143.253.186 "cd /home/almd/prcp && git commit && git push origin main"
```

### 前端构建失败但代码没问题

服务器首次构建需装依赖，脚本会自动执行 `npm ci`。若仍失败：

```bash
ssh almd@43.143.253.186 "cd /home/almd/prcp/frontend && rm -rf node_modules && npm install"
```