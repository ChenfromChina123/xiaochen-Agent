@echo off
chcp 65001 > nul
echo ========================================
echo    Python贪吃蛇游戏启动器
echo ========================================
echo.

REM 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python！
    echo 请先安装Python 3.6或更高版本。
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查Pygame是否安装
python -c "import pygame" > nul 2>&1
if errorlevel 1 (
    echo 检测到未安装Pygame，正在安装...
    echo.
    pip install pygame
    if errorlevel 1 (
        echo 安装Pygame失败！
        echo 请手动运行：pip install pygame
        pause
        exit /b 1
    )
    echo Pygame安装成功！
    echo.
)

REM 运行游戏
echo 正在启动贪吃蛇游戏...
echo.
python snake_game.py

if errorlevel 1 (
    echo.
    echo 游戏运行失败！
    echo 请检查错误信息。
    pause
    exit /b 1
)

echo.
echo 游戏已退出。
pause