from django.urls import path
from .views import MockTokenObtainPairView, MockTokenRefreshView, DataView
#爬蟲轉新聞稿
from .views import NewsAPIView, NewsGenView, NewsStatusView


urlpatterns = [
    path('api/token', MockTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh', MockTokenRefreshView.as_view(), name='token_refresh'),
    path('api/data', DataView.as_view(), name='data'),
    path('api/execute-newsapi', NewsAPIView.as_view(), name='execute_newsapi'),
    path('api/execute-status', NewsStatusView.as_view(), name='news_status'),
    path('api/execute-news-gen', NewsGenView.as_view(), name='execute_news_gen'),
]