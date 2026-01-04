# -*- coding: utf-8 -*-
"""
OCR 工具封装模块
提供简单的接口供 Agent 调用 OCR 功能
"""

import os
import sys
import json
from typing import Dict, Any, Optional

# 动态添加路径以便导入 ocr_core
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_CORE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "mcp", "ocr_core"))

if OCR_CORE_DIR not in sys.path:
    sys.path.insert(0, OCR_CORE_DIR)

try:
    from ocr_engine import OCREngine
except ImportError:
    OCREngine = None

def ocr_image(image_path: str) -> Dict[str, Any]:
    """
    对图片进行 OCR 识别
    
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
        # 注意：OCREngine 内部会使用相对路径加载配置，我们需要确保路径正确
        with OCREngine(config_path) as engine:
            result = engine.recognize_image(image_path)
            if result.get("code") == 100:
                # 提取纯文本方便 Agent 阅读
                result["text"] = engine.extract_text(result)
            return result
    except Exception as e:
        return {"code": 500, "data": f"OCR 识别执行异常: {str(e)}"}

def ocr_document(doc_path: str, page_start: int = 1, page_end: Optional[int] = None) -> Dict[str, Any]:
    """
    对 PDF 等文档文件进行 OCR 识别
    
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
                    # 如果只有起始页，我们需要先获取总页数，但这里简单处理，让引擎处理
                    # 实际上 recognize_document 支持 page_range=[start, end]
                    # 如果没有结束页，我们可以传一个很大的数
                    page_range = [page_start, 9999] 
                
                result = engine.recognize_document(doc_path, page_range=page_range)
                if result.get("code") == 100:
                    result["text"] = engine.extract_text(result)
                return result
            else:
                return {"code": 501, "data": "当前 OCR 引擎不支持文档识别"}
    except Exception as e:
        return {"code": 500, "data": f"文档 OCR 识别执行异常: {str(e)}"}
