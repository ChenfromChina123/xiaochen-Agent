# -*- coding: utf-8 -*-
"""
测试 OCR 进度反馈功能
使用 tests/data 中的文件，演示每 10% 的进度回调
"""

import os
import sys
import time
import uuid
import threading
import requests

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 服务器地址
SERVER_URL = "http://127.0.0.1:4999/ocr"

def poll_progress(task_id, stop_event):
    """
    轮询进度接口并打印
    """
    print(f"开始轮询任务 {task_id} 的进度...")
    last_p = -1
    while not stop_event.is_set():
        try:
            response = requests.get(f"{SERVER_URL}/api/progress/{task_id}")
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    p = data['data']['percentage']
                    if p != last_p:
                        print(f"  >>> [进度反馈] 任务 {task_id}: {p}%")
                        last_p = p
        except Exception as e:
            pass
        time.sleep(0.5)

def test_document_progress():
    """
    测试 PDF 文档识别进度
    """
    pdf_path = os.path.join(BASE_DIR, "tests", "data", "四级1000高频词.pdf")
    if not os.path.exists(pdf_path):
        print(f"[错误] 找不到测试文件: {pdf_path}")
        return

    print("\n" + "="*60)
    print("测试: PDF 文档识别进度 (每10%反馈)")
    print("="*60)

    task_id = f"task_doc_{uuid.uuid4().hex[:8]}"
    stop_event = threading.Event()
    
    # 启动进度轮询线程
    poller = threading.Thread(target=poll_progress, args=(task_id, stop_event))
    poller.start()

    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {
                'task_id': task_id,
                'extract_text': 'true',
                'page_range_start': '1',
                'page_range_end': '10' # 只测前10页，加快速度
            }
            print(f"正在发送识别请求 (任务ID: {task_id})...")
            response = requests.post(f"{SERVER_URL}/api/ocr/document", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and 'text' in result.get('data', {}):
                    print(f"[✓] 识别完成! 成功提取文本，前100个字符: \n{result['data']['text'][:100]}...")
                else:
                    print(f"[!] 识别结束，但返回格式不符合预期: {result}")
            else:
                print(f"[✗] 请求失败: {response.status_code}, {response.text}")
    finally:
        stop_event.set()
        poller.join()

def test_batch_progress():
    """
    测试批量文件识别进度
    """
    data_dir = os.path.join(BASE_DIR, "tests", "data")
    test_files = [f for f in os.listdir(data_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    
    if not test_files:
        print("[错误] tests/data 中没有图片文件用于批量测试")
        return

    # 为了演示 10% 间隔，我们需要多几个文件，或者重复同一个文件
    upload_files = []
    for i in range(5): # 减少到5个文件，避免 Nginx 502 超时
        f_name = test_files[0]
        f_path = os.path.join(data_dir, f_name)
        upload_files.append(('files', (f"{i}_{f_name}", open(f_path, 'rb'), 'image/jpeg')))

    print("\n" + "="*60)
    print("测试: 批量文件识别进度 (每10%反馈)")
    print("="*60)

    task_id = f"task_batch_{uuid.uuid4().hex[:8]}"
    stop_event = threading.Event()
    
    # 启动进度轮询线程
    poller = threading.Thread(target=poll_progress, args=(task_id, stop_event))
    poller.start()

    try:
        data = {'task_id': task_id, 'extract_text': 'true'}
        print(f"正在发送批量识别请求 (任务ID: {task_id}, 文件数: 5)...")
        response = requests.post(f"{SERVER_URL}/api/ocr/batch", files=upload_files, data=data)
        
        if response.status_code == 200:
            print(f"[✓] 批量识别完成!")
        else:
            print(f"[✗] 请求失败: {response.status_code}, {response.text}")
    finally:
        # 关闭所有打开的文件
        for item in upload_files:
            item[1][1].close()
        stop_event.set()
        poller.join()

if __name__ == "__main__":
    test_document_progress()
    test_batch_progress()
