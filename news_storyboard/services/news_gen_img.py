import os
import json
import requests
from django.http import JsonResponse
from django.conf import settings
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(os.path.join(settings.BASE_DIR, '.env'))
client = OpenAI(
    api_key=os.environ.get('OPENAI_API_KEY'),
)


# 提取 JSON 檔案
def extract_image_descriptions_from_storyboard(file_path):
    print(file_path)
    # 開啟並讀取 JSON 檔案
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 提取每篇文章的內容
    image_descriptions = {}
    for article in data['articles']:
        storyboard = article['storyboard']
        lines = storyboard.split('\n')

        images = []

        for line in lines:
            if line.startswith("Image:"):
                #  'Image:' 後面的部分
                image_description = line.split("Image:")[1].strip()
                print(image_description)
                images.append(image_description)

        # 保存提取到的圖片描述
        image_descriptions[article['title']] = images
    
    return image_descriptions

# 生成圖片的函數
def generate_images_from_descriptions(image_descriptions, save_directory=os.path.join(settings.MEDIA_ROOT, 'generated_images/')):
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

    image_urls = []
    
    for article_title, descriptions in image_descriptions.items():
        for idx, description in enumerate(descriptions):
            try:
                # 使用 DALL-E 生成圖片
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=description,
                    size="1792x1024",
                    quality="standard",
                    n=1,
                )
                image_url = response.data[0].url if response.data else None
                
                if image_url:
                    # 下載生成的圖片並保存
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        image_path = os.path.join(save_directory, f'{article_title}_image_{idx+1}.png')
                        with open(image_path, 'wb') as f:
                            f.write(image_response.content)
                        image_urls.append(image_url)
                    else:
                        print(f"圖片下載失敗: {description}")
                else:
                    print(f"生成圖片失敗: {description}")
            except Exception as e:
                print(f"生成圖片失敗: {str(e)}")
    
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
#先把圖片描述提取出來，再根據圖片描述生成圖片，最後輸出圖片的網址，並將圖片保存在指定的路徑
def run_news_gen_img():
    file_path = 'derivative_articles_and_storyboards.json'
    image_descriptions = extract_image_descriptions_from_storyboard(file_path)
    image_urls = generate_images_from_descriptions(image_descriptions)
    return image_urls

if __name__ == '__main__':
    run_news_gen_img()
