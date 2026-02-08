# Xiaochen Agent - PowerShell Installation Script
# Usage: irm https://path.to/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Xiaochen Agent - Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 确定安装目录（假设脚本所在目录或当前目录）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }
$RootDir = Split-Path -Parent $ScriptDir
$AgentScriptsDir = Join-Path $RootDir "scripts"

Write-Host "[1/4] 检查环境..." -ForegroundColor Yellow

# 2. 检查 Python
try {
    $pyVersion = & python --version 2>&1
    Write-Host "[SUCCESS] 检测到 Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] 未检测到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    return
}

# 3. 安装依赖
Write-Host "[2/4] 安装依赖..." -ForegroundColor Yellow
$ReqFile = Join-Path $RootDir "requirements.txt"
if (Test-Path $ReqFile) {
    python -m pip install -r $ReqFile
}

# 4. 配置环境变量 (PATH)
Write-Host "[3/4] 配置全局命令 'agent'..." -ForegroundColor Yellow
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathItems = $UserPath -split ";" | ForEach-Object { $_.Trim() } | Where-Object { $_ }

if ($PathItems -notcontains $AgentScriptsDir) {
    Write-Host "正在将 $AgentScriptsDir 添加到用户 PATH..."
    $NewPath = ($PathItems + $AgentScriptsDir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "[SUCCESS] 已添加到 PATH。请重启终端生效。" -ForegroundColor Green
} else {
    Write-Host "[INFO] $AgentScriptsDir 已经在 PATH 中。" -ForegroundColor Gray
}

# 5. 初始化全局配置目录
Write-Host "[4/4] 初始化全局配置目录..." -ForegroundColor Yellow
$DataDir = Join-Path $env:USERPROFILE ".xiaochen_agent_v2"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir | Out-Null
    Write-Host "[SUCCESS] 已创建配置目录: $DataDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 安装完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "现在你可以在任何地方输入 'agent' 来启动程序。"
Write-Host "例如: agent ."
Write-Host ""
