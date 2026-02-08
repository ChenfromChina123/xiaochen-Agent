import os
import sys
import subprocess
import threading
import time
from typing import List, Dict, Optional, Any
import keyboard  # 用于监听热键，需要 pip install keyboard

from ..core.agent import VoidAgent
from ..core.config import Config
from ..core.metrics import CacheStats
from ..utils.console import Fore, Style
from ..core.session import SessionManager
from ..core.config_manager import ConfigManager
from ..utils.process_tracker import ProcessTracker


from ..utils.files import get_repo_root, prune_directory, get_data_root
from ..tools import save_clipboard_image, save_clipboard_file, is_image_path, get_clipboard_text

def _normalize_user_input(text: str) -> str:
    """
    清理方向键等控制序列，避免终端不支持行编辑时污染输入内容。
    """
    if not isinstance(text, str) or not text:
        return ""
    s = text
    try:
        import unicodedata

        s = unicodedata.normalize("NFKC", s)
        s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    except Exception:
        pass

    s = (
        s.replace("\ufeff", "")
        .replace("\u200b", "")
        .replace("\u2060", "")
        .replace("\u00a0", " ")
        .replace("\u3000", " ")
    )
    if "\x1b" in s:
        import re

        s = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", s)
        s = re.sub(r"\x1b\][^\x07]*(\x07|\x1b\\)", "", s)
    s = s.replace("\x08", "")
    return s

def _normalize_command_token(token: str) -> str:
    """
    规范化命令 token，避免因不可见字符导致命令无法匹配。
    """
    return _normalize_user_input(token).strip()

def _get_sorted_terminals(manager) -> List[tuple]:
    """
    获取按启动时间排序的终端列表（用于生成简单 ID）。
    返回: List[(tid, terminal_obj)]
    """
    if not manager or not manager.terminals:
        return []
    
    # 将终端字典转换为列表并按启动时间排序
    # 假设 start_time 存在，如果不存在则使用 key (uuid) 排序保证确定性
    items = []
    for tid, term in manager.terminals.items():
        start_time = getattr(term, 'start_time', 0)
        items.append((tid, term, start_time))
    
    # 按启动时间升序排序（旧的在前，新的在后）
    items.sort(key=lambda x: x[2])
    return [(x[0], x[1]) for x in items]

def _resolve_terminal_id(manager, arg_id: str) -> Optional[str]:
    """
    解析终端 ID 参数，支持:
    1. 简单 ID (1, 2, 3...) -> 对应排序后的索引
    2. UUID 前缀或全名
    3. PID
    """
    if not arg_id:
        return None
        
    sorted_terms = _get_sorted_terminals(manager)
    
    # 1. 尝试作为简单 ID (索引)
    if arg_id.isdigit():
        idx = int(arg_id)
        # 如果是简单 ID (1-based index)
        if 1 <= idx <= len(sorted_terms):
            return sorted_terms[idx-1][0]
        # 同时也可能是 PID，继续往下查
    
    # 2. 尝试作为 UUID 匹配
    if arg_id in manager.terminals:
        return arg_id
        
    # 3. 尝试作为 PID 匹配
    for tid, term in manager.terminals.items():
        try:
            if str(term.process.pid) == arg_id:
                return tid
        except:
            pass
            
    # 4. 尝试 UUID 前缀匹配
    for tid in manager.terminals:
        if tid.startswith(arg_id):
            return tid
            
    return None

def run_setup_wizard(configManager: ConfigManager) -> Dict[str, Any]:
    """
    设置向导。
    引导用户配置数据存储路径和 API Key。
    """
    print(f"\n{Fore.CYAN}{'='*20} 设置向导 {'='*20}{Style.RESET_ALL}")
    print("您可以随时通过输入 'setup' 命令回到此向导。")
    
    # 获取当前配置作为默认值
    current_config = configManager.load_config()
    
    # 1. 询问存储根目录
    # 尝试从当前配置推导存储根目录（通常是 logs_dir 的父目录）
    current_logs_dir = current_config.get("logs_dir", "")
    if current_logs_dir and os.path.isdir(os.path.dirname(current_logs_dir)):
        default_storage_root = os.path.dirname(os.path.abspath(current_logs_dir))
    else:
        default_storage_root = os.getcwd()

    print(f"\n[1/2] 数据存储路径设置")
    print(f"所有日志、会话历史和粘贴文件将存放在此目录下。")
    print(f"当前/默认路径: {Fore.GREEN}{default_storage_root}{Style.RESET_ALL}")
    
    storage_root = input(f"请输入存储根目录路径 (直接回车保持不变): ").strip()
    if not storage_root:
        storage_root = default_storage_root
    
    # 确保路径是绝对路径
    storage_root = os.path.abspath(os.path.expanduser(storage_root))
    
    # 更新配置中的路径
    logs_dir = os.path.join(storage_root, "logs")
    storage_dir = os.path.join(storage_root, "storage")
    
    configManager.update_config("logs_dir", logs_dir)
    configManager.update_config("storage_dir", storage_dir)
    
    print(f"已设置日志目录: {Fore.YELLOW}{logs_dir}{Style.RESET_ALL}")
    print(f"已设置存储目录: {Fore.YELLOW}{storage_dir}{Style.RESET_ALL}")
    
    # 创建目录
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    
    # 2. 询问 API Key
    print(f"\n[2/2] API Key 设置")
    current_api_key = current_config.get("api_key", "")
    if current_api_key:
        # 只显示前后几位，中间脱敏
        masked_key = f"{current_api_key[:8]}...{current_api_key[-4:]}" if len(current_api_key) > 12 else "****"
        print(f"当前 API Key: {Fore.GREEN}{masked_key}{Style.RESET_ALL}")
    
    print("请输入您的 DeepSeek 或其他兼容模型的 API Key。")
    api_key = input("API Key (直接回车保持不变): ").strip()
    if api_key:
        configManager.update_config("api_key", api_key)
        print(f"{Fore.GREEN}API Key 已更新。{Style.RESET_ALL}")
    else:
        if not current_api_key:
            print(f"{Fore.YELLOW}未设置 API Key，您稍后可以在 config.json 中手动配置。{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}保持当前 API Key 不变。{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}设置完成！配置已更新至: {configManager.config_file}{Style.RESET_ALL}")
    print(f"{'='*50}\n")
    
    return configManager.load_config()

