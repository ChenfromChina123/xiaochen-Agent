from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image(text, path):
    # 创建一个白色背景的图片
    img = Image.new('RGB', (400, 100), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # 使用默认字体（在没有安装字体的情况下）
    d.text((10, 40), text, fill=(0, 0, 0))
    img.save(path)
    print(f'Test image created at {path}')

if __name__ == '__main__':
    create_test_image('Hello OCR Test 123', 'test_ocr_upload.png')
