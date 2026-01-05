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

echo "[3] 启动OCR服务..."
echo ""
python3 api/server.py

