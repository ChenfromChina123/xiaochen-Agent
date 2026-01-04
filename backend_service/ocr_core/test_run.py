# -*- coding: utf-8 -*-
"""
快速测试脚本
"""
import sys
import os

# 获取脚本所在目录（ocr_core目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 切换到脚本所在目录
os.chdir(SCRIPT_DIR)

# 添加当前目录到路径
sys.path.insert(0, SCRIPT_DIR)

from ocr_engine import OCREngine

def test_initialization():
    """测试引擎初始化"""
    print("=" * 60)
    print("测试1: 引擎初始化")
    print("=" * 60)
    
    try:
        engine = OCREngine("config.json")
        print(f"✓ 配置文件加载成功")
        print(f"  - OCR引擎路径: {engine.config.get('exe_path')}")
        print(f"  - 模型路径: {engine.config.get('models_path')}")
        print(f"  - 语言配置: {engine.config.get('language')}")
        
        # 检查引擎文件是否存在
        exe_path = os.path.abspath(engine.config.get('exe_path', ''))
        if os.path.exists(exe_path):
            print(f"✓ 引擎文件存在: {exe_path}")
        else:
            print(f"✗ 引擎文件不存在: {exe_path}")
            return False
        
        # 初始化引擎
        print("\n正在初始化OCR引擎...")
        success = engine.initialize()
        
        if success:
            print("✓ OCR引擎初始化成功")
            engine.close()
            print("✓ 引擎已关闭")
            return True
        else:
            print("✗ OCR引擎初始化失败")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_manager():
    """测试with语句"""
    print("\n" + "=" * 60)
    print("测试2: with语句支持")
    print("=" * 60)
    
    try:
        with OCREngine("config.json") as engine:
            print("✓ with语句创建引擎成功")
            print("✓ 引擎已自动初始化")
        print("✓ 引擎已自动关闭")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_check():
    """检查文件完整性"""
    print("\n" + "=" * 60)
    print("测试3: 文件完整性检查")
    print("=" * 60)
    
    files_to_check = [
        "paddleocr_engine/PaddleOCR-json.exe",
        "paddleocr_engine/models/config_chinese.txt",
        "paddleocr_engine/models/config_en.txt",
        "config.json",
        "ocr_engine.py",
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} 不存在")
            all_exist = False
    
    return all_exist


def main():
    """主测试函数"""
    print("\n" + "▓" * 60)
    print("OCR核心模块测试")
    print("▓" * 60)
    print(f"工作目录: {os.getcwd()}\n")
    
    results = []
    
    # 测试1: 文件完整性
    results.append(("文件完整性", test_file_check()))
    
    # 测试2: 引擎初始化
    results.append(("引擎初始化", test_initialization()))
    
    # 测试3: with语句
    results.append(("with语句", test_context_manager()))
    
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
        print("\n🎉 所有测试通过！模块可以正常使用。")
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

