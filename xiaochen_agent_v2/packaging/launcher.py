import sys
import os
import io
import platform
import json
import time
import threading
import requests
import colorama
import keyboard
import PIL
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

"""
小晨终端助手 (XIAOCHEN_TERMINAL) - PyInstaller 启动器
此脚本作为打包为 EXE 时的入口点。
"""

# 强制设置 Python 的标准输出为 UTF-8，防止 Windows 控制台乱码
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保当前目录在路径中，以便能够导入 xiaochen_agent_v2 包
if hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包后的路径
    base_path = sys._MEIPASS
else:
    # 普通脚本运行路径
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if base_path not in sys.path:
    sys.path.insert(0, base_path)

try:
    from xiaochen_agent_v2.ui.cli import run_cli
except ImportError as e:
    print(f"错误: 无法导入核心模块。请确保项目结构完整。\n详情: {e}")
    sys.exit(1)

if __name__ == "__main__":
    # 设置控制台标题（仅限 Windows）
    if os.name == 'nt':
        os.system('title 小晨终端助手 (XIAOCHEN_TERMINAL)')
    
    run_cli()
