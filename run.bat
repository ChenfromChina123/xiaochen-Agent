@echo off
setlocal enabledelayedexpansion

:: 设置控制台编码为 UTF-8
chcp 65001 >nul

echo ========================================
echo   小晨终端助手 (XIAOCHEN_TERMINAL)
echo        一键启动器 (Windows)
echo ========================================
echo.

:: 1. 检查 Python 是否安装
set "PYTHON_CMD=python"
!PYTHON_CMD! --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_CMD=py"
    !PYTHON_CMD! --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未检测到 Python，请先安装 Python 3.8+ (https://www.python.org/)
        pause
        exit /b 1
    )
)

:: 2. 检查并创建虚拟环境
if not exist ".venv" (
    echo [1/3] 正在创建虚拟环境 (.venv)...
    !PYTHON_CMD! -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
)

:: 3. 激活虚拟环境并安装/更新依赖
echo [2/3] 正在检查并安装依赖包...
call .venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [错误] 安装依赖失败，请检查网络连接。
    pause
    exit /b 1
)

:: 4. 启动程序
echo [3/3] 正在启动智能体...
echo.
:: 设置 PYTHONPATH 为当前目录，确保包导入正常
set PYTHONPATH=%CD%
python -m xiaochen_agent_v2

if %errorlevel% neq 0 (
    echo.
    echo [提示] 程序已退出 (退出码: %errorlevel%)
    pause
)

deactivate
