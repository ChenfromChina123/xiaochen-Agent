import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3

from .config import Config
from .console import Fore, Style
from .files import (
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
from .logs import append_edit_history, append_usage_history, log_request, rollback_last_edit
from .metrics import CacheStats
from .tags import parse_stack_of_tags
from .terminal import TerminalManager


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
        if not self.config.verifySsl:
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

    def estimateTokensOfMessages(self, messages: List[Dict[str, str]]) -> int:
        totalChars = 0
        for msg in messages:
            totalChars += len(msg["role"]) + len(msg["content"]) + 8
        return int(totalChars / 3)

    def isTaskWhitelisted(self, t: Dict[str, Any]) -> bool:
        """判断该工具调用是否在白名单中，可自动执行而无需用户批准。"""
        if t["type"] in self.config.whitelistedTools:
            return True
        if t["type"] == "run_command":
            cmd_first = str(t.get("command", "")).strip().splitlines()[:1]
            baseCmd = cmd_first[0].split()[0] if cmd_first and cmd_first[0] else ""
            if baseCmd in self.config.whitelistedCommands:
                return True
        return False

    def summarizeTask(self, t: Dict[str, Any]) -> str:
        """将单个任务压缩为一行摘要，便于批量批准时展示。"""
        ttype = t.get("type") or ""
        if ttype == "run_command":
            cmd = str(t.get("command", "")).strip().splitlines()[:1]
            cmdLine = cmd[0] if cmd and cmd[0] else ""
            return f"run_command: {cmdLine}"
        if ttype in {"write_file", "read_file"}:
            return f"{ttype}: {t.get('path', '')}"
        if ttype == "edit_lines":
            ds = t.get("delete_start")
            de = t.get("delete_end")
            ins = t.get("insert_at")
            return f"edit_lines: {t.get('path', '')} del={ds}-{de} ins={ins}"
        if ttype == "search_files":
            return f"search_files: {t.get('pattern', '')}"
        if ttype == "search_in_files":
            return f"search_in_files: {t.get('regex', '')}"
        if ttype.startswith("task_"):
            return f"{ttype}: {t.get('id', '')}"
        return str(ttype)

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
        status = self.terminalManager.get_terminal_status(tid)
        isRunning = bool(status.get("is_running")) if isinstance(status, dict) else False
        header = "SUCCESS" if success else "FAILURE"
        state = "running" if isRunning else "exited"
        print(f"{Style.BRIGHT}[Terminal]{Style.RESET_ALL} {header} | id={tid} | state={state}")
        print(f"{Style.BRIGHT}Command:{Style.RESET_ALL} {cmd}")
        if error and not success:
            print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        if isinstance(status, dict) and status.get("output"):
            shown = str(status.get("output") or "")
            if len(shown) > 4000:
                shown = shown[:4000] + "\n... (truncated)"
            print(f"{Style.BRIGHT}Output (tail):{Style.RESET_ALL}\n{shown}")
        else:
            shown = output or ""
            if len(shown) > 4000:
                shown = shown[:4000] + "\n... (truncated)"
            if shown.strip():
                print(f"{Style.BRIGHT}Output:{Style.RESET_ALL}\n{shown}")
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

## 📋 USER CONTEXT
- User rules, current directory, and task list are provided in the user message to keep this system prompt stable for caching.

## 🧩 TOOL TAGS (CLOSED TAGS ONLY)
- Search files:
  <search_files><pattern>**/*.py</pattern></search_files>
- Search in files:
  <search_in_files><regex>...</regex><glob>**/*.py</glob><root>.</root><max_matches>200</max_matches></search_in_files>
- Read file:
  <read_file><path>...</path><start_line>1</start_line><end_line>200</end_line></read_file>
  - Python files annotate indentation as: [s=<spaces> t=<tabs>], and whitespace-only lines show as <WS_ONLY>.
- Write file:
  <write_file><path>...</path><content>...</content></write_file>
- Edit lines:
  <edit_lines><path>...</path><delete_start>10</delete_start><delete_end>20</delete_end><insert_at>10</insert_at><auto_indent>true</auto_indent><content>...</content></edit_lines>
  - insert_at refers to original line numbers; the tool handles offsets.
  - auto_indent aligns inserted Python code to surrounding indentation.
- Run command:
  <run_command><command>...</command><is_long_running>false</is_long_running></run_command>
- Task list:
  <task_add>...</task_add> <task_update>...</task_update> <task_list></task_list> <task_delete>...</task_delete> <task_clear></task_clear>
"""

    def invalidateProjectTreeCache(self) -> None:
        """使项目树缓存失效（下次构造 user 上下文时会重新生成）。"""
        self.cacheOfProjectTree = None

    def invalidateUserRulesCache(self) -> None:
        """使 .voidrules 缓存失效（下次构造 user 上下文时会重新读取）。"""
        self.cacheOfUserRules = None

    def getUserRulesCached(self) -> str:
        """读取并缓存 .voidrules 内容；仅在缓存失效后才重新读取。"""
        if self.cacheOfUserRules is not None:
            return self.cacheOfUserRules

        contentOfRules = ""
        cwd = os.getcwd()
        pathOfRules = os.path.join(cwd, ".voidrules")
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

    def chat(self, inputOfUser: str):
        """
        处理用户输入并启动 AI 代理的多轮任务执行循环。
        
        Args:
            inputOfUser: 用户在控制台输入的原始文本。
        """
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
        while countCycle < self.config.maxCycles:
            try:
                countCycle += 1
                print(f"{Fore.YELLOW}[Cycle {countCycle}/{self.config.maxCycles}] Processing...{Style.RESET_ALL}")

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
                                if not hasReasoned:
                                    hasReasoned = True
                                fullReasoning += reasoning
                                print(f"{Fore.CYAN}{reasoning}{Style.RESET_ALL}", end="", flush=True)

                            # 提取正文内容
                            token = delta.get("content", "")
                            if token:
                                if hasReasoned:
                                    # 如果之前有推理内容，且现在开始输出正文，先换行
                                    print("\n")
                                    hasReasoned = False # 只换行一次
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
                ok, batchApproved = self.confirmBatchExecution(tasks)
                if not ok:
                    historyWorking.append({"role": "user", "content": "User cancelled execution"})
                    isCancelled = True
                for t in tasks:
                    if isCancelled:
                        break
                    isWhitelisted = self.isTaskWhitelisted(t)
                    if isWhitelisted or batchApproved:
                        confirm = "y"
                    else:
                        confirm = input(f"{Style.BRIGHT}Execute this task? (y/n): {Style.RESET_ALL}").strip().lower()
                        if confirm == "":
                            confirm = "y"

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
                            existedBefore = os.path.exists(path)
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
                            if os.path.basename(path).lower() == ".voidrules":
                                self.invalidateUserRulesCache()
                            obs = f"SUCCESS: Saved to {path} | +{added} | -{deleted}"
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
                            if os.path.basename(path).lower() == ".voidrules":
                                self.invalidateUserRulesCache()
                            obs = f"SUCCESS: Edited {path} | +{added} | -{deleted}"
                            observations.append(obs)
                            self.printToolResult(obs)
                        except Exception as e:
                            obs = f"FAILURE: {str(e)}"
                            observations.append(obs)
                            self.printToolResult(obs)

                    elif t["type"] == "read_file":
                        path = os.path.abspath(t["path"])
                        startLine = t.get("start_line", 1)
                        endLine = t.get("end_line")
                        try:
                            totalLines, actualEnd, content = read_range_numbered(path, startLine, endLine)
                            obs = (
                                f"SUCCESS: Read {path}\n"
                                f"Lines: {totalLines} | Range: {startLine}-{actualEnd}\n"
                                f"Content:\n{content}"
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
                                    success, tid, output, error = self.terminalManager.run_command(cmd, is_long_running=is_long)
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


VoidAgent = Agent
