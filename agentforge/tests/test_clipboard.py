# -*- coding: utf-8 -*-
import os
import sys
import time

# 添加项目根目录到路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
# 确保父目录在 sys.path 中，以便可以导入 xiaochen_agent_v2
PARENT_DIR = os.path.dirname(PROJECT_ROOT)
sys.path.insert(0, PARENT_DIR)

from xiaochen_agent_v2.tools.image import save_clipboard_image, get_clipboard_text

def test_clipboard():
    print("--- 剪贴板功能测试 ---")
    
    # 1. 测试文本获取
    print("\n[测试 1] 正在尝试获取剪贴板文本...")
    text = get_clipboard_text()
    if text:
        print(f"✅ 成功获取文本 (长度: {len(text)})")
        print(f"预览: {text[:50]}...")
    else:
        print("❌ 未在剪贴板中检测到文本")
        
    # 2. 测试图片获取
    print("\n[测试 2] 正在尝试获取剪贴板图片...")
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_outputs")
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
        
    img_path = save_clipboard_image(save_dir=test_dir)
    if img_path:
        print(f"✅ 成功保存图片: {img_path}")
        if os.path.exists(img_path):
            print(f"   文件确认存在，大小: {os.path.getsize(img_path)} bytes")
    else:
        print("❌ 未在剪贴板中检测到图片")

if __name__ == "__main__":
    test_clipboard()
