"""
中断处理模块
提供用户打断AI自动执行的功能
"""
import threading
import sys
from typing import Optional


class InterruptHandler:
    """中断处理器，允许用户在AI执行过程中打断"""
    
    def __init__(self):
        """初始化中断处理器"""
        self.interrupted = False
        self.lock = threading.Lock()
    
    def reset(self) -> None:
        """重置中断状态"""
        with self.lock:
            self.interrupted = False
    
    def set_interrupted(self) -> None:
        """设置中断标志"""
        with self.lock:
            self.interrupted = True
    
    def is_interrupted(self) -> bool:
        """检查是否已被中断"""
        with self.lock:
            return self.interrupted
    
    def check_and_raise(self) -> None:
        """检查中断状态，如果已中断则抛出异常"""
        if self.is_interrupted():
            raise KeyboardInterrupt("用户中断执行")


class InterruptibleInput:
    """可中断的输入处理器"""
    
    def __init__(self, interrupt_handler: InterruptHandler):
        """
        初始化可中断输入处理器
        
        Args:
            interrupt_handler: 中断处理器实例
        """
        self.interrupt_handler = interrupt_handler
    
    def prompt(self, message: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        显示提示并等待用户输入，支持中断
        
        Args:
            message: 提示消息
            timeout: 超时时间（秒），None表示无限等待
            
        Returns:
            用户输入的字符串，如果被中断则返回None
        """
        try:
            result = input(message)
            return result
        except KeyboardInterrupt:
            self.interrupt_handler.set_interrupted()
            return None


def create_interrupt_handler() -> InterruptHandler:
    """
    创建并返回一个新的中断处理器实例
    
    Returns:
        InterruptHandler实例
    """
    return InterruptHandler()

