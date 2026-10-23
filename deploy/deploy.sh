#!/bin/bash
# =============================================================================
# PRCP 统一部署脚本（服务器侧）
#
# 用法：
#   bash deploy.sh              # 拉取代码 + 重启后端 + 构建部署前端
#   bash deploy.sh --backend    # 仅重启后端
#   bash deploy.sh --frontend   # 仅构建部署前端
#   bash deploy.sh --pull       # 仅拉取代码
#
# 前提：服务器已配置 GitHub SSH 认证（本机已配置 ZhangHanghang123）
#
# 部署流程（标准）：
#   本地 git push  →  服务器 git pull  →  构建 + 重启
# =============================================================================
set -euo pipefail

APP_DIR=/home/almd/prcp
FRONT_DIR=/var/www/prcp
SERVICE=prcp-backend
SSH_PASS=almd
BRANCH=main

log()  { echo -e "\n\033[1;36m=== $* ===\033[0m"; }
warn() { echo -e "\033[1;33m[WARN] $*\033[0m"; }
die()  { echo -e "\033[1;31m[FAIL] $*\033[0m"; exit 1; }

# ---------- 1. 拉取代码 ----------
do_pull() {
  log "1/4 拉取代码（$BRANCH）"
  cd "$APP_DIR" || die "目录不存在：$APP_DIR"

  # 有本地改动则拒绝覆盖，避免丢失
  if [ -n "$(git status --porcelain)" ]; then
    warn "服务器存在未提交改动："
    git status --short | head -10
    die "请先在服务器处理掉这些改动（或 git stash），再执行部署"
  fi

  git fetch origin "$BRANCH" || die "git fetch 失败"
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse "origin/$BRANCH")

  if [ "$LOCAL" = "$REMOTE" ]; then
    echo "代码已是最新：$(git log --oneline -1)"
  else
    git merge --ff-only "origin/$BRANCH" || die "非快进合并失败，请人工处理"
    echo "已更新："
    git log --oneline "${LOCAL}..${REMOTE}" | head -20
  fi
}

# ---------- 2. 数据库迁移（若有） ----------
do_migrate() {
  log "2/4 检查数据库迁移脚本"
  # 约定：backend/scripts/migrations/*.sql 按序号执行，已执行的记录在 schema_migrations 表
  MIG_DIR="$APP_DIR/backend/scripts/migrations"
  [ -d "$MIG_DIR" ] || { echo "无 migrations 目录，跳过"; return 0; }

  echo "发现迁移脚本："
  ls -1 "$MIG_DIR"/*.sql 2>/dev/null | head -10
  echo "（当前无强制迁移，如需执行请手动：mysql -u prcp -p prcp_db < $MIG_DIR/<file>.sql）"
}

# ---------- 3. 后端 ----------
do_backend() {
  log "3/4 重启后端（$SERVICE）"
  cd "$APP_DIR/backend"

  # 语法自检，避免把坏代码发上线
  ./venv/bin/python -m compileall -q app > /dev/null || die "Python 语法检查失败"
  echo "语法检查通过"

  echo "$SSH_PASS" | sudo -S systemctl restart "$SERVICE" 2>/dev/null || die "服务重启失败"
  sleep 6

  if systemctl is-active --quiet "$SERVICE"; then
    echo "后端已启动"
    systemctl is-active "$SERVICE"
  else
    echo "服务状态：$(systemctl status $SERVICE --no-pager | head -8)"
    die "后端启动失败"
  fi

  # 健康检查：GET /openapi.json 返回 200 说明服务正常
  sleep 2
  CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8006/openapi.json || echo 000)
  if [ "$CODE" = "200" ]; then
    echo "健康检查通过（/openapi.json HTTP 200）"
  else
    echo "后端状态：$(systemctl status $SERVICE --no-pager | head -8)"
    die "健康检查失败（HTTP $CODE），部署已中止，请排查 journalctl -u $SERVICE"
  fi
}

# ---------- 4. 前端 ----------
do_frontend() {
  log "4/4 构建并部署前端"
  cd "$APP_DIR/frontend"

  if [ ! -d node_modules ]; then
    echo "安装依赖..."
    npm ci || npm install || die "依赖安装失败"
  fi

  rm -rf dist
  npm run build || die "前端构建失败"

  [ -d dist ] || die "dist 目录未生成"

  echo "部署到 $FRONT_DIR ..."
  echo "$SSH_PASS" | sudo -S mkdir -p "$FRONT_DIR"
  echo "$SSH_PASS" | sudo -S rm -rf "${FRONT_DIR:?}"/*    # :? 防止变量为空导致 rm -rf /
  echo "$SSH_PASS" | sudo -S cp -r dist/. "$FRONT_DIR/"
  echo "$SSH_PASS" | sudo -S chown -R almd:almd "$FRONT_DIR"

  echo "前端已部署："
  ls -la "$FRONT_DIR" | head -6
}

# ---------- 参数解析 ----------
MODE="${1:-all}"
case "$MODE" in
  --pull)     do_pull ;;
  --backend)  do_backend ;;
  --frontend) do_frontend ;;
  all)
    do_pull
    do_migrate
    do_backend
    do_frontend
    log "部署完成"
    echo "  后端： systemctl status $SERVICE"
    echo "  前端： $FRONT_DIR"
    echo "  日志： journalctl -u $SERVICE -f"
    ;;
  *) echo "用法: bash deploy.sh [--pull|--backend|--frontend]"; exit 1 ;;
esac