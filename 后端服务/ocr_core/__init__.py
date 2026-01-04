# -*- coding: utf-8 -*-
"""
OCR核心模块 - 最小化可复用OCR识别组件

这是一个从 Umi-OCR 项目中提取的核心OCR识别模块，提供了简洁的API接口。

主要功能:
- 图片文字识别（支持路径、字节流、base64）
- 批量识别
- 纯文本提取
- JSON配置管理

支持的图片格式:
.jpg, .jpeg, .jpe, .jfif, .png, .webp, .bmp, .tif, .tiff

使用示例:
    from ocr_core import OCREngine
    
    # 方式1: 基础使用
    engine = OCREngine("config.json")
    engine.initialize()
    result = engine.recognize_image("test.jpg")
    text = engine.extract_text(result)
    engine.close()
    
    # 方式2: 使用 with 语句（推荐）
    with OCREngine("config.json") as engine:
        result = engine.recognize_image("test.jpg")
        text = engine.extract_text(result)

版本: 1.0.0
"""

from .ocr_engine import OCREngine

__version__ = "1.0.0"
__all__ = ["OCREngine"]

