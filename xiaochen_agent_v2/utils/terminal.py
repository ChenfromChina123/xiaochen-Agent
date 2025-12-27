import subprocess
import threading
import time
import os
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from .console import Fore, Style

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

class TerminalManager:
    """
    管理多个终端进程，支持长期停留（非阻塞）和短期停留（阻塞）任务。
    """
    def __init__(self):
        self.terminals: Dict[str, TerminalProcess] = {}

    def run_command(self, command: str, is_long_running: bool = False, cwd: Optional[str] = None) -> Tuple[bool, str, str, str]:
        """
        执行指令。
        :param command: 要执行的命令
        :param is_long_running: 是否为长期停留任务（如 web 服务）
        :param cwd: 工作目录
        :return: (是否成功启动/执行, 终端ID, 输出结果, 错误信息)
        """
        tid = str(uuid.uuid4())[:8]
        
        try:
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
                universal_newlines=True
            )

            term = TerminalProcess(
                id=tid,
                command=command,
                process=proc,
                is_long_running=is_long_running
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
                        output = f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                        del self.terminals[tid]
                        return False, tid, output, f"Process exited early with code {proc.returncode}"
                    time.sleep(0.5)

                # 10 秒后仍然存活，返回已捕获的部分输出
                initial_output = "".join(term.output)
                return True, tid, f"Initial Output (10s):\n{initial_output}", ""
            else:
                # 短期任务：等待执行完毕并捕获输出
                try:
                    stdout, stderr = proc.communicate(timeout=120)
                    term.exit_code = proc.returncode
                    output = f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                    del self.terminals[tid]
                    if proc.returncode == 0:
                        return True, tid, output, ""
                    else:
                        return False, tid, output, f"Exit Code: {proc.returncode}"
                except subprocess.TimeoutExpired:
                    term.is_long_running = True
                    start_monitor()
                    time.sleep(0.2)
                    initial_output = "".join(term.output)
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
            for t in threads:
                t.join(timeout=0.2)
        except Exception:
            pass

    def get_terminal_status(self, tid: str) -> Optional[Dict[str, Any]]:
        """获取指定终端的状态和最新输出。"""
        if tid not in self.terminals:
            return None
        
        term = self.terminals[tid]
        return {
            "id": term.id,
            "command": term.command,
            "is_running": term.process.poll() is None,
            "exit_code": term.exit_code,
            "output": "".join(term.output[-50:]) # 返回最后50行输出
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
