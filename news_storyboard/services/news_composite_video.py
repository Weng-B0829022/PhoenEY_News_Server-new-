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
import os
from django.conf import settings
import traceback

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

def create_title_clip(title, video_size, duration, font='Arial', fontsize=30, color='white', stroke_color='black', stroke_width=1):
    """創建一個美觀的標題剪輯"""
    # 創建文字剪輯
    txt_clip = TextClip(title, fontsize=fontsize, font=font, color=color, stroke_color=stroke_color, stroke_width=stroke_width)
    
    # 設置位置（右上角，留有一些邊距）
    txt_clip = txt_clip.set_position((video_size[0] - txt_clip.w - 20, 20))
    
    # 設置持續時間
    return txt_clip.set_duration(duration)
def create_video_from_storyboard(story_data, fps=24, total_duration=120, video_size=(1920, 1080)):
    print("开始创建视频从故事板")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    materials_folder = f"video_materials_{timestamp}"
    os.makedirs(materials_folder, exist_ok=True)
    print(f"创建材料文件夹: {materials_folder}")

    clips = []
    audio_clips = []
    temp_audio_files = []
    current_time = 0
    
    try:
        api = VoiceAPI(api_base_ip="216.234.102.170", api_port="10620")
        api.set_model("woman1")
        print("语音 API 初始化完成")
    except Exception as e:
        print(f"初始化语音 API 时发生错误: {str(e)}")
        return None

    for article in story_data:
        try:
            title = article['title']
            print(f"处理文章: {title}")
            for item in article['storyboard']:
                try:
                    sequence = item['sequence']
                    start_time = item['time']['start']
                    end_time = item['time']['end']
                    voiceover_text = item['Voiceover Text']
                    
                    print(f"处理序列 {sequence}: 从 {start_time} 到 {end_time}")
                    
                    original_duration = calculate_duration(start_time, end_time)
                    
                    if current_time < time_to_seconds(start_time):
                        black_duration = time_to_seconds(start_time) - current_time
                        black_clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(black_duration)
                        clips.append(black_clip)
                        current_time += black_duration
                        print(f"添加黑色片段，持续时间: {black_duration}")

                    current_path = os.path.dirname(os.path.abspath(__file__))
                    parent_path = os.path.dirname(os.path.dirname(current_path))
                    generated_images_path = os.path.join(parent_path, 'generated_images')
                    image_path = os.path.join(generated_images_path, f"{title}_image_{sequence}.png")

                    if os.path.exists(image_path):
                        try:
                            new_image_path = os.path.join(materials_folder, f"{title}_image_{sequence}.png")
                            shutil.copy2(image_path, new_image_path)
                            print(f"复制图片到: {new_image_path}")
                            
                            audio = api.tts_generate(voiceover_text)
                            audio_path = os.path.join(materials_folder, f"{title}_audio_{sequence}.mp3")
                            audio.export(audio_path, format="mp3")
                            temp_audio_files.append(audio_path)
                            print(f"生成音频: {audio_path}")
                            
                            audio_clip = AudioFileClip(audio_path)
                            
                            final_duration = max(original_duration, audio_clip.duration)
                            
                            img = ImageClip(new_image_path)
                            img_resized = img.resize(height=video_size[1])
                            if img_resized.w > video_size[0]:
                                img_resized = img.resize(width=video_size[0])
                            clip = img_resized.set_position(('center', 'center')).set_duration(final_duration)
                            
                            clips.append(clip)
                            audio_clips.append(audio_clip)
                            
                            current_time += final_duration
                            print(f"添加图片和音频片段，持续时间: {final_duration}")
                            
                        except Exception as e:
                            print(f"处理图片或音频时发生错误 {image_path}: {str(e)}")
                            print(traceback.format_exc())
                            clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(original_duration)
                            clips.append(clip)
                            current_time += original_duration
                    else:
                        print(f"图片文件不存在: {image_path}")
                        clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(original_duration)
                        clips.append(clip)
                        current_time += original_duration
                except Exception as e:
                    print(f"处理故事板项目时发生错误: {str(e)}")
                    print(traceback.format_exc())
        except Exception as e:
            print(f"处理文章时发生错误: {str(e)}")
            print(traceback.format_exc())

    if current_time < total_duration:
        remaining_duration = total_duration - current_time
        final_black_clip = ColorClip(size=video_size, color=(0,0,0)).set_duration(remaining_duration)
        clips.append(final_black_clip)
        print(f"添加最终黑色片段，持续时间: {remaining_duration}")

    if not clips:
        print("没有可用的片段来创建视频")
        return None

    try:
        print("开始连接视频片段")
        final_clip = concatenate_videoclips(clips)
        if audio_clips:
            print("开始连接音频片段")
            final_audio = concatenate_audioclips(audio_clips)
            if final_audio.duration > final_clip.duration:
                final_audio = final_audio.subclip(0, final_clip.duration)
            final_clip = final_clip.set_audio(final_audio)
        
        final_clip = final_clip.set_fps(fps)
        output_path = os.path.join(materials_folder, f"{title}_final_video.mp4")
        print(f"开始写入最终视频: {output_path}")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", bitrate="8000k")
        print("视频写入完成")
    except Exception as e:
        print(f"生成最终视频时发生错误: {str(e)}")
        print(traceback.format_exc())
        return None
    finally:
        print("清理资源")
        for clip in clips:
            clip.close()
        for audio_clip in audio_clips:
            audio_clip.close()
        if 'final_clip' in locals():
            final_clip.close()
    
    print(f"所有素材和最终视频已保存在文件夹: {materials_folder}")
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

