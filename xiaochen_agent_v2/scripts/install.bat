@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Xiaochen Agent - Installation Script
echo ========================================
echo.

:: Get script directory (scripts folder)
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Get root directory
set "ROOT_DIR=%SCRIPT_DIR%\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

echo [1/4] Python detected:
python --version

:: Record Python path for agent.bat
for /f "delims=" %%i in ('powershell -NoProfile -Command "(Get-Command python).Source"') do set "PYTHON_PATH=%%i"
echo !PYTHON_PATH! > "%ROOT_DIR%\.python_path"

:: Install dependencies
echo.
echo [2/4] Installing dependencies...
pip install -r "%ROOT_DIR%\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

:: Check config
echo.
echo [3/4] Checking configuration...
if not exist "%ROOT_DIR%\config.json" (
    echo Configuration file not found, will be created on first run.
) else (
    echo Configuration file already exists.
)

:: Environment variable configuration
echo.
echo [4/4] Configuring environment variables...
set "MODE=%~1"
if "%MODE%"=="" set "MODE=user"

if /i "%MODE%"=="user" goto :INSTALL_USER
if /i "%MODE%"=="all" goto :INSTALL_ALL
if /i "%MODE%"=="skip" goto :INSTALL_SKIP

echo [ERROR] Invalid parameter: %MODE%
echo Usage:
echo   install.bat            (Default: user)
echo   install.bat user       (Current user only)
echo   install.bat all        (All users, requires admin)
echo   install.bat skip       (Skip PATH configuration)
pause
exit /b 1

:INSTALL_USER
echo Adding to User PATH...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$dir = '%SCRIPT_DIR%'; $p = [Environment]::GetEnvironmentVariable('Path','User'); if (-not $p) { $p = '' }; $items = @($p -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ }); if ($items -notcontains $dir) { $items += $dir }; [Environment]::SetEnvironmentVariable('Path', ($items -join ';'), 'User');"
if errorlevel 1 (
    echo [WARNING] Failed to set PATH. Please add this manually:
    echo %SCRIPT_DIR%
) else (
    echo [SUCCESS] Added to User PATH.
    echo Please restart your terminal and type 'agent' to start.
)
goto :INSTALL_DONE

:INSTALL_ALL
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Admin rights required for 'all' mode.
    pause
    exit /b 1
)
echo Adding to System PATH...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$dir = '%SCRIPT_DIR%'; $p = [Environment]::GetEnvironmentVariable('Path','Machine'); if (-not $p) { $p = '' }; $items = @($p -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ }); if ($items -notcontains $dir) { $items += $dir }; [Environment]::SetEnvironmentVariable('Path', ($items -join ';'), 'Machine');"
if errorlevel 1 (
    echo [WARNING] Failed to set System PATH. Please add this manually:
    echo %SCRIPT_DIR%
) else (
    echo [SUCCESS] Added to System PATH.
    echo Please restart your terminal and type 'agent' to start.
)
goto :INSTALL_DONE

:INSTALL_SKIP
echo [SKIP] PATH configuration skipped.
echo You can run the agent using: %SCRIPT_DIR%\agent.bat
goto :INSTALL_DONE

:INSTALL_DONE
echo.
echo ========================================
echo Installation Finished!
echo ========================================
echo.
echo How to use:
echo   1. If PATH is configured, type: agent
echo   2. Or run directly: %SCRIPT_DIR%\agent.bat
echo.
echo On first run, you will be asked for your API Key.
echo It will be saved automatically for future use.
echo.
pause
exit /b 0
