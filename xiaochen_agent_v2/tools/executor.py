import os
import re
import time
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple, Any

from ..utils.console import Fore, Style
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
from ..utils.display import print_tool_execution_header
from ..utils.logs import append_edit_history
from .web_search import web_search, visit_page, format_search_results
from .ocr import ocr_image, ocr_document
from ..core.utils import validate_python_file

class Tools:
    def __init__(self, agent):
        self.agent = agent

    def _validate_python_file(self, path: str) -> Tuple[bool, str]:
        """Wrapper for agent's validate_python_file or direct util call"""
        return self.agent._validate_python_file(path)

    def search_files(self, t: Dict[str, Any]) -> str:
        pattern = t["pattern"]
        try:
            results = search_files(pattern, os.getcwd())
            if results:
                treeOutput = generate_tree_structure(results, os.getcwd())
                return f"SUCCESS: Found {len(results)} files:\n{treeOutput}"
            else:
                suggestions = suggest_similar_patterns(pattern, os.getcwd())
                if suggestions:
                    sug = "\n".join([f"- {s}" for s in suggestions])
                    return f"SUCCESS: No files found matching {pattern}\nSuggestions:\n{sug}"
                else:
                    return f"SUCCESS: No files found matching {pattern}"
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def search_in_files(self, t: Dict[str, Any]) -> str:
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
                return f"FAILURE: Invalid regex: {error}"
            elif matches_by_path:
                treeOutput = generate_match_tree(matches_by_path, root)
                totalMatches = sum(len(v) for v in matches_by_path.values())
                return (
                    "SUCCESS: Regex matches found\n"
                    f"Regex: {regex}\n"
                    f"Glob: {glob_pattern}\n"
                    f"Matches: {totalMatches} (files: {len(matches_by_path)})\n"
                    f"{treeOutput}"
                )
            else:
                return (
                    "SUCCESS: No regex matches found\n"
                    f"Regex: {regex}\n"
                    f"Glob: {glob_pattern}\n"
                    f"Root: {root}"
                )
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def write_file(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        content = t["content"]
        try:
            overwrite = bool(t.get("overwrite") or False)
            if os.path.exists(path) and not overwrite:
                return (
                    "FAILURE: Refuse to overwrite existing file via write_file. "
                    "Use edit_lines, or set <overwrite>true</overwrite> explicitly."
                )

            self.agent.backupFile(path)
            ensure_parent_dir(path)
            before_content = self.agent.cacheOfBackups.get(path, "")
            added, deleted = calculate_diff_of_lines(path, content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.agent.historyOfOperations.append((path, added, deleted))
            append_edit_history(
                path_of_file=path,
                before_content=before_content,
                after_content=content,
                meta={"type": "write_file"},
            )
            self.agent.invalidateProjectTreeCache()
            self.agent._invalidate_read_cache_for_path(path)
            if os.path.basename(path).lower() == "userrules":
                self.agent.invalidateUserRulesCache()
            obs = f"SUCCESS: Saved to {path} | +{added} | -{deleted}"
            ext = os.path.splitext(path)[1].lower()
            if ext in {".py", ".pyw"}:
                ok, detail = self._validate_python_file(path)
                if not ok:
                    obs = f"FAILURE: Python validation failed: {path}\n{detail}"
            return obs
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def replace_in_file(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        search_text = str(t.get("search") or "")
        replace_text = str(t.get("replace") or "")
        count = int(t.get("count") or 1)
        is_regex = bool(t.get("regex") or False)
        auto_indent = bool(t.get("auto_indent") or False)
        try:
            if not os.path.exists(path):
                return f"FAILURE: File not found: {path}"
            if count <= 0:
                count = 1
            ext = os.path.splitext(path)[1].lower()
            if is_regex and auto_indent and ext in {".py", ".pyw"}:
                return "FAILURE: replace_in_file with regex does not support auto_indent"

            self.agent.backupFile(path)
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
                return "FAILURE: replace_in_file did not find any match to replace"

            added, deleted = calculate_diff_of_lines(path, after_content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(after_content)

            self.agent.historyOfOperations.append((path, added, deleted))
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
            self.agent.invalidateProjectTreeCache()
            self.agent._invalidate_read_cache_for_path(path)
            if os.path.basename(path).lower() == "userrules":
                self.agent.invalidateUserRulesCache()

            obs = f"SUCCESS: Replaced in {path} | times={replaced_times} | +{added} | -{deleted}"
            if ext in {".py", ".pyw"}:
                ok, detail = self._validate_python_file(path)
                if not ok:
                    obs = f"FAILURE: Python validation failed: {path}\n{detail}"
            return obs
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def edit_lines(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        delete_start = t.get("delete_start")
        delete_end = t.get("delete_end")
        insert_at = t.get("insert_at")
        auto_indent = bool(t.get("auto_indent") or False)
        content = t.get("content", "")
        try:
            self.agent.backupFile(path)
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
            self.agent.historyOfOperations.append((path, added, deleted))
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
            self.agent.invalidateProjectTreeCache()
            self.agent._invalidate_read_cache_for_path(path)
            if os.path.basename(path).lower() == "userrules":
                self.agent.invalidateUserRulesCache()
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
            return obs
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def copy_lines(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        start_line = int(t.get("start_line") or 1)
        end_line = int(t.get("end_line") or 1)
        register = str(t.get("register") or "default")
        
        try:
            if not os.path.exists(path):
                return f"FAILURE: File not found: {path}"
                
            content = read_lines_range_raw(path, start_line, end_line)
            
            self.agent.clipboard[register] = content
            
            line_count = len(content.splitlines())
            return f"SUCCESS: Copied {line_count} lines from {path} ({start_line}-{end_line}) to register '{register}'"
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def paste_lines(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        insert_at = int(t.get("insert_at") or 1)
        register = str(t.get("register") or "default")
        auto_indent = bool(t.get("auto_indent") or True)
        
        try:
            content = self.agent.clipboard.get(register)
            if content is None:
                return f"FAILURE: Register '{register}' is empty"
                
            return self.edit_lines({
                "type": "edit_lines",
                "path": path,
                "insert_at": insert_at,
                "content": content,
                "auto_indent": auto_indent
            })
        except Exception as e:
            return f"FAILURE: {str(e)}"
            
    def web_search(self, t: Dict[str, Any]) -> str:
        query = str(t.get("query", "")).strip()
        engine = str(t.get("engine", "bing")).strip()
        max_results = int(t.get("max_results", 3))
        
        if not query:
            return "FAILURE: 搜索关键词不能为空"
        else:
            try:
                success, error, results = web_search(
                    query=query,
                    engine=engine,
                    max_results=max_results,
                    timeout=30
                )
                
                if success:
                    formatted_results = format_search_results(results, query)
                    return f"SUCCESS: 网络搜索完成\n{formatted_results}"
                else:
                    return f"FAILURE: 搜索失败 - {error}"
            except Exception as e:
                return f"FAILURE: 搜索异常 - {str(e)}"

    def visit_page(self, t: Dict[str, Any]) -> str:
        url = str(t.get("url", "")).strip()
        if not url:
            return "FAILURE: 网页链接不能为空"
        else:
            try:
                success, error, content = visit_page(url, timeout=30)
                if success:
                    return f"SUCCESS: 网页内容获取成功\nURL: {url}\n\n{content}"
                else:
                    return f"FAILURE: 访问失败 - {error}"
            except Exception as e:
                return f"FAILURE: 访问异常 - {str(e)}"

    def indent_lines(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        start_line = int(t.get("start_line"))
        end_line = int(t.get("end_line"))
        spaces = int(t.get("spaces", 4))
        try:
            self.agent.backupFile(path)
            ensure_parent_dir(path)
            before_content, after_content = indent_lines_range(
                path_of_file=path,
                start_line=start_line,
                end_line=end_line,
                spaces=spaces,
            )
            added, deleted = calculate_diff_of_lines(path, after_content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(after_content)
            self.agent.historyOfOperations.append((path, added, deleted))
            append_edit_history(
                path_of_file=path,
                before_content=before_content,
                after_content=after_content,
                meta={
                    "type": "indent_lines",
                    "start_line": start_line,
                    "end_line": end_line,
                    "spaces": spaces,
                },
            )
            self.agent.invalidateProjectTreeCache()
            self.agent._invalidate_read_cache_for_path(path)
            if os.path.basename(path).lower() == "userrules":
                self.agent.invalidateUserRulesCache()
            ext = os.path.splitext(path)[1].lower()
            obs = f"SUCCESS: Indented {path} | range={start_line}-{end_line} | spaces={spaces} | +{added} | -{deleted}"
            if ext in {".py", ".pyw"}:
                ok, detail = self._validate_python_file(path)
                if not ok:
                    obs = f"FAILURE: Python validation failed: {path}\n{detail}"
            return obs
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def dedent_lines(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        start_line = int(t.get("start_line"))
        end_line = int(t.get("end_line"))
        spaces = int(t.get("spaces", 4))
        try:
            self.agent.backupFile(path)
            ensure_parent_dir(path)
            before_content, after_content = dedent_lines_range(
                path_of_file=path,
                start_line=start_line,
                end_line=end_line,
                spaces=spaces,
            )
            added, deleted = calculate_diff_of_lines(path, after_content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(after_content)
            self.agent.historyOfOperations.append((path, added, deleted))
            append_edit_history(
                path_of_file=path,
                before_content=before_content,
                after_content=after_content,
                meta={
                    "type": "dedent_lines",
                    "start_line": start_line,
                    "end_line": end_line,
                    "spaces": spaces,
                },
            )
            self.agent.invalidateProjectTreeCache()
            self.agent._invalidate_read_cache_for_path(path)
            if os.path.basename(path).lower() == "userrules":
                self.agent.invalidateUserRulesCache()
            ext = os.path.splitext(path)[1].lower()
            obs = f"SUCCESS: Dedented {path} | range={start_line}-{end_line} | spaces={spaces} | +{added} | -{deleted}"
            if ext in {".py", ".pyw"}:
                ok, detail = self._validate_python_file(path)
                if not ok:
                    obs = f"FAILURE: Python validation failed: {path}\n{detail}"
            return obs
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def read_file(self, t: Dict[str, Any]) -> str:
        path = os.path.abspath(t["path"])
        startLine = t.get("start_line")
        endLine = t.get("end_line")
        try:
            if startLine is None or endLine is None:
                return "FAILURE: read_file requires both start_line and end_line"
            startLine = int(startLine)
            endLine = int(endLine)
            if startLine < 1 or endLine < startLine:
                return f"FAILURE: Invalid range: {startLine}-{endLine}"

            max_window = 160
            orig_end = endLine
            if endLine - startLine + 1 > max_window:
                endLine = startLine + max_window - 1

            if not os.path.exists(path):
                return f"FAILURE: File not found: {path}"

            mtime = 0.0
            try:
                mtime = float(os.path.getmtime(path))
            except Exception:
                mtime = 0.0
            key = (path, startLine, endLine)
            cached = self.agent._recentReadCache.get(key)
            if cached is not None and cached[0] >= mtime:
                return (
                    "SUCCESS: Read skipped (duplicate)\n"
                    f"File: {path}\n"
                    f"Range: {startLine}-{endLine}\n"
                    "Content: <omitted>"
                )

            totalLines, actualEnd, content = read_range_numbered(
                path,
                startLine,
                endLine,
                indent_mode=getattr(self.agent, "readIndentMode", "smart"),
            )
            self.agent._recentReadCache[key] = (mtime, time.time())
            if len(self.agent._recentReadCache) > 200:
                items = sorted(self.agent._recentReadCache.items(), key=lambda kv: kv[1][1])
                for k, _v in items[: max(0, len(items) - 200)]:
                    self.agent._recentReadCache.pop(k, None)
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
            return obs
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def run_command(self, t: Dict[str, Any]) -> str:
        cmd_text = str(t["command"])
        is_long = str(t.get("is_long_running", "false")).lower() == "true"
        cwd = t.get("cwd")
        
        commands = [c.strip() for c in cmd_text.splitlines() if c.strip()]
        if not commands:
            return "FAILURE: Empty command"
        
        # Only execute the first command for now if multiple, or loop?
        # Agent implementation loops but returns only one observation usually?
        # Wait, Agent implementation loops and appends to observations list.
        # But Tool method usually returns a single string.
        # If I return a single string, I should join them?
        # But run_command in Agent iterates and appends observations.
        # If there are multiple commands, it produces multiple observations.
        # My Tools interface assumes one tool dict -> one string result.
        # If run_command handles multiple commands in one tool call, I should combine results.
        
        results = []
        for cmd in commands:
            dangerousCmds = ["rm -rf", "format", "del /f/s/q", "mkfs"]
            if any(d in cmd.lower() for d in dangerousCmds):
                results.append(f"FAILURE: Dangerous command blocked: {cmd}")
                continue
            
            try:
                run_cwd = None
                if cwd is not None and str(cwd).strip():
                    run_cwd = os.path.abspath(str(cwd).strip())
                success, tid, output, error = self.agent.terminalManager.run_command(cmd, is_long_running=is_long, cwd=run_cwd)
                if success:
                    status = self.agent.terminalManager.get_terminal_status(tid)
                    isRunning = bool(status.get("is_running")) if isinstance(status, dict) else False
                    if isRunning:
                        obs = (
                            "SUCCESS: Command started (running)\n"
                            f"Terminal ID: {tid}\n"
                            f"Command: {cmd}\n"
                            f"{output}\n"
                            f"{self.agent.renderRunningTerminals()}"
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
                
                self.agent.printRunCommandSummary(tid=tid, cmd=cmd, success=success, output=output, error=error)
                results.append(obs)
            except Exception as e:
                results.append(f"FAILURE: {str(e)}")
        
        return "\n\n".join(results)

    def task_add(self, t: Dict[str, Any]) -> str:
        content = str(t.get("content") or "").strip()
        status = str(t.get("status") or "").strip() or None
        tid = str(t.get("id") or "").strip() or None
        progress = t.get("progress")
        if not content:
            return "FAILURE: task_add missing <content>"
        
        item = self.agent.taskManager.add(content, id=tid, status=status, progress=progress)
        self.agent.printTaskProgress()
        return f"SUCCESS: Task added ({item.id})"

    def task_update(self, t: Dict[str, Any]) -> str:
        tid = str(t.get("id") or "").strip()
        content = t.get("content")
        status = t.get("status")
        progress = t.get("progress")
        item = self.agent.taskManager.update(tid, content=content, status=status, progress=progress)
        if not item:
            return f"FAILURE: Task not found: {tid}"
        
        self.agent.printTaskProgress()
        return f"SUCCESS: Task updated ({item.id})"

    def task_delete(self, t: Dict[str, Any]) -> str:
        tid = str(t.get("id") or "").strip()
        ok = self.agent.taskManager.delete(tid)
        if not ok:
            return f"FAILURE: Task not found: {tid}"
        
        self.agent.printTaskProgress()
        return f"SUCCESS: Task deleted ({tid})"

    def task_clear(self, t: Dict[str, Any]) -> str:
        self.agent.taskManager.clear()
        self.agent.printTaskProgress()
        return "SUCCESS: Tasks cleared"

    def task_list(self, t: Dict[str, Any]) -> str:
        self.agent.printTaskProgress()
        return "SUCCESS: Task list\n" + self.agent.taskManager.render()

    def ocr_image(self, t: Dict[str, Any], index: int = 1, total: int = 1) -> str:
        path = os.path.abspath(t["path"])
        try:
            print_tool_execution_header({"type": "ocr_image", "path": path}, index, total)
            result = ocr_image(path)
            if result.get("code") == 100:
                text = result.get("text", "")
                saved_path = result.get("saved_path", "")
                save_msg = f"\n(结果已保存至: {saved_path})" if saved_path else ""
                return f"SUCCESS: OCR completed{save_msg}\n\n{text}"
            else:
                return f"FAILURE: OCR failed (code: {result.get('code')})\nError: {result.get('data')}"
        except Exception as e:
            return f"FAILURE: {str(e)}"

    def ocr_document(self, t: Dict[str, Any], index: int = 1, total: int = 1) -> str:
        path = os.path.abspath(t["path"])
        page_start = int(t.get("page_start") or 1)
        page_end = t.get("page_end")
        if page_end is not None:
            page_end = int(page_end)
        
        try:
            print_tool_execution_header({
                "type": "ocr_document",
                "path": path,
                "page_start": page_start,
                "page_end": page_end
            }, index, total)
            result = ocr_document(path, page_start=page_start, page_end=page_end)
            if result.get("code") == 100:
                text = result.get("text", "")
                saved_path = result.get("saved_path", "")
                save_msg = f"\n(结果已保存至: {saved_path})" if saved_path else ""
                return f"SUCCESS: Document OCR completed{save_msg}\n\n{text}"
            else:
                return f"FAILURE: Document OCR failed (code: {result.get('code')})\nError: {result.get('data')}"
        except Exception as e:
            return f"FAILURE: {str(e)}"
