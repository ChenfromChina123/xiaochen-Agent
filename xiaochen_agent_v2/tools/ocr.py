# -*- coding: utf-8 -*-
"""
OCR 工具封装模块
提供简单的接口供 Agent 调用 OCR 功能
"""

import os
import sys
import json
import datetime
import requests
import uuid
import threading
import time
from typing import Dict, Any, Optional

# 导入清理工具与路径工具
try:
    from ..utils.files import prune_directory, get_storage_root, get_repo_root
except (ImportError, ValueError):
    prune_directory = None
    def get_storage_root():
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(current_dir, "storage")
    def get_repo_root():
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# OCR backend_service 配置加载
def _load_config():
    """从 ocr_config.json 加载配置，如果失败则使用默认值"""
    default_server_url = "http://localhost:5000"
    default_storage_dir = "ocr_results" # 默认相对于 get_storage_root()
    
    repo_root = get_repo_root()
    storage_root = get_storage_root()
    config_path = os.path.join(repo_root, "ocr_config.json")
    
    server_url = default_server_url
    storage_relative_path = default_storage_dir
    max_storage_files = 50
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                server_url = config_data.get("ocr_server_url", default_server_url)
                storage_relative_path = config_data.get("ocr_storage_dir", default_storage_dir)
                max_storage_files = config_data.get("ocr_max_storage_files", 50)
        except Exception as e:
            print(f"  [OCR警告] 无法加载配置文件 {config_path}: {e}")
    else:
        # 如果 ocr_config.json 不存在，尝试从 config.json 读取 (向后兼容)
        main_config_path = os.path.join(repo_root, "config.json")
        if os.path.exists(main_config_path):
            try:
                with open(main_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    if "ocr_server_url" in config_data:
                        server_url = config_data.get("ocr_server_url", default_server_url)
                        storage_relative_path = config_data.get("ocr_storage_dir", default_storage_dir)
                        max_storage_files = config_data.get("ocr_max_storage_files", 50)
            except Exception:
                pass
            
    # 计算存储目录的绝对路径
    if os.path.isabs(storage_relative_path):
        abs_storage_dir = storage_relative_path
    else:
        # 如果是相对路径，且包含 "storage/" 前缀，则尝试去除它并基于 storage_root
        if storage_relative_path.startswith("storage/"):
            storage_relative_path = storage_relative_path[len("storage/"):]
        elif storage_relative_path.startswith("storage\\"):
            storage_relative_path = storage_relative_path[len("storage\\"):]
            
        abs_storage_dir = os.path.join(storage_root, storage_relative_path)
        
    return server_url, abs_storage_dir, max_storage_files

OCR_SERVER_URL, STORAGE_DIR, MAX_STORAGE_FILES = _load_config()

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR, exist_ok=True)

def _save_result_locally(file_path: str, result: Dict[str, Any]) -> str:
    """
    将 OCR 结果保存到本地文件
    
    参数:
        file_path: 原始文件路径
        result: OCR 识别结果字典
        
    返回:
        保存的文件路径
    """
    # backend_service 返回的格式中，成功标志在 success 字段
    if not result.get("success"):
        return ""
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    
    # 保存为文本文件 (.txt)
    txt_filename = f"{file_name_without_ext}_{timestamp}.txt"
    txt_path = os.path.join(STORAGE_DIR, txt_filename)
    
    # backend_service 返回的数据在 data.text 中（如果请求了 extract_text）
    # 或者在 data.ocr_result.text 中
    data = result.get("data", {})
    text_content = data.get("text", "")
    
    if not text_content and "ocr_result" in data:
        ocr_res = data["ocr_result"]
        if "text" in ocr_res:
            text_content = ocr_res["text"]
        elif "data" in ocr_res and isinstance(ocr_res["data"], list):
            # 如果是原始结果列表，拼接文本
            text_content = "\n".join([item.get("text", "") for item in ocr_res["data"]])

    if not text_content:
        return ""

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text_content)
    
    # 自动清理旧文件
    if prune_directory:
        prune_directory(STORAGE_DIR, MAX_STORAGE_FILES)
        
    return txt_path

