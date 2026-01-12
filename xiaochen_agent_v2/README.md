# 小晨终端助手 (XIAOCHEN_TERMINAL)

一个强大的 AI 终端助手，支持多种 LLM 模型，提供智能的命令行交互体验。

## ✨ 主要功能

### 🤖 AI 智能助手
- 支持多种 LLM 模型（DeepSeek、Doubao 等）
- 智能理解用户意图并执行相应操作
- 支持文件读写、编辑、搜索等操作
- 支持命令执行和长期运行任务管理

### 💾 会话管理
- **保存会话历史**：可以保存当前对话历史，方便后续复用
- **加载历史会话**：启动时可以选择加载之前保存的会话
- **会话命名**：支持为会话添加自定义名称，便于识别
- **自动时间戳**：每个会话自动记录创建时间

### 🔄 增强回滚系统

独立的版本控制模块，提供专业级的文件回滚功能：

#### 核心功能
- **多级版本历史**：保存所有文件的历史版本，可回滚到任意版本
- **版本对比**：查看任意两个版本之间的差异（diff）
- **快照管理**：创建多文件快照，一键恢复整个项目状态
- **版本标签**：为重要版本打标签（如 `stable`, `tested`, `release`）
- **智能清理**：自动清理旧版本，保留最近和标记的重要版本
- **统计信息**：查看存储使用情况和版本数量

#### 使用示例

```python
from xiaochen_agent_v2.core.rollback_manager import RollbackManager

# 初始化回滚管理器
rm = RollbackManager()

# 备份文件（修改前）
rm.backup_file("config.py", operation="edit", description="Updated settings")

# 回滚到上一个版本
rm.rollback_file("config.py", steps_back=1)

# 查看版本历史
history = rm.get_version_history("config.py", limit=10)

# 比较版本差异
success, diff = rm.get_diff("config.py")

# 创建快照
rm.create_snapshot("项目里程碑 v1.0", tags=["milestone"])

# 恢复快照
rm.restore_snapshot(snapshot_id)

# 为版本打标签
rm.add_tag("config.py", version_id, "stable")

# 清理旧版本（保留最近5个和所有标记版本）
rm.cleanup_old_versions(keep_recent=5, keep_tagged=True)
```

#### 运行示例
```bash
cd xiaochen_agent_v2
python examples/rollback_example.py
```

### 🔍 OCR 识别工具
- **图片识别**：支持对本地图片（PNG, JPG, BMP等）进行文字识别
- **文档识别**：支持对 PDF 等多页文档进行 OCR 识别，支持指定页码范围
- **backend_service 支持**：采用高性能 OCR backend_service，支持多并发和多种文件格式
- **自动保存**：识别结果自动保存到 `storage/ocr_results` 目录下，方便后续查阅

### 🎨 友好的显示界面
- **工具执行可视化**：使用图标和友好格式显示 AI 工具调用
  - 📖 读取文件
  - ✍️ 写入文件
  - ✏️ 编辑文件
  - ⚙️ 执行命令
  - 🔍 搜索文件
  - 📝 任务管理
- **结果格式化**：优化工具执行结果的显示，避免信息过载
- **终端截断保护**：当终端执行命令返回内容过长时（超过 2000 字符），自动截断并仅保留尾部关键信息，节省 token 消耗
- **进度提示**：清晰显示任务执行进度（如 [1/5]）

### ⚡ 中断控制
- **打断 AI 输出**：在 AI 生成回复时按 `Ctrl+C` 可以打断当前输出，保留已生成的内容并允许用户继续对话
- **任务终止同步**：在执行 OCR 等耗时工具时按 `Ctrl+C` 会自动通知后端服务器终止对应任务，释放资源
- **随时中断**：在工具执行确认阶段按 `Ctrl+C` 可以取消当前任务
- **安全退出**：首次 `Ctrl+C` 仅请求中断并自动保存；1.5 秒内再次按 `Ctrl+C` 才会退出（会尝试再次自动保存）

### 🖥️ 终端增强功能

