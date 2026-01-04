# AISpring 工具集 V2 项目

## 项目概述
本项目是 AISpring 计划下开发的一系列工具和小型应用程序集合，包括贪吃蛇游戏实现、Void 智能体模块、网页组件以及各种功能测试脚本。

## 目录结构
| 目录/文件 | 描述 |
|-----------|------|
| `run.bat` | **推荐：Windows 一键启动脚本 (自动配置环境并启动)** |
| `build_exe.bat` | Windows 打包工具 (生成独立的 .exe 文件) |
| `requirements.txt` | 项目核心依赖列表 |
| `cpp_projects/` | C++示例项目和代码 |
| `python_snake_game/` | Python版贪吃蛇游戏实现 |
| `snake_game/` | 网页版贪吃蛇游戏 |
| `xiaochen_agent_v2/` | 小晨智能体V2核心模块 (分层架构) |
| &nbsp;&nbsp;├── `core/` | 核心逻辑 (智能体, 配置, 会话) |
| &nbsp;&nbsp;├── `tools/` | 外部工具集成 (OCR, 搜索, 网页访问) |
| &nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;└── `ocr_core/` | OCR 核心引擎 (基于 PaddleOCR-json) |
| &nbsp;&nbsp;├── `ui/` | 界面逻辑 (CLI) |
| &nbsp;&nbsp;├── `utils/` | 工具类 (控制台, 文件操作) |
| &nbsp;&nbsp;└── `scripts/` | 安装与启动脚本 |
| `webpage/` | 网页相关资源或前端组件 |
| `logs/` | 应用程序日志存储目录 |
| `__pycache__/` | 编译的Python文件（自动生成） |
| `.trae/` | 配置或临时文件目录 |
| `userrules` | 项目特定用户规则和指南 |
| `.gitignore` | Git忽略文件配置 |
| `test_doubao.py` | 豆包服务/工具集成测试脚本 |

## 关键文件说明
- `run.bat`: Windows 下的一键启动器。它会自动创建 Python 虚拟环境、安装依赖并启动智能体，无需手动干预。
- `build_exe.bat`: Windows 下的打包脚本。运行后会在 `dist/` 目录下生成 `xiaochen_agent.exe`，该文件可以分发给没有安装 Python 的用户直接运行。
- `build_linux.sh`: Linux/macOS 下的构建脚本。运行后会在 `dist/` 目录下生成 `xiaochen_terminal` 可执行文件。
- `build_linux_docker.sh`: 基于 Docker 的 Linux 构建脚本。当本地 Python 环境不满足要求（如缺少共享库）时，使用此脚本可确保构建成功。
- `cpp_projects/`: C++示例项目，包含基本的C++编程示例和构建配置
- `python_snake_game/snake_game.py`: Python版贪吃蛇游戏主程序
- `snake_game/index.html`: 网页版贪吃蛇游戏主文件
- `xiaochen_agent_v2/`: 小晨智能体V2核心模块，包含智能体相关功能
- `test_doubao.py`: 测试豆包服务的集成，包括API调用和功能检查

## 使用说明
1. **一键启动 (Windows)**: 直接在根目录双击运行 `run.bat`。该脚本会自动处理虚拟环境和依赖安装。
2. **打包为 EXE**: 如果您希望生成一个不需要 Python 环境即可运行的独立程序，请双击运行 `build_exe.bat`。打包完成后，在生成的 `dist` 文件夹中找到 `xiaochen_agent.exe` 即可使用。
3. **端口占用**: 如果端口被占用，表明程序处于热部署状态——请不要重新运行程序。
3. **传统安装方式**: Windows 下运行 `xiaochen_agent_v2/scripts/install.bat`。如果系统未将 Python 加入环境变量，脚本会尝试自动搜索常见安装路径并询问是否一键修复。重新打开终端后输入 `agent` 启动。
3. **Git同步**: 修改代码后，始终使用以下命令同步更改：
   ```bash
   git add .
   git commit -m "您的修改描述（使用中文）"
   git push
   ```
4. **控制台编码**: 运行脚本时确保控制台使用UTF-8编码，避免字符显示问题。
5. **Windows兼容性**: 针对Windows 11系统进行了优化。
6. **会话保存与格式**: 命令行对话过程中会自动将包含**完整历史记录（含系统提示词）**的会话写入`logs/sessions/`目录。会话文件采用分行内容格式（与 `void_chat` 类似），便于阅读和版本控制。
7. **历史会话管理**: 启动时可选择加载历史会话，程序会自动剔除重复的系统提示词，保持对话连贯。
8. **缩进调试**: 当使用智能体的`read_file`读取 Python 文件时，会在输出头部给出一次性缩进信息（如 `indent_style: spaces; indent_size: 4`），不再为每行附加`[s=<空格数> t=<制表符数>]`。
9. **精准读取**: `read_file` 必须显式提供 `start_line/end_line`，并且会强制限制读取窗口大小（默认最多 160 行）；同一文件相同范围在未变更时会跳过重复输出以节省 Token。
10. **批量批准**: 当智能体提出多个任务时，您可以使用`y`（一次）或`a`（始终）一次性批准，而不是重复确认每个任务。
11. **Python自动缩进**: 在`edit_lines`中，可以设置`<auto_indent>true</auto_indent>`来自动将插入的代码与周围缩进对齐。
12. **更好的通配符匹配**: 像`dir/**/*.py`这样的模式现在也匹配`dir/file.py`（没有中间子目录）。
13. **修改统计**: 文件修改统计按文件聚合，仅对增量新更改打印一次（不会每次聊天都重复，回滚不会阻止未来的统计）。
14. **终端信息**: 每个`run_command`现在都会打印`终端ID`和输出摘要到控制台。如果进程持续运行（或超时），还会打印运行终端摘要。
15. **模型切换**: 运行中支持`models`/`model use <n>`快速切换模型预设，`model set ...`自定义模型配置。
16. **会话自动保存**: 对话过程中会持续写入`logs/sessions/*_autosave.json`，退出时也会自动保存，无需手动输入`save`。
17. **AI 行为追踪**: 所有的命令执行都会被记录在全局日志文件 (`logs/process_tracker.json`) 中。系统会实时监控长时间运行的命令（如服务器进程），并在加载会话或启动时在终端反馈这些后台进程的实时状态（PID、CPU、内存等）。
18. **Linux 兼容性**: 提供了 `build_linux.sh` 脚本，可在 Linux 环境下构建独立的可执行文件。
19. **当前目录提示**: 命令提示符会实时显示当前工作目录，且该目录状态不会随 AI 模型切换而丢失。
20. **OCR 工具集成**: 系统集成了基于 PaddleOCR-json 的 OCR 功能，支持图片和 PDF 文档识别。Agent 调用时仅返回纯文本内容，过滤了坐标和置信度等冗余信息。
21. **粘贴图片优化**: 命令行支持直接粘贴图片路径或从剪贴板自动识别图片。支持 **Ctrl+V** 实时识别，系统会即时显示已粘贴的文件名（支持多图连贴），输入 `cancel` 或 `撤回` 可撤回当前待处理的图片，按回车即可发送分析。图片会自动保存到 `xiaochen_agent_v2/storage/pastes/` 目录。

## 重要规则
请参考 `userrules` 文件了解详细的项目规则和指南。
