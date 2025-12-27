#!/bin/bash
# 小晨终端助手安装脚本 (Linux/Mac)

set -e

echo "========================================"
echo "小晨终端助手 - 安装脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( dirname "$SCRIPT_DIR" )"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python 3，请先安装 Python 3.7+"
    exit 1
fi

echo "[1/4] 检测到 Python 环境"
python3 --version

# 安装依赖
echo ""
echo "[2/4] 安装依赖包..."
pip3 install -r "$ROOT_DIR/requirements.txt"

# 创建配置文件（如果不存在）
echo ""
echo "[3/4] 检查配置文件..."
if [ ! -f "$ROOT_DIR/config.json" ]; then
    echo "配置文件不存在，将在首次运行时创建"
else
    echo "配置文件已存在"
fi

# 添加到环境变量
echo ""
echo "[4/4] 配置环境变量..."
echo ""

# 给脚本添加执行权限
chmod +x "$SCRIPT_DIR/agent.sh"

# 检测 shell 类型
SHELL_RC=""
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
else
    SHELL_RC="$HOME/.profile"
fi

echo "检测到 shell 配置文件: $SHELL_RC"
echo ""
echo "请选择安装方式:"
echo "  1. 添加到 PATH (推荐)"
echo "  2. 创建软链接到 /usr/local/bin"
echo "  3. 跳过环境变量配置"
echo ""
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        # 添加到 PATH
        if ! grep -q "# xiaochen_agent_v2" "$SHELL_RC"; then
            echo "" >> "$SHELL_RC"
            echo "# xiaochen_agent_v2" >> "$SHELL_RC"
            echo "export PATH=\"\$PATH:$SCRIPT_DIR\"" >> "$SHELL_RC"
            echo "[成功] 已添加到 $SHELL_RC"
            echo "请运行以下命令使配置生效:"
            echo "  source $SHELL_RC"
            echo "然后输入 'agent.sh' 即可启动"
        else
            echo "[提示] PATH 已经配置过了"
        fi
        ;;
    2)
        # 创建软链接
        if [ -w "/usr/local/bin" ]; then
            ln -sf "$SCRIPT_DIR/agent.sh" "/usr/local/bin/agent"
            echo "[成功] 已创建软链接到 /usr/local/bin/agent"
            echo "输入 'agent' 即可启动"
        else
            echo "[错误] 没有权限写入 /usr/local/bin，请使用 sudo 运行此脚本"
            echo "或选择方式 1"
        fi
        ;;
    3)
        echo "[跳过] 环境变量配置"
        echo "您可以直接运行: $SCRIPT_DIR/agent.sh"
        ;;
    *)
        echo "[错误] 无效的选择"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "使用方法:"
echo "  1. 如果配置了环境变量，输入: agent 或 agent.sh"
echo "  2. 或者直接运行: $SCRIPT_DIR/agent.sh"
echo ""
echo "首次运行时，程序会提示您输入 API Key"
echo "API Key 将自动保存到配置文件中，下次无需再输入"
echo ""

