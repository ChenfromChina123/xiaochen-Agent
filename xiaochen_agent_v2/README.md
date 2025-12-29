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

### 🎨 友好的显示界面
- **工具执行可视化**：使用图标和友好格式显示 AI 工具调用
  - 📖 读取文件
  - ✍️ 写入文件
  - ✏️ 编辑文件
  - ⚙️ 执行命令
  - 🔍 搜索文件
  - 📝 任务管理
- **结果格式化**：优化工具执行结果的显示，避免信息过载
- **进度提示**：清晰显示任务执行进度（如 [1/5]）

### ⚡ 中断控制
- **随时中断**：在 AI 执行过程中按 `Ctrl+C` 可以立即中断
- **二次确认**：中断后可以选择继续或退出程序
- **安全退出**：退出时可选择保存当前会话

### 📊 其他功能
- **缓存优化**：智能缓存系统，减少 API 调用成本
- **精准切片读取**：read_file 必须提供 start_line/end_line，窗口默认最多 160 行，重复读取会跳过输出
- **操作回滚**：支持撤销上一次文件操作
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

#### 2. 配置 API Key（三种方式任选其一）

**方式 A：使用配置文件（推荐）**

首次运行时，程序会提示输入 API Key，并自动保存到 `config.json`：

```bash
python -m xiaochen_agent_v2
```

或手动创建 `config.json`：

```json
{
  "api_key": "your_api_key_here",
  "base_url": "https://api.deepseek.com",
  "model_name": "deepseek-chat",
  "verify_ssl": true,
  "auto_save_session": false,
  "max_cycles": 30
}
```

**方式 B：使用环境变量**

```bash
# Windows
set VOID_API_KEY=your_api_key_here
set VOID_BASE_URL=https://api.deepseek.com
set VOID_MODEL=deepseek-chat

# Linux/Mac
export VOID_API_KEY=your_api_key_here
export VOID_BASE_URL=https://api.deepseek.com
export VOID_MODEL=deepseek-chat
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
- **自动保存**：对话过程中自动保存到 `logs/sessions/*_autosave.json`，退出时也会自动保存
- **清空历史**：输入 `clear` 清空会话历史
- **回滚操作**：输入 `rollback` 撤销上一次文件操作
- **一键回退对话**：输入 `undo` 回退到上一次对话（含文件修改）
- **查看会话列表**：输入 `sessions` 查看最近 10 个历史会话
- **加载会话**：输入 `load <n>` 加载第 n 个历史会话（不退出）
- **新建会话**：输入 `new` 新建空会话并继续对话
- **模型预设**：输入 `models` 列出模型预设
- **查看模型**：输入 `model` 查看当前模型配置
- **切换模型**：输入 `model use <n>` 切换到第 n 个模型预设
- **自定义模型**：输入 `model set <base_url> <model_name> [ssl]` 自定义模型配置
- **设置密钥**：输入 `model key <api_key>` 更新 API Key
- **退出程序**：输入 `exit` 或 `quit`
- **帮助命令**：输入 `help` 或 `?` 显示命令帮助信息

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

### 中断控制

在 AI 执行任务时，可以随时按 `Ctrl+C` 中断：

```
[Cycle 2/30] Processing...
^C
⚠️  检测到中断信号 (Ctrl+C)
   再次按 Ctrl+C 退出程序
按回车继续，或 Ctrl+C 退出: 
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

## 📁 项目结构

```
xiaochen_agent_v2/
├── xiaochen_agent_v2/      # 主程序包
│   ├── __init__.py         # 包初始化
│   ├── __main__.py         # 程序入口
│   ├── agent.py            # AI 代理核心逻辑
│   ├── cli.py              # 命令行界面
│   ├── config.py           # 配置数据类
│   ├── console.py          # 控制台输出
│   ├── display.py          # 显示格式化（新增）
│   ├── files.py            # 文件操作
│   ├── interrupt.py        # 中断处理（新增）
│   ├── logs.py             # 日志记录
│   ├── metrics.py          # 性能指标
│   ├── session.py          # 会话管理（新增）
│   ├── tags.py             # 标签解析
│   └── terminal.py         # 终端管理
├── config_manager.py       # 配置文件管理（新增）
├── config.json.example     # 配置文件示例（新增）
├── agent.bat               # Windows 启动脚本（新增）
├── agent.sh                # Linux/Mac 启动脚本（新增）
├── install.bat             # Windows 安装脚本（新增）
├── install.sh              # Linux/Mac 安装脚本（新增）
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
- 完整的消息历史

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
