@echo off

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

echo [ERROR] Python not found.
pause
exit /b 1

:FOUND
if not exist ".venv" %PY_CMD% -m venv .venv

call .venv\Scripts\activate
pip install -r requirements.txt >nul

echo Starting Agent...
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%..\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"
set PYTHONPATH=%ROOT_DIR%
python -m xiaochen_agent_v2

deactivate