# AISpring 工具集 V2 项目

## 项目概述
本项目是 AISpring 计划下开发的一系列工具和小型应用程序集合，包括贪吃蛇游戏实现、Void 智能体模块、网页组件以及各种功能测试脚本。

## 目录结构
| 目录/文件 | 描述 |
|-----------|------|
| `cpp_projects/` | C++示例项目和代码 |
| `python_snake_game/` | Python版贪吃蛇游戏实现 |
| `snake_game/` | 网页版贪吃蛇游戏 |
| `xiaochen_agent_v2/` | 小晨智能体V2核心模块 (分层架构) |
| &nbsp;&nbsp;├── `core/` | 核心逻辑 (智能体, 配置, 会话) |
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
- `cpp_projects/`: C++示例项目，包含基本的C++编程示例和构建配置
- `python_snake_game/snake_game.py`: Python版贪吃蛇游戏主程序
- `snake_game/index.html`: 网页版贪吃蛇游戏主文件
- `xiaochen_agent_v2/`: 小晨智能体V2核心模块，包含智能体相关功能
- `test_doubao.py`: 测试豆包服务的集成，包括API调用和功能检查

## 使用说明
1. **端口占用**: 如果端口被占用，表明程序处于热部署状态——请不要重新运行程序。
2. **一键安装**: Windows 下运行 `xiaochen_agent_v2/scripts/install.bat`（默认仅当前用户加入 PATH），重新打开终端后输入 `agent` 启动。
3. **Git同步**: 修改代码后，始终使用以下命令同步更改：
   ```bash
   git add .
   git commit -m "您的修改描述（使用中文）"
   git push
   ```
4. **控制台编码**: 运行脚本时确保控制台使用UTF-8编码，避免字符显示问题。
5. **Windows兼容性**: 针对Windows 11系统进行了优化。
6. **会话自动保存**: 命令行对话过程中会自动将完整会话写入`logs/sessions/`目录（文件名包含`_autosave`），用于下次加载继续对话。
7. **缩进调试**: 当使用智能体的`read_file`读取Python文件时，每行包含`[s=<空格数> t=<制表符数>]`以使隐藏的缩进显式化。
8. **批量批准**: 当智能体提出多个任务时，您可以使用`y`（一次）或`a`（始终）一次性批准，而不是重复确认每个任务。
9. **Python自动缩进**: 在`edit_lines`中，可以设置`<auto_indent>true</auto_indent>`来自动将插入的代码与周围缩进对齐。
10. **更好的通配符匹配**: 像`dir/**/*.py`这样的模式现在也匹配`dir/file.py`（没有中间子目录）。
11. **修改统计**: 文件修改统计按文件聚合，仅对增量新更改打印一次（不会每次聊天都重复，回滚不会阻止未来的统计）。
12. **终端信息**: 每个`run_command`现在都会打印`终端ID`和输出摘要到控制台。如果进程持续运行（或超时），还会打印运行终端摘要。

## 重要规则
请参考 `userrules` 文件了解详细的项目规则和指南。
