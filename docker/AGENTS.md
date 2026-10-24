# AGENTS: DOCKER

## OVERVIEW
Container orchestration for GeoDjango, PostGIS, and Celery stacks. Manages development and production environments.

## STRUCTURE
- `dev/`: Hot-reloading development stack with host source mounting.
- `prod/services/`: Production web stack (Django, Redis, DB).
- `prod/workers/`: Dedicated scalable Celery worker stack.
- `postgis/`: Custom spatial database with auto-initialization.

## WHERE TO LOOK
- `dev/Dockerfile`: Development image with dev-tools and hot-reload support.
- `prod/Dockerfile`: Optimized production image with frozen dependencies.
- `docker-compose.yml`: Service definitions across `dev/` and `prod/`.
- `scripts/`: Internal orchestration (entrypoints, health checks).

## CONVENTIONS
- **Non-root**: Processes MUST run as `python` user (UID 1000).
- **uv logic**: `uv sync` for dependency sync; `uv run` for execution.
- **Isolated Venv**: Persisted in `/opt/venv` to avoid host mount conflicts.
- **Health Checks**: `wait_for_services.py` ensures DB/Redis availability.

## ANTI-PATTERNS
- **Root execution**: Forbidden; security violation and permission drift.
- **Local venv mount**: Mapping host `.venv` to container breaks Linux binaries.
- **Direct pip**: Bypasses `uv` integrity and performance benefits.
