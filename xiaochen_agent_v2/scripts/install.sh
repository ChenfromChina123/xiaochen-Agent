#!/bin/bash

# Xiaochen Agent - Linux/macOS Installation Script
# Usage: curl -sSL https://path.to/install.sh | bash

set -e

# 颜色定义
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} Xiaochen Agent - Installation Script   ${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 1. 确定安装目录
if [ -f "run.py" ] && [ -d "xiaochen_agent_v2" ]; then
    # 如果当前目录下有 run.py 和包文件夹，说明就在根目录
    ROOT_DIR="$(pwd)"
else
    # 否则尝试从脚本位置推断
    SCRIPT_PATH="${BASH_SOURCE[0]}"
    if [ -z "$SCRIPT_PATH" ]; then
        # 如果是通过 pipe 运行且不在根目录，则无法推断
        echo -e "${RED}[ERROR] 无法确定安装目录。请在项目根目录下运行此脚本。${NC}"
        echo -e "例如: cd xiaochen-Agent && bash scripts/install.sh"
        exit 1
    fi
    SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd )"
    ROOT_DIR="$(dirname "$SCRIPT_DIR")"
fi

AGENT_EXEC="$ROOT_DIR/run.py"

if [ ! -f "$AGENT_EXEC" ]; then
    echo -e "${RED}[ERROR] 找不到 $AGENT_EXEC。请确保在正确的目录下执行安装。${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/4] 检查环境...${NC}"

# 2. 检查 Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] 未检测到 Python，请先安装 Python 3.10+${NC}"
    exit 1
fi
echo -e "${GREEN}[SUCCESS] 检测到 Python: $($PYTHON_CMD --version)${NC}"

# 3. 安装依赖
echo -e "${YELLOW}[2/4] 安装依赖...${NC}"
REQ_FILE="$ROOT_DIR/requirements.txt"
if [ -f "$REQ_FILE" ]; then
    $PYTHON_CMD -m pip install -r "$REQ_FILE"
fi

# 4. 配置别名 (agent)
echo -e "${YELLOW}[3/4] 配置全局命令 'agent'...${NC}"

# 检测使用的 Shell
if [[ "$SHELL" == *"zsh"* ]]; then
    CONF_FILE="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    CONF_FILE="$HOME/.bashrc"
else
    CONF_FILE="$HOME/.profile"
fi

ALIAS_LINE="alias agent='$PYTHON_CMD $AGENT_EXEC'"

if grep -q "alias agent=" "$CONF_FILE"; then
    # 更新已存在的别名
    sed -i "s|alias agent=.*|$ALIAS_LINE|" "$CONF_FILE"
    echo -e "${GREEN}[INFO] 已更新 $CONF_FILE 中的 agent 别名${NC}"
else
    # 添加新别名
    echo "" >> "$CONF_FILE"
    echo "# Xiaochen Agent Alias" >> "$CONF_FILE"
    echo "$ALIAS_LINE" >> "$CONF_FILE"
    echo -e "${GREEN}[SUCCESS] 已在 $CONF_FILE 中添加 agent 别名${NC}"
fi

# 5. 初始化全局配置目录
echo -e "${YELLOW}[4/4] 初始化全局配置目录...${NC}"
DATA_DIR="$HOME/.xiaochen_agent_v2"
if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo -e "${GREEN}[SUCCESS] 已创建配置目录: $DATA_DIR${NC}"
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} 安装完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "请运行 ${YELLOW}source $CONF_FILE${NC} 或者重启终端使配置生效。"
echo -e "现在你可以在任何地方输入 'agent' 来启动程序。"
echo -e "例如: agent ."
echo ""
