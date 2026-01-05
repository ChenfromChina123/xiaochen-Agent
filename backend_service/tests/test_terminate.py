# -*- coding: utf-8 -*-
"""
测试 OCR 任务终止功能
"""

import os
import sys
import time
import uuid
import threading
import requests

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

def test_termination():
    """
    测试 PDF 文档识别终止
    """
    # 使用一个大文件以便有时间执行终止
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "四级1000高频词.pdf")
    if not os.path.exists(pdf_path):
        print(f"[错误] 找不到测试文件: {pdf_path}")
        return

    print("\n" + "="*60)
    print("测试: PDF 文档识别终止")
    print("="*60)

    task_id = f"task_term_{uuid.uuid4().hex[:8]}"
    stop_event = threading.Event()
    
    # 启动进度轮询线程
    poller = threading.Thread(target=poll_progress, args=(task_id, stop_event))
    poller.start()

    def send_terminate():
        time.sleep(3) # 等待3秒后终止
        print(f"\n[测试] 正在发送终止请求 (任务ID: {task_id})...")
        try:
            res = requests.post(f"{SERVER_URL}/api/ocr/terminate/{task_id}")
            print(f"[测试] 终止请求响应: {res.json()}")
        except Exception as e:
            print(f"[测试] 终止请求失败: {e}")

    # 启动终止线程
    terminator = threading.Thread(target=send_terminate)
    terminator.start()

    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {
                'task_id': task_id,
                'extract_text': 'true',
                'page_range_start': '1',
                'page_range_end': '100' # 处理100页，确保有足够时间
            }
            print(f"正在发送识别请求 (任务ID: {task_id})...")
            response = requests.post(f"{SERVER_URL}/api/ocr/document", files=files, data=data)
            
            print(f"\n[测试] 识别请求返回状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"[测试] 识别请求结果: {result}")
                if result.get('code') == 102 or "终止" in result.get('message', ''):
                    print("[✓] 成功验证任务终止功能")
                else:
                    print("[✗] 任务未按预期终止")
            else:
                print(f"[✗] 请求失败: {response.status_code}, {response.text}")
    finally:
        stop_event.set()
        poller.join()
        terminator.join()

if __name__ == "__main__":
    test_termination()
