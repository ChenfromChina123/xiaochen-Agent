"""
显示格式化模块
优化AI工具使用的显示逻辑，提供友好的输出格式
"""
from typing import Dict, Any
from .console import Fore, Style


def format_tool_display(task: Dict[str, Any]) -> str:
    """
    将AI工具调用格式化为友好的显示格式
    
    Args:
        task: 工具任务字典
        
    Returns:
        格式化后的显示字符串
    """
    task_type = task.get("type", "")
    
    if task_type == "read_file":
        path = task.get("path", "")
        start = task.get("start_line")
        end = task.get("end_line")
        if start and end:
            return f"📖 读取: {path} (行 {start}-{end})"
        return f"📖 读取: {path}"
    
    elif task_type == "write_file":
        path = task.get("path", "")
        return f"✍️  写入: {path}"
    
    elif task_type == "edit_lines":
        path = task.get("path", "")
        delete_start = task.get("delete_start")
        delete_end = task.get("delete_end")
        insert_at = task.get("insert_at")
        return f"✏️  编辑: {path} (删除 {delete_start}-{delete_end}, 插入于 {insert_at})"
    
    elif task_type == "replace_in_file":
        path = task.get("path", "")
        count = task.get("count", 1)
        return f"🔁 替换: {path} (最多 {count} 处)"
    
    elif task_type == "run_command":
        cmd = str(task.get("command", "")).strip().splitlines()[0] if task.get("command") else ""
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        return f"⚙️  执行: {cmd}"
    
    elif task_type == "search_files":
        pattern = task.get("pattern", "")
        return f"🔍 搜索文件: {pattern}"
    
    elif task_type == "search_in_files":
        regex = task.get("regex", "")
        glob_pattern = task.get("glob", "**/*")
        return f"🔎 搜索内容: {regex} (文件: {glob_pattern})"
    
    elif task_type.startswith("task_"):
        action = task_type.replace("task_", "")
        if action == "add":
            content = task.get("content", "")
            return f"📝 添加任务: {content}"
        elif action == "update":
            tid = task.get("id", "")
            return f"📝 更新任务: {tid}"
        elif action == "delete":
            tid = task.get("id", "")
            return f"🗑️  删除任务: {tid}"
        elif action == "list":
            return "📋 列出任务"
        elif action == "clear":
            return "🧹 清空任务"
    
    return f"🔧 {task_type}"


def format_observation_display(observation: str) -> str:
    """
    格式化工具执行结果的显示
    检测到指令前缀时使用友好格式输出
    
    Args:
        observation: 原始观察结果字符串
        
    Returns:
        格式化后的显示字符串
    """
    # 检测常见的指令前缀并替换为友好格式
    lines = observation.split('\n')
    formatted_lines = []
    
    for line in lines:
        # SUCCESS/FAILURE 前缀
        if line.startswith("SUCCESS:"):
            content = line[8:].strip()
            
            # 特殊处理不同类型的成功消息
            if "Read" in content and "Lines:" in content:
                # 读取文件成功
                formatted_lines.append(f"{Fore.GREEN}✓ {content}{Style.RESET_ALL}")
            elif "Saved to" in content or "Edited" in content:
                # 保存/编辑文件成功
                formatted_lines.append(f"{Fore.GREEN}✓ {content}{Style.RESET_ALL}")
            elif "Found" in content and "files" in content:
                # 搜索文件成功
                formatted_lines.append(f"{Fore.GREEN}✓ {content}{Style.RESET_ALL}")
            elif "Command" in content:
                # 命令执行成功
                formatted_lines.append(f"{Fore.GREEN}✓ {content}{Style.RESET_ALL}")
            else:
                formatted_lines.append(f"{Fore.GREEN}✓ {content}{Style.RESET_ALL}")
        
        elif line.startswith("FAILURE:"):
            content = line[8:].strip()
            formatted_lines.append(f"{Fore.RED}✗ {content}{Style.RESET_ALL}")
        
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


def print_tool_execution_header(task: Dict[str, Any], index: int, total: int) -> None:
    """
    打印工具执行的头部信息
    
    Args:
        task: 工具任务字典
        index: 当前任务索引（从1开始）
        total: 总任务数
    """
    display_text = format_tool_display(task)
    print(f"\n{Style.BRIGHT}[{index}/{total}] {display_text}{Style.RESET_ALL}")

