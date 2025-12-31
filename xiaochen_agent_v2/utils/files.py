import difflib
import fnmatch
import locale
import os
import re
from typing import Dict, List, Optional, Tuple


DEFAULT_MAX_READ_LINES = 250
DEFAULT_MAX_READ_CHARS = 20000


import sys

def get_repo_root() -> str:
    """获取项目的根目录。如果是打包后的 EXE，则返回 EXE 所在的目录。"""
    if getattr(sys, 'frozen', False):
        # 打包环境：sys.executable 是 EXE 的完整路径
        return os.path.dirname(os.path.abspath(sys.executable))
    
    # 源码环境：基于当前文件的位置推算
    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.abspath(os.path.join(pkg_dir, ".."))


def get_logs_root() -> str:
    return os.path.join(get_repo_root(), "logs")


def get_sessions_dir() -> str:
    return os.path.join(get_logs_root(), "sessions")


def search_files(pattern: str, root_dir: str, limit: int = 50) -> List[str]:
    results: List[str] = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            path_of_file = os.path.join(root, name)
            rel_path = os.path.relpath(path_of_file, root_dir)
            if _matches_glob(rel_path, pattern):
                results.append(path_of_file)
                if len(results) >= limit:
                    return results
    return results


def _matches_glob(rel_path: str, glob_pattern: str) -> bool:
    norm = rel_path.replace(os.sep, "/")
    gp = glob_pattern.replace("\\", "/")
    candidates = [gp]
    if gp.startswith("./"):
        candidates.append(gp[2:])
    if gp.startswith("**/"):
        candidates.append(gp[3:])

    expanded: List[str] = []
    for cand in candidates:
        expanded.append(cand)
        while "/**/" in cand:
            cand = cand.replace("/**/", "/")
            expanded.append(cand)
        if cand.endswith("/**"):
            expanded.append(cand[:-3])

    for cand in expanded:
        if fnmatch.fnmatch(norm, cand):
            return True
        if fnmatch.fnmatch(os.path.basename(norm), cand):
            return True
    return False


def suggest_similar_patterns(glob_pattern: str, root_dir: str, limit: int = 5) -> List[str]:
    norm = glob_pattern.replace("\\", "/")
    norm = norm[2:] if norm.startswith("./") else norm
    if "/" not in norm:
        return []
    first = norm.split("/", 1)[0]
    if not first or any(ch in first for ch in "*?[]"):
        return []
    try:
        entries = os.listdir(root_dir)
    except Exception:
        return []
    dirs = [e for e in entries if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith(".")]
    matches = difflib.get_close_matches(first, dirs, n=limit, cutoff=0.4)
    if not matches:
        return []
    rest = norm.split("/", 1)[1]
    return [f"{m}/{rest}" for m in matches]


def calculate_diff_of_lines(path_of_file: str, content_new: str) -> Tuple[int, int]:
    """
    计算文件现有内容与新内容之间的行数差异（增加和删除）。
    使用 difflib 进行精确计算。
    """
    if not os.path.exists(path_of_file):
        return len(content_new.splitlines()), 0
    
    lines_old = read_lines_robust(path_of_file)
    lines_new = content_new.splitlines()
    
    added = 0
    deleted = 0
    
    # 使用 difflib 计算差异
    diff = difflib.ndiff(lines_old, lines_new)
    for line in diff:
        if line.startswith("+ "):
            added += 1
        elif line.startswith("- "):
            deleted += 1
            
    return added, deleted


def ensure_parent_dir(path_of_file: str) -> None:
    os.makedirs(os.path.dirname(path_of_file), exist_ok=True)


def read_lines_robust(path_of_file: str) -> List[str]:
    try:
        with open(path_of_file, "r", encoding="utf-8") as f:
            return [line.rstrip("\r\n") for line in f.readlines()]
    except UnicodeDecodeError:
        try:
            with open(path_of_file, "r", encoding=locale.getpreferredencoding()) as f:
                return [line.rstrip("\r\n") for line in f.readlines()]
        except Exception:
            with open(path_of_file, "r", encoding="utf-8", errors="replace") as f:
                return [line.rstrip("\r\n") for line in f.readlines()]


