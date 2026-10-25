# testenv

A full dev stack (django, worker, beat, flower, db, redis) per git worktree, for
agent runs that must prove their work. Each run is its own Compose project
named `pod-<run-name>`, with loopback ports Docker picks
(`docker/dev/automation.env`), so several worktrees never collide with each
other or with the shared dev stack.

Run it from inside the worktree:

```bash
docker/testenv/testenv.sh prepare 134-20261025   # copy .env in, build images
docker/testenv/testenv.sh start                  # up, then wait for validate
docker/testenv/testenv.sh validate               # must pass before any test counts
docker/testenv/testenv.sh check                  # validate, ruff, format, mypy, full pytest
docker/testenv/testenv.sh reset                  # save logs, down -v, remove leftovers
```

Also: `exec <service> <cmd...>`, `logs`, `ps`, `stats` (memory per container)
and `measure` (cold and warm start, peak memory, disk, check time).

- **`.env`.** `prepare` copies `$TESTENV_ENV_FILE`, else the main checkout's
  `.env`, else `.env.example`, then forces test values: no `SENTRY_DSN`, no
  HTTPS redirect, no proxy SSL header, a dummy Maps key when there is none, and the stack's own DB and Redis settings.
- **validate** checks every service is running, Postgres and Redis answer,
  `manage.py check` and `migrate --check` pass, Django serves `/robots.txt`,
  the worker answers a Celery ping, beat has started and Flower is healthy.
- **check** runs every step to the end (no `-x`) and writes each step's output
  to the run's log folder.
- **Logs and state** live outside the worktree, in
  `~/.local/state/pod-testenv/<name>/`, so they survive the worktree's removal.
- **reset** never refuses. It removes everything labelled with the run's
  Compose project. `reset --all` removes every `pod-*` stack; the shared dev
  stack is never touched.
- A shared `pod-testenv-uv-cache` volume keeps each container's `uv sync` fast.
- On SELinux hosts (monolith runs Fedora) the overlay turns off labelling for
  the app containers so they can read the bind-mounted worktree; beat restarts
  on failure because it can start before django has migrated.
- `start` runs `collectstatic`, since the tests render templates through the
  manifest storage.
