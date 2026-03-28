#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试终端助手功能的示例文件
"""

def hello_world():
    """打印Hello World的简单函数"""
    print("Hello, World!")


def add_numbers(a: int, b: int) -> int:
    """
    计算两个数字的和

    Args:
        a: 第一个数字
        b: 第二个数字

    Returns:
        两个数字的和
    """
    return a + b


def multiply_numbers(a: int, b: int) -> int:
    """
    计算两个数字的乘积

    Args:
        a: 第一个数字
        b: 第二个数字

    Returns:
        两个数字的乘积
    """
    return a * b


if __name__ == "__main__":
    hello_world()
    result = add_numbers(5, 3)
    print(f"5 + 3 = {result}")
    product = multiply_numbers(4, 6)
    print(f"4 * 6 = {product}")