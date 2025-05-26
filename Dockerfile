# ---------- Stage 1: Build ----------
FROM python:3.13-slim AS builder

WORKDIR /app
    
    # Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies to a temporary location
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --prefix=/install -r requirements.txt


# ---------- Stage 2: Runtime ----------
FROM python:3.13-slim

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy app source code
COPY . /app

# Set environment variables (optional)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Start the app
CMD ["gunicorn", "fam_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
    