- **进程管理优化**:
  - `ps`: 列表形式展示子进程信息，支持 **简单 ID** (1, 2, 3...)。
  - `watch`: 实时监控子进程输出，支持 **PID** 或 **简单 ID**。
  - `kill`: 终止指定进程，支持 **PID** 或 **简单 ID**。
  - **默认行为**: `watch` 和 `kill` 无参数执行时，默认操作最近启动的子进程。
- **交互式支持**:
  - `watch` 模式下按 `i` 键进入 **交互模式**，支持向子进程发送输入（如确认提示、密码等）。
  - 支持向后台进程发送 `Ctrl+C` 等控制指令。
- **输出同步**:
  - 监控输出时采用实时刷新技术，确保终端显示与日志文件内容完全同步。

### 记录与日志

- **使用记录滑动窗口**: `void_usage_history.jsonl` 自动保留最近 **2000 条** Token 使用记录，防止日志文件无限增长。
- **结构化日志**: 所有 AI 工具调用和系统事件均有详细的时间戳和上下文记录。

### 📁 项目结构优化

为了提高可维护性，项目进行了模块化重组：
- `xiaochen_agent_v2/core/`: 核心逻辑（AI 模型对接、回滚系统、会话管理）。
- `xiaochen_agent_v2/ui/`: 用户界面相关（CLI 逻辑、显示优化）。
- `xiaochen_agent_v2/utils/`: 通用工具（终端管理、日志系统、OCR 接口）。
- `xiaochen_agent_v2/tools/`: AI 插件工具集。
- `xiaochen_agent_v2/scripts/`: 环境设置和辅助脚本。
- `xiaochen_agent_v2/config_samples/`: 配置文件示例。
- **任务管理**：内置任务列表，跟踪执行进度
- **日志记录**：完整的操作日志和使用统计

## 🚀 快速开始

### 方式一：一键安装（推荐）

#### Windows 用户

1. 双击运行 `scripts/install.bat`
2. 按照提示完成安装
3. 重新打开命令行，输入 `agent` 即可启动

```cmd
scripts\install.bat
```

#### Linux/Mac 用户

1. 运行安装脚本：

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

2. 按照提示完成安装
3. 重新打开终端，输入 `agent` 即可启动

### 方式二：手动安装

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 方式三：打包部署 (Windows)

1. 运行打包脚本：

```cmd
xiaochen_agent_v2\packaging\build_exe.bat
```

2. 打包完成后，在项目根目录的 `dist` 文件夹下会生成 `xiaochen_terminal.exe`。
3. 您可以将该 EXE 文件移动到任何位置直接运行，无需安装 Python 环境。

#### 2. 配置 API Key（三种方式任选其一）

**方式 A：使用配置文件（推荐）**

首次运行时，程序会提示输入 API Key，并自动保存到 `config.json`：

```bash
python -m xiaochen_agent_v2
```

或从示例文件复制并修改：

```bash
# Windows
copy config_samples\config.json.example config.json

# Linux/Mac
cp config_samples/config.json.example config.json
```

也可以手动创建 `config.json`：

```json
{
  "api_key": "your_api_key_here",
  "base_url": "https://api.deepseek.com",
  "model_name": "deepseek-chat",
  "logs_dir": "logs",
  "storage_dir": "storage"
}
```

*注意：`logs_dir` 和 `storage_dir` 支持相对路径（相对于程序根目录）或绝对路径。*

**方式 B：使用环境变量**

```bash
# Windows
set VOID_API_KEY=your_api_key_here
set VOID_BASE_URL=https://api.deepseek.com
set VOID_MODEL=deepseek-chat
set XIAOCHEN_START_CWD=D:\your\project\path  # 设置 Agent 启动时的初始目录

# Linux/Mac
export VOID_API_KEY=your_api_key_here
export VOID_BASE_URL=https://api.deepseek.com
export VOID_MODEL=deepseek-chat
export XIAOCHEN_START_CWD=/your/project/path
```

**方式 C：每次启动时输入**

直接运行程序，按提示输入（不推荐）

#### 3. 运行程序

```bash
# 方式 1：使用 Python 模块
python -m xiaochen_agent_v2

# 方式 2：使用启动脚本
python run.py

# 方式 3：使用批处理文件（Windows）
agent.bat

# 方式 4：使用 Shell 脚本（Linux/Mac）
./agent.sh
```

