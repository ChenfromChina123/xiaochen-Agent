#!/bin/bash
# OCR识别服务启动脚本 (Linux/Mac)

echo "============================================"
echo "OCR识别服务启动脚本"
echo "============================================"
echo ""

# 进入项目根目录
cd "$(dirname "$0")/.."

echo "[1] 检查Python环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "[错误] 未找到Python，请先安装Python 3.7+"
    exit 1
fi
echo ""

echo "[2] 检查依赖包..."
pip3 show Flask > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[警告] 未找到Flask，正在安装依赖..."
    pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
else
    echo "[提示] 依赖包已安装"
fi
echo ""

echo "[3] 启动OCR服务 (持久化)..."
echo ""

# 创建日志目录
mkdir -p logs

# 检查端口 4999 是否被占用
PORT=4999
PID=$(lsof -t -i:$PORT)
if [ ! -z "$PID" ]; then
    echo "[提示] 端口 $PORT 已被占用 (PID: $PID)，服务正在运行中。"
    echo "[提示] 如果需要重启，请先运行 ./stop_server.sh"
    exit 0
fi

# 使用 nohup 后台启动
nohup python3 api/server.py > logs/ocr_server.log 2>&1 &
NEW_PID=$!

echo $NEW_PID > ocr_server.pid
echo "[成功] OCR服务已在后台启动，PID: $NEW_PID"
echo "[提示] 日志文件: backend_service/logs/ocr_server.log"
echo "[提示] 使用 ./scripts/stop_server.sh 停止服务"

