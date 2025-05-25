from django.db import models

class Video(models.Model):
    video_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    published_at = models.DateTimeField()
    thumbnails = models.JSONField()
    channel_title = models.CharField(max_length=255)

    def __str__(self):
        return self.title
