# -*- coding: utf-8 -*-
import os
import sys

# 设置项目根目录到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from xiaochen_agent_v2.tools.ocr import ocr_image, ocr_document

def test_real_data():
    data_dir = os.path.join(PROJECT_ROOT, "xiaochen_agent_v2", "tests", "data")
    
    image_file = os.path.join(data_dir, "4月13日上午九点清扫活动.jpg")
    pdf_file = os.path.join(data_dir, "四级1000高频词.pdf")
    
    print("=" * 50)
    print("开始使用真实数据测试 OCR 功能")
    print("=" * 50)
    
    # 1. 测试图片 OCR
    print(f"\n[测试1] 图片 OCR: {os.path.basename(image_file)}")
    if os.path.exists(image_file):
        result = ocr_image(image_file)
        if result.get("code") == 100:
            print("✅ 图片识别成功！")
            print("识别内容摘要:")
            text = result.get("text", "")
            # 打印前 200 个字符
            print("-" * 30)
            print(text[:200] + "..." if len(text) > 200 else text)
            print("-" * 30)
        else:
            print(f"❌ 图片识别失败: {result}")
    else:
        print(f"⚠️ 图片文件不存在: {image_file}")
        
    # 2. 测试 PDF OCR (全部页面)
    print(f"\n[测试2] 文档 OCR (全文档): {os.path.basename(pdf_file)}")
    if os.path.exists(pdf_file):
        result = ocr_document(pdf_file) # 不传 page_end 默认全文档
        if result.get("code") == 100:
            print(f"✅ 文档识别成功！总页数: {result.get('page_count')}")
            print("识别内容摘要 (最后 300 字符):")
            text = result.get("text", "")
            print("-" * 30)
            print("..." + text[-300:] if len(text) > 300 else text)
            print("-" * 30)
            print(f"完整结果已保存至: {result.get('saved_path')}")
        else:
            print(f"❌ 文档识别失败: {result}")
    else:
        print(f"⚠️ 文档文件不存在: {pdf_file}")

if __name__ == "__main__":
    test_real_data()