def read_range(path_of_file: str, start_line: int = 1, end_line: Optional[int] = None) -> Tuple[int, int, str]:
    lines_all = read_lines_robust(path_of_file)
    total_lines = len(lines_all)
    if end_line is None:
        actual_end = min(total_lines, max(1, start_line) + DEFAULT_MAX_READ_LINES - 1)
    else:
        actual_end = end_line if end_line <= total_lines else total_lines
    lines_target = lines_all[start_line - 1 : actual_end]
    content = "\n".join(lines_target)
    if len(content) > DEFAULT_MAX_READ_CHARS:
        content = content[:DEFAULT_MAX_READ_CHARS] + "\n... (truncated)"
    return total_lines, actual_end, content


def read_range_numbered(
    path_of_file: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
    indent_mode: str = "smart",
) -> Tuple[int, int, str]:
    lines_all = read_lines_robust(path_of_file)
    total_lines = len(lines_all)
    if end_line is None:
        actual_end = min(total_lines, max(1, start_line) + DEFAULT_MAX_READ_LINES - 1)
    else:
        actual_end = end_line if end_line <= total_lines else total_lines
    lines_target = lines_all[start_line - 1 : actual_end]
    width = len(str(actual_end if actual_end > 0 else 1))
    ext = os.path.splitext(path_of_file)[1].lower()
    mode = str(indent_mode or "smart").strip().lower()

    def _analyze_python_indent(lines: List[str]) -> Tuple[str, int, bool]:
        has_tab = False
        has_space = False
        has_mixed = False
        widths: List[int] = []
        for ln in lines:
            if not ln or ln.strip() == "":
                continue
            ws = re.match(r"[ \t]*", ln).group(0)
            if "\t" in ws and " " in ws:
                has_mixed = True
            if "\t" in ws:
                has_tab = True
            if " " in ws:
                has_space = True
            width_est = len(ws.replace("\t", "    "))
            if width_est > 0:
                widths.append(width_est)
        mixed = has_mixed or (has_tab and has_space)
        if mixed:
            style = "mixed"
        elif has_tab:
            style = "tabs"
        else:
            style = "spaces"
        indent_size = 4
        if widths:
            widths = sorted(set(widths))
            indent_size = widths[0] if widths[0] > 0 else 4
        return style, indent_size, mixed

    if ext in {".py", ".pyw"} and mode in {"smart", "header", "always", "level"}:
        style, indent_size, mixed = _analyze_python_indent(lines_all)
        header = f"indent_style: {style}; indent_size: {indent_size}; mixed: {mixed}"

        numbered = [f"{i:>{width}}: {line if line.strip() != '' else '<WS_ONLY>'}" for i, line in enumerate(lines_target, start=start_line)]
        if mode in {"always", "level"}:
            numbered = numbered
        if mode in {"smart", "header", "always", "level"}:
            numbered = [header] + numbered
    else:
        numbered = [f"{i:>{width}}: {line}" for i, line in enumerate(lines_target, start=start_line)]
    content = "\n".join(numbered)
    if len(content) > DEFAULT_MAX_READ_CHARS:
        content = content[:DEFAULT_MAX_READ_CHARS] + "\n... (truncated)"
    if end_line is None and actual_end < total_lines:
        content = content + f"\n... (truncated lines, showing {start_line}-{actual_end} of {total_lines})"
    return total_lines, actual_end, content


