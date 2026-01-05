# OCR backend_service API文档

## 概述

OCR backend_service 提供了基于HTTP的RESTful API接口，可以通过标准的HTTP请求调用OCR识别功能。
- **服务地址**: `http://127.0.0.1:4999/ocr` (本地默认)
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
curl http://127.0.0.1:4999/ocr/
```

---

### 2. 健康检查
**接口**: `GET /api/health`

**说明**: 检查服务健康状态
**请求示例**:
```bash
curl http://127.0.0.1:4999/ocr/api/health
```

---

### 3. 服务状态
**接口**: `GET /api/status`

**说明**: 获取服务详细状态信息
**请求示例**:
```bash
curl http://127.0.0.1:4999/ocr/api/status
```

---

### 4. 文件识别

**接口**: `POST /api/ocr/file`

**说明**: 识别上传的图片或文档文件

**请求参数**:
- `file` (必需): 上传的文件 (multipart/form-data)
- `extract_text` (可选): 是否只返回纯文本，默认false
- `task_id` (可选): 任务ID，用于进度追踪和终止

**请求示例** (curl):
```bash
# 完整结果
curl -X POST http://127.0.0.1:4999/ocr/api/ocr/file \
  -F "file=@test_image.jpg"

# 只返回文本
curl -X POST http://127.0.0.1:4999/ocr/api/ocr/file \
  -F "file=@test_image.jpg" \
  -F "extract_text=true"
```

---

### 5. 文档识别

**接口**: `POST /api/ocr/document`

**说明**: 识别PDF等多页文档
**请求参数**:
- `file` (必需): 上传的文档文件 (multipart/form-data)
- `page_range_start` (可选): 起始页码，默认1
- `page_range_end` (可选): 结束页码，默认最后一页
- `dpi` (可选): 渲染DPI，默认200
- `password` (可选): 文档密码（如有加密）
- `extract_text` (可选): 是否只返回纯文本，默认false
- `task_id` (可选): 任务ID，用于进度追踪和终止

---

### 6. 批量识别

**接口**: `POST /api/ocr/batch`

**说明**: 批量识别多个文件

**请求参数**:
- `files` (必需): 多个上传的文件 (multipart/form-data)
- `extract_text` (可选): 是否只返回纯文本，默认false
- `task_id` (可选): 任务ID，用于进度追踪和终止

---

### 7. 获取进度

**接口**: `GET /api/progress/<task_id>`

**说明**: 获取指定 `task_id` 的任务处理进度。

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "uuid-12345",
    "current": 5,
    "total": 10,
    "percentage": 50,
    "timestamp": 1704445200.0
  }
}
```

---

### 8. 终止任务

**接口**: `POST /api/ocr/terminate/<task_id>`

**说明**: 强制终止指定的 OCR 任务。支持文档识别和批量识别的实时终止。

**响应示例**:
```json
{
  "success": true,
  "message": "已发出任务 uuid-12345 的终止指令"
}
```

---

### 9. 配置限制

**上传限制**: 服务器限制上传文件大小。当前配置为 `10MB`（可在 `config.json` 中通过 `max_upload_size_mb` 修改）。

如果超过限制，将返回 `413 Request Entity Too Large` 错误：
```json
{
  "success": false,
  "code": 413,
  "message": "上传文件太大。当前服务器限制最大上传大小为 10MB。"
}
```

---

## 部署说明

### 启动服务
```bash
python api/server.py
```
服务将在 `http://0.0.0.0:4999` 启动。

### 生产环境
建议使用生产级 WSGI 服务器，如 Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:4999 api.server:app
```
