#!/bin/sh
set -e

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Executing Django command..."
exec "$@"
