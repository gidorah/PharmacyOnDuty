# Production

How eczanerede.com runs today. Read from Coolify and the hosts on 28 Oct 2026.
Change this page in the same PR as any change to `docker/prod/` or to the
Coolify setup.

## Hosts

| Host | Coolify app | Runs | Built from |
|---|---|---|---|
| `unit-01` (Hetzner VPS) | `services` | django (gunicorn), beat, flower, db (PostGIS), redis | `docker/prod/services/docker-compose.yml` |
| `monolith` (home machine) | `workers` | Celery worker only | `docker/prod/workers/docker-compose.yml` |

Both apps build `docker/prod/Dockerfile`; the db service builds
`docker/postgis/Dockerfile`. Coolify Cloud (`app.coolify.io`) manages both
servers. The worker runs apart from the web stack on purpose: see
[ADR 0001](../decisions/0001-run-the-celery-worker-on-a-home-machine.md).

## Request path

```
browser ──HTTPS──▶ Traefik (Coolify proxy, unit-01) ──HTTP──▶ django :8000
```

- Traefik terminates TLS, so django runs with
  `DJANGO_ENABLE_SECURE_PROXY_SSL_HEADER=True` to trust `X-Forwarded-Proto`.
  Without it `SECURE_SSL_REDIRECT` loops.
- Traefik is one proxy hop, so `RATELIMIT_TRUSTED_PROXY_COUNT=1`
  ([ADR 0003](../decisions/0003-trust-one-proxy-hop-for-the-rate-limit-key.md)).
- `collectstatic` runs at container start; WhiteNoise serves static files.
- Flower is published at `flower.prod.eczanerede.onur.sh`, behind
  `FLOWER_BASIC_AUTH`.

## Scraping path

```
beat (unit-01) ──task──▶ redis (unit-01) ◀──Tailscale── worker (monolith)
                                                          │
                       db (unit-01) ◀──Tailscale──────────┘  writes duty times
```

- beat uses `django_celery_beat`'s `DatabaseScheduler`; the schedule lives in
  the database, not in code
  ([ADR 0002](../decisions/0002-drive-scrape-schedules-from-the-database.md)).
- The worker (`scraper@<host>`) reaches Redis and Postgres on `unit-01`'s
  Tailscale address. `unit-01` publishes them through `REDIS_HOST_PORT` and
  `DB_HOST_PORT`; the compose defaults bind to `127.0.0.1`, and Coolify sets
  the production values. Whether those bind only to the Tailscale address is
  tracked in #242.
- The worker's compose passes in only `CELERY_BROKER_URL` and the `DB_*`
  variables. Other variables set on the Coolify `workers` app are not used.

## Deploys

- Both apps deploy automatically on every push to `main`, with the
  docker-compose build pack and the base directory `/`.
- Preview deployments and Coolify health checks are off. The factory checks a
  deploy after its own merges (software-factory D39, D57).
- `django` runs migrations on start (`RUN_MIGRATIONS=true`,
  `scripts/entrypoint.sh`); `scripts/wait_for_services.py` waits for the
  database and Redis first.

## Not used in production

The root `Procfile`, `Aptfile`, `nginx.conf`, `remotedev_nginx.conf.template`
and `scripts/on_deploy.sh` date from the earlier Heroku and Nginx setup.
Nothing in the Coolify build reads them.

## Secrets and settings

Values live in Coolify, per app. The names the code reads are in
`PharmacyOnDuty/settings.py`; the production-only switches are set in
`docker/prod/services/docker-compose.yml` with their defaults and reasons.
