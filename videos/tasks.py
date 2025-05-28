import os
import json
import requests
import logging
import redis
from celery import shared_task, Celery
from celery.exceptions import Retry
from .models import Video
from datetime import datetime, timezone
from django.db import transaction

logger = logging.getLogger(__name__)

YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/search"
REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.StrictRedis.from_url(REDIS_URL)
BLOCK_DURATION = 3600  # 1 hour
app = Celery('youtube_tasks')

def is_key_blocked(api_key: str) -> bool:
    return redis_client.exists(f"quota_blocked:{api_key}")

def block_api_key(api_key: str):
    redis_client.setex(f"quota_blocked:{api_key}", BLOCK_DURATION, "1")

def get_start_of_today_utc():
    now = datetime.now(timezone.utc)
    start_of_today = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    return start_of_today.isoformat()

def get_last_fetch_time():
    ts = redis_client.get("youtube:last_fetch_time")
    return ts.decode() if ts else get_start_of_today_utc()

def set_last_fetch_time(timestamp: str):
    redis_client.set("youtube:last_fetch_time", timestamp)

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def fetch_youtube_videos(self):
    """
    Fetches recent YouTube videos based on a search query, filters the results,
    and stores or updates them in the PostgreSQL database.

    This task:
    - Reads multiple YouTube API keys from environment variables to handle quota limits. (API KEY ROTATION)
    - Queries the YouTube Data API for videos published after the current time.
    - Filters the response to extract relevant video details.
    - Updates existing video entries or creates new ones in the PostgreSQL database
      via Django's ORM.
    - Logs the status of each operation and handles API quota errors by cycling
      through available API keys.

    Environment Variables:
    - YOUTUBE_API_KEYS: Comma-separated list of YouTube Data API keys.
    - SEARCH_QUERY: Search keyword to query videos (default: "how to tea").

    Models:
    - Video: Django model representing the video data with fields such as video_id,
      title, description, published_at, thumbnails, and channel_title.

    Note:
    This task is intended to be run asynchronously using Celery.
    """
    try:
        api_keys = os.getenv("YOUTUBE_API_KEYS", "").split(",")
        search_query = os.getenv("SEARCH_QUERY", "how to tea")
        published_after = get_last_fetch_time()
        print(f"Fetching videos published after {published_after} (last fetch time) {api_keys}")

        # Redis Lock to prevent race conditions
        if not redis_client.set("youtube:lock", "1", nx=True, ex=60):
            logger.warning("Fetch already in progress, skipping execution.")
            return

        for api_key in api_keys:
            if is_key_blocked(api_key):
                logger.warning(f"Skipping blocked API key: {api_key[:5]}***")
                continue

            params = {
                "part": "snippet",
                "q": search_query,
                "type": "video",
                "order": "date",
                "maxResults": 5,
                "key": api_key,
                "publishedAfter": published_after,
            }

            response = requests.get(YOUTUBE_URL, params=params)
            print(f"Request URL: {response.url}")
            print(f"Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                print(f"Fetched {len(items)} items using API key {api_key[:5]}***")
                video_objects = []
                for item in items:
                    try:
                        vid_id = item["id"]["videoId"]
                        snippet = item["snippet"]
                        video_objects.append(Video(
                            video_id=vid_id,
                            title=snippet["title"],
                            description=snippet["description"],
                            published_at=snippet["publishedAt"],
                            thumbnails=json.dumps(snippet["thumbnails"]),
                            channel_title=snippet["channelTitle"]
                        ))
                    except Exception as e:
                        logger.error(f"Invalid item structure: {str(e)}")
                        app.send_task(
                            "youtube_tasks.deadletter_handler",
                            args=[{
                                "error": str(e),
                                "item": item
                            }],
                            queue="youtube_deadletter"
                        )

                if video_objects:
                    try:
                        with transaction.atomic():
                            Video.objects.bulk_create(video_objects, ignore_conflicts=True)
                            latest_published_at = max(v.published_at for v in video_objects)
                            set_last_fetch_time(latest_published_at)
                    except Exception as e:
                        logger.error(f"Bulk insert failed: {str(e)}")

                break  # Successfully fetched with one API key

            else:
                try:
                    error_info = response.json()
                    error_reason = error_info['error']['errors'][0]['reason']
                    logger.warning(f"API key {api_key[:5]}*** failed with reason: {error_reason}")
                except Exception as e:
                    error_reason = "unknown"
                    logger.error(f"Failed to parse error: {str(e)}")

                if error_reason in ['quotaExceeded', 'dailyLimitExceeded', 'userRateLimitExceeded']:
                    block_api_key(api_key)
                    continue
                else:
                    logger.error(f"Non-quota error encountered: {error_reason}")
                    break

    except Exception as exc:
        logger.error(f"Task failed, retrying and sending to deadletter queue: {str(exc)}")
        app.send_task(
            "youtube_tasks.deadletter_handler",
            args=[{
                "error": str(exc),
                "task": "fetch_youtube_videos"
            }],
            queue="youtube_deadletter"
        )
        raise self.retry(exc=exc)

@shared_task(name="youtube_tasks.deadletter_handler", queue="youtube_deadletter")
def deadletter_handler(payload):
    redis_client.rpush("youtube:deadletter", json.dumps(payload))

# Explicitly tell to run this worker
# celery -A fam_backend worker -l info -Q default,youtube_deadletter