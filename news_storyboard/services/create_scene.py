import cv2
import numpy as np
import os
from pydub import AudioSegment
from io import BytesIO
from tqdm import tqdm
from django.conf import settings
def create_videos_from_images_and_audio(img_binary_list, audio_byteIO_list, output_folder=os.path.join(settings.MEDIA_ROOT, 'generated_videos/')):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video_paths = []

    # 使用tqdm創建總體進度條
    for index, (img_binary, audio_byteIO) in enumerate(tqdm(list(zip(img_binary_list, audio_byteIO_list)), desc="處理視頻")):
        print(f"\n開始處理第 {index+1} 個視頻")

        # 讀取圖片
        img_array = np.frombuffer(img_binary, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        print("圖片讀取完成")

        # 獲取圖片尺寸
        height, width, layers = img.shape

        # 讀取音頻
        audio = AudioSegment.from_file(BytesIO(audio_byteIO))
        audio_duration = len(audio) / 1000  # 轉換為秒
        print(f"音頻讀取完成，持續時間: {audio_duration:.2f} 秒")

        # 設置視頻參數
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30
        video_path = os.path.join(output_folder, f'video_{index}.mp4')
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        # 計算需要的幀數
        total_frames = int(audio_duration * fps)

        # 創建視頻
        print("開始創建視頻幀")
        for _ in tqdm(range(total_frames), desc="創建視頻幀", leave=False):
            out.write(img)

        out.release()
        print("視頻幀創建完成")

        # 合併音頻和視頻
        temp_audio_path = os.path.join(output_folder, f'temp_audio_{index}.wav')
        audio.export(temp_audio_path, format="wav")
        print("音頻導出完成")

        final_video_path = os.path.join(output_folder, f'final_video_{index}.mp4')
        print("開始合併音頻和視頻")
        os.system(f"ffmpeg -i {video_path} -i {temp_audio_path} -c:v copy -c:a aac {final_video_path}")
        print("音頻視頻合併完成")

        # 清理臨時文件
        os.remove(video_path)
        os.remove(temp_audio_path)
        print("臨時文件清理完成")

        video_paths.append(final_video_path)

    print("\n所有視頻處理完成！")
    return video_paths