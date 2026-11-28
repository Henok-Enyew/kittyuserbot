# KittyUserbot image. Secrets are NOT baked in: they come from the .env file at
# runtime (docker compose reads it, see docker-compose.yml and .env.example).
#
#   docker compose up -d --build     build and start in the background
#   docker compose logs -f           watch the logs
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Africa/Addis_Ababa

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg git gcc python3-dev libwebp-dev libpq-dev libjpeg-dev \
        zlib1g-dev libevent-dev postgresql-client libpcre2-dev \
        libmagickwand-dev mediainfo tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so code changes don't reinstall everything
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip install "rembg[cpu]" onnxruntime Pillow

# Pre-download the background-removal model so the first .rmbg isn't slow
RUN python3 -c "from rembg import new_session; new_session('u2net')" || true

COPY . .
RUN mkdir -p /app/downloads

CMD ["python3", "-m", "userbot"]
