#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单功能测试文件
用于测试小晨终端助手的基本功能
"""

import os
import sys


def test_basic_operations():
    """测试基本操作功能"""
    print("测试基本操作...")

    # 创建测试文件
    test_file = "test_temp.txt"
    try:
        # 写入文件
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("测试文件内容\n")
            f.write("测试小晨终端助手\n")

        # 读取文件
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"文件内容: {content}")

        # 删除文件
        os.remove(test_file)
        print("基本操作测试完成")
        return True
    except Exception as e:
        print(f"基本操作测试失败: {e}")
        return False


def test_directory_operations():
    """测试目录操作功能"""
    print("测试目录操作...")

    try:
        # 列出当前目录文件
        files = os.listdir(".")
        print(f"当前目录文件数: {len(files)}")

        # 显示前5个文件
        print("前5个文件:")
        for file in files[:5]:
            print(f"  - {file}")

        return True
    except Exception as e:
        print(f"目录操作测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 40)
    print("小晨终端助手功能测试")
    print("=" * 40)

    # 定义测试用例
    tests = [
        ("基本操作测试", test_basic_operations),
        ("目录操作测试", test_directory_operations),
    ]

    results = []

    # 执行测试
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "[PASS]" if result else "[FAIL]"
            print(f"  结果: {status}")
        except Exception as e:
            print(f"  异常: {e}")
            results.append((test_name, False))

    # 输出结果汇总
    print("\n" + "=" * 40)
    print("测试结果汇总:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"通过测试: {passed}/{total}")

    for test_name, result in results:
        status = "通过" if result else "失败"
        print(f"  {test_name}: {status}")

    print("=" * 40)

    # 返回总体结果
    return all(result for _, result in results)


if __name__ == "__main__":
    # 设置控制台编码为UTF-8
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    success = main()
    sys.exit(0 if success else 1)