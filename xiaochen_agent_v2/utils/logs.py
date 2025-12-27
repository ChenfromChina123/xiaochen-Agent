import datetime
import json
import os
import base64
import gzip
import hashlib
from typing import Any, Dict, List, Optional, Tuple


def log_request(messages: List[Dict[str, str]], log_dir: str = "logs") -> None:
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"void_chat_{timestamp}.json")

    messages_to_log: List[Dict[str, object]] = []
    for msg in messages:
        msg_copy: Dict[str, object] = msg.copy()
        if "content" in msg_copy and isinstance(msg_copy["content"], str):
            if msg_copy.get("role") == "system":
                msg_copy["content"] = str(msg_copy["content"]).splitlines()
            else:
                msg_copy["content"] = str(msg_copy["content"]).splitlines()
        messages_to_log.append(msg_copy)

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(messages_to_log, f, ensure_ascii=False, indent=2)


def append_usage_history(
    usage: Dict[str, Any],
    cache: Optional[Dict[str, Any]] = None,
    history_file: str = os.path.join("logs", "void_usage_history.jsonl"),
) -> None:
    """将模型返回的 usage（以及可选缓存统计）按行追加写入日志文件。"""
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    record: Dict[str, Any] = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "cwd": os.getcwd(),
        "usage": usage,
    }
    if cache is not None:
        record["cache"] = cache
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _encode_text(content: str) -> str:
    raw = content.encode("utf-8")
    gz = gzip.compress(raw)
    return base64.b64encode(gz).decode("ascii")


def _decode_text(payload: str) -> str:
    gz = base64.b64decode(payload.encode("ascii"))
    raw = gzip.decompress(gz)
    return raw.decode("utf-8")


def append_edit_history(
    path_of_file: str,
    before_content: str,
    after_content: str,
    meta: Optional[Dict[str, Any]] = None,
    history_file: str = os.path.join("logs", "void_edit_history.jsonl"),
) -> None:
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    record = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "cwd": os.getcwd(),
        "path": os.path.abspath(path_of_file),
        "meta": meta or {},
        "before_sha256": _sha256_text(before_content),
        "after_sha256": _sha256_text(after_content),
        "before_gzip_b64": _encode_text(before_content),
    }
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_history_lines(history_file: str) -> List[str]:
    if not os.path.exists(history_file):
        return []
    with open(history_file, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f.readlines() if line.strip()]


def rollback_last_edit(
    history_file: str = os.path.join("logs", "void_edit_history.jsonl"),
) -> Tuple[bool, str]:
    lines = _read_history_lines(history_file)
    if not lines:
        return False, "No edit history found"

    last_line = lines[-1]
    try:
        record = json.loads(last_line)
    except Exception:
        return False, "Invalid edit history record"

    path_of_file = str(record.get("path") or "")
    before_payload = str(record.get("before_gzip_b64") or "")
    if not path_of_file or not before_payload:
        return False, "Incomplete edit history record"

    before_content = _decode_text(before_payload)
    os.makedirs(os.path.dirname(path_of_file), exist_ok=True)
    with open(path_of_file, "w", encoding="utf-8") as f:
        f.write(before_content)

    with open(history_file, "w", encoding="utf-8") as f:
        for line in lines[:-1]:
            f.write(line + "\n")

    return True, f"Rolled back: {path_of_file}"
