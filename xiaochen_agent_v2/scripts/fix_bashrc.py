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
    
    # 定义清理正则
    # 匹配 agent() { ... } 这种函数定义块的开始
    func_start_re = re.compile(r'^\s*agent\s*\(\s*\)\s*\{')
    # 匹配标记位
    start_mark = "# >>> XIAOCHEN AGENT START >>>"
    end_mark = "# <<< XIAOCHEN AGENT END <<<"
    
    i = 0
    while i < len(lines):
        line_num = i + 1
        line = lines[i]
        stripped = line.strip()
        
        # 如果这一行被 bash 明确标记为语法错误，且包含 suspicious 字符
        if line_num in error_lines and (stripped == "}" or stripped.startswith("local ")):
            print(f"检测到语法错误行 {line_num}: '{stripped}'，已自动移除。")
            i += 1
            continue

        # 处理标记位块
        if start_mark in line:
            skip_mode = True
            i += 1
            continue
        if end_mark in line:
            skip_mode = False
            i += 1
            continue
            
        if skip_mode:
            i += 1
            continue

        # 处理旧的函数定义块 (针对残留的 agent() { ... })
        if func_start_re.match(line):
            # 找到对应的闭合括号
            brace_count = line.count('{') - line.count('}')
            while i < len(lines) and brace_count > 0:
                i += 1
                if i < len(lines):
                    brace_count += lines[i].count('{') - lines[i].count('}')
            i += 1
            continue

        # 处理残留的别名
        if stripped.startswith("alias agent="):
            i += 1
            continue
            
        # 修复孤立的 '}' (只删除那些紧跟在 agent 相关配置后的孤立大括号)
        if stripped == "}":
            # 检查前几行是否有 agent 关键字
            context = "".join(new_lines[-3:]).lower()
            if "agent" in context:
                i += 1
                continue

        # 处理可能误用的 local (不在函数内的 local)
        if stripped.startswith("local ") and "{" not in "".join(new_lines[-5:]): # 简单启发式判断
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
