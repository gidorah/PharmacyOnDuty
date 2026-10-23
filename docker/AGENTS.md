# AGENTS: DOCKER

The root `AGENTS.md` covers this folder's layout and the container conventions: the `python` user (UID 1000), `uv` only, the venv at `/opt/venv`, never mounting the host `.venv`, and `wait_for_services.py`. This file holds only what the root file doesn't.

## WHERE TO LOOK
- `dev/Dockerfile`: Development image with dev-tools and hot-reload support.
- `prod/Dockerfile`: Production image with frozen dependencies (`uv sync --frozen --no-dev`).
- `dev/docker-compose.yml`, `prod/services/docker-compose.yml`, `prod/workers/docker-compose.yml`: Service definitions.
- `scripts/setup-postgis.sh`: Init script that `postgis/Dockerfile` copies into the database image.

## ANTI-PATTERNS
- **Root execution**: Forbidden; security violation and permission drift.
