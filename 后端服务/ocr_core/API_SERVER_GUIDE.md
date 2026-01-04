# OCR后端服务API文档

## 概述

OCR后端服务提供了基于HTTP的RESTful API接口，可以通过标准的HTTP请求调用OCR识别功能。

- **服务地址**: `http://localhost:5000` (默认)
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

## 统一响应格式

所有API接口返回统一的JSON格式：

```json
{
  "success": true,          // 是否成功
  "code": 200,             // 状态码
  "message": "操作成功",    // 消息
  "data": {},              // 数据
  "timestamp": "2024-01-01T12:00:00"  // 时间戳
}
```

## API接口列表

### 1. 服务信息

**接口**: `GET /`

**说明**: 获取服务基本信息和可用接口列表

**请求示例**:
```bash
curl http://localhost:5000/
```

**响应示例**:
```json
{
  "success": true,
  "code": 200,
  "message": "OCR服务运行中",
  "data": {
    "service": "OCR Recognition Service",
    "version": "1.0.0",
    "supported_formats": [".jpg", ".png", ".pdf", "..."],
    "endpoints": {
      "POST /api/ocr/file": "识别上传的文件",
      "POST /api/ocr/base64": "识别base64图片",
      "...": "..."
    }
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 2. 健康检查

**接口**: `GET /api/health`

**说明**: 检查服务健康状态

**请求示例**:
```bash
curl http://localhost:5000/api/health
```

**响应示例**:
```json
{
  "success": true,
  "code": 200,
  "message": "服务健康",
  "data": {
    "status": "healthy",
    "engine_initialized": true
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 3. 服务状态

**接口**: `GET /api/status`

**说明**: 获取服务详细状态信息

**请求示例**:
```bash
curl http://localhost:5000/api/status
```

**响应示例**:
```json
{
  "success": true,
  "code": 200,
  "message": "服务状态正常",
  "data": {
    "engine_initialized": true,
    "supported_image_formats": [".jpg", ".png", "..."],
    "supported_doc_formats": [".pdf", ".docx", "..."],
    "config": {
      "exe_path": "...",
      "models_path": "...",
      "...": "..."
    }
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 4. 文件识别

**接口**: `POST /api/ocr/file`

**说明**: 识别上传的图片或文档文件

**请求参数**:
- `file` (必需): 上传的文件 (multipart/form-data)
- `extract_text` (可选): 是否只返回纯文本，默认false

**请求示例** (curl):
```bash
# 完整结果
curl -X POST http://localhost:5000/api/ocr/file \
  -F "file=@test_image.jpg"

# 只返回文本
curl -X POST http://localhost:5000/api/ocr/file \
  -F "file=@test_image.jpg" \
  -F "extract_text=true"
```

**请求示例** (Python):
```python
import requests

url = "http://localhost:5000/api/ocr/file"
files = {'file': open('test_image.jpg', 'rb')}
data = {'extract_text': 'false'}
response = requests.post(url, files=files, data=data)
print(response.json())
```

**响应示例** (extract_text=false):
```json
{
  "success": true,
  "code": 200,
  "message": "识别成功",
  "data": {
    "filename": "test_image.jpg",
    "ocr_result": {
      "code": 100,
      "data": [
        {
          "text": "识别的文字",
          "score": 0.95,
          "box": [[10, 20], [100, 20], [100, 40], [10, 40]]
        }
      ],
      "score": 0.95
    }
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

**响应示例** (extract_text=true):
```json
{
  "success": true,
  "code": 200,
  "message": "识别成功",
  "data": {
    "text": "识别的文字\n第二行文字",
    "filename": "test_image.jpg"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 5. Base64识别

**接口**: `POST /api/ocr/base64`

**说明**: 识别base64编码的图片

**请求参数** (JSON):
- `image` (必需): base64编码的图片字符串
- `extract_text` (可选): 是否只返回纯文本，默认false

**请求示例** (curl):
```bash
curl -X POST http://localhost:5000/api/ocr/base64 \
  -H "Content-Type: application/json" \
  -d '{
    "image": "iVBORw0KGgoAAAANSUhEUgAA...",
    "extract_text": true
  }'
```

**请求示例** (Python):
```python
import requests
import base64

url = "http://localhost:5000/api/ocr/base64"

# 读取图片并转换为base64
with open('test_image.jpg', 'rb') as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

payload = {
    'image': image_base64,
    'extract_text': True
}

response = requests.post(url, json=payload)
print(response.json())
```

**响应格式**: 与文件识别接口相同

---

### 6. URL识别

**接口**: `POST /api/ocr/url`

**说明**: 识别网络图片URL

**请求参数** (JSON):
- `url` (必需): 图片URL
- `timeout` (可选): 超时时间（秒），默认30
- `extract_text` (可选): 是否只返回纯文本，默认false

**请求示例** (curl):
```bash
curl -X POST http://localhost:5000/api/ocr/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/image.jpg",
    "extract_text": true
  }'
```

**请求示例** (Python):
```python
import requests

url = "http://localhost:5000/api/ocr/url"

payload = {
    'url': 'https://example.com/image.jpg',
    'timeout': 30,
    'extract_text': True
}

response = requests.post(url, json=payload)
print(response.json())
```

**响应格式**: 与文件识别接口相同

---

### 7. 文档识别

**接口**: `POST /api/ocr/document`

**说明**: 识别PDF等多页文档

**请求参数**:
- `file` (必需): 上传的文档文件 (multipart/form-data)
- `page_range_start` (可选): 起始页码，默认1
- `page_range_end` (可选): 结束页码，默认最后一页
- `dpi` (可选): 渲染DPI，默认200
- `password` (可选): 文档密码（如有加密）
- `extract_text` (可选): 是否只返回纯文本，默认false

**请求示例** (curl):
```bash
# 识别全部页
curl -X POST http://localhost:5000/api/ocr/document \
  -F "file=@test_document.pdf"

# 指定页码范围
curl -X POST http://localhost:5000/api/ocr/document \
  -F "file=@test_document.pdf" \
  -F "page_range_start=1" \
  -F "page_range_end=3" \
  -F "dpi=300" \
  -F "extract_text=true"
```

**请求示例** (Python):
```python
import requests

url = "http://localhost:5000/api/ocr/document"

files = {'file': open('test_document.pdf', 'rb')}
data = {
    'page_range_start': '1',
    'page_range_end': '3',
    'dpi': '300',
    'extract_text': 'true'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**响应示例**:
```json
{
  "success": true,
  "code": 200,
  "message": "识别成功",
  "data": {
    "text": "第1页内容\n第2页内容\n...",
    "filename": "test_document.pdf",
    "page_count": 10
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 8. 批量识别

**接口**: `POST /api/ocr/batch`

**说明**: 批量识别多个文件

**请求参数**:
- `files` (必需): 多个上传的文件 (multipart/form-data)
- `extract_text` (可选): 是否只返回纯文本，默认false

**请求示例** (curl):
```bash
curl -X POST http://localhost:5000/api/ocr/batch \
  -F "files=@test1.jpg" \
  -F "files=@test2.png" \
  -F "files=@test3.jpg" \
  -F "extract_text=true"
```

**请求示例** (Python):
```python
import requests

url = "http://localhost:5000/api/ocr/batch"

files = [
    ('files', ('test1.jpg', open('test1.jpg', 'rb'))),
    ('files', ('test2.png', open('test2.png', 'rb'))),
    ('files', ('test3.jpg', open('test3.jpg', 'rb')))
]
data = {'extract_text': 'true'}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**响应示例**:
```json
{
  "success": true,
  "code": 200,
  "message": "批量识别完成，共3个文件",
  "data": {
    "results": [
      {
        "filename": "test1.jpg",
        "success": true,
        "text": "文件1识别结果"
      },
      {
        "filename": "test2.png",
        "success": true,
        "text": "文件2识别结果"
      },
      {
        "filename": "test3.jpg",
        "success": false,
        "message": "识别失败: ..."
      }
    ],
    "total": 3
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 接口不存在 |
| 405 | 不支持的请求方法 |
| 413 | 上传文件过大 |
| 500 | 服务器内部错误 |

## OCR结果码说明

| 结果码 | 说明 |
|--------|------|
| 100 | 识别成功 |
| 101 | 未识别到文字 |
| 200 | 引擎未初始化 |
| 201 | 引擎初始化失败 |
| 902 | 文件不存在 |
| 903 | 文档文件不存在 |
| 904 | 文档加密且密码错误 |
| 905 | 文档处理错误 |
| 906 | URL下载失败 |
| 907 | URL处理错误 |
| 908 | 目录不存在 |
| 910 | 引擎进程异常 |
| 911 | 引擎响应超时 |
| 912 | 文档识别异常 |

## 客户端集成示例

### JavaScript/Node.js

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// 文件识别
async function ocrFile(filePath) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));
  form.append('extract_text', 'true');
  
  const response = await axios.post(
    'http://localhost:5000/api/ocr/file',
    form,
    { headers: form.getHeaders() }
  );
  
  return response.data;
}

// URL识别
async function ocrUrl(imageUrl) {
  const response = await axios.post(
    'http://localhost:5000/api/ocr/url',
    {
      url: imageUrl,
      extract_text: true
    }
  );
  
  return response.data;
}

// 使用示例
ocrFile('test.jpg').then(result => console.log(result));
ocrUrl('https://example.com/image.jpg').then(result => console.log(result));
```

### C#

```csharp
using System;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;

class OCRClient
{
    private static readonly HttpClient client = new HttpClient();
    private const string baseUrl = "http://localhost:5000";
    
    public static async Task<string> OCRFile(string filePath)
    {
        using (var content = new MultipartFormDataContent())
        {
            var fileContent = new ByteArrayContent(File.ReadAllBytes(filePath));
            content.Add(fileContent, "file", Path.GetFileName(filePath));
            content.Add(new StringContent("true"), "extract_text");
            
            var response = await client.PostAsync($"{baseUrl}/api/ocr/file", content);
            return await response.Content.ReadAsStringAsync();
        }
    }
    
    public static async Task Main()
    {
        string result = await OCRFile("test.jpg");
        Console.WriteLine(result);
    }
}
```

### Java

```java
import okhttp3.*;
import java.io.File;
import java.io.IOException;

public class OCRClient {
    private static final String BASE_URL = "http://localhost:5000";
    private static final OkHttpClient client = new OkHttpClient();
    
    public static String ocrFile(String filePath) throws IOException {
        File file = new File(filePath);
        
        RequestBody requestBody = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", file.getName(),
                RequestBody.create(file, MediaType.parse("image/*")))
            .addFormDataPart("extract_text", "true")
            .build();
        
        Request request = new Request.Builder()
            .url(BASE_URL + "/api/ocr/file")
            .post(requestBody)
            .build();
        
        try (Response response = client.newCall(request).execute()) {
            return response.body().string();
        }
    }
    
    public static void main(String[] args) throws IOException {
        String result = ocrFile("test.jpg");
        System.out.println(result);
    }
}
```

## 部署说明

### 开发环境

```bash
# 1. 安装依赖
pip install -r requirements_server.txt

# 2. 启动服务
python ocr_server.py

# 服务将在 http://localhost:5000 启动
```

### 生产环境 (使用Gunicorn)

```bash
# 安装gunicorn
pip install gunicorn

# 启动服务（4个工作进程）
gunicorn -w 4 -b 0.0.0.0:5000 ocr_server:app

# 或使用配置文件
gunicorn -c gunicorn_config.py ocr_server:app
```

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install -r requirements_server.txt

EXPOSE 5000

CMD ["python", "ocr_server.py"]
```

## 性能优化建议

1. **并发处理**: 使用Gunicorn等WSGI服务器提供多进程并发
2. **结果缓存**: 对相同图片的识别结果进行缓存
3. **异步队列**: 对于大批量任务，使用Celery等任务队列
4. **负载均衡**: 多台服务器配合Nginx进行负载均衡
5. **资源限制**: 限制上传文件大小和并发请求数

## 安全建议

1. **认证授权**: 添加API密钥或JWT认证
2. **HTTPS**: 生产环境使用HTTPS加密传输
3. **速率限制**: 使用Flask-Limiter限制请求频率
4. **输入验证**: 严格验证上传文件类型和大小
5. **日志审计**: 记录所有API调用日志

## 常见问题

### Q: 如何修改服务端口？

A: 修改 `ocr_server.py` 文件最后的 `app.run()` 参数：
```python
app.run(host='0.0.0.0', port=8080)  # 改为8080端口
```

### Q: 如何增加上传文件大小限制？

A: 修改 `ocr_server.py` 中的配置：
```python
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 改为100MB
```

### Q: 如何启用调试模式？

A: 在 `app.run()` 中设置 `debug=True`：
```python
app.run(debug=True)
```

### Q: 如何跨域访问？

A: 服务已启用CORS，默认允许所有域名访问。如需限制，修改：
```python
CORS(app, resources={r"/api/*": {"origins": ["http://example.com"]}})
```

## 联系方式

如有问题或建议，请参考项目README文档或提交Issue。

