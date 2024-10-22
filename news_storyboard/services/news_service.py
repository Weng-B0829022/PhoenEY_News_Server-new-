# news_storyboard/services/news_service.py

from .newsapi import run_newsapi
from .news_gen import run_news_gen
from .news_gen_img import run_news_gen_img
from .news_gen_voice_and_video import run_news_gen_voice_and_video
from .upload_to_drive import upload_to_drive
import os 
from django.conf import settings
from .create_scene import create_videos_from_images_and_audio
from .storyboard_manager import StoryboardManager
import shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import random
import string
from concurrent.futures import ThreadPoolExecutor
from .config import HALF_CONFIG, FULL_CONFIG

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
    
def execute_news_gen_img(manager, storyboard_object, random_id, scene_coordinates):
    try:
        result = run_news_gen_img(manager, storyboard_object, random_id, scene_coordinates)
        
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
    
def execute_news_gen_voice_and_video(manager, storyboard_object, random_id, avatar_coordinates):
    try:
        print(storyboard_object)
        audios_path = run_news_gen_voice_and_video(manager, storyboard_object, random_id, avatar_coordinates)

        return audios_path
    except Exception as e:
        return [""]  # 返回一个包含空字符串的列表，表示出错

def combine_media(story_object):
    def generate_random_id(length=10):
        """生成指定長度的隨機字母數字字符串"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def setup_image(manager, random_id, image_name, top_left, top_right, bottom_right, bottom_left, z_index, copy_image=True):
        # Set the image configuration
        manager.set_image_config(image_name, top_left, top_right, bottom_right, bottom_left, z_index)
        
        # Add the configuration to all paragraphs
        manager.add_config_to_all_paragraphs()
        
        if copy_image:
            # Copy the background image to the output directory
            source_path = os.path.join(settings.BASE_DIR, image_name)
            destination_path = os.path.join(settings.BASE_DIR, 'generated', str(random_id), image_name)
            shutil.copy2(source_path, destination_path)

    story_object['storyboard'] = story_object['storyboard'][:1]
    random_id = generate_random_id()#每次生成給予專屬id
    #移除generated資料夾
    remove_generated_folder()
    manager = execute_storyboard_manager(os.path.join(settings.MEDIA_ROOT, 'generated', random_id), random_id, story_object)
    
    config = HALF_CONFIG if manager.storyboard['avatarType'] == 'half' else FULL_CONFIG
    #設定影片尺寸
    canvas_size = config['canvas_size']
    # 定義圖片在影片各個scene中的坐標
    scene_place_coordinates = config['scene_place_coordinates']
    #avatar位置
    avatar_place_coordinates = config['avatar_place_coordinates']
    #欲裁減avatar位置x, y, w, h
    crop_coords = config['crop_coords']
    


    with ThreadPoolExecutor(max_workers=2) as executor:  
        future_img = executor.submit(execute_news_gen_img, manager, manager.storyboard, random_id, scene_place_coordinates) 
        future_voice_and_video = executor.submit(execute_news_gen_voice_and_video, manager, manager.storyboard, random_id, avatar_place_coordinates)

    # 獲取結果 
    try: # 選擇配置
        
        #設定背景
        setup_image(manager, 
                    random_id, 
                    config['background']['file'], 
                    config['background']['top_left'],
                    config['background']['top_right'],
                    config['background']['bottom_right'],
                    config['background']['bottom_left'],
                    config['background']['z_index'], 
                    copy_image=True)
        #設定logo
        #setup_image(manager, random_id, "logo.png", top_left=(40, 40), width=100, height=100, z_index=100, copy_image=True)
        #設定標題
        #setup_image(manager, random_id, "title.png", top_left=(140, 40), width=400, height=100, z_index=100, copy_image=True)

        #標題文字生成
        title_img_path = text_to_image(
            manager.storyboard['title'], 
            os.path.join(settings.BASE_DIR, 'font', "NotoSansTC-Bold.ttf"),
            os.path.join(settings.BASE_DIR, 'generated', str(random_id), "title.png"),
            padding=5
        )
        #設定title
        setup_image(manager, random_id, 
                    "title.png", 
                    config['title']['top_left'],
                    config['title']['top_right'],
                    config['title']['bottom_right'],
                    config['title']['bottom_left'],
                    config['title']['z_index'], 
                    copy_image=False)
        img_binary, image_urls = future_img.result()
        audios_path = future_voice_and_video.result()  # 等待語音生成完成，但不使用其結果
        video_paths = create_videos_from_images_and_audio(manager, canvas_size, crop_coords)
        #return video_paths.split('/')[1]
        return random_id, image_urls
    except Exception as e:
        print(f"Error in image or voice generation: {str(e)}")
        return None
    #設定背景
    

def execute_storyboard_manager(file_path, random_id, initial_storyboard=None):
    return StoryboardManager(file_path, random_id, initial_storyboard)

def text_to_image(text, font_path, output_path, font_size=32, padding=0, bg_color=(255, 255, 255, 0), text_color=(255, 255, 255, 255)):
    # 使用絕對路徑
    absolute_output_path = os.path.abspath(output_path)
    
    # 創建完整的目錄結構
    os.makedirs(os.path.dirname(absolute_output_path), exist_ok=True)
    
    # 檢查字體文件是否存在
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")

    # 設置字體
    try:
        # Load a bold font if available
        font = ImageFont.truetype(font_path, font_size)
        print("Font loaded successfully")
    except Exception as e:
        print(f"Error loading font: {str(e)}")
        raise

    # 獲取文字大小
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    print(f"Text dimensions: {text_width}x{text_height}")

    # 創建一個比文字稍大的 PIL 圖像
    image_width = text_width + 2 * padding
    image_height = text_height + 2 * padding
    pil_image = Image.new('RGBA', (image_width, image_height), bg_color)
    print(f"Image created with dimensions: {image_width}x{image_height}")

    # 創建一個可以在 PIL 圖像上繪圖的對象
    draw = ImageDraw.Draw(pil_image)

    # 在圖像上繪製文字（位置考慮內邊距）
    # Adjust the text position to move it upwards
    text_y_position = padding - bbox[1]  # Adjust by the top of the bounding box
    draw.text((padding, text_y_position), text, font=font, fill=text_color)
    print("Text drawn on image")

    # 直接保存 PIL 图像
    try:
        pil_image.save(absolute_output_path, format='PNG')
        print(f"Image saved successfully to: {absolute_output_path}")
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        raise
    return absolute_output_path, image_width, image_height

def execute_upload_to_drive(random_id):
    file_id = upload_to_drive(random_id)
    return {"status":"success", "file_id":file_id}

def remove_generated_folder():
    generated_path = os.path.join(settings.BASE_DIR, 'generated')
    
    if os.path.exists(generated_path):
        try:
            shutil.rmtree(generated_path)
            print(f"'generated' folder has been successfully removed from {settings.BASE_DIR}")
        except Exception as e:
            print(f"Error occurred while trying to remove 'generated' folder: {e}")
    else:
        print(f"'generated' folder does not exist in {settings.BASE_DIR}")
