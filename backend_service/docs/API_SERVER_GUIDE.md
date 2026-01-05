# OCR backend_service API鏂囨。

## 姒傝堪

OCR backend_service 鎻愪緵浜嗗熀浜嶩TTP鐨凴ESTful API鎺ュ彛锛屽彲浠ラ€氳繃鏍囧噯鐨凥TTP璇锋眰璋冪敤OCR璇嗗埆鍔熻兘銆?
- **鏈嶅姟鍦板潃**: `http://aistudy.icu/ocr` (榛樿)
- **鍗忚**: HTTP/HTTPS
- **鏁版嵁鏍煎紡**: JSON
- **瀛楃缂栫爜**: UTF-8

## 缁熶竴鍝嶅簲鏍煎紡

鎵€鏈堿PI鎺ュ彛杩斿洖缁熶竴鐨凧SON鏍煎紡锛?
```json
{
  "success": true,          // 鏄惁鎴愬姛
  "code": 200,             // 鐘舵€佺爜
  "message": "鎿嶄綔鎴愬姛",    // 娑堟伅
  "data": {},              // 鏁版嵁
  "timestamp": "2024-01-01T12:00:00"  // 鏃堕棿鎴?}
```

## API鎺ュ彛鍒楄〃

### 1. 鏈嶅姟淇℃伅

**鎺ュ彛**: `GET /`

**璇存槑**: 鑾峰彇鏈嶅姟鍩烘湰淇℃伅鍜屽彲鐢ㄦ帴鍙ｅ垪琛?
**璇锋眰绀轰緥**:
```bash
curl http://aistudy.icu/ocr/
```

