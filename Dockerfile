FROM python:3.12-slim

# Install system dependencies
# build-essential: for compiling c extensions (like psutil if needed)
# binutils: for pyinstaller to check binaries
RUN apt-get update && apt-get install -y \
    build-essential \
    binutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY . .

# Grant execution permission
RUN chmod +x build_linux.sh

# Run the build script
# The script creates a venv and runs pyinstaller
RUN ./build_linux.sh
