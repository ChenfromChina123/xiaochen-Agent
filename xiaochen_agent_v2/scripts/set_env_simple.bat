@echo off
echo ========================================
echo Xiaochen Agent - Environment Setup (Simple)
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

:: Create an alias command in user's profile
echo Creating alias in user profile...

:: Check if we're running as administrator
net session >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Running as administrator, creating system-wide alias...
    
    :: Create a batch file in System32
    copy "%SCRIPT_DIR%\agent.bat" "%SystemRoot%\System32\agent.bat" >nul
    if %errorlevel% equ 0 (
        echo [SUCCESS] Created system-wide 'agent' command
    ) else (
        echo [WARNING] Could not create system-wide command
    )
) else (
    echo [INFO] Not running as administrator, creating user alias...
    
    :: Create a batch file in user's local bin directory
    if not exist "%USERPROFILE%\bin" mkdir "%USERPROFILE%\bin"
    copy "%SCRIPT_DIR%\agent.bat" "%USERPROFILE%\bin\agent.bat" >nul
    if %errorlevel% equ 0 (
        echo [SUCCESS] Created user 'agent' command in %USERPROFILE%\bin
        echo [NOTE] Add %USERPROFILE%\bin to your PATH to use 'agent' command
    )
)

echo.
echo [INFO] Environment setup completed!
echo.
echo [USAGE] You can now use:
echo         agent        - Start the agent (if added to PATH)
echo         Or navigate to %ROOT_DIR% and use python -m xiaochen_agent_v2
pause