#!/bin/bash
# 前端 + 后端 + nginx 保活脚本

FRONTEND_DIR="/root/.openclaw/workspace-zhanbu/web/frontend"
BACKEND_DIR="/root/.openclaw/workspace-zhanbu/web/backend"
LOG="/tmp/frontend.log"

# 检查 nginx，没有则启动
if ! pgrep -x nginx > /dev/null; then
    echo "[$(date)] nginx 未运行，正在启动..." >> $LOG
    /usr/sbin/nginx
fi

# 检查后端 8000 端口，不通则重启
if ! curl -sf --max-time 3 http://localhost:8000/health > /dev/null 2>&1; then
    echo "[$(date)] 8000端口无响应，正在重启后端..." >> $LOG
    pkill -f "uvicorn" 2>/dev/null
    sleep 1
    cd $BACKEND_DIR
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> /tmp/backend.log 2>&1 &
    echo "[$(date)] 后端已重启" >> $LOG
fi

# 检查前端 10008 端口，不通则重启
if ! curl -sf --max-time 3 http://localhost:10008 > /dev/null 2>&1; then
    echo "[$(date)] 10008端口无响应，正在重启前端..." >> $LOG
    pkill -f "next dev" 2>/dev/null
    sleep 2
    cd $FRONTEND_DIR
    PORT=10008 nohup npm run dev >> $LOG 2>&1 &
    echo "[$(date)] 前端已重启" >> $LOG
fi
