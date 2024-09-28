# news_storyboard/services/news_service.py

from .newsapi import run_newsapi
from .news_gen import run_news_gen
from .news_gen_img import run_news_gen_img
from .news_gen_voice import run_news_gen_voice
import base64
import io
from pydub import AudioSegment
import re 
import os 
from django.conf import settings
from .create_scene import create_videos_from_images_and_audio

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
    
def execute_news_gen_img(storyboard_object):
    try:
        result = run_news_gen_img(storyboard_object)
        
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
    
def execute_news_gen_voice(storyboard_object):
    try:
        audio_binary = run_news_gen_voice(storyboard_object)

        return audio_binary
    except Exception as e:
        return [""]  # 返回一个包含空字符串的列表，表示出错
    
def combine_media(storyboard, img_binary, audio_byteIO):
    video_paths = create_videos_from_images_and_audio(img_binary, audio_byteIO, os.path.join(settings.MEDIA_ROOT, 'generated_video/'))
    print(video_paths)
    return 

