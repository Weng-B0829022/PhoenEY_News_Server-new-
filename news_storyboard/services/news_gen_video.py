import re
import json

import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageClip
import os

def create_video_from_storyboard(story_data):
    clips = []
    for article in story_data:
        title = article['title']
        for item in article['storyboard']:
            sequence = item['sequence']
            start_time = item['time']['start']
            end_time = item['time']['end']
            
            # 計算持續時間（秒）
            duration = calculate_duration(start_time, end_time)
            
            if 'Image' in item:
                image_path = f"{title}_image_{sequence}.jpg"
                clip = ImageClip(image_path).set_duration(duration)
            elif 'Video' in item:
                video_path = f"{title}_video_{sequence}.mp4"
                clip = VideoFileClip(video_path).subclip(0, duration)
            
            clips.append(clip)
    
    final_clip = concatenate_videoclips(clips)
    output_path = f"{title}_final_video.mp4"
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    return output_path

def calculate_duration(start_time, end_time):
    start = sum(x * int(t) for x, t in zip([3600, 60, 1], start_time.split(':')[0:3]))
    end = sum(x * int(t) for x, t in zip([3600, 60, 1], end_time.split(':')[0:3]))
    return end - start



def clean_text(text):
    # 去除所有空格和換行符
    return ''.join(text.split())

def parse_storyboard(storyboard_text):
    # 使用之前定義的 parse_storyboard 函數的邏輯
    cleaned_text = clean_text(storyboard_text)
    pattern = r'(\d+)((\d{2}:\d{2}:\d{2},\d{3})-->(\d{2}:\d{2}:\d{2},\d{3}))(Image|Video):(.+?)VoiceoverText:"(.+?)"'
    matches = re.finditer(pattern, cleaned_text)

    result = []
    for match in matches:
        item = {
            "sequence": match.group(1),
            "time": {
                "start": match.group(3),
                "end": match.group(4)
            },
            match.group(5): match.group(6),
            "Voiceover Text": match.group(7)
        }
        result.append(item)

    return result

def extract_image_descriptions_from_storyboard(file_path):
    print(file_path)
    # 開啟並讀取 JSON 檔案
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # 提取每篇文章的內容
    articles_data = []
    for article in data['articles']:
        storyboard = article['storyboard']
        parsed_storyboard = parse_storyboard(storyboard)
        
        # 創建包含標題和解析後的故事板的物件
        article_data = {
            "title": article['title'],
            "storyboard": parsed_storyboard
        }
        articles_data.append(article_data)
        
        print(f"----> Processed article: {articles_data}")
    
    return articles_data

def run_news_gen_video():
    file_path = 'derivative_articles_and_storyboards.json'
    story_data = extract_image_descriptions_from_storyboard(file_path)
    output_video = create_video_from_storyboard(story_data)
    print(f"生成的視頻保存在：{output_video}")
    return output_video

if __name__ == '__main__':
    run_news_gen_video()