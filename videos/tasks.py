import os
import json
import requests
import logging
import redis
from celery import shared_task
from .models import Video
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/search"
REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.StrictRedis.from_url(REDIS_URL)
BLOCK_DURATION = 3600  # 1 hour

def is_key_blocked(api_key: str) -> bool:
    return redis_client.exists(f"quota_blocked:{api_key}")

def block_api_key(api_key: str):
    redis_client.setex(f"quota_blocked:{api_key}", BLOCK_DURATION, "1")

from datetime import datetime, timezone

def get_start_of_today_utc():
    now = datetime.now(timezone.utc)
    start_of_today = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    return start_of_today.isoformat()

@shared_task
def fetch_youtube_videos():
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

    api_keys = os.getenv("YOUTUBE_API_KEYS", "").split(",")
    search_query = os.getenv("SEARCH_QUERY", "how to tea") # predefined search query
    published_after = get_start_of_today_utc()
    print(f"Fetching videos published after {published_after} (start of today UTC) {api_keys}")

    for api_key in api_keys:
        if is_key_blocked(api_key):
            logger.warning(f"Skipping blocked API key: {api_key[:5]}***")
            continue

        params = {
            "part": "snippet",
            "q": search_query,
            "type": "video",
            "order": "date",
            "maxResults": 5, # for testing purpose it is limited to 5
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

            for item in items:
                try:
                    vid_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    video, created = Video.objects.update_or_create(
                        video_id=vid_id,
                        defaults={
                            "title": snippet["title"],
                            "description": snippet["description"],
                            "published_at": snippet["publishedAt"],
                            "thumbnails": json.dumps(snippet["thumbnails"]),
                            "channel_title": snippet["channelTitle"]
                        }
                    )
                    logger.info(f"{'Created' if created else 'Updated'} video: {vid_id}")
                except Exception as e:
                    logger.error(f"Error saving video {item}: {str(e)}")
            break  # Successful call
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
                logger.warning(f"Blocked API key {api_key[:5]}*** for {BLOCK_DURATION//60} minutes due to quota error.")
                continue  # Try next key
            else:
                logger.error(f"Stopping attempts. Non-quota error: {error_reason}")
                break
    