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
    indent_lines_range,
    dedent_lines_range,
    ensure_parent_dir,
    generate_dir_tree,
    generate_tree_structure,
    generate_match_tree,
    read_range,
    read_range_numbered,
    read_lines_range_raw,
    search_files,
    search_in_files,
    suggest_similar_patterns,
)
from ..utils.interrupt import InterruptHandler
from ..utils.logs import append_edit_history, append_usage_history, log_request, rollback_last_edit
from .metrics import CacheStats
from ..utils.tags import parse_stack_of_tags
from ..utils.terminal import TerminalManager
from ..tools import web_search, visit_page, Tools
from .task_manager import TaskManager, TaskItem
from .utils import detect_ruff_runner, validate_python_file, require_requests


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
        self.clipboard: Dict[str, str] = {}
        self.tools = Tools(self)

    def _require_requests(self) -> bool:
        """
        检查 requests 依赖是否可用。

        Returns:
            是否可用
        """
        return require_requests()

    def _detect_ruff_runner(self) -> Optional[List[str]]:
        """
        探测 ruff 可用的执行方式。

        Returns:
            - ["<path-to-ruff>"] 或 ["<python>", "-m", "ruff"]：ruff 可用
            - None：未安装或不可用（不引入强依赖时的默认行为）
        """
        new_cached, runner = detect_ruff_runner(self._cachedRuffRunner, self.pythonValidateRuff)
        self._cachedRuffRunner = new_cached
        return runner

    def _validate_python_file(self, path: str) -> Tuple[bool, str]:
        """
        校验 Python 文件的语法与风格（可选）。

        - 必跑：py_compile（语法/缩进错误能立即发现）
        - 可选：ruff check（若系统已安装 ruff，则自动启用；否则跳过）
        """
        runner = self._detect_ruff_runner()
        return validate_python_file(path, runner)

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
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                print(f"{Fore.RED}[Summary Error] 401 Unauthorized: API Key 无效。{Style.RESET_ALL}")
            return ""
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
        return """# XIAOCHEN_TERMINAL - XiaoChen Terminal Assistant
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
  - Python indentation display uses header mode by default: indent_style/indent_size/mixed are output once at the beginning; blank lines are displayed as <WS_ONLY>.
- Write file:
  <write_file><path>...</path><content>...</content><overwrite>false</overwrite></write_file>
  - Use write_file ONLY for new files. If the target file already exists, you MUST use edit_lines, unless overwrite=true is explicitly set.
- Edit lines:
  <edit_lines><path>...</path><delete_start>10</delete_start><delete_end>20</delete_end><insert_at>10</insert_at><auto_indent>true</auto_indent><content>...</content></edit_lines>
  - insert_at refers to original line numbers; the tool handles offsets.
  - auto_indent aligns inserted Python code to surrounding indentation.
- Indent/Dedent lines (spaces only):
  <indent_lines><path>...</path><start_line>10</start_line><end_line>20</end_line><spaces>4</spaces></indent_lines>
  <dedent_lines><path>...</path><start_line>10</start_line><end_line>20</end_line><spaces>4</spaces></dedent_lines>
- Copy/Paste lines:
  <copy_lines><path>...</path><start_line>10</start_line><end_line>20</end_line><register>default</register></copy_lines>
  <paste_lines><path>...</path><insert_at>10</insert_at><register>default</register><auto_indent>true</auto_indent></paste_lines>
  - register: Optional. Use different names for multiple clips.
- Search/Replace:
  <replace_in_file><path>...</path><search>...</search><replace>...</replace><count>1</count><regex>false</regex><auto_indent>true</auto_indent></replace_in_file>
- Run command:
  <run_command><command>...</command><is_long_running>false</is_long_running><cwd>.</cwd></run_command>
- Web search (retrieve real-time knowledge):
  <web_search><query>search keywords</query><engine>bing</engine><max_results>3</max_results></web_search>
  - query: Search keywords (automatically limited to 200 characters)
  - engine: Search engine, options: bing (default) or duckduckgo
  - max_results: Number of results to return (1-10, default 3, recommended to keep small to save tokens)
  <visit_page><url>...</url></visit_page>
  - url: URL of the webpage to visit, returns the main content of the webpage
- OCR recognition:
  <ocr_image><path>...</path></ocr_image>
  - path: Absolute path to the image file
  <ocr_document><path>...</path><page_start>1</page_start><page_end>5</page_end></ocr_document>
  - path: Absolute path to the document file (e.g., PDF)
  - page_start: Starting page number (optional, default is 1)
  - page_end: Ending page number (optional, default is to the end)
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

    def getContextOfCurrentUserMinimal(self, inputOfUser: str) -> str:
        cwd = os.getcwd()
        task_str = ""
        if self.taskManager._tasks:
            task_str = f"\n\n## 📋 CURRENT TASKS\n{self.taskManager.render()}"

        return f"""Current Directory: {cwd}{task_str}

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
        if (
            isinstance(self.historyOfMessages, list)
            and self.historyOfMessages
            and isinstance(self.historyOfMessages[0], dict)
            and self.historyOfMessages[0].get("role") == "system"
        ):
            return list(self.historyOfMessages)
        return [self.getSystemMessage()] + list(self.historyOfMessages)

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
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                print(f"{Fore.RED}[Title Error] 401 Unauthorized: API Key 无效。{Style.RESET_ALL}")
            return ""
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

        loaded_system = None
        if (
            isinstance(self.historyOfMessages, list)
            and self.historyOfMessages
            and isinstance(self.historyOfMessages[0], dict)
            and self.historyOfMessages[0].get("role") == "system"
        ):
            loaded_system = self.historyOfMessages[0]

        msgSystem = loaded_system or self.getSystemMessage()
        baseHistoryLen = len(self.historyOfMessages)
        historyWorking: List[Dict[str, str]] = list(self.historyOfMessages[1:] if loaded_system else self.historyOfMessages)
        insertedUserContext = False
        if inputOfUser:
            if baseHistoryLen <= 0:
                content = self.getContextOfCurrentUser(inputOfUser)
            else:
                content = self.getContextOfCurrentUserMinimal(inputOfUser)
            historyWorking.append({"role": "user", "content": content})
            insertedUserContext = True

        countCycle = 0
        compactedInThisChat = False
        try:
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
                    except KeyboardInterrupt:
                        print(f"\n{Fore.YELLOW}⚠️  用户中断了 AI 输出{Style.RESET_ALL}")
                        self.interruptHandler.set_interrupted()
                        if not replyFull:
                            replyFull = "[Interrupted]"
                        else:
                            replyFull += "\n[Interrupted]"
                    except Exception as e:
                        if hasattr(e, "response") and e.response is not None and e.response.status_code == 401:
                            msgError = f"{Fore.RED}[Request Error] 401 Unauthorized: 您的 API Key 无效或已过期。{Style.RESET_ALL}\n"
                            msgError += f"{Fore.YELLOW}请检查 config.json 中的 api_key，或使用命令 `model key <your_key>` 重新设置。{Style.RESET_ALL}"
                        else:
                            msgError = f"{Fore.RED}[Request Error] {str(e)}{Style.RESET_ALL}"
                        print(msgError)
                        replyFull = msgError
                        break
                    finally:
                        print("\n" + "-" * 40)
                        if usageOfRequest:
                            prompt = int(usageOfRequest.get("prompt_tokens") or 0)
                            hit = 0
                            hit_source = "vendor"
                            if "prompt_cache_hit_tokens" in usageOfRequest:
                                hit = int(usageOfRequest.get("prompt_cache_hit_tokens") or 0)
                            else:
                                details = usageOfRequest.get("prompt_tokens_details")
                                if isinstance(details, dict) and "cached_tokens" in details:
                                    hit = int(details.get("cached_tokens") or 0)
                                else:
                                    hit_source = "local"
                                    if localHitEstimate > 0 and prompt > 0:
                                        hit = min(int(localHitEstimate), prompt)
                                usageOfRequest["prompt_cache_hit_tokens"] = hit
                                if "prompt_tokens_details" not in usageOfRequest:
                                    usageOfRequest["prompt_tokens_details"] = {}
                                if isinstance(usageOfRequest["prompt_tokens_details"], dict):
                                    usageOfRequest["prompt_tokens_details"]["cached_tokens"] = hit

                            self.statsOfCache.updateFromUsage(usageOfRequest)

                            miss = int(usageOfRequest.get("prompt_cache_miss_tokens") or 0)
                            if miss == 0 and prompt > hit:
                                miss = prompt - hit

                            rateReq = CacheStats.getHitRateOfUsage(usageOfRequest)
                            rateSession = self.statsOfCache.getSessionHitRate()
                            rateReqStr = f"{rateReq*100:.1f}%" if rateReq is not None else "N/A"
                            if hit_source == "local":
                                rateReqStr += " (Local)"
                            
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
                    
                    # 对任务进行去重，防止相同任务在同一批次中重复执行
                    if tasks:
                        unique_tasks = []
                        seen_tasks = set()
                        for t in tasks:
                            # 转换为可哈希的字符串表示进行去重
                            t_repr = str(sorted(t.items()))
                            if t_repr not in seen_tasks:
                                seen_tasks.add(t_repr)
                                unique_tasks.append(t)
                        if len(unique_tasks) < len(tasks):
                            print(f"{Fore.YELLOW}[系统] 已自动过滤 {len(tasks) - len(unique_tasks)} 个重复任务{Style.RESET_ALL}")
                        tasks = unique_tasks

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
                            "<web_search",
                            "<visit_page",
                            "<task_add",
                            "<task_update",
                            "<task_delete",
                            "<task_list",
                            "<task_clear",
                        "<ocr_image",
                        "<ocr_document",
                        "</write_file",
                        "</read_file",
                        "</run_command",
                        "</search_files",
                        "</search_in_files",
                        "</edit_lines",
                        "</replace_in_file",
                        "</web_search",
                        "</visit_page",
                        "</task_add",
                        "</task_update",
                        "</task_delete",
                        "</task_list",
                        "</task_clear",
                        "</ocr_image",
                        "</ocr_document",
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

                        obs = None
                        if t["type"] == "search_files":
                            obs = self.tools.search_files(t)
                        elif t["type"] == "search_in_files":
                            obs = self.tools.search_in_files(t)
                        elif t["type"] == "write_file":
                            obs = self.tools.write_file(t)
                        elif t["type"] == "replace_in_file":
                            obs = self.tools.replace_in_file(t)
                        elif t["type"] == "edit_lines":
                            obs = self.tools.edit_lines(t)
                        elif t["type"] == "copy_lines":
                            obs = self.tools.copy_lines(t)
                        elif t["type"] == "paste_lines":
                            obs = self.tools.paste_lines(t)
                        elif t["type"] == "indent_lines":
                            obs = self.tools.indent_lines(t)
                        elif t["type"] == "dedent_lines":
                            obs = self.tools.dedent_lines(t)
                        elif t["type"] == "read_file":
                            obs = self.tools.read_file(t)
                        elif t["type"] == "run_command":
                            obs = self.tools.run_command(t)
                        elif t["type"] == "web_search":
                            obs = self.tools.web_search(t)
                        elif t["type"] == "visit_page":
                            obs = self.tools.visit_page(t)
                        elif t["type"] == "ocr_image":
                            obs = self.tools.ocr_image(t)
                        elif t["type"] == "ocr_document":
                            obs = self.tools.ocr_document(t)
                        elif t["type"] == "task_add":
                            obs = self.tools.task_add(t)
                        elif t["type"] == "task_update":
                            obs = self.tools.task_update(t)
                        elif t["type"] == "task_delete":
                            obs = self.tools.task_delete(t)
                        elif t["type"] == "task_clear":
                            obs = self.tools.task_clear(t)
                        elif t["type"] == "task_list":
                            obs = self.tools.task_list(t)

                        if obs:
                            observations.append(obs)
                            self.printToolResult(obs)

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

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⚠️  用户中断了代理运行{Style.RESET_ALL}")
            self.interruptHandler.set_interrupted()
            # 如果最后一条消息不是中断提示，且此时确实发生了中断，则记录
            if not historyWorking or (historyWorking[-1].get("role") == "assistant" and "[Interrupted]" not in historyWorking[-1].get("content", "")):
                if not historyWorking or historyWorking[-1].get("content") != "用户中断执行":
                    historyWorking.append({"role": "user", "content": "用户中断执行"})
        finally:
            self.historyOfMessages = [msgSystem] + list(historyWorking)
            # 确保即使中断也能持久化历史记录
            if on_history_updated is not None:
                try:
                    on_history_updated(self.historyOfMessages)
                except Exception:
                    pass
            self.maybePrintModificationStats()
            self._chatMarkers.append(chat_marker)


VoidAgent = Agent
