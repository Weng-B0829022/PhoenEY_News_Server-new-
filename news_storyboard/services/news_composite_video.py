import re
import json
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageClip, ColorClip
import os
from gtts import gTTS
from pydub import AudioSegment
from moviepy.editor import *
from voice_api import VoiceAPI
import shutil
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image
from django.conf import settings
from .news_gen_img import run_news_gen_img

def overlay_video_on_image(background_path, video_path, output_path):
    # 讀取背景圖像
    background = ImageClip(background_path)
    
    # 讀取視頻（包括音頻）
    video = VideoFileClip(video_path)
    
    # 定義視頻在背景中的位置（順序：左上，右上，右下，左下）
    pts_dst = np.array([
        [234, 265],  # 左上
        [844, 265],  # 右上
        [844, 635],  # 右下
        [234, 635]   # 左下
    ], dtype="float32")
    
    # 計算視頻原始尺寸
    video_width, video_height = int(video.w), int(video.h)
    
    # 定義視頻原始的四個角點
    pts_src = np.array([
        [0, 0],
        [video_width - 1, 0],
        [video_width - 1, video_height - 1],
        [0, video_height - 1]
    ], dtype="float32")
    
    # 計算透視變換矩陣
    M = cv2.getPerspectiveTransform(pts_src, pts_dst)
    
    def transform_frame(frame):
        # 對每一幀應用透視變換
        warped = cv2.warpPerspective(frame, M, (background.w, background.h))
        # 創建遮罩
        mask = np.zeros((background.h, background.w, 3), dtype=np.uint8)
        cv2.fillConvexPoly(mask, pts_dst.astype(int), (255, 255, 255))
        # 應用遮罩
        result = np.where(mask == 255, warped, background.get_frame(0))
        return result
    
    # 創建變換後的視頻剪輯
    transformed_video = video.fl_image(transform_frame)
    
    # 創建合成視頻
    final_video = CompositeVideoClip([background.set_duration(video.duration), transformed_video])
    
    # 設置音頻
    final_video = final_video.set_audio(video.audio)
    
    # 寫入最終視頻
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    # 清理資源
    video.close()
    background.close()
    final_video.close()

def time_to_seconds(time_str):
    parts = time_str.replace(',', ':').split(':')
    if len(parts) != 4:
        print(f"警告：時間格式不正確 - {time_str}")
        return 0
    hours, minutes, seconds, milliseconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000

def calculate_duration(start_time, end_time):
    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)
    duration = end_seconds - start_seconds
    if duration < 0:
        print(f"警告：計算出的持續時間為負值 - 開始：{start_time}，結束：{end_time}")
        return 0
    return duration

def clean_text(text):
    return ''.join(text.split())

def parse_storyboard(storyboard_text):
    cleaned_text = clean_text(storyboard_text)
    pattern = r'(\d+)((\d{2}:\d{2}:\d{2},\d{3})-->(\d{2}:\d{2}:\d{2},\d{3}))(Image|Video):(.+?)VoiceoverText:"(.+?)"'
    matches = re.finditer(pattern, cleaned_text)

    result = []
    for match in matches:
        start_time = match.group(3)
        end_time = match.group(4)
        
        if not (start_time.startswith("00:") and end_time.startswith("00:")):
            print(f"警告：檢測到不正確的時間格式。開始時間：{start_time}，結束時間：{end_time}")
        
        item = {
            "sequence": match.group(1),
            "time": {
                "start": start_time,
                "end": end_time
            },
            match.group(5): match.group(6),
            "Voiceover Text": match.group(7)
        }
        result.append(item)

    if not result:
        print("警告：沒有找到匹配的 storyboard 項目")

    return result

