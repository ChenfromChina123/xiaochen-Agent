FROM python:3.12-slim

# Use Aliyun mirror for apt to speed up build in China
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# Use Aliyun mirror for pip
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_TRUSTED_HOST=mirrors.aliyun.com

# Install system dependencies
# binutils: for pyinstaller to check binaries
RUN apt-get update && apt-get install -y \
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
