#!/bin/bash

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH."
    echo "Please install Docker to use this build method."
    echo "This method is recommended if your local Python environment lacks shared libraries."
    exit 1
fi

echo "========================================"
echo "  Xiaochen Terminal Docker Builder"
echo "========================================"

echo "[1/3] Building Docker image..."
docker build -t xiaochen_terminal_builder .

if [ $? -ne 0 ]; then
    echo "[ERROR] Docker build failed."
    exit 1
fi

echo "[2/3] Extracting binary..."
mkdir -p dist
# Create a temporary container
container_id=$(docker create xiaochen_terminal_builder)

# Copy the binary out from the container
docker cp $container_id:/app/dist/xiaochen_terminal ./dist/xiaochen_terminal

# Clean up
docker rm $container_id > /dev/null

if [ -f "dist/xiaochen_terminal" ]; then
    chmod +x dist/xiaochen_terminal
    echo "[3/3] Success!"
    echo "Binary location: dist/xiaochen_terminal"
else
    echo "[ERROR] Binary not found in container."
    exit 1
fi
