import os
import json
import requests
import logging
from celery import shared_task
from .models import Video
from django.utils import timezone
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/search"

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
    dt = datetime.now(timezone.utc)
    # Strip microseconds and format correctly:
    published_after = dt.replace(microsecond=0).isoformat() 
    print(f"Fetching videos published after {published_after} {api_keys}")

    for api_key in api_keys:
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

            break  # Successfully fetched and processed, no need to try other keys

        elif response.status_code == 403:
            logger.warning(f"API key {api_key[:5]}*** quota exceeded or forbidden. Trying next key.")
            continue

        else:
            logger.error(f"Failed with status {response.status_code}: {response.text}")
