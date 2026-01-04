# -*- coding: utf-8 -*-
import os
import sys
import unittest
import requests
import json
from typing import Dict, Any

# 设置项目根目录到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from xiaochen_agent_v2.tools.ocr import ocr_image, ocr_document
from xiaochen_agent_v2.tools.executor import Tools

class TestOCRBackendFull(unittest.TestCase):
    """
    全面测试 OCR 后端服务集成
    """
    
    @classmethod
    def setUpClass(cls):
        # 测试文件路径
        cls.img_path = os.path.join(PROJECT_ROOT, "tests", "data", "4月13日上午九点清扫活动.jpg")
        cls.pdf_path = os.path.join(PROJECT_ROOT, "tests", "data", "四级1000高频词.pdf")
        cls.non_existent_path = os.path.join(PROJECT_ROOT, "tests", "data", "non_existent.jpg")
        
        # 验证服务是否在线
        try:
            res = requests.get("http://localhost:5000/api/health", timeout=5)
            if res.status_code != 200:
                raise Exception("OCR 服务响应异常")
        except Exception as e:
            raise Exception(f"OCR 服务未启动或无法访问: {str(e)}")

    def test_01_health_check(self):
        """测试服务健康检查"""
        print("\n[Test] 检查服务健康状态...")
        res = requests.get("http://localhost:5000/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        print("✓ 服务健康检查通过")

    def test_02_image_ocr(self):
        """测试图片 OCR 识别"""
        print(f"\n[Test] 测试图片识别: {os.path.basename(self.img_path)}")
        res = ocr_image(self.img_path)
        self.assertTrue(res.get("success"), f"识别失败: {res.get('message')}")
        self.assertIn("data", res)
        self.assertIn("text", res["data"])
        self.assertIn("saved_path", res["data"])
        
        text = res["data"]["text"]
        print(f"✓ 识别成功，字数: {len(text)}")
        self.assertTrue(len(text) > 0)
        self.assertTrue(os.path.exists(res["data"]["saved_path"]))
        print(f"✓ 结果已保存至: {res['data']['saved_path']}")

    def test_03_document_ocr_single_page(self):
        """测试文档单页识别"""
        print(f"\n[Test] 测试文档单页识别: {os.path.basename(self.pdf_path)}")
        res = ocr_document(self.pdf_path, page_start=1, page_end=1)
        self.assertTrue(res.get("success"), f"识别失败: {res.get('message')}")
        self.assertIn("text", res["data"])
        
        text = res["data"]["text"]
        print(f"✓ 第1页识别成功，字数: {len(text)}")
        self.assertTrue("四级" in text or "1000" in text)

    def test_04_document_ocr_multi_page(self):
        """测试文档多页识别"""
        print(f"\n[Test] 测试文档多页识别 (1-2页): {os.path.basename(self.pdf_path)}")
        res = ocr_document(self.pdf_path, page_start=1, page_end=2)
        self.assertTrue(res.get("success"), f"识别失败: {res.get('message')}")
        
        text = res["data"]["text"]
        print(f"✓ 1-2页识别成功，总字数: {len(text)}")
        self.assertTrue(len(text) > 100) # 简易判断多页内容

    def test_05_error_handling_file_not_found(self):
        """测试文件不存在的错误处理"""
        print("\n[Test] 测试文件不存在错误处理...")
        res = ocr_image(self.non_existent_path)
        self.assertFalse(res.get("success"))
        self.assertIn("不存在", res.get("message"))
        print("✓ 错误处理正常")

    def test_06_executor_integration(self):
        """测试 Tools 执行器集成"""
        print("\n[Test] 测试 Tools 执行器集成...")
        from unittest.mock import MagicMock
        mock_agent = MagicMock()
        tools = Tools(mock_agent)
        
        # 测试图片
        print("  - 执行器: ocr_image")
        response = tools.ocr_image({"path": self.img_path})
        self.assertTrue(response.startswith("SUCCESS"))
        self.assertIn("结果已保存至", response)
        
        # 测试文档
        print("  - 执行器: ocr_document")
        response = tools.ocr_document({"path": self.pdf_path, "page_start": 1, "page_end": 1})
        self.assertTrue(response.startswith("SUCCESS"))
        print("✓ 执行器集成测试通过")

if __name__ == "__main__":
    unittest.main()
