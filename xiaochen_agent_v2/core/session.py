"""
会话历史管理模块
提供会话的保存、加载、列表和选择功能
"""
import os
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..utils.files import cleanup_directory, get_sessions_dir


class SessionManager:
    """会话管理器，负责会话历史的持久化存储"""
    
    def __init__(self, sessions_dir: Optional[str] = None):
        """
        初始化会话管理器
        
        Args:
            sessions_dir: 会话存储目录路径
        """
        self.sessions_dir = sessions_dir or get_sessions_dir()
        os.makedirs(self.sessions_dir, exist_ok=True)

    def create_autosave_session(self, session_name: Optional[str] = None) -> str:
        """
        创建一个 autosave 会话文件。

        Args:
            session_name: 可选会话名称（仅用于文件名）

        Returns:
            新建的会话文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if session_name:
            session_name = "".join(c for c in session_name if c.isalnum() or c in (" ", "-", "_")).strip()
            filename = f"{timestamp}_{session_name}.json"
        else:
            filename = f"{timestamp}_autosave.json"

        filepath = os.path.join(self.sessions_dir, filename)
        session_data = {
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0,
            "messages": [],
            "autosave": True,
            "title": "",
            "first_user_input": "",
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return filename

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """将消息内容转换为分行列表格式，便于阅读和匹配 void_chat 格式"""
        formatted = []
        for msg in messages:
            msg_copy = msg.copy()
            if "content" in msg_copy and isinstance(msg_copy["content"], str):
                msg_copy["content"] = msg_copy["content"].splitlines()
            formatted.append(msg_copy)
        return formatted

    def _parse_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """将分行列表格式的消息内容转换回字符串格式"""
        parsed = []
        for msg in messages:
            msg_copy = msg.copy()
            if "content" in msg_copy and isinstance(msg_copy["content"], list):
                msg_copy["content"] = "\n".join(msg_copy["content"])
            parsed.append(msg_copy)
        return parsed

    def update_session(self, filename: str, messages: List[Dict[str, str]]) -> bool:
        """
        更新指定会话文件内容。

        Args:
            filename: 会话文件名
            messages: 完整消息列表（建议包含 system）

        Returns:
            是否写入成功
        """
        if not filename:
            return False

        filepath = os.path.join(self.sessions_dir, filename)
        
        # 定期清理历史会话，保留最近 50 个
        cleanup_directory(self.sessions_dir, max_files=50, pattern="*.json")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_at = datetime.now().isoformat()
        autosave = False
        title = ""
        first_user_input = ""
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    timestamp = data.get("timestamp", timestamp)
                    created_at = data.get("created_at", created_at)
                    autosave = bool(data.get("autosave", False))
                    title = str(data.get("title") or "").strip()
                    first_user_input = str(data.get("first_user_input") or "").strip()
            except Exception:
                pass

        # 转换为分行格式
        formatted_messages = self._format_messages(messages)

        if not first_user_input:
            first_user_input = self._guess_first_user_input_from_messages(formatted_messages)
        if not title:
            title = self._default_title_from_first_user_input(first_user_input)

        session_data = {
            "timestamp": timestamp,
            "created_at": created_at,
            "updated_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": formatted_messages,
            "title": title,
            "first_user_input": first_user_input,
        }
        if autosave:
            session_data["autosave"] = True

        try:
            os.makedirs(self.sessions_dir, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def update_session_meta(
        self,
        filename: str,
        *,
        title: Optional[str] = None,
        first_user_input: Optional[str] = None,
    ) -> bool:
        """
        仅更新会话元数据（title/first_user_input），不改写消息内容。

        Args:
            filename: 会话文件名
            title: 可选标题
            first_user_input: 可选首条用户输入

        Returns:
            是否更新成功
        """
        if not filename:
            return False
        filepath = os.path.join(self.sessions_dir, filename)
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return False
            if title is not None and str(title).strip():
                data["title"] = str(title).strip()
            if first_user_input is not None and str(first_user_input).strip():
                data["first_user_input"] = str(first_user_input).strip()
            data["updated_at"] = datetime.now().isoformat()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def _guess_first_user_input_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        从 messages 中推断第一条用户输入。
        """
        for msg in messages:
            try:
                if msg.get("role") != "user":
                    continue
                content = msg.get("content")
                if isinstance(content, list):
                    text = "\n".join([str(x) for x in content]).strip()
                else:
                    text = str(content or "").strip()
                if not text:
                    continue
                if "## 📥 USER INPUT" in text:
                    parts = text.split("## 📥 USER INPUT", 1)
                    if len(parts) == 2:
                        tail = parts[1].strip()
                        tail = tail.lstrip("\n").strip()
                        if tail:
                            return tail.splitlines()[0].strip()
                return text.splitlines()[0].strip()
            except Exception:
                continue
        return ""

    def _default_title_from_first_user_input(self, first_user_input: str) -> str:
        """
        使用首条用户输入生成默认标题（用于历史无标题的兼容）。
        """
        text = (first_user_input or "").strip()
        if not text:
            return ""
        line = text.splitlines()[0].strip()
        return (line[:24] + "…") if len(line) > 24 else line
    
    def save_session(self, messages: List[Dict[str, str]], session_name: Optional[str] = None) -> str:
        """
        保存当前会话到文件
        
        Args:
            messages: 消息历史列表
            session_name: 可选的会话名称，如果不提供则使用时间戳
            
        Returns:
            保存的会话文件名
        """
        if not messages:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if session_name:
            # 清理文件名中的非法字符
            session_name = "".join(c for c in session_name if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = f"{timestamp}_{session_name}.json"
        else:
            filename = f"{timestamp}.json"
        
        filepath = os.path.join(self.sessions_dir, filename)
        
        # 转换为分行格式
        formatted_messages = self._format_messages(messages)

        session_data = {
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": formatted_messages,
            "title": (session_name or "").strip(),
            "first_user_input": self._guess_first_user_input_from_messages(formatted_messages),
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        列出所有保存的会话
        
        Args:
            limit: 返回的最大会话数量
            
        Returns:
            会话信息列表，按时间倒序排列
        """
        sessions = []
        
        if not os.path.exists(self.sessions_dir):
            return sessions
        
        for filename in os.listdir(self.sessions_dir):
            if not filename.endswith(".json"):
                continue
            
            filepath = os.path.join(self.sessions_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                sessions.append({
                    "filename": filename,
                    "filepath": filepath,
                    "timestamp": data.get("timestamp", ""),
                    "created_at": data.get("created_at", ""),
                    "message_count": data.get("message_count", 0),
                    "file_size": os.path.getsize(filepath),
                    "title": self._safe_session_title(data),
                })
            except Exception:
                continue
        
        # 按创建时间倒序排列
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        
        return sessions[:limit]

    def _safe_session_title(self, data: Dict[str, Any]) -> str:
        """
        返回会话标题：优先取 title，否则取 first_user_input，否则尝试从 messages 推断。
        """
        try:
            title = str(data.get("title") or "").strip()
            if title:
                return title
            first_user_input = str(data.get("first_user_input") or "").strip()
            if not first_user_input:
                msgs = data.get("messages", [])
                if isinstance(msgs, list):
                    first_user_input = self._guess_first_user_input_from_messages(msgs)
            return self._default_title_from_first_user_input(first_user_input) or "未命名会话"
        except Exception:
            return "未命名会话"
    
    def load_session(self, filename: str) -> Optional[List[Dict[str, str]]]:
        """
        加载指定的会话
        
        Args:
            filename: 会话文件名
            
        Returns:
            消息历史列表，如果加载失败则返回None
        """
        filepath = os.path.join(self.sessions_dir, filename)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            messages = data.get("messages", [])
            return self._parse_messages(messages)
        except Exception:
            return None
    
    def delete_session(self, filename: str) -> bool:
        """
        删除指定的会话
        
        Args:
            filename: 会话文件名
            
        Returns:
            是否删除成功
        """
        filepath = os.path.join(self.sessions_dir, filename)
        
        if not os.path.exists(filepath):
            return False
        
        try:
            os.remove(filepath)
            return True
        except Exception:
            return False
