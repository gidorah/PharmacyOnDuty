#!/bin/sh
set -e

echo "Waiting for services to be ready..."
if [ -f "/app/scripts/wait_for_services.py" ]; then
  uv run python -m scripts.wait_for_services
elif [ -f "/usr/local/bin/wait_for_services.py" ]; then
  uv run python /usr/local/bin/wait_for_services.py
else
  echo "wait_for_services.py not found" >&2
  exit 1
fi

# Only run migrations if explicitly requested
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  uv run --no-dev python manage.py migrate --noinput
fi

echo "Executing Django command..."
exec "$@"
