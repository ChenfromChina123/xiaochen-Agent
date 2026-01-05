# -*- coding: utf-8 -*-
"""
OCR服务器完整功能测试
"""

import os
import sys
import json
import base64
import time
import requests
from PIL import Image, ImageDraw, ImageFont

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 服务器地址
SERVER_URL = "http://aistudy.icu/ocr"

def create_test_image(text="测试文字OCR", filename=None):
    """
    创建一个包含文字的测试图片
    """
    if filename is None:
        filename = os.path.join(BASE_DIR, "tests", "test_image.png")
    
    # 创建白色背景图片
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # 尝试使用中文字体，如果不存在则使用默认
    try:
        # Windows中文字体
        font = ImageFont.truetype("msyh.ttc", 48)
    except:
        try:
            font = ImageFont.truetype("simhei.ttf", 48)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
    
    # 绘制文字
    draw.text((50, 80), text, fill='black', font=font)
    
    # 保存图片
    img.save(filename)
    print(f"[✓] 创建测试图片: {filename}")
    return filename

def test_server_info():
    """
    测试服务器信息接口
    """
    print("\n" + "="*60)
    print("测试1: 服务器信息")
    print("="*60)
    
    try:
        response = requests.get(f"{SERVER_URL}/")
        if response.status_code == 200:
            result = response.json()
            print(f"[✓] 服务名称: {result['data']['service']}")
            print(f"[✓] 版本: {result['data']['version']}")
            print(f"[✓] 支持格式: {len(result['data']['supported_formats'])}种")
            return True
        else:
            print(f"[✗] 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False

def test_health():
    """
    测试健康检查接口
    """
    print("\n" + "="*60)
    print("测试2: 健康检查")
    print("="*60)
    
    try:
        response = requests.get(f"{SERVER_URL}/api/health")
        if response.status_code == 200:
            result = response.json()
            if result['data']['status'] == 'healthy':
                print(f"[✓] 服务健康")
                print(f"[✓] 引擎已初始化: {result['data']['engine_initialized']}")
                return True
            else:
                print(f"[✗] 服务不健康")
                return False
        else:
            print(f"[✗] 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False

def test_ocr_file(image_path):
    """
    测试文件识别接口
    """
    print("\n" + "="*60)
    print("测试3: 文件识别")
    print("="*60)
    
    if not os.path.exists(image_path):
        print(f"[✗] 图片文件不存在: {image_path}")
        return False

    try:
        with open(image_path, 'rb') as f:
            files = {'file': (os.path.basename(image_path), f)}
            data = {'extract_text': 'true'}
            response = requests.post(f"{SERVER_URL}/api/ocr/file", files=files, data=data)
            
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"[✓] 识别成功")
                print(f"[✓] 识别文本:\n{result['data']['text']}")
                return True
            else:
                print(f"[✗] 识别失败: {result['message']}")
                return False
        else:
            print(f"[✗] 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False

def main():
    """
    运行所有测试
    """
    print("OCR服务器完整功能测试")
    print("="*60)
    
    # 1. 检查服务器是否在线
    if not test_server_info():
        print("\n[!] 错误: 服务器未在线，请先启动服务器")
        print("    提示: 运行 scripts/start_server.bat")
        return

    # 2. 健康检查
    test_health()
    
    # 3. 创建测试图片并识别
    image_path = create_test_image()
    try:
        test_ocr_file(image_path)
    finally:
        # 清理测试图片
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"[✓] 已清理测试图片: {image_path}")
            except:
                pass

if __name__ == "__main__":
    main()

