from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views import View
from news_storyboard.services.news_service import execute_newsapi, execute_news_gen, execute_news_gen_img, execute_news_composite_video
import logging
import asyncio
import threading
import traceback

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

class NewsCompositeVideoView(APIView):
    def post(self, request):
        
        logger.info("Received request for video generation")
        try:
            # 从查询参数中获取 index
            index = request.query_params.get('index')
            logger.info(f"Received index parameter: {index}")
            
            if index is None:
                logger.warning("Index parameter is missing")
                return Response({"error": "Index parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 将 index 转换为整数
            index = int(index)
            logger.info(f"Converted index to integer: {index}")
            
            # 更新全局状态
            global_state['current_step'] = 'news_composite_video'
            global_state['status'] = 'generating'
            global_state['error_message'] = None
            logger.info(f"Updated global state: step={global_state['current_step']}, status={global_state['status']}")
            
            # 立即返回成功响应
            response_data = {
                "message": "Video generation started",
                "id": index,
                "status": "processing"
            }
            logger.info(f"Preparing response: {response_data}")
            
            # 在后台启动视频生成过程
            logger.info(f"Starting background video generation task for index {index}")
            threading.Thread(target=self.generate_video, args=(index,)).start()
            
            logger.info("Returning successful response")
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
        
        except ValueError:
            logger.error(f"Invalid index value: {index}")
            return Response({"error": "Invalid index. Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in NewsCompositeVideoView: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_video(self, index):
        logger.info(f"Starting video generation process for index {index}")

        try:
            # 执行视频生成逻辑
            logger.info(f"Executing news_composite_video for index {index}")
            result = execute_news_composite_video(index)
            logger.info(f"Video generation completed for index {index}. Result: {result}")
            
            # 更新全局状态
            global_state['current_step'] = 'completed'
            global_state['news_result'] = result
            global_state['status'] = 'completed'
            logger.info(f"Updated global state after video generation: {global_state}")
        except Exception as e:
            logger.error(f"Error during video generation for index {index}: {str(e)}", exc_info=True)
            global_state['status'] = 'error'
            global_state['error_message'] = str(e)
            logger.info(f"Updated global state after error: {global_state}")