#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精美爱心绘制程序
使用多种库函数创建精美的爱心图案
包含颜色、动画、随机效果等

新增功能：支持命令行参数选择爱心类型
用法：python test.py [heart_type]
可选类型：beautiful, ascii, flower, modern, minimalist, all
"""

import argparse
import sys
import os
import io
import math
import time
import random
from datetime import datetime

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    # 设置标准输出流的编码为UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    # 设置控制台代码页为UTF-8
    os.system('chcp 65001 > nul')

# 尝试导入colorama库用于彩色输出
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    print("提示: 安装colorama库可获得更好的彩色效果: pip install colorama")
def print_color(text, color="", bg_color="", style=""):
    """
    彩色打印函数

    Args:
        text (str): 要打印的文本
        color (str): 前景色
        bg_color (str): 背景色
        style (str): 样式
    """
    if COLORAMA_AVAILABLE:
        color_map = {
            "red": Fore.RED,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "blue": Fore.BLUE,
            "magenta": Fore.MAGENTA,
            "cyan": Fore.CYAN,
            "white": Fore.WHITE,
            "black": Fore.BLACK
        }

        bg_map = {
            "red": Back.RED,
            "green": Back.GREEN,
            "yellow": Back.YELLOW,
            "blue": Back.BLUE,
            "magenta": Back.MAGENTA,
            "cyan": Back.CYAN,
            "white": Back.WHITE,
            "black": Back.BLACK
        }

        style_map = {
            "bright": Style.BRIGHT,
            "dim": Style.DIM,
            "normal": Style.NORMAL
        }

        output = ""
        if color in color_map:
            output += color_map[color]
        if bg_color in bg_map:
            output += bg_map[bg_color]
        if style in style_map:
            output += style_map[style]

        output += text
        if COLORAMA_AVAILABLE:
            output += Style.RESET_ALL

        print(output)
    else:
        print(text)


def draw_beautiful_heart(size=20):
    """
    绘制美观的爱心图案

    Args:
        size (int): 爱心的大小
    """
    print_color("\n" + "💖 美观爱心 💖", "magenta", style="bright")
    print_color("=" * 50, "cyan")

    # 更美观的爱心字符
    heart_chars = ["❤", "💗", "💓", "💞", "💕"]

    for y in range(size, -size, -1):
        line = ""
        for x in range(-2*size, 2*size):
            # 使用更美观的爱心方程
            x_scaled = x * 0.04
            y_scaled = y * 0.07

            # 爱心方程: (x^2 + (1.2*y - sqrt(|x|))^2 - 1)^3 - x^2 * (1.2*y - sqrt(|x|))^3 <= 0
            # 这个方程会产生更美观的心形
            if x == 0:
                x_abs = 0.001  # 避免除零
            else:
                x_abs = abs(x_scaled)

            y_modified = 1.2 * y_scaled - math.sqrt(x_abs)
            equation = math.pow(x_scaled*x_scaled + y_modified*y_modified - 1, 3) - x_scaled*x_scaled * math.pow(y_modified, 3)

            if equation <= 0.1:  # 稍微放宽条件让爱心更饱满
                # 根据位置选择不同的爱心字符，创建渐变效果
                distance_from_center = math.sqrt(x_scaled*x_scaled + y_scaled*y_scaled)
                char_index = int(distance_from_center * 2) % len(heart_chars)
                line += heart_chars[char_index]
            else:
                line += "  "

        # 根据Y坐标添加渐变色
        if y > size * 0.3:
            print_color(line, "red")
        elif y > -size * 0.3:
            print_color(line, "magenta")
        else:
            print_color(line, "pink" if COLORAMA_AVAILABLE else "red")


def draw_ascii_heart(size=15):
    """
    使用ASCII字符绘制精美的爱心

    Args:
        size (int): 爱心的大小
    """
    print_color("\n" + "🎀 ASCII爱心 🎀", "cyan", style="bright")
    print_color("=" * 50, "green")

    # ASCII字符渐变，从密集到稀疏
    ascii_chars = ["█", "▓", "▒", "░", " "]

    for y in range(size, -size, -1):
        line = ""
        for x in range(-2*size, 2*size):
            # 使用标准爱心方程
            x_scaled = x * 0.05
            y_scaled = y * 0.1

            # 标准爱心方程
            equation = math.pow(x_scaled*x_scaled + y_scaled*y_scaled - 1, 3) - x_scaled*x_scaled * math.pow(y_scaled, 3)

            if equation <= 0:
                # 根据方程值选择ASCII字符，创建3D效果
                depth = abs(equation)
                if depth < 0.01:
                    char_idx = 0  # █
                elif depth < 0.05:
                    char_idx = 1  # ▓
                elif depth < 0.1:
                    char_idx = 2  # ▒
                else:
                    char_idx = 3  # ░
                line += ascii_chars[char_idx]
            else:
                line += ascii_chars[-1]  # 空格

        print_color(line, "yellow" if y > 0 else "red")


def draw_flower_heart(size=12):
    """
    绘制花式爱心，结合花朵元素

    Args:
        size (int): 爱心的大小
    """
    print_color("\n" + "🌸 花式爱心 🌸", "green", style="bright")
    print_color("=" * 50, "magenta")

    # 花朵和爱心混合字符
    flower_chars = ["❀", "✿", "💮", "🏵️", "🌺", "🌹", "🥀", "🌷", "🌼", "🌸"]

    for y in range(size, -size, -1):
        line = ""
        for x in range(-2*size, 2*size):
            # 爱心方程
            x_scaled = x * 0.06
            y_scaled = y * 0.09

            # 旋转的爱心方程，更优雅
            angle = math.atan2(y_scaled, x_scaled)
            r = math.sqrt(x_scaled*x_scaled + y_scaled*y_scaled)

            # 极坐标下的爱心方程
            heart_eq = r - (1 - math.sin(angle)) * 0.8

            if heart_eq <= 0.2:
                # 在爱心边缘使用花朵字符
                if abs(heart_eq) < 0.05:
                    char_idx = (abs(x) + abs(y)) % len(flower_chars)
                    line += flower_chars[char_idx]
                else:
                    line += "❤"
            else:
                line += "  "

        # 创建彩虹渐变效果
        colors = ["red", "magenta", "blue", "cyan", "green", "yellow"]
        color_idx = (y + size) % len(colors)
        print_color(line, colors[color_idx] if COLORAMA_AVAILABLE else "red")


def draw_modern_heart():
    """
    绘制现代风格的爱心图案
    """
    print_color("\n" + "✨ 现代爱心 ✨", "blue", style="bright")
    print_color("=" * 50, "cyan")

    # 现代风格的爱心图案
    modern_heart = [
        "                    💖                    ",
        "                💖💖💖💖                ",
        "            💖💖💖💖💖💖💖            ",
        "          💖💖💖💖💖💖💖💖💖          ",
        "        💖💖💖💖💖💖💖💖💖💖💖        ",
        "      💖💖💖💖💖💖💖💖💖💖💖💖💖      ",
        "    💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖    ",
        "  💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖  ",
        "💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖",
        "  💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖  ",
        "    💖💖💖💖💖💖💖💖💖💖💖💖💖💖💖    ",
        "      💖💖💖💖💖💖💖💖💖💖💖💖💖      ",
        "        💖💖💖💖💖💖💖💖💖💖💖        ",
        "          💖💖💖💖💖💖💖💖💖          ",
        "            💖💖💖💖💖💖💖            ",
        "              💖💖💖💖💖              ",
        "                💖💖💖                ",
        "                  💖                  "
    ]

    # 添加闪烁效果
    sparkles = ["✨", "🌟", "⭐", "💫"]

    for i, line in enumerate(modern_heart):
        sparkled_line = ""
        for char in line:
            if char == "💖" and random.random() < 0.2:
                sparkled_line += random.choice(sparkles)
            else:
                sparkled_line += char

        # 创建彩虹渐变
        colors = ["red", "magenta", "blue", "cyan", "green", "yellow"]
        color_idx = i % len(colors)
        print_color(sparkled_line, colors[color_idx] if COLORAMA_AVAILABLE else "red")


def draw_minimalist_heart():
    """
    绘制极简主义风格的爱心
    """
    print_color("\n" + "⚪ 极简爱心 ⚪", "white", style="bright")
    print_color("=" * 50, "white")

    minimalist_heart = [
        "            ○○○            ",
        "        ○○○○○○○○○        ",
        "      ○○○○○○○○○○○○○      ",
        "    ○○○○○○○○○○○○○○○○○    ",
        "  ○○○○○○○○○○○○○○○○○○○○○  ",
        "○○○○○○○○○○○○○○○○○○○○○○○○",
        "  ○○○○○○○○○○○○○○○○○○○○○  ",
        "    ○○○○○○○○○○○○○○○○○    ",
        "      ○○○○○○○○○○○○○      ",
        "        ○○○○○○○○○        ",
        "          ○○○○○          ",
        "            ○            "
    ]

    for line in minimalist_heart:
        # 将○替换为更美观的字符
        beautiful_line = line.replace("○", "●")
        print_color(beautiful_line, "white", style="bright")


def show_progress_animation():
    """
    显示加载动画
    """
    print_color("\n加载中", "yellow", style="bright")

    animation_chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    for i in range(20):
        sys.stdout.write(f"\r{animation_chars[i % len(animation_chars)]} 正在准备精美爱心... {i * 5}%")
        sys.stdout.flush()
        time.sleep(0.1)

    print_color("\r✅ 准备完成! 100%", "green", style="bright")


def main():
    """
    主函数：运行精美爱心绘制程序
    支持命令行参数选择爱心类型
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Beautiful Heart Drawing Program')
    parser.add_argument('heart_type', nargs='?', default='all',
                       choices=['beautiful', 'ascii', 'flower', 'modern', 'minimalist', 'all'],
                       help='Heart type: beautiful, ascii, flower, modern, minimalist, all (default: all)')
    parser.add_argument('--size', type=int, default=18,
                       help='Heart size (only effective for some types)')
    parser.add_argument('--no-clear', action='store_true',
                       help='Do not clear screen')

    args = parser.parse_args()

    # 显示程序标题
    if not args.no_clear:
        os.system('cls' if os.name == 'nt' else 'clear')

    print_color("=" * 60, "cyan", style="bright")
    print_color("            🎀 精美爱心绘制程序 🎀", "magenta", style="bright")
    print_color("=" * 60, "cyan", style="bright")

    print_color(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "yellow")
    print_color(f"系统平台: {sys.platform}", "yellow")
    print_color(f"选择的爱心类型: {args.heart_type}", "yellow")

    if not COLORAMA_AVAILABLE:
        print_color("提示: 安装colorama库可获得彩色效果: pip install colorama", "yellow")

    # 显示加载动画
    show_progress_animation()

    # 根据参数绘制爱心
    heart_type = args.heart_type

    if heart_type in ['beautiful', 'all']:
        time.sleep(0.5)
        draw_beautiful_heart(size=args.size)
        time.sleep(1)

    if heart_type in ['ascii', 'all']:
        draw_ascii_heart(size=min(args.size, 15))
        time.sleep(1)

    if heart_type in ['flower', 'all']:
        draw_flower_heart(size=min(args.size, 12))
        time.sleep(1)

    if heart_type in ['modern', 'all']:
        draw_modern_heart()
        time.sleep(1)

    if heart_type in ['minimalist', 'all']:
        draw_minimalist_heart()
        time.sleep(1)

    # 显示结束信息
    print_color("\n" + "=" * 60, "green", style="bright")
    print_color("            🎉 程序执行完毕！ 🎉", "cyan", style="bright")
    print_color("=" * 60, "green", style="bright")

    # 显示感谢信息
    print_color("\n感谢使用精美爱心绘制程序！", "yellow", style="bright")
    print_color("愿你的生活充满爱与美好！ 💖", "magenta", style="bright")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\n\n程序被用户中断。", "yellow")
    except Exception as e:
        print_color(f"\n程序执行出错: {e}", "red")