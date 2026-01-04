import sys
from unittest.mock import MagicMock

# Mock requests before importing agent because it might not be installed in the test environment
mock_requests = MagicMock()
# Ensure it acts like a module
mock_requests.__name__ = "requests"
mock_requests.__file__ = "mock_requests.py"

sys.modules["requests"] = mock_requests
sys.modules["requests.exceptions"] = MagicMock()
sys.modules["requests.exceptions.RequestException"] = Exception

# Test import immediately
try:
    import requests
    print(f"DEBUG: requests imported: {requests}")
except Exception as e:
    print(f"DEBUG: failed to import requests: {e}")

import unittest
from unittest.mock import patch
# Import Agent after mocking
from xiaochen_agent_v2.core import agent as agent_module
from xiaochen_agent_v2.core.agent import VoidAgent
from xiaochen_agent_v2.core.config import Config

print(f"DEBUG: agent_module.requests is {agent_module.requests}")

class TestAgentInterrupt(unittest.TestCase):
    def setUp(self):
        # Force set requests in agent module if it failed
        if agent_module.requests is None:
             print("DEBUG: Forcing requests injection into agent module")
             agent_module.requests = mock_requests
             
        self.config = Config(apiKey="test", baseUrl="test", modelName="test")
        self.agent = VoidAgent(self.config)

    def test_chat_interrupt_preserves_history(self):
        # 模拟流式响应，生成几行后抛出 KeyboardInterrupt
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        def iter_lines():
            # 模拟正常的流式输出
            yield b'data: {"choices": [{"delta": {"content": "Hello"}}]}'
            yield b'data: {"choices": [{"delta": {"content": " World"}}]}'
            # 模拟中断
            raise KeyboardInterrupt()
            
        mock_response.iter_lines = iter_lines
        
        # 配置 mock_requests.post 返回我们的 mock_response
        mock_requests.post.return_value = mock_response

        # 执行 chat
        print("DEBUG: Calling chat...")
        self.agent.chat("Hi")

        # 验证中断标志是否被设置
        self.assertTrue(self.agent.interruptHandler.is_interrupted())
        
        # 检查历史记录中是否包含被中断的消息
        # 我们期望 "Hello" 和 " World" 被捕获，且最后追加了 "[Interrupted]"
        last_msg = self.agent.historyOfMessages[-1]
        self.assertEqual(last_msg["role"], "assistant")
        print(f"Captured content: {last_msg['content']}")
        self.assertIn("Hello World", last_msg["content"])
        self.assertIn("[Interrupted]", last_msg["content"])

if __name__ == "__main__":
    unittest.main()
