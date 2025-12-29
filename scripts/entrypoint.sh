#!/bin/sh
set -e

echo "Waiting for services to be ready..."
if [ -f "/usr/local/bin/wait_for_services.py" ]; then
  uv run python /usr/local/bin/wait_for_services.py
else
  uv run python scripts/wait_for_services.py
fi

# Only run migrations if explicitly requested
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  uv run --no-dev python manage.py migrate --noinput
fi

echo "Executing Django command..."
exec "$@"
