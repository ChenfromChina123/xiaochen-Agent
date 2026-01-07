#!/bin/bash
# 设置路径
PACKAGING_DIR=$(cd "$(dirname "$0")"; pwd)
# 尝试定位根目录（寻找 launcher.py）
if [ -f "$PACKAGING_DIR/launcher.py" ]; then
    # launcher.py 在 packaging 目录中
    # packaging 的父目录是 xiaochen_agent_v2，再往上一级才是项目根目录
    PROJECT_ROOT=$(cd "$PACKAGING_DIR/../.."; pwd)
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
if [ -f "xiaochen_agent_v2/requirements.txt" ]; then
    pip install -r xiaochen_agent_v2/requirements.txt
else
    echo "ERROR: requirements.txt not found in $PROJECT_ROOT/xiaochen_agent_v2"
    exit 1
fi
pip install pyinstaller

# 将 xiaochen_agent_v2 包以可编辑模式安装到虚拟环境，这样 PyInstaller 可以正确识别它
echo "Installing xiaochen_agent_v2 package in editable mode..."
pip install -e xiaochen_agent_v2

# [3/4] 构建二进制文件
echo "[3/4] Building Binary..."
# 清理旧的构建文件和 spec 文件
echo "Cleaning old build files..."
rm -rf build dist *.spec

# 确保在项目根目录运行 pyinstaller，以便正确处理导入
# 计算 launcher.py 相对于项目根目录的路径
if [ "$LAUNCHER_PATH" = "$PACKAGING_DIR/launcher.py" ]; then
    # launcher.py 在 packaging 目录中
    # 相对于项目根目录是 xiaochen_agent_v2/packaging/launcher.py
    LAUNCHER_RELATIVE="xiaochen_agent_v2/packaging/launcher.py"
else
    # launcher.py 在项目根目录中
    LAUNCHER_RELATIVE="launcher.py"
fi

# 构建 PyInstaller 命令
# 使用 --paths "." 添加当前目录到 Python 路径
# 使用 --clean 强制清理缓存
# 由于已经将包安装到虚拟环境，PyInstaller 可以自动识别和包含它
PYINSTALLER_CMD="pyinstaller --clean --noconfirm --onefile --console --name xiaochen-agent --paths ."

# 添加静态文件（如果存在）
if [ -d "xiaochen_agent_v2/static" ]; then
    PYINSTALLER_CMD="$PYINSTALLER_CMD --add-data xiaochen_agent_v2/static:xiaochen_agent_v2/static"
fi

# 添加配置文件（如果存在）
if [ -f "xiaochen_agent_v2/config.json" ]; then
    PYINSTALLER_CMD="$PYINSTALLER_CMD --add-data xiaochen_agent_v2/config.json:xiaochen_agent_v2"
fi
if [ -f "xiaochen_agent_v2/ocr_config.json" ]; then
    PYINSTALLER_CMD="$PYINSTALLER_CMD --add-data xiaochen_agent_v2/ocr_config.json:xiaochen_agent_v2"
fi

# 执行构建
$PYINSTALLER_CMD "$LAUNCHER_RELATIVE"

if [ $? -eq 0 ]; then
    echo "[4/4] Done! Binary is in dist/ folder."
else
    echo "[ERROR] Build failed."
    exit 1
fi
