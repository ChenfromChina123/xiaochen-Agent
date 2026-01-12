@echo off
echo ========================================
echo Xiaochen Agent - Environment Setup
echo ========================================
echo.

:: Get current directory (scripts folder)
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Get root directory
set "ROOT_DIR=%SCRIPT_DIR%\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

echo [INFO] Setting environment variables...
echo.

:: Set XIAOCHEN_AGENT_HOME environment variable
setx XIAOCHEN_AGENT_HOME "%ROOT_DIR%"
echo [SUCCESS] XIAOCHEN_AGENT_HOME set to: %ROOT_DIR%

:: Add scripts directory to PATH
set "NEW_PATH=%PATH%"
echo %NEW_PATH% | findstr /C:"%SCRIPT_DIR%" >nul
if errorlevel 1 (
    setx PATH "%SCRIPT_DIR%;%PATH%"
    echo [SUCCESS] Added to PATH: %SCRIPT_DIR%
) else (
    echo [INFO] Scripts directory already in PATH
)

echo.
echo [INFO] Environment variables set successfully!
echo.
echo [NOTE] You may need to restart your terminal for changes to take effect.
echo.
echo [USAGE] After restart, you can run:
echo         agent        - Start the agent
echo         agent --help - Show help
pause