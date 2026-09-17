#!/bin/bash
# PRCP 前端部署脚本
set -e
echo "=== 清理旧文件 ==="
sudo rm -rf /var/www/prcp/assets/*
sudo rm -f /var/www/prcp/index.html
echo "=== 拷贝新文件 ==="
sudo cp /tmp/index-BSeIpmFj.js /var/www/prcp/assets/
sudo cp /tmp/index-CxaUM2Jg.css /var/www/prcp/assets/
sudo cp /tmp/index.html /var/www/prcp/
echo "=== 设置权限 ==="
sudo chown -R almd:almd /var/www/prcp
echo "=== 清理临时 ==="
rm -f /tmp/index-BSeIpmFj.js /tmp/index-CxaUM2Jg.css /tmp/index.html
echo "=== 验证 ==="
ls -la /var/www/prcp/
ls -la /var/www/prcp/assets/
echo "DONE"