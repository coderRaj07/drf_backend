
# 📺 YouTube Video Fetcher API

## 🎯 Project Overview

This project provides a robust API to fetch the latest YouTube videos based on a predefined search query. It continuously polls the YouTube Data API to retrieve new videos, stores them in a PostgreSQL database, and offers endpoints to access and search the stored videos efficiently.

---

## 🌟 Features

* **Continuous Background Fetching**: Utilizes Celery to asynchronously fetch new videos every 10 seconds.
* **Multiple API Key Support**: Automatically rotates through multiple YouTube API keys upon quota exhaustion 🔑🔄.
* **Efficient Data Storage**: Stores video details with proper indexing in PostgreSQL.
* **Advanced Search**: Implements full-text search combined with trigram similarity for partial and fuzzy matching 🔍.
* **Dashboard Interface**: Dashboard to view and filter stored videos 📊.
* **Dockerized Deployment**: Easily deployable using Docker and Docker Compose 🐳.

---

## 📹 Demo

Watch the project in action:

👉 [Demo Video on Loom](https://www.loom.com/share/c359abc15c5b4489a9702ea2a393b201?sid=76085edc-227f-4ba2-90ac-5118c19b8c74)

---

## 🧠 Smart Fetching Logic

* **Initial Run**: Fetches videos published from midnight UTC of the current day.
* **Subsequent Runs**: Only fetches videos published after the latest stored video, avoiding duplicates. Also acts as a fallback — if Celery stops, it restores from the last known timestamp using Redis. 
* **State Management**: Uses Redis to persist the timestamp of the latest fetched video, ensuring continuity across restarts.

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/coderraj07/youtube-video-fetcher.git
cd youtube-video-fetcher
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory. Refer to `.env.example` for the required variables.

**Note**: The project uses a remote PostgreSQL database. Ensure your `DATABASE_URL` is set accordingly.

### 3. Set Up PostgreSQL Extension

Ensure the `pg_trgm` extension is enabled for trigram similarity search:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 4. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🚀 Running the Application

### Option A: Using Celery with Django Runserver (Development)

**Start Redis Server** (if not already running):

```bash
redis-server
```

**Start Django Development Server**:

```bash
python manage.py runserver
```

**Start Celery Worker and Beat**:

```bash
celery -A fam_backend worker --beat --scheduler django --loglevel=info
```

### Option B: Using Docker Compose (Recommended for Production)

Ensure Docker and Docker Compose are installed.

**Build and Start Containers**:

```bash
docker-compose up --build
```

This command sets up the Django app, Celery worker, Celery beat scheduler, and Redis.

---

## 🔗 API Endpoints

* `GET /api/videos/`: Retrieve paginated list of stored videos, sorted by published date (newest first).
* `GET /api/videos/?search=your_query`: Search videos by title and description with support for partial and fuzzy matching.
* `GET /api/videos/table/`: Access the dashboard interface to view and filter videos (optional feature).

---

## 🛠️ Technologies Used

* **Backend**: Python, Django Rest Framework
* **Asynchronous Task Queue**: Celery
* **Database**: PostgreSQL with `pg_trgm` extension
* **Caching & Message Broker**: Redis
* **Deployment**: Docker, Docker Compose
* **External API**: YouTube Data API v3

---

## 🙌 Acknowledgements

* [YouTube Data API](https://developers.google.com/youtube/v3)
* [Django Rest Framework](https://www.django-rest-framework.org/)
* [Celery](https://docs.celeryq.dev/en/stable/)
* [Docker](https://www.docker.com/)
