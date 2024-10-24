import os
import json
import requests
from django.http import JsonResponse
from django.conf import settings
from dotenv import load_dotenv
import time
import logging
from openai import OpenAI
import threading
import re
import concurrent.futures
from collections import OrderedDict
from news_storyboard.views import log_and_print
from datetime import datetime

load_dotenv(os.path.join(settings.BASE_DIR, '.env'))
# 設定 logger
logger = logging.getLogger(__name__)

# 初始化 OpenAI API Key
client = OpenAI(
        api_key=os.environ.get('OPENAI_API_KEY'),
    )
def fetch_generation_images(generation_id):
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {os.environ.get("LEONARDO_API_KEY")}',
    }

    for attempt in range(40):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            api_response = response.json()

            generated_images = api_response.get("generations_by_pk", {}).get("generated_images", [])
            image_urls = [img.get("url") for img in generated_images if img.get("url")]

            if image_urls:
                return image_urls[0]  # 返回第一個圖片 URL
            else:
                #print(f"等待生成圖片... 嘗試 {attempt + 1}/40")
                time.sleep(5)  # 沒有圖片則延遲後重試

        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {attempt + 1}: API request failed: {e}")
            continue

    logger.error("無法獲取生成的圖片")
    return None

# 翻譯描述為英文的函數
def translate_to_english(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 使用 gpt-3.5-turbo 或 gpt-4
            messages=[
                {"role": "system", "content": "You are a helpful assistant that translates text to English."},
                {"role": "user", "content": f"Please translate the following text to English. If it's already in English, return it as is: {text}"}
            ],
            max_tokens=100,
            temperature=0.5,
        )
        english_text = response.choices[0].message.content.strip()
        return english_text
    except Exception as e:
        logger.error(f"翻譯失敗: {str(e)}")
        return text  # 如果翻譯失敗，返回原始文本

# 獲取生成圖片的 URL
def generate_images_from_descriptions(title, image_descriptions, random_id):
    save_directory=os.path.join(settings.MEDIA_ROOT, 'generated', random_id)
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    
    leonardo_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {os.environ.get("LEONARDO_API_KEY")}',
        'content-type': 'application/json'
    }
    
    total_images = len(image_descriptions)
    progress_counter = 0
    progress_lock = threading.Lock()
    results = OrderedDict()

    def generate_image(idx, description):
        nonlocal progress_counter
        try:
            payload = {
                "prompt": description,
                "alchemy": True,
                "height": 768,
                "modelId": "aa77f04e-3eec-4034-9c07-d0f619684628",
                "num_images": 1,
                "presetStyle": "NONE",
                "width": 1024,
                "photoReal": True,
                "expandedDomain": True,
                "photoRealVersion": "v2",
                "public": False,
                "guidance_scale": 7,
                "num_inference_steps": 30,
                "contrastRatio": 0.8,
                "highResolution": True,
                "negative_prompt": "low resolution, bad quality, unrealistic"
            }
            response = requests.post(leonardo_url, headers=headers, json=payload)
            response.raise_for_status()
            api_response = response.json()

            generation_id = api_response.get("sdGenerationJob", {}).get("generationId")
            if generation_id:
                image_url = fetch_generation_images(generation_id)

                if image_url:
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        safe_title = re.sub(r'[^\w\-_\. ]', '_', title)
                        image_filename = f'{safe_title}_{idx+1}.png'
                        image_path = os.path.join(save_directory, image_filename)
                        with open(image_path, 'wb') as f:
                            f.write(image_response.content)

                        # 只保留檔名，不包含路徑
                        return idx, (image_url, image_filename)
                    else:
                        logger.error(f"圖片下載失敗: {description}")
                else:
                    logger.error(f"生成圖片失敗: {description}")
            else:
                logger.error(f"Leonardo API 沒有返回 generation_id")
        except Exception as e:
            logger.error(f"生成圖片失敗: {str(e)}")
        finally:
            with progress_lock:
                progress_counter += 1
                log_and_print(f"圖片生成進度: {progress_counter}/{total_images}")
        return idx, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {executor.submit(generate_image, idx, desc): idx for idx, desc in enumerate(image_descriptions)}
        for future in concurrent.futures.as_completed(future_to_idx):
            idx, result = future.result()
            if result:
                results[idx] = result

    # 按照原始順序整理結果
    image_results = [results[i] for i in range(len(image_descriptions)) if i in results]

    return image_results

# 測試新聞生成邏輯
def run_news_gen_img(manager, storyboard_object, random_id, coordinates):
    try:
        log_and_print("開始生成新聞圖片")
        
        image_descriptions = []
        title = storyboard_object.get('title')
        for idx, item in enumerate(storyboard_object.get('storyboard', [])):
            description = item.get('imageDescription')
            if description:
                log_and_print(f"開始處理 Paragraph {idx + 1} 的圖片")
                translated_description = translate_to_english(description)
                image_descriptions.append((idx, translated_description))

        image_results = generate_images_from_descriptions(title, [desc for _, desc in image_descriptions], random_id)
        
        for (idx, _), result in zip(image_descriptions, image_results):
            if result:
                log_and_print(f"成功生成 Paragraph {idx + 1} 的圖片")
                image_url, image_path = result
                image_info = {
                    "img_path": image_path,
                    "url": image_url,
                    "top_left": coordinates["top_left"],
                    "top_right": coordinates["top_right"],
                    "bottom_right": coordinates["bottom_right"],
                    "bottom_left": coordinates["bottom_left"],
                    "z_index": 0
                }
                manager.update_paragraph(idx, {"images": [image_info]})
        
        manager.wait_for_queue()
        log_and_print("完成所有圖片生成")
        
        return image_results 

    except Exception as e:
        log_and_print(f"圖片生成過程中發生錯誤: {str(e)}")
        return []

if __name__ == '__main__':
    run_news_gen_img()
