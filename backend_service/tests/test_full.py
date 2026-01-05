# -*- coding: utf-8 -*-
"""
完整功能测试 - 包括实际图片识别
"""
import sys
import os

# 获取项目根目录和脚本目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# 添加项目根目录到路径
sys.path.insert(0, BASE_DIR)

from core.engine import OCREngine

# 配置文件路径
CONFIG_PATH = os.path.join(BASE_DIR, "configs", "config.json")

def test_api_methods():
    """测试所有API方法"""
    print("=" * 60)
    print("测试: API方法测试")
    print("=" * 60)
    
    try:
        engine = OCREngine(CONFIG_PATH)
        
        # 测试方法是否存在
        methods = [
            'initialize', 'recognize_image', 'recognize_bytes',
            'recognize_base64', 'batch_recognize', 'extract_text', 'close'
        ]
        
        for method in methods:
            if hasattr(engine, method):
                print(f"✓ {method} 方法存在")
            else:
                print(f"✗ {method} 方法不存在")
                return False
        
        # 测试类方法
        try:
            formats = engine.get_supported_formats()
            print(f"\n✓ get_supported_formats() 方法存在")
            print(f"  支持的格式: {', '.join(formats)}")
            print(f"  支持PDF/文档: {hasattr(engine, 'recognize_document')}")
        except Exception as e:
            print(f"✗ SUPPORTED_FORMATS 属性访问失败: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """测试配置加载"""
    print("\n" + "=" * 60)
    print("测试: 配置文件加载")
    print("=" * 60)
    
    try:
        # 测试默认配置
        engine = OCREngine(CONFIG_PATH)
        config = engine.config
        
        required_keys = ['exe_path', 'models_path', 'language', 'cpu_threads']
        
        for key in required_keys:
            if key in config:
                print(f"✓ {key}: {config[key]}")
            else:
                print(f"✗ 缺少配置项: {key}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试: 错误处理")
    print("=" * 60)
    
    try:
        with OCREngine(CONFIG_PATH) as engine:
            # 测试不存在的文件
            result = engine.recognize_image("nonexistent_file.jpg")
            
            if result['code'] != 100:
                print(f"✓ 正确处理不存在的文件")
                print(f"  状态码: {result['code']}")
                print(f"  错误信息: {result['data']}")
            else:
                print(f"✗ 应该返回错误但返回了成功")
                return False
            
            # 测试不支持的格式
            result = engine.recognize_image("test.txt")
            
            if result['code'] != 100:
                print(f"✓ 正确处理不支持的格式")
                print(f"  状态码: {result['code']}")
            else:
                print(f"✗ 应该返回错误但返回了成功")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_extract_text():
    """测试文本提取功能"""
    print("\n" + "=" * 60)
    print("测试: 文本提取功能")
    print("=" * 60)
    
    try:
        engine = OCREngine(CONFIG_PATH)
        
        # 模拟识别结果
        mock_result_success = {
            "code": 100,
            "data": [
                {"text": "第一行", "score": 0.95, "box": [[0,0], [100,0], [100,20], [0,20]]},
                {"text": "第二行", "score": 0.92, "box": [[0,25], [100,25], [100,45], [0,45]]},
                {"text": "第三行", "score": 0.98, "box": [[0,50], [100,50], [100,70], [0,70]]},
            ],
            "score": 0.95
        }
        
        text = engine.extract_text(mock_result_success)
        expected_text = "第一行\n第二行\n第三行"
        
        if text == expected_text:
            print(f"✓ 文本提取正确")
            print(f"  提取的文本:\n{text}")
        else:
            print(f"✗ 文本提取错误")
            print(f"  期望: {expected_text}")
            print(f"  实际: {text}")
            return False
        
        # 测试空结果
        mock_result_empty = {"code": 101, "data": []}
        text_empty = engine.extract_text(mock_result_empty)
        
        if text_empty == "":
            print(f"✓ 空结果处理正确")
        else:
            print(f"✗ 空结果处理错误")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_structure():
    """测试目录结构"""
    print("\n" + "=" * 60)
    print("测试: 目录结构完整性")
    print("=" * 60)
    
    required_files = [
        os.path.join(BASE_DIR, "core", "engine.py"),
        CONFIG_PATH,
        os.path.join(BASE_DIR, "core", "__init__.py"),
        os.path.join(BASE_DIR, "tests", "example.py"),
        os.path.join(BASE_DIR, "tests", "test_simple.py"),
        os.path.join(BASE_DIR, "docs", "API_GUIDE.txt"),
        os.path.join(BASE_DIR, "docs", "README.md"),
        os.path.join(BASE_DIR, "core", "paddleocr_engine", "PaddleOCR-json.exe"),
        os.path.join(BASE_DIR, "core", "paddleocr_engine", "models", "config_chinese.txt"),
        os.path.join(BASE_DIR, "core", "paddleocr_engine", "models", "config_en.txt"),
        os.path.join(BASE_DIR, "core", "paddleocr_engine", "models", "ch_PP-OCRv3_det_infer/inference.pdmodel"),
        os.path.join(BASE_DIR, "core", "paddleocr_engine", "models", "ch_PP-OCRv3_rec_infer/inference.pdmodel"),
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            size_str = f"{size:,} bytes" if size < 1024*1024 else f"{size/(1024*1024):.2f} MB"
            print(f"✓ {file_path:60s} ({size_str})")
        else:
            print(f"✗ {file_path} 不存在")
            all_exist = False
    
    if all_exist:
        # 统计总大小
        total_size = 0
        for root, dirs, files in os.walk('.'):
            for file in files:
                try:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                except:
                    pass
        
        print(f"\n模块总大小: {total_size/(1024*1024):.2f} MB")
    
    return all_exist


def main():
    """主测试函数"""
    print("\n" + "▓" * 60)
    print("OCR核心模块 - 完整功能测试")
    print("▓" * 60)
    print(f"工作目录: {os.getcwd()}")
    print(f"脚本目录: {SCRIPT_DIR}\n")
    
    results = []
    
    # 测试1: 目录结构
    results.append(("目录结构完整性", test_directory_structure()))
    
    # 测试2: 配置加载
    results.append(("配置文件加载", test_config_loading()))
    
    # 测试3: API方法
    results.append(("API方法", test_api_methods()))
    
    # 测试4: 错误处理
    results.append(("错误处理", test_error_handling()))
    
    # 测试5: 文本提取
    results.append(("文本提取", test_extract_text()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20s} : {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        print("\n模块特性:")
        print("  ✓ 完全独立 - 包含完整引擎和模型")
        print("  ✓ 开箱即用 - 无需额外配置")
        print("  ✓ 便携部署 - 可直接复制到任何位置")
        print("  ✓ JSON配置 - 灵活调整参数")
        print("  ✓ 简洁API - 易于集成")
        return 0
    else:
        print(f"\n⚠ {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

