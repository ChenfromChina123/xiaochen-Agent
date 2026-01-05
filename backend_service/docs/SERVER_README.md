# OCR backend_service - 快速开始

## 🚀 一键启动

### Windows
```bash
双击运行: scripts/start_server.bat
```

### Linux/Mac
```bash
chmod +x scripts/start_server.sh
./scripts/start_server.sh
```

### 手动启动
```bash
cd backend_service
pip install -r requirements.txt
python api/server.py
```

服务将在 `http://localhost:4999` 启动

## 📋 快速测试

### 1. 健康检查
```bash
curl http://localhost:4999/api/health
```

### 2. 识别图片文件
```bash
curl -X POST http://localhost:4999/api/ocr/file \
  -F "file=@test.jpg" \
  -F "extract_text=true"
```

### 3. 识别网络图片
```bash
curl -X POST http://localhost:4999/api/ocr/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/image.jpg", "extract_text": true}'
```

### 4. 运行完整测试
```bash
python tests/test_server.py
```

## 🔧 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/api/health` | GET | 健康检查 |
| `/api/status` | GET | 服务状态 |
| `/api/ocr/file` | POST | 识别上传文件 |
| `/api/ocr/base64` | POST | 识别base64图片 |
| `/api/ocr/url` | POST | 识别网络图片 |
| `/api/ocr/document` | POST | 识别PDF文档 |
| `/api/ocr/batch` | POST | 批量识别 |

## 📖 详细文档

- **HTTP API文档**: `API_SERVER_GUIDE.md`
- **Python API文档**: `API_GUIDE.txt`
- **完整README**: `README.md`

## 💡 客户端示例

### Python
```python
import requests

# 文件识别
with open('test.jpg', 'rb') as f:
    files = {'file': f}
    data = {'extract_text': 'true'}
    response = requests.post('http://localhost:4999/api/ocr/file', 
                            files=files, data=data)
    result = response.json()
    print(result['data']['text'])
```

### JavaScript
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('extract_text', 'true');

fetch('http://localhost:4999/api/ocr/file', {
    method: 'POST',
    body: formData
})
.then(res => res.json())
.then(data => console.log(data.data.text));
```

### curl
```bash
curl -X POST http://localhost:4999/api/ocr/file \
  -F "file=@image.jpg" \
  -F "extract_text=true"
```

## ✅ 测试结果

运行 `test_server.py` 后的测试结果：

```
============================================================
测试结果汇总
============================================================
[✓] 通过 - 服务器信息
[✓] 通过 - 健康检查
[✓] 通过 - 文件识别
[✓] 通过 - Base64识别
[✓] 通过 - 批量识别
[✓] 通过 - 错误处理

总计: 6/6 测试通过
成功率: 100%
```

## 🔒 支持的格式

### 图片格式
`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`

### 文档格式
`.pdf`, `.xps`, `.epub`, `.mobi`, `.fb2`, `.cbz`, `.oxps`

## ⚙️ 配置

编辑 `config.json` 修改OCR引擎参数：

```json
{
    "exe_path": "paddleocr_engine/PaddleOCR-json.exe",
    "models_path": "paddleocr_engine/models",
    "language": "models/config_chinese.txt",
    "cpu_threads": 4,
    "enable_mkldnn": true,
    "cls": false,
    "limit_side_len": 4320,
    "doc_render_dpi": 300
}
```

## 🌐 跨域支持

服务已启用CORS，支持跨域请求，可从任何前端应用调用。

## 📊 性能说明

- **并发**: 使用Flask内置服务器，支持多线程
- **建议**: 生产环境使用Gunicorn等WSGI服务器
- **内存**: 约300-500MB（引擎初始化后）
- **速度**: 单张图片识别约1-3秒（取决于图片大小和内容）

## 🐛 故障排查

### 服务无法启动
1. 检查Python版本（需要3.7+）
2. 安装依赖：`pip install -r requirements_server.txt`
3. 检查端口4999是否被占用

### 识别失败
1. 检查图片格式是否支持
2. 查看服务器日志输出
3. 确认OCR引擎初始化成功

### 连接被拒绝
1. 确认服务器已启动
2. 检查防火墙设置
3. 确认访问地址正确（http://localhost:4999）

## 📞 更多信息

- 完整API文档：`API_SERVER_GUIDE.md`
- 客户端示例：`client_example.py`
- 测试脚本：`test_server.py`

