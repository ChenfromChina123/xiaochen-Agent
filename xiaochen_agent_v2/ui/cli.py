import os
import sys
import threading
import time
from typing import List, Dict, Optional
import keyboard  # 用于监听热键，需要 pip install keyboard

from ..core.agent import VoidAgent
from ..core.config import Config
from ..core.metrics import CacheStats
from ..utils.console import Fore, Style
from ..core.session import SessionManager
from ..core.config_manager import ConfigManager
from ..utils.process_tracker import ProcessTracker


from ..utils.files import get_repo_root, prune_directory
from ..tools import save_clipboard_image, is_image_path, get_clipboard_text

def run_cli() -> None:
    """
    启动 Void Agent 的命令行交互界面。
    负责初始化配置、设置控制台环境以及处理用户循环输入。
    """
    # 确保 Windows 控制台编码为 UTF-8
    import sys
    if sys.platform == "win32":
        import io
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        os.system('chcp 65001 > nul')
    else:
        try:
            import readline
        except Exception:
            pass

    def _normalize_user_input(text: str) -> str:
        """
        清理方向键等控制序列，避免终端不支持行编辑时污染输入内容。
        """
        if not isinstance(text, str) or not text:
            return ""
        s = text
        if "\x1b" in s:
            import re

            s = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", s)
            s = re.sub(r"\x1b\][^\x07]*(\x07|\x1b\\)", "", s)
        s = s.replace("\x08", "")
        return s

    # 初始化配置管理器
    config_file = os.path.join(get_repo_root(), "config.json")
    configManager = ConfigManager(config_file=config_file)
    savedConfig = {}
    
    if configManager:
        savedConfig = configManager.load_config()
    
    # 模型预设
    PRESETS = {
        "1": {
            "name": "DeepSeek (Default)",
            "baseUrl": "https://api.deepseek.com",
            "modelName": "deepseek-chat",
            "verifySsl": True
        },
        "2": {
            "name": "Doubao (Volcano Ark)",
            "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
            "modelName": "doubao-seed-1-6-251015",
            "verifySsl": False  # 基于测试脚本设置为 False
        }
    }

    def display_history_messages(messages: List[Dict[str, str]]) -> None:
        """格式化并显示历史消息内容"""
        if not messages:
            return

        print(f"\n{Fore.CYAN}{'='*20} 历史消息记录 {'='*20}{Style.RESET_ALL}")
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # 处理分行显示的消息内容
            if isinstance(content, list):
                content = "\n".join([str(x) for x in content])
            
            if role == "system":
                # 系统消息通常很长，只显示前两行或简略显示
                lines = str(content).strip().splitlines()
                display_content = lines[0] + "..." if len(lines) > 1 else lines[0]
                print(f"{Fore.MAGENTA}[System]{Style.RESET_ALL} {display_content}")
            elif role == "user":
                # 尝试从复杂的输入格式中提取纯文本
                display_text = content
                if "## 📥 USER INPUT" in content:
                    try:
                        display_text = content.split("## 📥 USER INPUT")[-1].strip()
                    except:
                        pass
                print(f"\n{Fore.GREEN}[User]{Style.RESET_ALL} {display_text}")
            elif role == "assistant":
                if "tool_calls" in msg:
                    print(f"{Fore.YELLOW}[Assistant]{Style.RESET_ALL} (调用了工具)")
                else:
                    # 简略显示助手回答，避免刷屏
                    lines = str(content).strip().splitlines()
                    if len(lines) > 5:
                        display_content = "\n".join(lines[:5]) + f"\n{Fore.BLACK}{Style.BRIGHT}(... 剩余 {len(lines)-5} 行 ...){Style.RESET_ALL}"
                    else:
                        display_content = content
                    print(f"{Fore.CYAN}[Assistant]{Style.RESET_ALL} {display_content}")
            elif role == "tool":
                print(f"{Fore.BLACK}{Style.BRIGHT}[Tool Result]{Style.RESET_ALL} (工具执行结果)")
        
        print(f"{Fore.CYAN}{'='*54}{Style.RESET_ALL}\n")

    def _infer_last_prompt_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not messages:
            return []
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            m = messages[i]
            if isinstance(m, dict) and m.get("role") == "user":
                last_user_idx = i
                break
        if last_user_idx < 0:
            return list(messages)
        return list(messages[: last_user_idx + 1])

    def print_model_status() -> None:
        """
        打印当前正在使用的模型配置（以当前运行时配置为准）。
        """
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}当前模型配置{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"Base URL   : {agent.config.baseUrl}")
        print(f"Model Name : {agent.config.modelName}")
        print(f"Verify SSL : {agent.config.verifySsl}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    def print_model_presets() -> None:
        """
        打印内置模型预设列表。
        """
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}当前模型（运行时）{Style.RESET_ALL}")
        print(f"base_url: {agent.config.baseUrl}")
        print(f"model   : {agent.config.modelName}")
        print(f"ssl     : {agent.config.verifySsl}")
        print(f"{Fore.CYAN}{'-'*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}可用模型预设{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        for k, v in PRESETS.items():
            print(f"{k}. {v['name']}")
            print(f"   base_url: {v['baseUrl']}")
            print(f"   model   : {v['modelName']}")
            print(f"   ssl     : {v['verifySsl']}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    def apply_model_config(*, base_url: str, model_name: str, verify_ssl: bool, api_key: str = "") -> None:
        """
        应用模型配置到当前运行时，并写入 config.json（便于下次启动复用）。

        Args:
            base_url: API Base URL
            model_name: 模型名称
            verify_ssl: 是否校验 SSL
            api_key: 可选的 API Key（为空则不修改）
        """
        agent.updateModelConfig(
            apiKey=api_key if api_key.strip() else None,
            baseUrl=base_url,
            modelName=model_name,
            verifySsl=verify_ssl,
        )
        if configManager:
            if api_key.strip():
                configManager.update_config("api_key", api_key.strip())
            configManager.update_config("base_url", base_url)
            configManager.update_config("model_name", model_name)
            configManager.update_config("verify_ssl", verify_ssl)

    # 优先级: 环境变量 > 配置文件 > 用户输入
    apiKey = os.environ.get("VOID_API_KEY") or savedConfig.get("api_key", "")
    baseUrl = os.environ.get("VOID_BASE_URL") or savedConfig.get("base_url", "")
    modelName = os.environ.get("VOID_MODEL") or savedConfig.get("model_name", "")
    verifySsl = savedConfig.get("verify_ssl", True)
    whitelistedTools = savedConfig.get("whitelisted_tools")
    whitelistedCommands = savedConfig.get("whitelisted_commands")
    readIndentMode = savedConfig.get("read_indent_mode", "smart")
    pythonValidateRuff = savedConfig.get("python_validate_ruff", "auto")
    tokenThreshold = savedConfig.get("token_threshold", 30000)

    if not apiKey:
        print(f"{Fore.CYAN}=== 小晨终端助手 (XIAOCHEN_TERMINAL) ==={Style.RESET_ALL}")
        for k, v in PRESETS.items():
            print(f"{k}. {v['name']}")
        
        choice = input(f"\nSelect model (default 1): ").strip() or "1"
        preset = PRESETS.get(choice, PRESETS["1"])
        
        baseUrl = preset["baseUrl"]
        modelName = preset["modelName"]
        verifySsl = preset["verifySsl"]
        
        print(f"\nSelected: {preset['name']}")
        apiKey = input(f"Enter API Key for {modelName}: ").strip()
        if not apiKey:
            print(f"{Fore.RED}Error: API Key is required.{Style.RESET_ALL}")
            return
        
        if configManager:
            configManager.update_config("api_key", apiKey)
            configManager.update_config("base_url", baseUrl)
            configManager.update_config("model_name", modelName)
            configManager.update_config("verify_ssl", verifySsl)
            print(f"{Fore.GREEN}✓ 配置已自动保存到 config.json{Style.RESET_ALL}")
            print(f"{Fore.GREEN}  下次启动将自动使用此配置{Style.RESET_ALL}")

    config = Config(
        apiKey=apiKey,
        baseUrl=baseUrl or "https://api.deepseek.com",
        modelName=modelName or "deepseek-chat",
        verifySsl=verifySsl,
        tokenThreshold=int(tokenThreshold) if str(tokenThreshold).strip().isdigit() else 30000,
    )
    if isinstance(whitelistedTools, list):
        config.whitelistedTools = whitelistedTools
    if isinstance(whitelistedCommands, list):
        config.whitelistedCommands = whitelistedCommands
    agent = VoidAgent(config)
    agent.readIndentMode = str(readIndentMode or "smart")
    agent.pythonValidateRuff = str(pythonValidateRuff or "auto")
    sessionManager = SessionManager()
    autosaveFilename = None
    autosaveTitle = ""
    firstUserInput = ""
    titleLock = threading.Lock()
    
    # 询问是否加载历史会话
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}会话管理{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    load_choice = input(f"是否加载历史会话? (y=是 / n=否，默认n): ").strip().lower()
    
    if load_choice == "y":
        sessions = sessionManager.list_sessions(limit=10)
        if sessions:
            print(f"\n{Fore.CYAN}可用的历史会话:{Style.RESET_ALL}")
            for i, sess in enumerate(sessions, 1):
                size_kb = sess['file_size'] / 1024
                title = sess.get("title", "")
                print(f"{i}. [{sess['timestamp']}] {title}  {sess['message_count']} 条消息 ({size_kb:.1f} KB)")
            
            try:
                choice_idx = input(f"\n选择会话编号 (1-{len(sessions)}, 或按回车跳过): ").strip()
                if choice_idx and choice_idx.isdigit():
                    idx = int(choice_idx) - 1
                    if 0 <= idx < len(sessions):
                        selected_session = sessions[idx]
                        messages, stats = sessionManager.load_session(selected_session['filename'])
                        if messages:
                            # 加载会话历史（保持原样，不剔除 System Message，确保一致性）
                            agent.historyOfMessages = messages
                            if (
                                isinstance(messages, list)
                                and messages
                                and isinstance(messages[0], dict)
                                and messages[0].get("role") == "system"
                            ):
                                agent.cacheOfSystemMessage = messages[0]
                            # 恢复缓存统计
                            if stats:
                                agent.statsOfCache = CacheStats.from_dict(stats)
                            else:
                                agent.statsOfCache = CacheStats()

                            agent.lastFullMessages = _infer_last_prompt_messages(messages)
                            
                            # 延续当前会话文件
                            autosaveFilename = selected_session['filename']
                            autosaveTitle = selected_session.get("title", "")
                            # 尝试重置 firstUserInput，避免标题生成逻辑混淆
                            firstUserInput = "" 

                            print(f"{Fore.GREEN}✓ 已加载会话: {selected_session['filename']}{Style.RESET_ALL}")
                            print(f"{Fore.GREEN}  包含 {len(messages)} 条历史消息{Style.RESET_ALL}")
                            display_history_messages(messages)
                        else:
                            print(f"{Fore.RED}✗ 加载会话失败{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ 加载会话出错: {str(e)}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}没有找到历史会话{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}开始对话 (输入 'exit' 退出, 'save' 保存会话, 'clear' 清空历史){Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    last_ctrl_c_time = 0.0

    def _normalize_unique_list(values: list) -> list:
        items = []
        seen = set()
        for v in values:
            s = str(v or "").strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append(s)
        return items

    def _persist_whitelist() -> None:
        if not configManager:
            return
        configManager.update_config("whitelisted_tools", list(agent.config.whitelistedTools))
        configManager.update_config("whitelisted_commands", list(agent.config.whitelistedCommands))

    def print_whitelist() -> None:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}白名单（自动执行，无需确认）{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        tools = list(agent.config.whitelistedTools or [])
        cmds = list(agent.config.whitelistedCommands or [])
        tools.sort(key=lambda x: str(x).lower())
        cmds.sort(key=lambda x: str(x).lower())
        print("Tools:")
        for t in tools:
            print(f"  - {t}")
        print("Commands (base cmd):")
        for c in cmds:
            print(f"  - {c}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    def print_help_main() -> None:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}命令帮助{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print("sessions -help        会话管理（查看/加载/新建）")
        print("model -help           模型管理（查看/切换/配置）")
        print("whitelist -help       白名单管理（查看/修改）")
        print("paste                 进入粘贴模式，保存长文本到文件并通知 Agent")
        print("快捷键 [Ctrl+V]       实时识别并分析剪贴板图片（无需回车）")
        print("cancel / 撤回         撤回当前已粘贴但未发送的图片")
        print("rollback              回退最近一次文件修改")
        print("undo                  一键回退到上一次对话（含文件修改）")
        print("save                  保存当前会话")
        print("clear                 清空当前会话历史")
        print("exit / quit           退出（自动保存 autosave）")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    def print_help_sessions() -> None:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}sessions -help{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print("sessions              查看最近 10 个历史会话")
        print("sessions delete <n...|filename...> [-y]     删除会话（支持批量）")
        print("sessions delete --all [-y]                  删除所有会话")
        print("sessions prune [--max-files N] [--max-age-days D] [-y]  清理会话")
        print("load [n]              加载第 n 个历史会话（不退出）")
        print("new                   新建空会话并继续对话")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    def print_help_model() -> None:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}model -help{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print("models                          列出模型预设")
        print("model                           查看当前模型配置")
        print("model use [n]                   切换到第 n 个模型预设")
        print("model set <url> <name> [ssl]     自定义模型配置 (ssl=true/false)")
        print("model key <api_key>             设置/更新 API Key（写入 config.json）")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    def print_help_whitelist() -> None:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}whitelist -help{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print("whitelist                       查看白名单")
        print("whitelist tool add <name>        添加工具白名单")
        print("whitelist tool remove <name>     移除工具白名单")
        print("whitelist cmd add <basecmd>      添加命令白名单（仅匹配首段命令）")
        print("whitelist cmd remove <basecmd>   移除命令白名单")
        print("whitelist reset                 重置为默认白名单")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    def persist_history(messages: list) -> None:
        """
        将最新历史立即写入 autosave，会被 Agent 在每次模型输出后调用。
        """
        nonlocal autosaveFilename
        # 懒加载：只有在真正有内容要保存时才创建文件
        if not autosaveFilename:
            try:
                autosaveFilename = sessionManager.create_autosave_session()
            except Exception:
                return

        with titleLock:
            title = autosaveTitle
            first = firstUserInput
        sessionManager.update_session(autosaveFilename, messages, cache_stats=agent.statsOfCache.to_dict())
        if title or first:
            sessionManager.update_session_meta(autosaveFilename, title=title or None, first_user_input=first or None)

    def start_title_generation(user_input: str) -> None:
        """
        并行生成会话标题并写入 autosave 元数据。
        """
        nonlocal autosaveTitle
        try:
            title = agent.generateSessionTitle(user_input)
        except Exception:
            title = ""
        title = (title or "").strip()
        if not title:
            return
        with titleLock:
            if autosaveTitle:
                return
            autosaveTitle = title
        try:
            if autosaveFilename:
                sessionManager.update_session_meta(autosaveFilename, title=autosaveTitle)
        except Exception:
            pass

    pending_pastes = []  # 存储当前待处理的粘贴文件路径

    def handle_clipboard_shortcut():
        """监听 Ctrl+V 快捷键，实时处理图片"""
        nonlocal pending_pastes
        paste_dir = os.path.join(get_repo_root(), "xiaochen_agent_v2", "storage", "pastes")
        img_path = save_clipboard_image(save_dir=paste_dir)
        if img_path:
            pending_pastes.append(img_path)
            filename = os.path.basename(img_path)
            print(f"\n{Fore.GREEN}[已粘贴] {filename} (当前共 {len(pending_pastes)} 个文件){Style.RESET_ALL}")
            print(f"{Fore.CYAN}[提示] 继续粘贴图片，或直接按【回车】发送分析，输入 'cancel' 撤回。{Style.RESET_ALL}")
            # 自动清理旧文件
            prune_directory(paste_dir, 50)
        else:
            # 如果不是图片，不做任何处理，让系统原生的 Ctrl+V 处理文本粘贴
            pass

    # 注册全局热键监听 (仅在 Windows 下有效且需要管理员权限)
    try:
        keyboard.add_hotkey('ctrl+v', handle_clipboard_shortcut)
    except:
        pass

    while True:
        try:
            # 重置中断标志
            agent.interruptHandler.reset()
            
            # 在提示符中显示当前工作目录
            current_dir = os.getcwd()
            prompt = f"\n{Fore.BLUE}{current_dir}{Style.RESET_ALL}\n{Style.BRIGHT}User: "
            inputOfUser = _normalize_user_input(input(prompt))
            
            # 优化内容处理流程 (支持直接粘贴路径、剪贴板图片、剪贴板多行文本)
            
            # 1. 如果输入为空，尝试从剪贴板获取内容
            if not inputOfUser.strip():
                if pending_pastes:
                    # 如果有待处理的粘贴，则整合发送
                    paths_str = "\n".join([f"- {p}" for p in pending_pastes])
                    inputOfUser = f"请识别并分析以下图片/文档：\n{paths_str}"
                    print(f"{Fore.GREEN}[系统] 正在分析 {len(pending_pastes)} 张图片...{Style.RESET_ALL}")
                    pending_pastes = [] # 发送后清空
                else:
                    # 尝试获取图片 (优先图片，因为 PIL 抓取图片很准确)
                    paste_dir = os.path.join(get_repo_root(), "xiaochen_agent_v2", "storage", "pastes")
                    print(f"{Fore.YELLOW}[系统] 正在检查剪贴板内容...{Style.RESET_ALL}", end="\r")
                    img_path = save_clipboard_image(save_dir=paste_dir)
                    if img_path:
                        inputOfUser = f"请识别并分析这张图片/文档: {img_path}"
                        print(f"{Fore.GREEN}[系统] 已从剪贴板保存并加载图片: {img_path}{Style.RESET_ALL}")
                        # 自动清理旧文件
                        prune_directory(paste_dir, 50)
                    else:
                        # 尝试获取文本 (支持多行)
                        cb_text = get_clipboard_text()
                        if cb_text:
                            inputOfUser = cb_text
                            # 显示文本预览
                            lines = cb_text.splitlines()
                            if len(lines) > 1:
                                print(f"{Fore.GREEN}[系统] 已从剪贴板获取多行文本 ({len(lines)} 行){Style.RESET_ALL}")
                            else:
                                preview = cb_text[:50] + "..." if len(cb_text) > 50 else cb_text
                                print(f"{Fore.GREEN}[系统] 已从剪贴板获取文本: {preview}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}[系统] 剪贴板中未发现可识别的图片或文本内容。{Style.RESET_ALL}")
                            # 既没有图片也没有文本，继续循环
                            continue
            
            # 2. 如果输入不为空，检查是否为文件路径
            elif is_image_path(inputOfUser):
                img_path = inputOfUser.strip().strip('"').strip("'")
                inputOfUser = f"请识别并分析这张图片/文档: {img_path}"
                print(f"{Fore.GREEN}[系统] 已检测到粘贴的文件路径: {img_path}{Style.RESET_ALL}")
            
            # 3. 如果是普通文本但包含图片关键词，再次检查剪贴板图片 (兼容旧逻辑)
            else:
                image_keywords = ["图片", "图", "识别", "ocr", "看下", "分析", "image", "pic", "这张"]
                if any(k in inputOfUser.lower() for k in image_keywords) and len(inputOfUser) < 20:
                    paste_dir = os.path.join(get_repo_root(), "xiaochen_agent_v2", "storage", "pastes")
                    img_path = save_clipboard_image(save_dir=paste_dir)
                    if img_path:
                        inputOfUser += f" (图片已自动保存: {img_path})"
                        print(f"{Fore.GREEN}[系统] 已检测并保存剪贴板图片: {img_path}{Style.RESET_ALL}")
                        # 自动清理旧文件
                        prune_directory(paste_dir, 50)

            raw_cmd = inputOfUser.strip()
            if not raw_cmd:
                continue
            
            # 处理特殊命令
            parts = raw_cmd.split()
            cmd = parts[0].lower()
            args = parts[1:]
            
            if raw_cmd.lower() in ["help", "?"]:
                print_help_main()
                continue

            if raw_cmd.lower() in ["cancel", "撤回"]:
                if pending_pastes:
                    count = len(pending_pastes)
                    pending_pastes = []
                    print(f"{Fore.YELLOW}✓ 已撤回当前待处理的 {count} 张图片。{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}当前没有待处理的粘贴内容。{Style.RESET_ALL}")
                continue

            if cmd == "paste":
                print(f"\n{Fore.CYAN}--- 进入粘贴模式 ---{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}请粘贴您的内容。输入完成后，请在一行中输入 ':wq' 或按 Ctrl+Z (Win) 然后回车结束并保存。{Style.RESET_ALL}")
                
                paste_lines = []
                while True:
                    try:
                        line = input()
                        if line.strip() == ":wq":
                            break
                        paste_lines.append(line)
                    except EOFError:
                        break
                
                content = "\n".join(paste_lines)
                if not content.strip():
                    print(f"{Fore.RED}✗ 内容为空，已取消保存。{Style.RESET_ALL}")
                    continue
                
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                paste_dir = os.path.join(get_repo_root(), "xiaochen_agent_v2", "storage", "pastes")
                os.makedirs(paste_dir, exist_ok=True)
                
                file_path = os.path.abspath(os.path.join(paste_dir, f"paste_{timestamp}.txt"))
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                print(f"{Fore.GREEN}✓ 内容已保存至: {file_path}{Style.RESET_ALL}")
                
                # 自动清理旧文件
                prune_directory(paste_dir, 50)
                
                # 自动构造发送给 Agent 的消息
                inputOfUser = f"我刚才粘贴了一段内容并保存到了文件：{file_path}\n请阅读并处理该文件中的内容。"
                print(f"{Fore.CYAN}[系统] 已自动构造消息发送给 Agent。{Style.RESET_ALL}")
                # 注意：这里不需要 continue，因为我们希望这个 inputOfUser 被发送给 agent.chat()

            if cmd == "rollback" and not args:
                agent.rollbackLastOperation()
                try:
                    if autosaveFilename:
                        sessionManager.update_session(autosaveFilename, agent.getFullHistory(), cache_stats=agent.statsOfCache.to_dict())
                except Exception:
                    pass
                continue

            if cmd == "undo" and not args:
                agent.rollbackLastChat()
                try:
                    if autosaveFilename:
                        sessionManager.update_session(autosaveFilename, agent.getFullHistory(), cache_stats=agent.statsOfCache.to_dict())
                except Exception:
                    pass
                continue
            
            if cmd in ["sessions"]:
                if args and args[0].lower() in {"-help", "help", "?"}:
                    print_help_sessions()
                    continue
                if args and args[0].lower() in {"delete", "del", "rm"}:
                    # 处理 --all, -all 或 all
                    is_all = any(a.lower() in {"--all", "-all", "all"} for a in args[1:])
                    yes = any(a.lower() in {"-y", "--yes"} for a in args[1:])

                    if is_all:
                        all_sessions = sessionManager.list_sessions(limit=1000)
                        if not all_sessions:
                            print(f"{Fore.YELLOW}没有找到任何会话{Style.RESET_ALL}")
                            continue
                        
                        if not yes:
                            print(f"{Fore.RED}{Style.BRIGHT}警告: 即将删除所有会话 ({len(all_sessions)} 个)！{Style.RESET_ALL}")
                            confirm = input("确认清空所有会话? (y/N): ").strip().lower()
                            if confirm != "y":
                                print(f"{Fore.YELLOW}已取消操作{Style.RESET_ALL}")
                                continue
                        
                        filenames = [s["filename"] for s in all_sessions]
                        result = sessionManager.delete_sessions(filenames)
                        print(f"{Fore.GREEN}✓ 已清空所有会话{Style.RESET_ALL} (deleted={result.get('deleted', 0)})")
                        
                        # 重置当前会话状态
                        autosaveFilename = None
                        autosaveTitle = ""
                        firstUserInput = ""
                        continue

                    sessions = sessionManager.list_sessions(limit=10)
                    if not sessions:
                        print(f"{Fore.YELLOW}没有找到历史会话{Style.RESET_ALL}")
                        continue

                    yes = any(a.lower() in {"-y", "--yes"} for a in args[1:])
                    raw_targets = [a for a in args[1:] if a.lower() not in {"-y", "--yes"}]
                    if not raw_targets:
                        entered = input("输入要删除的会话编号或文件名（支持多个，以空格/逗号分隔）: ").strip()
                        raw_targets = [t for t in entered.replace(",", " ").split() if t]

                    targets: List[str] = []
                    bad: List[str] = []
                    for tok in raw_targets:
                        t = str(tok).strip()
                        if not t:
                            continue
                        if t.isdigit():
                            idx = int(t) - 1
                            if 0 <= idx < len(sessions):
                                targets.append(sessions[idx]["filename"])
                            else:
                                bad.append(t)
                        else:
                            targets.append(t)

                    deduped: List[str] = []
                    seen = set()
                    for fn in targets:
                        key = str(fn).lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        deduped.append(fn)

                    if bad:
                        print(f"{Fore.RED}✗ 会话编号超出范围: {', '.join(bad)}{Style.RESET_ALL}")
                        continue
                    if not deduped:
                        print(f"{Fore.RED}✗ 未提供要删除的会话{Style.RESET_ALL}")
                        continue

                    if not yes:
                        print(f"\n{Fore.YELLOW}即将删除 {len(deduped)} 个会话:{Style.RESET_ALL}")
                        for fn in deduped:
                            print(f"  - {fn}")
                        confirm = input("确认删除? (y/N): ").strip().lower()
                        if confirm != "y":
                            print(f"{Fore.YELLOW}已取消删除{Style.RESET_ALL}")
                            continue

                    result = sessionManager.delete_sessions(deduped)
                    print(
                        f"{Fore.GREEN}✓ 删除完成{Style.RESET_ALL} "
                        f"(deleted={result.get('deleted', 0)}, missing={result.get('missing', 0)}, errors={result.get('errors', 0)})"
                    )

                    if autosaveFilename:
                        try:
                            fp = os.path.join(sessionManager.sessions_dir, autosaveFilename)
                            if not os.path.exists(fp):
                                autosaveFilename = None
                                autosaveTitle = ""
                                firstUserInput = ""
                        except Exception:
                            pass

                    continue

                if args and args[0].lower() in {"prune", "clean"}:
                    yes = any(a.lower() in {"-y", "--yes"} for a in args[1:])
                    max_files = None
                    max_age_days = None
                    sub_args = args[1:]

                    parse_error = False
                    i = 0
                    while i < len(sub_args):
                        t = str(sub_args[i]).strip()
                        low = t.lower()
                        if low in {"-y", "--yes"}:
                            i += 1
                            continue
                        if low in {"--max-files", "--max_file", "--keep"}:
                            if i + 1 >= len(sub_args):
                                parse_error = True
                                break
                            v = str(sub_args[i + 1]).strip()
                            if not v.isdigit():
                                parse_error = True
                                break
                            max_files = int(v)
                            i += 2
                            continue
                        if low in {"--max-age-days", "--max_age_days", "--age-days"}:
                            if i + 1 >= len(sub_args):
                                parse_error = True
                                break
                            v = str(sub_args[i + 1]).strip()
                            if not v.isdigit():
                                parse_error = True
                                break
                            max_age_days = int(v)
                            i += 2
                            continue
                        if low.isdigit() and max_files is None:
                            max_files = int(low)
                            i += 1
                            continue
                        parse_error = True
                        break

                    if parse_error:
                        print(f"{Fore.RED}✗ 用法: sessions prune [--max-files N] [--max-age-days D] [-y]{Style.RESET_ALL}")
                        continue

                    eff_max_files = sessionManager.max_files if max_files is None else int(max_files)
                    eff_max_age_days = sessionManager.max_age_days if max_age_days is None else int(max_age_days)
                    if not yes:
                        print(f"{Fore.YELLOW}将清理会话: max_files={eff_max_files}, max_age_days={eff_max_age_days}{Style.RESET_ALL}")
                        confirm = input("确认清理? (y/N): ").strip().lower()
                        if confirm != "y":
                            print(f"{Fore.YELLOW}已取消清理{Style.RESET_ALL}")
                            continue

                    result = sessionManager.prune_sessions(max_files=max_files, max_age_days=max_age_days)
                    print(
                        f"{Fore.GREEN}✓ 清理完成{Style.RESET_ALL} "
                        f"(deleted={result.get('deleted', 0)}, kept={result.get('kept', 0)}, errors={result.get('errors', 0)})"
                    )

                    if autosaveFilename:
                        try:
                            fp = os.path.join(sessionManager.sessions_dir, autosaveFilename)
                            if not os.path.exists(fp):
                                autosaveFilename = None
                                autosaveTitle = ""
                                firstUserInput = ""
                        except Exception:
                            pass

                    continue

                sessions = sessionManager.list_sessions(limit=10)
                if not sessions:
                    print(f"{Fore.YELLOW}没有找到历史会话{Style.RESET_ALL}")
                    continue
                print(f"\n{Fore.CYAN}可用的历史会话:{Style.RESET_ALL}")
                for i, sess in enumerate(sessions, 1):
                    size_kb = sess['file_size'] / 1024
                    title = sess.get("title", "")
                    print(f"{i}. [{sess['timestamp']}] {title}  {sess['message_count']} 条消息 ({size_kb:.1f} KB)  {sess['filename']}")
                continue

            if cmd in ["load"]:
                sessions = sessionManager.list_sessions(limit=10)
                if not sessions:
                    print(f"{Fore.YELLOW}没有找到历史会话{Style.RESET_ALL}")
                    continue
                idx_str = args[0] if args else input(f"\n选择会话编号 (1-{len(sessions)}): ").strip()
                if not idx_str.isdigit():
                    print(f"{Fore.RED}✗ 会话编号无效{Style.RESET_ALL}")
                    continue
                idx = int(idx_str) - 1
                if idx < 0 or idx >= len(sessions):
                    print(f"{Fore.RED}✗ 会话编号超出范围{Style.RESET_ALL}")
                    continue
                selected_session = sessions[idx]
                messages, stats = sessionManager.load_session(selected_session["filename"])
                if not messages:
                    print(f"{Fore.RED}✗ 加载会话失败{Style.RESET_ALL}")
                    continue
                
                # 保持原样加载，不剔除 System Message
                agent.historyOfMessages = messages
                if (
                    isinstance(messages, list)
                    and messages
                    and isinstance(messages[0], dict)
                    and messages[0].get("role") == "system"
                ):
                    agent.cacheOfSystemMessage = messages[0]
                # 恢复缓存统计
                if stats:
                    agent.statsOfCache = CacheStats.from_dict(stats)
                else:
                    agent.statsOfCache = CacheStats()
                
                agent.historyOfOperations = []
                agent.lastFullMessages = _infer_last_prompt_messages(messages)
                if hasattr(agent, "_chatMarkers"):
                    agent._chatMarkers = []
                
                # 切换到加载的会话文件
                autosaveFilename = selected_session['filename']
                autosaveTitle = selected_session.get("title", "")
                firstUserInput = ""
                
                # 检查并显示活跃的 AI 进程
                ProcessTracker().print_active_processes()
                
                print(f"{Fore.GREEN}✓ 已加载会话: {selected_session['filename']}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}  包含 {len(messages)} 条历史消息{Style.RESET_ALL}")
                display_history_messages(messages)
                continue

            if cmd in ["new"] and not args:
                agent.historyOfMessages = []
                agent.historyOfOperations = []
                agent.lastFullMessages = []
                if hasattr(agent, "_chatMarkers"):
                    agent._chatMarkers = []
                agent.invalidateSystemMessageCache()
                
                # 重置会话文件（懒加载，下次保存时创建新文件）
                autosaveFilename = None
                autosaveTitle = ""
                firstUserInput = ""
                agent.statsOfCache = CacheStats() # 重置统计
                
                print(f"{Fore.GREEN}✓ 已新建会话{Style.RESET_ALL}")
                continue

            if cmd == "models" and not args:
                print_model_presets()
                continue

            if cmd == "model":
                if args and args[0].lower() in {"-help", "help", "?"}:
                    print_help_model()
                    continue
                if not args:
                    print_model_status()
                    continue

                sub = args[0].lower()
                sub_args = args[1:]

                if sub == "use":
                    choice = sub_args[0] if sub_args else input("选择模型预设编号: ").strip()
                    preset = PRESETS.get(choice)
                    if not preset:
                        print(f"{Fore.RED}✗ 预设编号无效: {choice}{Style.RESET_ALL}")
                        continue
                    apply_model_config(
                        base_url=preset["baseUrl"],
                        model_name=preset["modelName"],
                        verify_ssl=bool(preset["verifySsl"]),
                    )
                    print(f"{Fore.GREEN}✓ 已切换模型: {preset['name']}{Style.RESET_ALL}")
                    print_model_status()
                    continue

                if sub == "set":
                    if len(sub_args) < 2:
                        print(f"{Fore.RED}✗ 用法: model set <base_url> <model_name> [ssl]{Style.RESET_ALL}")
                        continue
                    base_url = sub_args[0].strip()
                    model_name = sub_args[1].strip()
                    ssl_str = (sub_args[2].strip().lower() if len(sub_args) >= 3 else "true")
                    verify_ssl = ssl_str in {"1", "true", "yes", "y", "on"}
                    apply_model_config(base_url=base_url, model_name=model_name, verify_ssl=verify_ssl)
                    print(f"{Fore.GREEN}✓ 已更新模型配置{Style.RESET_ALL}")
                    print_model_status()
                    continue

                if sub == "key":
                    api_key = sub_args[0] if sub_args else input("请输入 API Key: ").strip()
                    if not api_key.strip():
                        print(f"{Fore.RED}✗ API Key 不能为空{Style.RESET_ALL}")
                        continue
                    apply_model_config(
                        base_url=agent.config.baseUrl,
                        model_name=agent.config.modelName,
                        verify_ssl=agent.config.verifySsl,
                        api_key=api_key.strip(),
                    )
                    print(f"{Fore.GREEN}✓ API Key 已更新并写入 config.json{Style.RESET_ALL}")
                    continue

                print(f"{Fore.RED}✗ 未知子命令: {sub}{Style.RESET_ALL}")
                continue

            if cmd == "whitelist":
                if args and args[0].lower() in {"-help", "help", "?"}:
                    print_help_whitelist()
                    continue
                if not args or args[0].lower() in {"list", "show"}:
                    print_whitelist()
                    continue

                sub = args[0].lower()
                sub_args = args[1:]
                if sub == "reset":
                    defaults = Config(
                        apiKey=agent.config.apiKey,
                        baseUrl=agent.config.baseUrl,
                        modelName=agent.config.modelName,
                        verifySsl=agent.config.verifySsl,
                    )
                    agent.config.whitelistedTools = list(defaults.whitelistedTools)
                    agent.config.whitelistedCommands = list(defaults.whitelistedCommands)
                    _persist_whitelist()
                    print(f"{Fore.GREEN}✓ 白名单已重置为默认值{Style.RESET_ALL}")
                    print_whitelist()
                    continue

                if len(sub_args) < 2:
                    print_help_whitelist()
                    continue

                kind = sub
                op = sub_args[0].lower()
                name = sub_args[1].strip() if len(sub_args) >= 2 else ""
                if not name:
                    print_help_whitelist()
                    continue

                if kind == "tool":
                    tools = list(agent.config.whitelistedTools or [])
                    if op == "add":
                        tools.append(name)
                        agent.config.whitelistedTools = _normalize_unique_list(tools)
                        _persist_whitelist()
                        print(f"{Fore.GREEN}✓ 已添加工具白名单: {name}{Style.RESET_ALL}")
                        continue
                    if op == "remove":
                        agent.config.whitelistedTools = [t for t in tools if str(t).lower() != name.lower()]
                        _persist_whitelist()
                        print(f"{Fore.GREEN}✓ 已移除工具白名单: {name}{Style.RESET_ALL}")
                        continue

                if kind in {"cmd", "command"}:
                    cmds = list(agent.config.whitelistedCommands or [])
                    base = name.split()[0].strip().lower()
                    if not base:
                        print_help_whitelist()
                        continue
                    if op == "add":
                        cmds.append(base)
                        agent.config.whitelistedCommands = _normalize_unique_list(cmds)
                        _persist_whitelist()
                        print(f"{Fore.GREEN}✓ 已添加命令白名单: {base}{Style.RESET_ALL}")
                        continue
                    if op == "remove":
                        agent.config.whitelistedCommands = [c for c in cmds if str(c).lower() != base]
                        _persist_whitelist()
                        print(f"{Fore.GREEN}✓ 已移除命令白名单: {base}{Style.RESET_ALL}")
                        continue

                print_help_whitelist()
                continue

            if cmd in ["exit", "quit"] and not args:
                if agent.historyOfMessages:
                    try:
                        if autosaveFilename:
                            sessionManager.update_session(autosaveFilename, agent.getFullHistory(), cache_stats=agent.statsOfCache.to_dict())
                            print(f"{Fore.GREEN}✓ 会话已自动保存: {autosaveFilename}{Style.RESET_ALL}")
                    except Exception:
                        pass
                break
            
            if cmd == "save" and not args:
                if agent.historyOfMessages:
                    session_name = input(f"{Fore.CYAN}输入会话名称 (可选，按回车跳过): {Style.RESET_ALL}").strip()
                    filename = sessionManager.save_session(agent.getFullHistory(), session_name or None, cache_stats=agent.statsOfCache.to_dict())
                    if filename:
                        print(f"{Fore.GREEN}✓ 会话已保存: {filename}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}当前没有会话历史{Style.RESET_ALL}")
                continue
            
            if cmd == "clear" and not args:
                confirm = input(f"{Fore.YELLOW}确认清空会话历史? (y/n): {Style.RESET_ALL}").strip().lower()
                if confirm == "y":
                    agent.historyOfMessages = []
                    agent.invalidateSystemMessageCache()
                    # 清空后视为新会话（懒加载）
                    autosaveFilename = None
                    autosaveTitle = ""
                    firstUserInput = ""
                    agent.statsOfCache = CacheStats() # 重置统计
                    print(f"{Fore.GREEN}✓ 会话历史已清空{Style.RESET_ALL}")
                continue
            
            # 正常对话
            if not firstUserInput:
                firstUserInput = inputOfUser.strip()
                try:
                    if autosaveFilename:
                        sessionManager.update_session_meta(autosaveFilename, first_user_input=firstUserInput)
                except Exception:
                    pass
                t = threading.Thread(target=start_title_generation, args=(firstUserInput,), daemon=True)
                t.start()

            agent.chat(inputOfUser, on_history_updated=persist_history)
            
        except KeyboardInterrupt:
            agent.interruptHandler.set_interrupted()
            now = time.time()
            if now - last_ctrl_c_time < 1.5:
                try:
                    if autosaveFilename:
                        sessionManager.update_session(autosaveFilename, agent.getFullHistory(), cache_stats=agent.statsOfCache.to_dict())
                        print(f"\n{Fore.GREEN}✓ 会话已自动保存: {autosaveFilename}{Style.RESET_ALL}")
                except Exception:
                    pass
                print(f"{Fore.BLUE}小晨终端助手 正在退出...{Style.RESET_ALL}")
                break
            last_ctrl_c_time = now
            try:
                if autosaveFilename:
                    sessionManager.update_session(autosaveFilename, agent.getFullHistory(), cache_stats=agent.statsOfCache.to_dict())
                    print(f"\n{Fore.GREEN}✓ 会话已自动保存: {autosaveFilename}{Style.RESET_ALL}")
            except Exception:
                pass
            print(f"\n{Fore.YELLOW}⚠️  已请求中断 (Ctrl+C)。为避免误触，不会立即退出。{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   若要强制退出，请在 1.5 秒内再按一次 Ctrl+C{Style.RESET_ALL}")
            try:
                continue
            except Exception:
                continue
