import cv2
import numpy as np
import os
from pydub import AudioSegment
from io import BytesIO
from tqdm import tqdm
from django.conf import settings
import random
import string

def create_videos_from_images_and_audio(storyboard, img_binary_list, audio_byteIO_list, output_folder=os.path.join(settings.MEDIA_ROOT, 'static/')):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video_paths = []
    random_id = generate_random_id()
    # 讀取背景圖片
    background = cv2.imread(os.path.join(settings.MEDIA_ROOT, 'background.webp'))
    if background is None:
        raise ValueError("無法讀取背景圖片 './background.webp'")

    # 定義目標區域的四個角點
    target_points = np.float32([
        [234, 265],  # 左上
        [844, 265],  # 右上
        [844, 635],  # 右下
        [234, 635]   # 左下
    ])

    # 使用tqdm創建總體進度條
    for index, (img_binary, audio_byteIO) in enumerate(tqdm(list(zip(img_binary_list, audio_byteIO_list)), desc="處理視頻")):
        print(f"\n開始處理第 {index+1} 個視頻")

        # 讀取圖片
        img_array = np.frombuffer(img_binary, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        print("圖片讀取完成")

        # 獲取圖片尺寸
        height, width = img.shape[:2]

        # 定義原圖的四個角點
        source_points = np.float32([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ])

        # 計算透視變換矩陣
        M = cv2.getPerspectiveTransform(source_points, target_points)

        # 進行透視變換
        warped = cv2.warpPerspective(img, M, (background.shape[1], background.shape[0]))

        # 創建遮罩
        mask = np.zeros(background.shape[:2], dtype=np.uint8)
        cv2.fillConvexPoly(mask, target_points.astype(int), 255)

        # 將變換後的圖片疊加到背景上
        background_copy = background.copy()
        background_copy[mask != 0] = warped[mask != 0]

        print("圖片疊加到背景完成")

        # 讀取音頻
        audio = AudioSegment.from_file(BytesIO(audio_byteIO))
        audio_duration = len(audio) / 1000  # 轉換為秒
        print(f"音頻讀取完成，持續時間: {audio_duration:.2f} 秒")

        # 設置視頻參數
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        video_path = os.path.join(output_folder, f'video_{random_id}_{index}.mp4')
        out = cv2.VideoWriter(video_path, fourcc, fps, (background.shape[1], background.shape[0]))

        # 計算需要的幀數
        total_frames = int(audio_duration * fps)

        # 創建視頻
        print("開始創建視頻幀")
        for _ in tqdm(range(total_frames), desc="創建視頻幀", leave=False):
            out.write(background_copy)

        out.release()
        print("視頻幀創建完成")

        # 合併音頻和視頻
        temp_audio_path = os.path.join(output_folder, f'temp_audio_{random_id}_{index}.wav')
        audio.export(temp_audio_path, format="wav")
        print("音頻導出完成")


        final_video_path = os.path.join(output_folder, f'{random_id}_{index}.mp4')
        print("開始合併音頻和視頻")
        os.system(f"ffmpeg -i {video_path} -i {temp_audio_path} -c:v copy -c:a aac {final_video_path}")
        print("音頻視頻合併完成")
        
        # 清理臨時文件
        os.remove(video_path)
        os.remove(temp_audio_path)
        print("臨時文件清理完成")

        video_paths.append(final_video_path)

    print("\n所有視頻處理完成！")

    
    # 合併所有視頻
    print("\n開始合併所有視頻")
    final_output_path = os.path.join(output_folder, f'{random_id}.mp4')
    
    # 按數字順序排序視頻路徑
    sorted_video_paths = sorted(video_paths, key=lambda x: int(x.split('_')[-1].split('.')[0]))
    
    # 使用 FFmpeg 的 filter_complex 選項直接合併所有視頻，確保正確的順序
    filter_complex = ""
    for i in range(len(sorted_video_paths)):
        filter_complex += f"[{i}:v] [{i}:a] "
    filter_complex += f"concat=n={len(sorted_video_paths)}:v=1:a=1 [v] [a]"
    
    input_files = " ".join([f"-i {path}" for path in sorted_video_paths])
    ffmpeg_command = f"ffmpeg {input_files} -filter_complex \"{filter_complex}\" -map \"[v]\" -map \"[a]\" {final_output_path}"
    
    os.system(ffmpeg_command)

    for video_path in video_paths:
        os.remove(video_path)

    print(f"所有視頻已合併為：{final_output_path}")

    return final_output_path
def generate_random_id(length=10):
    """生成指定長度的隨機字母數字字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))