# Mag sovereign stack — container boundary (not a host desktop pet).
# Agent tools, backend, and subprocesses run inside this cage.
# Host exposes only localhost ports + mounted operator dirs (memory/, watch/, …).

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MAG_CONTAINER=1 \
    MAG_BIND_HOST=0.0.0.0 \
    MAG_NO_MIRROR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x scripts/container/entrypoint.sh \
    && mkdir -p memory/biography memory/briefs logs state watch queue/handoff queue/results

EXPOSE 8765 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health', timeout=3)"

ENTRYPOINT ["/app/scripts/container/entrypoint.sh"]
