# -*- coding: utf-8 -*-
"""
OCR backend_service - Flask RESTful API
提供HTTP接口调用OCR识别功能
"""

import os
import sys
import json
import base64
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.engine import OCREngine

# ==================== 配置 ====================

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 创建 Blueprint 以支持 /ocr 前缀
ocr_bp = Blueprint('ocr', __name__)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 最大50MB
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
# 使用绝对路径加载配置文件
app.config['OCR_CONFIG'] = os.path.join(BASE_DIR, 'configs', 'config.json')

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'jpe', 'jfif', 'png', 'webp', 'bmp', 'tif', 'tiff',
    'pdf', 'xps', 'epub', 'mobi', 'fb2', 'cbz', 'oxps'
}

# 全局OCR引擎实例
ocr_engine = None

def init_ocr_engine():
    """
    初始化OCR引擎（全局单例）
    """
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = OCREngine(app.config['OCR_CONFIG'])
        success = ocr_engine.initialize()
        if success:
            print("[服务器] OCR引擎初始化成功")
        else:
            print("[服务器] OCR引擎初始化失败")
            raise Exception("OCR引擎初始化失败")
    return ocr_engine

def allowed_file(filename):
    """
    检查文件扩展名是否允许
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_response(success=True, code=200, message="", data=None):
    """
    格式化API响应
    
    参数:
        success: 是否成功
        code: 状态码
        message: 消息
        data: 数据
        
    返回:
        标准化的JSON响应
    """
    return jsonify({
        'success': success,
        'code': code,
        'message': message,
        'data': data,
        'timestamp': datetime.now().isoformat()
    })

# 进度存储目录
PROGRESS_DIR = os.path.join(tempfile.gettempdir(), "ocr_progress")
if not os.path.exists(PROGRESS_DIR):
    os.makedirs(PROGRESS_DIR, exist_ok=True)

def update_task_progress(task_id, current, total, percentage):
    """更新任务进度到临时文件"""
    if not task_id:
        return
    progress_file = os.path.join(PROGRESS_DIR, f"{task_id}.json")
    try:
        with open(progress_file, 'w') as f:
            json.dump({
                "current": current,
                "total": total,
                "percentage": percentage,
                "timestamp": datetime.now().isoformat()
            }, f)
    except Exception as e:
        print(f"[警告] 无法更新进度文件: {e}")

# ==================== API路由 ====================

@ocr_bp.route('/api/progress/<task_id>')
def get_progress(task_id):
    """获取任务进度"""
    progress_file = os.path.join(PROGRESS_DIR, f"{task_id}.json")
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)
            return format_response(success=True, data=data)
        except:
            pass
    return format_response(success=False, message="任务不存在或进度不可用")

@ocr_bp.route('/')
def index():
    """
    服务器信息
    """
    engine = init_ocr_engine()
    return format_response(
        success=True,
        message="OCR服务运行中",
        data={
            'service': 'OCR Recognition Service',
            'version': '1.0.0',
            'supported_formats': engine.get_supported_formats(),
            'endpoints': {
                'POST /api/ocr/file': '识别上传的文件',
                'POST /api/ocr/base64': '识别base64图片',
                'POST /api/ocr/url': '识别网络图片',
                'POST /api/ocr/document': '识别PDF文档（多页）',
                'POST /api/ocr/batch': '批量识别',
                'GET /api/status': '服务状态',
                'GET /api/health': '健康检查'
            }
        }
    )

@ocr_bp.route('/api/health')
def health():
    """
    健康检查接口
    """
    try:
        engine = init_ocr_engine()
        return format_response(
            success=True,
            message="服务健康",
            data={'status': 'healthy', 'engine_initialized': engine.is_initialized}
        )
    except Exception as e:
        return format_response(
            success=False,
            code=500,
            message=f"服务异常: {str(e)}",
            data={'status': 'unhealthy'}
        )

@ocr_bp.route('/api/status')
def status():
    """
    服务状态接口
    """
    try:
        engine = init_ocr_engine()
        return format_response(
            success=True,
            message="服务状态正常",
            data={
                'engine_initialized': engine.is_initialized,
                'supported_image_formats': engine.SUPPORTED_IMAGE_FORMATS,
                'supported_doc_formats': engine.SUPPORTED_DOC_FORMATS if hasattr(engine, 'SUPPORTED_DOC_FORMATS') else [],
                'config': engine.config
            }
        )
    except Exception as e:
        return format_response(
            success=False,
            code=500,
            message=f"获取状态失败: {str(e)}"
        )

@ocr_bp.route('/api/ocr/file', methods=['POST'])
def ocr_file():
    """
    识别上传的文件
    
    参数:
        file: 上传的文件（multipart/form-data）
        extract_text: 是否只返回纯文本（可选，默认false）
        
    返回:
        OCR识别结果
    """
    try:
        # 检查文件
        if 'file' not in request.files:
            return format_response(
                success=False,
                code=400,
                message="未找到上传的文件"
            )
        
        file = request.files['file']
        
        if file.filename == '':
            return format_response(
                success=False,
                code=400,
                message="文件名为空"
            )
        
        if not allowed_file(file.filename):
            return format_response(
                success=False,
                code=400,
                message=f"不支持的文件格式: {file.filename}"
            )
        
        # 获取引擎和文件扩展名
        engine = init_ocr_engine()
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[-1].lower()
        
        # 区分图片和文档处理
        if ext in engine.SUPPORTED_IMAGE_FORMATS:
            # 图片处理：直接读取字节流，避免产生临时文件导致的文件占用问题
            file_bytes = file.read()
            result = engine.recognize_bytes(file_bytes)
            
            # 是否只返回文本
            extract_text = request.form.get('extract_text', 'false').lower() == 'true'
            
            if extract_text and result.get('code') == 100:
                text = engine.extract_text(result)
                return format_response(
                    success=True,
                    message="识别成功",
                    data={'text': text, 'filename': filename}
                )
            else:
                return format_response(
                    success=result.get('code') == 100,
                    code=200 if result.get('code') == 100 else 400,
                    message="识别成功" if result.get('code') == 100 else f"识别失败: {result.get('data')}",
                    data={
                        'filename': filename,
                        'ocr_result': result
                    }
                )
        else:
            # 文档处理：仍需保存临时文件（PyMuPDF需要路径）
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"ocr_temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
            file.save(temp_path)
            
            try:
                # OCR识别
                result = engine.recognize_image(temp_path)
                
                # 是否只返回文本
                extract_text = request.form.get('extract_text', 'false').lower() == 'true'
                
                if extract_text and result.get('code') == 100:
                    text = engine.extract_text(result)
                    return format_response(
                        success=True,
                        message="识别成功",
                        data={'text': text, 'filename': filename}
                    )
                else:
                    return format_response(
                        success=result.get('code') == 100,
                        code=200 if result.get('code') == 100 else 400,
                        message="识别成功" if result.get('code') == 100 else f"识别失败: {result.get('data')}",
                        data={
                            'filename': filename,
                            'ocr_result': result
                        }
                    )
            finally:
                # 安全删除临时文件
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        print(f"[警告] 无法删除临时文件 {temp_path}: {e}")
                
    except Exception as e:
        return format_response(
            success=False,
            code=500,
            message=f"服务器错误: {str(e)}"
        )

@ocr_bp.route('/api/ocr/base64', methods=['POST'])
def ocr_base64():
    """
    识别base64编码的图片
    
    参数 (JSON):
        image: base64编码的图片字符串
        extract_text: 是否只返回纯文本（可选）
        
    返回:
        OCR识别结果
    """
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return format_response(
                success=False,
                code=400,
                message="缺少image参数"
            )
        
        image_base64 = data['image']
        extract_text = data.get('extract_text', False)
        
        # OCR识别
        engine = init_ocr_engine()
        result = engine.recognize_base64(image_base64)
        
        if extract_text and result.get('code') == 100:
            text = engine.extract_text(result)
            return format_response(
                success=True,
                message="识别成功",
                data={'text': text}
            )
        else:
            return format_response(
                success=result.get('code') == 100,
                code=200 if result.get('code') == 100 else 400,
                message="识别成功" if result.get('code') == 100 else f"识别失败: {result.get('data')}",
                data={'ocr_result': result}
            )
            
    except Exception as e:
        return format_response(
            success=False,
            code=500,
            message=f"服务器错误: {str(e)}"
        )

@ocr_bp.route('/api/ocr/url', methods=['POST'])
def ocr_url():
    """
    识别网络图片URL
    
    参数 (JSON):
        url: 图片URL
        timeout: 超时时间（可选，默认30秒）
        extract_text: 是否只返回纯文本（可选）
        
    返回:
        OCR识别结果
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return format_response(
                success=False,
                code=400,
                message="缺少url参数"
            )
        
        url = data['url']
        timeout = data.get('timeout', 30)
        extract_text = data.get('extract_text', False)
        
        # OCR识别
        engine = init_ocr_engine()
        result = engine.recognize_url(url, timeout=timeout)
        
        if extract_text and result.get('code') == 100:
            text = engine.extract_text(result)
            return format_response(
                success=True,
                message="识别成功",
                data={'text': text, 'url': url}
            )
        else:
            return format_response(
                success=result.get('code') == 100,
                code=200 if result.get('code') == 100 else 400,
                message="识别成功" if result.get('code') == 100 else f"识别失败: {result.get('data')}",
                data={'url': url, 'ocr_result': result}
            )
            
    except Exception as e:
        return format_response(
            success=False,
            code=500,
            message=f"服务器错误: {str(e)}"
        )

