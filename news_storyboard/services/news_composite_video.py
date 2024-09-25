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
from django.conf import settings

def overlay_video_on_image(background_path, video_path, output_path):
    # 讀取背景圖像
    background = ImageClip(background_path)
    
    # 讀取視頻（包括音頻）
    video = VideoFileClip(video_path)
    
    # 定義視頻在背景中的位置（順序：左上，右上，右下，左下）
    pts_dst = np.array([
        [410, 274],  # 左上
        [996, 140],  # 右上
        [995, 685],  # 右下
        [410, 649]   # 左下
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

def create_video_from_storyboard(article_data, fps=24, total_duration=120, video_size=(1920, 1080)):
    clips = []
    audio_clips = []
    temp_audio_files = []
    current_time = 0
    
    api = VoiceAPI(api_base_ip="216.234.102.170", api_port="10620")
    api.set_model("woman1")
    
    title = article_data['title']
    for item in article_data['storyboard']:
        sequence = item['sequence']
        start_time = item['time']['start']
        end_time = item['time']['end']
        voiceover_text = item['Voiceover Text']
        
        original_duration = calculate_duration(start_time, end_time)
        
        if current_time < time_to_seconds(start_time):
            black_duration = time_to_seconds(start_time) - current_time
            black_clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(black_duration)
            clips.append(black_clip)
            current_time += black_duration
        
        image_path = f"{title}_image_{sequence}.png"
        if os.path.exists(image_path):
            try:
                # Generate audio
                audio = api.tts_generate(voiceover_text)
                audio_path = f"{title}_audio_{sequence}.mp3"
                audio.export(audio_path, format="mp3")
                temp_audio_files.append(audio_path)
                
                # Read audio
                audio_clip = AudioFileClip(audio_path)
                
                # Determine final duration
                final_duration = max(original_duration, audio_clip.duration)
                
                # Create image clip
                img = ImageClip(image_path)
                img_resized = img.resize(height=video_size[1])
                if img_resized.w > video_size[0]:
                    img_resized = img.resize(width=video_size[0])
                clip = img_resized.set_position(('center', 'center')).set_duration(final_duration)
                
                clips.append(clip)
                audio_clips.append(audio_clip)
                
                current_time += final_duration
                
            except Exception as e:
                print(f"Unable to process image or audio {image_path}: {str(e)}")
                clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(original_duration)
                clips.append(clip)
                current_time += original_duration
        else:
            print(f"Image file does not exist: {image_path}")
            clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(original_duration)
            clips.append(clip)
            current_time += original_duration
    
    # If total duration is less than expected, add black clip
    if current_time < total_duration:
        remaining_duration = total_duration - current_time
        final_black_clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(remaining_duration)
        clips.append(final_black_clip)
    
    if not clips:
        print("No clips available to create video")
        return None

    try:
        final_clip = concatenate_videoclips(clips)
        if audio_clips:
            final_audio = concatenate_audioclips(audio_clips)
            # If audio duration is longer than video, trim the audio
            if final_audio.duration > final_clip.duration:
                final_audio = final_audio.subclip(0, final_clip.duration)
            final_clip = final_clip.set_audio(final_audio)
        
        final_clip = final_clip.set_fps(fps)
        output_path = f"{title}_final_video.mp4"
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", bitrate="8000k")
    except Exception as e:
        print(f"Error occurred while generating video: {str(e)}")
        return None
    finally:
        # Clean up resources
        for clip in clips:
            clip.close()
        for audio_clip in audio_clips:
            audio_clip.close()
        if 'final_clip' in locals():
            final_clip.close()
        
        # Delete temporary audio files
        for audio_file in temp_audio_files:
            try:
                os.remove(audio_file)
            except Exception as e:
                print(f"Unable to delete temporary audio file {audio_file}: {str(e)}")
    
    return output_path

def time_to_seconds(time_str):
    parts = time_str.replace(',', ':').split(':')
    if len(parts) != 4:
        print(f"警告：時間格式不正確 - {time_str}")
        return 0
    hours, minutes, seconds, milliseconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000

def calculate_duration(start_time, end_time):
    def time_to_seconds(time_str):
        # 分割時間字符串
        parts = time_str.replace(',', ':').split(':')
        if len(parts) != 4:
            print(f"警告：時間格式不正確 - {time_str}")
            return 0

        hours, minutes, seconds, milliseconds = parts
        
        # 轉換為秒
        total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
        return total_seconds

    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)

    duration = end_seconds - start_seconds
    if duration < 0:
        print(f"警告：計算出的持續時間為負值 - 開始：{start_time}，結束：{end_time}")
        return 0

    return duration



def clean_text(text):
    # 去除所有空格和換行符
    return ''.join(text.split())

def parse_storyboard(storyboard_text):
    cleaned_text = clean_text(storyboard_text)
    # 修改正則表達式以確保匹配完整的時間格式
    pattern = r'(\d+)((\d{2}:\d{2}:\d{2},\d{3})-->(\d{2}:\d{2}:\d{2},\d{3}))(Image|Video):(.+?)VoiceoverText:"(.+?)"'
    matches = re.finditer(pattern, cleaned_text)

    result = []
    for match in matches:
        start_time = match.group(3)
        end_time = match.group(4)
        
        # 檢查時間格式是否正確
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

def extract_image_descriptions_from_storyboard(file_path, article_index):
    print(file_path)
    # Open and read the JSON file
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Extract content for the specified article
    articles_data = []
    if 0 <= article_index < len(data['articles']):
        article = data['articles'][article_index]
        storyboard = article['storyboard']
        parsed_storyboard = parse_storyboard(storyboard)
        
        # Create an object containing the title and parsed storyboard
        article_data = {
            "title": article['title'],
            "storyboard": parsed_storyboard
        }
        articles_data.append(article_data)
        
        print(f"----> Processed article: {article_data}")
    else:
        print(f"Error: Invalid article index. Index should be between 0 and {len(data['articles']) - 1}")
    
    return articles_data

def run_news_composite_video(index):
    file_path = os.path.join(settings.BASE_DIR, 'derivative_articles_and_storyboards.json')
    story_data = extract_image_descriptions_from_storyboard(file_path, index)
    initial_video = create_video_from_storyboard(story_data)
    
    if initial_video:
        print(f"初始視頻保存在：{initial_video}")
        
        # 新增的視頻疊加步驟
        background_image = 'background.webp'
        output_video = 'final_output_video.mp4'
        
        try:
            overlay_video_on_image(background_image, initial_video, output_video)
            print(f"最終視頻（包含背景疊加和音頻）保存在：{output_video}")
            return output_video
        except Exception as e:
            print(f"視頻疊加過程中發生錯誤：{str(e)}")
            return initial_video
    else:
        print("無法生成初始視頻")
        return None

if __name__ == '__main__':
    run_news_composite_video()