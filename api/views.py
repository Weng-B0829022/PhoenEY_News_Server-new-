from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views import View
from news_storyboard.services.news_service import execute_newsapi, execute_news_gen, execute_news_gen_img, execute_news_gen_voice, combine_media
import logging
import time
import threading
import traceback
from asgiref.sync import async_to_sync
import json
from concurrent.futures import ThreadPoolExecutor
from django.http import FileResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.conf import settings
import os
import re

logger = logging.getLogger(__name__)
logger.debug("This is a debug message")
# 模擬的用戶憑證
MOCK_USERNAME = 'testuser'
MOCK_PASSWORD = 'testpassword'

# 確保模擬用戶存在

def ensure_mock_user_exists():
    if not User.objects.filter(username=MOCK_USERNAME).exists():
        User.objects.create_user(username=MOCK_USERNAME, password=MOCK_PASSWORD)
        logger.info(f"Created mock user: {MOCK_USERNAME}")

class MockTokenObtainPairView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        logger.info(f"Login attempt for user: {username}")

        ensure_mock_user_exists()
        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            logger.info(f"Login successful for user: {username}")
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            logger.warning(f"Invalid login attempt for user: {username}")
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)

class MockTokenRefreshView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        try:
            refresh = RefreshToken(refresh_token)
            logger.info("Token refresh successful")
            return Response({
                'access': str(refresh.access_token),
            })
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return Response({"error": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)


class DataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(f"Data access attempt by user: {request.user}")
        return Response({"message": "This is protected data", "user": str(request.user)})
        
global_state = {
    'current_step': 'idle',
    'news_result': None,
    'status': 'idle',
    'error_message': None
}

class NewsAPIView(View):
    def get(self, request):
        keyword = request.GET.get('keyword', '')
        if not keyword:
            return JsonResponse({'error': 'Keyword is required'}, status=400)
        
        global_state['current_step'] = 'news_api'
        global_state['status'] = 'generating'
        global_state['error_message'] = None
        
        threading.Thread(target=self.process_news_api, args=(keyword,)).start()
        logger.info(f"Started news API processing for keyword: {keyword}")
        return JsonResponse({'message': 'Processing started', 'status': 'generating', 'step': 'news_api'})

    def process_news_api(self, keyword):
        logger.info(f"Executing news API for keyword: {keyword}")
        try:
            result = execute_newsapi(keyword)  # 注意：這裡不再使用 asyncio.run()
            logger.info(f"Raw result from execute_newsapi: {result}")
            
            if isinstance(result, dict) and result.get('status') == 'success':
                global_state['news_result'] = result
                global_state['current_step'] = 'news_api_completed'
                global_state['status'] = 'completed'
                logger.info("News API processing completed successfully")
            else:
                raise ValueError(f"Unexpected result format: {result}")
        except Exception as e:
            logger.error(f"Error in news API processing: {str(e)}")
            logger.error(traceback.format_exc())
            global_state['status'] = 'error'
            global_state['current_step'] = 'idle'
            global_state['error_message'] = str(e)

class NewsGenView(View):
    def get(self, request):
        global_state['current_step'] = 'news_gen'
        global_state['status'] = 'generating'
        global_state['error_message'] = None
        
        threading.Thread(target=self.process_news_gen).start()
        logger.info("Started news generation")
        return JsonResponse({'message': 'News generation started', 'status': 'generating', 'step': 'news_gen'})

    def process_news_gen(self):
        logger.info("Executing news generation")
        try:
            result = execute_news_gen()
            global_state['news_result'] = result
            global_state['current_step'] = 'completed'
            global_state['status'] = 'completed'
            logger.info("News generation completed successfully")
        except Exception as e:
            logger.error(f"Error in news generation: {str(e)}")
            logger.error(traceback.format_exc())
            global_state['status'] = 'error'
            global_state['current_step'] = 'idle'
            global_state['error_message'] = str(e)

class NewsStatusView(View):
    def get(self, request):
        current_step = global_state['current_step']
        news_result = global_state['news_result']
        status = global_state['status']
        error_message = global_state['error_message']
        
        logger.info(f"Checking status. Current step: {current_step}, Status: {status}")

        if status == 'generating':
            return JsonResponse({'status': 'generating', 'step': current_step})
        elif status == 'completed':
            if current_step == 'news_api_completed':
                return JsonResponse({'status': 'completed', 'step': 'news_api', 'result': news_result})
            elif current_step == 'completed':
                result = news_result
                global_state['current_step'] = 'idle'
                global_state['news_result'] = None
                global_state['status'] = 'idle'
                global_state['error_message'] = None
                logger.info("Processing completed. Resetting to idle state.")
                return JsonResponse({'status': 'completed', 'step': 'news_gen', 'result': result}, json_dumps_params={'ensure_ascii': False})
        elif status == 'error':
            logger.error(f"Error occurred: {error_message}")
            return JsonResponse({'status': 'error', 'message': error_message or 'An error occurred during processing'})
        else:
            logger.warning(f"Unexpected state: {current_step}")
            return JsonResponse({'status': 'idle'})

class NewsGenImgView(APIView):
    def post(self, request):
        # 從請求中獲取 index 參數，如果沒有提供則默認為 0
        index = request.query_params.get('index', 0)
        try:
            # 將 index 轉換為整數
            index = int(index)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid index. Must be an integer.'
            }, status=400)
    
        # 調用執行函數，傳入 index 參數
        result = execute_news_gen_img(index)
        
        if result['status'] == 'success':
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False}, status=500)


