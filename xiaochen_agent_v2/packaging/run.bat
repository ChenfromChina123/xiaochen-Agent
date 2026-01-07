@echo off
chcp 65001 > nul

set "PY_CMD="
set "PY_ARGS="

py -3.13 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    set "PY_ARGS=-3.13"
    goto FOUND
)

python3.13 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python3.13"
    set "PY_ARGS="
    goto FOUND
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    set "PY_ARGS="
    goto FOUND
)

echo [ERROR] Python not found.
pause
exit /b 1

:FOUND
if not exist ".venv" %PY_CMD% %PY_ARGS% -m venv .venv

call .venv\Scripts\activate
pip install -r requirements.txt >nul

echo Starting Agent...
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%..\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"
set PYTHONPATH=%ROOT_DIR%
.venv\Scripts\python -m xiaochen_agent_v2

deactivate
