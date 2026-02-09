#!/bin/bash
set -e

# Load Pixi production environment
eval "$(pixi shell-hook -e prod)"

echo "Starting Gunicorn in Pixi prod environment..."
echo "Workers: ${GUNICORN_WORKERS:-4}"
echo "Bind: ${GUNICORN_BIND:-0.0.0.0}"

gunicorn app.config.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    --bind "${GUNICORN_BIND:-0.0.0.0}" \
    --workers "${GUNICORN_WORKERS:-4}" \
    --access-logfile - \
    --error-logfile - \
    --log-level "${LOG_LEVEL:-info}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
