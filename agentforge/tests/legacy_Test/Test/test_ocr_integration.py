# -*- coding: utf-8 -*-
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from xiaochen_agent_v2.utils.ocr import ocr_image

def test_ocr_integration():
    print("测试 OCR 集成...")
    # 即使图片不存在，也应该返回 404 错误而不是崩溃
    result = ocr_image("non_existent_image.jpg")
    print(f"识别结果 (预期 404): {result}")
    
    if result.get("code") == 404:
        print("✅ 路径检查正常")
    else:
        print("❌ 路径检查异常")

if __name__ == "__main__":
    test_ocr_integration()
