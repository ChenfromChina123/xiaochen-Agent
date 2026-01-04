# -*- coding: utf-8 -*-
"""
OCR 工具封装模块
提供简单的接口供 Agent 调用 OCR 功能
"""

import os
import sys
import json
import datetime
from typing import Dict, Any, Optional

# 动态添加路径以便导入 ocr_core
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OCR_CORE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "ocr_core"))
STORAGE_DIR = os.path.join(PROJECT_ROOT, "storage", "ocr_results")

# 导入清理工具
try:
    from ..utils.files import prune_directory
except (ImportError, ValueError):
    prune_directory = None

MAX_STORAGE_FILES = 50  # 默认最大保存条数

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR, exist_ok=True)

if OCR_CORE_DIR not in sys.path:
    sys.path.insert(0, OCR_CORE_DIR)

try:
    from .ocr_core.ocr_engine import OCREngine
except (ImportError, ValueError):
    try:
        from ocr_engine import OCREngine
    except ImportError:
        OCREngine = None

def _save_result_locally(file_path: str, result: Dict[str, Any]) -> str:
    """
    将 OCR 结果保存到本地文件
    
    参数:
        file_path: 原始文件路径
        result: OCR 识别结果字典
        
    返回:
        保存的文件路径
    """
    if not result or result.get("code") != 100:
        return ""
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    
    # 保存为文本文件 (.txt)
    txt_filename = f"{file_name_without_ext}_{timestamp}.txt"
    txt_path = os.path.join(STORAGE_DIR, txt_filename)
    
    text_content = result.get("text", "")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text_content)
    
    # 自动清理旧文件
    if prune_directory:
        prune_directory(STORAGE_DIR, MAX_STORAGE_FILES)
        
    return txt_path

def ocr_image(image_path: str) -> Dict[str, Any]:
    """
    对图片进行 OCR 识别，并自动保存结果到本地
    
    参数:
        image_path: 图片文件的绝对路径
        
    返回:
        包含识别结果的字典
    """
    if OCREngine is None:
        return {"code": 500, "data": "OCR 核心模块导入失败，请检查路径。"}
    
    if not os.path.exists(image_path):
        return {"code": 404, "data": f"图片文件不存在: {image_path}"}
    
    # 配置文件路径
    config_path = os.path.join(OCR_CORE_DIR, "config.json")
    
    try:
        # 使用 with 语句自动管理引擎生命周期
        with OCREngine(config_path) as engine:
            result = engine.recognize_image(image_path)
            if result.get("code") == 100:
                # 提取纯文本方便 Agent 阅读
                result["text"] = engine.extract_text(result)
                # 保存到本地
                save_path = _save_result_locally(image_path, result)
                result["saved_path"] = save_path
            return result
    except Exception as e:
        return {"code": 500, "data": f"OCR 识别执行异常: {str(e)}"}

def ocr_document(doc_path: str, page_start: int = 1, page_end: Optional[int] = None) -> Dict[str, Any]:
    """
    对 PDF 等文档文件进行 OCR 识别，并自动保存结果到本地
    
    参数:
        doc_path: 文档文件的绝对路径
        page_start: 起始页码（从1开始）
        page_end: 结束页码，None 表示到最后一页
        
    返回:
        包含识别结果的字典
    """
    if OCREngine is None:
        return {"code": 500, "data": "OCR 核心模块导入失败，请检查路径。"}
    
    if not os.path.exists(doc_path):
        return {"code": 404, "data": f"文档文件不存在: {doc_path}"}
    
    config_path = os.path.join(OCR_CORE_DIR, "config.json")
    
    try:
        with OCREngine(config_path) as engine:
            if hasattr(engine, 'recognize_document'):
                page_range = None
                if page_end is not None:
                    page_range = [page_start, page_end]
                elif page_start > 1:
                    page_range = [page_start, 9999] 
                
                result = engine.recognize_document(doc_path, page_range=page_range)
                if result.get("code") == 100:
                    result["text"] = engine.extract_text(result)
                    # 保存到本地
                    save_path = _save_result_locally(doc_path, result)
                    result["saved_path"] = save_path
                return result
            else:
                return {"code": 501, "data": "当前 OCR 引擎不支持文档识别"}
    except Exception as e:
        return {"code": 500, "data": f"文档 OCR 识别执行异常: {str(e)}"}
