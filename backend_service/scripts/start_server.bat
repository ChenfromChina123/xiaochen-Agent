@echo off
chcp 65001 >nul
echo ============================================
echo OCR识别服务启动脚本
echo ============================================
echo.

cd /d %~dp0\..

set PYTHON_EXE="D:\Users\Administrator\miniconda3\python.exe"

echo [1] 检查Python环境...
%PYTHON_EXE% --version
if errorlevel 1 (
    echo [警告] 未找到 Miniconda Python，尝试使用系统默认 python...
    set PYTHON_EXE=python
    python --version
    if errorlevel 1 (
        echo [错误] 未找到任何 Python 环境，请先安装 Python 3.7+
        pause
        exit /b 1
    )
)
echo.

echo [2] 检查依赖包...
%PYTHON_EXE% -m pip show Flask >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到Flask，正在安装依赖...
    %PYTHON_EXE% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [提示] 依赖包已安装
)
echo.

echo [3] 启动OCR服务...
echo.
%PYTHON_EXE% api/server.py

pause

