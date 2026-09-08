#!/bin/bash
# PRCP 后端启动脚本
cd "$(dirname "$0")"
exec /home/almd/prcp/backend/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 --port 8006 --workers 1 --log-level info