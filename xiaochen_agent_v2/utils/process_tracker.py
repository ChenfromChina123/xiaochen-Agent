import json
import os
import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    import psutil
except ImportError:
    psutil = None

from .files import get_logs_root
from .console import Fore, Style

@dataclass
class ProcessRecord:
    uuid: str
    command: str
    pid: int
    start_time: float
    status: str  # "running", "completed", "failed", "terminated"
    exit_code: Optional[int] = None
    cwd: str = ""
    platform: str = ""

class ProcessTracker:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProcessTracker, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.log_file = os.path.join(get_logs_root(), "process_tracker.json")
        self._ensure_log_file()

    def _ensure_log_file(self):
        if not os.path.exists(self.log_file):
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def _load_records(self) -> List[Dict[str, Any]]:
        try:
            if not os.path.exists(self.log_file):
                return []
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def _save_records(self, records: List[Dict[str, Any]]):
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_process(self, command: str, pid: int, proc_uuid: str, cwd: str = "") -> None:
        """记录新启动的进程"""
        records = self._load_records()
        
        record = ProcessRecord(
            uuid=proc_uuid,
            command=command,
            pid=pid,
            start_time=time.time(),
            status="running",
            cwd=cwd,
            platform=os.name
        )
        
        records.append(asdict(record))
        self._save_records(records)

    def update_status(self, proc_uuid: str, status: str, exit_code: Optional[int] = None) -> None:
        """更新进程状态"""
        records = self._load_records()
        updated = False
        for r in records:
            if r.get("uuid") == proc_uuid:
                r["status"] = status
                if exit_code is not None:
                    r["exit_code"] = exit_code
                updated = True
                break
        
        if updated:
            self._save_records(records)

    def get_running_processes(self) -> List[Dict[str, Any]]:
        """
        获取所有记录中状态为 running 的进程，并验证其实际存活状态。
        如果是 '假死' (记录显示 running 但实际已不存在或 UUID 不匹配)，则更新记录为 terminated。
        """
        if psutil is None:
            return []

        records = self._load_records()
        active_processes = []
        needs_save = False

        for r in records:
            if r.get("status") != "running":
                continue
            
            pid = r.get("pid")
            uuid_target = r.get("uuid")
            
            is_alive = False
            try:
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    # 验证状态，避免僵尸进程
                    if proc.status() == psutil.STATUS_ZOMBIE:
                        is_alive = False
                    else:
                        # 尝试验证 UUID
                        try:
                            environ = proc.environ()
                            if environ.get("XIAOCHEN_PROC_UUID") == uuid_target:
                                is_alive = True
                            else:
                                # PID 存在但 UUID 不匹配，说明是 PID 复用，原进程已死
                                is_alive = False
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            # 权限不足或进程刚消失
                            # 如果无法读取环境变量，保守起见，根据进程名辅助判断？
                            # 暂时认为如果不匹配或无法读取，则视为不可控，但在同一用户下通常能读
                            # 如果是 Windows，AccessDenied 比较常见，可以尝试匹配 command name
                            try:
                                cmdline = " ".join(proc.cmdline())
                                # 简单的命令包含检查
                                if r.get("command") in cmdline:
                                    is_alive = True
                            except:
                                pass
            except:
                is_alive = False

            if is_alive:
                # 补充实时信息
                try:
                    p = psutil.Process(pid)
                    r["cpu_percent"] = p.cpu_percent(interval=0.1)
                    r["memory_info"] = p.memory_info().rss / 1024 / 1024 # MB
                except:
                    pass
                active_processes.append(r)
            else:
                # 标记为 terminated (abnormal)
                r["status"] = "terminated_unknown"
                needs_save = True
        
        if needs_save:
            self._save_records(records)
            
        return active_processes

    def print_active_processes(self):
        """在控制台打印活跃进程摘要"""
        actives = self.get_running_processes()
        if not actives:
            return

        print(f"\n{Fore.MAGENTA}{'='*20} 后台 AI 进程监控 {'='*20}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}检测到 {len(actives)} 个正在运行的后台任务:{Style.RESET_ALL}")
        
        for p in actives:
            pid = p.get("pid")
            cmd = p.get("command")
            start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.get("start_time")))
            cpu = p.get("cpu_percent", 0)
            mem = p.get("memory_info", 0)
            
            print(f"{Fore.YELLOW}PID: {pid}{Style.RESET_ALL} | 启动时间: {start}")
            print(f"命令: {cmd}")
            print(f"资源: CPU {cpu:.1f}% | Mem {mem:.1f} MB")
            print(f"{'-'*60}")
        print("")