def extract_image_descriptions_from_storyboard(file_path, index):
    print(f"Processing file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    if index < 0 or index >= len(data['articles']):
        print(f"錯誤：無效的 index {index}。文章總數：{len(data['articles'])}")
        return None

    article = data['articles'][index]
    storyboard = article['storyboard']
    parsed_storyboard = parse_storyboard(storyboard)
    
    article_data = {
        "title": article['title'],
        "storyboard": parsed_storyboard
    }
    
    print(f"----> Processed article: {article_data}")
    
    return article_data

def create_video_from_storyboard(story_data, image_urls, fps=24, total_duration=120, video_size=(1920, 1080)):
    print("開始創建視頻...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    materials_folder = f"video_materials_{timestamp}"
    os.makedirs(materials_folder, exist_ok=True)
    print(f"創建材料文件夾: {materials_folder}")

    clips = []
    audio_clips = []
    temp_audio_files = []
    current_time = 0
    
    api = VoiceAPI(api_base_ip="216.234.102.170", api_port="10620")
    api.set_model("woman1")
    
    title = story_data['title']
    total_items = len(story_data['storyboard'])
    print(f"處理文章: {title}")
    print(f"總片段數: {total_items}")

    for i, item in enumerate(story_data['storyboard']):
        print(f"\n處理片段 {i+1}/{total_items}")
        sequence = item['sequence']
        start_time = item['time']['start']
        end_time = item['time']['end']
        voiceover_text = item['Voiceover Text']
        image_url = image_urls[i]
        
        original_duration = calculate_duration(start_time, end_time)
        
        if current_time < time_to_seconds(start_time):
            black_duration = time_to_seconds(start_time) - current_time
            print(f"添加黑色片段，持續時間: {black_duration:.2f}秒")
            black_clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(black_duration)
            clips.append(black_clip)
            current_time += black_duration

        try:
            print(f"下載圖片: {image_url}")
            response = requests.get(image_url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            
            new_image_path = os.path.join(materials_folder, f"{title}_image_{sequence}.png")
            img.save(new_image_path)
            print(f"圖片保存至: {new_image_path}")
            
            print("生成音頻...")
            audio = api.tts_generate(voiceover_text)
            audio_path = os.path.join(materials_folder, f"{title}_audio_{sequence}.mp3")
            audio.export(audio_path, format="mp3")
            temp_audio_files.append(audio_path)
            print(f"音頻保存至: {audio_path}")
            
            audio_clip = AudioFileClip(audio_path)
            
            final_duration = max(original_duration, audio_clip.duration)
            print(f"片段持續時間: {final_duration:.2f}秒")
            
            print("創建視頻片段...")
            img_clip = ImageClip(new_image_path)
            img_resized = img_clip.resize(height=video_size[1])
            if img_resized.w > video_size[0]:
                img_resized = img_clip.resize(width=video_size[0])
            clip = img_resized.set_position(('center', 'center')).set_duration(final_duration)
            
            clips.append(clip)
            audio_clips.append(audio_clip)
            
            current_time += final_duration
            
        except Exception as e:
            print(f"處理片段時發生錯誤: {str(e)}")
            clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(original_duration)
            clips.append(clip)
            current_time += original_duration

    if current_time < total_duration:
        remaining_duration = total_duration - current_time
        print(f"添加最終黑色片段，持續時間: {remaining_duration:.2f}秒")
        final_black_clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(remaining_duration)
        clips.append(final_black_clip)
    
    if not clips:
        print("沒有可用的片段來創建視頻")
        return None

    try:
        print("\n開始合成最終視頻...")
        final_clip = concatenate_videoclips(clips)
        if audio_clips:
            print("合成音頻...")
            final_audio = concatenate_audioclips(audio_clips)
            if final_audio.duration > final_clip.duration:
                final_audio = final_audio.subclip(0, final_clip.duration)
            final_clip = final_clip.set_audio(final_audio)
        
        final_clip = final_clip.set_fps(fps)
        output_path = os.path.join(materials_folder, f"{title}_final_video.mp4")
        print(f"正在寫入最終視頻: {output_path}")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", bitrate="8000k")
        print("視頻創建完成！")
    except Exception as e:
        print(f"生成視頻時發生錯誤: {str(e)}")
        return None
    finally:
        print("清理資源...")
        for clip in clips:
            clip.close()
        for audio_clip in audio_clips:
            audio_clip.close()
        if 'final_clip' in locals():
            final_clip.close()
    
    print(f"所有素材和最終視頻已保存在資料夾: {materials_folder}")
    return output_path


def run_news_composite_video(index):
    print(f"開始為索引 {index} 的文章生成視頻...")

    file_path = os.path.join(settings.BASE_DIR, 'derivative_articles_and_storyboards.json')
    
    # 使用 run_news_gen_img 函數獲取圖片 URL
    image_urls = run_news_gen_img(index)
    
    # 獲取故事數據
    story_data = extract_image_descriptions_from_storyboard(file_path, index)
    
    if not story_data or not image_urls:
        print("無法獲取故事數據或生成圖片 URL")
        return None
    
    # 創建初始視頻
    initial_video = create_video_from_storyboard(story_data, image_urls)
    
    if initial_video:
        # 新增的視頻疊加步驟
        background_image = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background2.webp")
        output_video = 'final_output_video.mp4'
        
        try:
            overlay_video_on_image(background_image, initial_video, output_video)
            print(f"視頻生成完成。最終視頻保存在：{output_video}")
            return output_video
        except Exception as e:
            print(f"視頻疊加過程中發生錯誤：{str(e)}")
            return initial_video
    else:
        print("無法生成視頻")
        return None

if __name__ == '__main__':
    index = 0  # 假設我們要處理第一篇文章
    final_video = run_news_composite_video(index)
    if final_video:
        print(f"成功生成視頻：{final_video}")
    else:
        print("視頻生成失敗")