@ocr_bp.route('/api/ocr/document', methods=['POST'])
def ocr_document():
    """
    识别PDF等文档（支持多页）
    
    参数:
        file: 上传的文档文件
        page_range_start: 起始页（可选，默认1）
        page_range_end: 结束页（可选，默认最后一页）
        dpi: 渲染DPI（可选，默认200）
        password: 文档密码（可选）
        extract_text: 是否只返回纯文本（可选）
        
    返回:
        文档OCR识别结果
    """
    try:
        if 'file' not in request.files:
            return format_response(
                success=False,
                code=400,
                message="未找到上传的文件"
            )
        
        file = request.files['file']
        
        if file.filename == '':
            return format_response(
                success=False,
                code=400,
                message="文件名为空"
            )
        
        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"ocr_doc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
        file.save(temp_path)
        
        try:
            # 获取参数
            page_start = request.form.get('page_range_start', None)
            page_end = request.form.get('page_range_end', None)
            task_id = request.form.get('task_id', None)
            page_range = None
            if page_start and page_end:
                page_range = [int(page_start), int(page_end)]
            
            dpi = int(request.form.get('dpi', 200))
            password = request.form.get('password', '')
            extract_text = request.form.get('extract_text', 'false').lower() == 'true'
            
            # OCR识别
            engine = init_ocr_engine()
            
            # 定义进度回调函数
            def progress_callback(current, total, percentage):
                print(f"[进度] 文档识别中: {percentage}% ({current}/{total}页)")
                if task_id:
                    update_task_progress(task_id, current, total, percentage)
            
            result = engine.recognize_document(temp_path, page_range=page_range, dpi=dpi, password=password, progress_callback=progress_callback)
            
            # 完成后清理进度文件
            if task_id:
                progress_file = os.path.join(PROGRESS_DIR, f"{task_id}.json")
                if os.path.exists(progress_file):
                    os.remove(progress_file)
            
            if extract_text and result.get('code') == 100:
                text = engine.extract_text(result)
                return format_response(
                    success=True,
                    message="识别成功",
                    data={
                        'text': text,
                        'filename': filename,
                        'page_count': result.get('page_count', 0)
                    }
                )
            else:
                return format_response(
                    success=result.get('code') == 100,
                    code=200 if result.get('code') == 100 else 400,
                    message="识别成功" if result.get('code') == 100 else f"识别失败: {result.get('data')}",
                    data={
                        'filename': filename,
                        'ocr_result': result
                    }
                )
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        return format_response(
            success=False,
            code=500,
            message=f"服务器错误: {str(e)}"
        )

