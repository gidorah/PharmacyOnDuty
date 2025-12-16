#!/bin/sh
set -e

# Only run migrations if explicitly requested
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  uv run python manage.py migrate --noinput
fi

echo "Executing Django command..."
exec "$@"
