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

# 服务器地址
SERVER_URL = "http://localhost:5000"

def create_test_image(text="测试文字OCR", filename="test_image.png"):
    """
    创建一个包含文字的测试图片
    """
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
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (os.path.basename(image_path), f)}
            data = {'extract_text': 'true'}
            response = requests.post(f"{SERVER_URL}/api/ocr/file", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                text = result['data'].get('text', '')
                print(f"[✓] 识别成功")
                print(f"[✓] 识别文本: {text}")
                return True
            else:
                print(f"[✗] 识别失败: {result.get('message')}")
                return False
        else:
            print(f"[✗] 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False

def test_ocr_base64(image_path):
    """
    测试Base64识别接口
    """
    print("\n" + "="*60)
    print("测试4: Base64识别")
    print("="*60)
    
    try:
        # 读取图片并转换为base64
        with open(image_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            'image': image_base64,
            'extract_text': True
        }
        
        response = requests.post(f"{SERVER_URL}/api/ocr/base64", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                text = result['data'].get('text', '')
                print(f"[✓] 识别成功")
                print(f"[✓] 识别文本: {text}")
                return True
            else:
                print(f"[✗] 识别失败: {result.get('message')}")
                return False
        else:
            print(f"[✗] 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False

def test_ocr_batch(image_paths):
    """
    测试批量识别接口
    """
    print("\n" + "="*60)
    print("测试5: 批量识别")
    print("="*60)
    
    try:
        files = []
        for path in image_paths:
            if os.path.exists(path):
                files.append(('files', (os.path.basename(path), open(path, 'rb'))))
        
        data = {'extract_text': 'true'}
        response = requests.post(f"{SERVER_URL}/api/ocr/batch", files=files, data=data)
        
        # 关闭文件
        for _, (_, f) in files:
            f.close()
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                total = result['data']['total']
                success_count = sum(1 for r in result['data']['results'] if r.get('success'))
                print(f"[✓] 批量识别完成")
                print(f"[✓] 成功: {success_count}/{total}")
                for r in result['data']['results']:
                    if r.get('success'):
                        print(f"    - {r['filename']}: {r.get('text', '')[:50]}...")
                return True
            else:
                print(f"[✗] 识别失败: {result.get('message')}")
                return False
        else:
            print(f"[✗] 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False

def test_error_handling():
    """
    测试错误处理
    """
    print("\n" + "="*60)
    print("测试6: 错误处理")
    print("="*60)
    
    # 测试不存在的接口
    try:
        response = requests.get(f"{SERVER_URL}/api/nonexistent")
        if response.status_code == 404:
            print(f"[✓] 404错误处理正确")
        else:
            print(f"[✗] 404错误处理异常")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False
    
    # 测试缺少参数
    try:
        response = requests.post(f"{SERVER_URL}/api/ocr/file")
        result = response.json()
        if not result['success']:
            print(f"[✓] 参数验证正确: {result['message']}")
        else:
            print(f"[✗] 参数验证异常")
            return False
    except Exception as e:
        print(f"[✗] 错误: {e}")
        return False
    
    return True

def main():
    """
    主测试函数
    """
    print("\n" + "="*60)
    print("OCR服务器完整功能测试")
    print(f"服务器地址: {SERVER_URL}")
    print("="*60)
    
    # 检查服务器是否运行
    print("\n[步骤0] 检查服务器连接...")
    try:
        response = requests.get(f"{SERVER_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print(f"[✗] 服务器未运行或不可达")
            print(f"[提示] 请先启动服务器: py ocr_server.py")
            return
    except Exception as e:
        print(f"[✗] 无法连接到服务器: {e}")
        print(f"[提示] 请先启动服务器: py ocr_server.py")
        return
    
    print(f"[✓] 服务器连接成功")
    
    # 创建测试图片
    print("\n[步骤1] 创建测试图片...")
    test_image1 = create_test_image("测试文字OCR", "test_image1.png")
    test_image2 = create_test_image("识别成功", "test_image2.png")
    
    # 运行测试
    results = []
    
    results.append(("服务器信息", test_server_info()))
    results.append(("健康检查", test_health()))
    results.append(("文件识别", test_ocr_file(test_image1)))
    results.append(("Base64识别", test_ocr_base64(test_image1)))
    results.append(("批量识别", test_ocr_batch([test_image1, test_image2])))
    results.append(("错误处理", test_error_handling()))
    
    # 清理测试文件
    print("\n[清理] 删除测试图片...")
    for img in [test_image1, test_image2]:
        if os.path.exists(img):
            os.remove(img)
            print(f"[✓] 删除: {img}")
    
    # 统计结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    total = len(results)
    success = sum(1 for _, r in results if r)
    
    for name, result in results:
        status = "[✓] 通过" if result else "[✗] 失败"
        print(f"{status} - {name}")
    
    print("\n" + "="*60)
    print(f"总计: {success}/{total} 测试通过")
    print(f"成功率: {success*100//total}%")
    print("="*60)
    
    if success == total:
        print("\n[✓] 所有测试通过！OCR服务器运行正常！")
    else:
        print(f"\n[!] {total - success} 个测试失败，请检查服务器日志")

if __name__ == '__main__':
    main()

