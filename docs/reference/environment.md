# Environment variables

Every environment variable the project reads, with its default, what it does and
where production sets it. `tests/test_environment_reference.py` checks this page
against `PharmacyOnDuty/settings.py`, `PharmacyOnDuty/database_config.py`,
`scripts/` and the three compose files under `docker/dev` and `docker/prod`, and
CI runs it. Add or remove a row in the same pull request that adds or removes a
variable. `.env.example` lists the variables the dev stack uses; commented lines
there show a variable that has a code default.

Production runs as two Coolify apps: `services` (unit-01, `docker/prod/services/docker-compose.yml`)
and `workers` (monolith, `docker/prod/workers/docker-compose.yml`). See
[production](../explanation/production.md) for the hosts. Values are never kept in
the repository.

## Read by the code

Booleans read through `_env_bool` accept `1`, `true`, `yes` or `on`, in any case;
anything else is false.

| Variable | Default | What it does | Where production sets it |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | none | Django `SECRET_KEY`. Required. | Coolify (`services` app) |
| `DJANGO_DEBUG` | `False` | Django `DEBUG`. Only the exact value `True` enables it. | `services` compose file sets `False` |
| `DJANGO_ALLOWED_HOSTS` | empty | Space-separated host names. `localhost` and `127.0.0.1` are always added. | Coolify (`services` app) |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Space-separated origins trusted for CSRF. | Coolify (`services` app) |
| `DJANGO_ENABLE_SECURE_PROXY_SSL_HEADER` | false | Trust `X-Forwarded-Proto` from the TLS-terminating proxy. | `services` compose file sets `True` |
| `DJANGO_SECURE_SSL_REDIRECT` | not `DJANGO_DEBUG` | Redirect HTTP to HTTPS. | `services` compose file, default `True` |
| `DJANGO_SESSION_COOKIE_SECURE` | not `DJANGO_DEBUG` | Send the session cookie over HTTPS only. | `services` compose file, default `True` |
| `DJANGO_CSRF_COOKIE_SECURE` | not `DJANGO_DEBUG` | Send the CSRF cookie over HTTPS only. | `services` compose file, default `True` |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000`, or `0` when `DJANGO_DEBUG` is on | `Strict-Transport-Security` max-age. | `services` compose file, default `3600` |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | not `DJANGO_DEBUG` | Add `includeSubDomains` to the HSTS header. | `services` compose file, default `True` |
| `DJANGO_SECURE_HSTS_PRELOAD` | false | Add `preload` to the HSTS header. | `services` compose file, default `False` |
| `GOOGLE_MAPS_API_KEY` | none | Google Maps key, used by the Maps proxy and the Distance Matrix calls. | Coolify (`services` app) |
| `GOOGLE_MAPS_MAP_ID` | `DEMO_MAP_ID` | Google vector Map ID. Production needs a real one. | Coolify (`services` app) |
| `ALLOWED_REFERERS` | empty | Space-separated origins allowed to load the Maps proxy script ([ADR 0004](../decisions/0004-proxy-the-google-maps-script-behind-a-referer-allow-list.md)). | Coolify (`services` app) |
| `DATABASE_URL` | unset | Database URL, parsed first. The field variables below override its parts. | Not set |
| `DB_NAME`, `PGDATABASE`, `POSTGRES_DB` | `postgres` | Database name. The first non-empty one wins. | Coolify (`workers` and `services` apps) sets `DB_NAME` |
| `DB_USER`, `PGUSER`, `POSTGRES_USER` | `postgres` | Database user. The first non-empty one wins. | Coolify (`workers` and `services` apps) sets `DB_USER` |
| `DB_PASSWORD`, `PGPASSWORD`, `POSTGRES_PASSWORD` | `password` | Database password. The first non-empty one wins. | Coolify (`workers` and `services` apps) sets `DB_PASSWORD` |
| `DB_HOST`, `PGHOST`, `POSTGRES_HOST` | `db` | Database host. The first non-empty one wins. | `services` compose file sets `db`; Coolify (`workers` app) sets `DB_HOST` |
| `DB_PORT`, `PGPORT`, `POSTGRES_PORT` | `5432` | Database port. The first non-empty one wins. | Not set |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis URL for Celery. `scripts/wait_for_services.py` skips the Redis wait when it is unset. | `services` compose file builds it from `REDIS_PASSWORD`; Coolify (`workers` app) |
| `RATELIMIT_CACHE_URL` | `CELERY_BROKER_URL` | Redis URL for the rate-limit cache. | Not set |
| `PHARMACY_POINTS_RATE_LIMIT` | `30/m` | Rate limit of the pharmacy points endpoint. | Not set |
| `RATELIMIT_TRUSTED_PROXY_COUNT` | `0` | `0` keys the limit on `REMOTE_ADDR`. `N` trusts the Nth-from-right `X-Forwarded-For` entry. See [ADR 0003](../decisions/0003-trust-one-proxy-hop-for-the-rate-limit-key.md). | `services` compose file, default `1` |
| `SENTRY_DSN` | unset | Turns Sentry on when set. | Coolify (`services` app) |
| `REMOTE_DEBUGGING_PORT` | unset | debugpy port. It listens only when `DJANGO_DEBUG` is also on. | Not set (the dev compose file sets `5678`) |
| `DOTENV_PATH` | unset (python-dotenv finds `.env`); `.env` in `scripts/wait_for_services.py` | Path of the dotenv file to load. | Not set |
| `DJANGO_SETTINGS_MODULE` | `PharmacyOnDuty.settings` in `scripts/record_distance_matrix.py` | Django settings module. | `workers` compose file |
| `RUN_MIGRATIONS` | unset | `scripts/entrypoint.sh` runs `migrate` when it is `true`. | `services` compose file sets `true` |
| `CLAUDE_CODE_REMOTE` | unset | Set by Claude Code cloud sessions; `scripts/cloud/start-docker.sh` only runs there. Not used in production. | Not set |
| `CLAUDE_PROJECT_DIR` | unset | Set by Claude Code cloud sessions; project path for `scripts/cloud/start-docker.sh`. Not used in production. | Not set |

The `POSTGRES_*` names in the compose `db` service configure the PostGIS image;
they are separate from the Django aliases above.

## Read by Docker Compose

These are interpolated in the compose files and never reach Django directly.

| Variable | Default | What it does | Where production sets it |
|---|---|---|---|
| `REDIS_PASSWORD` | none | Redis password; also builds `CELERY_BROKER_URL`. | Coolify (`services` app) |
| `DJANGO_HOST_PORT` | `127.0.0.1:8000` (prod), `8000` (dev) | Host port that publishes Django. | Not set |
| `DB_HOST_PORT` | `127.0.0.1:5432` | Host port that publishes Postgres (prod `services` file). | Coolify (`services` app) |
| `POSTGRES_HOST_PORT` | `5432` | Host port that publishes Postgres (dev file). | Not set |
| `REDIS_HOST_PORT` | `127.0.0.1:6379` (prod), `6379` (dev) | Host port that publishes Redis. | Coolify (`services` app) |
| `FLOWER_HOST_PORT` | `127.0.0.1:5555` (prod), `5555` (dev) | Host port that publishes Flower. | Not set |
| `FLOWER_BASIC_AUTH` | empty | `user:password` for Flower basic auth. | Coolify (`services` app) |
| `REMOTE_DEBUGGING_HOST_PORT` | `5678` | Host port for the debugpy port (dev file). | Not set |

`docker/dev/automation.env` sets the host ports to `127.0.0.1:0` for scheduled runs.
