#!/bin/bash

echo "========================================"
echo "  Xiaochen Terminal Agent Linux Builder"
echo "========================================"

# Detect Python
if command -v python3 &> /dev/null; then
    PY_CMD=python3
elif command -v python &> /dev/null; then
    PY_CMD=python
else
    echo "[ERROR] Python not found."
    exit 1
fi

echo "Using Python: $PY_CMD"

if [ ! -d ".venv" ]; then
    echo "[1/4] Creating venv..."
    $PY_CMD -m venv .venv
fi

echo "[2/4] Installing requirements..."
source .venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

echo "[3/4] Building Binary..."

# Force clean build and dist folders
rm -rf build dist

# Check if static/images/app.ico exists, though icon is mostly for Windows/Mac .app
ICON_PARAM=""
if [ -f "static/images/app.ico" ]; then
    ICON_PARAM="--icon=static/images/app.ico"
fi

# PyInstaller command for Linux (onefile)
pyinstaller --onefile --name "xiaochen_terminal" --clean $ICON_PARAM \
    --add-data "xiaochen_agent_v2:xiaochen_agent_v2" \
    --add-data "static:static" \
    launcher.py

if [ $? -ne 0 ]; then
    echo "[ERROR] Build failed."
    exit 1
fi

echo "[4/4] Success! Binary in dist/xiaochen_terminal"
deactivate
