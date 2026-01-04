# -*- coding: utf-8 -*-
"""
OCR服务客户端调用示例
演示如何调用OCR backend_service 的各种接口
"""

import os
import json
import base64
import requests

# 服务器地址
SERVER_URL = "http://localhost:5000"

def test_health():
    """
    测试健康检查接口
    """
    print("\n" + "="*60)
    print("测试健康检查接口")
    print("="*60)
    
    url = f"{SERVER_URL}/api/health"
    response = requests.get(url)
    result = response.json()
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result

def test_status():
    """
    测试状态接口
    """
    print("\n" + "="*60)
    print("测试状态接口")
    print("="*60)
    
    url = f"{SERVER_URL}/api/status"
    response = requests.get(url)
    result = response.json()
    
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result

def test_ocr_file(file_path, extract_text=False):
    """
    测试文件识别接口
    
    参数:
        file_path: 文件路径
        extract_text: 是否只返回文本
    """
    print("\n" + "="*60)
    print(f"测试文件识别: {file_path}")
    print("="*60)
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return None
    
    url = f"{SERVER_URL}/api/ocr/file"
    
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        data = {'extract_text': 'true' if extract_text else 'false'}
        response = requests.post(url, files=files, data=data)
    
    result = response.json()
    
    print(f"响应状态码: {response.status_code}")
    print(f"识别成功: {result['success']}")
    
    if extract_text and result['success']:
        print(f"识别文本:\n{result['data']['text']}")
    else:
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result

def test_ocr_base64(image_path, extract_text=False):
    """
    测试base64识别接口
    
    参数:
        image_path: 图片路径
        extract_text: 是否只返回文本
    """
    print("\n" + "="*60)
    print(f"测试base64识别: {image_path}")
    print("="*60)
    
    if not os.path.exists(image_path):
        print(f"文件不存在: {image_path}")
        return None
    
    # 读取图片并转换为base64
    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    url = f"{SERVER_URL}/api/ocr/base64"
    
    payload = {
        'image': image_base64,
        'extract_text': extract_text
    }
    
    response = requests.post(url, json=payload)
    result = response.json()
    
    print(f"响应状态码: {response.status_code}")
    print(f"识别成功: {result['success']}")
    
    if extract_text and result['success']:
        print(f"识别文本:\n{result['data']['text']}")
    else:
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result

def test_ocr_url(image_url, extract_text=False):
    """
    测试URL识别接口
    
    参数:
        image_url: 图片URL
        extract_text: 是否只返回文本
    """
    print("\n" + "="*60)
    print(f"测试URL识别: {image_url}")
    print("="*60)
    
    url = f"{SERVER_URL}/api/ocr/url"
    
    payload = {
        'url': image_url,
        'extract_text': extract_text
    }
    
    response = requests.post(url, json=payload)
    result = response.json()
    
    print(f"响应状态码: {response.status_code}")
    print(f"识别成功: {result['success']}")
    
    if extract_text and result['success']:
        print(f"识别文本:\n{result['data']['text']}")
    else:
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result

def test_ocr_document(doc_path, page_range_start=None, page_range_end=None, dpi=200, extract_text=False):
    """
    测试文档识别接口
    
    参数:
        doc_path: 文档路径
        page_range_start: 起始页
        page_range_end: 结束页
        dpi: 渲染DPI
        extract_text: 是否只返回文本
    """
    print("\n" + "="*60)
    print(f"测试文档识别: {doc_path}")
    print("="*60)
    
    if not os.path.exists(doc_path):
        print(f"文件不存在: {doc_path}")
        return None
    
    url = f"{SERVER_URL}/api/ocr/document"
    
    with open(doc_path, 'rb') as f:
        files = {'file': (os.path.basename(doc_path), f)}
        data = {
            'extract_text': 'true' if extract_text else 'false',
            'dpi': str(dpi)
        }
        
        if page_range_start:
            data['page_range_start'] = str(page_range_start)
        if page_range_end:
            data['page_range_end'] = str(page_range_end)
        
        response = requests.post(url, files=files, data=data)
    
    result = response.json()
    
    print(f"响应状态码: {response.status_code}")
    print(f"识别成功: {result['success']}")
    
    if extract_text and result['success']:
        print(f"识别文本:\n{result['data']['text']}")
    else:
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    return result

def test_ocr_batch(file_paths, extract_text=False):
    """
    测试批量识别接口
    
    参数:
        file_paths: 文件路径列表
        extract_text: 是否只返回文本
    """
    print("\n" + "="*60)
    print(f"测试批量识别: {len(file_paths)}个文件")
    print("="*60)
    
    url = f"{SERVER_URL}/api/ocr/batch"
    
    files = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            files.append(('files', (os.path.basename(file_path), open(file_path, 'rb'))))
        else:
            print(f"警告: 文件不存在: {file_path}")
    
    if not files:
        print("没有有效的文件")
        return None
    
    try:
        data = {'extract_text': 'true' if extract_text else 'false'}
        response = requests.post(url, files=files, data=data)
        result = response.json()
        
        print(f"响应状态码: {response.status_code}")
        print(f"识别成功: {result['success']}")
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        return result
    finally:
        # 关闭所有文件
        for _, (_, f) in files:
            f.close()

def main():
    """
    主测试函数
    """
    print("\n" + "="*60)
    print("OCR服务客户端测试")
    print(f"服务器地址: {SERVER_URL}")
    print("="*60)
    
    # 1. 健康检查
    try:
        health_result = test_health()
        if not health_result['success']:
            print("\n[错误] 服务不健康，请检查服务器")
            return
    except Exception as e:
        print(f"\n[错误] 无法连接到服务器: {e}")
        print("请确保服务器已启动: python ocr_server.py")
        return
    
    # 2. 获取状态
    test_status()
    
    # 3. 测试文件识别（需要提供测试图片）
    # test_ocr_file("test_image.jpg", extract_text=True)
    
    # 4. 测试base64识别
    # test_ocr_base64("test_image.jpg", extract_text=True)
    
    # 5. 测试URL识别
    # test_ocr_url("https://example.com/image.jpg", extract_text=True)
    
    # 6. 测试文档识别
    # test_ocr_document("test_document.pdf", extract_text=True)
    
    # 7. 测试批量识别
    # test_ocr_batch(["test1.jpg", "test2.png"], extract_text=True)
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == '__main__':
    main()

