from PIL import Image, ImageDraw
import os

def create_test_image(text, path):
    # 创建一个白色背景的大一点的图片
    img = Image.new('RGB', (800, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # 绘制文字，尝试多次绘制以加粗效果（如果没有字体文件）
    for i in range(5):
        d.text((50 + i, 50), text, fill=(0, 0, 0))
        d.text((50, 50 + i), text, fill=(0, 0, 0))
    img.save(path)
    print(f'Enhanced test image created at {path}')

if __name__ == '__main__':
    create_test_image('PADDLE OCR TEST CONTENT 123456', 'test_ocr_upload_v2.png')
