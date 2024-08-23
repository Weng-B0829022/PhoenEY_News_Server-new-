from django.urls import path, include

urlpatterns = [
    path('', include('api.urls')),  # 這會包含 api 應用的所有 URL
]