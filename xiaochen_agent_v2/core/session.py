"""
会话历史管理模块
提供会话的保存、加载、列表和选择功能
"""
import os
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..utils.files import cleanup_directory


class SessionManager:
    """会话管理器，负责会话历史的持久化存储"""
    
    def __init__(self, sessions_dir: str = "logs/sessions"):
        """
        初始化会话管理器
        
        Args:
            sessions_dir: 会话存储目录路径
        """
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)

    def create_autosave_session(self, session_name: Optional[str] = None) -> str:
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
        if not filename:
            return False

        filepath = os.path.join(self.sessions_dir, filename)
        
        # 定期清理历史会话，保留最近 50 个
        cleanup_directory(self.sessions_dir, max_files=50, pattern="*.json")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_at = datetime.now().isoformat()
        autosave = False
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    timestamp = data.get("timestamp", timestamp)
                    created_at = data.get("created_at", created_at)
                    autosave = bool(data.get("autosave", False))
            except Exception:
                pass

        # 转换为分行格式
        formatted_messages = self._format_messages(messages)

        session_data = {
            "timestamp": timestamp,
            "created_at": created_at,
            "updated_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": formatted_messages,
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
            "messages": formatted_messages
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
                    "file_size": os.path.getsize(filepath)
                })
            except Exception:
                continue
        
        # 按创建时间倒序排列
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        
        return sessions[:limit]
    
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

