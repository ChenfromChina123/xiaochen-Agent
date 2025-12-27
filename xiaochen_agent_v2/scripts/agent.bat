@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Package directory (xiaochen_agent_v2)
set "PACKAGE_DIR=%SCRIPT_DIR%\.."
for %%I in ("%PACKAGE_DIR%") do set "PACKAGE_DIR=%%~fI"

:: Root directory (parent of xiaochen_agent_v2)
set "ROOT_DIR=%PACKAGE_DIR%\.."
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"

:: Set PYTHONPATH to include the parent of the package
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
    :: Global python failed, check for saved path in package dir
    if exist "%PACKAGE_DIR%\.python_path" (
        for /f "usebackq delims=" %%i in ("%PACKAGE_DIR%\.python_path") do (
            set "SAVED_PYTHON=%%i"
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
