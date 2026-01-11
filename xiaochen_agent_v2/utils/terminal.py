import subprocess
import threading
import time
import os
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from .console import Fore, Style
from .process_tracker import ProcessTracker

DEFAULT_MAX_TERMINAL_RETURN_CHARS = 2000

def clip_terminal_return_text(text: str, max_chars: int = DEFAULT_MAX_TERMINAL_RETURN_CHARS, terminal_id: Optional[str] = None) -> str:
    """
    将终端输出按字符数截断为"仅保留尾部"。

    Args:
        text: 原始输出文本
        max_chars: 最大保留字符数
        terminal_id: 终端ID，用于提示用户查看完整输出

    Returns:
        截断后的文本（若未超长则原样返回）
    """
    if not text:
        return ""
    max_chars = int(max_chars or 0)
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    removed = len(text) - max_chars
    tail = text[-max_chars:]
    
    hint = f"... (输出内容过长，为节省 token 已自动截断 {removed} 字符，仅保留末尾 {max_chars} 字符)"
    if terminal_id:
        hint += f"\n💡 提示：输入 'terminal {terminal_id}' 或 'logs {terminal_id}' 查看完整输出"
    
    return f"{hint}\n{tail}"

def clip_terminal_return_text_head_tail(
    text: str,
    max_chars: int = DEFAULT_MAX_TERMINAL_RETURN_CHARS,
    head_chars: int = 1200,
    terminal_id: Optional[str] = None
) -> str:
    """
    将终端输出截断为"保留少量头部 + 保留尾部"。

    适用于既要保留关键信息（头部如状态/标题），又要保留最新日志（尾部）的场景。

    Args:
        text: 原始输出文本
        max_chars: 最大保留字符数（总长度上限）
        head_chars: 头部保留字符数（不足时会自动调整以保障尾部最小长度）
        terminal_id: 终端ID，用于提示用户查看完整输出

    Returns:
        截断后的文本（若未超长则原样返回）
    """
    if not text:
        return ""
    max_chars = int(max_chars or 0)
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    marker = "\n... (输出内容过长，为节省 token 已自动截断，以下为末尾输出"
    if terminal_id:
        marker += f"，输入 'terminal {terminal_id}' 查看完整内容"
    marker += ")\n"
    
    if max_chars <= len(marker) + 1:
        return clip_terminal_return_text(text, max_chars=max_chars, terminal_id=terminal_id)

    head_chars = max(0, int(head_chars or 0))
    head_chars = min(head_chars, max_chars - len(marker) - 1)

    min_tail = 200
    if max_chars - head_chars - len(marker) < min_tail:
        head_chars = max(0, max_chars - len(marker) - min_tail)

    tail_chars = max_chars - head_chars - len(marker)
    tail = text[-tail_chars:] if tail_chars > 0 else ""
    return text[:head_chars] + marker + tail

@dataclass
class TerminalProcess:
    id: str
    command: str
    process: subprocess.Popen
    is_long_running: bool
    output: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    exit_code: Optional[int] = None
    thread: Optional[threading.Thread] = None
    proc_uuid: str = ""  # 全局唯一追踪ID

