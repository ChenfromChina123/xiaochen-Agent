#!/bin/bash
cd "$(dirname "$0")/../.."

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH."
    echo "Please install Docker to use this build method."
    echo "This method is recommended if your local Python environment lacks shared libraries."
    exit 1
fi

echo "========================================"
echo "  AgentForge Docker Builder"
echo "========================================"

echo "[1/3] Building Docker image..."
docker build -t agentforge_builder -f agentforge/packaging/Dockerfile .

if [ $? -ne 0 ]; then
    echo "[ERROR] Docker build failed."
    exit 1
fi

echo "[2/3] Extracting binary..."
mkdir -p dist
# Create a temporary container
container_id=$(docker create agentforge_builder)

# Copy the binary out from the container
docker cp $container_id:/app/dist/agentforge_terminal ./dist/agentforge_terminal

# Clean up
docker rm $container_id > /dev/null

if [ -f "dist/agentforge_terminal" ]; then
    chmod +x dist/agentforge_terminal
    echo "[3/3] Success!"
    echo "Binary location: dist/agentforge_terminal"
else
    echo "[ERROR] Binary not found in container."
    exit 1
fi
