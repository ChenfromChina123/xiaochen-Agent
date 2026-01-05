@echo off
chcp 65001 >nul
echo ============================================
echo OCR识别服务启动脚本
echo ============================================
echo.

cd /d %~dp0\..

echo [1] 检查Python环境...
python --version
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)
echo.

echo [2] 检查依赖包...
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到Flask，正在安装依赖...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
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
python api/server.py

pause