def run_cli() -> None:
    """
    启动 Void Agent 的命令行交互界面。
    负责初始化配置、设置控制台环境以及处理用户循环输入。
    """
    # 确保 Windows 控制台编码为 UTF-8
    import sys
    if sys.platform == "win32":
        import io
        # 仅当编码不是 utf-8 时才重新包装，避免双重缓冲问题
        if sys.stdin.encoding.lower() != 'utf-8':
            try:
                sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
            except Exception:
                pass
        if sys.stdout.encoding.lower() != 'utf-8':
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            except Exception:
                pass
        os.system('chcp 65001 > nul')
    else:
        try:
            import readline
        except Exception:
            pass

    # 解析命令行参数，支持指定工作目录
    if len(sys.argv) > 1:
        # 如果第一个参数是目录，则切换到该目录
        potential_dir = sys.argv[1]
        if os.path.isdir(potential_dir):
            try:
                os.chdir(os.path.abspath(potential_dir))
            except Exception:
                pass

    start_cwd = os.environ.get("XIAOCHEN_START_CWD") or os.environ.get("XIAOCHEN_WORKDIR")
    if start_cwd:
        target_dir = os.path.expandvars(str(start_cwd))
        if os.path.isdir(target_dir):
            try:
                os.chdir(target_dir)
            except Exception:
                pass



    # 初始化配置管理器
    data_root = get_data_root()
    os.makedirs(data_root, exist_ok=True)
    
    config_file = os.path.join(data_root, "config.json")
    
    # 向后兼容：如果全局配置不存在，但源码目录下存在，则迁移或使用源码目录的
    repo_config = os.path.join(get_repo_root(), "config.json")
    if not os.path.exists(config_file) and os.path.exists(repo_config):
        import shutil
        try:
            shutil.copy2(repo_config, config_file)
            print(f"{Fore.GREEN}[系统] 已自动将配置文件从 {repo_config} 迁移至 {config_file}{Style.RESET_ALL}")
        except Exception:
            config_file = repo_config
    
    configManager = ConfigManager(config_file=config_file)
    
    # 检查是否是首次运行或缺少关键配置
    if configManager.is_first_run():
        savedConfig = run_setup_wizard(configManager)
    else:
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
        print("terminal <id>         查看指定终端的完整输出")
        print("terminal list         列出最近的终端输出记录")
        print("terminal stats        查看终端输出存储统计")
        print("ps                    查看正在运行的进程")
        print("watch <id>            监控进程输出（支持暂停/清屏/终止等）")
        print("monitor <id>          在新窗口中监控进程输出")
        print("kill <id>             终止指定进程（优雅终止）")
        print("kill <id> -f          强制终止指定进程")
        print("kill all              终止所有进程")
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
    just_pasted = False  # 标记是否刚刚发生了粘贴操作，用于刷新输入行
    last_paste_time = 0  # 记录上一次粘贴的时间，用于防抖

    def is_terminal_active() -> bool:
        """
        检查当前终端窗口是否处于激活状态，避免全局捕捉 Ctrl+V。
        仅在 Windows 下通过窗口标题简单判断。
        """
        if sys.platform != "win32":
            return True # 非 Windows 暂不限制
            
        try:
            import ctypes
            from ctypes import wintypes
            
            # 获取当前激活窗口的句柄
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return False
                
            # 获取窗口标题
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.lower()
            
            # 常见的终端关键词
            terminal_keywords = [
                "cmd.exe", "powershell", "windows terminal", "conhost", 
                "agent.bat", "xiaochen", "terminal", "trae", "code", "visual studio"
            ]
            is_active = any(k in title for k in terminal_keywords)
            # print(f"[DEBUG] Window Title: {title}, Is Active: {is_active}") # 调试用
            return is_active
        except:
            return True # 出错则默认允许，保证可用性

    def handle_clipboard_shortcut():
        """监听 Ctrl+V 快捷键，实时处理图片/文档"""
        nonlocal pending_pastes, just_pasted, last_paste_time
        
        # 防抖处理：500ms 内只允许一次粘贴
        current_time = time.time()
        if current_time - last_paste_time < 0.5:
            return
        last_paste_time = current_time
        
        # 核心修改：仅在终端窗口激活时处理
        try:
            if not is_terminal_active():
                return
        except:
            pass # 确保报错不影响流程
            
        paste_dir = os.path.join(savedConfig.get("storage_dir", os.path.join(get_repo_root(), "storage")), "pastes")
        try:
            img_path = save_clipboard_file(save_dir=paste_dir)
            if img_path:
                pending_pastes.append(img_path)
                just_pasted = True
                # 自动清理旧文件
                prune_directory(paste_dir, 50)
                # 模拟按下回车，强制结束当前的 input() 阻塞，以便主循环刷新显示
                keyboard.press_and_release('enter')
        except Exception as e:
            # print(f"[DEBUG] 快捷键处理异常: {e}")
            pass

    # 注册全局热键监听 (仅在 Windows 下有效且需要管理员权限)
    try:
        # 使用 suppress=False 允许事件继续传递给系统，这样正常的文本粘贴不受影响
        keyboard.add_hotkey('ctrl+v', handle_clipboard_shortcut, suppress=False)
    except Exception as e:
        # print(f"[DEBUG] 热键注册失败: {e}")
        pass

    while True:
        try:
            # 重置中断标志
            agent.interruptHandler.reset()
            
            # 在提示符中显示当前工作目录和运行中的进程数
            current_dir = os.getcwd()
            
            # 检查是否有正在运行的进程
            try:
                running_processes = agent.terminalManager.list_terminals()
                if running_processes:
                    proc_info = f" {Fore.YELLOW}[{len(running_processes)} 个进程运行中]{Style.RESET_ALL}"
                else:
                    proc_info = ""
            except:
                proc_info = ""
            
            prompt = f"\n{Fore.BLUE}{current_dir}{Style.RESET_ALL}{proc_info}\n{Style.BRIGHT}User: "
            inputOfUser = _normalize_user_input(input(prompt))
            
            # 3a. 如果是由于粘贴操作触发的自动回车，则刷新显示并恢复之前的输入内容
            if just_pasted:
                just_pasted = False
                if pending_pastes:
                    last_path = pending_pastes[-1]
                    filename = os.path.basename(last_path)
                    # 清除当前行（即自动回车产生的新行），保持界面整洁
                    print("\033[F\033[K", end="") # 回到上一行并清除内容
                    print(f"{Fore.GREEN}[已粘贴] {filename} (当前共 {len(pending_pastes)} 个文件){Style.RESET_ALL}")
                    print(f"{Fore.CYAN}[提示] 继续粘贴图片，或直接按【回车】发送分析，输入 'cancel' 撤回。{Style.RESET_ALL}")
                
                # 如果用户之前正在输入内容，通过模拟键盘输入将其写回终端，方便用户继续输入
                if inputOfUser:
                    keyboard.write(inputOfUser)
                continue
            
            # 优化内容处理流程 (支持直接粘贴路径、剪贴板图片、剪贴板多行文本)
            
            # 1. 如果输入为空，尝试从剪贴板获取内容
            if not inputOfUser.strip():
                if pending_pastes:
                    # 如果有待处理的粘贴，则整合发送
                    paths_str = "\n".join([f"- {p}" for p in pending_pastes])
                    inputOfUser = f"请识别并分析以下图片/文档：\n{paths_str}"
                    print(f"{Fore.GREEN}[系统] 正在准备发送 {len(pending_pastes)} 个文件...{Style.RESET_ALL}")
                    pending_pastes = [] # 发送后清空
                else:
                    # 尝试获取图片/文件 (优先文件，因为 PIL 抓取图片很准确)
                    paste_dir = os.path.join(savedConfig.get("storage_dir", os.path.join(get_repo_root(), "storage")), "pastes")
                    print(f"{Fore.YELLOW}[系统] 正在检查剪贴板内容...{Style.RESET_ALL}", end="\r")
                    img_path = save_clipboard_file(save_dir=paste_dir)
                    if img_path:
                        inputOfUser = f"请识别并分析这个图片/文档: {img_path}"
                        print(f"{Fore.GREEN}[系统] 已从剪贴板加载文件: {img_path}{Style.RESET_ALL}")
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
            
            # 3. 如果是普通文本但包含图片/文档关键词，再次检查剪贴板内容 (兼容旧逻辑)
            else:
                doc_keywords = ["图片", "图", "识别", "ocr", "看下", "分析", "image", "pic", "这张", "pdf", "文档", "文件"]
                if any(k in inputOfUser.lower() for k in doc_keywords) and len(inputOfUser) < 20:
                    paste_dir = os.path.join(savedConfig.get("storage_dir", os.path.join(get_repo_root(), "storage")), "pastes")
                    img_path = save_clipboard_file(save_dir=paste_dir)
                    if img_path:
                        inputOfUser += f" (文件已自动关联: {img_path})"
                        print(f"{Fore.GREEN}[系统] 已检测并关联剪贴板内容: {img_path}{Style.RESET_ALL}")
                        # 自动清理旧文件
                        prune_directory(paste_dir, 50)

            raw_cmd = inputOfUser.strip()
            if not raw_cmd:
                continue
            
            # 处理特殊命令
            parts = raw_cmd.split()
            cmd = _normalize_command_token(parts[0]).lower()
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
                paste_dir = os.path.join(savedConfig.get("storage_dir", os.path.join(get_repo_root(), "storage")), "pastes")
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

            if cmd == "setup" and not args:
                savedConfig = run_setup_wizard(configManager)
                # 重新初始化 agent 以加载新配置 (特别是 API Key 和路径)
                agent = VoidAgent(config=Config(**savedConfig))
                continue
            
            if cmd in ["terminal", "logs"]:
                # Import output manager
                try:
                    from ..core.terminal_output_manager import TerminalOutputManager
                    output_mgr = TerminalOutputManager()
                    
                    if not args:
                        print(f"{Fore.YELLOW}用法:{Style.RESET_ALL}")
                        print(f"  terminal <id>     - 查看指定终端的完整输出")
                        print(f"  terminal list     - 列出最近的终端记录")
                        print(f"  terminal stats    - 查看存储统计")
                        continue
                    
                    if args[0].lower() == "list":
                        # List recent terminal outputs
                        limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
                        records = output_mgr.list_recent(limit=limit)
                        
                        if not records:
                            print(f"{Fore.YELLOW}没有找到终端输出记录{Style.RESET_ALL}")
                            continue
                        
                        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}最近的终端输出记录{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
                        
                        for i, rec in enumerate(records, 1):
                            exit_color = Fore.GREEN if rec['exit_code'] == 0 else Fore.RED
                            truncated = f" {Fore.YELLOW}(已截断){Style.RESET_ALL}" if rec['truncated'] else ""
                            print(f"{i}. {Fore.YELLOW}[{rec['record_id']}]{Style.RESET_ALL} {rec['command']}")
                            print(f"   时间: {rec['timestamp'][:19]} | 退出码: {exit_color}{rec['exit_code']}{Style.RESET_ALL}{truncated}")
                            print(f"   目录: {rec['cwd']}")
                            print()
                        
                        print(f"{Fore.CYAN}提示: 使用 'terminal <id>' 查看完整输出{Style.RESET_ALL}\n")
                        continue
                    
                    elif args[0].lower() == "stats":
                        # Show storage statistics
                        stats = output_mgr.get_storage_stats()
                        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}终端输出存储统计{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
                        print(f"{Fore.YELLOW}总记录数:{Style.RESET_ALL} {stats['total_records']}")
                        print(f"{Fore.YELLOW}存储大小:{Style.RESET_ALL} {stats['total_size_mb']} MB")
                        print(f"{Fore.YELLOW}日期目录数:{Style.RESET_ALL} {stats['date_directories']}")
                        print(f"{Fore.YELLOW}缓存记录数:{Style.RESET_ALL} {stats['recent_records_cached']}")
                        print(f"{Fore.YELLOW}存储目录:{Style.RESET_ALL} {stats['storage_dir']}")
                        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
                        continue
                    
                    else:
                        # View specific terminal output
                        record_id = args[0]
                        success, record, msg = output_mgr.get_output(record_id)
                        
                        if not success or not record:
                            print(f"{Fore.RED}未找到终端输出记录: {record_id}{Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}提示: 使用 'terminal list' 查看可用的记录{Style.RESET_ALL}")
                            continue
                        
                        # Display full output
                        display = output_mgr.format_output_display(record, max_lines=None)
                        print(display)
                        
                        # Ask if user wants to save to file
                        save_choice = input(f"{Fore.CYAN}是否保存到文件? (y/N): {Style.RESET_ALL}").strip().lower()
                        if save_choice == 'y':
                            filename = f"terminal_{record_id}.txt"
                            try:
                                with open(filename, 'w', encoding='utf-8') as f:
                                    f.write(f"Command: {record.command}\n")
                                    f.write(f"Working Directory: {record.cwd}\n")
                                    f.write(f"Timestamp: {record.timestamp}\n")
                                    f.write(f"Exit Code: {record.exit_code}\n")
                                    f.write(f"{'=' * 60}\n\n")
                                    f.write("=== STDOUT ===\n")
                                    f.write(record.stdout)
                                    f.write("\n\n=== STDERR ===\n")
                                    f.write(record.stderr)
                                print(f"{Fore.GREEN}已保存到: {filename}{Style.RESET_ALL}")
                            except Exception as e:
                                print(f"{Fore.RED}保存失败: {e}{Style.RESET_ALL}")
                        
                        continue
                
                except ImportError:
                    print(f"{Fore.RED}终端输出管理器未安装{Style.RESET_ALL}")
                    continue
                except Exception as e:
                    print(f"{Fore.RED}错误: {e}{Style.RESET_ALL}")
                    continue
            


    # ... (inside run_cli loop) ...

            if cmd == "ps" and not args:
                # List running processes
                try:
                    # 使用排序后的列表
                    sorted_terms = _get_sorted_terminals(agent.terminalManager)
                    terminals = []
                    # 重新封装为 list_terminals 的格式，但附带 index
                    for idx, (tid, term) in enumerate(sorted_terms, 1):
                         status = agent.terminalManager.get_terminal_status(tid)
                         status['index'] = idx
                         terminals.append(status)
                         
                    total_tracked = len(agent.terminalManager.terminals)
                except Exception as e:
                    print(f"{Fore.RED}错误: 获取进程列表失败: {e}{Style.RESET_ALL}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                if not terminals:
                    if total_tracked > 0:
                        print(f"{Fore.YELLOW}没有正在运行的进程（已跟踪 {total_tracked} 个已结束的进程）{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}没有正在运行的进程{Style.RESET_ALL}")
                    continue
                
                print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}正在运行的进程 ({len(terminals)}/{total_tracked}){Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
                
                for t in terminals:
                    uptime_str = f"{int(t['uptime'])}s"
                    if t['uptime'] >= 60:
                        uptime_str = f"{int(t['uptime'] / 60)}m {int(t['uptime']) % 60}s"
                    
                    status_color = Fore.GREEN if t['is_running'] else Fore.RED
                    status = "RUNNING" if t['is_running'] else "STOPPED"
                    
                    proc_type = "长期" if t.get('is_long_running') else "短期"
                    
                    # 显示简单 ID
                    idx_str = f"[{t['index']}]"
                    print(f"{Fore.YELLOW}{idx_str:<5}{Style.RESET_ALL} {t['command'][:60]}")
                    print(f"      ID: {t['id']} | PID: {t['pid']} | 状态: {status_color}{status}{Style.RESET_ALL} | 运行: {uptime_str}")
                    print()
                
                print(f"{Fore.CYAN}提示: 使用 'kill <id>' 或 'watch <id>' (支持简单ID 1,2...){Style.RESET_ALL}\n")
                continue
            
            if cmd == "kill":
                target_tid = None
                force = False
                
                if not args:
                    # 无参数：尝试 kill 最近的一个？
                    # 用户通常不会希望无意中 kill 进程，所以 kill 最好还是要求确认或者显式参数。
                    # 但用户需求里提到了：如果直接无参数回车则默认使用最近启动的子进程。
                    # 对于 kill 来说这有点危险，但既然用户要求... 我们加个确认吧。
                    sorted_terms = _get_sorted_terminals(agent.terminalManager)
                    if sorted_terms:
                        target_tid = sorted_terms[-1][0] # 最近的一个
                        print(f"{Fore.YELLOW}未指定 ID，默认选择最近的进程: {target_tid}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}用法:{Style.RESET_ALL}")
                        print(f"  kill <id>        - 终止指定进程（支持简单ID 1,2...）")
                        print(f"  kill <id> -f     - 强制终止指定进程")
                        print(f"  kill all         - 终止所有进程")
                        continue
                else:
                    if args[0].lower() == "all":
                         # ... (existing all logic) ...
                         pass
                    else:
                        raw_id = args[0]
                        target_tid = _resolve_terminal_id(agent.terminalManager, raw_id)
                        if not target_tid:
                            print(f"{Fore.RED}找不到 ID 为 '{raw_id}' 的进程{Style.RESET_ALL}")
                            continue
                        
                        force = len(args) > 1 and args[1].lower() in {"-f", "--force", "force"}

                if args and args[0].lower() == "all":
                     # existing logic
                     terminals = agent.terminalManager.list_terminals()
                     if not terminals:
                        print(f"{Fore.YELLOW}没有正在运行的进程{Style.RESET_ALL}")
                        continue
                    
                     confirm = input(f"{Fore.RED}确认终止所有 {len(terminals)} 个进程? (y/N): {Style.RESET_ALL}").strip().lower()
                     if confirm != "y":
                        print(f"{Fore.YELLOW}已取消{Style.RESET_ALL}")
                        continue
                    
                     success, failed = agent.terminalManager.kill_all_terminals()
                     print(f"{Fore.GREEN}成功终止: {success}{Style.RESET_ALL} | {Fore.RED}失败: {failed}{Style.RESET_ALL}")
                     continue

                # Execute single kill
                if target_tid:
                    # 如果是默认选择的（无参），或者用户输入的，都执行
                    # 再次确认一下如果是默认的
                    if not args:
                         confirm = input(f"{Fore.YELLOW}确认终止最近的进程 {target_tid}? (y/N): {Style.RESET_ALL}").strip().lower()
                         if confirm != "y":
                             continue

                    ok, msg = agent.terminalManager.kill_terminal(target_tid, force=force)
                    if ok:
                        print(f"{Fore.GREEN}✓ {msg}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}✗ {msg}{Style.RESET_ALL}")
                continue
            
            if cmd == "watch":
                target_tid = None
                
                if not args:
                    # 默认最近
                    sorted_terms = _get_sorted_terminals(agent.terminalManager)
                    if sorted_terms:
                        target_tid = sorted_terms[-1][0]
                        # print(f"{Fore.CYAN}自动选择最近的进程: {target_tid}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}当前没有运行中的进程。{Style.RESET_ALL}")
                        continue
                else:
                    raw_id = args[0]
                    # 检查是否是 flag
                    if raw_id.startswith("-"):
                        # 如果第一个参数是 flag，说明没给 ID，默认最近
                         sorted_terms = _get_sorted_terminals(agent.terminalManager)
                         if sorted_terms:
                            target_tid = sorted_terms[-1][0]
                         else:
                            print(f"{Fore.YELLOW}当前没有运行中的进程。{Style.RESET_ALL}")
                            continue
                    else:
                        target_tid = _resolve_terminal_id(agent.terminalManager, raw_id)
                        if not target_tid:
                             print(f"{Fore.RED}找不到 ID 为 '{raw_id}' 的进程{Style.RESET_ALL}")
                             continue

                tid = target_tid
                term = agent.terminalManager.terminals.get(tid)
                # ... rest of watch logic ...


                timeout_s: Optional[float] = None
                interval_s = 0.1
                plain = False

                idx = 1
                bad_arg = None
                while idx < len(args):
                    a = str(args[idx]).strip()
                    al = a.lower()
                    if al in {"-h", "--help", "help", "?"}:
                        print(f"{Fore.YELLOW}用法: watch <terminal_id> [--timeout 秒] [--interval 秒] [--plain]{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}交互控制: q退出 p暂停/继续 c清屏 k终止 f强制终止 +/-调速 t状态 h帮助{Style.RESET_ALL}")
                        bad_arg = "help"
                        break
                    if al in {"--plain", "--no-prefix"}:
                        plain = True
                        idx += 1
                        continue
                    if al in {"--timeout", "-t"}:
                        if idx + 1 >= len(args):
                            bad_arg = a
                            break
                        try:
                            v = float(str(args[idx + 1]).strip())
                            timeout_s = None if v <= 0 else v
                        except Exception:
                            bad_arg = a
                            break
                        idx += 2
                        continue
                    if al in {"--interval", "-i"}:
                        if idx + 1 >= len(args):
                            bad_arg = a
                            break
                        try:
                            v = float(str(args[idx + 1]).strip())
                            interval_s = 0.1 if v <= 0 else v
                        except Exception:
                            bad_arg = a
                            break
                        idx += 2
                        continue
                    bad_arg = a
                    break

                if bad_arg:
                    if bad_arg != "help":
                        print(f"{Fore.YELLOW}参数错误: {bad_arg}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}用法: watch <terminal_id> [--timeout 秒] [--interval 秒] [--plain]{Style.RESET_ALL}")
                    continue

                def _format_watch_line(s: str) -> str:
                    if not plain:
                        return s
                    if s.startswith("stdout: "):
                        return s[8:]
                    if s.startswith("stderr: "):
                        return s[8:]
                    return s

                def _read_key() -> Optional[str]:
                    try:
                        if sys.platform == "win32":
                            import msvcrt

                            if not msvcrt.kbhit():
                                return None
                            ch = msvcrt.getwch()
                            if ch in {"\x00", "\xe0"}:
                                try:
                                    _ = msvcrt.getwch()
                                except Exception:
                                    pass
                                return None
                            return ch
                        else:
                            import select

                            r, _, _ = select.select([sys.stdin], [], [], 0)
                            if not r:
                                return None
                            return sys.stdin.read(1)
                    except Exception:
                        return None

                def _print_watch_header(current_term) -> None:
                    pid = None
                    try:
                        pid = current_term.process.pid
                    except Exception:
                        pid = None
                    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}监控: {current_term.command}{Style.RESET_ALL}")
                    if pid is not None:
                        print(f"{Fore.CYAN}终端 ID: {tid} | PID: {pid}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}终端 ID: {tid}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}按键: q退出 i交互 p暂停/继续 c清屏 k终止 f强制终止 +/-调速 t状态 h帮助{Style.RESET_ALL}")
                    
                    # 检查是否为交互式控制台进程（输出未捕获）
                    if sys.platform == "win32" and current_term.is_long_running:
                        try:
                            # 粗略判断：如果是交互式创建的，stdout 应该是 None
                            if current_term.process.stdout is None:
                                print(f"\n{Fore.YELLOW}⚠️  注意：此进程运行在独立的交互式窗口中。{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}    输出内容无法在此处显示，请切换到弹出的新窗口进行查看和交互。{Style.RESET_ALL}")
                        except Exception:
                            pass

                    if timeout_s:
                        print(f"{Fore.CYAN}超时: {timeout_s:.0f}s | 刷新: {interval_s:.2f}s{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}刷新: {interval_s:.2f}s{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
                    sys.stdout.flush()

                paused = False
                history_lines = 80
                try:
                    _print_watch_header(term)
                    print(f"{Fore.GREEN}=== 历史输出 (最近{history_lines}行) ==={Style.RESET_ALL}")
                    sys.stdout.flush()
                    if term.output:
                        for line in list(term.output)[-history_lines:]:
                            print(_format_watch_line(str(line)).rstrip())
                        sys.stdout.flush()
                    else:
                        print(f"{Fore.YELLOW}(暂无输出){Style.RESET_ALL}")
                        sys.stdout.flush()

                    print(f"\n{Fore.GREEN}=== 实时输出（监控中...）==={Style.RESET_ALL}")
                    sys.stdout.flush()

                    last_line_count = len(term.output)
                    start_watch_time = time.time()

                    input_mode = False
                    should_exit_watch = False

                    while True:
                        if should_exit_watch:
                            break

                        # 处理所有缓冲按键
                        while True:
                            key = _read_key()
                            if not key:
                                break
                            
                            if input_mode:
                                if key == '\x1b': # ESC
                                    input_mode = False
                                    print(f"\n{Fore.CYAN}已退出交互模式{Style.RESET_ALL}")
                                    sys.stdout.flush()
                                else:
                                    # 发送输入
                                    # 将回车符转换为换行符，因为管道模式下的 input() 通常需要 \n
                                    data_to_send = key
                                    if key == '\r':
                                        data_to_send = '\n'
                                    
                                    if agent.terminalManager.send_input(tid, data_to_send):
                                        # 本地回显
                                        if key == '\r':
                                            sys.stdout.write('\n')
                                        elif key == '\x08': # Backspace
                                            sys.stdout.write('\b \b')
                                        else:
                                            sys.stdout.write(key)
                                        sys.stdout.flush()
                                continue

                            kl = key.lower()
                            
                            if kl == 'i':
                                input_mode = True
                                print(f"\n{Fore.GREEN}=== 进入交互模式 (按 ESC 退出) ==={Style.RESET_ALL}")
                                print(f"{Fore.GREEN}提示: 你的输入将直接发送给进程。{Style.RESET_ALL}")
                                sys.stdout.flush()
                                continue

                            if kl in {"q"}:
                                should_exit_watch = True
                                break
                            if kl in {"h", "?"}:
                                print(f"\n{Fore.CYAN}按键: q退出 i交互 p暂停/继续 c清屏 k终止 f强制终止 +/-调速 t状态 h帮助{Style.RESET_ALL}")
                                sys.stdout.flush()
                            elif kl in {"p", " "}:
                                paused = not paused
                                st = "暂停" if paused else "继续"
                                print(f"\n{Fore.CYAN}已{st}监控{Style.RESET_ALL}")
                                sys.stdout.flush()
                            elif kl in {"c"}:
                                try:
                                    os.system("cls" if sys.platform == "win32" else "clear")
                                except Exception:
                                    pass
                                current_term = agent.terminalManager.terminals.get(tid) or term
                                _print_watch_header(current_term)
                                print(f"{Fore.GREEN}=== 历史输出 (最近{history_lines}行) ==={Style.RESET_ALL}")
                                if current_term.output:
                                    for line in list(current_term.output)[-history_lines:]:
                                        print(_format_watch_line(str(line)).rstrip())
                                else:
                                    print(f"{Fore.YELLOW}(暂无输出){Style.RESET_ALL}")
                                print(f"\n{Fore.GREEN}=== 实时输出（监控中...）==={Style.RESET_ALL}")
                                sys.stdout.flush()
                                last_line_count = len(current_term.output)
                            elif kl in {"k"}:
                                ok, msg = agent.terminalManager.kill_terminal(tid, force=False)
                                color = Fore.GREEN if ok else Fore.RED
                                print(f"\n{color}{msg}{Style.RESET_ALL}")
                                sys.stdout.flush()
                                should_exit_watch = True
                                break
                            elif kl in {"f"}:
                                ok, msg = agent.terminalManager.kill_terminal(tid, force=True)
                                color = Fore.GREEN if ok else Fore.RED
                                print(f"\n{color}{msg}{Style.RESET_ALL}")
                                sys.stdout.flush()
                                should_exit_watch = True
                                break
                            elif key == "+":
                                interval_s = max(0.02, interval_s * 0.8)
                                print(f"\n{Fore.CYAN}刷新间隔: {interval_s:.2f}s{Style.RESET_ALL}")
                                sys.stdout.flush()
                            elif key == "-":
                                interval_s = min(5.0, interval_s * 1.25)
                                print(f"\n{Fore.CYAN}刷新间隔: {interval_s:.2f}s{Style.RESET_ALL}")
                                sys.stdout.flush()
                            elif kl in {"t"}:
                                current_term = agent.terminalManager.terminals.get(tid) or term
                                status = agent.terminalManager.get_terminal_status(tid) or {}
                                is_running = bool(status.get("is_running"))
                                uptime = status.get("uptime")
                                exit_code = status.get("exit_code")
                                lines = len(current_term.output) if current_term and hasattr(current_term, "output") else 0
                                up_str = f"{uptime:.1f}s" if isinstance(uptime, (int, float)) else "-"
                                run_str = f"{Fore.GREEN}RUNNING{Style.RESET_ALL}" if is_running else f"{Fore.YELLOW}STOPPED{Style.RESET_ALL}"
                                print(f"\n{Fore.CYAN}状态: {run_str} | uptime={up_str} | exit_code={exit_code} | 输出行={lines}{Style.RESET_ALL}")
                                sys.stdout.flush()
                            else:
                                # 提示用户：常规模式下无法输入
                                current_term = agent.terminalManager.terminals.get(tid) or term
                                if sys.platform == "win32" and getattr(current_term, "is_long_running", False):
                                    if current_term.process.stdout is None:
                                         print(f"\n{Fore.YELLOW}提示: 此为交互式窗口进程，请切换到新窗口操作。按 q 退出监控。{Style.RESET_ALL}")
                                         sys.stdout.flush()
                                else:
                                    print(f"\n{Fore.YELLOW}提示: 监控模式。按 i 进入交互模式可发送输入。按 q 退出监控。{Style.RESET_ALL}")
                                    sys.stdout.flush()

                        current_term = agent.terminalManager.terminals.get(tid) or term
                        if not paused:
                            out = getattr(current_term, "output", None)
                            if isinstance(out, list):
                                current_len = len(out)
                                
                                # 处理新增行
                                if current_len > last_line_count:
                                    # 先把之前未完结的行（如果有）补全
                                    # 注意：last_line_count 指的是之前已经完整打印或部分打印过的行数
                                    # 实际上，如果 last_line_count 指向的最后一行发生了变化（从部分变完整），我们也需要刷新它
                                    
                                    # 简单策略：如果之前打印过最后一行且它被更新了，我们可能需要回退并重打？
                                    # 由于终端回退比较麻烦，我们这里采用一种简化的“流式追加”逻辑
                                    
                                    # 打印从 last_line_count 开始的所有新行
                                    # 如果 last_line_count > 0，说明之前已经打印过 out[:last_line_count]
                                    # 但 out[last_line_count-1] 可能从不完整变成了完整，或者 out[last_line_count] 是新行
                                    
                                    # 修正逻辑：
                                    # 我们维护 last_printed_content 来追踪最后一行的内容
                                    pass

                                # 重新实现输出逻辑以支持行内刷新
                                start_idx = last_line_count
                                # 如果之前打印过行，且最后一行可能被更新（即不是以换行符结尾），我们需要检查
                                if last_line_count > 0:
                                    # 检查上一行是否发生了变化（例如从 partial 变成了 complete）
                                    # 但由于我们无法轻易覆盖上一行（除非用 \r），这里简化处理：
                                    # 如果 terminal.py 保证 append 只发生在换行时（旧逻辑），那没问题。
                                    # 但新逻辑是 update in place。
                                    
                                    # 既然我们无法完美控制光标上移，我们假设：
                                    # 如果上一行是部分内容（没换行），我们应该用 \r 覆盖它。
                                    # 但为了简单，我们只关注“当前最后一行”的实时刷新。
                                    pass

                                # 打印完全新增的行（除了最后一行，因为最后一行可能还在变）
                                if current_len > last_line_count:
                                    # 如果有新行加入
                                    # 1. 先打印那些已经确定的行
                                    for i in range(last_line_count, current_len - 1):
                                        print(_format_watch_line(str(out[i])).rstrip())
                                    
                                    # 2. 更新 last_line_count 到只剩最后一行未处理
                                    last_line_count = current_len - 1
                                
                                # 处理最后一行（可能是新增的，也可能是更新的）
                                if current_len > 0:
                                    last_line_idx = current_len - 1
                                    last_line_content = str(out[last_line_idx])
                                    formatted_line = _format_watch_line(last_line_content)
                                    
                                    # 如果这一行是全新的（last_line_count <= last_line_idx）
                                    # 或者这一行虽然之前打印过，但现在内容变了
                                    # 我们使用 \r 来实现行内刷新
                                    
                                    # 注意：rstrip() 会去掉末尾换行符，这对于判断是否行结束很重要
                                    # 但 _format_watch_line 返回的原始内容可能包含 \n
                                    
                                    has_newline = last_line_content.endswith('\n')
                                    display_content = formatted_line.rstrip()
                                    
                                    if last_line_count <= last_line_idx:
                                        # 这是新的一行（或者之前没打印完的行）
                                        # 如果是追加模式，且不是第一行输出，我们可能需要先换行？
                                        # 不，print默认换行。
                                        # 我们使用 sys.stdout.write + \r 来支持刷新
                                        
                                        # 如果这一行已经结束了
                                        if has_newline:
                                            # 如果它是新行，直接打印
                                            # 如果它是之前刷新的行，我们需要先 \r 覆盖再打印
                                            sys.stdout.write('\r' + display_content + '\n')
                                            last_line_count = current_len # 这一行已完结
                                        else:
                                            # 还没结束，使用 \r 打印
                                            sys.stdout.write('\r' + display_content)
                                            # 不更新 last_line_count，因为这行还没完
                                    
                                    sys.stdout.flush()

                        try:
                            running = current_term.process.poll() is None
                        except Exception:
                            running = False

                        if timeout_s and (time.time() - start_watch_time) > timeout_s:
                            print(f"\n{Fore.YELLOW}监控超时（{timeout_s:.0f}秒），自动退出{Style.RESET_ALL}")
                            sys.stdout.flush()
                            break

                        if not running:
                            if not paused:
                                print(f"\n{Fore.YELLOW}进程已结束 | 退出码: {current_term.exit_code}{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}按 q 退出，或按 t 查看状态{Style.RESET_ALL}")
                                sys.stdout.flush()
                                paused = True

                        time.sleep(interval_s)

                except KeyboardInterrupt:
                    print(f"\n\n{Fore.CYAN}已退出监控模式{Style.RESET_ALL}\n")
                except Exception as e:
                    print(f"\n{Fore.RED}监控出错: {e}{Style.RESET_ALL}\n")
                    import traceback
                    traceback.print_exc()

                continue
            
            if cmd == "monitor":
                if not args:
                    print(f"{Fore.YELLOW}用法: monitor <terminal_id>{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}功能说明: 在新 CMD 窗口中打开进程输出监控{Style.RESET_ALL}")
                    continue
                
                tid = args[0]
                term = agent.terminalManager.terminals.get(tid)
                
                if not term:
                    print(f"{Fore.RED}终端 {tid} 不存在{Style.RESET_ALL}")
                    continue
                
                # 简化版：在新窗口启动 watch 命令
                try:
                    # 获取当前 agent 的启动命令
                    current_script = os.path.abspath(sys.argv[0]) if sys.argv else "agent"
                    
                    # 构建在新窗口中运行 watch 的命令
                    watch_cmd = f'start "Monitor: {term.command[:40]}" cmd /k "agent && echo. && echo 输入: watch {tid} && echo."'
                    
                    subprocess.Popen(watch_cmd, shell=True)
                    print(f"{Fore.GREEN}✓ 已在新窗口中打开监控（请在新窗口中输入 'watch {tid}'）{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}提示: 关闭监控窗口不会影响进程运行{Style.RESET_ALL}")
                    
                except Exception as e:
                    print(f"{Fore.RED}打开监控窗口失败: {e}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}替代方案: 在当前窗口使用 'watch {tid}' 命令{Style.RESET_ALL}")
                
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
                    except KeyboardInterrupt:
                        pass
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
                except KeyboardInterrupt:
                    pass
                except Exception:
                    pass
                print(f"{Fore.BLUE}小晨终端助手 正在退出...{Style.RESET_ALL}")
                break
            last_ctrl_c_time = now
            try:
                if autosaveFilename:
                    sessionManager.update_session(autosaveFilename, agent.getFullHistory(), cache_stats=agent.statsOfCache.to_dict())
                    print(f"\n{Fore.GREEN}✓ 会话已自动保存: {autosaveFilename}{Style.RESET_ALL}")
            except KeyboardInterrupt:
                pass
            except Exception:
                pass
            print(f"\n{Fore.YELLOW}⚠️  已请求中断 (Ctrl+C)。为避免误触，不会立即退出。{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   若要强制退出，请在 1.5 秒内再按一次 Ctrl+C{Style.RESET_ALL}")
            try:
                continue
            except Exception:
                continue
