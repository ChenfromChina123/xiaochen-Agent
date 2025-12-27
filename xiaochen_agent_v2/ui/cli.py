import os
import sys

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
                print(f"{i}. [{sess['timestamp']}] {sess['message_count']} 条消息 ({size_kb:.1f} KB)")
            
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

    while True:
        try:
            # 重置中断标志
            agent.interruptHandler.reset()
            
            inputOfUser = input(f"\n{Style.BRIGHT}User: ")
            if not inputOfUser.strip():
                continue
            
            # 处理特殊命令
            cmd_lower = inputOfUser.strip().lower()
            
            if cmd_lower == "rollback":
                agent.rollbackLastOperation()
                continue
            
            if cmd_lower in ["exit", "quit"]:
                # 询问是否保存会话
                if agent.historyOfMessages:
                    save_choice = input(f"{Fore.CYAN}是否保存当前会话? (y/n, 默认n): {Style.RESET_ALL}").strip().lower()
                    if save_choice == "y":
                        session_name = input(f"{Fore.CYAN}输入会话名称 (可选，按回车跳过): {Style.RESET_ALL}").strip()
                        filename = sessionManager.save_session(agent.getFullHistory(), session_name or None)
                        if filename:
                            print(f"{Fore.GREEN}✓ 会话已保存: {filename}{Style.RESET_ALL}")
                break
            
            if cmd_lower == "save":
                if agent.historyOfMessages:
                    session_name = input(f"{Fore.CYAN}输入会话名称 (可选，按回车跳过): {Style.RESET_ALL}").strip()
                    filename = sessionManager.save_session(agent.getFullHistory(), session_name or None)
                    if filename:
                        print(f"{Fore.GREEN}✓ 会话已保存: {filename}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}当前没有会话历史{Style.RESET_ALL}")
                continue
            
            if cmd_lower == "clear":
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
            agent.chat(inputOfUser)
            try:
                if autosaveFilename:
                    sessionManager.update_session(autosaveFilename, agent.getFullHistory())
            except Exception:
                pass
            
        except KeyboardInterrupt:
            # 设置中断标志
            agent.interruptHandler.set_interrupted()
            print(f"\n{Fore.YELLOW}⚠️  检测到中断信号 (Ctrl+C){Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   再次按 Ctrl+C 退出程序{Style.RESET_ALL}")
            
            # 等待第二次 Ctrl+C 来真正退出
            try:
                input(f"{Fore.CYAN}按回车继续，或 Ctrl+C 退出: {Style.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.BLUE}小晨终端助手 正在退出...{Style.RESET_ALL}")
                break