def edit_lines(
    path_of_file: str,
    delete_start: Optional[int] = None,
    delete_end: Optional[int] = None,
    insert_at: Optional[int] = None,
    auto_indent: bool = False,
    content: str = "",
) -> Tuple[str, str]:
    """
    编辑文件的特定行。支持删除范围和在指定位置插入。
    优化了行号偏移处理：insert_at 现在参考的是原始行号。
    """
    if os.path.exists(path_of_file):
        lines = read_lines_robust(path_of_file)
    else:
        lines = []

    original_lines = list(lines)
    before = "\n".join(lines)
    original_lines_count = len(lines)

    # 1. 计算删除范围
    ds = 0
    de = 0
    if delete_start is not None:
        ds = max(1, int(delete_start))
        de = int(delete_end) if delete_end is not None else ds
        de = max(ds, de)
        # 限制在实际行数内
        if original_lines_count > 0:
            ds = min(ds, original_lines_count)
            de = min(de, original_lines_count)
        else:
            ds = 0
            de = 0

    # 2. 计算插入位置（参考原始行号）
    target_insert_index = -1
    if insert_at is not None:
        ins = max(1, int(insert_at))
        # 如果插入位置在删除范围之后，需要根据删除的行数进行偏移
        if ds > 0 and ins > de:
            # 插入点在删除范围之后
            target_insert_index = (ins - 1) - (de - ds + 1)
        elif ds > 0 and ins >= ds:
            # 插入点在删除范围内，默认插在删除后的起始位置
            target_insert_index = ds - 1
        else:
            # 插入点在删除范围之前
            target_insert_index = ins - 1
        
        # 限制在调整后的范围内
        new_total_after_del = original_lines_count - (de - ds + 1) if ds > 0 else original_lines_count
        target_insert_index = max(0, min(target_insert_index, new_total_after_del))

    # 3. 执行删除
    if ds > 0:
        del lines[ds - 1 : de]

    # 4. 执行插入
    if content and target_insert_index != -1:
        insert_lines = content.splitlines()
        if auto_indent and os.path.splitext(path_of_file)[1].lower() in {".py", ".pyw"}:
            ins_line = int(insert_at) if insert_at is not None else (ds if ds > 0 else 1)
            ins_line = max(1, ins_line)
            ins_line = min(ins_line, len(original_lines) if original_lines else 1)
            indent_prefix = ""
            if original_lines:
                start_idx = ins_line - 1
                found_idx = None
                for j in range(start_idx, -1, -1):
                    line = original_lines[j]
                    if line.strip() != "":
                        found_idx = j
                        break
                if found_idx is None:
                    for j in range(start_idx, len(original_lines)):
                        line = original_lines[j]
                        if line.strip() != "":
                            found_idx = j
                            break
                if found_idx is not None:
                    indent_prefix = re.match(r"[ \t]*", original_lines[found_idx]).group(0)

            min_ws = None
            for line in insert_lines:
                if line.strip() == "":
                    continue
                ws = re.match(r"[ \t]*", line).group(0)
                if min_ws is None or len(ws) < min_ws:
                    min_ws = len(ws)
            if min_ws is None:
                min_ws = 0

            normalized: List[str] = []
            for line in insert_lines:
                if line.strip() == "":
                    normalized.append("")
                    continue
                trimmed = line[min_ws:] if len(line) >= min_ws else line.lstrip(" \t")
                normalized.append(f"{indent_prefix}{trimmed}")
            insert_lines = normalized
        lines[target_insert_index : target_insert_index] = insert_lines
    elif content and insert_at is None and ds > 0:
        # 如果指定了删除但没指定插入位置，且有内容，则默认在删除位置插入（即替换）
        lines[ds - 1 : ds - 1] = content.splitlines()

    def _strip_python_module_header(remain_lines: List[str]) -> List[str]:
        """
        移除 Python 文件开头的模块头部块（shebang/encoding/模块 docstring），用于避免重复头部。
        """
        i = 0
        n = len(remain_lines)
        if i < n and remain_lines[i].startswith("#!"):
            i += 1
        while i < n and remain_lines[i].lstrip().startswith("#") and "coding" in remain_lines[i]:
            i += 1
        if i < n and remain_lines[i].strip() in {'"""', "'''"}:
            quote = remain_lines[i].strip()
            i += 1
            while i < n:
                if remain_lines[i].strip() == quote:
                    i += 1
                    break
                i += 1
        while i < n and remain_lines[i].strip() == "":
            i += 1
        return remain_lines[i:]

    ext = os.path.splitext(path_of_file)[1].lower()
    if ext in {".py", ".pyw"} and insert_at == 1 and ds == 1 and de <= 3 and content:
        has_new_header = False
        head_lines = content.splitlines()[:10]
        if any(l.startswith("#!") for l in head_lines) or any("coding" in l for l in head_lines):
            has_new_header = True
        if any(l.strip() in {'"""', "'''"} for l in head_lines):
            has_new_header = True
        if has_new_header:
            inserted_len = len(content.splitlines()) if content else 0
            if inserted_len > 0 and inserted_len <= len(lines):
                tail = lines[inserted_len:]
                if tail and (tail[0].startswith("#!") or "coding" in tail[0] or tail[0].strip() in {'"""', "'''"}):
                    lines = lines[:inserted_len] + _strip_python_module_header(tail)

    after = "\n".join(lines)
    return before, after


