import textwrap
from typing import Any, Dict, List, Optional, Tuple


def _find_tag_span(source: str, tag: str) -> Optional[Tuple[int, int]]:
    """返回指定tag在source中对应的(inner_start, inner_end)区间，大小写不敏感。"""
    s = f"<{tag}>"
    e = f"</{tag}>"
    si = source.find(s)
    if si != -1:
        ei = source.find(e, si + len(s))
        if ei != -1:
            return si + len(s), ei

    source_lower = source.lower()
    s_lower = f"<{tag.lower()}>"
    e_lower = f"</{tag.lower()}>"
    si_lower = source_lower.find(s_lower)
    if si_lower != -1:
        ei_lower = source_lower.find(e_lower, si_lower + len(s_lower))
        if ei_lower != -1:
            return si_lower + len(s_lower), ei_lower

    return None


def _normalize_block_text(raw: str) -> str:
    """去除标签缩进带来的公共前导空白，保留相对缩进。"""
    if raw.startswith("\r\n"):
        raw = raw[2:]
    elif raw.startswith("\n"):
        raw = raw[1:]

    if raw.endswith("\r\n"):
        raw = raw[:-2]
    elif raw.endswith("\n"):
        raw = raw[:-1]

    return textwrap.dedent(raw)


def find_substring(source: str, sub: str, *, keep_indentation: bool = False) -> str:
    """提取子标签内容。

    - keep_indentation=False：默认行为，去掉首尾空白。
    - keep_indentation=True：用于<content>类多行块，保留相对缩进并去除标签缩进影响。
    """
    span = _find_tag_span(source, sub)
    if span is None:
        return ""
    inner = source[span[0] : span[1]]
    if keep_indentation:
        return _normalize_block_text(inner)
    return inner.strip()


def parse_stack_of_tags(text: str) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    text_lower = text.lower()
    valid_tags = [
        "write_file",
        "read_file",
        "run_command",
        "search_files",
        "search_in_files",
        "edit_lines",
        "task_add",
        "task_update",
        "task_delete",
        "task_list",
        "task_clear",
    ]
    idx = 0

    while idx < len(text):
        next_tag = None
        next_start = -1
        for tag in valid_tags:
            start_tag = f"<{tag}>"
            s_idx = text.find(start_tag, idx)
            if s_idx == -1:
                s_idx = text_lower.find(start_tag, idx)
            if s_idx == -1:
                continue
            if next_start == -1 or s_idx < next_start:
                next_start = s_idx
                next_tag = tag

        if next_start == -1 or not next_tag:
            break

        start_tag = f"<{next_tag}>"
        end_tag = f"</{next_tag}>"
        e_idx = text.find(end_tag, next_start + len(start_tag))
        if e_idx == -1:
            e_idx = text_lower.find(end_tag, next_start + len(start_tag))
        if e_idx == -1:
            idx = next_start + len(start_tag)
            continue

        inner = text[next_start + len(start_tag) : e_idx].strip()
        task: Dict[str, Any] = {"type": next_tag}

        if next_tag == "write_file":
            task["path"] = find_substring(inner, "path")
            task["content"] = find_substring(inner, "content", keep_indentation=True)
            if not task["path"] or not task["content"]:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "read_file":
            task["path"] = find_substring(inner, "path")
            start_line_str = find_substring(inner, "start_line")
            end_line_str = find_substring(inner, "end_line")
            task["start_line"] = int(start_line_str) if start_line_str.strip() else 1
            task["end_line"] = int(end_line_str) if end_line_str.strip() else None
            if not task["path"]:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "run_command":
            task["command"] = find_substring(inner, "command") or inner.strip()
            if not task["command"]:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "search_files":
            task["pattern"] = find_substring(inner, "pattern") or "*"
        elif next_tag == "search_in_files":
            task["regex"] = find_substring(inner, "regex")
            task["glob"] = find_substring(inner, "glob") or "**/*"
            task["root"] = find_substring(inner, "root") or "."
            max_matches_str = find_substring(inner, "max_matches")
            task["max_matches"] = int(max_matches_str) if max_matches_str.strip() else 200
            if not task["regex"]:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "edit_lines":
            task["path"] = find_substring(inner, "path")
            delete_start_str = find_substring(inner, "delete_start")
            delete_end_str = find_substring(inner, "delete_end")
            insert_at_str = find_substring(inner, "insert_at")
            auto_indent_str = find_substring(inner, "auto_indent")
            task["delete_start"] = int(delete_start_str) if delete_start_str.strip() else None
            task["delete_end"] = int(delete_end_str) if delete_end_str.strip() else None
            task["insert_at"] = int(insert_at_str) if insert_at_str.strip() else None
            task["auto_indent"] = auto_indent_str.strip().lower() in {"1", "true", "yes", "y", "on"}
            task["content"] = find_substring(inner, "content", keep_indentation=True)
            if not task["path"]:
                idx = e_idx + len(end_tag)
                continue
            if task["delete_start"] is None and task["insert_at"] is None and not task["content"]:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "task_add":
            task["id"] = find_substring(inner, "id")
            task["content"] = find_substring(inner, "content", keep_indentation=True) or find_substring(inner, "title")
            task["status"] = find_substring(inner, "status") or "pending"
            progress_str = find_substring(inner, "progress")
            task["progress"] = int(progress_str) if progress_str.strip() else None
            if not task["content"]:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "task_update":
            task["id"] = find_substring(inner, "id")
            task["content"] = find_substring(inner, "content", keep_indentation=True) or find_substring(inner, "title")
            task["status"] = find_substring(inner, "status")
            progress_str = find_substring(inner, "progress")
            task["progress"] = int(progress_str) if progress_str.strip() else None
            if not task["id"]:
                idx = e_idx + len(end_tag)
                continue
            if not task["content"] and not task["status"] and task["progress"] is None:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "task_delete":
            task["id"] = find_substring(inner, "id")
            if not task["id"]:
                idx = e_idx + len(end_tag)
                continue
        elif next_tag == "task_list":
            pass
        elif next_tag == "task_clear":
            pass

        tasks.append(task)
        idx = e_idx + len(end_tag)

    return tasks
