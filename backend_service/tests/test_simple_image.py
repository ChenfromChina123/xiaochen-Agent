import requests
import os
import json

def test_simple_image_ocr():
    """使用简单图片测试 OCR 后端服务"""
    # 服务地址
    url = "http://127.0.0.1:4999/ocr/api/ocr/file"
    
    # 测试图片路径
    img_path = os.path.join(os.path.dirname(__file__), "data", "4月13日上午九点清扫活动.jpg")
    
    if not os.path.exists(img_path):
        print(f"错误: 找不到测试图片 {img_path}")
        return

    print(f"正在测试图片识别: {os.path.basename(img_path)}")
    
    try:
        # 发送 POST 请求
        with open(img_path, "rb") as f:
            files = {"file": f}
            # 增加任务ID用于追踪
            data = {"task_id": "test_simple_img_001"}
            response = requests.post(url, files=files, data=data, timeout=60)
        
        # 处理结果
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 100:
                print("\n[测试成功] OCR 识别结果:")
                print("-" * 30)
                # 打印识别出的文本
                if "data" in result and isinstance(result["data"], list):
                    for item in result["data"]:
                        if isinstance(item, list) and len(item) > 1:
                            # 格式: [[box], [text, score]]
                            text = item[1][0]
                            score = item[1][1]
                            print(f"文本: {text} (置信度: {score:.2f})")
                elif "data" in result:
                    print(result["data"])
                print("-" * 30)
            else:
                print(f"\n[测试失败] 后端返回错误: {result.get('data')}")
        else:
            print(f"\n[测试失败] HTTP 状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"\n[测试异常]: {str(e)}")

if __name__ == "__main__":
    test_simple_image_ocr()
