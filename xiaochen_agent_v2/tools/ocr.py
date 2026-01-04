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
from typing import Dict, Any, Optional

# OCR 后端服务配置
OCR_SERVER_URL = "http://localhost:5000"
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "ocr_results")

# 导入清理工具
try:
    from ..utils.files import prune_directory
except (ImportError, ValueError):
    prune_directory = None

MAX_STORAGE_FILES = 50  # 默认最大保存条数

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
    # 后端服务返回的格式中，成功标志在 success 字段
    if not result.get("success"):
        return ""
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    
    # 保存为文本文件 (.txt)
    txt_filename = f"{file_name_without_ext}_{timestamp}.txt"
    txt_path = os.path.join(STORAGE_DIR, txt_filename)
    
    # 后端服务返回的数据在 data.text 中（如果请求了 extract_text）
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
    通过后端服务对图片进行 OCR 识别，并自动保存结果到本地
    
    参数:
        image_path: 图片文件的绝对路径
        
    返回:
        包含识别结果的字典
    """
    if not os.path.exists(image_path):
        return {"success": False, "message": f"图片文件不存在: {image_path}"}
    
    url = f"{OCR_SERVER_URL}/api/ocr/file"
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {'extract_text': 'true'}
            response = requests.post(url, files=files, data=data, timeout=30)
            
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
        return {"success": False, "message": "无法连接到 OCR 后端服务，请确保服务已启动。"}
    except Exception as e:
        return {"success": False, "message": f"OCR 识别执行异常: {str(e)}"}

def ocr_document(doc_path: str, page_start: int = 1, page_end: Optional[int] = None) -> Dict[str, Any]:
    """
    通过后端服务对 PDF 等文档文件进行 OCR 识别，并自动保存结果到本地
    
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
    
    try:
        with open(doc_path, 'rb') as f:
            files = {'file': f}
            payload = {
                'page_range_start': str(page_start),
                'extract_text': 'true'
            }
            if page_end is not None:
                payload['page_range_end'] = str(page_end)
                
            response = requests.post(url, files=files, data=payload, timeout=60)
            
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
        return {"success": False, "message": "无法连接到 OCR 后端服务，请确保服务已启动。"}
    except Exception as e:
        return {"success": False, "message": f"文档 OCR 识别执行异常: {str(e)}"}
