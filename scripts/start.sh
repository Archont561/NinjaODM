echo "Running database migrations..."
pixi run -e prod django:manage migrate

echo "Starting production server with gunicorn..."
echo "Workers: ${GUNICORN_WORKERS:-4}"
echo "Bind: ${GUNICORN_BIND:-0.0.0.0:8000}"
exec gunicorn app.config.asgi:application \
  -k uvicorn.workers.UvicornWorker \
  --bind "${GUNICORN_BIND:-0.0.0.0:8000}" \
  --workers "${GUNICORN_WORKERS:-4}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-logfile - \
  --error-logfile - \
  --log-level "${LOG_LEVEL:-INFO}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