def cleanup_directory(directory: str, max_files: int = 50, pattern: str = "*") -> int:
    """
    清理指定目录中的文件，如果文件数量超过 max_files，则删除最早的文件。
    
    Args:
        directory: 要清理的目录路径
        max_files: 允许保留的最大文件数量
        pattern: 匹配文件的通配符模式
        
    Returns:
        已删除的文件数量
    """
    if not os.path.exists(directory):
        return 0
    
    files = []
    for filename in os.listdir(directory):
        if not fnmatch.fnmatch(filename, pattern):
            continue
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            files.append((filepath, os.path.getmtime(filepath)))
    
    if len(files) <= max_files:
        return 0
    
    # 按修改时间升序排列（最早的在前）
    files.sort(key=lambda x: x[1])
    
    to_delete = files[:len(files) - max_files]
    deleted_count = 0
    for filepath, _ in to_delete:
        try:
            os.remove(filepath)
            deleted_count += 1
        except Exception:
            pass
            
    return deleted_count


def search_in_files(
    regex: str,
    root_dir: str,
    glob_pattern: str = "**/*",
    max_matches: int = 200,
) -> Tuple[Dict[str, List[Tuple[int, str]]], Optional[str]]:
    try:
        re_obj = re.compile(regex)
    except re.error as e:
        return {}, str(e)

    matches_by_path: Dict[str, List[Tuple[int, str]]] = {}
    count_matches = 0

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            path_of_file = os.path.join(root, name)
            rel_path = os.path.relpath(path_of_file, root_dir)
            if not _matches_glob(rel_path, glob_pattern):
                continue
            try:
                lines_all = read_lines_robust(path_of_file)
            except Exception:
                continue
            for line_no, line in enumerate(lines_all, start=1):
                if re_obj.search(line):
                    matches_by_path.setdefault(path_of_file, []).append((line_no, line))
                    count_matches += 1
                    if count_matches >= max_matches:
                        return matches_by_path, None

    return matches_by_path, None


class TreeNode:
    name: str
    children: Dict[str, "TreeNode"]

    def __init__(self, name: str):
        self.name = name
        self.children = {}


def generate_dir_tree(
    root_dir: str,
    max_depth: int = 3,
    max_entries: int = 300,
) -> str:
    root_dir_abs = os.path.abspath(root_dir)
    collapse_dir_names = {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        "out",
        "coverage",
        "logs",
        "tmp",
        "temp",
        ".cache",
    }
    lines: List[str] = [f"{root_dir_abs}/"]
    count = 0

    def list_dir(path: str) -> Tuple[List[os.DirEntry], List[os.DirEntry]]:
        try:
            entries = list(os.scandir(path))
        except Exception:
            return [], []
        dirs = [e for e in entries if e.is_dir(follow_symlinks=False) and not e.name.startswith(".")]
        files = [e for e in entries if e.is_file(follow_symlinks=False) and not e.name.startswith(".")]
        dirs.sort(key=lambda e: e.name.lower())
        files.sort(key=lambda e: e.name.lower())
        return dirs, files

    def walk_dir(path: str, prefix: str, depth: int) -> None:
        nonlocal count
        if count >= max_entries:
            return
        if depth >= max_depth:
            lines.append(f"{prefix}└── ...")
            count += 1
            return

        dirs, files = list_dir(path)
        items: List[Tuple[str, Optional[os.DirEntry]]] = []
        for d in dirs:
            items.append(("dir", d))
        for f in files:
            items.append(("file", f))

        for idx, (kind, entry) in enumerate(items):
            if count >= max_entries:
                break
            is_last = idx == len(items) - 1
            connector = "└── " if is_last else "├── "
            if entry is None:
                continue
            should_collapse = kind == "dir" and entry.name in collapse_dir_names
            name = entry.name + ("/" if kind == "dir" else "")
            lines.append(f"{prefix}{connector}{name}")
            count += 1
            if kind == "dir" and not should_collapse:
                next_prefix = prefix + ("    " if is_last else "│   ")
                walk_dir(entry.path, next_prefix, depth + 1)

    walk_dir(root_dir_abs, "", 0)
    if count >= max_entries:
        lines.append("... (truncated)")
    return "\n".join(lines)


