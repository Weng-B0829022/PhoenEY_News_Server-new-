from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views import View
from news_storyboard.services.news_service import execute_newsapi, execute_news_gen
import logging

logger = logging.getLogger(__name__)

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
        
# api/views.py


class NewsAPIView(View):
    def get(self, request):
        keyword = request.GET.get('keyword', '')
        if not keyword:
            return JsonResponse({'error': 'Keyword is required'}, status=400)
        
        result = execute_newsapi(keyword)
        if result['status'] == 'success':
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False}, status=500)

class NewsGenView(View):
    def get(self, request):
        result = execute_news_gen()
        if result['status'] == 'success':
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False},  status=500)