**鍝嶅簲绀轰緥**:
```json
{
  "success": true,
  "code": 200,
  "message": "OCR鏈嶅姟杩愯涓?,
  "data": {
    "service": "OCR Recognition Service",
    "version": "1.0.0",
    "supported_formats": [".jpg", ".png", ".pdf", "..."],
    "endpoints": {
      "POST /api/ocr/file": "璇嗗埆涓婁紶鐨勬枃浠?,
      "POST /api/ocr/base64": "璇嗗埆base64鍥剧墖",
      "...": "..."
    }
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 2. 鍋ュ悍妫€鏌?
**鎺ュ彛**: `GET /api/health`

**璇存槑**: 妫€鏌ユ湇鍔″仴搴风姸鎬?
**璇锋眰绀轰緥**:
```bash
curl http://aistudy.icu/ocr/api/health
```

**鍝嶅簲绀轰緥**:
```json
{
  "success": true,
  "code": 200,
  "message": "鏈嶅姟鍋ュ悍",
  "data": {
    "status": "healthy",
    "engine_initialized": true
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 3. 鏈嶅姟鐘舵€?
**鎺ュ彛**: `GET /api/status`

**璇存槑**: 鑾峰彇鏈嶅姟璇︾粏鐘舵€佷俊鎭?
**璇锋眰绀轰緥**:
```bash
curl http://aistudy.icu/ocr/api/status
```

**鍝嶅簲绀轰緥**:
```json
{
  "success": true,
  "code": 200,
  "message": "鏈嶅姟鐘舵€佹甯?,
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

### 4. 鏂囦欢璇嗗埆

**鎺ュ彛**: `POST /api/ocr/file`

**璇存槑**: 璇嗗埆涓婁紶鐨勫浘鐗囨垨鏂囨。鏂囦欢

**璇锋眰鍙傛暟**:
- `file` (蹇呴渶): 涓婁紶鐨勬枃浠?(multipart/form-data)
- `extract_text` (鍙€?: 鏄惁鍙繑鍥炵函鏂囨湰锛岄粯璁alse

**璇锋眰绀轰緥** (curl):
```bash
# 瀹屾暣缁撴灉
curl -X POST http://aistudy.icu/ocr/api/ocr/file \
  -F "file=@test_image.jpg"

# 鍙繑鍥炴枃鏈?curl -X POST http://aistudy.icu/ocr/api/ocr/file \
  -F "file=@test_image.jpg" \
  -F "extract_text=true"
```

**璇锋眰绀轰緥** (Python):
```python
import requests

url = "http://aistudy.icu/ocr/api/ocr/file"
files = {'file': open('test_image.jpg', 'rb')}
data = {'extract_text': 'false'}
response = requests.post(url, files=files, data=data)
print(response.json())
```

**鍝嶅簲绀轰緥** (extract_text=false):
```json
{
  "success": true,
  "code": 200,
  "message": "璇嗗埆鎴愬姛",
  "data": {
    "filename": "test_image.jpg",
    "ocr_result": {
      "code": 100,
      "data": [
        {
          "text": "璇嗗埆鐨勬枃瀛?,
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

**鍝嶅簲绀轰緥** (extract_text=true):
```json
{
  "success": true,
  "code": 200,
  "message": "璇嗗埆鎴愬姛",
  "data": {
    "text": "璇嗗埆鐨勬枃瀛梊n绗簩琛屾枃瀛?,
    "filename": "test_image.jpg"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 5. Base64璇嗗埆

**鎺ュ彛**: `POST /api/ocr/base64`

**璇存槑**: 璇嗗埆base64缂栫爜鐨勫浘鐗?
**璇锋眰鍙傛暟** (JSON):
- `image` (蹇呴渶): base64缂栫爜鐨勫浘鐗囧瓧绗︿覆
- `extract_text` (鍙€?: 鏄惁鍙繑鍥炵函鏂囨湰锛岄粯璁alse

**璇锋眰绀轰緥** (curl):
```bash
curl -X POST http://aistudy.icu/ocr/api/ocr/base64 \
  -H "Content-Type: application/json" \
  -d '{
    "image": "iVBORw0KGgoAAAANSUhEUgAA...",
    "extract_text": true
  }'
```

**璇锋眰绀轰緥** (Python):
```python
import requests
import base64

url = "http://aistudy.icu/ocr/api/ocr/base64"

# 璇诲彇鍥剧墖骞惰浆鎹负base64
with open('test_image.jpg', 'rb') as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

payload = {
    'image': image_base64,
    'extract_text': True
}

response = requests.post(url, json=payload)
print(response.json())
```

**鍝嶅簲鏍煎紡**: 涓庢枃浠惰瘑鍒帴鍙ｇ浉鍚?
---

### 6. URL璇嗗埆

**鎺ュ彛**: `POST /api/ocr/url`

**璇存槑**: 璇嗗埆缃戠粶鍥剧墖URL

**璇锋眰鍙傛暟** (JSON):
- `url` (蹇呴渶): 鍥剧墖URL
- `timeout` (鍙€?: 瓒呮椂鏃堕棿锛堢锛夛紝榛樿30
- `extract_text` (鍙€?: 鏄惁鍙繑鍥炵函鏂囨湰锛岄粯璁alse

**璇锋眰绀轰緥** (curl):
```bash
curl -X POST http://aistudy.icu/ocr/api/ocr/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/image.jpg",
    "extract_text": true
  }'
```

**璇锋眰绀轰緥** (Python):
```python
import requests

url = "http://aistudy.icu/ocr/api/ocr/url"

payload = {
    'url': 'https://example.com/image.jpg',
    'timeout': 30,
    'extract_text': True
}

response = requests.post(url, json=payload)
print(response.json())
```

**鍝嶅簲鏍煎紡**: 涓庢枃浠惰瘑鍒帴鍙ｇ浉鍚?
---

### 7. 鏂囨。璇嗗埆

**鎺ュ彛**: `POST /api/ocr/document`

**璇存槑**: 璇嗗埆PDF绛夊椤垫枃妗?
**璇锋眰鍙傛暟**:
- `file` (蹇呴渶): 涓婁紶鐨勬枃妗ｆ枃浠?(multipart/form-data)
- `page_range_start` (鍙€?: 璧峰椤电爜锛岄粯璁?
- `page_range_end` (鍙€?: 缁撴潫椤电爜锛岄粯璁ゆ渶鍚庝竴椤?- `dpi` (鍙€?: 娓叉煋DPI锛岄粯璁?00
- `password` (鍙€?: 鏂囨。瀵嗙爜锛堝鏈夊姞瀵嗭級
- `extract_text` (鍙€?: 鏄惁鍙繑鍥炵函鏂囨湰锛岄粯璁alse

**璇锋眰绀轰緥** (curl):
```bash
# 璇嗗埆鍏ㄩ儴椤?curl -X POST http://aistudy.icu/ocr/api/ocr/document \
  -F "file=@test_document.pdf"

# 鎸囧畾椤电爜鑼冨洿
curl -X POST http://aistudy.icu/ocr/api/ocr/document \
  -F "file=@test_document.pdf" \
  -F "page_range_start=1" \
  -F "page_range_end=3" \
  -F "dpi=300" \
  -F "extract_text=true"
```

**璇锋眰绀轰緥** (Python):
```python
import requests

url = "http://aistudy.icu/ocr/api/ocr/document"

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

**鍝嶅簲绀轰緥**:
```json
{
  "success": true,
  "code": 200,
  "message": "璇嗗埆鎴愬姛",
  "data": {
    "text": "绗?椤靛唴瀹筡n绗?椤靛唴瀹筡n...",
    "filename": "test_document.pdf",
    "page_count": 10
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 8. 鎵归噺璇嗗埆

**鎺ュ彛**: `POST /api/ocr/batch`

**璇存槑**: 鎵归噺璇嗗埆澶氫釜鏂囦欢

**璇锋眰鍙傛暟**:
- `files` (蹇呴渶): 澶氫釜涓婁紶鐨勬枃浠?(multipart/form-data)
- `extract_text` (鍙€?: 鏄惁鍙繑鍥炵函鏂囨湰锛岄粯璁alse

**璇锋眰绀轰緥** (curl):
```bash
curl -X POST http://aistudy.icu/ocr/api/ocr/batch \
  -F "files=@test1.jpg" \
  -F "files=@test2.png" \
  -F "files=@test3.jpg" \
  -F "extract_text=true"
```

**璇锋眰绀轰緥** (Python):
```python
import requests

url = "http://aistudy.icu/ocr/api/ocr/batch"

files = [
    ('files', ('test1.jpg', open('test1.jpg', 'rb'))),
    ('files', ('test2.png', open('test2.png', 'rb'))),
    ('files', ('test3.jpg', open('test3.jpg', 'rb')))
]
data = {'extract_text': 'true'}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**鍝嶅簲绀轰緥**:
```json
{
  "success": true,
  "code": 200,
  "message": "鎵归噺璇嗗埆瀹屾垚锛屽叡3涓枃浠?,
  "data": {
    "results": [
      {
        "filename": "test1.jpg",
        "success": true,
        "text": "鏂囦欢1璇嗗埆缁撴灉"
      },
      {
        "filename": "test2.png",
        "success": true,
        "text": "鏂囦欢2璇嗗埆缁撴灉"
      },
      {
        "filename": "test3.jpg",
        "success": false,
        "message": "璇嗗埆澶辫触: ..."
      }
    ],
    "total": 3
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 9. 获取进度

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

### 10. 终止任务

**接口**: `POST /api/ocr/terminate/<task_id>`

**说明**: 强制终止指定的 OCR 任务。

**响应示例**:
```json
{
  "success": true,
  "message": "已发出任务 uuid-12345 的终止指令"
}
```

---

### 11. 配置限制

**上传限制**: 服务器默认限制上传文件大小。当前配置为 `10MB`（可在 `config.json` 中通过 `max_upload_size_mb` 修改）。

如果超过限制，将返回 `413 Request Entity Too Large` 错误：
```json
{
  "success": false,
  "code": 413,
  "message": "上传文件太大。当前服务器限制最大上传大小为 10MB。"
}
```

---

## 错误代码对照表
| 閿欒鐮?| 璇存槑 |
|--------|------|
| 200 | 鎴愬姛 |
| 400 | 璇锋眰鍙傛暟閿欒 |
| 404 | 鎺ュ彛涓嶅瓨鍦?|
| 405 | 涓嶆敮鎸佺殑璇锋眰鏂规硶 |
| 413 | 涓婁紶鏂囦欢杩囧ぇ |
| 500 | 鏈嶅姟鍣ㄥ唴閮ㄩ敊璇?|

## OCR缁撴灉鐮佽鏄?
| 缁撴灉鐮?| 璇存槑 |
|--------|------|
| 100 | 璇嗗埆鎴愬姛 |
| 101 | 鏈瘑鍒埌鏂囧瓧 |
| 200 | 寮曟搸鏈垵濮嬪寲 |
| 201 | 寮曟搸鍒濆鍖栧け璐?|
| 902 | 鏂囦欢涓嶅瓨鍦?|
| 903 | 鏂囨。鏂囦欢涓嶅瓨鍦?|
| 904 | 鏂囨。鍔犲瘑涓斿瘑鐮侀敊璇?|
| 905 | 鏂囨。澶勭悊閿欒 |
| 906 | URL涓嬭浇澶辫触 |
| 907 | URL澶勭悊閿欒 |
| 908 | 鐩綍涓嶅瓨鍦?|
| 910 | 寮曟搸杩涚▼寮傚父 |
| 911 | 寮曟搸鍝嶅簲瓒呮椂 |
| 912 | 鏂囨。璇嗗埆寮傚父 |

## 瀹㈡埛绔泦鎴愮ず渚?
### JavaScript/Node.js

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// 鏂囦欢璇嗗埆
async function ocrFile(filePath) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));
  form.append('extract_text', 'true');
  
  const response = await axios.post(
    'http://aistudy.icu/ocr/api/ocr/file',
    form,
    { headers: form.getHeaders() }
  );
  
  return response.data;
}

// URL璇嗗埆
async function ocrUrl(imageUrl) {
  const response = await axios.post(
    'http://aistudy.icu/ocr/api/ocr/url',
    {
      url: imageUrl,
      extract_text: true
    }
  );
  
  return response.data;
}

// 浣跨敤绀轰緥
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
    private const string baseUrl = "http://aistudy.icu/ocr";
    
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
    private static final String BASE_URL = "http://aistudy.icu/ocr";
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

## 閮ㄧ讲璇存槑

### 寮€鍙戠幆澧?
```bash
# 1. 瀹夎渚濊禆
pip install -r requirements_server.txt

# 2. 鍚姩鏈嶅姟
python ocr_server.py

# 鏈嶅姟灏嗗湪 http://aistudy.icu/ocr 鍚姩
```

### 鐢熶骇鐜 (浣跨敤Gunicorn)

```bash
# 瀹夎gunicorn
pip install gunicorn

# 鍚姩鏈嶅姟锛?涓伐浣滆繘绋嬶級
gunicorn -w 4 -b 0.0.0.0:4999 ocr_server:app

# 鎴栦娇鐢ㄩ厤缃枃浠?gunicorn -c gunicorn_config.py ocr_server:app
```

### Docker閮ㄧ讲

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install -r requirements_server.txt

EXPOSE 4999

CMD ["python", "ocr_server.py"]
```

## 鎬ц兘浼樺寲寤鸿

1. **骞跺彂澶勭悊**: 浣跨敤Gunicorn绛塛SGI鏈嶅姟鍣ㄦ彁渚涘杩涚▼骞跺彂
2. **缁撴灉缂撳瓨**: 瀵圭浉鍚屽浘鐗囩殑璇嗗埆缁撴灉杩涜缂撳瓨
3. **寮傛闃熷垪**: 瀵逛簬澶ф壒閲忎换鍔★紝浣跨敤Celery绛変换鍔￠槦鍒?4. **璐熻浇鍧囪　**: 澶氬彴鏈嶅姟鍣ㄩ厤鍚圢ginx杩涜璐熻浇鍧囪　
5. **璧勬簮闄愬埗**: 闄愬埗涓婁紶鏂囦欢澶у皬鍜屽苟鍙戣姹傛暟

## 瀹夊叏寤鸿

1. **璁よ瘉鎺堟潈**: 娣诲姞API瀵嗛挜鎴朖WT璁よ瘉
2. **HTTPS**: 鐢熶骇鐜浣跨敤HTTPS鍔犲瘑浼犺緭
3. **閫熺巼闄愬埗**: 浣跨敤Flask-Limiter闄愬埗璇锋眰棰戠巼
4. **杈撳叆楠岃瘉**: 涓ユ牸楠岃瘉涓婁紶鏂囦欢绫诲瀷鍜屽ぇ灏?5. **鏃ュ織瀹¤**: 璁板綍鎵€鏈堿PI璋冪敤鏃ュ織

## 甯歌闂

### Q: 濡備綍淇敼鏈嶅姟绔彛锛?
A: 淇敼 `ocr_server.py` 鏂囦欢鏈€鍚庣殑 `app.run()` 鍙傛暟锛?```python
app.run(host='0.0.0.0', port=8080)  # 鏀逛负8080绔彛
```

### Q: 濡備綍澧炲姞涓婁紶鏂囦欢澶у皬闄愬埗锛?
A: 淇敼 `ocr_server.py` 涓殑閰嶇疆锛?```python
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 鏀逛负100MB
```

### Q: 濡備綍鍚敤璋冭瘯妯″紡锛?
A: 鍦?`app.run()` 涓缃?`debug=True`锛?```python
app.run(debug=True)
```

### Q: 濡備綍璺ㄥ煙璁块棶锛?
A: 鏈嶅姟宸插惎鐢–ORS锛岄粯璁ゅ厑璁告墍鏈夊煙鍚嶈闂€傚闇€闄愬埗锛屼慨鏀癸細
```python
CORS(app, resources={r"/api/*": {"origins": ["http://example.com"]}})
```

## 鑱旂郴鏂瑰紡

濡傛湁闂鎴栧缓璁紝璇峰弬鑰冮」鐩甊EADME鏂囨。鎴栨彁浜ssue銆
