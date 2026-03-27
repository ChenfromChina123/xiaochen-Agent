@echo off
pushd "%~dp0\..\.."

echo ========================================
echo   AgentForge EXE Builder
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
pip install -r agentforge\requirements.txt

echo [3/4] Building EXE...
set ICON_PATH=%CD%\agentforge\static\images\app.ico
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

pyinstaller --onefile --name "agentforge_terminal" --console --clean %ICON_PARAM% --version-file="agentforge/packaging/file_version_info.txt" --paths "." --add-data "agentforge/static;agentforge/static" --add-data "agentforge/config.json;agentforge" --add-data "agentforge/ocr_config.json;agentforge" agentforge\packaging\launcher.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo [4/4] Success! EXE in dist folder.
powershell -Command "Compress-Archive -Path 'dist\agentforge_terminal.exe' -DestinationPath 'dist\agentforge_terminal.zip' -Force"
echo [INFO] Created dist\agentforge_terminal.zip
deactivate
pause
