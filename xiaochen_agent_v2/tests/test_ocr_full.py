# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import MagicMock

# 设置项目根目录到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from xiaochen_agent_v2.tools.ocr import ocr_image, ocr_document
from xiaochen_agent_v2.tools.executor import Tools

class TestAgentOCRIntegration(unittest.TestCase):
    """
    测试 Agent OCR 功能的完整集成，包括：
    1. ocr.py 的底层调用
    2. executor.py 的工具封装
    """
    
    def test_ocr_image_basic(self):
        """测试 ocr_image 基础调用（预期文件不存在错误）"""
        print("\n[Test] Testing ocr_image basic call...")
        result = ocr_image("non_existent_file.jpg")
        self.assertEqual(result.get("code"), 404)
        self.assertIn("图片文件不存在", result.get("data"))
        print("✓ ocr_image basic call returns 404 as expected.")

    def test_ocr_document_basic(self):
        """测试 ocr_document 基础调用（预期文件不存在错误）"""
        print("\n[Test] Testing ocr_document basic call...")
        result = ocr_document("non_existent_file.pdf")
        self.assertEqual(result.get("code"), 404)
        self.assertIn("文档文件不存在", result.get("data"))
        print("✓ ocr_document basic call returns 404 as expected.")

    def test_tools_executor_ocr_image(self):
        """测试 Tools 类对 ocr_image 的封装"""
        print("\n[Test] Testing Tools.ocr_image executor wrapper...")
        # 模拟 agent 对象
        mock_agent = MagicMock()
        tools = Tools(mock_agent)
        
        # 模拟输入参数
        t = {"path": "non_existent_file.jpg"}
        
        # 调用 executor 中的方法
        # 注意：Tools.ocr_image 会在内部调用 ocr_image 并打印 header
        # 我们这里主要检查它是否能正常捕获 ocr_image 的返回结果并格式化为 SUCCESS/FAILURE 字符串
        response = tools.ocr_image(t)
        
        self.assertTrue(response.startswith("FAILURE: OCR failed"))
        self.assertIn("404", response)
        print(f"✓ Tools.ocr_image wrapper handled failure correctly: {response[:50]}...")

    def test_tools_executor_ocr_document(self):
        """测试 Tools 类对 ocr_document 的封装"""
        print("\n[Test] Testing Tools.ocr_document executor wrapper...")
        mock_agent = MagicMock()
        tools = Tools(mock_agent)
        
        t = {"path": "non_existent_file.pdf", "page_start": 1}
        response = tools.ocr_document(t)
        
        self.assertTrue(response.startswith("FAILURE: Document OCR failed"))
        self.assertIn("404", response)
        print(f"✓ Tools.ocr_document wrapper handled failure correctly: {response[:50]}...")

if __name__ == "__main__":
    print("Starting Agent-OCR Integration Tests...")
    unittest.main()
