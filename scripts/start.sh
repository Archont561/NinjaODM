# Run migrations
echo "Running database migrations..."
python ./app/manage.py migrate --noinput

ENVIRONMENT="$1"

# Collect static files in production
if [ "${ENVIRONMENT}" = "prod" ]; then
    echo "Collecting static files..."
    python ./app/manage.py collectstatic --noinput
fi

# Start the server based on environment
case "${ENVIRONMENT}" in
  prod)
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
    ;;
  dev)
    echo "Starting development server with uvicorn..."
    echo "Bind: ${UVICORN_HOST:-0.0.0.0}:${UVICORN_PORT:-8000}"
    exec uvicorn app.config.asgi:application \
      --reload \
      --host "${UVICORN_HOST:-0.0.0.0}" \
      --port "${UVICORN_PORT:-8000}" \
      --log-level "${LOG_LEVEL:-info}"
    ;;
  test)
    echo "Running tests..."
    exec pytest tests/ -v
    ;;
  *)
    echo "ERROR: Unknown environment: ${ENVIRONMENT}"
    echo "Valid environments: prod, dev, test"
    exit 1
    ;;
esac
