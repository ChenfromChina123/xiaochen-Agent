# OCR核心模块

## 简介

这是从 Umi-OCR 项目中剥离出的**完全独立**、可复用的OCR识别核心模块。

### 主要特性

- ✅ **完全独立**：包含完整的OCR引擎和模型，可直接复制到任何地方使用
- ✅ **最小代码量**：只保留核心识别功能，去除UI、任务队列等复杂组件
- ✅ **JSON配置**：所有参数通过配置文件管理，无需修改代码
- ✅ **多种输入**：支持图片路径、字节流、base64等多种输入方式
- ✅ **简洁API**：清晰的输入输出接口，易于集成到其他项目
- ✅ **完整文档**：详细的API文档和使用示例
- ✅ **开箱即用**：无需安装额外依赖，下载即可使用

## 支持的文件格式

### 图片格式
`.jpg`, `.jpeg`, `.jpe`, `.jfif`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`

### 文档格式（自动转换后识别）
`.pdf`, `.xps`, `.epub`, `.mobi`, `.fb2`, `.cbz`, `.oxps`

支持PDF等文档的多页识别，自动渲染为图片后进行OCR识别。

## 部署说明

### 完全独立部署

此模块是**完全独立**的，包含所有必需的文件：

1. **直接使用**：无需任何配置，开箱即用
2. **复制部署**：将整个 `backend_service` 文件夹复制到任意位置即可
3. **无外部依赖**：不依赖父项目的任何文件
4. **跨项目使用**：可以集成到任何 Python 项目中
5. **backend_service**：可一键启动为HTTP REST API服务

### 部署方式

#### 方式1：作为Python库使用（推荐）

```bash
# 直接运行测试
cd backend_service
python tests/test_simple.py

# 作为Python包导入
import sys
sys.path.append('/path/to/backend_service')
from core.engine import OCREngine
```

#### 方式2：作为 backend_service 部署

本模块现已支持作为HTTP REST API服务运行，支持跨语言调用：

```bash
# Windows：双击启动
scripts/start_server.bat

# Linux/Mac：命令行启动
scripts/start_server.sh

# 或直接运行
cd backend_service
pip install -r requirements.txt
python api/server.py
```

服务启动后访问：`http://localhost:5000`

**可用接口**：
- `POST /api/ocr/file` - 识别上传的文件
- `POST /api/ocr/base64` - 识别base64图片
- `POST /api/ocr/url` - 识别网络图片
- `POST /api/ocr/document` - 识别PDF文档
- `POST /api/ocr/batch` - 批量识别
- `GET /api/status` - 服务状态
- `GET /api/health` - 健康检查

详细API文档请查看：`API_SERVER_GUIDE.md`

**客户端调用示例**：

```python
# Python客户端
import requests

# 文件识别
with open('test.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:5000/api/ocr/file', files=files)
    print(response.json())

# Base64识别
import base64
with open('test.jpg', 'rb') as f:
    image_base64 = base64.b64encode(f.read()).decode()
    response = requests.post('http://localhost:5000/api/ocr/base64', 
                            json={'image': image_base64, 'extract_text': True})
    print(response.json()['data']['text'])
```

```javascript
// JavaScript客户端
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('extract_text', 'true');

fetch('http://localhost:5000/api/ocr/file', {
    method: 'POST',
    body: formData
})
.then(res => res.json())
.then(data => console.log(data.data.text));
```

```bash
# curl命令行
curl -X POST http://localhost:5000/api/ocr/file \
  -F "file=@test.jpg" \
  -F "extract_text=true"
```

更多客户端示例（C#、Java等）请参考 `client_example.py`

## 快速开始

### 1. 基础使用

```python
from ocr_core import OCREngine

# 创建引擎实例
engine = OCREngine("config.json")

# 初始化引擎
if engine.initialize():
    # 识别图片
    result = engine.recognize_image("test.jpg")
    
    # 输出结果
    if result["code"] == 100:
        text = engine.extract_text(result)
        print(text)
    
    # 关闭引擎
    engine.close()
```

### 2. 使用 with 语句（推荐）

```python
from ocr_core import OCREngine

with OCREngine("config.json") as engine:
    result = engine.recognize_image("test.jpg")
    
    if result["code"] == 100:
        text = engine.extract_text(result)
        print(text)
```