class TerminalManager:
    """
    管理多个终端进程，支持长期停留（非阻塞）和短期停留（阻塞）任务。
    """
    def __init__(self):
        self.terminals: Dict[str, TerminalProcess] = {}
        # Initialize output manager for storing full terminal outputs
        try:
            from ..core.terminal_output_manager import TerminalOutputManager
            self.output_manager = TerminalOutputManager()
        except Exception:
            self.output_manager = None
    
    def _save_output_to_storage(self, tid: str, command: str, cwd: str, stdout: str, stderr: str, exit_code: Optional[int], duration_ms: Optional[int] = None) -> None:
        """
        Save terminal output to storage manager
        
        Args:
            tid: Terminal ID
            command: Executed command
            cwd: Working directory
            stdout: Standard output
            stderr: Standard error
            exit_code: Exit code
            duration_ms: Duration in milliseconds
        """
        if self.output_manager:
            try:
                self.output_manager.save_output(
                    record_id=tid,
                    command=command,
                    cwd=cwd,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration_ms=duration_ms
                )
            except Exception:
                # Silently fail if storage fails
                pass

    def run_command(self, command: str, is_long_running: bool = False, cwd: Optional[str] = None) -> Tuple[bool, str, str, str]:
        """
        执行指令。
        :param command: 要执行的命令
        :param is_long_running: 是否为长期停留任务（如 web 服务）
        :param cwd: 工作目录
        :return: (是否成功启动/执行, 终端ID, 输出结果, 错误信息)
        """
        tid = str(uuid.uuid4())[:8]
        proc_uuid = str(uuid.uuid4())  # 用于进程追踪的唯一ID
        
        try:
            # 准备环境变量
            env = os.environ.copy()
            env["XIAOCHEN_PROC_UUID"] = proc_uuid

            # 统一使用 shell 执行，并设置编码为 utf-8 以避免 Windows 上的解码错误
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace', # 解码失败时替换字符，不抛出异常
                cwd=cwd or os.getcwd(),
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # 记录到全局追踪器
            ProcessTracker().add_process(command, proc.pid, proc_uuid, cwd or os.getcwd())

            term = TerminalProcess(
                id=tid,
                command=command,
                process=proc,
                is_long_running=is_long_running,
                proc_uuid=proc_uuid
            )
            self.terminals[tid] = term

            def start_monitor() -> None:
                if term.thread and term.thread.is_alive():
                    return
                term.thread = threading.Thread(target=self._monitor_process, args=(term,), daemon=True)
                term.thread.start()

            if is_long_running:
                start_monitor()

                # 等待 10 秒观察进程状态
                wait_seconds = 10
                start_wait = time.time()
                while time.time() - start_wait < wait_seconds:
                    if proc.poll() is not None:
                        # 进程在 10 秒内提前结束，说明启动失败或瞬时任务
                        stdout, stderr = proc.communicate()
                        term.exit_code = proc.returncode
                        duration_ms = int((time.time() - term.start_time) * 1000)
                        ProcessTracker().update_status(proc_uuid, "failed" if proc.returncode != 0 else "completed", proc.returncode)
                        
                        # Save full output to storage
                        self._save_output_to_storage(tid, command, cwd or os.getcwd(), stdout, stderr, proc.returncode, duration_ms)
                        
                        output = clip_terminal_return_text(f"Stdout:\n{stdout}\nStderr:\n{stderr}", terminal_id=tid)
                        del self.terminals[tid]
                        return False, tid, output, f"Process exited early with code {proc.returncode}"
                    time.sleep(0.5)

                # 10 秒后仍然存活，返回已捕获的部分输出
                initial_output = clip_terminal_return_text("".join(term.output))
                return True, tid, f"Initial Output (10s):\n{initial_output}", ""
            else:
                # 短期任务：等待执行完毕并捕获输出
                try:
                    stdout, stderr = proc.communicate(timeout=120)
                    term.exit_code = proc.returncode
                    duration_ms = int((time.time() - term.start_time) * 1000)
                    ProcessTracker().update_status(proc_uuid, "completed" if proc.returncode == 0 else "failed", proc.returncode)
                    
                    # Save full output to storage
                    self._save_output_to_storage(tid, command, cwd or os.getcwd(), stdout, stderr, proc.returncode, duration_ms)
                    
                    output = clip_terminal_return_text(f"Stdout:\n{stdout}\nStderr:\n{stderr}", terminal_id=tid)
                    del self.terminals[tid]
                    if proc.returncode == 0:
                        return True, tid, output, ""
                    else:
                        return False, tid, output, f"Exit Code: {proc.returncode}"
                except subprocess.TimeoutExpired:
                    term.is_long_running = True
                    start_monitor()
                    time.sleep(0.2)
                    initial_output = clip_terminal_return_text("".join(term.output))
                    output = (
                        "Status: running (timeout, may be waiting for input)\n"
                        f"Initial Output:\n{initial_output}"
                    )
                    return True, tid, output, ""

        except Exception as e:
            return False, tid, "", str(e)

    def _monitor_process(self, term: TerminalProcess) -> None:
        """监控长期任务，异步读取 stdout/stderr 并在结束时记录退出码。"""
        try:
            def reader(stream, prefix: str) -> None:
                try:
                    for line in iter(stream.readline, ""):
                        if not line:
                            break
                        term.output.append(f"{prefix}{line}")
                        if len(term.output) > 1000:
                            term.output.pop(0)
                except Exception:
                    return

            threads: List[threading.Thread] = []
            if term.process.stdout is not None:
                t1 = threading.Thread(target=reader, args=(term.process.stdout, ""), daemon=True)
                threads.append(t1)
                t1.start()
            if term.process.stderr is not None:
                t2 = threading.Thread(target=reader, args=(term.process.stderr, "[stderr] "), daemon=True)
                threads.append(t2)
                t2.start()

            term.process.wait()
            term.exit_code = term.process.returncode
            
            # 进程结束，更新追踪状态
            status = "completed" if term.exit_code == 0 else "failed"
            ProcessTracker().update_status(term.proc_uuid, status, term.exit_code)
            
            for t in threads:
                t.join(timeout=0.2)
        except Exception:
            pass

    def get_terminal_status(self, tid: str) -> Optional[Dict[str, Any]]:
        """获取指定终端的状态和最新输出。"""
        if tid not in self.terminals:
            return None
        
        term = self.terminals[tid]
        output = clip_terminal_return_text("".join(term.output[-50:]))
        return {
            "id": term.id,
            "command": term.command,
            "is_running": term.process.poll() is None,
            "exit_code": term.exit_code,
            "output": output
        }

    def stop_terminal(self, tid: str) -> bool:
        """停止并移除指定终端。"""
        if tid not in self.terminals:
            return False
        
        term = self.terminals[tid]
        try:
            if term.process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(f"taskkill /F /T /PID {term.process.pid}", shell=True, capture_output=True)
                else:
                    term.process.terminate()
            del self.terminals[tid]
            return True
        except Exception:
            return False

    def list_terminals(self) -> List[Dict[str, Any]]:
        """列出所有正在运行的长期任务终端。"""
        return [
            {
                "id": t.id,
                "command": t.command,
                "uptime": time.time() - t.start_time,
                "is_running": t.process.poll() is None
            }
            for t in self.terminals.values() if t.is_long_running
        ]
