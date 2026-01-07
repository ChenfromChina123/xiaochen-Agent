#!/bin/bash
# 小晨终端助手 Linux 构建脚本 (重构版)
# 使用自定义 spec 文件确保所有模块正确打包

set -e  # 遇到错误立即退出

# 设置路径
PACKAGING_DIR=$(cd "$(dirname "$0")"; pwd)
PROJECT_ROOT=$(cd "$PACKAGING_DIR/../.."; pwd)

echo "========================================"
echo "  Xiaochen Terminal Agent Linux Builder"
echo "========================================"
echo "Project Root: $PROJECT_ROOT"
echo "Packaging Dir: $PACKAGING_DIR"

cd "$PROJECT_ROOT"

# 检测 Python
if command -v python3.13 &> /dev/null; then
    PY_CMD=python3.13
elif command -v python3 &> /dev/null; then
    PY_CMD=python3
elif command -v python &> /dev/null; then
    PY_CMD=python
else
    echo "[ERROR] Python not found."
    exit 1
fi

echo "Using Python: $PY_CMD"

# [1/4] 创建虚拟环境
echo ""
echo "[1/4] Creating venv..."
if [ ! -d "venv" ]; then
    "$PY_CMD" -m venv venv
else
    echo "venv already exists, skipping creation..."
fi
source venv/bin/activate

# [2/4] 安装依赖
echo ""
echo "[2/4] Installing requirements..."
pip install --upgrade pip -q
pip install -r xiaochen_agent_v2/requirements.txt
pip install pyinstaller

# [3/4] 清理旧文件
echo ""
echo "[3/4] Cleaning old build files..."
rm -rf build dist *.spec

# [4/4] 构建二进制文件
echo ""
echo "[4/4] Building Binary..."
echo "Using spec file: $PACKAGING_DIR/xiaochen_linux.spec"

# 使用自定义 spec 文件构建
pyinstaller --clean --distpath "$PROJECT_ROOT/dist" --workpath "$PROJECT_ROOT/build" "$PACKAGING_DIR/xiaochen_linux.spec"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  Build Success!"
    echo "========================================"
    echo "Binary location: $PROJECT_ROOT/dist/xiaochen-agent"
    echo ""
    echo "To run the binary:"
    echo "  cd $PROJECT_ROOT/dist"
    echo "  ./xiaochen-agent"
else
    echo ""
    echo "[ERROR] Build failed."
    exit 1
fi