### 配置优先级

程序按以下优先级读取配置：

1. **环境变量**（最高优先级）
2. **配置文件** `config.json`
3. **用户输入**（最低优先级）

## 📖 使用指南

### 基本命令

- **正常对话**：直接输入问题或指令
- **保存会话**：输入 `save` 保存当前会话
- **自动保存**：对话过程中自动保存到 `xiaochen_agent_v2/logs/sessions/*_autosave.json`，退出时也会自动保存
- **清空历史**：输入 `clear` 清空会话历史
- **回滚操作**：输入 `rollback` 撤销上一次文件操作
- **一键回退对话**：输入 `undo` 回退到上一次对话（含文件修改）
- **增强回滚系统**：使用独立的 `RollbackManager` 提供更强大的版本控制功能（详见下方）
- **撤回粘贴**：输入 `cancel` 或 `撤回` 撤回当前已通过 Ctrl+V 粘贴但未发送的图片
- **查看后台进程**：输入 `ps` 查看正在运行的任务
- **监控进程输出**：输入 `watch <id>` 进入监控模式（支持 q 退出、p 暂停、k/f 终止、c 清屏、+/- 调速、t 状态）
- **长命令自动转后台**：命令执行若超过最大等待时间（默认约 10 秒）会返回 Terminal ID，可用 `watch <id>` 继续观察
- **交互式程序提示**：后台命令默认不接收键盘输入（避免抢占当前终端），交互式程序请直接在终端运行
- **查看会话列表**：输入 `sessions` 查看最近 10 个历史会话
- **删除会话**：输入 `sessions delete <n...|--all> [-y]` 删除指定或所有会话
- **清理会话**：输入 `sessions prune [--max-files N] [--max-age-days D] [-y]` 清理会话
- **加载会话**：输入 `load <n>` 加载第 n 个历史会话（不退出）
- **新建会话**：输入 `new` 新建空会话并继续对话
- **模型预设**：输入 `models` 列出模型预设
- **查看模型**：输入 `model` 查看当前模型配置
- **切换模型**：输入 `model use <n>` 切换到第 n 个模型预设
- **自定义模型**：输入 `model set <base_url> <model_name> [ssl]` 自定义模型配置
- **设置密钥**：输入 `model key <api_key>` 更新 API Key
- **退出程序**：输入 `exit` 或 `quit`
- **帮助命令**：输入 `help` 或 `?` 显示命令帮助信息
- **关键词判定**：当系统关键词后还跟随其他文本时，会按“正常对话”处理（例如 `help 配置怎么写`）

### 会话管理

#### 启动时加载会话

程序启动时会询问是否加载历史会话：

```
是否加载历史会话? (y=是 / n=否，默认n): y

可用的历史会话:
1. [20251227_143022] 15 条消息 (23.5 KB)
2. [20251227_120145] 8 条消息 (12.3 KB)

选择会话编号 (1-2, 或按回车跳过): 1
✓ 已加载会话: 20251227_143022_项目优化.json
  包含 15 条历史消息
```

#### 保存当前会话

在对话过程中随时输入 `save`：

```
User: save
输入会话名称 (可选，按回车跳过): 项目优化讨论
✓ 会话已保存: 20251227_143530_项目优化讨论.json
```

#### 退出时保存

输入 `exit` 退出时会提示保存：

```
User: exit
是否保存当前会话? (y/n, 默认n): y
输入会话名称 (可选，按回车跳过): 
✓ 会话已保存: 20251227_144022.json
```

#### 管理历史会话

除了自动保存，你还可以通过 `sessions` 命令对历史记录进行精细化管理：

- **查看列表**：输入 `sessions` 查看最近 10 条会话。
- **删除会话**：
    - `sessions delete <编号>`：删除指定编号的会话（需确认）。
    - `sessions delete <编号1> <编号2> -y`：批量删除且不提示确认。
    - `sessions delete --all`：清空所有会话记录（支持 `all`, `-all` 或 `--all`）。
    - `sessions delete <完整文件名>`：删除不在最近列表中的特定文件。
    - `sessions delete`：不带参数执行，将进入交互式多选模式。
