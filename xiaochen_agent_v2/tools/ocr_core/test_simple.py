# -*- coding: utf-8 -*-
"""
简单测试脚本 - 测试OCR引擎基本功能
运行此脚本前，请确保已正确配置 config.json
"""

import os
import sys
from ocr_engine import OCREngine


def test_initialization():
    """测试引擎初始化"""
    print("【测试1】引擎初始化测试")
    print("-" * 40)
    
    engine = OCREngine("config.json")
    
    # 检查配置加载
    print(f"配置文件路径: config.json")
    print(f"OCR引擎路径: {engine.config.get('exe_path')}")
    print(f"模型路径: {engine.config.get('models_path')}")
    print(f"语言配置: {engine.config.get('language')}")
    print(f"CPU线程数: {engine.config.get('cpu_threads')}")
    
    # 初始化
    success = engine.initialize()
    
    if success:
        print("✓ 引擎初始化成功")
        engine.close()
        return True
    else:
        print("✗ 引擎初始化失败")
        return False


def test_recognition(image_path):
    """测试图片识别"""
    print(f"\n【测试2】图片识别测试")
    print("-" * 40)
    
    if not os.path.exists(image_path):
        print(f"✗ 测试图片不存在: {image_path}")
        print(f"  请将测试图片放到当前目录，或修改图片路径")
        return False
    
    print(f"测试图片: {image_path}")
    
    with OCREngine("config.json") as engine:
        result = engine.recognize_image(image_path)
        
        print(f"状态码: {result['code']}")
        
        if result['code'] == 100:
            print(f"✓ 识别成功")
            print(f"置信度: {result['score']:.4f}")
            print(f"识别文本行数: {len(result['data'])}")
            
            print("\n识别内容:")
            print("=" * 40)
            for i, item in enumerate(result['data'], 1):
                print(f"{i}. [{item['score']:.2f}] {item['text']}")
            
            print("\n纯文本:")
            print("=" * 40)
            text = engine.extract_text(result)
            print(text)
            
            return True
            
        elif result['code'] == 101:
            print("⚠ 图片中未识别到文字")
            return True
        else:
            print(f"✗ 识别失败: {result['data']}")
            return False


def test_format_support():
    """测试格式支持"""
    print(f"\n【测试3】支持的图片格式")
    print("-" * 40)
    
    engine = OCREngine("config.json")
    formats = engine.SUPPORTED_FORMATS
    print(f"支持的格式数量: {len(formats)}")
    print(f"支持的格式: {', '.join(formats)}")
    
    return True


def main():
    """主测试函数"""
    print("=" * 50)
    print("OCR核心引擎测试")
    print("=" * 50)
    print()
    
    # 测试1: 初始化
    if not test_initialization():
        print("\n初始化测试失败，请检查配置文件")
        return
    
    # 测试2: 识别（需要提供测试图片）
    # 你可以修改下面的图片路径为实际存在的图片
    test_images = [
        "test.jpg",
        "test.png",
        "../test/1000.txt",  # 如果是文本文件会被正确拒绝
    ]
    
    # 找到第一个存在的图片文件
    found_image = None
    for img in test_images:
        if os.path.exists(img):
            ext = os.path.splitext(img)[-1].lower()
            if ext in OCREngine.SUPPORTED_FORMATS:
                found_image = img
                break
    
    if found_image:
        test_recognition(found_image)
    else:
        print("\n【测试2】跳过（未找到测试图片）")
        print("提示: 请将测试图片命名为 test.jpg 或 test.png 放到当前目录")
    
    # 测试3: 格式支持
    test_format_support()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
    except Exception as e:
        print(f"\n\n测试出现异常: {e}")
        import traceback
        traceback.print_exc()

