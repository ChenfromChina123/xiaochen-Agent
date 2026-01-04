import shutil
import subprocess
import sys
import traceback
import py_compile
from typing import List, Optional, Tuple, Dict
from ..utils.display import format_tool_display

try:
    import requests
except Exception:
    requests = None

try:
    import urllib3
except Exception:
    urllib3 = None

def require_requests() -> bool:
    """
    检查 requests 依赖是否可用。

    Returns:
        是否可用
    """
    return requests is not None

def detect_ruff_runner(cached_runner: Optional[List[str]], python_validate_ruff: str) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    """
    探测 ruff 可用的执行方式。

    Args:
        cached_runner: 缓存的 ruff 执行命令列表
        python_validate_ruff: 用户配置的 ruff 验证设置

    Returns:
        (新的 cached_runner, ruff_runner)
    """
    setting = str(python_validate_ruff or "auto").strip().lower()
    if setting in {"0", "false", "off", "no", "disable", "disabled"}:
        return None, None

    if cached_runner is not None:
        return cached_runner, cached_runner

    exe = shutil.which("ruff")
    if exe:
        new_cached = [exe]
        return new_cached, new_cached

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
            new_cached = [sys.executable, "-m", "ruff"]
            return new_cached, new_cached
    except Exception:
        pass

    return None, None

def validate_python_file(path: str, runner: Optional[List[str]]) -> Tuple[bool, str]:
    """
    校验 Python 文件的语法与风格（可选）。

    - 必跑：py_compile（语法/缩进错误能立即发现）
    - 可选：ruff check（若系统已安装 ruff，则自动启用；否则跳过）
    """
    try:
        py_compile.compile(path, doraise=True)
    except Exception:
        return False, traceback.format_exc(limit=2)

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

def estimate_tokens_of_messages(messages: List[Dict[str, str]]) -> int:
    totalChars = 0
    for msg in messages:
        totalChars += len(msg["role"]) + len(msg["content"]) + 8
    return int(totalChars / 3)

def is_persistent_summary_message(msg: Dict[str, str]) -> bool:
    if not isinstance(msg, dict):
        return False
    if msg.get("role") != "system":
        return False
    content = str(msg.get("content") or "")
    return content.startswith("【长期摘要】")

def extract_persistent_summary_text(content: str) -> str:
    text = str(content or "")
    if not text.startswith("【长期摘要】"):
        return text.strip()
    text = text[len("【长期摘要】") :]
    if text.startswith("\n"):
        text = text[1:]
    return text.strip()

def format_messages_for_summary(messages: List[Dict[str, str]]) -> str:
    parts: List[str] = []
    for m in messages:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)

def generate_summary_via_model(text: str, api_key: str, model_name: str, endpoint: str, verify_ssl: bool) -> str:
    if not requests:
        return ""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_name,
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
            endpoint,
            headers=headers,
            json=payload,
            timeout=120,
            verify=verify_ssl,
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

def summarize_task(t: Dict[str, str]) -> str:
    """将单个任务压缩为一行摘要，便于批量批准时展示。"""
    return format_tool_display(t)
