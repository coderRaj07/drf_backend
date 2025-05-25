from django.contrib import admin
from .models import Video

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('video_id', 'title', 'published_at', 'channel_title')
    search_fields = ('title', 'description', 'channel_title')
