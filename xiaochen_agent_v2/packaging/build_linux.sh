#!/bin/bash
# 设置路径
PACKAGING_DIR=$(cd "$(dirname "$0")"; pwd)
# 尝试定位根目录（寻找 launcher.py）
if [ -f "$PACKAGING_DIR/launcher.py" ]; then
    # launcher.py 在 packaging 目录中，项目根目录是 packaging 的父目录
    PROJECT_ROOT=$(cd "$PACKAGING_DIR/.."; pwd)
    LAUNCHER_PATH="$PACKAGING_DIR/launcher.py"
elif [ -f "$PACKAGING_DIR/../launcher.py" ]; then
    PROJECT_ROOT=$(cd "$PACKAGING_DIR/.."; pwd)
    LAUNCHER_PATH="$PROJECT_ROOT/launcher.py"
elif [ -f "$PACKAGING_DIR/../../launcher.py" ]; then
    PROJECT_ROOT=$(cd "$PACKAGING_DIR/../.."; pwd)
    LAUNCHER_PATH="$PROJECT_ROOT/launcher.py"
else
    echo "ERROR: Could not find launcher.py in parent directories."
    exit 1
fi

cd "$PROJECT_ROOT"

echo "========================================"
echo "  Xiaochen Terminal Agent Linux Builder"
echo "========================================"
echo "Project Root: $PROJECT_ROOT"

# Detect Python
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
echo "[1/4] Creating venv..."
"$PY_CMD" -m venv venv
source venv/bin/activate

# [2/4] 安装依赖
echo "[2/4] Installing requirements..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found in $PROJECT_ROOT"
    exit 1
fi
pip install pyinstaller

# [3/4] 构建二进制文件
echo "[3/4] Building Binary..."
# 确保在项目根目录运行 pyinstaller，以便正确处理导入
# 计算 launcher.py 相对于项目根目录的路径
if [ "$LAUNCHER_PATH" = "$PACKAGING_DIR/launcher.py" ]; then
    # launcher.py 在 packaging 目录中
    LAUNCHER_RELATIVE="packaging/launcher.py"
else
    # launcher.py 在项目根目录中
    LAUNCHER_RELATIVE="launcher.py"
fi
pyinstaller --noconfirm --onefile --console \
    --name "xiaochen-agent" \
    --add-data "xiaochen_agent_v2:xiaochen_agent_v2" \
    "$LAUNCHER_RELATIVE"

if [ $? -eq 0 ]; then
    echo "[4/4] Done! Binary is in dist/ folder."
else
    echo "[ERROR] Build failed."
    exit 1
fi
