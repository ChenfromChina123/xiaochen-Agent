# -*- coding: utf-8 -*-
"""
图片处理工具模块
提供从剪贴板保存图片、图片压缩等功能
"""

import os
import datetime
from PIL import Image, ImageGrab

def save_clipboard_image(save_dir="attachments"):
    """
    从剪贴板获取图片并保存到指定目录
    
    参数:
        save_dir: 保存目录，默认为 attachments
        
    返回:
        成功返回保存的绝对路径，失败返回 None
    """
    try:
        # 获取剪贴板中的图片
        img = ImageGrab.grabclipboard()
        
        if isinstance(img, Image.Image):
            # 确保目录存在
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 生成文件名: img_YYYYMMDD_HHMMSS.png
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"img_{timestamp}.png"
            save_path = os.path.abspath(os.path.join(save_dir, filename))
            
            # 保存图片
            img.save(save_path, "PNG")
            return save_path
        
        elif isinstance(img, list):
            # 如果剪贴板里是文件列表（比如在文件管理器里复制了图片文件）
            for item in img:
                if isinstance(item, str) and item.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    return os.path.abspath(item)
                    
        return None
    except Exception as e:
        print(f"[DEBUG] 从剪贴板获取图片失败: {e}")
        return None

def is_image_path(text):
    """判断文本是否为合法的图片路径"""
    if not text or not isinstance(text, str):
        return False
    
    # 移除引号
    path = text.strip().strip('"').strip("'")
    
    if os.path.exists(path) and path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf')):
        return True
    return False
