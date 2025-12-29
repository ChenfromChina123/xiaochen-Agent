#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件编辑功能测试脚本

此脚本专门测试文件编辑功能，包括：
1. 行级编辑（插入、删除、替换）
2. 批量编辑
3. 模式匹配和替换
4. 文件备份和恢复

版本: 1.0
修改日志:
- 2024-01-15: 初始版本创建
"""

import os
import tempfile
import shutil


def test_line_editing():
    """
    测试行级编辑功能

    演示如何：
    1. 在指定位置插入行
    2. 删除指定范围的行
    3. 替换特定行
    """
    print("=== 开始行级编辑测试 ===")

    # 创建测试文件
    test_content = """# 测试文件
第一行内容
第二行内容
第三行内容
第四行内容
第五行内容
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        test_file = f.name
        f.write(test_content)
        print(f"1. 已创建测试文件: {test_file}")

    # 读取文件内容
    with open(test_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print("\n2. 原始文件内容:")
    for i, line in enumerate(lines, 1):
        print(f"   行 {i}: {line.rstrip()}")

    # 执行编辑操作
    print("\n3. 执行编辑操作:")

    # 显示原始行
    print("   原始行:")
    for i, line in enumerate(lines, 1):
        print(f"     行{i}: {line.rstrip()}")

    # 1. 删除第2行（索引1）- "第一行内容"
    if len(lines) > 1:
        deleted_line = lines.pop(1)
        print(f"   - 删除第2行: {deleted_line.rstrip()}")

    # 显示删除后的行
    print("   删除第2行后的行:")
    for i, line in enumerate(lines, 1):
        print(f"     行{i}: {line.rstrip()}")

    # 2. 在第3行位置插入新行（索引2）
    insert_index = 2  # 在"第三行内容"之前插入
    new_line = "这是插入的新行\n"
    lines.insert(insert_index, new_line)
    print(f"   - 在第{insert_index+1}行位置插入新行")

    # 显示插入后的行
    print("   插入新行后的行:")
    for i, line in enumerate(lines, 1):
        print(f"     行{i}: {line.rstrip()}")

    # 3. 替换第5行（索引4）- 原来的"第四行内容"
    if len(lines) > 4:
        lines[4] = "这是替换后的第四行\n"
        print(f"   - 替换第5行内容")

    # 写回文件
    with open(test_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("\n4. 编辑后的文件内容:")
    with open(test_file, 'r', encoding='utf-8') as f:
        edited_content = f.read()
        print(edited_content)

    # 验证编辑结果
    expected_lines = [
        "# 测试文件\n",
        "第二行内容\n",      # 删除第一行后，原来的第二行变成了第一行
        "这是插入的新行\n",  # 在第三行位置插入的新行
        "第三行内容\n",      # 原来的第三行
        "这是替换后的第四行\n",  # 替换原来的第四行
        "第五行内容\n"       # 原来的第五行
    ]

    with open(test_file, 'r', encoding='utf-8') as f:
        final_lines = f.readlines()

    if final_lines == expected_lines:
        print("✓ 行级编辑测试通过")
    else:
        print("✗ 行级编辑测试失败")
        print(f"   预期行数: {len(expected_lines)}")
        print(f"   实际行数: {len(final_lines)}")
        print(f"   预期: {expected_lines}")
        print(f"   实际: {final_lines}")

    # 清理
    os.unlink(test_file)
    print(f"\n5. 已清理测试文件: {test_file}")
    print("=== 行级编辑测试完成 ===")
    print("=== 行级编辑测试完成 ===")


def test_pattern_replacement():
    """
    测试模式匹配和替换功能

    演示如何：
    1. 使用正则表达式匹配模式
    2. 批量替换文本
    3. 条件替换
    """
    print("\n" + "="*50)
    print("=== 开始模式匹配替换测试 ===")

    # 创建包含多种格式的测试文件
    test_content = """# 配置文件示例
server_host = "localhost"
server_port = 8080
database_url = "postgresql://user:pass@localhost:5432/db"
api_key = "sk-1234567890abcdef"
debug_mode = true
max_connections = 100
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False, encoding='utf-8') as f:
        test_file = f.name
        f.write(test_content)
        print(f"1. 已创建测试文件: {test_file}")

    print("\n2. 原始文件内容:")
    print(test_content)

    # 读取文件内容
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("\n3. 执行模式替换操作:")

    # 替换端口号
    import re
    old_content = content

    # 将端口号从8080改为9090
    content = re.sub(r'port\s*=\s*\d+', 'port = 9090', content)
    print("   - 将端口号从8080改为9090")

    # 隐藏API密钥
    content = re.sub(r'api_key\s*=\s*"[^"]+"', 'api_key = "***HIDDEN***"', content)
    print("   - 隐藏API密钥")

    # 将debug模式改为false
    content = content.replace('debug_mode = true', 'debug_mode = false')
    print("   - 将debug模式改为false")

    # 写回文件
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n4. 替换后的文件内容:")
    print(content)

    # 验证替换结果
    if 'port = 9090' in content and 'api_key = "***HIDDEN***"' in content and 'debug_mode = false' in content:
        print("✓ 模式匹配替换测试通过")
    else:
        print("✗ 模式匹配替换测试失败")

    # 清理
    os.unlink(test_file)
    print(f"\n5. 已清理测试文件: {test_file}")
    print("=== 模式匹配替换测试完成 ===")


def test_file_backup_restore():
    """
    测试文件备份和恢复功能

    演示如何：
    1. 创建文件备份
    2. 恢复文件
    3. 版本控制
    """
    print("\n" + "="*50)
    print("=== 开始文件备份恢复测试 ===")

    # 创建测试目录
    temp_dir = tempfile.mkdtemp()
    original_dir = os.path.join(temp_dir, "original")
    backup_dir = os.path.join(temp_dir, "backup")
    os.makedirs(original_dir, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)

    print(f"1. 已创建测试目录结构:")
    print(f"   原始目录: {original_dir}")
    print(f"   备份目录: {backup_dir}")

    # 创建原始文件
    original_files = {
        "document.txt": "这是原始文档内容\n版本1.0\n",
        "config.json": '{"version": "1.0", "settings": {"debug": true}}',
        "data.csv": "id,name,value\n1,item1,100\n2,item2,200\n"
    }

    for filename, content in original_files.items():
        filepath = os.path.join(original_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   已创建原始文件: {filename}")

    print("\n2. 执行备份操作:")

    # 备份所有文件
    for filename in original_files.keys():
        src = os.path.join(original_dir, filename)
        dst = os.path.join(backup_dir, filename)
        shutil.copy2(src, dst)
        print(f"   - 已备份: {filename}")

    print("\n3. 修改原始文件（模拟错误修改）:")

    # 修改原始文件
    document_path = os.path.join(original_dir, "document.txt")
    with open(document_path, 'a', encoding='utf-8') as f:
        f.write("错误的内容添加\n")

    print("   已向document.txt添加错误内容")

    print("\n4. 验证备份文件完整性:")

    # 比较原始文件和备份文件
    backup_document = os.path.join(backup_dir, "document.txt")
    with open(backup_document, 'r', encoding='utf-8') as f:
        backup_content = f.read()

    if "错误的内容添加" not in backup_content:
        print("   ✓ 备份文件未受错误修改影响")
    else:
        print("   ✗ 备份文件被错误修改")

    print("\n5. 执行恢复操作:")

    # 从备份恢复文件
    for filename in original_files.keys():
        src = os.path.join(backup_dir, filename)
        dst = os.path.join(original_dir, filename)
        shutil.copy2(src, dst)
        print(f"   - 已恢复: {filename}")

    # 验证恢复结果
    with open(document_path, 'r', encoding='utf-8') as f:
        restored_content = f.read()

    if "错误的内容添加" not in restored_content:
        print("   ✓ 文件恢复成功")
    else:
        print("   ✗ 文件恢复失败")

    print("\n6. 最终目录结构:")
    for root, dirs, files in os.walk(temp_dir):
        level = root.replace(temp_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{subindent}{file}')

    # 清理
    shutil.rmtree(temp_dir)
    print(f"\n7. 已清理测试目录: {temp_dir}")
    print("=== 文件备份恢复测试完成 ===")


def run_all_tests():
    """
    运行所有测试函数
    """
    print("开始执行文件编辑功能测试套件")
    print("="*60)

    test_line_editing()
    test_pattern_replacement()
    test_file_backup_restore()

    print("\n" + "="*60)
    print("所有测试完成！")


if __name__ == "__main__":
    # 设置控制台编码为UTF-8
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    run_all_tests()