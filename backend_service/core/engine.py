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
import io
from urllib.parse import urlparse
from urllib.request import urlopen, Request

# 添加当前目录到Python路径以导入pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pymupdf as fitz  # PDF文档处理
    DOCUMENT_SUPPORT = True
except ImportError:
    DOCUMENT_SUPPORT = False

try:
    from paddleocr import PaddleOCR
    import numpy as np
    from PIL import Image
    import gc
    PADDLE_OCR_SUPPORT = True
except ImportError:
    PADDLE_OCR_SUPPORT = False


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
    
    @classmethod
    def get_supported_formats(cls):
        """返回所有支持的文件格式"""
        formats = cls.SUPPORTED_IMAGE_FORMATS.copy()
        if DOCUMENT_SUPPORT:
            formats.extend(cls.SUPPORTED_DOC_FORMATS)
        return formats
    
    def __init__(self, config_path="config.json"):
        """
        初始化OCR引擎
        
        参数:
            config_path: 配置文件路径，默认为 config.json
        """
        self.config_path = os.path.abspath(config_path) if config_path else None
        self.config_dir = os.path.dirname(self.config_path) if self.config_path else os.getcwd()
        self.config = self._load_config(self.config_path)
        self.process = None
        self.ocr_instance = None # 用于存储 PaddleOCR 实例
        self.is_initialized = False
        self.use_python_lib = False # 是否使用 Python 库版本
        
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
    
    def _get_absolute_path(self, path):
        """将配置中的路径转换为绝对路径"""
        if not path:
            return ""
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(self.config_dir, path))

    def initialize(self):
        """
        初始化OCR引擎
        
        返回:
            成功返回 True，失败返回 False
        """
        if self.is_initialized:
            return True
            
        # 自动检测是否需要使用 Python 库版本 (Linux 或 配置强制使用)
        is_linux = "linux" in str(sys_platform).lower()
        force_python = self.config.get("use_python_lib", False)
        
        if (is_linux or force_python) and PADDLE_OCR_SUPPORT:
            try:
                print(f"[信息] 正在初始化 Python 版 PaddleOCR (平台: {sys_platform})...")
                # 初始化 PaddleOCR 实例
                # 参数映射
                lang = "ch"
                if "config_chinese.txt" in self.config.get("language", ""):
                    lang = "ch"
                elif "config_en.txt" in self.config.get("language", ""):
                    lang = "en"
                
                # 提取更多配置参数
                use_angle_cls = self.config.get("cls", self.config.get("use_angle_cls", False))
                cpu_threads = self.config.get("cpu_threads", 1)
                enable_mkldnn = self.config.get("enable_mkldnn", False)
                
                # 指定模型目录 (如果是 Linux 且配置了 models_path)
                det_model_dir = None
                rec_model_dir = None
                cls_model_dir = None
                
                models_path = self.config.get("models_path")
                if models_path and is_linux:
                    # 尝试将相对路径转为绝对路径
                    models_path = self._get_absolute_path(models_path)
                    print(f"[信息] 尝试加载本地模型: {models_path}")
                    
                    # 检查模型子目录是否存在
                    if os.path.exists(os.path.join(models_path, "ocr-v4/ch/ch_PP-OCRv4_det_infer")):
                         det_model_dir = os.path.join(models_path, "ocr-v4/ch/ch_PP-OCRv4_det_infer")
                    
                    if os.path.exists(os.path.join(models_path, "ocr-v4/ch/ch_PP-OCRv4_rec_infer")):
                         rec_model_dir = os.path.join(models_path, "ocr-v4/ch/ch_PP-OCRv4_rec_infer")
                         
                    if os.path.exists(os.path.join(models_path, "ocr-v4/ch/ch_ppocr_mobile_v2.0_cls_infer")):
                         cls_model_dir = os.path.join(models_path, "ocr-v4/ch/ch_ppocr_mobile_v2.0_cls_infer")

                # 显式传递内存优化参数
                try:
                    # 构建初始化参数字典
                    ocr_params = {
                        "use_angle_cls": use_angle_cls,
                        "lang": lang,
                        "cpu_threads": cpu_threads,
                        "enable_mkldnn": enable_mkldnn,
                        "use_gpu": False,  # 强制禁用 GPU
                        "show_log": False  # 减少日志输出
                    }
                    
                    # 如果找到了本地模型路径，则添加进去
                    if det_model_dir: ocr_params["det_model_dir"] = det_model_dir
                    if rec_model_dir: ocr_params["rec_model_dir"] = rec_model_dir
                    if cls_model_dir: ocr_params["cls_model_dir"] = cls_model_dir
                    
                    print(f"[信息] PaddleOCR 初始化参数: {ocr_params}")
                    self.ocr_instance = PaddleOCR(**ocr_params)

                except TypeError:
                    # 如果不支持某些参数，尝试最简初始化
                    print("[警告] PaddleOCR 不支持部分优化参数，尝试基础初始化...")
                    self.ocr_instance = PaddleOCR(
                        use_angle_cls=use_angle_cls,
                        lang=lang
                    )
                
                self.use_python_lib = True
                self.is_initialized = True
                print("[成功] Python 版 PaddleOCR 初始化完成")
                return True
            except Exception as e:
                print(f"[错误] 初始化 Python 版 PaddleOCR 失败: {e}")
                if is_linux: # Linux 下只能用 Python 版，失败直接返回
                    return False
                # Windows 下如果 Python 版失败，尝试回退到 exe 版
                print("[信息] 尝试回退到 EXE 版...")

        try:
            # 获取exe路径
            exe_path = self._get_absolute_path(self.config.get("exe_path", ""))
            if not os.path.exists(exe_path):
                print(f"[错误] OCR引擎不存在: {exe_path}")
                return False
            
            # 构建启动命令
            cwd = os.path.dirname(exe_path)
            cmds = [exe_path]
            
            # 添加启动参数
            models_path = self.config.get("models_path")
            if models_path:
                models_path = self._get_absolute_path(models_path)
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
    
    def recognize_bytes(self, image_bytes, extract_text=False):
        """
        识别内存中的图片字节流
        
        参数:
            image_bytes: 图片字节数据
            extract_text: 是否只提取文本（针对Python库版本优化）
            
        返回:
            识别结果字典
        """
        if not self.is_initialized:
            if not self.initialize():
                return {"code": 901, "data": "OCR引擎未初始化", "score": 0}
        
        # 将字节流转为base64发送给进程，或者直接传递给 Python 库
        img_base64 = b64encode(image_bytes).decode('utf-8')
        cmd_dict = {"image_base64": img_base64}
        
        # 如果是 Python 库版本，可以传递 extract_text 参数进行内存优化
        if self.use_python_lib:
            cmd_dict["extract_text"] = extract_text
            
        return self._run_dict(cmd_dict)
    
    def recognize_base64(self, image_base64, extract_text=False):
        """
        识别base64编码的图片
        
        参数:
            image_base64: 图片的base64字符串
            extract_text: 是否只提取文本（针对Python库版本优化）
            
        返回:
            识别结果字典
        """
        if not self.is_initialized:
            if not self.initialize():
                return {"code": 901, "data": "OCR引擎未初始化", "score": 0}
        
        cmd_dict = {"image_base64": image_base64}
        
        # 如果是 Python 库版本，可以传递 extract_text 参数进行内存优化
        if self.use_python_lib:
            cmd_dict["extract_text"] = extract_text
            
        return self._run_dict(cmd_dict)
    
    def _run_dict(self, cmd_dict):
        """
        向OCR引擎发送指令字典
        
        参数:
            cmd_dict: 指令字典
            
        返回:
            识别结果字典
        """
        if self.use_python_lib:
            return self._run_python_ocr(cmd_dict)

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

    def _run_python_ocr(self, cmd_dict):
        """
        使用 Python 库版本进行识别
        """
        if not self.ocr_instance:
            return {"code": 901, "data": "Python OCR 实例未初始化", "score": 0}

        try:
            # 在执行识别前主动触发垃圾回收
            gc.collect()
            
            # 是否只提取文本（内存优化模式）
            extract_text = cmd_dict.get("extract_text", False)

            # 获取图像输入
            img_input = None
            if "image_path" in cmd_dict:
                img_path = cmd_dict["image_path"]
                print(f"[引擎] 正在识别文件: {img_path}")
                img_input = img_path
            elif "image_base64" in cmd_dict:
                print(f"[引擎] 正在识别 Base64 图像...")
                img_data = b64decode(cmd_dict["image_base64"])
                img_input = np.array(Image.open(io.BytesIO(img_data)))
            
            if img_input is None:
                return {"code": 906, "data": "未提供有效的图像输入", "score": 0}

            # 执行识别
            print(f"[引擎] 开始 OCR 推理...")
            try:
                use_cls = cmd_dict.get("cls", self.config.get("cls", False))
                result = self.ocr_instance.ocr(img_input, cls=use_cls)
            except TypeError as e:
                if "unexpected keyword argument 'cls'" in str(e):
                    result = self.ocr_instance.ocr(img_input)
                else:
                    raise e
            
            print(f"[引擎] 推理完成，解析结果...")
            
            # 转换格式为 PaddleOCR-json 格式
            formatted_data = []
            total_score = 0
            
            if result and isinstance(result, list) and len(result) > 0 and result[0] is not None:
                for line in result[0]:
                    try:
                        if not isinstance(line, list) or len(line) < 2:
                            continue
                            
                        box = line[0]
                        res = line[1]
                        
                        if isinstance(res, tuple) or isinstance(res, list):
                            if len(res) >= 2:
                                text, score = res[0], res[1]
                            else:
                                text, score = res[0], 0.0
                        else:
                            text, score = str(res), 0.0
                        
                        # 如果是 extract_text 模式，我们只保留文本和置信度，不保留坐标信息以节省内存
                        if extract_text:
                            formatted_data.append({
                                "text": text,
                                "score": score
                            })
                        else:
                            formatted_data.append({
                                "text": text,
                                "box": box,
                                "score": score
                            })
                        total_score += score
                    except Exception as e:
                        print(f"[警告] 解析 OCR 行数据失败: {e}, 数据内容: {line}")
                        continue
                
                count = len(formatted_data)
                avg_score = total_score / count if count > 0 else 0
                
                # 清理
                del img_input
                if 'img' in locals():
                    del img
                gc.collect()

                return {
                    "code": 100,
                    "data": formatted_data,
                    "score": avg_score
                }
            else:
                return {
                    "code": 101,
                    "data": [],
                    "score": 0
                }

        except Exception as e:
            return {"code": 905, "data": f"Python OCR 识别异常: {e}", "score": 0}
    
    def recognize_document(self, doc_path, page_range=None, dpi=200, password="", progress_callback=None, cancel_check=None, extract_text=False):
        """
        识别PDF等文档文件（支持多页）
        
        参数:
            doc_path: 文档文件路径
            page_range: 页面范围，None=全部页面，[start, end]=指定范围（从1开始）
            dpi: 渲染DPI，影响图片质量和识别准确度，默认200
            password: 文档密码（如果需要）
            progress_callback: 进度回调函数，接收参数 (current_page, total_pages, progress_percentage)
            cancel_check: 任务终止检查函数，返回 True 表示需要终止
            extract_text: 是否只提取文本（如果为True，将减少内存占用，不返回每页的详细坐标信息）
            
        返回:
            识别结果字典: {
                "code": 状态码,
                "data": 所有页面的识别结果列表（合并）,
                "score": 平均置信度,
                "pages": 每页的详细结果列表 (如果 extract_text 为 True，则此项为空)
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
                pages_to_process = list(range(page_count))
            else:
                start, end = page_range
                start = max(1, min(start, page_count)) - 1  # 转为0-based
                end = max(1, min(end, page_count))
                pages_to_process = list(range(start, end))
            
            total_to_process = len(pages_to_process)
            
            # 进度跟踪
            last_progress = -1
            
            # 逐页识别
            all_results = []
            all_text_blocks = []
            total_score = 0
            success_count = 0
            
            # 初始进度
            if progress_callback:
                progress_callback(0, total_to_process, 0)

            for i, page_num in enumerate(pages_to_process):
                # 检查是否需要终止任务
                if cancel_check and cancel_check():
                    print(f"[引擎] 识别任务已收到终止指令，正在停止...")
                    return {
                        "code": 102,
                        "data": "任务已终止",
                        "score": 0,
                        "pages": all_results
                    }
                
                page = doc[page_num]
                
                # 将页面渲染为图片
                zoom = dpi / 72  # 72是PDF的默认DPI
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为字节流
                img_bytes = pix.tobytes("png")
                
                # 释放 Pixmap 内存
                del pix
                
                # 识别页面
                result = self.recognize_bytes(img_bytes)
                
                # 释放字节流内存
                del img_bytes
                import gc
                gc.collect()
                
                if result["code"] == 100:
                    all_text_blocks.extend(result["data"])
                    total_score += result["score"]
                    success_count += 1
                
                # 如果不需要提取纯文本，则保存每页详细结果
                if not extract_text:
                    page_result = {
                        "page": page_num + 1,  # 转回1-based
                        "result": result
                    }
                    all_results.append(page_result)

                # 处理完当前页后计算进度
                processed_count = i + 1
                current_progress = int((processed_count / total_to_process) * 100)
                
                # 每完成10%反馈一次，或者完成了最后一页
                if current_progress // 10 > last_progress // 10 or processed_count == total_to_process:
                    if progress_callback:
                        progress_callback(processed_count, total_to_process, current_progress)
                    else:
                        print(f"[进度] 文档识别中: {current_progress}% ({processed_count}/{total_to_process}页)")
                    last_progress = current_progress

            doc.close()
            
            # 汇总结果
            avg_score = total_score / success_count if success_count > 0 else 0
            
            # 报告 100% 进度
            if progress_callback:
                progress_callback(total_to_process, total_to_process, 100)
            else:
                print(f"[进度] 文档识别完成: 100% ({total_to_process}/{total_to_process}页)")
            
            return {
                "code": 100 if all_text_blocks else 101,
                "data": all_text_blocks,
                "score": avg_score,
                "pages": all_results,
                "page_count": page_count
            }
                
        except Exception as e:
            return {"code": 912, "data": f"文档识别异常: {e}", "score": 0}
    
    def recognize_url(self, url, timeout=30, extract_text=False):
        """
        识别网络图片URL
        
        参数:
            url: 图片URL地址
            timeout: 超时时间（秒）
            extract_text: 是否只提取文本（针对Python库版本优化）
            
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
            result = self.recognize_bytes(image_bytes, extract_text=extract_text)
            result["url"] = url
            return result
            
        except Exception as e:
            return {"code": 913, "data": f"URL下载或识别失败: {e}", "score": 0}
    
    def recognize_directory(self, dir_path, recursive=False, progress_callback=None):
        """
        识别目录中的所有图片/文档
        
        参数:
            dir_path: 目录路径
            recursive: 是否递归子目录
            progress_callback: 进度回调函数
            
        返回:
            识别结果列表
        """
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            return [{"code": 903, "data": f"目录不存在: {dir_path}", "score": 0}]
        
        # 收集所有支持的文件
        file_paths = []
        supported_formats = self.get_supported_formats()
        
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
        return self.batch_recognize(file_paths, progress_callback=progress_callback)
    
    def batch_recognize(self, image_paths, progress_callback=None):
        """
        批量识别图片/文档
        
        参数:
            image_paths: 图片/文档路径列表（可以是字符串列表或单个字符串）
            progress_callback: 进度回调函数，接收参数 (current_index, total_count, progress_percentage)
            
        返回:
            识别结果列表
        """
        # 如果传入单个路径，转换为列表
        if isinstance(image_paths, str):
            image_paths = [image_paths]
        
        total_count = len(image_paths)
        results = []
        last_progress = -1
        
        for i, path in enumerate(image_paths):
            # 计算并报告进度
            current_progress = int((i / total_count) * 100)
            if current_progress // 10 > last_progress // 10:
                if progress_callback:
                    progress_callback(i, total_count, current_progress)
                else:
                    print(f"[进度] 批量识别中: {current_progress}% ({i}/{total_count}个文件)")
                last_progress = current_progress
                
            result = self.recognize_image(path)
            result["path"] = path
            results.append(result)
        
        # 报告 100% 进度
        if progress_callback:
            progress_callback(total_count, total_count, 100)
        else:
            print(f"[进度] 批量识别完成: 100% ({total_count}/{total_count}个文件)")
            
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
        if self.use_python_lib:
            self.ocr_instance = None
            self.is_initialized = False
            print("[成功] Python OCR 实例已释放")
            return

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

