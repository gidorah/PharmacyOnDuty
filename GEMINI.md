# PharmacyOnDuty (Eczanerede) Project Context

## Project Overview
**PharmacyOnDuty** (Eczanerede) is a mobile-first web application designed to help users find open and on-duty pharmacies in Turkish cities (currently Eskişehir, Istanbul, Ankara). It features real-time status updates, location-based search, interactive maps (Google Maps), and turn-by-turn directions.

## Tech Stack
- **Language:** Python 3.13
- **Framework:** Django 5.1
- **Database:** PostgreSQL 15 with PostGIS (Spatial Data)
- **Task Queue:** Celery + Redis (Broker & Result Backend)
- **Monitoring:** Flower
- **Frontend:** HTML5, Tailwind CSS, JavaScript (Google Maps API, Hammer.js for gestures)
- **Dependency Management:** `uv`
- **Containerization:** Docker & Docker Compose

## Architecture
- **Core App (`pharmacies/`):** Handles models (`City`, `Pharmacy`, `WorkingSchedule`), API views, and business logic.
- **Scrapers (`pharmacies/utils/`):** Custom scrapers for different city pharmacy chambers, running asynchronously via Celery.
- **Theme (`theme/`):** Tailwind CSS configuration and static assets.
- **Docker:**
    - **Dev:** `docker/dev/` (Local development with hot-reload, debugpy).
    - **Prod:** `docker/prod/` (Production optimized, Gunicorn, Nginx).
    - **PostGIS:** Custom PostGIS image.

## Development Setup & Workflow

### Dependency Management
The project uses **uv** for fast package management.
- **Install deps:** `uv sync` (creates/updates `.venv`).
- **Add dep:** `uv add <package>`.
- **Run command in venv:** `uv run <command>`.

### Docker Environment
The project relies heavily on Docker Compose, managed via `just`.
- **Entrypoints:** Located in `/usr/local/bin/` inside containers to avoid volume mount masking.
- **Syncing:** Dev containers explicitly run `uv sync` on startup to ensure dependencies are up-to-date.

### Key Commands (via `just`)
- **Start Dev:** `just dev-up` (Starts Django, DB, Redis, Worker, Beat, Flower).
- **Rebuild Dev:** `just dev-rebuild` (Rebuilds images and starts).
- **Logs:** `just dev-logs` or `just logs <service>`.
- **Shell:** `just shell` (Django shell).
- **Migrations:** `just make-migrations`, `just migrate`.
- **Tests:** `just test`.
- **Clean:** `just clean` (Removes containers/volumes).

### Manual Commands (if not using `just`)
- **Run Server:** `uv run python manage.py runserver 0.0.0.0:8000`
- **Celery Worker:** `uv run celery -A PharmacyOnDuty worker -l info`

## Code Standards & Conventions
(Derived from `AGENTS.md`)

- **Linting & Formatting:** Ruff. Run `uv run ruff check --fix .` and `uv run ruff format .`.
- **Type Hints:** Strict typing required. Use `mypy`.
- **Imports:** Standard Lib -> Django -> Third-party -> Local.
- **Naming:** `snake_case` for functions/vars, `PascalCase` for classes.
- **Django Best Practices:**
    - Use `timezone.now()` for time.
    - Use GeoDjango for spatial queries.
    - Use `bulk_create`/`bulk_update` for efficiency.
- **Comments:** Focus on *why*, not *what*.

## Key Configuration Files
- **`pyproject.toml`**: Dependencies and tool config (Ruff, Mypy).
- **`justfile`**: Command runner recipes.
- **`docker-compose.yml`**: Dev environment orchestration.
- **`.env`**: Environment variables (Database creds, API keys).
- **`docker/dev/Dockerfile`**: Development container definition.

## Important Notes
- **Flower:** Accessible at `http://localhost:5555` for monitoring Celery.
- **Scrapers:** Located in `pharmacies/utils/`. Triggered by Celery beat or manual tasks.
- **Frontend Build:** Tailwind is built via `uv run python manage.py tailwind build`.
