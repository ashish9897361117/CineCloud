FROM python:3.11-slim

# Install system dependencies including FFmpeg for video processing & HLS transcoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create persistent storage directories
RUN mkdir -p data uploads/movies uploads/posters uploads/subtitles uploads/chunks

EXPOSE 8080

ENV PORT=8080
ENV HOST=0.0.0.0
ENV STORAGE_DRIVER=local

CMD ["python", "backend/server.py"]