### 3. PDF文档识别

```python
from ocr_core import OCREngine

with OCREngine("config.json") as engine:
    # 识别整个PDF文档
    result = engine.recognize_document("document.pdf")
    
    if result["code"] == 100:
        print(f"总页数: {result['page_count']}")
        print(f"识别的文本块数: {len(result['data'])}")
        
        # 提取所有文本
        text = engine.extract_text(result)
        print(text)
        
        # 查看每页的识别结果
        for page_info in result['pages']:
            print(f"第{page_info['page']}页: {page_info['result']['code']}")

# 识别指定页面范围（例如第2-5页）
with OCREngine("config.json") as engine:
    result = engine.recognize_document("document.pdf", page_range=[2, 5])
```

### 4. 网络图片识别

```python
from ocr_core import OCREngine

with OCREngine("config.json") as engine:
    # 识别网络图片
    url = "https://example.com/image.jpg"
    result = engine.recognize_url(url)
    
    if result["code"] == 100:
        text = engine.extract_text(result)
        print(text)
```

### 5. 目录批量识别

```python
from ocr_core import OCREngine

with OCREngine("config.json") as engine:
    # 识别目录中所有图片/文档（不递归子目录）
    results = engine.recognize_directory("./images")
    
    # 递归识别所有子目录
    results = engine.recognize_directory("./documents", recursive=True)
    
    # 统计结果
    total = len(results)
    success = sum(1 for r in results if r["code"] == 100)
    print(f"成功: {success}/{total}")
```

### 6. 批量识别

