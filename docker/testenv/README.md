# testenv

A full dev stack (django, worker, beat, flower, db, redis) per git worktree, for
agent runs that must prove their work. Each run is its own Compose project
named `pod-<run-name>`, with loopback ports Docker picks
(`docker/dev/automation.env`), so several worktrees never collide with each
other or with the shared dev stack.

Run it from inside the worktree:

```bash
docker/testenv/testenv.sh prepare 134-20261025   # copy .env in, build images
docker/testenv/testenv.sh start                  # up, wait for validate, seed cities
docker/testenv/testenv.sh validate               # must pass before any test counts
docker/testenv/testenv.sh check                  # validate, ruff, format, mypy, full pytest
docker/testenv/testenv.sh reset                  # save logs, down -v, remove leftovers
```

Also: `exec <service> <cmd...>`, `logs`, `ps`, `stats` (memory per container)
and `measure` (cold and warm start, peak memory, disk, check time).

- **`.env`.** `prepare` copies `$TESTENV_ENV_FILE`, else the main checkout's
  `.env`, else `.env.example`, then forces test values: no `SENTRY_DSN`, no
  HTTPS redirect, no proxy SSL header, a dummy Maps key when there is none, and the stack's own DB and Redis settings.
  `ALLOWED_REFERERS` gains `http://localhost:8000` and `http://127.0.0.1:`; the
  Maps proxy matches by prefix, so the map page at the stack's URL loads.
- **validate** checks every service is running, Postgres and Redis answer,
  `manage.py check` and `migrate --check` pass, Django serves `/robots.txt`,
  the worker answers a Celery ping, beat has started and Flower is healthy.
- **check** runs every step to the end (no `-x`) and writes each step's output
  to the run's log folder. Its summary names every failed test.
- **Logs and state** live outside the worktree, in
  `~/.local/state/pod-testenv/<name>/`, so they survive the worktree's removal.
- **Buildx state** lives in `~/.local/state/pod-testenv/buildx/` (the script
  sets `BUILDX_CONFIG`), not `~/.docker/buildx`. On monolith, Coolify deploys
  leave root-owned files in `~/.docker/buildx` that break `compose build`.
- **reset** never refuses. It removes everything labelled with the run's
  Compose project. `reset --all` removes every `pod-*` stack; the shared dev
  stack is never touched.
- A shared `pod-testenv-uv-cache` volume keeps each container's `uv sync` fast.
- On SELinux hosts (monolith runs Fedora) the overlay turns off labelling for
  the app containers so they can read the bind-mounted worktree; beat restarts
  on failure because it can start before django has migrated.
- `start` runs `collectstatic`, since the tests render templates through the
  manifest storage, and `seed_cities`, since a fresh database has no City rows.
  Seeding also creates the hourly scraper tasks, so beat may scrape live sites.
- **Redis CLI.** The redis container has `REDISCLI_AUTH` set, so
  `testenv.sh exec redis redis-cli <cmd>` needs no password flag. The password
  is `REDIS_PASSWORD` in the worktree's `.env`; the container has no variable
  of that name, so `redis-cli -a "$REDIS_PASSWORD"` inside it sends an empty one.

## Cloud sessions (claude.ai/code)

testenv runs in a Claude Code cloud session too. The environment is set up in
the claude.ai/code UI, not in this repo:

- **Network access: Custom.** Tick "include default package managers" and add
  the hosts the image builds use that the default list may miss:

  ```text
  deb.debian.org
  security.debian.org
  apt.postgresql.org
  production.cloudflare.docker.com
  pkg-containers.githubusercontent.com
  ```

  The chamber sites are not on the list, so beat's scrapes fail there. Tests
  mock the network and `validate` does not scrape, so nothing else depends on them.
- **Environment variables:** none. `prepare` falls back to `.env.example` and
  fills in test values. Put no secrets here: anyone using the environment can
  read them.
- **Setup script:** runs once as root and is snapshotted, so it pulls the
  base images the builds need:

  ```bash
  #!/bin/bash
  set -euo pipefail
  nohup dockerd >/var/log/dockerd-setup.log 2>&1 &
  for _ in $(seq 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
  for image in python:3.13-slim postgres:15 redis:alpine ghcr.io/astral-sh/uv:latest; do
    docker pull "$image"
  done
  pkill dockerd || true
  for _ in $(seq 30); do pgrep -x dockerd >/dev/null || break; sleep 1; done
  ```

The snapshot keeps files but no processes. The SessionStart hook in
`.claude/settings.json` runs `scripts/cloud/start-docker.sh`, which starts
dockerd in each cloud session and does nothing locally.
