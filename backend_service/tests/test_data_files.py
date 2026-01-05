# -*- coding: utf-8 -*-
"""
数据测试脚本 - 测试 tests/data 目录下的特定文件
"""

import os
import sys
import time

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.engine import OCREngine

# 配置文件路径
CONFIG_PATH = os.path.join(BASE_DIR, "configs", "config.json")
DATA_DIR = os.path.join(BASE_DIR, "tests", "data")

def test_file(engine, file_name):
    """
    测试单个文件
    
    Args:
        engine: OCREngine 实例
        file_name: 文件名
    """
    file_path = os.path.join(DATA_DIR, file_name)
    print(f"\n{'='*60}")
    print(f"正在测试文件: {file_name}")
    print(f"文件路径: {file_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(file_path):
        print(f"✗ 错误: 文件不存在")
        return False
    
    start_time = time.time()
    
    # 根据文件扩展名选择识别方法
    ext = os.path.splitext(file_name)[1].lower()
    
    if ext in ['.pdf', '.epub', '.mobi', '.fb2', '.cbz', '.xps', '.oxps']:
        print(f"检测到文档格式: {ext}，使用 recognize_document 方法")
        result = engine.recognize_document(file_path)
    else:
        print(f"检测到图片格式: {ext}，使用 recognize_image 方法")
        result = engine.recognize_image(file_path)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"耗时: {duration:.2f} 秒")
    print(f"状态码: {result.get('code')}")
    
    if result.get('code') == 100:
        print(f"✓ 识别成功")
        
        # 提取并打印部分文本
        full_text = engine.extract_text(result)
        print("\n识别结果摘要 (前 500 个字符):")
        print("-" * 40)
        print(full_text[:500] + ("..." if len(full_text) > 500 else ""))
        print("-" * 40)
        
        # 如果是 PDF 且有分页信息
        if 'data' in result and isinstance(result['data'], list) and len(result['data']) > 0:
            if 'page' in result['data'][0]:
                pages = set(item.get('page') for item in result['data'])
                print(f"识别页数: {max(pages) if pages else 1}")
        
        return True
    elif result.get('code') == 101:
        print("⚠ 未识别到文字")
        return True
    else:
        print(f"✗ 识别失败: {result.get('data', '未知错误')}")
        return False

def main():
    """主函数"""
    print("OCR 数据目录功能测试")
    print(f"工作目录: {os.getcwd()}")
    
    # 待测试文件列表
    test_files = [
        "4月13日上午九点清扫活动.jpg",
        "四级1000高频词.pdf"
    ]
    
    # 初始化引擎
    print("\n[1] 正在初始化 OCR 引擎...")
    with OCREngine(CONFIG_PATH) as engine:
        if not engine.initialize():
            print("✗ 引擎初始化失败，请检查配置")
            return
        
        print("✓ 引擎初始化成功")
        
        # 遍历测试文件
        results = []
        for file_name in test_files:
            success = test_file(engine, file_name)
            results.append((file_name, success))
        
        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        
        passed = sum(1 for _, res in results if res)
        for file_name, success in results:
            status = "✓ 通过" if success else "✗ 失败"
            print(f"{file_name:30s} : {status}")
            
        print(f"\n总计: {passed}/{len(test_files)} 通过")

if __name__ == "__main__":
    main()
