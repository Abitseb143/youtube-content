#!/bin/sh
# Entry point for the `api` Railway service.
# Runs Alembic migrations against the live DATABASE_URL, then starts uvicorn.
set -e

echo "[start-api] running migrations…"
alembic upgrade head

echo "[start-api] starting uvicorn on 0.0.0.0:${PORT:-8000}"
exec uvicorn faceless.main:app --host 0.0.0.0 --port "${PORT:-8000}"