```python
from ocr_core import OCREngine

# 混合识别图片和PDF文档
paths = ["img1.jpg", "doc1.pdf", "img2.png"]

with OCREngine("config.json") as engine:
    results = engine.batch_recognize(paths)
    
    for result in results:
        if result["code"] == 100:
            text = engine.extract_text(result)
            print(f"{result['path']}: {text[:100]}...")

## 配置说明

配置文件 `config.json` 示例：

```json
{
    "exe_path": "paddleocr_engine/PaddleOCR-json.exe",
    "models_path": "paddleocr_engine/models",
    "language": "models/config_chinese.txt",
    "cpu_threads": 4,
    "enable_mkldnn": true,
    "cls": false,
    "limit_side_len": 4320
}
```

**注意**：路径为相对于配置文件的相对路径，模块已内置引擎，无需修改。

### 配置项说明

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `exe_path` | string | OCR引擎可执行文件路径 | 必需 |
| `models_path` | string | 模型文件夹路径 | 可选 |
| `language` | string | 语言配置文件 | 必需 |
| `cpu_threads` | int | CPU线程数 | 4 |
| `enable_mkldnn` | bool | 是否启用MKL-DNN加速 | true |
| `cls` | bool | 是否启用方向分类 | false |
| `limit_side_len` | int | 图片长边压缩限制 | 4320 |

### 支持的语言

- `models/config_chinese.txt` - 中文简体
- `models/config_chinese_cht.txt` - 中文繁体
- `models/config_en.txt` - 英文
- `models/config_japan.txt` - 日文
- `models/config_korean.txt` - 韩文
- `models/config_cyrillic.txt` - 西里尔文

## API接口

### OCREngine 类

#### 构造函数

```python
OCREngine(config_path="config.json")
```

#### 主要方法

- `initialize()` - 初始化OCR引擎
- `recognize_image(image_path)` - 识别图片文件（自动支持PDF等文档）
- `recognize_document(doc_path, page_range, dpi, password)` - 识别PDF等文档（多页）
- `recognize_bytes(image_bytes)` - 识别字节流
- `recognize_base64(image_base64)` - 识别base64编码图片
- `recognize_url(url, timeout)` - 识别网络图片URL
- `recognize_directory(dir_path, recursive)` - 识别目录中所有文件
- `batch_recognize(image_paths)` - 批量识别（支持混合文件类型）
- `extract_text(result)` - 提取纯文本
- `close()` - 关闭引擎

### 返回值格式

```python
{
    "code": 100,        # 状态码
    "score": 0.95,      # 平均置信度
    "data": [           # 识别结果列表
        {
            "text": "识别的文字",
            "score": 0.95,
            "box": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        },
        ...
    ]
}
```

### 状态码

- `100` - 成功：识别到文字
- `101` - 成功：图片中未识别到文字
- `901` - 失败：OCR引擎未初始化
- `902` - 失败：不支持的图片格式
- `903` - 失败：图片文件不存在
- `904` - 失败：OCR引擎进程已退出
- `905` - 失败：OCR识别异常

## 文件结构

```
ocr_core/                       # 完全独立的OCR核心模块
├── paddleocr_engine/           # 内置OCR引擎（约200MB）
│   ├── PaddleOCR-json.exe     # 引擎可执行文件
│   ├── models/                 # 模型文件夹
│   │   ├── config_chinese.txt  # 中文简体配置
│   │   ├── config_en.txt       # 英文配置
│   │   ├── config_japan.txt    # 日文配置
│   │   └── ...                 # 其他语言配置
│   └── *.dll                   # 依赖库文件
├── __init__.py                 # 包初始化
├── ocr_engine.py               # 核心引擎类
├── ocr_server.py               # HTTP服务器（新增）
├── client_example.py           # 客户端调用示例（新增）
├── config.json                 # 配置文件
├── requirements_server.txt     # 服务器依赖（新增）
├── start_server.bat            # Windows启动脚本（新增）
├── start_server.sh             # Linux/Mac启动脚本（新增）
├── example.py                  # 完整示例
├── test_simple.py              # 简单测试
├── API_GUIDE.txt               # Python API文档
├── API_SERVER_GUIDE.md         # HTTP API文档（新增）
└── README.md                   # 本文件
```

**整个文件夹约 200MB，可直接复制到任何地方使用。**

## 使用示例

详细的使用示例请参考：
- **Python库方式**：
  - `example.py` - 包含5个完整示例
  - `test_simple.py` - 简单测试脚本
  - `API_GUIDE.txt` - 完整Python API文档
- **服务器方式**：
  - `ocr_server.py` - HTTP服务器实现
  - `client_example.py` - 客户端调用示例（Python）
  - `API_SERVER_GUIDE.md` - 完整HTTP API文档（含多语言示例）

## 依赖说明

本模块是完全独立的，已内置 PaddleOCR-json 引擎，无需额外依赖：

```
ocr_core/
├── paddleocr_engine/    # 内置OCR引擎
│   ├── PaddleOCR-json.exe
│   ├── models/
│   │   ├── config_chinese.txt
│   │   ├── config_en.txt
│   │   └── ...
│   └── *.dll
├── ocr_engine.py
├── config.json
└── ...
```

可以直接将整个 `ocr_core` 文件夹复制到任何地方使用。

## 注意事项

1. **完全独立**：模块已包含所有必需文件，配置文件使用相对路径，无需修改
2. **资源管理**：使用完毕后记得调用 `close()` 或使用 `with` 语句
3. **线程数**：建议 `cpu_threads` 设置为 4-8，过高反而会降低性能
4. **内存占用**：引擎初始化后会占用约300-500MB内存，建议复用同一个实例
5. **文件大小**：完整模块约200MB，主要是模型文件（支持多语言）
6. **便携性**：可以打包成压缩包分发，解压即用

## 常见问题

### Q: 初始化失败？
A: 检查配置文件中的 `exe_path` 和 `models_path` 是否正确

### Q: 识别速度慢？
A: 尝试增加 `cpu_threads`、启用 `enable_mkldnn`、或降低 `limit_side_len`

### Q: 识别准确率低？
A: 确保使用正确的语言配置、提高图片质量、或启用 `cls` 方向分类

### Q: 支持其他平台吗？
A: 需要对应平台的 PaddleOCR-json 可执行文件，请访问项目主页获取

## 相关链接

- [Umi-OCR 项目](https://github.com/hiroi-sora/Umi-OCR)
- [PaddleOCR-json](https://github.com/hiroi-sora/PaddleOCR-json)

## 版本信息

- 版本：1.0.0
- 更新日期：2025-01-04
- 基于：Umi-OCR v2.1.5

## 许可证

本模块继承 Umi-OCR 项目的许可证。

