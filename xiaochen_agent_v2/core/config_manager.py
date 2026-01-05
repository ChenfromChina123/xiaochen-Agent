"""
配置文件管理模块
负责配置的读取、保存和更新
"""
import os
import json
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理器，处理配置文件的读写"""
    
    DEFAULT_CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model_name": "deepseek-chat",
        "verify_ssl": True,
        "auto_save_session": False,
        "max_cycles": 30,
        "token_threshold": 30000,
        "whitelisted_tools": [
            "search_files",
            "search_in_files",
            "read_file",
            "task_add",
            "task_update",
            "task_delete",
            "task_list",
            "task_clear",
        ],
        "whitelisted_commands": ["ls", "dir", "pwd", "whoami", "echo", "cat", "type"],
        "read_indent_mode": "header",
        "python_validate_ruff": "auto"
    }
    
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                # 合并默认配置，确保所有键都存在
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value
                return self.config
            except Exception as e:
                print(f"加载配置文件失败: {str(e)}")
                self.config = dict(self.DEFAULT_CONFIG)
                return self.config
        else:
            # 配置文件不存在，使用默认配置
            self.config = dict(self.DEFAULT_CONFIG)
            return self.config
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置字典，如果为 None 则保存当前配置
            
        Returns:
            是否保存成功
        """
        if config is not None:
            self.config = config
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            return False
    
    def update_config(self, key: str, value: Any) -> bool:
        """
        更新配置项
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否更新成功
        """
        self.config[key] = value
        return self.save_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def has_api_key(self) -> bool:
        """
        检查是否已配置 API Key
        
        Returns:
            是否已配置
        """
        api_key = self.config.get("api_key", "")
        return bool(api_key and api_key.strip())
    
    def create_example_config(self) -> bool:
        """
        创建示例配置文件
        
        Returns:
            是否创建成功
        """
        example_file = "config.json.example"
        try:
            with open(example_file, "w", encoding="utf-8") as f:
                json.dump(self.DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
