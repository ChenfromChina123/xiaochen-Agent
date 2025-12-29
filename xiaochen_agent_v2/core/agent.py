import os
import platform
import re
import shutil
import subprocess
import sys
import time
import py_compile
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import requests
except Exception:
    requests = None

try:
    import urllib3
except Exception:
    urllib3 = None

from .config import Config
from ..utils.console import Fore, Style
from ..utils.display import format_tool_display, format_observation_display, print_tool_execution_header
from ..utils.files import (
    calculate_diff_of_lines,
    edit_lines,
    ensure_parent_dir,
    generate_dir_tree,
    generate_tree_structure,
    generate_match_tree,
    read_range,
    read_range_numbered,
    search_files,
    search_in_files,
    suggest_similar_patterns,
)
from ..utils.interrupt import InterruptHandler
from ..utils.logs import append_edit_history, append_usage_history, log_request, rollback_last_edit
from .metrics import CacheStats
from ..utils.tags import parse_stack_of_tags
from ..utils.terminal import TerminalManager


@dataclass
class TaskItem:
    id: str
    content: str
    status: str = "pending"
    progress: Optional[int] = None
    updated_at: float = field(default_factory=time.time)


class TaskManager:
    def __init__(self) -> None:
        self._counter = 0
        self._order: List[str] = []
        self._tasks: Dict[str, TaskItem] = {}

    def _normalize_status(self, status: Optional[str]) -> str:
        s = (status or "pending").strip().lower()
        if s in ("pending", "in_progress", "completed"):
            return s
        if s in ("doing", "inprogress", "in-progress", "in progress"):
            return "in_progress"
        if s in ("done", "finish", "finished"):
            return "completed"
        return "pending"

    def _normalize_progress(self, progress: Optional[int]) -> Optional[int]:
        if progress is None:
            return None
        try:
            p = int(progress)
        except Exception:
            return None
        if p < 0:
            return 0
        if p > 100:
            return 100
        return p

    def _next_id(self) -> str:
        self._counter += 1
        return f"T{self._counter}"

    def add(self, content: str, *, id: Optional[str] = None, status: Optional[str] = None, progress: Optional[int] = None) -> TaskItem:
        tid = (id or "").strip() or self._next_id()
        if tid in self._tasks:
            tid = self._next_id()
        item = TaskItem(
            id=tid,
            content=content.strip(),
            status=self._normalize_status(status),
            progress=self._normalize_progress(progress),
        )
        self._tasks[tid] = item
        self._order.append(tid)
        return item

    def update(
        self,
        id: str,
        *,
        content: Optional[str] = None,
        status: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> Optional[TaskItem]:
        tid = (id or "").strip()
        if not tid or tid not in self._tasks:
            return None
        item = self._tasks[tid]
        if content is not None and content.strip():
            item.content = content.strip()
        if status is not None and status.strip():
            item.status = self._normalize_status(status)
        if progress is not None:
            item.progress = self._normalize_progress(progress)
        item.updated_at = time.time()
        return item

    def delete(self, id: str) -> bool:
        tid = (id or "").strip()
        if not tid or tid not in self._tasks:
            return False
        del self._tasks[tid]
        self._order = [x for x in self._order if x != tid]
        return True

    def clear(self) -> None:
        self._tasks.clear()
        self._order.clear()
        self._counter = 0

    def summary(self) -> Tuple[int, int, int]:
        total = len(self._order)
        done = 0
        doing = 0
        for tid in self._order:
            t = self._tasks.get(tid)
            if not t:
                continue
            if t.status == "completed":
                done += 1
            elif t.status == "in_progress":
                doing += 1
        return total, done, doing

    def render(self) -> str:
        total, done, doing = self.summary()
        lines = [f"Tasks: {done}/{total} completed | {doing} in_progress"]
        for tid in self._order:
            t = self._tasks.get(tid)
            if not t:
                continue
            prog = "" if t.progress is None else f" {t.progress}%"
            lines.append(f"- ({t.id}) [{t.status}{prog}] {t.content}")
        return "\n".join(lines)

class Agent:
    def __init__(self, config: Config):
        self.config = config
        if not self.config.verifySsl and urllib3 is not None:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.historyOfMessages: List[Dict[str, str]] = []
        self.endpointOfChat = f"{self.config.baseUrl.rstrip('/')}/chat/completions"
        self.historyOfOperations: List[Tuple[str, int, int]] = []
        self.cacheOfBackups: Dict[str, str] = {}
        self.cacheOfSystemMessage: Optional[Dict[str, str]] = None
        self.statsOfCache = CacheStats()
        self.terminalManager = TerminalManager()
        self.cacheOfProjectTree: Optional[str] = None
        self.cacheOfUserRules: Optional[str] = None
        self.taskManager = TaskManager()
        self.lastFullMessages: List[Dict[str, str]] = []
        self.isAutoApproveEnabled = False
        self._lastOperationIndexOfLastChat = 0
        self._lastPrintedOperationIndex = 0
        self._chatMarkers: List[Tuple[int, int]] = []
        self.interruptHandler = InterruptHandler()
        self.readIndentMode = "header"
        self.pythonValidateRuff = "auto"
        self._cachedRuffRunner: Optional[List[str]] = None
        self._recentReadCache: Dict[Tuple[str, int, int], Tuple[float, float]] = {}

    def _require_requests(self) -> bool:
        """
        检查 requests 依赖是否可用。

        Returns:
            是否可用
        """
        return requests is not None

    def _detect_ruff_runner(self) -> Optional[List[str]]:
        """
        探测 ruff 可用的执行方式。

        Returns:
            - ["<path-to-ruff>"] 或 ["<python>", "-m", "ruff"]：ruff 可用
            - None：未安装或不可用（不引入强依赖时的默认行为）
        """
        setting = str(getattr(self, "pythonValidateRuff", "auto") or "auto").strip().lower()
        if setting in {"0", "false", "off", "no", "disable", "disabled"}:
            return None

        if self._cachedRuffRunner is not None:
            return self._cachedRuffRunner

        exe = shutil.which("ruff")
        if exe:
            self._cachedRuffRunner = [exe]
            return self._cachedRuffRunner

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "ruff", "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=2,
            )
            if proc.returncode == 0:
                self._cachedRuffRunner = [sys.executable, "-m", "ruff"]
                return self._cachedRuffRunner
        except Exception:
            pass

        self._cachedRuffRunner = None
        return None

    def _validate_python_file(self, path: str) -> Tuple[bool, str]:
        """
        校验 Python 文件的语法与风格（可选）。

        - 必跑：py_compile（语法/缩进错误能立即发现）
        - 可选：ruff check（若系统已安装 ruff，则自动启用；否则跳过）
        """
        try:
            py_compile.compile(path, doraise=True)
        except Exception:
            return False, traceback.format_exc(limit=2)

        runner = self._detect_ruff_runner()
        if not runner:
            return True, ""

        try:
            proc = subprocess.run(
                [*runner, "check", path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            if proc.returncode == 0:
                return True, ""
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            detail = "\n".join([x for x in [out, err] if x])
            return False, detail or "ruff check failed"
        except Exception:
            return False, traceback.format_exc(limit=2)

    def updateModelConfig(
        self,
        *,
        apiKey: Optional[str] = None,
        baseUrl: Optional[str] = None,
        modelName: Optional[str] = None,
        verifySsl: Optional[bool] = None,
    ) -> None:
        """
        运行时更新模型配置，并刷新依赖配置计算出的字段（如 chat/completions 端点）。

        Args:
            apiKey: 新的 API Key（可选）
            baseUrl: 新的 Base URL（可选）
            modelName: 新的模型名称（可选）
            verifySsl: 是否验证 SSL（可选）
        """
        if apiKey is not None and str(apiKey).strip():
            self.config.apiKey = str(apiKey).strip()
        if baseUrl is not None and str(baseUrl).strip():
            self.config.baseUrl = str(baseUrl).strip()
        if modelName is not None and str(modelName).strip():
            self.config.modelName = str(modelName).strip()
        if verifySsl is not None:
            self.config.verifySsl = bool(verifySsl)
            if not self.config.verifySsl and urllib3 is not None:
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.endpointOfChat = f"{self.config.baseUrl.rstrip('/')}/chat/completions"

    def estimateTokensOfMessages(self, messages: List[Dict[str, str]]) -> int:
        totalChars = 0
        for msg in messages:
            totalChars += len(msg["role"]) + len(msg["content"]) + 8
        return int(totalChars / 3)

    def _get_token_threshold(self) -> int:
        raw = getattr(self.config, "tokenThreshold", 30000)
        try:
            return int(raw)
        except Exception:
            return 30000

    def _is_persistent_summary_message(self, msg: Dict[str, str]) -> bool:
        if not isinstance(msg, dict):
            return False
        if msg.get("role") != "system":
            return False
        content = str(msg.get("content") or "")
        return content.startswith("【长期摘要】")

    def _extract_persistent_summary_text(self, content: str) -> str:
        text = str(content or "")
        if not text.startswith("【长期摘要】"):
            return text.strip()
        text = text[len("【长期摘要】") :]
        if text.startswith("\n"):
            text = text[1:]
        return text.strip()

    def _format_messages_for_summary(self, messages: List[Dict[str, str]]) -> str:
        parts: List[str] = []
        for m in messages:
            role = str(m.get("role") or "")
            content = str(m.get("content") or "")
            parts.append(f"[{role}]\n{content}")
        return "\n\n".join(parts)

    def _generate_summary_via_model(self, text: str) -> str:
        if not self._require_requests():
            return ""
        headers = {"Authorization": f"Bearer {self.config.apiKey}", "Content-Type": "application/json"}
        payload = {
            "model": self.config.modelName,
            "messages": [
                {
                    "role": "system",
                    "content": "你是对话历史压缩器。请把输入内容压缩为可长期缓存的摘要，保留关键需求、已做决策/改动点、重要约束、未完成事项与当前状态。输出用中文，条目化，简洁准确，不要编造。",
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
            "stream": False,
            "max_tokens": 1200,
        }
        try:
            resp = requests.post(
                self.endpointOfChat,
                headers=headers,
                json=payload,
                timeout=120,
                verify=self.config.verifySsl,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                return ""
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            content = (msg.get("content") if isinstance(msg, dict) else "") or ""
            return str(content).strip()
        except Exception:
            return ""

    def _maybe_compact_history(
        self,
        history_working: List[Dict[str, str]],
        msg_system: Dict[str, str],
        *,
        keep_last_messages: int = 10,
    ) -> Tuple[List[Dict[str, str]], bool]:
        threshold = self._get_token_threshold()
        if threshold <= 0:
            return history_working, False

        try:
            estimate = self.estimateTokensOfMessages([msg_system] + list(history_working))
        except Exception:
            estimate = 0
        if estimate < threshold:
            return history_working, False

        summary_msg: Optional[Dict[str, str]] = None
        rest = list(history_working)
        if rest and self._is_persistent_summary_message(rest[0]):
            summary_msg = rest[0]
            rest = rest[1:]

        if len(rest) <= keep_last_messages:
            return history_working, False

        keep = rest[-keep_last_messages:]
        to_summarize = rest[:-keep_last_messages]
        existing = self._extract_persistent_summary_text(summary_msg.get("content") if summary_msg else "")
        pieces: List[str] = []
        if existing:
            pieces.append("现有摘要:\n" + existing)
        pieces.append("需要合并的新内容:\n" + self._format_messages_for_summary(to_summarize))
        summary_text = self._generate_summary_via_model("\n\n".join(pieces))
        if not summary_text.strip():
            return history_working, False

        new_summary_msg = {"role": "system", "content": "【长期摘要】\n" + summary_text.strip()}
        new_history = [new_summary_msg] + keep
        return new_history, True

    def isTaskWhitelisted(self, t: Dict[str, Any]) -> bool:
        """判断该工具调用是否在白名单中，可自动执行而无需用户批准。"""
        if t["type"] in (self.config.whitelistedTools or []):
            return True
        if t["type"] == "run_command":
            cmd_first = str(t.get("command", "")).strip().splitlines()[:1]
            baseCmd = cmd_first[0].split()[0] if cmd_first and cmd_first[0] else ""
            base_lower = baseCmd.strip().lower()
            allowed = {str(c).strip().lower() for c in (self.config.whitelistedCommands or []) if str(c).strip()}
            if base_lower and base_lower in allowed:
                return True
        return False

    def summarizeTask(self, t: Dict[str, Any]) -> str:
        """将单个任务压缩为一行摘要，便于批量批准时展示。"""
        # 使用新的友好格式显示
        return format_tool_display(t)

    def confirmBatchExecution(self, tasks: List[Dict[str, Any]]) -> Tuple[bool, bool]:
        """对一批任务进行一次性批准：y=本批次执行，a=后续批次也自动批准，n=取消。"""
        needsApproval = [t for t in tasks if not self.isTaskWhitelisted(t)]
        if not needsApproval:
            return True, False
        if self.isAutoApproveEnabled:
            return True, True

        print(f"{Style.BRIGHT}===== Pending Tasks ({len(tasks)}) ====={Style.RESET_ALL}")
        for i, t in enumerate(tasks, start=1):
            flag = "AUTO" if self.isTaskWhitelisted(t) else "ASK"
            print(f"{i:>2}. [{flag}] {self.summarizeTask(t)}")
        print(f"{Style.BRIGHT}==========================={Style.RESET_ALL}")

        ans = input(f"{Style.BRIGHT}Execute all tasks once? (y=once / a=always / n=cancel): {Style.RESET_ALL}").strip().lower()
        if ans == "":
            ans = "y"
        if ans == "a":
            self.isAutoApproveEnabled = True
            return True, True
        if ans == "y":
            return True, True
        return False, False

    def renderRunningTerminals(self) -> str:
        """渲染正在运行的长期任务终端列表，便于用户及时查看和处理。"""
        terminals = self.terminalManager.list_terminals()
        if not terminals:
            return ""
        lines = ["Running Terminals:"]
        for t in terminals:
            uptime = float(t.get("uptime") or 0.0)
            cmd = str(t.get("command") or "")
            tid = str(t.get("id") or "")
            is_running = bool(t.get("is_running"))
            lines.append(f"- id={tid} running={is_running} uptime={uptime:.1f}s cmd={cmd}")
        return "\n".join(lines)

    def printRunCommandSummary(self, *, tid: str, cmd: str, success: bool, output: str, error: str) -> None:
        """将 run_command 的关键信息直接打印给用户，便于及时查看终端状态与输出。"""
        # 不在这里打印输出，避免重复显示
        # 输出已经在 observations 中返回给 AI，不需要再显示给用户
        return
        summary = self.renderRunningTerminals()
        if summary:
            print(f"{Style.BRIGHT}{summary}{Style.RESET_ALL}")

    def getContextOfSystem(self) -> str:
        return """# XIAOCHEN_TERMINAL - 小晨终端助手
## 🔴 VOID RULES (STRICT ADHERENCE REQUIRED)
1. **PROJECT AWARENESS**: Before making assumptions, explore the project structure.
2. **PASSIVE VALIDATION**: Do NOT execute commands blindly. You must PROPOSE actions. The user validates.
3. **SEARCH FIRST**: When looking for code, prefer searching file contents.
4. **MULTI TASKS ALLOWED**: You may output multiple closed tags per reply; they will be executed in order.
5. **NO HALLUCINATION**: If a tool returns no results, try different patterns/paths.
6. **NO TASK = NO TAGS**: Reply with natural language only if no action is needed.
7. **FOCUS FIRST**: Only do what the user explicitly asked.
8. **STOP AFTER TASK**: After completing the requested task(s), respond briefly.
9. **EDIT > REWRITE**: If a file already exists, prefer <edit_lines> and avoid rewriting the whole file.

## 📋 USER CONTEXT
- User rules, current directory, and task list are provided in the user message to keep this system prompt stable for caching.

## 🧩 TOOL TAGS (CLOSED TAGS ONLY)
- Search files:
  <search_files><pattern>**/*.py</pattern></search_files>
- Search in files:
  <search_in_files><regex>...</regex><glob>**/*.py</glob><root>.</root><max_matches>200</max_matches></search_in_files>
- Read file:
  <read_file><path>...</path><start_line>1</start_line><end_line>160</end_line></read_file>
  - You MUST always provide start_line and end_line. Keep the window small (<=160 lines). Prefer search_in_files first, then read only the needed slice. Duplicate reads may be skipped.
  - Python 缩进显示默认使用 header 模式：只在内容开头输出一次 indent_style/indent_size/mixed；空白行显示为 <WS_ONLY>。
- Write file:
  <write_file><path>...</path><content>...</content><overwrite>false</overwrite></write_file>
  - Use write_file ONLY for new files. If the target file already exists, you MUST use edit_lines, unless overwrite=true is explicitly set.
- Edit lines:
  <edit_lines><path>...</path><delete_start>10</delete_start><delete_end>20</delete_end><insert_at>10</insert_at><auto_indent>true</auto_indent><content>...</content></edit_lines>
  - insert_at refers to original line numbers; the tool handles offsets.
  - auto_indent aligns inserted Python code to surrounding indentation.
- Search/Replace:
  <replace_in_file><path>...</path><search>...</search><replace>...</replace><count>1</count><regex>false</regex><auto_indent>true</auto_indent></replace_in_file>
- Run command:
  <run_command><command>...</command><is_long_running>false</is_long_running><cwd>.</cwd></run_command>
- Task list:
  <task_add><content>...</content><status>pending</status></task_add>
  <task_update><id>T1</id><status>in_progress</status></task_update>
  <task_list></task_list> <task_delete><id>T1</id></task_delete> <task_clear></task_clear>
"""

    def _invalidate_read_cache_for_path(self, path: str) -> None:
        remove_keys = [k for k in self._recentReadCache.keys() if k[0] == path]
        for k in remove_keys:
            self._recentReadCache.pop(k, None)

    def invalidateProjectTreeCache(self) -> None:
        """使项目树缓存失效（下次构造 user 上下文时会重新生成）。"""
        self.cacheOfProjectTree = None

    def invalidateUserRulesCache(self) -> None:
        """使 userrules 缓存失效（下次构造 user 上下文时会重新读取）。"""
        self.cacheOfUserRules = None

    def getUserRulesCached(self) -> str:
        """读取并缓存 userrules 内容；仅在缓存失效后才重新读取。"""
        if self.cacheOfUserRules is not None:
            return self.cacheOfUserRules

        contentOfRules = ""
        cwd = os.getcwd()
        pathOfRules = os.path.join(cwd, "userrules")
        if os.path.exists(pathOfRules):
            try:
                with open(pathOfRules, "r", encoding="utf-8") as f:
                    contentOfRules = f.read().strip()
            except Exception:
                contentOfRules = ""
        self.cacheOfUserRules = contentOfRules
        return self.cacheOfUserRules

    def getProjectTreeCached(self) -> str:
        """生成并缓存项目树；仅在缓存失效（例如写入/编辑文件）后才重新生成。"""
        if self.cacheOfProjectTree is not None:
            return self.cacheOfProjectTree

        cwd = os.getcwd()
        treeOfCwd = ""
        try:
            treeOfCwd = generate_dir_tree(cwd, max_depth=3, max_entries=300)
        except Exception:
            treeOfCwd = f"{cwd}/"

        self.cacheOfProjectTree = treeOfCwd
        return self.cacheOfProjectTree

    def printToolResult(self, text: str, maxChars: int = 8000) -> None:
        """
        打印工具执行结果的关键摘要。

        仅输出失败信息与少量关键成功摘要，避免 read_file 等内容刷屏。
        """
        if not text:
            return
        head = text[:maxChars]
        first_line = head.splitlines()[:1]
        first_line = first_line[0] if first_line else head

        if first_line.startswith("FAILURE:"):
            print(format_observation_display("\n".join(head.splitlines()[:12])))
            return
        if first_line.startswith("SUCCESS: Command"):
            print(format_observation_display("\n".join(head.splitlines()[:8])))
            return
        if first_line.startswith("SUCCESS: Edited") or first_line.startswith("SUCCESS: Saved to"):
            print(format_observation_display(first_line))
            return

    def printTaskProgress(self) -> None:
        content = self.taskManager.render()
        print(f"{Style.BRIGHT}===== TASKS ====={Style.RESET_ALL}")
        print(content)
        print(f"{Style.BRIGHT}================={Style.RESET_ALL}")

    def getContextOfCurrentUser(self, inputOfUser: str) -> str:
        """返回 User 上下文。"""
        cwd = os.getcwd()
        rulesBlock = self.getUserRulesCached() or ""
        rules_str = ""
        if rulesBlock:
            rules_str = f"\n\n## 📋 USER RULES\n```text\n{rulesBlock}\n```"
        # 获取任务清单状态
        task_str = ""
        if self.taskManager._tasks:
            task_str = f"\n\n## 📋 CURRENT TASKS\n{self.taskManager.render()}"

        # 获取一级目录列表作为提示，但不展示完整树
        try:
            top_items = os.listdir(cwd)
            dirs = [d for d in top_items if os.path.isdir(os.path.join(cwd, d)) and not d.startswith(".")]
            files = [f for f in top_items if os.path.isfile(os.path.join(cwd, f)) and not f.startswith(".")]
            hint = f"Current Directory: {cwd}\nTop-level Dirs: {dirs}\nTop-level Files: {files}"
        except Exception:
            hint = f"Current Directory: {cwd}"

        return f"""{hint}{rules_str}{task_str}

## 📥 USER INPUT
{inputOfUser}
"""

    def getSystemMessage(self) -> Dict[str, str]:
        if self.cacheOfSystemMessage is None:
            self.cacheOfSystemMessage = {"role": "system", "content": self.getContextOfSystem()}
        return self.cacheOfSystemMessage

    def invalidateSystemMessageCache(self) -> None:
        self.cacheOfSystemMessage = None

    def backupFile(self, pathOfFile: str):
        if os.path.exists(pathOfFile):
            with open(pathOfFile, "r", encoding="utf-8") as f:
                self.cacheOfBackups[pathOfFile] = f.read()

    def rollbackLastOperation(self):
        ok, msg = rollback_last_edit()
        if ok:
            print(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")
            if self.historyOfOperations:
                self.historyOfOperations.pop()
                self._lastPrintedOperationIndex = min(self._lastPrintedOperationIndex, len(self.historyOfOperations))
            return

        if not self.historyOfOperations:
            print(f"{Fore.RED}No operation to rollback{Style.RESET_ALL}")
            return
        lastOp = self.historyOfOperations[-1]
        pathOfFile = lastOp[0]
        if pathOfFile in self.cacheOfBackups:
            try:
                with open(pathOfFile, "w", encoding="utf-8") as f:
                    f.write(self.cacheOfBackups[pathOfFile])
                print(f"{Fore.GREEN}Rolled back file: {pathOfFile}{Style.RESET_ALL}")
                self.historyOfOperations.pop()
                self._lastPrintedOperationIndex = min(self._lastPrintedOperationIndex, len(self.historyOfOperations))
                del self.cacheOfBackups[pathOfFile]
            except Exception as e:
                print(f"{Fore.RED}Rollback failed: {str(e)}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}No backup data found for rollback{Style.RESET_ALL}")

    def rollbackLastChat(self) -> None:
        if not self._chatMarkers:
            print(f"{Fore.RED}No chat to rollback{Style.RESET_ALL}")
            return

        msg_len, op_len = self._chatMarkers.pop()
        ops_to_rollback = max(0, len(self.historyOfOperations) - op_len)
        rolled = 0
        for _ in range(ops_to_rollback):
            ok, _ = rollback_last_edit()
            if not ok:
                break
            rolled += 1

        self.historyOfOperations = self.historyOfOperations[:op_len]
        self.historyOfMessages = self.historyOfMessages[:msg_len]
        self._lastPrintedOperationIndex = min(self._lastPrintedOperationIndex, len(self.historyOfOperations))
        self.invalidateProjectTreeCache()
        self.invalidateUserRulesCache()
        print(f"{Fore.GREEN}Rolled back last chat (file edits: {rolled}){Style.RESET_ALL}")

    def printStatsOfModification(self, ops: List[Tuple[str, int, int]]) -> None:
        """按文件聚合输出本次对话产生的变动统计；如果本次无变动则不输出。"""
        if not ops:
            return

        aggregated: Dict[str, Tuple[int, int]] = {}
        for pathOfFile, added, deleted in ops:
            prev = aggregated.get(pathOfFile)
            if prev is None:
                aggregated[pathOfFile] = (added, deleted)
            else:
                aggregated[pathOfFile] = (prev[0] + added, prev[1] + deleted)

        print(f"\n{Style.BRIGHT}===== File Modification Stats ====={Style.RESET_ALL}")
        for pathOfFile in sorted(aggregated.keys(), key=lambda p: p.lower()):
            added, deleted = aggregated[pathOfFile]
            print(f"File: {pathOfFile}")
            print(f"  {Fore.BLUE}+({added}){Style.RESET_ALL} | {Fore.RED}-({deleted}){Style.RESET_ALL}")
        print(f"{Style.BRIGHT}==================================={Style.RESET_ALL}")

    def maybePrintModificationStats(self) -> None:
        if self._lastPrintedOperationIndex > len(self.historyOfOperations):
            self._lastPrintedOperationIndex = len(self.historyOfOperations)
        opsOfThisChat = self.historyOfOperations[self._lastOperationIndexOfLastChat :]
        if not opsOfThisChat:
            return
        if self._lastPrintedOperationIndex >= len(self.historyOfOperations):
            return
        opsToPrint = self.historyOfOperations[self._lastPrintedOperationIndex :]
        if not opsToPrint:
            return
        self.printStatsOfModification(opsToPrint)
        self._lastPrintedOperationIndex = len(self.historyOfOperations)

    def getFullHistory(self) -> List[Dict[str, str]]:
        """返回包含系统提示词的完整历史记录。"""
        return [self.getSystemMessage()] + self.historyOfMessages

    def generateSessionTitle(self, firstUserInput: str) -> str:
        """
        使用当前模型快速生成一个简短会话标题。

        Args:
            firstUserInput: 用户第一条输入（原始文本）

        Returns:
            简短标题（可能为空）
        """
        if not self._require_requests():
            return ""
        text = (firstUserInput or "").strip()
        if not text:
            return ""
        prompt = text.splitlines()[0].strip()
        if len(prompt) > 200:
            prompt = prompt[:200]

        headers = {"Authorization": f"Bearer {self.config.apiKey}", "Content-Type": "application/json"}
        payload = {
            "model": self.config.modelName,
            "messages": [
                {"role": "system", "content": "你是一个会话标题生成器。只输出标题本身，不要解释。"},
                {
                    "role": "user",
                    "content": f"基于用户输入生成一个简短中文标题（6-12字，最多16字）：\n{prompt}",
                },
            ],
            "temperature": 0.2,
            "stream": False,
            "max_tokens": 60,
        }
        try:
            resp = requests.post(
                self.endpointOfChat,
                headers=headers,
                json=payload,
                timeout=20,
                verify=self.config.verifySsl,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                return ""
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            content = (msg.get("content") if isinstance(msg, dict) else "") or ""
            title = str(content).strip().strip('"').strip()
            title = title.replace("\r", " ").replace("\n", " ").strip()
            if len(title) > 16:
                title = title[:16]
            return title
        except Exception:
            return ""

    def chat(self, inputOfUser: str, *, on_history_updated: Optional[Callable[[List[Dict[str, str]]], None]] = None):
        """
        处理用户输入并启动 AI 代理的多轮任务执行循环。
        
        Args:
            inputOfUser: 用户在控制台输入的原始文本。
            on_history_updated: 可选回调，用于在关键时刻持久化历史（例如自动保存会话）。
        """
        if not self._require_requests():
            print(f"{Fore.RED}[Error] requests 未安装，无法发起网络请求。{Style.RESET_ALL}")
            return
        chat_marker = (len(self.historyOfMessages), len(self.historyOfOperations))
        self._lastOperationIndexOfLastChat = len(self.historyOfOperations)
        if not inputOfUser.strip() and not self.historyOfMessages:
            print(f"{Fore.YELLOW}Empty input and no history. Waiting for command...{Style.RESET_ALL}")
            return

        msgSystem = self.getSystemMessage()
        baseHistoryLen = len(self.historyOfMessages)
        historyWorking: List[Dict[str, str]] = list(self.historyOfMessages)
        insertedUserContext = False
        if inputOfUser:
            historyWorking.append({"role": "user", "content": self.getContextOfCurrentUser(inputOfUser)})
            insertedUserContext = True

        countCycle = 0
        compactedInThisChat = False
        while countCycle < self.config.maxCycles:
            try:
                countCycle += 1
                print(f"{Fore.YELLOW}[Cycle {countCycle}/{self.config.maxCycles}] Processing...{Style.RESET_ALL}")

                if not compactedInThisChat:
                    historyWorking, didCompact = self._maybe_compact_history(historyWorking, msgSystem)
                    if didCompact:
                        compactedInThisChat = True

                messages = [msgSystem] + historyWorking
                estimateTokens = self.estimateTokensOfMessages(messages)
                if estimateTokens > 115000 and len(historyWorking) > 60:
                    head = historyWorking[:6]
                    tail = historyWorking[-54:]
                    messages = [msgSystem] + head + tail
                    estimateTokens = self.estimateTokensOfMessages(messages)
                
                # 本地计算缓存命中估算 (备用方案)
                localHitEstimate = 0
                if self.lastFullMessages:
                    commonPrefix = []
                    for m1, m2 in zip(self.lastFullMessages, messages):
                        if m1 == m2:
                            commonPrefix.append(m1)
                        else:
                            break
                    if commonPrefix:
                        localHitEstimate = self.estimateTokensOfMessages(commonPrefix)
                
                # 更新本次请求的完整消息，供下次对比
                self.lastFullMessages = list(messages)
                
                print(f"{Fore.MAGENTA}[Token Estimate] ~{estimateTokens} tokens{Style.RESET_ALL}")

                try:
                    log_request(messages)
                except Exception as e:
                    print(f"{Fore.RED}[Log Error] Could not save log: {str(e)}{Style.RESET_ALL}")

                headers = {"Authorization": f"Bearer {self.config.apiKey}", "Content-Type": "application/json"}
                payload = {
                    "model": self.config.modelName,
                    "messages": messages,
                    "temperature": 0.1,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                    "max_tokens": 8000,
                }

                replyFull = ""
                fullReasoning = ""
                hasReasoned = False
                printedReasoningHeader = False
                printedAnswerHeader = False
                usageOfRequest: Optional[Dict[str, Any]] = None
                print(f"{Fore.GREEN}[小晨终端助手]: ", end="")
                try:
                    response = requests.post(
                        self.endpointOfChat, 
                        headers=headers, 
                        json=payload, 
                        stream=True, 
                        timeout=60,
                        verify=self.config.verifySsl
                    )
                    response.raise_for_status()

                    for line in response.iter_lines():
                        if not line:
                            continue
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            line = line[6:]
                        if line in ("", "[DONE]"):
                            continue
                        import json

                        dataChunk = json.loads(line)
                        if isinstance(dataChunk, dict) and "usage" in dataChunk and isinstance(dataChunk.get("usage"), dict):
                            usageOfRequest = dataChunk.get("usage")
                        choices = dataChunk.get("choices") if isinstance(dataChunk, dict) else None
                        if isinstance(choices, list) and choices:
                            delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                            if not delta:
                                continue
                            
                            # 提取推理内容 (reasoning_content)
                            reasoning = delta.get("reasoning_content", "")
                            if reasoning:
                                if not printedReasoningHeader:
                                    printedReasoningHeader = True
                                    printedAnswerHeader = False
                                    print(f"\n{Fore.CYAN}【思考】{Style.RESET_ALL}\n", end="", flush=True)
                                if not hasReasoned:
                                    hasReasoned = True
                                fullReasoning += reasoning
                                print(f"{Fore.CYAN}{reasoning}{Style.RESET_ALL}", end="", flush=True)

                            # 提取正文内容
                            token = delta.get("content", "")
                            if token:
                                if (hasReasoned or printedReasoningHeader) and not printedAnswerHeader:
                                    printedAnswerHeader = True
                                    hasReasoned = False
                                    print(f"\n{Fore.GREEN}【回答】{Style.RESET_ALL}\n", end="", flush=True)
                                replyFull += token
                                print(token, end="", flush=True)
                except requests.exceptions.RequestException as e:
                    msgError = f"{Fore.RED}[Request Error] {str(e)}{Style.RESET_ALL}"
                    print(msgError)
                    replyFull = msgError
                    break
                finally:
                    print("\n" + "-" * 40)
                    if usageOfRequest:
                        # 从单次请求中提取命中和未命中
                        hit = int(usageOfRequest.get("prompt_cache_hit_tokens") or 0)
                        if hit == 0:
                            details = usageOfRequest.get("prompt_tokens_details")
                            if isinstance(details, dict):
                                hit = int(details.get("cached_tokens") or 0)
                        
                        # 备用方案：如果 API 返回 0 但本地计算有重复前缀，则使用本地估算值
                        isEstimated = False
                        if hit == 0 and localHitEstimate > 0:
                            hit = localHitEstimate
                            isEstimated = True
                            # 更新 usage 对象以便后续统计使用
                            if "prompt_tokens_details" not in usageOfRequest:
                                usageOfRequest["prompt_tokens_details"] = {}
                            usageOfRequest["prompt_tokens_details"]["cached_tokens"] = hit
                            # 如果是 DeepSeek 风格也可以设置
                            usageOfRequest["prompt_cache_hit_tokens"] = hit

                        self.statsOfCache.updateFromUsage(usageOfRequest)
                        
                        prompt = int(usageOfRequest.get("prompt_tokens") or 0)
                        miss = int(usageOfRequest.get("prompt_cache_miss_tokens") or 0)
                        if miss == 0 and prompt > hit:
                            miss = prompt - hit

                        rateReq = CacheStats.getHitRateOfUsage(usageOfRequest)
                        rateSession = self.statsOfCache.getSessionHitRate()
                        rateReqStr = f"{rateReq*100:.1f}%" if rateReq is not None else "N/A"
                        if isEstimated:
                            rateReqStr += " (Est.)"
                        
                        rateSessionStr = f"{rateSession*100:.1f}%" if rateSession is not None else "N/A"
                        print(
                            f"{Fore.CYAN}[Cache] hit={hit} miss={miss} rate={rateReqStr} | session_rate={rateSessionStr}{Style.RESET_ALL}"
                        )
                        try:
                            append_usage_history(
                                usage=usageOfRequest,
                                cache={
                                    "hit": hit,
                                    "miss": miss,
                                    "rate_request": rateReq,
                                    "rate_session": rateSession,
                                    "session": {
                                        "counted_requests": self.statsOfCache.countedRequests,
                                        "hit_tokens": self.statsOfCache.promptCacheHitTokens,
                                        "miss_tokens": self.statsOfCache.promptCacheMissTokens,
                                        "prompt_tokens": self.statsOfCache.promptTokens,
                                        "completion_tokens": self.statsOfCache.completionTokens,
                                        "total_tokens": self.statsOfCache.totalTokens,
                                    },
                                },
                            )
                        except Exception:
                            pass

                historyWorking.append({"role": "assistant", "content": replyFull})
                if on_history_updated is not None:
                    try:
                        on_history_updated([msgSystem] + list(historyWorking))
                    except Exception:
                        pass
                tasks = parse_stack_of_tags(replyFull)

                if not tasks:
                    replyLower = replyFull.lower()
                    suspiciousTagTokens = [
                        "<write_file",
                        "<read_file",
                        "<run_command",
                        "<search_files",
                        "<search_in_files",
                        "<edit_lines",
                        "<replace_in_file",
                        "<task_add",
                        "<task_update",
                        "<task_delete",
                        "<task_list",
                        "<task_clear",
                        "</write_file",
                        "</read_file",
                        "</run_command",
                        "</search_files",
                        "</search_in_files",
                        "</edit_lines",
                        "</replace_in_file",
                        "</task_add",
                        "</task_update",
                        "</task_delete",
                        "</task_list",
                        "</task_clear",
                    ]
                    if any(tok in replyLower for tok in suspiciousTagTokens):
                        feedbackError = "ERROR: Invalid Format! Use one or more closed tags. No tag if no task."
                        historyWorking.append({"role": "user", "content": feedbackError})
                    else:
                        break

                observations: List[str] = []
                isCancelled = False
                didExecuteAnyTask = False
                
                # 检查是否被用户中断
                if self.interruptHandler.is_interrupted():
                    print(f"\n{Fore.YELLOW}⚠️  用户已中断执行{Style.RESET_ALL}")
                    historyWorking.append({"role": "user", "content": "用户中断执行"})
                    break
                
                ok, batchApproved = self.confirmBatchExecution(tasks)
                if not ok:
                    historyWorking.append({"role": "user", "content": "User cancelled execution"})
                    isCancelled = True
                
                # 打印任务执行计划
                if tasks and ok:
                    print(f"\n{Style.BRIGHT}{'='*50}{Style.RESET_ALL}")
                    print(f"{Style.BRIGHT}开始执行 {len(tasks)} 个任务{Style.RESET_ALL}")
                    print(f"{Style.BRIGHT}{'='*50}{Style.RESET_ALL}")
                
                for idx, t in enumerate(tasks, 1):
                    # 检查中断
                    if self.interruptHandler.is_interrupted():
                        print(f"\n{Fore.YELLOW}⚠️  用户已中断执行{Style.RESET_ALL}")
                        historyWorking.append({"role": "user", "content": "用户中断执行"})
                        isCancelled = True
                        break
                    
                    if isCancelled:
                        break
                    
                    # 打印当前任务信息
                    print_tool_execution_header(t, idx, len(tasks))
                    
                    isWhitelisted = self.isTaskWhitelisted(t)
                    if isWhitelisted or batchApproved:
                        confirm = "y"
                    else:
                        try:
                            confirm = input(f"{Style.BRIGHT}执行此任务? (y=是 / n=否 / Ctrl+C=中断): {Style.RESET_ALL}").strip().lower()
                            if confirm == "":
                                confirm = "y"
                        except KeyboardInterrupt:
                            print(f"\n{Fore.YELLOW}⚠️  用户中断执行{Style.RESET_ALL}")
                            self.interruptHandler.set_interrupted()
                            historyWorking.append({"role": "user", "content": "用户中断执行"})
                            isCancelled = True
                            break

                    if confirm.lower() != "y":
                        historyWorking.append({"role": "user", "content": "User cancelled execution"})
                        isCancelled = True
                        break
                    didExecuteAnyTask = True

                    if t["type"] == "search_files":
                        pattern = t["pattern"]
                        try:
                            results = search_files(pattern, os.getcwd())
                            if results:
                                treeOutput = generate_tree_structure(results, os.getcwd())
                                obs = f"SUCCESS: Found {len(results)} files:\n{treeOutput}"
                                observations.append(obs)
                                self.printToolResult(obs)
                            else:
                                suggestions = suggest_similar_patterns(pattern, os.getcwd())
                                if suggestions:
                                    sug = "\n".join([f"- {s}" for s in suggestions])
                                    obs = f"SUCCESS: No files found matching {pattern}\nSuggestions:\n{sug}"
                                else:
                                    obs = f"SUCCESS: No files found matching {pattern}"
                                observations.append(obs)
                                self.printToolResult(obs)
                        except Exception as e:
                            obs = f"FAILURE: {str(e)}"
                            observations.append(obs)
                            self.printToolResult(obs)

                    elif t["type"] == "search_in_files":
                        regex = t["regex"]
                        glob_pattern = t.get("glob") or "**/*"
                        root = os.path.abspath(t.get("root") or ".")
                        max_matches = int(t.get("max_matches") or 200)
                        try:
                            matches_by_path, error = search_in_files(
                                regex=regex,
                                root_dir=root,
                                glob_pattern=glob_pattern,
                                max_matches=max_matches,
                            )
                            if error:
                                obs = f"FAILURE: Invalid regex: {error}"
                                observations.append(obs)
                                self.printToolResult(obs)
                            elif matches_by_path:
                                treeOutput = generate_match_tree(matches_by_path, root)
                                totalMatches = sum(len(v) for v in matches_by_path.values())
                                obs = (
                                    "SUCCESS: Regex matches found\n"
                                    f"Regex: {regex}\n"
                                    f"Glob: {glob_pattern}\n"
                                    f"Matches: {totalMatches} (files: {len(matches_by_path)})\n"
                                    f"{treeOutput}"
                                )
                                observations.append(obs)
                                self.printToolResult(obs)
                            else:
                                obs = (
                                    "SUCCESS: No regex matches found\n"
                                    f"Regex: {regex}\n"
                                    f"Glob: {glob_pattern}\n"
                                    f"Root: {root}"
                                )
                                observations.append(obs)
                                self.printToolResult(obs)
                        except Exception as e:
                            obs = f"FAILURE: {str(e)}"
                            observations.append(obs)
                            self.printToolResult(obs)

                    elif t["type"] == "write_file":
                        path = os.path.abspath(t["path"])
                        content = t["content"]
                        try:
                            overwrite = bool(t.get("overwrite") or False)
                            if os.path.exists(path) and not overwrite:
                                obs = (
                                    "FAILURE: Refuse to overwrite existing file via write_file. "
                                    "Use edit_lines, or set <overwrite>true</overwrite> explicitly."
                                )
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue

                            self.backupFile(path)
                            ensure_parent_dir(path)
                            before_content = self.cacheOfBackups.get(path, "")
                            added, deleted = calculate_diff_of_lines(path, content)
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(content)
                            self.historyOfOperations.append((path, added, deleted))
                            append_edit_history(
                                path_of_file=path,
                                before_content=before_content,
                                after_content=content,
                                meta={"type": "write_file"},
                            )
                            self.invalidateProjectTreeCache()
                            self._invalidate_read_cache_for_path(path)
                            if os.path.basename(path).lower() == "userrules":
                                self.invalidateUserRulesCache()
                            obs = f"SUCCESS: Saved to {path} | +{added} | -{deleted}"
                            ext = os.path.splitext(path)[1].lower()
                            if ext in {".py", ".pyw"}:
                                ok, detail = self._validate_python_file(path)
                                if not ok:
                                    obs = f"FAILURE: Python validation failed: {path}\n{detail}"
                            observations.append(obs)
                            self.printToolResult(obs)
                        except Exception as e:
                            obs = f"FAILURE: {str(e)}"
                            observations.append(obs)
                            self.printToolResult(obs)

                    elif t["type"] == "replace_in_file":
                        path = os.path.abspath(t["path"])
                        search_text = str(t.get("search") or "")
                        replace_text = str(t.get("replace") or "")
                        count = int(t.get("count") or 1)
                        is_regex = bool(t.get("regex") or False)
                        auto_indent = bool(t.get("auto_indent") or False)
                        try:
                            if not os.path.exists(path):
                                obs = f"FAILURE: File not found: {path}"
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue
                            if count <= 0:
                                count = 1
                            ext = os.path.splitext(path)[1].lower()
                            if is_regex and auto_indent and ext in {".py", ".pyw"}:
                                obs = "FAILURE: replace_in_file with regex does not support auto_indent"
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue

                            self.backupFile(path)
                            with open(path, "r", encoding="utf-8") as f:
                                before_content = f.read()

                            after_content = before_content
                            replaced_times = 0

                            def _dedent_block(s: str) -> str:
                                lines = s.splitlines()
                                min_ws = None
                                for ln in lines:
                                    if ln.strip() == "":
                                        continue
                                    ws = re.match(r"[ \t]*", ln).group(0)
                                    if min_ws is None or len(ws) < min_ws:
                                        min_ws = len(ws)
                                if min_ws is None or min_ws <= 0:
                                    return s
                                out = []
                                for ln in lines:
                                    if ln.strip() == "":
                                        out.append("")
                                    else:
                                        out.append(ln[min_ws:] if len(ln) >= min_ws else ln.lstrip(" \t"))
                                return "\n".join(out)

                            if is_regex:
                                pattern = re.compile(search_text, flags=re.MULTILINE)
                                after_content, replaced_times = pattern.subn(replace_text, after_content, count=count)
                            else:
                                for _ in range(count):
                                    idx0 = after_content.find(search_text)
                                    if idx0 == -1:
                                        break
                                    rep = replace_text
                                    if auto_indent and ext in {".py", ".pyw"}:
                                        line_start = after_content.rfind("\n", 0, idx0) + 1
                                        line_prefix = re.match(r"[ \t]*", after_content[line_start:]).group(0)
                                        rep = _dedent_block(rep)
                                        rep_lines = rep.splitlines()
                                        rep = "\n".join([(line_prefix + ln) if ln.strip() != "" else "" for ln in rep_lines])
                                    after_content = after_content[:idx0] + rep + after_content[idx0 + len(search_text) :]
                                    replaced_times += 1

                            if replaced_times <= 0 or after_content == before_content:
                                obs = "FAILURE: replace_in_file did not find any match to replace"
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue

                            added, deleted = calculate_diff_of_lines(path, after_content)
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(after_content)

                            self.historyOfOperations.append((path, added, deleted))
                            append_edit_history(
                                path_of_file=path,
                                before_content=before_content,
                                after_content=after_content,
                                meta={
                                    "type": "replace_in_file",
                                    "count": count,
                                    "regex": is_regex,
                                    "auto_indent": auto_indent,
                                    "replaced": replaced_times,
                                },
                            )
                            self.invalidateProjectTreeCache()
                            self._invalidate_read_cache_for_path(path)
                            if os.path.basename(path).lower() == "userrules":
                                self.invalidateUserRulesCache()

                            obs = f"SUCCESS: Replaced in {path} | times={replaced_times} | +{added} | -{deleted}"
                            if ext in {".py", ".pyw"}:
                                ok, detail = self._validate_python_file(path)
                                if not ok:
                                    obs = f"FAILURE: Python validation failed: {path}\n{detail}"
                            observations.append(obs)
                            self.printToolResult(obs)
                        except Exception as e:
                            obs = f"FAILURE: {str(e)}"
                            observations.append(obs)
                            self.printToolResult(obs)

                    elif t["type"] == "edit_lines":
                        path = os.path.abspath(t["path"])
                        delete_start = t.get("delete_start")
                        delete_end = t.get("delete_end")
                        insert_at = t.get("insert_at")
                        auto_indent = bool(t.get("auto_indent") or False)
                        content = t.get("content", "")
                        try:
                            existedBefore = os.path.exists(path)
                            self.backupFile(path)
                            ensure_parent_dir(path)
                            before_content, after_content = edit_lines(
                                path_of_file=path,
                                delete_start=delete_start,
                                delete_end=delete_end,
                                insert_at=insert_at,
                                auto_indent=auto_indent,
                                content=content,
                            )
                            added, deleted = calculate_diff_of_lines(path, after_content)
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(after_content)
                            self.historyOfOperations.append((path, added, deleted))
                            append_edit_history(
                                path_of_file=path,
                                before_content=before_content,
                                after_content=after_content,
                                meta={
                                    "type": "edit_lines",
                                    "delete_start": delete_start,
                                    "delete_end": delete_end,
                                    "insert_at": insert_at,
                                },
                            )
                            self.invalidateProjectTreeCache()
                            self._invalidate_read_cache_for_path(path)
                            if os.path.basename(path).lower() == "userrules":
                                self.invalidateUserRulesCache()
                            warn = ""
                            ext = os.path.splitext(path)[1].lower()
                            if ext in {".py", ".pyw"}:
                                has_tab = False
                                has_space = False
                                has_mixed = False
                                for ln in after_content.splitlines():
                                    if not ln or ln.strip() == "":
                                        continue
                                    ws = re.match(r"[ \t]*", ln).group(0)
                                    if "\t" in ws and " " in ws:
                                        has_mixed = True
                                        break
                                    if "\t" in ws:
                                        has_tab = True
                                    elif " " in ws:
                                        has_space = True
                                if has_mixed or (has_tab and has_space):
                                    warn = " | WARNING: Mixed indentation (tabs/spaces)"
                            obs = f"SUCCESS: Edited {path} | +{added} | -{deleted}{warn}"
                            if ext in {".py", ".pyw"}:
                                ok, detail = self._validate_python_file(path)
                                if not ok:
                                    obs = f"FAILURE: Python validation failed: {path}\n{detail}"
                            observations.append(obs)
                            self.printToolResult(obs)
                        except Exception as e:
                            obs = f"FAILURE: {str(e)}"
                            observations.append(obs)
                            self.printToolResult(obs)

                    elif t["type"] == "read_file":
                        path = os.path.abspath(t["path"])
                        startLine = t.get("start_line")
                        endLine = t.get("end_line")
                        try:
                            if startLine is None or endLine is None:
                                obs = "FAILURE: read_file requires both start_line and end_line"
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue
                            startLine = int(startLine)
                            endLine = int(endLine)
                            if startLine < 1 or endLine < startLine:
                                obs = f"FAILURE: Invalid range: {startLine}-{endLine}"
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue

                            max_window = 160
                            orig_end = endLine
                            if endLine - startLine + 1 > max_window:
                                endLine = startLine + max_window - 1

                            if not os.path.exists(path):
                                obs = f"FAILURE: File not found: {path}"
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue

                            mtime = 0.0
                            try:
                                mtime = float(os.path.getmtime(path))
                            except Exception:
                                mtime = 0.0
                            key = (path, startLine, endLine)
                            cached = self._recentReadCache.get(key)
                            if cached is not None and cached[0] >= mtime:
                                obs = (
                                    "SUCCESS: Read skipped (duplicate)\n"
                                    f"File: {path}\n"
                                    f"Range: {startLine}-{endLine}\n"
                                    "Content: <omitted>"
                                )
                                observations.append(obs)
                                self.printToolResult(obs)
                                continue

                            totalLines, actualEnd, content = read_range_numbered(
                                path,
                                startLine,
                                endLine,
                                indent_mode=getattr(self, "readIndentMode", "smart"),
                            )
                            self._recentReadCache[key] = (mtime, time.time())
                            if len(self._recentReadCache) > 200:
                                items = sorted(self._recentReadCache.items(), key=lambda kv: kv[1][1])
                                for k, _v in items[: max(0, len(items) - 200)]:
                                    self._recentReadCache.pop(k, None)
                            obs = (
                                f"SUCCESS: Read {path}\n"
                                f"Lines: {totalLines} | Range: {startLine}-{actualEnd}\n"
                                f"Content:\n{content}"
                            )
                            if orig_end != endLine:
                                obs = obs.replace(
                                    f"Range: {startLine}-{actualEnd}",
                                    f"Range: {startLine}-{actualEnd} | clamped_from={orig_end}",
                                )
                            observations.append(obs)
                            self.printToolResult(obs)
                        except Exception as e:
                            obs = f"FAILURE: {str(e)}"
                            observations.append(obs)
                            self.printToolResult(obs)

                    elif t["type"] == "run_command":
                        cmd_text = str(t["command"])
                        is_long = str(t.get("is_long_running", "false")).lower() == "true"
                        cwd = t.get("cwd")
                        
                        commands = [c.strip() for c in cmd_text.splitlines() if c.strip()]
                        if not commands:
                            obs = "FAILURE: Empty command"
                            observations.append(obs)
                            self.printToolResult(obs)
                        else:
                            for cmd in commands:
                                dangerousCmds = ["rm -rf", "format", "del /f/s/q", "mkfs"]
                                if any(d in cmd.lower() for d in dangerousCmds):
                                    obs = f"FAILURE: Dangerous command blocked: {cmd}"
                                    observations.append(obs)
                                    self.printToolResult(obs)
                                    continue
                                
                                try:
                                    run_cwd = None
                                    if cwd is not None and str(cwd).strip():
                                        run_cwd = os.path.abspath(str(cwd).strip())
                                    success, tid, output, error = self.terminalManager.run_command(cmd, is_long_running=is_long, cwd=run_cwd)
                                    if success:
                                        status = self.terminalManager.get_terminal_status(tid)
                                        isRunning = bool(status.get("is_running")) if isinstance(status, dict) else False
                                        if isRunning:
                                            obs = (
                                                "SUCCESS: Command started (running)\n"
                                                f"Terminal ID: {tid}\n"
                                                f"Command: {cmd}\n"
                                                f"{output}\n"
                                                f"{self.renderRunningTerminals()}"
                                            )
                                        else:
                                            obs = (
                                                "SUCCESS: Command executed\n"
                                                f"Terminal ID: {tid}\n"
                                                f"Command: {cmd}\n"
                                                f"{output}"
                                            )
                                    else:
                                        obs = (
                                            "FAILURE: Command failed\n"
                                            f"Terminal ID: {tid}\n"
                                            f"Command: {cmd}\n"
                                            f"{error}\n"
                                            f"{output}"
                                        )
                                    
                                    self.printRunCommandSummary(tid=tid, cmd=cmd, success=success, output=output, error=error)
                                    observations.append(obs)
                                    self.printToolResult(obs)
                                except Exception as e:
                                    obs = f"FAILURE: {str(e)}"
                                    observations.append(obs)
                                    self.printToolResult(obs)
                    elif t["type"] == "task_add":
                        content = str(t.get("content") or "").strip()
                        status = str(t.get("status") or "").strip() or None
                        tid = str(t.get("id") or "").strip() or None
                        progress = t.get("progress")
                        if not content:
                            obs = "FAILURE: task_add missing <content>"
                            observations.append(obs)
                        else:
                            item = self.taskManager.add(content, id=tid, status=status, progress=progress)
                            obs = f"SUCCESS: Task added ({item.id})"
                            observations.append(obs)
                            self.printTaskProgress()

                    elif t["type"] == "task_update":
                        tid = str(t.get("id") or "").strip()
                        content = t.get("content")
                        status = t.get("status")
                        progress = t.get("progress")
                        item = self.taskManager.update(tid, content=content, status=status, progress=progress)
                        if not item:
                            obs = f"FAILURE: Task not found: {tid}"
                            observations.append(obs)
                        else:
                            obs = f"SUCCESS: Task updated ({item.id})"
                            observations.append(obs)
                            self.printTaskProgress()

                    elif t["type"] == "task_delete":
                        tid = str(t.get("id") or "").strip()
                        ok = self.taskManager.delete(tid)
                        if not ok:
                            obs = f"FAILURE: Task not found: {tid}"
                            observations.append(obs)
                        else:
                            obs = f"SUCCESS: Task deleted ({tid})"
                            observations.append(obs)
                            self.printTaskProgress()

                    elif t["type"] == "task_clear":
                        self.taskManager.clear()
                        obs = "SUCCESS: Tasks cleared"
                        observations.append(obs)
                        self.printTaskProgress()

                    elif t["type"] == "task_list":
                        obs = "SUCCESS: Task list\n" + self.taskManager.render()
                        observations.append(obs)
                        self.printTaskProgress()

                if observations:
                    historyWorking.append({"role": "user", "content": "\n".join(observations)})
                    if on_history_updated is not None:
                        try:
                            on_history_updated([msgSystem] + list(historyWorking))
                        except Exception:
                            pass
                if isCancelled:
                    break
                if didExecuteAnyTask and self.config.stopAfterFirstToolExecution:
                    break

            except Exception as e:
                print(f"{Fore.RED}[Cycle Error] {str(e)}{Style.RESET_ALL}")
                historyWorking.append({"role": "user", "content": f"ERROR: Agent crashed with error: {str(e)}"})
                break

        if countCycle >= self.config.maxCycles:
            print(f"{Fore.RED}[Tip] Max cycles reached.{Style.RESET_ALL}")

        self.historyOfMessages = historyWorking
        self.maybePrintModificationStats()
        self._chatMarkers.append(chat_marker)


VoidAgent = Agent
