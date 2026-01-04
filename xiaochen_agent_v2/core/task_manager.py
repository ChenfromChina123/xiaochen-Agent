import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
