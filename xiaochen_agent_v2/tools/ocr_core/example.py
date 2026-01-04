# -*- coding: utf-8 -*-
"""
OCR引擎使用示例
演示如何使用 OCREngine 进行图片文字识别
"""

import os
import sys
from ocr_engine import OCREngine


def example_basic():
    """基础使用示例"""
    print("=" * 50)
    print("示例1: 基础使用")
    print("=" * 50)
    
    # 创建OCR引擎实例
    engine = OCREngine("config.json")
    
    # 初始化引擎
    if not engine.initialize():
        print("OCR引擎初始化失败")
        return
    
    # 识别图片（请替换为实际的图片路径）
    image_path = "test_image.jpg"
    
    if os.path.exists(image_path):
        result = engine.recognize_image(image_path)
        
        # 显示识别结果
        print(f"\n识别状态码: {result['code']}")
        print(f"平均置信度: {result['score']:.2f}")
        
        if result['code'] == 100:
            print("\n识别结果:")
            for i, item in enumerate(result['data'], 1):
                print(f"  {i}. [{item['score']:.2f}] {item['text']}")
                print(f"     位置: {item['box']}")
            
            # 提取纯文本
            text = engine.extract_text(result)
            print(f"\n纯文本:\n{text}")
        else:
            print(f"识别失败: {result['data']}")
    else:
        print(f"测试图片不存在: {image_path}")
    
    # 关闭引擎
    engine.close()


def example_with_statement():
    """使用 with 语句自动管理资源"""
    print("\n" + "=" * 50)
    print("示例2: 使用 with 语句")
    print("=" * 50)
    
    image_path = "test_image.jpg"
    
    if os.path.exists(image_path):
        # 使用 with 语句，自动初始化和关闭
        with OCREngine("config.json") as engine:
            result = engine.recognize_image(image_path)
            
            if result['code'] == 100:
                text = engine.extract_text(result)
                print(f"识别文本:\n{text}")
            else:
                print(f"识别失败: {result['data']}")
    else:
        print(f"测试图片不存在: {image_path}")


def example_batch():
    """批量识别示例"""
    print("\n" + "=" * 50)
    print("示例3: 批量识别")
    print("=" * 50)
    
    # 图片列表（请替换为实际的图片路径）
    image_paths = [
        "test1.jpg",
        "test2.png",
        "test3.jpg"
    ]
    
    # 过滤存在的图片
    existing_paths = [p for p in image_paths if os.path.exists(p)]
    
    if not existing_paths:
        print("没有找到测试图片")
        return
    
    with OCREngine("config.json") as engine:
        results = engine.batch_recognize(existing_paths)
        
        for result in results:
            print(f"\n图片: {result['path']}")
            print(f"状态: {result['code']}, 置信度: {result['score']:.2f}")
            
            if result['code'] == 100:
                text = engine.extract_text(result)
                print(f"文本: {text[:100]}...")  # 只显示前100字符


def example_bytes():
    """使用字节流识别"""
    print("\n" + "=" * 50)
    print("示例4: 字节流识别")
    print("=" * 50)
    
    image_path = "test_image.jpg"
    
    if os.path.exists(image_path):
        # 读取图片字节流
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # 使用字节流识别
        with OCREngine("config.json") as engine:
            result = engine.recognize_bytes(image_bytes)
            
            if result['code'] == 100:
                text = engine.extract_text(result)
                print(f"识别文本:\n{text}")
            else:
                print(f"识别失败: {result['data']}")
    else:
        print(f"测试图片不存在: {image_path}")


def example_custom_config():
    """使用自定义配置"""
    print("\n" + "=" * 50)
    print("示例5: 自定义配置")
    print("=" * 50)
    
    # 模块已内置OCR引擎，配置文件使用相对路径，无需修改
    # 也可以直接修改配置文件，或者创建新的配置文件
    # 配置说明:
    # - exe_path: OCR引擎可执行文件路径（相对路径）
    # - models_path: 模型文件夹路径（相对路径）
    # - language: 语言配置文件 (config_chinese.txt, config_en.txt等)
    # - cpu_threads: CPU线程数 (建议4-8)
    # - enable_mkldnn: 是否启用MKL-DNN加速 (true/false)
    # - cls: 是否启用方向分类 (true/false)
    # - limit_side_len: 图片长边压缩限制 (默认4320)
    
    print("本模块已内置OCR引擎，开箱即用")
    print("如需自定义，可编辑 config.json 文件")
    print("\n默认配置文件示例:")
    print("""
    {
        "exe_path": "paddleocr_engine/PaddleOCR-json.exe",
        "models_path": "paddleocr_engine/models",
        "language": "models/config_chinese.txt",
        "cpu_threads": 4,
        "enable_mkldnn": true,
        "cls": false,
        "limit_side_len": 4320
    }
    """)


if __name__ == "__main__":
    print("OCR引擎使用示例\n")
    
    # 运行各个示例
    try:
        example_basic()
        example_with_statement()
        example_batch()
        example_bytes()
        example_custom_config()
        
        print("\n" + "=" * 50)
        print("所有示例运行完成")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()