- **清理与维护**：
    - `sessions prune --max-files 50`：保留最近的 50 个文件，其余删除。
    - `sessions prune --max-age-days 7`：删除 7 天前的所有历史会话。

> **💡 提示**：
> - 编号（1-10）对应 `sessions` 列表显示的顺序，最上面的通常是最近的会话。
> - 文件名通常包含日期，如 `20251231_...json`。
> - 在 `sessions delete` 交互模式下，你可以一次性输入 `1, 2, 5` 这种带逗号的格式。

```text
User: sessions delete 1 2 -y
✓ 删除完成 (deleted=2, missing=0, errors=0)

User: sessions delete --all
警告: 即将删除所有会话 (15 个)！
确认清空所有会话? (y/N): y
✓ 已清空所有会话 (deleted=15)

User: sessions prune --max-files 10
将清理会话: max_files=10, max_age_days=None
确认清理? (y/N): y
✓ 清理完成 (deleted=5, kept=10, errors=0)
```

#### 跨会话状态恢复

### 中断控制

在 AI 执行任务时，可以随时按 `Ctrl+C` 中断：

```
[Cycle 2/30] Processing...
^C
✓ 会话已自动保存: ..._autosave.json

⚠️  已请求中断 (Ctrl+C)。为避免误触，不会立即退出。
   若要强制退出，请在 1.5 秒内再按一次 Ctrl+C
```

### 任务执行确认

程序会显示即将执行的任务列表：

```
==================================================
开始执行 3 个任务
==================================================

[1/3] 📖 读取: config.py
[2/3] ✏️  编辑: config.py (删除 10-15, 插入于 10)
[3/3] ⚙️  执行: git add .
```

#### 交互式命令（Windows）

当命令需要交互式输入（例如启动另一个 CLI 程序）时，需要启用交互模式执行，否则子进程会因为无法读取输入而退出。

交互模式示例：

```xml
<run_command>
<command>python xiaochen_agent_v2/run.py</command>
<is_long_running>true</is_long_running>
<cwd>.</cwd>
<interactive>true</interactive>
</run_command>
```

说明：
- Windows 下交互模式会打开新的控制台窗口，且不会回传 stdout/stderr 到当前对话。
- 若未显式指定 `interactive`，当检测到 `python xiaochen_agent_v2/run.py`（或 `python -m xiaochen_agent_v2`）且 `is_long_running=true` 时会自动启用交互模式。

## 📁 项目结构

```
xiaochen_agent_v2/
├── xiaochen_agent_v2/      # 主程序包
│   ├── __init__.py         # 包初始化
│   ├── __main__.py         # 程序入口
│   ├── agent.py            # Agent 核心逻辑
│   ├── config.py           # 配置数据类
│   ├── config_manager.py   # 配置文件管理
│   ├── metrics.py          # 性能指标
│   ├── rollback_manager.py # 回滚管理
│   ├── session.py          # 会话管理
│   ├── task_manager.py     # 任务管理
│   └── terminal_output_manager.py # 终端输出管理
├── tools/                  # 工具模块
│   ├── executor.py         # 工具执行器
│   ├── image.py            # 图像处理工具
│   ├── ocr.py              # OCR 工具
│   └── web_search.py       # 网络搜索工具
├── ui/                     # 用户界面
│   └── cli.py              # 命令行界面
├── utils/                  # 通用工具
│   ├── console.py          # 控制台输出
│   ├── display.py          # 显示格式化
│   ├── files.py            # 文件操作
│   ├── interrupt.py        # 中断处理
│   ├── logs.py             # 日志记录
│   ├── tags.py             # 标签解析
│   └── terminal.py         # 终端管理
├── scripts/                # 脚本目录
│   ├── agent.bat           # Windows 启动脚本
│   ├── install.bat         # Windows 安装脚本
│   ├── set_env.bat         # 环境变量设置
│   └── ...
├── config_samples/         # 配置文件示例
│   ├── config.json.example # 配置文件示例
│   └── ocr_config.json.example
├── run.py                  # Python 运行脚本
├── requirements.txt        # 依赖列表
└── README.md               # 项目文档
```