class NewsGenVideoView(APIView):
    def post(self, request):
        story_object = request.data.get('story_object')
        
        if not story_object:
            return JsonResponse({'error': 'Missing story_object parameter'}, status=400)
        
        # 直接執行 start_data_collection 並獲取 image_urls
        video_paths, image_urls = self.start_data_collection(story_object)

        # 立即返回 image_urls 給前端
        return JsonResponse({'message': 'Image generation completed', 'image_urls': image_urls, 'video_paths': video_paths}, status=200)

    def start_data_collection(self, story_object):
        # 移除最後9個元素
        story_object['storyboard'] = story_object['storyboard'][:]
        
        # 使用 ThreadPoolExecutor 異步執行圖片和聲音生成任務
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_img = executor.submit(execute_news_gen_img, story_object)
            future_voice = executor.submit(execute_news_gen_voice, story_object)

        # 獲取結果
        try:
            img_binary, image_urls = future_img.result()
            audio_byteIO = future_voice.result()  # 等待語音生成完成，但不使用其結果
            video_paths = combine_media(story_object, img_binary, audio_byteIO)
            return video_paths, image_urls
        except Exception as e:
            print(f"Error in image or voice generation: {str(e)}")
            return None

class GetGeneratedVideoView(View):
    def get(self, request):
        filename = request.GET.get('filename')
        
        if not filename:
            logger.warning("Missing filename parameter in request")
            return HttpResponseBadRequest("Missing filename parameter")

        # 使用正則表達式驗證文件名格式
        if not re.match(r'^[\w\-. ]+\.mp4$', filename):
            logger.warning(f"Invalid filename format: {filename}")
            return HttpResponseBadRequest("Invalid filename format")

        # 使用 os.path.basename 來確保只使用文件名部分
        safe_filename = os.path.basename(filename)
        
        video_dir = os.path.join(settings.MEDIA_ROOT, 'generated_video')
        video_path = os.path.join(video_dir, safe_filename)

        # 使用 os.path.abspath 和比較來確保文件路徑不會超出預期目錄
        if not os.path.abspath(video_path).startswith(os.path.abspath(video_dir)):
            logger.warning(f"Attempted directory traversal: {filename}")
            return HttpResponseBadRequest("Invalid filename")

        if os.path.exists(video_path):
            logger.info(f"Serving video file: {video_path}")
            return FileResponse(open(video_path, 'rb'), content_type='video/mp4')
        else:
            logger.warning(f"Video file not found: {video_path}")
            return HttpResponseNotFound("Video not found")