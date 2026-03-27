#!/bin/bash

# AgentForge - Linux/macOS Installation Script
# Usage: curl -sSL https://path.to/install.sh | bash

set -e

# 颜色定义
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} AgentForge - Installation Script   ${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 1. 确定安装目录
# 优先检查当前目录是否为项目根目录 (包含 run.py 和 core 文件夹)
if [ -f "run.py" ] && [ -d "core" ]; then
    ROOT_DIR="$(pwd)"
else
    # 尝试从脚本位置推断
    SCRIPT_PATH="${BASH_SOURCE[0]}"
    if [ -n "$SCRIPT_PATH" ]; then
        SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd )"
        ROOT_DIR="$(dirname "$SCRIPT_DIR")"
    else
        # 如果是通过管道运行且当前不在根目录，打印错误并退出
        echo -e "${RED}[ERROR] 无法确定安装目录。${NC}"
        echo -e "请进入项目根目录（包含 run.py 的目录）后运行此脚本。"
        echo -e "例如: cd /path/to/AgentForge && curl -sSL ... | bash"
        exit 1
    fi
fi

# 使用 readlink 获取绝对路径（兼容性处理）
get_abs_path() {
    if command -v realpath >/dev/null 2>&1; then
        realpath "$1"
    else
        readlink -f "$1"
    fi
}

AGENT_EXEC=$(get_abs_path "$ROOT_DIR/run.py")

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
echo -e "${YELLOW}[2/4] 正在检查/安装依赖...${NC}"
REQ_FILE="$ROOT_DIR/requirements.txt"
if [ -f "$REQ_FILE" ]; then
    $PYTHON_CMD -m pip install -q -r "$REQ_FILE"
fi

# 4. 配置别名 (agent)
echo -e "${YELLOW}[3/4] 配置全局命令 'agent'...${NC}"

# 使用 Python 脚本进行强力清理，防止 shell 语法错误
FIX_SCRIPT="$ROOT_DIR/scripts/fix_bashrc.py"
if [ -f "$FIX_SCRIPT" ]; then
    echo -e "${YELLOW}运行 .bashrc 修复工具...${NC}"
    $PYTHON_CMD "$FIX_SCRIPT"
fi

# 检测使用的 Shell
if [[ "$SHELL" == *"zsh"* ]]; then
    CONF_FILE="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    CONF_FILE="$HOME/.bashrc"
else
    CONF_FILE="$HOME/.profile"
fi

# 确保配置文件存在
touch "$CONF_FILE"

# 定义标记位
START_MARK="# >>> AGENTFORGE START >>>"
END_MARK="# <<< AGENTFORGE END <<<"
ALIAS_LINE="alias agent='$PYTHON_CMD $AGENT_EXEC'"

# 添加新配置
echo -e "\n$START_MARK" >> "$CONF_FILE"
echo "$ALIAS_LINE" >> "$CONF_FILE"
echo "$END_MARK" >> "$CONF_FILE"

echo -e "${GREEN}[SUCCESS] ★★★ 智匠 AgentForge 配置已就绪 ($CONF_FILE) ★★★${NC}"

# 检查语法错误
if command -v bash >/dev/null 2>&1; then
    if ! bash -n "$CONF_FILE" 2>/dev/null; then
        echo -e "${YELLOW}[WARNING] 检测到 $CONF_FILE 存在语法错误，正在尝试深度修复...${NC}"
        $PYTHON_CMD "$FIX_SCRIPT"
    fi
fi

# 5. 初始化全局配置目录
echo -e "${YELLOW}[4/4] 初始化全局配置目录...${NC}"
DATA_DIR="$HOME/.agentforge"
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
