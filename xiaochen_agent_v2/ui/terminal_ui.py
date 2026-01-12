"""
终端UI模块 - 使用 rich 库提供高级终端界面
"""
import time
import sys
from typing import Optional, List, Dict, Any

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


class TerminalUI:
    """高级终端UI管理器"""
    
    def __init__(self):
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
    
    def is_available(self) -> bool:
        """检查 rich 是否可用"""
        return RICH_AVAILABLE
    
    def print_info(self, message: str):
        """打印信息"""
        if self.console:
            self.console.print(f"[cyan]ℹ {message}[/cyan]")
        else:
            print(f"ℹ {message}")
    
    def print_success(self, message: str):
        """打印成功信息"""
        if self.console:
            self.console.print(f"[green]✓ {message}[/green]")
        else:
            print(f"✓ {message}")
    
    def print_error(self, message: str):
        """打印错误信息"""
        if self.console:
            self.console.print(f"[red]✗ {message}[/red]")
        else:
            print(f"✗ {message}")
    
    def print_warning(self, message: str):
        """打印警告信息"""
        if self.console:
            self.console.print(f"[yellow]⚠ {message}[/yellow]")
        else:
            print(f"⚠ {message}")
    
    def show_process_table(self, processes: List[Dict[str, Any]]):
        """显示进程表格"""
        if not self.console:
            # 降级到简单输出
            print("\n正在运行的进程:")
            print("=" * 80)
            for p in processes:
                uptime = int(p['uptime'])
                print(f"[{p['id']}] {p['command'][:50]}")
                print(f"  PID: {p['pid']} | 运行时间: {uptime}s | 类型: {'长期' if p.get('is_long_running') else '短期'}")
            print("=" * 80)
            return
        
        # 使用 rich 表格
        table = Table(title="正在运行的进程", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        
        table.add_column("终端ID", style="yellow", width=10)
        table.add_column("命令", style="white", width=40)
        table.add_column("PID", style="cyan", width=8)
        table.add_column("类型", style="magenta", width=6)
        table.add_column("运行时间", style="green", width=12)
        table.add_column("状态", style="bold green", width=10)
        
        for p in processes:
            uptime = int(p['uptime'])
            if uptime < 60:
                uptime_str = f"{uptime}s"
            elif uptime < 3600:
                uptime_str = f"{uptime // 60}m {uptime % 60}s"
            else:
                uptime_str = f"{uptime // 3600}h {(uptime % 3600) // 60}m"
            
            proc_type = "长期" if p.get('is_long_running') else "短期"
            status = "[green]RUNNING[/green]" if p.get('is_running') else "[red]STOPPED[/red]"
            
            table.add_row(
                p['id'],
                p['command'][:40] + ("..." if len(p['command']) > 40 else ""),
                str(p['pid']),
                proc_type,
                uptime_str,
                status
            )
        
        self.console.print()
        self.console.print(table)
        self.console.print()
        self.console.print("[cyan]💡 提示: 使用 'watch <id>' 实时监控进程输出[/cyan]")
        self.console.print()
    
    def watch_process(self, terminal_process, terminal_id: str, max_duration: int = 300):
        """
        实时监控进程输出
        
        Args:
            terminal_process: TerminalProcess 对象
            terminal_id: 终端ID
            max_duration: 最大监控时长（秒）
        """
        if not self.console:
            # 降级到简单输出
            self._watch_process_simple(terminal_process, terminal_id, max_duration)
            return
        
        # 使用 rich Live Display
        try:
            start_time = time.time()
            last_line_count = len(terminal_process.output)
            
            # 创建布局
            layout = Layout()
            layout.split(
                Layout(name="header", size=7),
                Layout(name="output")
            )
            
            with Live(layout, refresh_per_second=4, screen=False) as live:
                while terminal_process.process.poll() is None:
                    # 检查超时
                    elapsed = time.time() - start_time
                    if elapsed > max_duration:
                        self.console.print()
                        self.print_warning(f"监控超时（{max_duration}秒），自动退出")
                        self.print_info(f"进程仍在运行，使用 'watch {terminal_id}' 继续监控")
                        break
                    
                    # 更新头部
                    uptime = int(elapsed)
                    header_text = Text()
                    header_text.append("实时监控\n", style="bold cyan")
                    header_text.append(f"终端ID: {terminal_id} | ", style="yellow")
                    header_text.append(f"PID: {terminal_process.process.pid} | ", style="cyan")
                    header_text.append(f"监控时长: {uptime}s\n", style="green")
                    header_text.append(f"命令: {terminal_process.command}\n", style="white")
                    header_text.append("按 Ctrl+C 退出", style="dim")
                    
                    layout["header"].update(Panel(header_text, border_style="cyan"))
                    
                    # 更新输出区域
                    output_lines = terminal_process.output[-30:]  # 显示最近30行
                    output_text = "\n".join(line.rstrip() for line in output_lines)
                    
                    if len(terminal_process.output) > last_line_count:
                        # 有新输出
                        last_line_count = len(terminal_process.output)
                    
                    if output_text:
                        layout["output"].update(Panel(output_text, title="输出", border_style="green"))
                    else:
                        layout["output"].update(Panel("[dim](暂无输出)[/dim]", title="输出", border_style="yellow"))
                    
                    time.sleep(0.25)
                
                # 进程结束
                if terminal_process.process.poll() is not None:
                    self.console.print()
                    self.print_warning(f"进程已结束 | 退出码: {terminal_process.exit_code}")
                    
        except KeyboardInterrupt:
            self.console.print()
            self.print_info("已退出监控模式（进程仍在运行）")
        except Exception as e:
            self.console.print()
            self.print_error(f"监控出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _watch_process_simple(self, terminal_process, terminal_id: str, max_duration: int):
        """简单模式的进程监控（不使用 rich）"""
        print("\n" + "=" * 80)
        print(f"实时监控: {terminal_process.command}")
        print(f"终端ID: {terminal_id} | PID: {terminal_process.process.pid}")
        print("按 Ctrl+C 退出监控")
        print("=" * 80 + "\n")
        
        # 显示历史输出
        if terminal_process.output:
            print("=== 历史输出 (最近50行) ===")
            for line in terminal_process.output[-50:]:
                print(line.rstrip())
        
        print("\n=== 实时输出 ===")
        sys.stdout.flush()
        
        last_line_count = len(terminal_process.output)
        start_time = time.time()
        
        try:
            while terminal_process.process.poll() is None:
                # 检查超时
                if time.time() - start_time > max_duration:
                    print(f"\n监控超时（{max_duration}秒），自动退出")
                    print(f"提示: 使用 'watch {terminal_id}' 继续监控")
                    break
                
                # 检查新输出
                if len(terminal_process.output) > last_line_count:
                    for line in terminal_process.output[last_line_count:]:
                        print(line.rstrip())
                        sys.stdout.flush()
                    last_line_count = len(terminal_process.output)
                
                time.sleep(0.1)
            
            # 进程结束
            if terminal_process.process.poll() is not None:
                if len(terminal_process.output) > last_line_count:
                    for line in terminal_process.output[last_line_count:]:
                        print(line.rstrip())
                
                print("\n" + "=" * 80)
                print(f"进程已结束 | 退出码: {terminal_process.exit_code}")
                print("=" * 80 + "\n")
                
        except KeyboardInterrupt:
            print("\n已退出监控模式（进程仍在运行）\n")
    
    def show_panel(self, content: str, title: str, border_style: str = "cyan"):
        """显示面板"""
        if self.console:
            self.console.print(Panel(content, title=title, border_style=border_style))
        else:
            print(f"\n{'=' * 80}")
            print(f"{title}")
            print("=" * 80)
            print(content)
            print("=" * 80 + "\n")


# 全局实例
_terminal_ui = None

def get_terminal_ui() -> TerminalUI:
    """获取全局 TerminalUI 实例"""
    global _terminal_ui
    if _terminal_ui is None:
        _terminal_ui = TerminalUI()
    return _terminal_ui
