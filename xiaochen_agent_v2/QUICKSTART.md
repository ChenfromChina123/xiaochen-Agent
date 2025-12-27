# 快速开始指南

## 🚀 5分钟快速上手

### Windows 用户

#### 第一步：安装

1. 下载项目到本地
2. 双击运行 `install.bat`
3. 选择 "1. 仅当前用户"
4. 等待安装完成

```cmd
# 或使用命令行
cd xiaochen_agent_v2
install.bat
```

#### 第二步：配置 API Key

安装完成后，**重新打开命令行窗口**，输入：

```cmd
agent
```

首次运行会提示：

```
=== 小晨终端助手 (XIAOCHEN_TERMINAL) ===
1. DeepSeek (Default)
2. Doubao (Volcano Ark)

Select model (default 1): 1

Selected: DeepSeek (Default)
Enter API Key for deepseek-chat: [输入你的API Key]

是否保存 API Key 到配置文件? (y/n, 默认y): y
✓ 配置已保存到 config.json
  下次启动将自动使用此配置
```

#### 第三步：开始使用

配置完成后，以后只需输入 `agent` 即可启动：

```cmd
agent
```

---

### Linux/Mac 用户

#### 第一步：安装

```bash
cd xiaochen_agent_v2
chmod +x install.sh
./install.sh
```

选择安装方式（推荐选择 1）：

```
请选择安装方式:
  1. 添加到 PATH (推荐)
  2. 创建软链接到 /usr/local/bin
  3. 跳过环境变量配置

请输入选择 (1-3): 1
```

#### 第二步：使配置生效

```bash
# 如果使用 bash
source ~/.bashrc

# 如果使用 zsh
source ~/.zshrc
```

#### 第三步：配置 API Key

```bash
agent.sh
# 或如果配置了软链接
agent
```

按提示输入 API Key，选择保存到配置文件。

#### 第四步：开始使用

```bash
agent.sh
# 或
agent
```

---

## 💡 常见使用场景

### 场景1：代码开发助手

```
User: 帮我创建一个 Python 的快速排序函数

[AI 会自动创建文件并写入代码]
```

### 场景2：文件批量处理

```
User: 搜索所有 .py 文件中包含 "TODO" 的地方

[AI 会使用搜索工具找到所有匹配项]
```

### 场景3：项目自动化

```
User: 帮我运行测试，如果通过就提交代码

[AI 会执行测试命令，检查结果，然后提交]
```

### 场景4：保存重要对话

```
User: save
输入会话名称 (可选，按回车跳过): 项目重构讨论
✓ 会话已保存: 20251227_143530_项目重构讨论.json
```

### 场景5：复用历史会话

下次启动时：

```
是否加载历史会话? (y=是 / n=否，默认n): y

可用的历史会话:
1. [20251227_143530] 项目重构讨论 - 25 条消息
2. [20251227_120145] 代码优化 - 15 条消息

选择会话编号 (1-2, 或按回车跳过): 1
✓ 已加载会话
```

---

## ⚡ 快捷命令

在对话中可以使用以下命令：

| 命令 | 说明 |
|------|------|
| `save` | 保存当前会话 |
| `clear` | 清空会话历史 |
| `rollback` | 撤销上一次文件操作 |
| `exit` 或 `quit` | 退出程序 |
| `Ctrl+C` | 中断 AI 执行 |

---

## 🔧 配置文件位置

配置文件 `config.json` 位于项目根目录：

```
xiaochen_agent_v2/
└── config.json  ← 这里
```

可以手动编辑此文件来修改配置：

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

---

## ❓ 常见问题

### Q: 输入 `agent` 提示命令不存在？

**A:** 需要重新打开命令行窗口，或者手动运行：

```cmd
# Windows
cd xiaochen_agent_v2
agent.bat

# Linux/Mac
cd xiaochen_agent_v2
./agent.sh
```

### Q: 如何更换 API Key？

**A:** 三种方式：

1. 删除 `config.json`，重新运行程序
2. 直接编辑 `config.json` 文件
3. 设置环境变量 `VOID_API_KEY`

### Q: 会话文件保存在哪里？

**A:** 默认保存在 `logs/sessions/` 目录下

### Q: 如何卸载？

**A:** 

1. 删除项目文件夹
2. 从环境变量 PATH 中移除项目路径

Windows: 系统属性 -> 环境变量 -> 编辑 PATH
Linux/Mac: 编辑 `~/.bashrc` 或 `~/.zshrc`，删除相关行

### Q: 支持哪些 AI 模型？

**A:** 目前内置支持：

- DeepSeek (deepseek-chat)
- Doubao (doubao-seed-1-6-251015)

可以通过配置文件添加其他兼容 OpenAI API 的模型。

---

## 📚 更多帮助

- 完整文档：查看 [README.md](README.md)
- 问题反馈：提交 GitHub Issue
- 功能建议：提交 Pull Request

---

## 🎉 开始你的 AI 助手之旅！

现在你已经准备好了，输入 `agent` 开始使用吧！

```cmd
agent
```

祝你使用愉快！ 🚀