@ocr_bp.route('/api/ocr/batch', methods=['POST'])
def ocr_batch():
    """
    批量识别多个文件
    
    参数:
        files: 多个上传的文件
        extract_text: 是否只返回纯文本（可选）
        
    返回:
        批量识别结果列表
    """
    try:
        if 'files' not in request.files:
            return format_response(
                success=False,
                code=400,
                message="未找到上传的文件"
            )
        
        files = request.files.getlist('files')
        task_id = request.form.get('task_id', None)
        
        if not files:
            return format_response(
                success=False,
                code=400,
                message="文件列表为空"
            )
        
        extract_text = request.form.get('extract_text', 'false').lower() == 'true'
        
        results = []
        temp_files = []
        
        try:
            engine = init_ocr_engine()
            total_files = len(files)
            last_progress = -1
            
            # 收集文件并识别
            for i, file in enumerate(files):
                if file.filename == '':
                    continue
                
                # 计算并显示进度
                current_progress = int((i / total_files) * 100)
                if current_progress // 10 > last_progress // 10:
                    print(f"[进度] 批量识别中: {current_progress}% ({i}/{total_files})")
                    if task_id:
                        update_task_progress(task_id, i, total_files, current_progress)
                    last_progress = current_progress
                
                filename = secure_filename(file.filename)
                ext = os.path.splitext(filename)[-1].lower()
                
                try:
                    if ext in engine.SUPPORTED_IMAGE_FORMATS:
                        # 图片处理：直接读取字节流
                        file_bytes = file.read()
                        result = engine.recognize_bytes(file_bytes)
                        
                        if extract_text and result.get('code') == 100:
                            text = engine.extract_text(result)
                            results.append({
                                'filename': filename,
                                'success': True,
                                'text': text
                            })
                        else:
                            results.append({
                                'filename': filename,
                                'success': result.get('code') == 100,
                                'ocr_result': result
                            })
                    else:
                        # 文档处理：保存临时文件
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"ocr_batch_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
                        file.save(temp_path)
                        
                        try:
                            result = engine.recognize_image(temp_path)
                            
                            if extract_text and result.get('code') == 100:
                                text = engine.extract_text(result)
                                results.append({
                                    'filename': filename,
                                    'success': True,
                                    'text': text
                                })
                            else:
                                results.append({
                                    'filename': filename,
                                    'success': result.get('code') == 100,
                                    'ocr_result': result
                                })
                        finally:
                            # 安全删除临时文件
                            if os.path.exists(temp_path):
                                try:
                                    os.remove(temp_path)
                                except Exception as e:
                                    print(f"[警告] 无法删除临时文件 {temp_path}: {e}")
                except Exception as e:
                    results.append({
                        'filename': filename,
                        'success': False,
                        'message': f'识别失败: {str(e)}'
                    })
            
            # 报告 100% 进度
            print(f"[进度] 批量识别完成: 100% ({len(results)}/{total_files})")
            if task_id:
                update_task_progress(task_id, total_files, total_files, 100)
                # 稍微延迟删除，让客户端有机会读取到100%
                # 但这里是同步请求，客户端只有在请求结束后才会知道100%，
                # 所以其实请求结束后删除即可
                progress_file = os.path.join(PROGRESS_DIR, f"{task_id}.json")
                if os.path.exists(progress_file):
                    os.remove(progress_file)
            
            return format_response(
                success=True,
                message=f"批量识别完成，共{len(results)}个文件",
                data={'results': results, 'total': len(results)}
            )
            
        finally:
            # 删除所有临时文件
            for temp_path, _ in temp_files:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
    except Exception as e:
        return format_response(
            success=False,
            code=500,
            message=f"服务器错误: {str(e)}"
        )

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return format_response(
        success=False,
        code=404,
        message="接口不存在"
    ), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """405错误处理"""
    return format_response(
        success=False,
        code=405,
        message="不支持的请求方法"
    ), 405

