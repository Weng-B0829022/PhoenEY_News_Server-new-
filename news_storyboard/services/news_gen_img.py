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
import queue

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

    for attempt in range(10):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            api_response = response.json()

            generated_images = api_response.get("generations_by_pk", {}).get("generated_images", [])
            image_urls = [img.get("url") for img in generated_images if img.get("url")]

            if image_urls:
                return image_urls[0]  # 返回第一個圖片 URL
            else:
                print(f"等待生成圖片... 嘗試 {attempt + 1}/10")
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
            model="gpt-4o-mini",  # 使用 gpt-3.5-turbo 或 gpt-4
            messages=[
                {"role": "system", "content": "You are a helpful assistant that translates text to English."},
                {"role": "user", "content": f"Please translate the following text to English: {text}"}
            ],
            max_tokens=100,
            temperature=0.5,
        )
        english_text = response.choices[0].message.content.strip()
        return english_text
    except Exception as e:
        logger.error(f"翻譯失敗: {str(e)}")
        return text  # 如果翻譯失敗，返回原始文本

# 提取 JSON 檔案並翻譯圖片描述
def extract_image_descriptions_from_storyboard(file_path, article_index):
    # 開啟並讀取 JSON 檔案
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 檢查 article_index 是否有效
    if article_index < 0 or article_index >= len(data['articles']):
        logger.error(f"無效的文章索引: {article_index}")
        return None

    # 提取指定索引的文章內容
    article = data['articles'][article_index]
    storyboard = article['storyboard']
    lines = storyboard.split('\n')
    images = []

    for line in lines:
        if line.startswith("Image:"):
            # 'Image:' 後面的部分
            image_description = line.split("Image:")[1].strip()
            # 翻譯為英文
            translated_description = translate_to_english(image_description)
            images.append(translated_description)

    # 返回提取到的圖片描述
    return {article['title']: images}

# 獲取生成圖片的 URL
def generate_images_from_descriptions(image_descriptions, save_directory=os.path.join(settings.MEDIA_ROOT, 'generated_images/')):
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

    image_urls = []
    
    # Leonardo API 基本設置
    leonardo_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {os.environ.get("LEONARDO_API_KEY")}',
        'content-type': 'application/json'
    }

    # 添加進度追踪
    total_images = sum(len(descriptions) for descriptions in image_descriptions.values())
    progress_counter = 0
    progress_lock = threading.Lock()

    def generate_image(article_title, description, idx):
        nonlocal progress_counter
        try:
            # 使用 Leonardo API 生成圖片
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
                        image_path = os.path.join(save_directory, f'{article_title}_image_{idx+1}.png')
                        with open(image_path, 'wb') as f:
                            f.write(image_response.content)
                        image_urls.append(image_url)
                    else:
                        logger.error(f"圖片下載失敗: {description}")
                else:
                    logger.error(f"生成圖片失敗: {description}")
            else:
                logger.error(f"Leonardo API 沒有返回 generation_id")
        except Exception as e:
            logger.error(f"生成圖片失敗: {str(e)}")
        finally:
            # 更新進度
            with progress_lock:
                progress_counter += 1
                print(f"進度: {progress_counter}/{total_images} ({progress_counter/total_images*100:.2f}%)")

    threads = []
    for article_title, descriptions in image_descriptions.items():
        for idx, description in enumerate(descriptions):
            thread = threading.Thread(target=generate_image, args=(article_title, description, idx))
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()
    
    return image_urls
# 生成新聞相關圖片
def generate_news():
    try:
        # 設定保存圖片的路徑
        save_directory = os.path.join(settings.MEDIA_ROOT, 'generated_images/')
        file_path = 'derivative_articles_and_storyboards.json'

        # 提取圖片描述
        image_descriptions = extract_image_descriptions_from_storyboard(file_path)

        # 根據圖片描述生成圖片
        image_urls = generate_images_from_descriptions(image_descriptions, save_directory)

        return JsonResponse({'image_urls': image_urls})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'An unexpected error occurred: ' + str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

# 測試新聞生成邏輯
def run_news_gen_img(index):
    file_path = 'derivative_articles_and_storyboards.json'
    image_descriptions = extract_image_descriptions_from_storyboard(file_path, index)
    image_urls = generate_images_from_descriptions(image_descriptions)
    return image_urls

if __name__ == '__main__':
    run_news_gen_img()