import os

from .agent import VoidAgent
from .config import Config
from .console import Fore, Style


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

    apiKey = os.environ.get("VOID_API_KEY")
    baseUrl = os.environ.get("VOID_BASE_URL")
    modelName = os.environ.get("VOID_MODEL")
    verifySsl = True

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

    config = Config(
        apiKey=apiKey, 
        baseUrl=baseUrl or "https://api.deepseek.com", 
        modelName=modelName or "deepseek-chat",
        verifySsl=verifySsl
    )
    agent = VoidAgent(config)

    while True:
        try:
            inputOfUser = input(f"\n{Style.BRIGHT}User: ")
            if not inputOfUser.strip():
                continue
            if inputOfUser.strip().lower() == "rollback":
                agent.rollbackLastOperation()
                continue
            if inputOfUser.strip().lower() in ["exit", "quit"]:
                break
            agent.chat(inputOfUser)
        except KeyboardInterrupt:
            print(f"\n{Fore.BLUE}小晨终端助手 正在退出...{Style.RESET_ALL}")
            break

