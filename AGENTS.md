# PROJECT KNOWLEDGE BASE

**Generated:** 2025-12-30
**Commit:** HEAD
**Branch:** main

## OVERVIEW

Pharmacy on Duty finder for Turkey. Django 5 (GeoDjango/PostGIS), Tailwind CSS, Celery/Redis.
**AI-First Architecture**: Uses `conductor/` for development governance and Gemini for CI/CD.

## STRUCTURE

```
./
├── pharmacies/       # Core domain (models, scrapers, views)
├── conductor/        # Dev governance (tracks, specs, plans) - SOURCE OF TRUTH
├── theme/            # Tailwind CSS frontend (django-tailwind)
├── docker/           # Environment config (dev/prod/workers)
├── scripts/          # Ops scripts (entrypoints, data prep)
└── .github/          # Gemini AI workflows (review, triage)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Start New Feature** | `conductor/tracks/` | MUST create track & `plan.md` first |
| Add City Scraper | `pharmacies/utils/` | Inherit `BaseScraper`, mocking required in tests |
| DB Schema | `pharmacies/models.py` | `Pharmacy` (GIS), `City` (Schedule logic) |
| BG Worker Logic | `pharmacies/tasks.py` | Celery tasks, scheduled via DB models |
| API Endpoints | `pharmacies/views.py` | Geo-spatial queries (nearest) |
| CI/CD Logic | `.github/workflows/` | AI-driven (Gemini + MCP) |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `Pharmacy` | Model | `pharmacies/models.py` | Core GIS entity |
| `ScraperConfig` | Model | `pharmacies/models.py` | Controls scraping schedule |
| `seed_cities` | Command | `pharmacies/management/` | Data initialization |
| `wait_for_services`| Script | `scripts/` | Docker startup check |

## CONVENTIONS

- **Workflow**: "Conductor" protocol. Update `plan.md` → Red/Green/Refactor.
- **Deps**: `uv` ONLY. `uv sync`, `uv run`. No `pip`.
- **Commands**: `just` is the task runner. `just dev-up`, `just test`.
- **Type Hints**: Strict `mypy` (v3.13).
- **Testing**: `pytest` + `pytest-django`. Goal >90% cov.
- **GIS**: `Aptfile`/`on_deploy.sh` handle GDAL/Proj deps.

## ANTI-PATTERNS (THIS PROJECT)

- **Ignoring Conductor**: working without a track/plan is FORBIDDEN.
- **Manual Venv**: Use `uv run`.
- **Raw CSS**: Use Tailwind classes in `theme/`.
- **Hardcoded Schedules**: Use `django-celery-beat` DB models.
- **O(N) Queries**: Bulk ingest must be O(1) (verified by tests).

## UNIQUE STYLES

- **Self-Mutating Schedule**: Models (`ScraperConfig`) update Celery PeriodicTasks on save.
- **AI Integration**: Gemini workflows handle review/triage via MCP.
- **Remote Debug**: Auto-enables `debugpy` if port env var set.

## COMMANDS

```bash
just dev-up       # Start full stack (Docker)
just test         # Run pytest
just migrate      # DB migrations
just seed         # Init city data
just tailwind     # Build CSS
```

## NOTES

- **PostGIS**: Essential. `docker/` handles it.
- **Sentry**: Auto-init if `SENTRY_DSN` present.
- **Deployment**: Coolify/PaaS ready via `Procfile` & `Aptfile`.

## Code Standards & Conventions

- **Linting & Formatting:** Ruff. Run `uv run ruff check --fix .` and `uv run ruff format .`.
- **Type Hints:** Strict typing required. Use `mypy`.
- **Imports:** Standard Lib -> Django -> Third-party -> Local.
- **Naming:** `snake_case` for functions/vars, `PascalCase` for classes.
- **Django Best Practices:**
    - Use `timezone.now()` for time.
    - Use GeoDjango for spatial queries.
    - Use `bulk_create`/`bulk_update` for efficiency.
- **Comments:** Focus on *why*, not *what*.
