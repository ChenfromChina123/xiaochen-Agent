import os
import re
import sys
import subprocess

def fix_bashrc():
    """
    专门修复和清理 .bashrc 中由于安装失败残留的损坏配置
    """
    home = os.path.expanduser("~")
    bashrc_path = os.path.join(home, ".bashrc")
    
    if not os.path.exists(bashrc_path):
        print(f"未找到 {bashrc_path}，无需修复。")
        return

    # 1. 备份
    backup_path = bashrc_path + ".bak_xiaochen"
    with open(bashrc_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"已备份原始文件到: {backup_path}")

    # 1.5 尝试检测语法错误的行号
    error_lines = set()
    try:
        res = subprocess.run(['bash', '-n', bashrc_path], capture_output=True, text=True)
        if res.returncode != 0:
            # 解析错误消息，例如: /root/.bashrc: line 25: syntax error...
            for line in res.stderr.splitlines():
                match = re.search(r'line (\d+):', line)
                if match:
                    error_lines.add(int(match.group(1)))
    except:
        pass

    # 2. 清理逻辑
    new_lines = []
    skip_mode = False
    
    # 强制清理：移除所有与 agent 相关的行，以及可能导致错误的孤立行
    # 我们宁愿删错也不愿留下语法错误
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        lower_line = line.lower()
        
        # 1. 处理标记位块 (优先级最高)
        if "# >>> XIAOCHEN AGENT" in line:
            skip_mode = True
            i += 1
            continue
        if "# <<< XIAOCHEN AGENT" in line:
            skip_mode = False
            i += 1
            continue
        if skip_mode:
            i += 1
            continue

        # 2. 处理残留的别名和直接运行指令
        # 如果行中包含 agent 路径且不是注释
        if "xiaochen-agent" in lower_line or "xiaochen_agent_v2" in lower_line:
            # 排除掉我们刚才处理的标记位
            i += 1
            continue

        # 3. 处理函数块 agent() {
        if re.search(r'^\s*agent\s*\(\s*\)\s*\{', line):
            # 跳过整个块
            brace_count = line.count('{') - line.count('}')
            while i < len(lines) and brace_count > 0:
                i += 1
                if i < len(lines):
                    brace_count += lines[i].count('{') - lines[i].count('}')
            i += 1
            continue

        # 4. 处理孤立的 local 和 }
        # 在 .bashrc 顶层出现的 local 或 } 几乎都是语法错误
        if stripped == "}" or stripped.startswith("local "):
            i += 1
            continue
            
        # 5. 处理残留的 alias
        if stripped.startswith("alias agent="):
            i += 1
            continue

        new_lines.append(line)
        i += 1

    # 3. 写入新文件 (移除连续的空行)
    clean_lines = []
    last_line_empty = False
    for line in new_lines:
        is_empty = not line.strip()
        if is_empty and last_line_empty:
            continue
        clean_lines.append(line)
        last_line_empty = is_empty

    with open(bashrc_path, 'w', encoding='utf-8') as f:
        f.writelines(clean_lines)
    
    print("已成功清理 .bashrc 中的损坏配置。")

if __name__ == "__main__":
    fix_bashrc()
