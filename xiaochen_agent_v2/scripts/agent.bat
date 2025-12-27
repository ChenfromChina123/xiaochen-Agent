@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: Get current directory
set "AGENT_DIR=%~dp0"
set "AGENT_DIR=%AGENT_DIR:~0,-1%"

:: Set PYTHONPATH to parent directory to allow "import xiaochen_agent_v2"
set "ROOT_DIR=%AGENT_DIR%\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

if defined PYTHONPATH (
    set "PYTHONPATH=%ROOT_DIR%;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%ROOT_DIR%"
)

:: Try to find Python path from config if global 'python' fails
set "PYTHON_EXE=python"

:: Check if global python works
where %PYTHON_EXE% >nul 2>&1
if errorlevel 1 (
    :: Global python failed, check for saved path
    if exist "%ROOT_DIR%\.python_path" (
        for /f "usebackq delims=" %%i in ("%ROOT_DIR%\.python_path") do (
            set "SAVED_PYTHON=%%i"
            :: Remove trailing space if any
            set "SAVED_PYTHON=!SAVED_PYTHON:~0!"
            if exist "!SAVED_PYTHON!" (
                set "PYTHON_EXE=!SAVED_PYTHON!"
            )
        )
    )
)

:: Run the agent
"!PYTHON_EXE!" -m xiaochen_agent_v2 %*

endlocal
