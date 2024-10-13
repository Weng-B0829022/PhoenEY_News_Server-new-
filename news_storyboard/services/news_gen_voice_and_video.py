import os
import logging
from django.conf import settings
from voice_api import VoiceAPI
import concurrent.futures
import re
import io
from avatar_sync_lip import FullBodyAvatarGenerator

# Configure logger
logger = logging.getLogger(__name__)

def generate_voice(text, filename, save_directory):
    try:
        # Initialize API
        api_base_ip = "216.234.102.170"
        api_port = "10620"
        api = VoiceAPI(api_base_ip=api_base_ip, api_port=api_port)

        # Set voice model
        api.set_model("woman1")  # Currently only woman1 is available

        # Generate voice
        audio = api.tts_generate(text)

        # Save the audio to a BytesIO object
        audio_buffer = io.BytesIO()
        audio.export(audio_buffer, format="mp3")

        # Save the audio file to the specified directory
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        file_path = os.path.join(save_directory, filename)
        with open(file_path, 'wb') as f:
            f.write(audio_buffer.getvalue())

        logger.info(f"Audio file saved: {file_path}")

        # Return only the filename instead of the full path
        return filename
    except Exception as e:
        error_message = f"Voice generation failed: {str(e)}"
        logger.error(error_message)
        return None

def generate_video(manager, audio_file_name, character):
    try:
        # 從 manager 中取得 random_id
        random_id = manager.storyboard.get('random_id', '')

        # 音頻文件名現在只是一個名稱，重新構建完整路徑
        audio_file_path = os.path.join(settings.MEDIA_ROOT, 'generated', random_id, audio_file_name)
        
        save_directory = os.path.dirname(audio_file_path)
        audio_filename = os.path.basename(audio_file_path)
        
        video_filename = os.path.splitext(audio_filename)[0] + '.mp4'
        
        save_path = os.path.join(save_directory, video_filename)

        # 檢查是否需要生成人偶視頻
        paragraph_index = int(re.search(r'\d+', audio_filename).group()) - 1
        need_avatar = manager.storyboard['storyboard'][paragraph_index].get('needAvatar', False)

        if need_avatar:
            print(f"Initializing FullBodyAvatarGenerator with audio file: {audio_file_name}")
            generator = FullBodyAvatarGenerator(
                api_base_ip="216.234.102.170", 
                api_port="10639",
            )
            
            video_url = generator.generate_full_body_avatar(character='woman2',
                                                            audio_file_path=audio_file_path,
                                                            save_path=save_path)
        else:
            # 如果不需要人偶，只返回音頻文件名
            video_url = audio_filename

        # 返回只包含影片檔案名稱或音頻檔案名稱
        return video_filename if need_avatar else audio_filename

    except Exception as e:
        error_message = f"Video generation failed for {audio_file_name}: {str(e)}"
        logger.error(f"Error in video generation: {error_message}")
        return None

def run_news_gen_voice_and_video(manager, storyboard_object, random_id, character='woman1'):
    title = storyboard_object.get('title', '')
    safetitle = re.sub(r'[^\w\-\. ]', '_', title)

    voice_texts = []
    for idx, item in enumerate(storyboard_object.get('storyboard', [])):
        text = item.get('voiceover', '')
        if text:
            voice_texts.append((idx, text))

    results = [None] * len(voice_texts)  # Pre-allocate the results list
    save_directory = os.path.join(settings.MEDIA_ROOT, 'generated', random_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_idx = {executor.submit(generate_voice, text, f'{safetitle}_{idx+1}.mp3', save_directory): idx
                        for idx, (_, text) in enumerate(voice_texts)}

        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            result = future.result()
            print(future, ": finished")
            if result:
                results[idx] = result  # Now this will be the file name

    # Remove any None values (failed generations)
    audio_file_paths = [r for r in results if r is not None]

    # Generate video for each audio file and store both paths
    voice_and_video_paths = []
    for idx, audio_file_path in enumerate(audio_file_paths):
        video_path = generate_video(manager, audio_file_path, character)
        if video_path:
            voice_and_video_paths.append({
                'audios_path': audio_file_path,  # Only file name is stored
                'avatar_path': video_path  # Only file name is stored
            })
            # 更新 storyboard
            manager.add_audio_path(voice_texts[idx][0], audio_file_path)
            
            # 檢查是否需要添加視頻
            need_avatar = manager.storyboard['storyboard'][voice_texts[idx][0]].get('needAvatar', False)
            if need_avatar:
                manager.add_video(voice_texts[idx][0], {
                    'avatar_path': video_path,
                    'x': 0,
                    'y': 240,
                    'width': '1024',
                    'height': '768',
                    'z_index': 1,
                })

    # 等待所有更新完成
    manager.wait_for_queue()

    if voice_and_video_paths:
        return voice_and_video_paths
    else:
        logger.error("No videos were generated successfully.")
        return None

def execute_news_gen_voice(manager, storyboard_object, random_id, character='woman1'):
    try:
        result = run_news_gen_voice_and_video(manager, storyboard_object, random_id, character)
        print(result)
        return result
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return None

if __name__ == '__main__':
    video_path = execute_news_gen_voice()
