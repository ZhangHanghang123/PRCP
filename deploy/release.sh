#!/bin/bash
# =============================================================================
# PRCP 本地发布脚本（一键提交 + 推送 + 服务器部署）
#
# 用法（在项目根目录执行）：
#   bash deploy/release.sh              # 提交全部改动 → 推送 → 服务器部署
#   bash deploy/release.sh -m "feat(x): xxx"   # 指定提交信息
#   bash deploy/release.sh --no-commit  # 只部署，不提交（工作区须干净）
#   bash deploy/release.sh --amend      # 追加到上次提交后推送
#
# 流程：
#   本地 git add/commit → git push → ssh 服务器执行 deploy/deploy.sh
#
# 约定：
#   · 服务器地址 /home/almd/prcp，SSH 用户 almd
#   · 后端由 systemd 管理（prcp-backend），前端构建产物直接覆盖 /var/www/prcp
# =============================================================================
set -euo pipefail

SERVER="almd@43.143.253.186"
APP_DIR="/home/almd/prcp"
BRANCH="main"

log()  { echo -e "\n\033[1;36m=== $* ===\033[0m"; }
warn() { echo -e "\033[1;33m[WARN] $*\033[0m"; }
die()  { echo -e "\033[1;31m[FAIL] $*\033[0m"; exit 1; }

MSG=""
DO_COMMIT=1
AMEND=0
while [ $# -gt 0 ]; do
  case "$1" in
    -m) MSG="$2"; shift 2 ;;
    --no-commit) DO_COMMIT=0; shift ;;
    --amend) AMEND=1; shift ;;
    *) die "未知参数：$1" ;;
  esac
done

cd "$(git rev-parse --show-toplevel)" || die "不在 git 仓库中"

# ---------- 1. 提交 ----------
if [ "$DO_COMMIT" = "1" ]; then
  log "1/3 本地提交"

  if [ -z "$(git status --porcelain)" ]; then
    echo "工作区干净，无需提交"
  elif [ "$AMEND" = "1" ]; then
    git add -A
    [ -n "$MSG" ] && git commit --amend -m "$MSG" || git commit --amend --no-edit
    echo "已追加到上次提交"
  else
    [ -z "$MSG" ] && die "请用 -m \"提交信息\" 指定提交说明（或用 --no-commit 跳过提交）"
    git add -A
    git commit -m "$MSG" || die "提交失败"
    echo "已提交："
    git log --oneline -1
  fi
else
  log "1/3 跳过提交（--no-commit）"
  [ -n "$(git status --porcelain)" ] && warn "工作区有未提交改动，服务器将拉取上次提交的内容"
fi

# ---------- 2. 推送 ----------
log "2/3 推送到 origin/$BRANCH"
git push origin "$BRANCH" || die "推送失败"
echo "本地 HEAD：$(git rev-parse --short HEAD)"

# ---------- 3. 服务器部署 ----------
log "3/3 触发服务器部署"
echo "→ $SERVER:$APP_DIR/deploy/deploy.sh"
ssh "$SERVER" "cd $APP_DIR && bash deploy/deploy.sh" || die "服务器部署失败"

log "发布完成"
cat <<EOF
  版本：$(git rev-parse --short HEAD)
  后端：systemctl status prcp-backend
  前端：https://wxfzhh.online/prcp/
  日志：ssh $SERVER "journalctl -u prcp-backend -f"
EOF