def extract_image_descriptions_from_storyboard(file_path, index):
    print(f"Processing file: {file_path}")
    # 開啟並讀取 JSON 檔案
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # 檢查 index 是否有效
    if index < 0 or index >= len(data['articles']):
        print(f"錯誤：無效的 index {index}。文章總數：{len(data['articles'])}")
        return None

    # 只處理指定 index 的文章
    article = data['articles'][index]
    storyboard = article['storyboard']
    parsed_storyboard = parse_storyboard(storyboard)
    
    # 創建包含標題和解析後的故事板的物件
    article_data = {
        "title": article['title'],
        "storyboard": parsed_storyboard
    }
    
    print(f"----> Processed article: {article_data}")
    
    return [article_data] 
def run_news_composite_video(index):
    try:
        file_path = os.path.join(settings.BASE_DIR, 'derivative_articles_and_storyboards.json')
        print(f"使用文件路径: {file_path}")
        
        story_data = extract_image_descriptions_from_storyboard(file_path, index)
        if not story_data:
            print("无法从故事板提取数据")
            return {"status": "error", "message": "无法从故事板提取数据", "video_path": None}

        initial_video = create_video_from_storyboard(story_data)
        
        if initial_video:
            print(f"初始视频保存在：{initial_video}")
            
            background_image = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background2.webp")
            output_video = 'final_output_video.mp4'
            
            try:
                overlay_video_on_image(background_image, initial_video, output_video)
                print(f"最终视频（包含背景叠加和音频）保存在：{output_video}")
                
                if os.path.exists(output_video):
                    return {
                        "status": "success",
                        "message": "视频生成成功",
                        "video_path": output_video
                    }
                else:
                    return {
                        "status": "error",
                        "message": "最终视频文件未找到",
                        "video_path": initial_video
                    }
            except Exception as e:
                print(f"视频叠加过程中发生错误：{str(e)}")
                traceback.print_exc()
                return {
                    "status": "error",
                    "message": f"视频叠加过程中发生错误: {str(e)}",
                    "video_path": initial_video
                }
        else:
            print("无法生成初始视频")
            return {"status": "error", "message": "无法生成初始视频", "video_path": None}
    except Exception as e:
        print(f"视频生成过程中发生未预期的错误：{str(e)}")
        traceback.print_exc()
        return {"status": "error", "message": f"发生未预期的错误: {str(e)}", "video_path": None}

if __name__ == '__main__':
    run_news_composite_video()
    