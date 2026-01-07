#!/bin/bash
# 小晨终端助手启动脚本 (Linux/Mac)

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( dirname "$SCRIPT_DIR" )"

# 设置 PYTHONPATH 以支持模块导入
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

# 如果设置了 XIAOCHEN_START_CWD，则切换到该目录
if [ ! -z "$XIAOCHEN_START_CWD" ]; then
    if [ -d "$XIAOCHEN_START_CWD" ]; then
        cd "$XIAOCHEN_START_CWD"
    else
        echo "警告: 目录 $XIAOCHEN_START_CWD 不存在，将在当前目录启动。"
    fi
fi

# 检测 Python 版本，优先使用 3.13
if command -v python3.13 >/dev/null 2>&1; then
    PYTHON_CMD="python3.13"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    echo "错误: 未找到 python3 或 python3.13，请先安装 Python。"
    exit 1
fi

# 运行程序
echo "正在从 $ROOT_DIR 启动小晨终端助手..."
cd "$ROOT_DIR"
$PYTHON_CMD -m xiaochen_agent_v2 "$@"

