import os
import sys
import threading
import time

from ..core.agent import VoidAgent
from ..core.config import Config
from ..utils.console import Fore, Style
from ..core.session import SessionManager
from ..core.config_manager import ConfigManager


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

    # 初始化配置管理器
    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
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
        verifySsl=verifySsl
    )
    agent = VoidAgent(config)
    sessionManager = SessionManager()
    autosaveFilename = ""
    autosaveTitle = ""
    firstUserInput = ""
    titleLock = threading.Lock()
    try:
        autosaveFilename = sessionManager.create_autosave_session()
    except Exception:
        autosaveFilename = ""
    
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
                        messages = sessionManager.load_session(selected_session['filename'])
                        if messages:
                            # 如果第一条消息是系统消息，则剔除它，因为 Agent 会自动生成
                            if messages and messages[0].get("role") == "system":
                                agent.historyOfMessages = messages[1:]
                            else:
                                agent.historyOfMessages = messages
                            
                            try:
                                if autosaveFilename:
                                    sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                            except Exception:
                                pass
                            print(f"{Fore.GREEN}✓ 已加载会话: {selected_session['filename']}{Style.RESET_ALL}")
                            print(f"{Fore.GREEN}  包含 {len(messages)} 条历史消息{Style.RESET_ALL}")
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

    def persist_history(messages: list) -> None:
        """
        将最新历史立即写入 autosave，会被 Agent 在每次模型输出后调用。
        """
        if not autosaveFilename:
            return
        with titleLock:
            title = autosaveTitle
            first = firstUserInput
        sessionManager.update_session(autosaveFilename, messages)
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

    while True:
        try:
            # 重置中断标志
            agent.interruptHandler.reset()
            
            inputOfUser = input(f"\n{Style.BRIGHT}User: ")
            raw_cmd = inputOfUser.strip()
            if not raw_cmd:
                continue
            
            # 处理特殊命令
            parts = raw_cmd.split()
            cmd = parts[0].lower()
            args = parts[1:]
            
            if cmd in ["help", "?"]:
                print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}命令帮助{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                print("exit / quit           退出（可选择保存会话）")
                print("save                  保存当前会话")
                print("clear                 清空当前会话历史")
                print("rollback              回退最近一次文件修改")
                print("undo                  一键回退到上一次对话（含文件修改）")
                print("sessions              查看最近 10 个历史会话")
                print("load [n]              加载第 n 个历史会话（不退出）")
                print("new                   新建空会话并继续对话")
                print("models                列出模型预设")
                print("model                 查看当前模型配置")
                print("model use [n]          切换到第 n 个模型预设")
                print("model set <url> <name> [ssl]  自定义模型配置 (ssl=true/false)")
                print("model key <api_key>    设置/更新 API Key（会写入 config.json）")
                print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")
                continue

            if cmd == "rollback":
                agent.rollbackLastOperation()
                try:
                    if autosaveFilename:
                        sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                except Exception:
                    pass
                continue

            if cmd == "undo":
                agent.rollbackLastChat()
                try:
                    if autosaveFilename:
                        sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                except Exception:
                    pass
                continue
            
            if cmd in ["sessions"]:
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
                messages = sessionManager.load_session(selected_session["filename"])
                if not messages:
                    print(f"{Fore.RED}✗ 加载会话失败{Style.RESET_ALL}")
                    continue
                if messages and messages[0].get("role") == "system":
                    agent.historyOfMessages = messages[1:]
                else:
                    agent.historyOfMessages = messages
                agent.historyOfOperations = []
                agent.lastFullMessages = []
                if hasattr(agent, "_chatMarkers"):
                    agent._chatMarkers = []
                try:
                    autosaveFilename = sessionManager.create_autosave_session()
                    sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                except Exception:
                    pass
                print(f"{Fore.GREEN}✓ 已加载会话: {selected_session['filename']}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}  包含 {len(messages)} 条历史消息{Style.RESET_ALL}")
                continue

            if cmd in ["new"]:
                agent.historyOfMessages = []
                agent.historyOfOperations = []
                agent.lastFullMessages = []
                if hasattr(agent, "_chatMarkers"):
                    agent._chatMarkers = []
                try:
                    autosaveFilename = sessionManager.create_autosave_session()
                    sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                except Exception:
                    pass
                print(f"{Fore.GREEN}✓ 已新建会话{Style.RESET_ALL}")
                continue

            if cmd == "models":
                print_model_presets()
                continue

            if cmd == "model":
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

            if cmd in ["exit", "quit"]:
                if agent.historyOfMessages:
                    try:
                        if autosaveFilename:
                            sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                            print(f"{Fore.GREEN}✓ 会话已自动保存: {autosaveFilename}{Style.RESET_ALL}")
                    except Exception:
                        pass
                break
            
            if cmd == "save":
                if agent.historyOfMessages:
                    session_name = input(f"{Fore.CYAN}输入会话名称 (可选，按回车跳过): {Style.RESET_ALL}").strip()
                    filename = sessionManager.save_session(agent.getFullHistory(), session_name or None)
                    if filename:
                        print(f"{Fore.GREEN}✓ 会话已保存: {filename}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}当前没有会话历史{Style.RESET_ALL}")
                continue
            
            if cmd == "clear":
                confirm = input(f"{Fore.YELLOW}确认清空会话历史? (y/n): {Style.RESET_ALL}").strip().lower()
                if confirm == "y":
                    agent.historyOfMessages = []
                    try:
                        if autosaveFilename:
                            sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                    except Exception:
                        pass
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
            try:
                if autosaveFilename:
                    sessionManager.update_session(autosaveFilename, agent.getFullHistory())
            except Exception:
                pass
            
        except KeyboardInterrupt:
            agent.interruptHandler.set_interrupted()
            now = time.time()
            if now - last_ctrl_c_time < 1.5:
                try:
                    if autosaveFilename:
                        sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                        print(f"\n{Fore.GREEN}✓ 会话已自动保存: {autosaveFilename}{Style.RESET_ALL}")
                except Exception:
                    pass
                print(f"{Fore.BLUE}小晨终端助手 正在退出...{Style.RESET_ALL}")
                break
            last_ctrl_c_time = now
            try:
                if autosaveFilename:
                    sessionManager.update_session(autosaveFilename, agent.getFullHistory())
                    print(f"\n{Fore.GREEN}✓ 会话已自动保存: {autosaveFilename}{Style.RESET_ALL}")
            except Exception:
                pass
            print(f"\n{Fore.YELLOW}⚠️  已请求中断 (Ctrl+C)。为避免误触，不会立即退出。{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   若要强制退出，请在 1.5 秒内再按一次 Ctrl+C{Style.RESET_ALL}")
            try:
                continue
            except Exception:
                continue
