# -*- coding: utf-8 -*-
import os
import sys
from unittest.mock import MagicMock

# 设置项目根目录到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from xiaochen_agent_v2.tools.executor import Tools

def test_ocr_document_empty_params():
    mock_agent = MagicMock()
    tools = Tools(mock_agent)
    
    # 模拟导致报错的输入：page_start 或 page_end 为空字符串
    test_cases = [
        {"path": "dummy.pdf", "page_start": ""},
        {"path": "dummy.pdf", "page_end": ""},
        {"path": "dummy.pdf", "page_start": "  ", "page_end": ""},
    ]
    
    pdf_path = os.path.join(PROJECT_ROOT, "tests", "data", "四级1000高频词.pdf")
    
    for i, t in enumerate(test_cases):
        t["path"] = pdf_path
        print(f"Testing case {i+1}: {t}")
        try:
            response = tools.ocr_document(t)
            if "SUCCESS" in response:
                print(f"✓ Case {i+1} passed")
            else:
                print(f"✗ Case {i+1} failed: {response}")
        except Exception as e:
            print(f"✗ Case {i+1} raised exception: {e}")

if __name__ == "__main__":
    test_ocr_document_empty_params()