## 🔧 配置说明

### 配置文件 (config.json)

配置文件支持以下选项：

```json
{
  "api_key": "your_api_key_here",        // API 密钥（必填）
  "base_url": "https://api.deepseek.com", // API 基础 URL
  "model_name": "deepseek-chat",          // 模型名称
  "verify_ssl": true,                     // 是否验证 SSL 证书
  "auto_save_session": false,             // 是否自动保存会话
  "max_cycles": 30,                       // 最大循环次数
  "token_threshold": 30000,               // 触发“长期摘要”压缩的 token 阈值（估算值）
  "whitelisted_tools": [                  // 允许自动执行的工具白名单
    "search_files",
    "search_in_files",
    "read_file",
    "task_add",
    "task_update",
    "task_delete",
    "task_list",
    "task_clear"
  ],
  "whitelisted_commands": [               // run_command 允许的命令白名单（按首个单词匹配）
    "ls",
    "dir",
    "pwd",
    "whoami",
    "echo",
    "cat",
    "type"
  ],
  "read_indent_mode": "header",           // 读取代码时的缩进展示模式：smart/header
  "python_validate_ruff": "auto"          // Python 校验：auto(自动探测 ruff)/off(禁用 ruff，仅 py_compile)
}
```

- `token_threshold`：当单次请求构造的消息历史（估算 token）超过该阈值时，程序会生成/更新一条系统消息 `【长期摘要】`，并丢弃更早的详细历史，仅保留最近一小段对话用于继续交互。

### 模型预设

程序内置了以下模型预设：

1. **DeepSeek (Default)**
   - Base URL: `https://api.deepseek.com`
   - Model: `deepseek-chat`
   - 推荐用于：通用对话、代码生成

2. **Doubao (Volcano Ark)**
   - Base URL: `https://ark.cn-beijing.volces.com/api/v3`
   - Model: `doubao-seed-1-6-251015`
   - 推荐用于：中文对话

### 会话存储

会话文件默认存储在 `logs/sessions/` 目录下，格式为：

```
20251227_143022_会话名称.json
```

每个会话文件包含：
- 时间戳
- 创建时间
- 消息数量
- 标题（首次对话时由 AI 并行生成；若缺失则使用首条用户输入作为标题）
- 完整的消息历史（首条为系统提示词 System Message）
- 缓存统计（cache_stats，用于命中率的跨会话恢复）

### 环境变量配置到系统

#### Windows (永久配置)

```cmd
# 添加到用户环境变量
setx VOID_API_KEY "your_api_key_here"

# 或使用图形界面
# 1. Win + R 输入 sysdm.cpl
# 2. 高级 -> 环境变量
# 3. 新建用户变量 VOID_API_KEY
```

#### Linux/Mac (永久配置)

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export VOID_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

## 🎯 使用场景

1. **代码开发**：让 AI 帮助编写、修改、调试代码
2. **文件管理**：批量处理文件，搜索内容
3. **任务自动化**：执行复杂的命令序列
4. **学习记录**：保存与 AI 的对话历史，方便回顾
5. **项目协作**：分享会话历史，复用成功的对话流程

## ⚠️ 注意事项

1. **API Key 安全**：不要将 API Key 提交到版本控制系统
2. **会话隐私**：会话文件可能包含敏感信息，注意保护
3. **命令安全**：程序会阻止危险命令（如 `rm -rf`），但仍需谨慎
4. **中断时机**：在 AI 思考或执行任务时可以中断，但可能导致任务未完成
5. **Token 与缓存命中率**：仅首轮输入会携带完整“目录/规则/任务”上下文，后续轮次会自动精简以减少重复 token，提高缓存命中比例。

## 📝 更新日志

### v2.1.0 (2025-12-27)

#### 新增功能
- ✅ 会话历史保存和加载功能
- ✅ 友好的工具执行显示界面
- ✅ 用户中断 AI 执行功能
- ✅ 优化命令结果显示，避免重复输出

#### 改进
- 优化任务执行流程，显示更清晰
- 改进中断处理逻辑，支持二次确认
- 增强会话管理功能，支持命名和列表

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过 Issue 反馈。
