# AISpring 工具集 V2 项目

## 项目概述
本项目是 AISpring 计划下开发的一系列工具和小型应用程序集合，包括贪吃蛇游戏实现、Void 智能体模块、网页组件以及各种功能测试脚本。

## 目录结构
| 目录/文件 | 描述 |
|-----------|------|
| `backend_service/` | **OCR 后端服务 (分层架构)** |
| &nbsp;&nbsp;├── `api/` | API 接口层 (server.py) |
| &nbsp;&nbsp;├── `core/` | 核心引擎层 (PaddleOCR-json) |
| &nbsp;&nbsp;├── `configs/` | 配置文件 (config.json) |
| &nbsp;&nbsp;├── `scripts/` | 启动脚本 (start_server.bat) |
| &nbsp;&nbsp;├── `tests/` | 测试代码 |
| &nbsp;&nbsp;└── `docs/` | 文档说明 |
| `xiaochen_agent_v2/` | 小晨智能体V2核心模块 (分层架构) |
| &nbsp;&nbsp;├── `core/` | 核心逻辑 (智能体, 配置, 会话) |
| &nbsp;&nbsp;├── `tools/` | 外部工具集成 (OCR, 搜索, 网页访问) |
| &nbsp;&nbsp;├── `ui/` | 界面逻辑 (CLI) |
| &nbsp;&nbsp;├── `utils/` | 工具类 (控制台, 文件操作) |
| &nbsp;&nbsp;├── `scripts/` | 安装与启动脚本 |
| &nbsp;&nbsp;├── `packaging/` | 打包工具与构建脚本 (Windows/Linux/Docker) |
| &nbsp;&nbsp;├── `logs/` | 应用程序日志存储目录 |
| &nbsp;&nbsp;├── `docs/` | 文档说明 (包括本 README) |
| &nbsp;&nbsp;├── `tests/` | 测试脚本与数据 |
| &nbsp;&nbsp;└── `static/` | 静态资源 (图标等) |
| `.gitignore` | Git忽略文件配置 |

## 关键文件说明
- `xiaochen_agent_v2/run.py`: 智能体入口程序。
- `xiaochen_agent_v2/packaging/run.bat`: Windows 下的一键启动器。它会自动创建 Python 虚拟环境、安装依赖并启动智能体。
- `xiaochen_agent_v2/packaging/build_exe.bat`: Windows 下的打包脚本。运行后会在 `dist/` 目录下生成 `xiaochen_agent.exe`。
- `xiaochen_agent_v2/packaging/build_linux.sh`: Linux/macOS 下的构建脚本。
- `xiaochen_agent_v2/packaging/build_linux_docker.sh`: 基于 Docker 的 Linux 构建脚本。

## 使用说明
1. **一键启动 (Windows)**: 运行 `xiaochen_agent_v2/packaging/run.bat`。
2. **打包为 EXE**: 运行 `xiaochen_agent_v2/packaging/build_exe.bat`。
3. **传统安装方式**: Windows 下运行 `xiaochen_agent_v2/scripts/install.bat`。
4. **会话保存与格式**: 会话写入`xiaochen_agent_v2/logs/sessions/`目录。
5. **AI 行为追踪**: 命令执行记录在 `xiaochen_agent_v2/logs/process_tracker.json` 中。

## 重要规则
请参考 `userrules` 文件了解详细的项目规则和指南。
