#!/usr/bin/env bash
# Writes .env for CI from .env.example with the test values that
# docker/testenv/testenv.sh (write_env) sets, so CI and the factory's testenv
# check run under the same settings. The differences: the keys are fixed
# placeholders, not secrets, and Redis has no password (see ci.yml).
set -euo pipefail

cp .env.example .env

set_env() {
  local key=$1 value=$2
  sed -i "/^$key=/d" .env
  printf '%s=%s\n' "$key" "$value" >>.env
}

set_env SENTRY_DSN ""
# Tests reload settings with this unset; a value in .env would come back.
sed -i "/^DJANGO_ENABLE_SECURE_PROXY_SSL_HEADER=/d" .env
set_env GOOGLE_MAPS_API_KEY ci-placeholder-not-a-key
set_env DJANGO_SECRET_KEY ci-placeholder-not-a-secret
set_env DJANGO_ALLOWED_HOSTS "localhost 127.0.0.1 django"
set_env ALLOWED_REFERERS \
  "https://eczanerede.com https://www.eczanerede.com http://localhost:8000 http://127.0.0.1:"
set_env DJANGO_SECURE_SSL_REDIRECT False
set_env DJANGO_SESSION_COOKIE_SECURE False
set_env DJANGO_CSRF_COOKIE_SECURE False
set_env DB_HOST db
set_env DB_PORT 5432
set_env DB_USER postgres
set_env DB_PASSWORD password
set_env REDIS_PASSWORD ""
set_env CELERY_BROKER_URL "redis://redis:6379/0"
