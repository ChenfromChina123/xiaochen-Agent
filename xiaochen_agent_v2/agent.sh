#!/bin/bash
# 小晨终端助手启动脚本 (Linux/Mac)

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 运行程序
python3 -m xiaochen_agent_v2