def ocr_image(image_path: str) -> Dict[str, Any]:
    """
    通过 backend_service 对图片进行 OCR 识别，并自动保存结果到本地
    
    参数:
        image_path: 图片文件的绝对路径
        
    返回:
        包含识别结果的字典
    """
    if not os.path.exists(image_path):
        return {"success": False, "message": f"图片文件不存在: {image_path}"}
    
    url = f"{OCR_SERVER_URL}/api/ocr/file"
    
    try:
        print(f"  [OCR] 正在发送图片到服务器: {os.path.basename(image_path)}...")
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {'extract_text': 'true'}
            response = requests.post(url, files=files, data=data, timeout=30)
        
        print(f"  [OCR] 服务器响应状态: {response.status_code}")
            
        if response.status_code != 200:
            return {"success": False, "message": f"服务器返回错误: {response.status_code}"}
            
        result = response.json()
        if result.get("success"):
            # 保存到本地
            save_path = _save_result_locally(image_path, result)
            if "data" in result:
                result["data"]["saved_path"] = save_path
        return result
        
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "无法连接到 OCR backend_service，请确保服务已启动。"}
    except Exception as e:
        return {"success": False, "message": f"OCR 识别执行异常: {str(e)}"}

def _poll_progress(task_id: str, stop_event: threading.Event):
    """后台轮询进度并打印"""
    last_percentage = -1
    url = f"{OCR_SERVER_URL}/api/progress/{task_id}"
    
    while not stop_event.is_set():
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    progress = data.get("data", {})
                    percentage = progress.get("percentage", 0)
                    current = progress.get("current", 0)
                    total = progress.get("total", 0)
                    
                    if percentage > last_percentage:
                        print(f"  [OCR进度] 处理中: {percentage}% ({current}/{total})")
                        last_percentage = percentage
            
            if last_percentage >= 100:
                break
        except:
            pass
        time.sleep(1)

def ocr_document(doc_path: str, page_start: int = 1, page_end: Optional[int] = None) -> Dict[str, Any]:
    """
    通过 backend_service 对 PDF 等文档文件进行 OCR 识别，并自动保存结果到本地
    
    参数:
        doc_path: 文档文件的绝对路径
        page_start: 起始页码（从1开始）
        page_end: 结束页码，None 表示到最后一页
        
    返回:
        包含识别结果的字典
    """
    if not os.path.exists(doc_path):
        return {"success": False, "message": f"文档文件不存在: {doc_path}"}
    
    url = f"{OCR_SERVER_URL}/api/ocr/document"
    task_id = str(uuid.uuid4())
    stop_event = threading.Event()
    
    # 启动进度轮询线程
    progress_thread = threading.Thread(target=_poll_progress, args=(task_id, stop_event))
    progress_thread.daemon = True
    progress_thread.start()
    
    try:
        print(f"  [OCR] 正在发送文档到服务器: {os.path.basename(doc_path)} (页码: {page_start}-{page_end if page_end else '末尾'})...")
        with open(doc_path, 'rb') as f:
            files = {'file': f}
            payload = {
                'page_range_start': str(page_start),
                'extract_text': 'true',
                'task_id': task_id
            }
            if page_end is not None:
                payload['page_range_end'] = str(page_end)
                
            response = requests.post(url, files=files, data=payload, timeout=120)
        
        stop_event.set()
        progress_thread.join(timeout=1)
        
        print(f"  [OCR] 服务器响应状态: {response.status_code}")
        
        if response.status_code != 200:
            return {"success": False, "message": f"服务器返回错误: {response.status_code}"}
            
        result = response.json()
        if result.get("success"):
            # 保存到本地
            save_path = _save_result_locally(doc_path, result)
            if "data" in result:
                result["data"]["saved_path"] = save_path
        return result
        
    except requests.exceptions.ConnectionError:
        stop_event.set()
        return {"success": False, "message": "无法连接到 OCR backend_service，请确保服务已启动。"}
    except Exception as e:
        stop_event.set()
        return {"success": False, "message": f"文档 OCR 识别执行异常: {str(e)}"}
