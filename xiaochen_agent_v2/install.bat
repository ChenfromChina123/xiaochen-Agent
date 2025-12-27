@echo off
chcp 65001 > nul
setlocal

echo ========================================
echo 小晨终端助手 - 安装脚本
echo ========================================
echo.

:: 获取当前脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

echo [1/4] 检测到 Python 环境
python --version

:: 安装依赖
echo.
echo [2/4] 安装依赖包...
pip install -r "%SCRIPT_DIR%\requirements.txt"
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 创建配置文件（如果不存在）
echo.
echo [3/4] 检查配置文件...
if not exist "%SCRIPT_DIR%\config.json" (
    echo 配置文件不存在，将在首次运行时创建
) else (
    echo 配置文件已存在
)

:: 添加到环境变量
echo.
echo [4/4] 配置环境变量...
echo.
echo 请选择安装方式:
echo   1. 仅当前用户 (推荐)
echo   2. 所有用户 (需要管理员权限)
echo   3. 跳过环境变量配置
echo.
set /p choice="请输入选择 (1-3): "

if "%choice%"=="1" (
    :: 添加到用户环境变量
    setx PATH "%PATH%;%SCRIPT_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo [警告] 环境变量设置失败，请手动添加以下路径到 PATH:
        echo %SCRIPT_DIR%
    ) else (
        echo [成功] 已添加到用户环境变量
        echo 请重新打开命令行窗口后，输入 'agent' 即可启动
    )
) else if "%choice%"=="2" (
    :: 检查管理员权限
    net session >nul 2>&1
    if errorlevel 1 (
        echo [错误] 需要管理员权限，请以管理员身份运行此脚本
        pause
        exit /b 1
    )
    :: 添加到系统环境变量
    for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "SYSTEM_PATH=%%b"
    setx PATH "%SYSTEM_PATH%;%SCRIPT_DIR%" /M >nul 2>&1
    if errorlevel 1 (
        echo [警告] 环境变量设置失败，请手动添加以下路径到系统 PATH:
        echo %SCRIPT_DIR%
    ) else (
        echo [成功] 已添加到系统环境变量
        echo 请重新打开命令行窗口后，输入 'agent' 即可启动
    )
) else (
    echo [跳过] 环境变量配置
    echo 您可以直接运行 agent.bat 启动程序
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 使用方法:
echo   1. 如果配置了环境变量，在任意位置输入: agent
echo   2. 或者直接运行: %SCRIPT_DIR%\agent.bat
echo.
echo 首次运行时，程序会提示您输入 API Key
echo API Key 将自动保存到配置文件中，下次无需再输入
echo.
pause

