import sys
import os

"""
小晨终端助手 (XIAOCHEN_TERMINAL) - PyInstaller 启动器
此脚本作为打包为 EXE 时的入口点。
"""

# 确保当前目录在路径中，以便能够导入 xiaochen_agent_v2 包
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

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
