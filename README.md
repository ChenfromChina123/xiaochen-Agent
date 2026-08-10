# 智匠 AgentForge (AGENTFORGE_TERMINAL)

一个强大的 AI 终端助手，支持多种 LLM 模型，提供智能的命令行交互体验。

> 本仓库包含该项目两个迭代版本，功能核心相同，`xiaochen_agent_v2` 在 `agentforge` 基础上增加了完整的打包与分发配置。

## 📦 仓库结构

| 目录 | 说明 |
|------|------|
| `agentforge/` | v1 版本：AI 终端助手核心（Agent、会话、工具、OCR、终端管理） |
| `xiaochen_agent_v2/` | v2 版本：在 v1 基础上补充 PyInstaller / Docker 打包配置（`xiaochen_agent.spec`、`build_exe.bat`、`Dockerfile` 等） |
| `tests/` | 根目录级测试（日志滑动窗口、简单 ID 等） |

## 🚀 快速开始

两个版本的使用方式一致：

```bash
# 进入任一版本目录，安装依赖
pip install -r agentforge/requirements.txt

# 运行
python agentforge/run.py
```

一键安装脚本（配置全局 `agent` 命令）：

- **Windows (PowerShell)**

  ```powershell
  irm https://raw.githubusercontent.com/ChenfromChina123/AgentForge/main/agentforge/scripts/install.ps1 | iex
  ```

- **Linux / macOS (Bash/Zsh)**

  ```bash
  curl -sSL https://raw.githubusercontent.com/ChenfromChina123/AgentForge/main/agentforge/scripts/install.sh | bash
  ```

安装后可在任意目录直接输入 `agent`（或 `agent D:\MyProject` 指定目录）启动。

## ✨ 主要功能

- **AI 智能助手**：支持 DeepSeek、Doubao 等多种 LLM 模型；智能理解意图并执行文件读写、编辑、搜索、命令执行等操作
- **会话管理**：保存/加载会话历史、会话命名、自动时间戳
- **工具集成**：OCR 识别、图片处理、网页搜索、终端输出管理
- **任务回滚**：内置回滚管理器，任务执行出错可回退
- **打包分发**：支持 exe / Linux 二进制 / Docker 镜像构建

## 📚 详细文档

- v1：见 [`agentforge/README.md`](agentforge/README.md)
- v2：见 [`xiaochen_agent_v2/README.md`](xiaochen_agent_v2/README.md)
- 说明文档：`agentforge/docs/ROOT_README.md`

## 📄 许可

请参考各子目录中的开源声明与许可文件。
