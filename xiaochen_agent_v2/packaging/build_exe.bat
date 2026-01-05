@echo off
pushd "%~dp0\..\.."

echo ========================================
echo   Xiaochen Terminal Agent EXE Builder
echo ========================================

:: Detect Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto FOUND
)

python3.13 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python3.13
    goto FOUND
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py
    goto FOUND
)

echo [ERROR] Python not found.
pause
exit /b 1

:FOUND
echo Using Python: %PY_CMD%

if not exist ".venv" (
    echo [1/4] Creating venv...
    %PY_CMD% -m venv .venv
)

echo [2/4] Installing requirements...
call .venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r xiaochen_agent_v2\requirements.txt

echo [3/4] Building EXE...
set ICON_PATH=%CD%\xiaochen_agent_v2\static\images\app.ico
set ICON_PARAM=
if exist "%ICON_PATH%" (
    echo [INFO] Found icon at %ICON_PATH%
    set ICON_PARAM=--icon="%ICON_PATH%"
) else (
    echo [WARN] Icon not found at %ICON_PATH%
)

:: Force clean build and dist folders
if exist "build" rd /s /q build
if exist "dist" rd /s /q dist

pyinstaller --onefile --name "xiaochen_terminal" --console --clean %ICON_PARAM% --paths "." --add-data "xiaochen_agent_v2/static;xiaochen_agent_v2/static" --add-data "xiaochen_agent_v2/config.json;xiaochen_agent_v2" --add-data "xiaochen_agent_v2/ocr_config.json;xiaochen_agent_v2" xiaochen_agent_v2\packaging\launcher.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo [4/4] Success! EXE in dist folder.
deactivate
pause