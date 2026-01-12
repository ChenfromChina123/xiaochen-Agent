import subprocess
import threading
import time
import os
import sys
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
        text: 原始文本
        max_chars: 最大保留字符数
        terminal_id: 终端ID，用于提示用户查看完整输出
    
    Returns:
        截断后的文本
    """
    if len(text) <= max_chars:
        return text
    removed = len(text) - max_chars
    tail = text[-max_chars:]
    
    hint = ""
    if terminal_id:
        hint = f"\n💡 提示：输入 'terminal {terminal_id}' 或 'logs {terminal_id}' 查看完整输出"
    
    return f"... (输出内容过长，为节省 token 已自动截断 {removed} 字符，仅保留末尾 {max_chars} 字符){hint}\n{tail}"

def clip_terminal_return_text_head_tail(text: str, max_chars: int = DEFAULT_MAX_TERMINAL_RETURN_CHARS) -> str:
    """
    将终端输出按字符数截断为"保留头部+尾部"。
    
    Args:
        text: 原始文本
        max_chars: 最大保留字符数
    
    Returns:
        截断后的文本（前一半 + 省略提示 + 后一半）
    """
    if len(text) <= max_chars:
        return text
    removed = len(text) - max_chars
    half = max_chars // 2
    head = text[:half]
    tail = text[-half:]
    return f"{head}\n\n... (输出内容过长，为节省 token 已自动截断 {removed} 字符，保留头尾各 {half} 字符)\n💡 提示：查看具体终端 ID 的完整输出，使用 'terminal <id>' 命令\n\n{tail}"

def format_duration(seconds: float) -> str:
    """
    将秒数格式化为友好的时间字符串
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化后的字符串，如 "2m 30s" 或 "1h 5m"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"

@dataclass
class TerminalProcess:
    id: str
    command: str
    process: subprocess.Popen
    is_long_running: bool = False
    output: list = field(default_factory=list)
    exit_code: Optional[int] = None
    start_time: float = field(default_factory=time.time)
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
                        term.output.append(f"{prefix}: {line}")
                except Exception:
                    pass

            stdout_thread = threading.Thread(target=reader, args=(term.process.stdout, "stdout"), daemon=True)
            stderr_thread = threading.Thread(target=reader, args=(term.process.stderr, "stderr"), daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            term.process.wait()
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            term.exit_code = term.process.returncode
            
            # 更新进程追踪器
            ProcessTracker().update_status(term.proc_uuid, "completed" if term.exit_code == 0 else "failed", term.exit_code)
            
            # Save full output when process completes
            stdout_lines = [line.replace("stdout: ", "") for line in term.output if line.startswith("stdout: ")]
            stderr_lines = [line.replace("stderr: ", "") for line in term.output if line.startswith("stderr: ")]
            stdout_text = "".join(stdout_lines)
            stderr_text = "".join(stderr_lines)
            duration_ms = int((time.time() - term.start_time) * 1000)
            self._save_output_to_storage(
                term.id, 
                term.command, 
                os.getcwd(), 
                stdout_text, 
                stderr_text, 
                term.exit_code,
                duration_ms
            )
        except Exception:
            pass

    def get_terminal_status(self, tid: str) -> Optional[Dict[str, Any]]:
        """获取指定 Terminal 的状态。"""
        term = self.terminals.get(tid)
        if not term:
            return None
        is_running = term.process.poll() is None
        return {
            "id": term.id,
            "command": term.command,
            "is_running": is_running,
            "exit_code": term.exit_code,
            "uptime": time.time() - term.start_time
        }

    def send_signal_to_terminal(self, tid: str, sig: int = 2) -> bool:
        """向指定 Terminal 发送信号（Windows 默认仅支持 SIGTERM）。"""
        term = self.terminals.get(tid)
        if not term:
            return False
        try:
            term.process.send_signal(sig)
            return True
        except Exception:
            return False

    def list_terminals(self) -> List[Dict[str, Any]]:
        """列出所有正在运行的终端进程（包括长期和短期任务）。"""
        result = []
        for t in self.terminals.values():
            is_alive = t.process.poll() is None
            # 只显示仍在运行的进程
            if is_alive:
                result.append({
                    "id": t.id,
                    "command": t.command,
                    "uptime": time.time() - t.start_time,
                    "is_running": True,
                    "pid": t.process.pid,
                    "proc_uuid": t.proc_uuid,
                    "is_long_running": t.is_long_running
                })
        return result
    
    def kill_terminal(self, tid: str, force: bool = False) -> Tuple[bool, str]:
        """
        终止指定的终端进程
        
        Args:
            tid: 终端ID
            force: 是否强制终止（Windows 上使用 taskkill /F）
        
        Returns:
            (是否成功, 消息)
        """
        if tid not in self.terminals:
            return False, f"Terminal {tid} not found"
        
        term = self.terminals[tid]
        
        try:
            if term.process.poll() is not None:
                # 进程已经结束
                del self.terminals[tid]
                return True, f"Terminal {tid} was already terminated"
            
            # 尝试终止进程
            if force:
                # 强制终止（包括子进程）
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(term.process.pid)], 
                                      capture_output=True, timeout=5)
                    else:
                        term.process.kill()
                except Exception:
                    term.process.kill()
            else:
                # 优雅终止
                term.process.terminate()
            
            # 等待进程结束
            try:
                term.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 超时则强制终止
                term.process.kill()
                term.process.wait(timeout=2)
            
            # 更新追踪器
            ProcessTracker().update_status(term.proc_uuid, "killed", -1)
            
            # 清理
            del self.terminals[tid]
            return True, f"Terminal {tid} terminated successfully"
        
        except Exception as e:
            return False, f"Failed to terminate terminal {tid}: {str(e)}"
    
    def kill_all_terminals(self) -> Tuple[int, int]:
        """
        终止所有正在运行的终端进程
        
        Returns:
            (成功数量, 失败数量)
        """
        success = 0
        failed = 0
        
        terminal_ids = list(self.terminals.keys())
        for tid in terminal_ids:
            ok, _ = self.kill_terminal(tid, force=True)
            if ok:
                success += 1
            else:
                failed += 1
        
        return success, failed
