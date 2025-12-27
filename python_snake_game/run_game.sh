#!/bin/bash

echo "========================================"
echo "   Python贪吃蛇游戏启动器"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python3！"
    echo "请先安装Python 3.6或更高版本。"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "macOS: brew install python"
    echo "其他系统请参考：https://www.python.org/downloads/"
    exit 1
fi

# 检查Pygame是否安装
if ! python3 -c "import pygame" &> /dev/null; then
    echo "检测到未安装Pygame，正在安装..."
    echo ""
    pip3 install pygame
    if [ $? -ne 0 ]; then
        echo "安装Pygame失败！"
        echo "请手动运行：pip3 install pygame"
        exit 1
    fi
    echo "Pygame安装成功！"
    echo ""
fi

# 运行游戏
echo "正在启动贪吃蛇游戏..."
echo ""
python3 snake_game.py

if [ $? -ne 0 ]; then
    echo ""
    echo "游戏运行失败！"
    echo "请检查错误信息。"
    exit 1
fi

echo ""
echo "游戏已退出。"