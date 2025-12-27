import difflib
import fnmatch
import locale
import os
import re
from typing import Dict, List, Optional, Tuple


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
    actual_end = end_line if end_line and end_line <= total_lines else total_lines
    lines_target = lines_all[start_line - 1 : actual_end]
    content = "\n".join(lines_target)
    return total_lines, actual_end, content


def read_range_numbered(
    path_of_file: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
) -> Tuple[int, int, str]:
    lines_all = read_lines_robust(path_of_file)
    total_lines = len(lines_all)
    actual_end = end_line if end_line and end_line <= total_lines else total_lines
    lines_target = lines_all[start_line - 1 : actual_end]
    width = len(str(actual_end if actual_end > 0 else 1))
    ext = os.path.splitext(path_of_file)[1].lower()
    if ext in {".py", ".pyw"}:
        numbered: List[str] = []
        for i, line in enumerate(lines_target, start=start_line):
            spaces = 0
            tabs = 0
            for ch in line:
                if ch == " ":
                    spaces += 1
                elif ch == "\t":
                    tabs += 1
                else:
                    break
            if line and line.strip() == "":
                shown = "<WS_ONLY>"
            else:
                shown = line
            numbered.append(f"{i:>{width}}: [s={spaces} t={tabs}] {shown}")
    else:
        numbered = [f"{i:>{width}}: {line}" for i, line in enumerate(lines_target, start=start_line)]
    return total_lines, actual_end, "\n".join(numbered)


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
                for j in range(start_idx, -1, -1):
                    line = original_lines[j]
                    if line.strip() != "":
                        indent_prefix = re.match(r"[ \t]*", line).group(0)
                        break

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

    after = "\n".join(lines)
    return before, after


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
