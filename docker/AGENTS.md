# AGENTS: DOCKER

Compose stacks and images. Directory names say what each holds; only the
non-obvious parts are here.

- `dev/`: hot-reload stack that mounts the host source. Services: django, db,
  redis, worker, beat, flower.
- `prod/`: one `Dockerfile` serving two Coolify apps, `prod/services/`
  (django, db, redis, beat, flower) and `prod/workers/` (worker). See
  [docs/explanation/production.md](../docs/explanation/production.md); update it
  with any change here.
- `testenv/`: per-worktree test stack for agent runs, see
  [its README](testenv/README.md).
- `scripts/` here holds only `setup-postgis.sh`. The entrypoint and
  `wait_for_services.py` live in the root `scripts/` and the Dockerfiles copy
  them to `/usr/local/bin/`, so volume mounts do not mask them. The latter gates
  startup on DB and Redis.

## Conventions

- App containers run as the `python` user (UID 1000), never root.
- The venv lives at `/opt/venv` (`UV_PROJECT_ENVIRONMENT`). Dev containers run
  `uv sync` on startup; the prod image syncs at build time (`--frozen --no-dev`). Never mount the host `.venv`: its binaries are not Linux-container ones.
- `uv` only, no direct `pip`.
