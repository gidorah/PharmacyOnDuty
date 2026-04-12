# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Pharmacy on-duty finder for Turkey (Eskişehir, Istanbul, Ankara). Django 5 + GeoDjango/PostGIS, Celery/Redis, Tailwind. Python 3.13, `uv` for deps, `just` as task runner, Docker Compose for environments.

## Commands

Everything routes through `just`, which shells into the dev Docker Compose stack. Do not invoke `python`/`pytest`/`pip` on the host — use `uv run` inside the container (or via `just`).

```bash
just dev-up          # Start dev stack (django, db, redis, celery, beat, flower)
just dev-rebuild     # Rebuild + start
just dev-down
just dev-django      # Shell into the django container
just dev-db          # psql into the PostGIS db
just logs <service>  # Tail one service

just migrate / just makemigrations
just shell           # Django shell
just seed            # Run seed_cities management command
just test            # Runs `manage.py test` inside container

# Single test via pytest (preferred for dev):
just manage "test pharmacies.tests.test_views.TestNearest::test_happy_path"
# or inside `just dev-django`:
uv run pytest pharmacies/tests/test_views.py::TestNearest::test_happy_path -x
```

Lint/format/type-check (run inside container or via `uv run`):
```bash
uv run ruff check --fix .
uv run ruff format .
uv run mypy .
```

Pytest is configured via `pyproject.toml` with `DJANGO_SETTINGS_MODULE=PharmacyOnDuty.settings` and `--cov=pharmacies`. Test discovery covers both `tests/` (top-level infra/perf tests) and `pharmacies/tests/` (domain tests).

## Architecture

**Django project**: `PharmacyOnDuty/` holds settings, urls, celery app, sitemaps, and `database_config.py` (env-driven DB selection).

**Core domain**: `pharmacies/` is the only app.
- `models.py` — `City`, `Pharmacy` (PostGIS Point), `ScraperConfig`, `WorkingSchedule`. `ScraperConfig.save()` mutates `django-celery-beat` `PeriodicTask` rows, so scraping cadence is controlled from the DB, not code.
- `utils/` — one `*_scraper.py` per city chamber (`ankaraeo`, `eskisehireo`, `istanbul_saglik`) plus shared helpers in `utils.py`. Scrapers must return the standardized dict (`name`, `address`, `district`, `phone`, `coordinates.{lat,lng}`, `duty_start`, `duty_end`) and are registered in `utils/utils.py:get_city_data` — do not wire them up anywhere else.
- `tasks.py` — Celery entrypoints that invoke scrapers; results ingested via `utils.py:add_scraped_data_to_db` (bulk UPSERT with a pre-fetched lookup map; **never** loop `.save()`).
- `views.py` — geo-spatial endpoints. Nearest-pharmacy search uses `Distance` annotations via `utils.py:get_nearest_pharmacies_on_duty`; travel time uses Google Distance Matrix separately.
- `management/commands/seed_cities.py` — bootstraps City rows.

**GIS gotcha**: GeoDjango `Point(x, y)` expects `(lng, lat)`, not `(lat, lng)`. Always validate scraped coordinates before constructing a Point. Use `utils.py:normalize_string` for Turkish character handling.

**Frontend**: `theme/` is a `django-tailwind` app. Build CSS with `uv run python manage.py tailwind build` (or the dev watcher). Don't hand-write raw CSS — use Tailwind classes.

**Docker layout** (`docker/`):
- `dev/` — hot-reload stack, mounts host source, runs as UID 1000 (`python` user), isolated venv at `/opt/venv` (never mount host `.venv`).
- `prod/services/` — web stack (gunicorn + nginx + redis + db).
- `prod/workers/` — scalable Celery worker stack.
- `postgis/` — custom PostGIS image with auto-init.
- Containers run `uv sync` on startup; entrypoint scripts live in `/usr/local/bin/` so they aren't masked by volume mounts. `scripts/wait_for_services.py` gates startup on DB/Redis.

**Observability**: Sentry auto-initializes if `SENTRY_DSN` is set. Flower is exposed at `localhost:5555` in dev. `debugpy` auto-attaches if its port env var is set.

**Deployment**: Coolify/PaaS via `Procfile` + `Aptfile` (GDAL/Proj system deps) + `scripts/on_deploy.sh`.

## Conventions & gates

- **`uv` only.** No `pip`, no manual venvs. `uv sync` / `uv run` / `uv add`.
- **Strict mypy** (`python_version = 3.13`, `strict = true`) — don't weaken it; fix types properly.
- **Ruff** is the sole linter/formatter (`E4/E7/F/I/UP`, line length 88, double quotes). Never suppress a lint error to make it go away — if you can't resolve it, ask.
- **Commits**: use the `committing-changes` skill. Direct `git commit` is prohibited by global policy.
- **Bulk DB ops**: `bulk_create(ignore_conflicts=True)` / `bulk_update`. Ingest performance is enforced by tests in `pharmacies/tests/test_scraper_performance.py`.
- **Time**: `timezone.now()`, never `datetime.now()`.
- **Scraper tests** mock `requests.get`; don't hit the network.

## Companion docs

- `AGENTS.md` (root) and `pharmacies/AGENTS.md`, `docker/AGENTS.md` — per-area knowledge bases; read the relevant one before non-trivial edits in that area.
- `GEMINI.md` — mostly overlaps with this file; kept for the Gemini review workflows in `.github/`.
- `readme.md` — long-form product/feature doc.
