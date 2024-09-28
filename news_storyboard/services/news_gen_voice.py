import os
import logging
from django.conf import settings
from voice_api import VoiceAPI
import concurrent.futures
import re
import io

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
        
        return audio_buffer.getvalue()
    except Exception as e:
        error_message = f"Voice generation failed: {str(e)}"
        logger.error(error_message)
        return None

def run_news_gen_voice(storyboard_object):
    title = storyboard_object.get('title', '')
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title)

    voice_texts = []
    for item in storyboard_object.get('storyboard', []):
        text = item.get('voiceover', '')
        if text:
            voice_texts.append(text)

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {executor.submit(generate_voice, text, f'{safe_title}_{idx+1}.mp3', None): idx 
                        for idx, text in enumerate(voice_texts)}
        
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            result = future.result()
            if result:
                results.append(result)

    return results

def execute_news_gen_voice(storyboard_object):
    try:
        result = run_news_gen_voice(storyboard_object)
        return result  
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return []

if __name__ == '__main__':
    execute_news_gen_voice()