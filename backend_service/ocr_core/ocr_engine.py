# -*- coding: utf-8 -*-
"""
OCR核心引擎 - 最小化可复用模块
提供简洁的OCR识别接口，支持图片路径、字节流、base64等多种输入方式
"""

import os
import json
import subprocess
import sys
from base64 import b64encode, b64decode
from json import loads as json_loads, dumps as json_dumps
from sys import platform as sys_platform
from io import BytesIO
from urllib.parse import urlparse
from urllib.request import urlopen, Request

# 添加当前目录到Python路径以导入pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pymupdf as fitz  # PDF文档处理
    DOCUMENT_SUPPORT = True
except ImportError:
    DOCUMENT_SUPPORT = False


class OCREngine:
    """OCR识别引擎核心类"""
    
    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = [
        ".jpg", ".jpe", ".jpeg", ".jfif",
        ".png", ".webp", ".bmp", ".tif", ".tiff"
    ]
    
    # 支持的文档格式（需要PyMuPDF）
    SUPPORTED_DOC_FORMATS = [
        ".pdf", ".xps", ".epub", ".mobi", 
        ".fb2", ".cbz", ".oxps"
    ]
    
    # 所有支持的格式
    @property
    def SUPPORTED_FORMATS(self):
        """返回所有支持的文件格式"""
        formats = self.SUPPORTED_IMAGE_FORMATS.copy()
        if DOCUMENT_SUPPORT:
            formats.extend(self.SUPPORTED_DOC_FORMATS)
        return formats
    
    def __init__(self, config_path="config.json"):
        """
        初始化OCR引擎
        
        参数:
            config_path: 配置文件路径，默认为 config.json
        """
        self.config = self._load_config(config_path)
        self.process = None
        self.is_initialized = False
        
    def _load_config(self, config_path):
        """
        加载配置文件
        
        参数:
            config_path: 配置文件路径
            
        返回:
            配置字典
        """
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 返回默认配置
            return {
                "exe_path": "../UmiOCR-data/plugins/win7_x64_PaddleOCR-json/PaddleOCR-json.exe",
                "models_path": "../UmiOCR-data/plugins/win7_x64_PaddleOCR-json/models",
                "language": "models/config_chinese.txt",
                "cpu_threads": 4,
                "enable_mkldnn": True,
                "cls": False,
                "limit_side_len": 4320
            }
    
    def initialize(self):
        """
        初始化OCR引擎进程
        
        返回:
            成功返回 True，失败返回 False
        """
        if self.is_initialized:
            return True
            
        try:
            # 获取exe路径
            exe_path = os.path.abspath(self.config.get("exe_path", ""))
            if not os.path.exists(exe_path):
                print(f"[错误] OCR引擎不存在: {exe_path}")
                return False
            
            # 构建启动命令
            cwd = os.path.dirname(exe_path)
            cmds = [exe_path]
            
            # 添加启动参数
            models_path = self.config.get("models_path")
            if models_path:
                models_path = os.path.abspath(models_path)
                if os.path.exists(models_path):
                    cmds += ["--models_path", models_path]
            
            # 添加其他参数
            param_mapping = {
                "language": "config_path",
                "cpu_threads": "cpu_threads",
                "enable_mkldnn": "enable_mkldnn",
                "cls": "cls",
                "limit_side_len": "limit_side_len"
            }
            
            for config_key, arg_key in param_mapping.items():
                if config_key in self.config:
                    value = self.config[config_key]
                    if isinstance(value, bool):
                        cmds.append(f"--{arg_key}={value}")
                    else:
                        cmds += [f"--{arg_key}", str(value)]
            
            # 设置静默模式（Windows）
            startupinfo = None
            if "win32" in str(sys_platform).lower():
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags = (
                    subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
                )
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # 启动子进程
            self.process = subprocess.Popen(
                cmds,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo
            )
            
            # 等待初始化完成
            while True:
                if self.process.poll() is not None:
                    print("[错误] OCR引擎启动失败")
                    return False
                    
                line = self.process.stdout.readline().decode('utf-8', errors='ignore')
                if "OCR init completed." in line:
                    self.is_initialized = True
                    print("[成功] OCR引擎初始化完成")
                    return True
                    
        except Exception as e:
            print(f"[错误] 初始化OCR引擎异常: {e}")
            return False
    
    def recognize_image(self, image_path):
        """
        识别图片文件
        
        参数:
            image_path: 图片文件路径
            
        返回:
            识别结果字典: {
                "code": 状态码 (100=成功, 101=无文字, 其他=失败),
                "data": 识别结果列表或错误信息,
                "score": 平均置信度
            }
        """
        if not self.is_initialized:
            if not self.initialize():
                return {"code": 901, "data": "OCR引擎未初始化", "score": 0}
        
        # 检查文件格式
        ext = os.path.splitext(image_path)[-1].lower()
        
        # 如果是文档格式，使用文档识别
        if DOCUMENT_SUPPORT and ext in self.SUPPORTED_DOC_FORMATS:
            return self.recognize_document(image_path)
        
        # 检查是否支持的图片格式
        if ext not in self.SUPPORTED_IMAGE_FORMATS:
            return {"code": 902, "data": f"不支持的文件格式: {ext}", "score": 0}
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return {"code": 903, "data": f"图片文件不存在: {image_path}", "score": 0}
        
        # 调用识别
        return self._run_dict({"image_path": image_path})
    
    def recognize_bytes(self, image_bytes):
        """
        识别图片字节流
        
        参数:
            image_bytes: 图片字节流
            
        返回:
            识别结果字典
        """
        if not self.is_initialized:
            if not self.initialize():
                return {"code": 901, "data": "OCR引擎未初始化", "score": 0}
        
        # 转换为base64
        image_base64 = b64encode(image_bytes).decode('utf-8')
        return self._run_dict({"image_base64": image_base64})
    
    def recognize_base64(self, image_base64):
        """
        识别base64编码的图片
        
        参数:
            image_base64: 图片的base64字符串
            
        返回:
            识别结果字典
        """
        if not self.is_initialized:
            if not self.initialize():
                return {"code": 901, "data": "OCR引擎未初始化", "score": 0}
        
        return self._run_dict({"image_base64": image_base64})
    
    def _run_dict(self, cmd_dict):
        """
        向OCR引擎发送指令字典
        
        参数:
            cmd_dict: 指令字典
            
        返回:
            识别结果字典
        """
        if not self.process or self.process.poll() is not None:
            return {"code": 904, "data": "OCR引擎进程已退出", "score": 0}
        
        try:
            # 发送指令
            cmd_str = json_dumps(cmd_dict, ensure_ascii=True, indent=None) + "\n"
            self.process.stdin.write(cmd_str.encode('utf-8'))
            self.process.stdin.flush()
            
            # 读取结果
            result_str = self.process.stdout.readline().decode('utf-8', errors='ignore')
            result = json_loads(result_str)
            
            # 计算平均置信度
            if result.get("code") == 100 and isinstance(result.get("data"), list):
                total_score = sum(item.get("score", 0) for item in result["data"])
                count = len(result["data"])
                result["score"] = total_score / count if count > 0 else 0
            else:
                result["score"] = 0
            
            return result
            
        except Exception as e:
            return {"code": 905, "data": f"OCR识别异常: {e}", "score": 0}
    
    def recognize_document(self, doc_path, page_range=None, dpi=200, password=""):
        """
        识别PDF等文档文件（支持多页）
        
        参数:
            doc_path: 文档文件路径
            page_range: 页面范围，None=全部页面，[start, end]=指定范围（从1开始）
            dpi: 渲染DPI，影响图片质量和识别准确度，默认200
            password: 文档密码（如果需要）
            
        返回:
            识别结果字典: {
                "code": 状态码,
                "data": 所有页面的识别结果列表（合并）,
                "score": 平均置信度,
                "pages": 每页的详细结果列表
            }
        """
        if not DOCUMENT_SUPPORT:
            return {"code": 910, "data": "文档支持未启用（缺少PyMuPDF库）", "score": 0}
        
        if not self.is_initialized:
            if not self.initialize():
                return {"code": 901, "data": "OCR引擎未初始化", "score": 0}
        
        # 检查文件是否存在
        if not os.path.exists(doc_path):
            return {"code": 903, "data": f"文档文件不存在: {doc_path}", "score": 0}
        
        try:
            # 打开文档
            doc = fitz.open(doc_path)
            
            # 检查密码
            if doc.is_encrypted and not doc.authenticate(password):
                doc.close()
                return {"code": 911, "data": "文档已加密，密码错误或未提供", "score": 0}
            
            # 确定页面范围
            page_count = doc.page_count
            if page_range is None:
                pages_to_process = range(page_count)
            else:
                start, end = page_range
                start = max(1, min(start, page_count)) - 1  # 转为0-based
                end = max(1, min(end, page_count))
                pages_to_process = range(start, end)
            
            # 逐页识别
            all_results = []
            all_text_blocks = []
            total_score = 0
            success_count = 0
            
            for page_num in pages_to_process:
                page = doc[page_num]
                
                # 将页面渲染为图片
                zoom = dpi / 72  # 72是PDF的默认DPI
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为字节流
                img_bytes = pix.tobytes("png")
                
                # OCR识别
                result = self.recognize_bytes(img_bytes)
                
                if result["code"] == 100:
                    all_text_blocks.extend(result["data"])
                    total_score += result["score"]
                    success_count += 1
                
                # 保存每页结果
                page_result = {
                    "page": page_num + 1,  # 转回1-based
                    "result": result
                }
                all_results.append(page_result)
            
            doc.close()
            
            # 汇总结果
            avg_score = total_score / success_count if success_count > 0 else 0
            
            if all_text_blocks:
                return {
                    "code": 100,
                    "data": all_text_blocks,
                    "score": avg_score,
                    "pages": all_results,
                    "page_count": page_count
                }
            else:
                return {
                    "code": 101,
                    "data": [],
                    "score": 0,
                    "pages": all_results,
                    "page_count": page_count
                }
                
        except Exception as e:
            return {"code": 912, "data": f"文档识别异常: {e}", "score": 0}
    
    def recognize_url(self, url, timeout=30):
        """
        识别网络图片URL
        
        参数:
            url: 图片URL地址
            timeout: 超时时间（秒）
            
        返回:
            识别结果字典
        """
        if not self.is_initialized:
            if not self.initialize():
                return {"code": 901, "data": "OCR引擎未初始化", "score": 0}
        
        try:
            # 下载图片
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as response:
                image_bytes = response.read()
            
            # 识别下载的图片
            result = self.recognize_bytes(image_bytes)
            result["url"] = url
            return result
            
        except Exception as e:
            return {"code": 913, "data": f"URL下载或识别失败: {e}", "score": 0}
    
    def recognize_directory(self, dir_path, recursive=False):
        """
        识别目录中的所有图片/文档
        
        参数:
            dir_path: 目录路径
            recursive: 是否递归子目录
            
        返回:
            识别结果列表
        """
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            return [{"code": 903, "data": f"目录不存在: {dir_path}", "score": 0}]
        
        # 收集所有支持的文件
        file_paths = []
        supported_formats = self.SUPPORTED_FORMATS
        
        if recursive:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    ext = os.path.splitext(file)[-1].lower()
                    if ext in supported_formats:
                        file_paths.append(os.path.join(root, file))
        else:
            for file in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[-1].lower()
                    if ext in supported_formats:
                        file_paths.append(file_path)
        
        # 批量识别
        return self.batch_recognize(file_paths)
    
    def batch_recognize(self, image_paths):
        """
        批量识别图片/文档
        
        参数:
            image_paths: 图片/文档路径列表（可以是字符串列表或单个字符串）
            
        返回:
            识别结果列表
        """
        # 如果传入单个路径，转换为列表
        if isinstance(image_paths, str):
            image_paths = [image_paths]
        
        results = []
        for path in image_paths:
            result = self.recognize_image(path)
            result["path"] = path
            results.append(result)
        return results
    
    def extract_text(self, result):
        """
        从识别结果中提取纯文本
        
        参数:
            result: recognize_* 方法返回的结果字典
            
        返回:
            纯文本字符串，每行文本用换行符分隔
        """
        if result.get("code") != 100:
            return ""
        
        data = result.get("data", [])
        if not isinstance(data, list):
            return ""
        
        return "\n".join(item.get("text", "") for item in data)
    
    def close(self):
        """
        关闭OCR引擎，释放资源
        """
        if self.process:
            try:
                self.process.kill()
                self.process = None
                self.is_initialized = False
                print("[成功] OCR引擎已关闭")
            except Exception as e:
                print(f"[错误] 关闭OCR引擎异常: {e}")
    
    def __del__(self):
        """析构函数，确保资源释放"""
        self.close()
    
    def __enter__(self):
        """支持 with 语句"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        self.close()

