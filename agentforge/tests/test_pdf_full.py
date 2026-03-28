# -*- coding: utf-8 -*-
import os
import sys

# 设置项目根目录到 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from xiaochen_agent_v2.tools.ocr import ocr_document

def check_full_pdf():
    pdf_file = os.path.join(PROJECT_ROOT, "xiaochen_agent_v2", "tests", "data", "四级1000高频词.pdf")
    
    print(f"正在分析 PDF: {pdf_file}")
    if not os.path.exists(pdf_file):
        print("文件不存在！")
        return

    # 不指定 page_end，理论上应该识别全部
    print("开始识别全文档...")
    result = ocr_document(pdf_file)
    
    if result.get("code") == 100:
        text = result.get("text", "")
        page_count = result.get("page_count", "未知")
        print(f"✅ 识别成功！总页数: {page_count}")
        print(f"总字符数: {len(text)}")
        print(f"保存路径: {result.get('saved_path')}")
        
        # 检查单词数量（粗略估计）
        words = text.split()
        print(f"估计单词/数据项数量: {len(words)}")
        
        # 打印最后一部分内容看看是否到末尾
        print("\n内容末尾摘要:")
        print("-" * 30)
        print(text[-500:] if len(text) > 500 else text)
        print("-" * 30)
    else:
        print(f"❌ 识别失败: {result}")

if __name__ == "__main__":
    check_full_pdf()
