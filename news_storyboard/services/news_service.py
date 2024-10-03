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
    
def combine_media(manager, custom_setting):
    #manager.custom_setting(custom_setting)
    #manager.set_background_config('background.webp', width=1024, height=1024)
    #manager.add_background_to_all_paragraphs()#設定背景
    #shutil.copy2(os.path.join(settings.BASE_DIR, 'background.webp'), os.path.join(settings.BASE_DIR, 'generated', str(random_id), 'background.webp'))


    video_paths = create_videos_from_images_and_audio(manager)
    #return video_paths.split('/')[1]

def execute_storyboard_manager(file_path, random_id, initial_storyboard=None):
    return StoryboardManager(file_path, random_id, initial_storyboard)