@app.errorhandler(413)
def request_entity_too_large(error):
    """413错误处理"""
    return format_response(
        success=False,
        code=413,
        message="上传文件过大，最大支持50MB"
    ), 413

@app.errorhandler(500)
def internal_server_error(error):
    """500错误处理"""
    return format_response(
        success=False,
        code=500,
        message="服务器内部错误"
    ), 500

# 注册 Blueprint
app.register_blueprint(ocr_bp, url_prefix='/ocr')

# ==================== 主程序 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("OCR识别服务启动中...")
    print("=" * 60)
    
    # 初始化OCR引擎
    try:
        init_ocr_engine()
        print("\n[✓] OCR引擎初始化成功")
    except Exception as e:
        print(f"\n[✗] OCR引擎初始化失败: {e}")
        sys.exit(1)
    
    print("\n可用接口:")
    print("  POST /api/ocr/file      - 识别上传的文件")
    print("  POST /api/ocr/base64    - 识别base64图片")
    print("  POST /api/ocr/url       - 识别网络图片")
    print("  POST /api/ocr/document  - 识别PDF文档（多页）")
    print("  POST /api/ocr/batch     - 批量识别")
    print("  GET  /api/status        - 服务状态")
    print("  GET  /api/health        - 健康检查")
    print("\n" + "=" * 60)
    
    # 启动服务器
    app.run(
        host='0.0.0.0',
        port=4999,
        debug=False,
        threaded=True
    )

