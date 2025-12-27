#!/bin/bash
# 小晨终端助手启动脚本 (Linux/Mac)

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( dirname "$SCRIPT_DIR" )"

# 设置 PYTHONPATH 以支持模块导入
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

# 运行程序
python3 -m xiaochen_agent_v2 "$@"

