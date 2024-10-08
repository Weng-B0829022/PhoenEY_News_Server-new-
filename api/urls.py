from django.urls import path
from .views import (
    MockTokenObtainPairView,
    MockTokenRefreshView,
    DataView,
    NewsAPIView,
    NewsGenView,
    NewsStatusView,
    NewsGenImgView,
    NewsCompositeVideoView,
    TestVideoView
)

urlpatterns = [
    path('api/token', MockTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh', MockTokenRefreshView.as_view(), name='token_refresh'),
    path('api/data', DataView.as_view(), name='data'),
    path('api/execute-newsapi', NewsAPIView.as_view(), name='execute_newsapi'),
    path('api/execute-status', NewsStatusView.as_view(), name='news_status'),
    path('api/execute-news-gen', NewsGenView.as_view(), name='execute_news_gen'),
    path('api/execute-news-gen-img', NewsGenImgView.as_view(), name='execute_news_gen_img'),
    path('api/execute-news-composite-video', NewsCompositeVideoView.as_view(), name='execute_news_composite_video'),
    path('api/test-video', TestVideoView.as_view(), name='test-video'),
]