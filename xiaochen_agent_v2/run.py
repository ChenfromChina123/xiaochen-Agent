import sys
import os

# 将上级目录添加到 sys.path 以支持包导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaochen_agent_v2.ui.cli import run_cli

if __name__ == "__main__":
    run_cli()
