#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件读写编辑功能的示例文件
此文件用于演示文件创建、编辑和读取操作
版本: 1.0
修改日志:
- 2024-01-01: 初始版本创建
- 2024-01-02: 添加乘法函数和更新主函数
- 2024-01-03: 修复缩进问题，添加文件操作测试函数
"""

def greet(name: str) -> str:
    """
    向指定名字的人打招呼

    Args:
        name (str): 要打招呼的人名

    Returns:
        str: 问候语
    """
    return f"你好，{name}！欢迎使用文件操作测试。"


def add_numbers(a: int, b: int) -> int:
    """
    计算两个整数的和

    Args:
        a (int): 第一个整数
        b (int): 第二个整数

    Returns:
        int: 两个整数的和
    """
    return a + b


def multiply_numbers(a: int, b: int) -> int:
    """
    计算两个整数的乘积

    Args:
        a (int): 第一个整数
        b (int): 第二个整数

    Returns:
        int: 两个整数的乘积
    """
    return a * b


def main():
    """
    主函数，演示功能调用
    """
    print(greet("开发者"))
    result = add_numbers(5, 3)
    print(f"5 + 3 = {result}")

    # 演示乘法函数
    product = multiply_numbers(4, 7)
    print(f"4 × 7 = {product}")


def test_file_operations():
    """
    测试文件读写编辑功能

    此函数演示：
    1. 创建新文件并写入内容
    2. 读取文件内容
    3. 编辑文件内容
    4. 验证编辑结果
    """
    import os
    import tempfile

    print("=== 开始文件操作测试 ===")

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        temp_file_path = f.name
        initial_content = "这是初始内容\n第二行\n第三行"
        f.write(initial_content)
        print(f"1. 已创建临时文件: {temp_file_path}")
        print(f"   初始内容: {initial_content}")

    # 读取文件内容
    with open(temp_file_path, 'r', encoding='utf-8') as f:
        read_content = f.read()
        print(f"2. 读取文件内容: {read_content}")

    # 编辑文件内容（追加新行）
    with open(temp_file_path, 'a', encoding='utf-8') as f:
        new_content = "\n这是追加的内容\n测试完成"
        f.write(new_content)
        print(f"3. 已追加内容: {new_content}")

    # 再次读取验证
    with open(temp_file_path, 'r', encoding='utf-8') as f:
        final_content = f.read()
        print(f"4. 最终文件内容: {final_content}")
        # 验证内容
        expected_content = initial_content + new_content
        if final_content == expected_content:
            print("测试通过：文件读写编辑功能正常")
        else:
            print("测试失败：文件内容不符合预期")

    # 清理临时文件
    os.unlink(temp_file_path)
    print(f"5. 已清理临时文件: {temp_file_path}")
    print("=== 文件操作测试完成 ===")

    def demonstrate_file_editing():
        """
        if __name__ == "__main__":
            # 设置控制台编码为UTF-8
            import sys
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

            main()
            print("\n" + "="*50)
            test_file_operations()
            print("\n" + "="*50)
            demonstrate_file_editing()
            print("\n" + "="*50)
            advanced_file_operations()
        2. 使用编辑功能修改文件内容
        3. 验证编辑结果
        """
        import os
        import tempfile

        print("=== 开始文件编辑功能演示 ===")

        # 创建测试文件
        test_content = """# 测试文件编辑功能
    def old_function():
        \"\"\"这是一个旧函数\"\"\"
        return "旧功能"

    def another_old_function():
        \"\"\"另一个旧函数\"\"\"
        return "另一个旧功能"

    # 主程序
    if __name__ == "__main__":
        result = old_function()
        print(result)
    """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            test_file_path = f.name
            f.write(test_content)
            print(f"1. 已创建测试文件: {test_file_path}")
            print("   初始内容:")
            print(test_content)

        # 演示编辑功能：替换函数名和添加新函数
        print("\n2. 执行编辑操作:")
        print("   - 将 'old_function' 重命名为 'new_function'")
        print("   - 将 'another_old_function' 重命名为 'updated_function'")
        print("   - 添加一个新函数 'additional_function'")

        # 读取文件内容
        with open(test_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 执行编辑操作
        edited_lines = []
        for line in lines:
            # 替换函数名
            edited_line = line.replace('old_function', 'new_function')
            edited_line = edited_line.replace('another_old_function', 'updated_function')
            edited_lines.append(edited_line)

        # 在第15行后添加新函数（在if __name__ == "__main__":之前）
        insert_index = 15  # 在if __name__ == "__main__":之前插入
        new_function = """
    def additional_function():
        \"\"\"新增的函数，演示编辑功能\"\"\"
        return "这是通过编辑功能添加的新函数"
    """

        # 插入新函数
        edited_lines.insert(insert_index, new_function)

        # 更新主程序调用
        for i, line in enumerate(edited_lines):
            if 'result = new_function()' in line:
                # 在原有调用后添加对新函数的调用
                edited_lines[i] = line.rstrip() + '\n    result2 = additional_function()\n    print(result2)\n'
                break

        # 写回文件
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.writelines(edited_lines)

        print("\n3. 编辑后的文件内容:")
        with open(test_file_path, 'r', encoding='utf-8') as f:
            edited_content = f.read()
            print(edited_content)

        # 验证编辑结果
        print("\n4. 验证编辑结果:")
        if 'def new_function():' in edited_content and 'def additional_function():' in edited_content:
            print("✓ 编辑成功：函数名已更新，新函数已添加")
        else:
            print("✗ 编辑失败：预期内容未找到")

        # 清理临时文件
        os.unlink(test_file_path)
        print(f"\n5. 已清理测试文件: {test_file_path}")
        print("=== 文件编辑功能演示完成 ===")


    def advanced_file_operations():
        """
        高级文件操作演示

        此函数展示更复杂的文件操作：
        1. 批量文件处理
        2. 模式匹配和替换
        3. 文件备份和恢复
        """
        import os
        import tempfile
        import shutil

        print("=== 开始高级文件操作演示 ===")

        # 创建测试目录和多个文件
        temp_dir = tempfile.mkdtemp()
        print(f"1. 已创建测试目录: {temp_dir}")

        # 创建多个测试文件
        test_files = {
            "config.txt": """# 配置文件
    server=localhost
    port=8080
    debug=true
    max_connections=100
    """,
            "data.csv": """id,name,value
    1,item1,100
    2,item2,200
    3,item3,300
    """,
            "script.py": """#!/usr/bin/env python3
    # 测试脚本
    def process_data(data):
        return data * 2

    if __name__ == "__main__":
        result = process_data(10)
        print(f"结果: {result}")
    """
        }

        for filename, content in test_files.items():
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   已创建文件: {filename}")

        # 演示批量编辑：将所有文件中的端口号从8080改为9090
        print("\n2. 执行批量编辑操作:")
        print("   将 config.txt 中的端口号从 8080 改为 9090")

        config_path = os.path.join(temp_dir, "config.txt")
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()

        # 替换端口号
        updated_config = config_content.replace('port=8080', 'port=9090')

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(updated_config)

        # 验证替换结果
        with open(config_path, 'r', encoding='utf-8') as f:
            final_config = f.read()

        if 'port=9090' in final_config:
            print("   ✓ 批量编辑成功：端口号已更新")
        else:
            print("   ✗ 批量编辑失败：端口号未更新")

        # 创建备份
        backup_dir = os.path.join(temp_dir, "backup")
        os.makedirs(backup_dir, exist_ok=True)

        for filename in test_files.keys():
            src = os.path.join(temp_dir, filename)
            dst = os.path.join(backup_dir, filename)
            shutil.copy2(src, dst)

        print(f"\n3. 已创建文件备份到: {backup_dir}")

        # 显示目录结构
        print("\n4. 最终目录结构:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f'{indent}{os.path.basename(root)}/')
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f'{subindent}{file}')

        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n5. 已清理测试目录: {temp_dir}")
        print("=== 高级文件操作演示完成 ===")
if __name__ == "__main__":
    main()
    print("\n" + "="*50)
    test_file_operations()
    print("\n" + "="*50)
    demonstrate_file_editing()
    print("\n" + "="*50)
    advanced_file_operations()