def generate_tree_structure(paths: List[str], cwd: str) -> str:
    if not paths:
        return ""

    paths = sorted(paths)

    if len(paths) == 1:
        common_root = os.path.dirname(paths[0])
    else:
        common_root = os.path.commonpath(paths)
        if not os.path.isdir(common_root):
            common_root = os.path.dirname(common_root)

    if not common_root or common_root == os.path.splitdrive(cwd)[0]:
        common_root = cwd

    tree_lines = [f"{common_root}/"]
    root_node = TreeNode("")

    for path in paths:
        rel_path = os.path.relpath(path, common_root)
        parts = rel_path.split(os.sep)
        curr = root_node
        for part in parts:
            if part not in curr.children:
                curr.children[part] = TreeNode(part)
            curr = curr.children[part]

    def build_tree_string(node: TreeNode, prefix: str = "", is_last: bool = True) -> List[str]:
        lines: List[str] = []
        if node.name:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{node.name}")
            prefix = prefix + ("    " if is_last else "│   ")

        children = list(node.children.values())
        for idx, child in enumerate(children):
            lines.extend(build_tree_string(child, prefix, idx == len(children) - 1))
        return lines

    tree_lines.extend(build_tree_string(root_node))
    return "\n".join(tree_lines)


def generate_match_tree(
    matches_by_path: Dict[str, List[Tuple[int, str]]],
    root_dir: str,
) -> str:
    if not matches_by_path:
        return f"{root_dir}/"

    root_dir_abs = os.path.abspath(root_dir)
    tree_lines = [f"{root_dir_abs}/"]

    root_node = TreeNode("")
    matches_of_rel_path: Dict[str, List[Tuple[int, str]]] = {}
    for abs_path, matches in matches_by_path.items():
        rel_path = os.path.relpath(abs_path, root_dir_abs)
        matches_of_rel_path[rel_path] = matches
        parts = rel_path.split(os.sep)
        curr = root_node
        for part in parts:
            if part not in curr.children:
                curr.children[part] = TreeNode(part)
            curr = curr.children[part]

    def build_tree_lines(node: TreeNode, prefix: str = "", is_last: bool = True, path_parts: Optional[List[str]] = None) -> List[str]:
        if path_parts is None:
            path_parts = []
        lines: List[str] = []
        if node.name:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{node.name}")
            next_prefix = prefix + ("    " if is_last else "│   ")
            path_parts = path_parts + [node.name]
        else:
            next_prefix = prefix

        rel_path = os.sep.join(path_parts)
        if rel_path in matches_of_rel_path:
            matches = matches_of_rel_path[rel_path]
            for idx, (line_no, line) in enumerate(matches):
                line_connector = "└── " if idx == len(matches) - 1 else "├── "
                shown = line.rstrip()
                if len(shown) > 240:
                    shown = shown[:240] + "..."
                lines.append(f"{next_prefix}{line_connector}L{line_no}: {shown}")

        children = list(node.children.values())
        for idx, child in enumerate(children):
            lines.extend(build_tree_lines(child, next_prefix, idx == len(children) - 1, path_parts))
        return lines

    tree_lines.extend(build_tree_lines(root_node))
    return "\n".join(tree_lines)
