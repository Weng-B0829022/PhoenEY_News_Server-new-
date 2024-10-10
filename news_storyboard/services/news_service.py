# news_storyboard/services/news_service.py

from .newsapi import run_newsapi
from .news_gen import run_news_gen
from .news_gen_img import run_news_gen_img
from .news_gen_voice_and_video import run_news_gen_voice_and_video
import base64
import io
from pydub import AudioSegment
import re 
import os 
from django.conf import settings
from .create_scene import create_videos_from_images_and_audio
from .storyboard_manager import StoryboardManager
import shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

def execute_newsapi(keyword):
    try:
        result = run_newsapi(keyword)
        return {"status": "success", "message": f"NewsAPI execution completed for keyword: {keyword}", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def execute_news_gen():
    try:
        result = run_news_gen()
        return {"status": "success", "message": "News generation completed", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def execute_news_gen_img(manager, storyboard_object, random_id):
    try:
        result = run_news_gen_img(manager, storyboard_object, random_id)
        
        # 处理结果，分离 URL 和图片数据
        processed_result = []
        img_binary = []  # 存储所有图片的二进制数据
        
        for item in result:
            url, img_data = item
            # 直接存储二进制数据，不进行 base64 编码
            img_binary.append(img_data)
            processed_result.append({
                "url": url,
            })
        
        # 如果没有处理任何图片，设置一个默认值
        if not img_binary:
            img_binary = [b""]  # 空的字节串作为默认值
        
        return (img_binary, processed_result)
    except Exception as e:
        print(str(e))
        return (None, {"status": "error", "message": str(e)})
    
def execute_news_gen_voice_and_video(manager, storyboard_object, random_id):
    try:
        audios_path = run_news_gen_voice_and_video(manager, storyboard_object, random_id)

        return audios_path
    except Exception as e:
        return [""]  # 返回一个包含空字符串的列表，表示出错
    
def combine_media(manager, random_id, custom_setting):
    #manager.custom_setting(custom_setting)

    #設定背景圖片座標
    manager.set_image_config("background.webp", top_left=(0, 0), width=1024, height=1024, z_index=-1)
    manager.add_config_to_all_paragraphs()#移動背景圖片
    shutil.copy2(os.path.join(settings.BASE_DIR, 'background.webp'), os.path.join(settings.BASE_DIR, 'generated', str(random_id), 'background.webp'))
    
    #設定logo座標
    manager.set_image_config("logo.png", top_left=(40, 40), width=100, height=100, z_index=100)
    manager.add_config_to_all_paragraphs()#移動logo
    shutil.copy2(os.path.join(settings.BASE_DIR, 'logo.png'), os.path.join(settings.BASE_DIR, 'generated', str(random_id), 'logo.png'))

    #標題文字
    #chinese_text = "你好"#manager.storyboard['title']
    #print(text_to_image(chinese_text, os.path.join(settings.BASE_DIR,"LXGWWenKaiMonoTC-Bold.ttf"), os.path.join(settings.BASE_DIR, 'title.png'), padding=5))
    #manager.set_image_config("title.png", top_left=(140, 40), width=400, height=100, z_index=100)
    #manager.add_config_to_all_paragraphs()


    video_paths = create_videos_from_images_and_audio(manager)
    #return video_paths.split('/')[1]

def execute_storyboard_manager(file_path, random_id, initial_storyboard=None):
    return StoryboardManager(file_path, random_id, initial_storyboard)

def text_to_image(text, font_path, output_path, font_size=32, padding=5, bg_color=(255, 255, 255, 0), text_color=(0, 0, 0, 255)):
    print(f"Starting text_to_image function")
    print(f"Text: {text}")
    print(f"Font path: {font_path}")
    print(f"Output path: {output_path}")

    # 檢查字體文件是否存在
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")

    # 設置字體
    try:
        font = ImageFont.truetype(font_path, font_size)
        print("Font loaded successfully")
    except Exception as e:
        print(f"Error loading font: {str(e)}")
        raise

    # 獲取文字大小
    left, top, right, bottom = font.getbbox(text)
    text_width = right - left
    text_height = bottom - top
    print(f"Text dimensions: {text_width}x{text_height}")

    # 創建一個比文字稍大的 PIL 圖像
    image_width = text_width + 2 * padding
    image_height = text_height + 2 * padding
    pil_image = Image.new('RGBA', (image_width, image_height), bg_color)
    print(f"Image created with dimensions: {image_width}x{image_height}")

    # 創建一個可以在 PIL 圖像上繪圖的對象
    draw = ImageDraw.Draw(pil_image)

    # 在圖像上繪製文字（位置考慮內邊距）
    draw.text((padding, padding), text, font=font, fill=text_color)
    print("Text drawn on image")

    # 將 PIL 圖像轉換為 OpenCV 格式
    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGRA)

    # 確保輸出目錄存在

    print(f"Output directory created/verified: {os.path.dirname(output_path)}")

    # 保存圖像
    try:
        cv2.imwrite(output_path, opencv_image)
        print(f"Image saved successfully to: {output_path}")
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        raise

    # 驗證文件是否確實被創建
    if os.path.exists(output_path):
        print(f"File exists at: {output_path}")
        print(f"File size: {os.path.getsize(output_path)} bytes")
    else:
        print(f"File does not exist at: {output_path}")

    return output_path, image_width, image_height