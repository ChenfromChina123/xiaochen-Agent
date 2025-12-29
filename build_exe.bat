@echo off
setlocal enabledelayedexpansion

:: 强制设置控制台编码为 UTF-8
chcp 65001 >nul

echo ========================================
echo   小晨终端助手 (XIAOCHEN_TERMINAL)
echo        EXE 打包工具 (Windows)
echo ========================================
echo.

:: 1. 检查 Python 环境
set "PY_CMD=python"
%PY_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PY_CMD=py"
    !PY_CMD! --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未检测到 Python，打包需要 Python 环境。
        pause
        exit /b 1
    )
)

:: 2. 创建/激活虚拟环境以保持打包环境纯净
if not exist ".venv" (
    echo [1/4] 正在创建打包专用虚拟环境...
    %PY_CMD% -m venv .venv
)

echo [2/4] 正在安装打包依赖 (pyinstaller)...
call .venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

:: 3. 开始打包
echo [3/4] 正在开始打包为单文件 EXE (这可能需要几分钟)...
echo.

:: 使用 pyinstaller 打包
:: 续行符 ^ 后面不能有任何空格，否则会导致命令断开
pyinstaller --onefile ^
--name "xiaochen_agent" ^
--console ^
--clean ^
--add-data "xiaochen_agent_v2;xiaochen_agent_v2" ^
launcher.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包过程中出现问题。
    pause
    exit /b 1
)

:: 4. 完成
echo.
echo [4/4] 打包成功！
echo.
echo 可执行文件位于: %CD%\dist\xiaochen_agent.exe
echo.
echo 注意: 
echo 1. 第一次运行 exe 时会自动在同级目录创建 config.json
echo 2. exe 是独立运行的，不再需要安装 Python 环境
echo.

deactivate
pause
