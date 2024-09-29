from django.urls import path
from .views import (
    MockTokenObtainPairView,
    MockTokenRefreshView,
    DataView,
    NewsAPIView,
    NewsGenView,
    NewsStatusView,
    NewsGenVideoView,
    NewsGenImgView,
    GetGeneratedVideoView  
)

urlpatterns = [
    path('api/token', MockTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh', MockTokenRefreshView.as_view(), name='token_refresh'),
    path('api/data', DataView.as_view(), name='data'),
    path('api/execute-newsapi', NewsAPIView.as_view(), name='execute_newsapi'),
    path('api/execute-status', NewsStatusView.as_view(), name='news_status'),
    path('api/execute-news-gen', NewsGenView.as_view(), name='execute_news_gen'),
    path('api/execute-news-gen-img', NewsGenImgView.as_view(), name='execute_news_gen_img'),
    path('api/execute-news-gen-video', NewsGenVideoView.as_view(), name='execute_news_gen_video'),
    #path('api/execute-news-composite-video', NewsCompositeVideoView.as_view(), name='execute_news_composite_video'),
    path('api/get-generated-video', GetGeneratedVideoView.as_view(), name='get_generated_video'),  # Add this line

]