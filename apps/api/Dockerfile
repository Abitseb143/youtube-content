# Multi-purpose image — used by both `api` and `worker` Railway services.
# Built from build context = apps/api/ (set Service Root Directory to apps/api).
# `api` service uses default CMD (start-api.sh runs migrations + uvicorn).
# `worker` service overrides CMD to: arq faceless.worker.WorkerSettings

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip && pip install -e .

# Copy migrations + config
COPY alembic.ini ./
COPY alembic ./alembic

# Copy startup script
COPY scripts/start-api.sh ./scripts/start-api.sh
RUN chmod +x ./scripts/start-api.sh

EXPOSE 8000

CMD ["./scripts/start-api.sh"]
