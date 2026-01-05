#!/bin/bash
# OCR识别服务停止脚本 (Linux/Mac)

echo "============================================"
echo "OCR识别服务停止脚本"
echo "============================================"
echo ""

# 进入脚本所在目录
cd "$(dirname "$0")"

PID_FILE="ocr_server.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "[提示] 正在停止 PID 为 $PID 的 OCR 服务..."
    
    # 尝试优雅停止
    kill $PID > /dev/null 2>&1
    
    # 等待几秒检查是否还在运行
    sleep 2
    if ps -p $PID > /dev/null; then
        echo "[提示] 服务未响应，强制停止..."
        kill -9 $PID > /dev/null 2>&1
    fi
    
    rm "$PID_FILE"
    echo "[成功] OCR 服务已停止"
else
    # 如果 PID 文件不存在，尝试通过端口查找
    PORT=4999
    PID=$(lsof -t -i:$PORT)
    if [ ! -z "$PID" ]; then
        echo "[提示] 未找到 PID 文件，但发现端口 $PORT 正在被 PID $PID 占用，正在停止..."
        kill -9 $PID
        echo "[成功] 端口 $PORT 已释放"
    else
        echo "[警告] 未发现运行中的 OCR 服务"
    fi
fi
