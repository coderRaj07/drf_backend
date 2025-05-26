from django.urls import path
from .views import VideoListView, video_table_view

urlpatterns = [
    path('', VideoListView.as_view(), name='video-list'),  # API JSON
    path('table/', video_table_view, name='video-table'),  # HTML page
]
