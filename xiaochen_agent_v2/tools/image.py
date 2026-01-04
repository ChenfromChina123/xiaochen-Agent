# -*- coding: utf-8 -*-
"""
图片处理工具模块
提供从剪贴板保存图片、图片压缩等功能
"""

import os
import datetime
import subprocess
from PIL import Image, ImageGrab

def get_clipboard_text():
    """
    使用 PowerShell 获取剪贴板中的文本内容内容
    
    返回:
        字符串内容，如果不是文本或获取失败则返回 None
    """
    try:
        # 使用 powershell 获取剪贴板文本
        # -Raw 参数保留原始换行符
        process = subprocess.Popen(
            ['powershell', '-NoProfile', '-Command', 'Get-Clipboard -Raw'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        stdout, stderr = process.communicate(timeout=5)
        
        if process.returncode == 0 and stdout.strip():
            return stdout.strip()
        return None
    except Exception as e:
        print(f"[DEBUG] 获取剪贴板文本失败: {e}")
        return None

def save_clipboard_file(save_dir="attachments"):
    """
    从剪贴板获取文件或图片并保存
    支持：
    1. 直接从文件管理器复制的文件 (PDF, Docx, 图片等)
    2. 截图/位图数据
    
    返回:
        成功返回保存的绝对路径，失败返回 None
    """
    try:
        # 1. 优先检查是否是文件列表 (HDROP)
        img_or_files = ImageGrab.grabclipboard()
        
        if isinstance(img_or_files, list):
            # 如果是文件列表，返回第一个支持的文件路径
            supported_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf', '.docx', '.txt', '.md', '.xlsx', '.csv')
            for item in img_or_files:
                if isinstance(item, str) and item.lower().endswith(supported_exts):
                    # 如果文件不在 save_dir 中，则复制过去以便统一管理
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir)
                    
                    filename = os.path.basename(item)
                    dest_path = os.path.join(save_dir, filename)
                    
                    # 如果目标位置已有同名文件且不是同一个文件，则加时间戳
                    if os.path.exists(dest_path) and os.path.abspath(dest_path) != os.path.abspath(item):
                        timestamp = datetime.datetime.now().strftime("%H%M%S")
                        name, ext = os.path.splitext(filename)
                        filename = f"{name}_{timestamp}{ext}"
                        dest_path = os.path.join(save_dir, filename)
                    
                    # 只有在路径不同时才复制
                    if os.path.abspath(dest_path) != os.path.abspath(item):
                        import shutil
                        shutil.copy2(item, dest_path)
                        return os.path.abspath(dest_path)
                    
                    return os.path.abspath(item)
        
        # 2. 如果是位图数据 (截图)
        if isinstance(img_or_files, Image.Image):
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"img_{timestamp}.png"
            save_path = os.path.abspath(os.path.join(save_dir, filename))
            img_or_files.save(save_path, "PNG")
            return save_path

        # 3. 备选方案：使用 PowerShell 检查位图 (Pillow 有时抓不到)
        try:
            temp_img = os.path.join(save_dir, f"temp_clip_{datetime.datetime.now().strftime('%H%M%S')}.png")
            save_cmd = [
                'powershell', '-NoProfile', '-Command', 
                f'$img = Get-Clipboard -Format Image; if ($img) {{ $img.Save("{temp_img}", [System.Drawing.Imaging.ImageFormat]::Png); echo "SUCCESS" }}'
            ]
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            res = subprocess.run(save_cmd, capture_output=True, text=True)
            if "SUCCESS" in res.stdout and os.path.exists(temp_img):
                return os.path.abspath(temp_img)
        except:
            pass
            
        return None
    except Exception as e:
        print(f"[DEBUG] 从剪贴板获取内容失败: {e}")
        return None

def save_clipboard_image(save_dir="attachments"):
    """
    从剪贴板获取图片并保存到指定目录
    
    参数:
        save_dir: 保存目录，默认为 attachments
        
    返回:
        成功返回保存的绝对路径，失败返回 None
    """
    try:
        # 记录调试信息
        # print("[DEBUG] 尝试从剪贴板抓取内容...")
        
        # 获取剪贴板中的内容
        img = ImageGrab.grabclipboard()
        
        # 调试信息: 打印抓取到的对象类型
        # print(f"[DEBUG] 抓取到的对象类型: {type(img)}")
        
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
            # print(f"[DEBUG] 检测到文件列表: {img}")
            for item in img:
                if isinstance(item, str) and item.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    return os.path.abspath(item)
                    
        # 特殊处理：如果上述失败，尝试使用 PowerShell 检查是否有位图
        # print("[DEBUG] Pillow 抓取失败，尝试备选方案...")
        try:
            import subprocess
            # 检查剪贴板是否包含位图格式
            check_cmd = ['powershell', '-NoProfile', '-Command', 'Get-Clipboard -Format Image']
            # 注意：Get-Clipboard -Format Image 返回的是 System.Drawing.Bitmap 对象
            # 我们通过判断命令是否执行成功且有输出来确定
            
            # 另一个更可靠的方法是使用 PowerShell 将图片保存到临时文件
            temp_img = os.path.join(save_dir, f"temp_clip_{datetime.datetime.now().strftime('%H%M%S')}.png")
            save_cmd = [
                'powershell', '-NoProfile', '-Command', 
                f'$img = Get-Clipboard -Format Image; if ($img) {{ $img.Save("{temp_img}", [System.Drawing.Imaging.ImageFormat]::Png); echo "SUCCESS" }}'
            ]
            
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            res = subprocess.run(save_cmd, capture_output=True, text=True)
            if "SUCCESS" in res.stdout and os.path.exists(temp_img):
                # print(f"[DEBUG] PowerShell 方案成功保存: {temp_img}")
                return os.path.abspath(temp_img)
        except Exception as e:
            # print(f"[DEBUG] PowerShell 备选方案失败: {e}")
            pass
                    
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
