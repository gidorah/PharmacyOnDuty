# Run the Celery worker on a home machine, apart from the web stack

## Status

Accepted. Back-filled 28 Oct 2026. The reason is recorded in one old note
only and has not been re-tested since the worker moved to `monolith`.

Amended 28 Oct 2026 by #249: the worker now receives `SENTRY_DSN`.

## Context

The scrapers read the chambers' websites (`pharmacies/utils/*_scraper.py`).
The earlier stack notes (`conductor/tech-stack.md`) say the workers ran on a
home Raspberry Pi "to bypass geoblocking restrictions on scraping targets".
Nobody has checked since whether a fetch from the VPS (`unit-01`) is blocked.

## Decision

The Celery worker runs as its own Coolify app (`workers`,
`docker/prod/workers/docker-compose.yml`) on a home machine, today `monolith`,
and is the only worker on the production broker. It reaches Redis and
Postgres on `unit-01` over Tailscale. Beat, Flower, Redis and Postgres stay
with django on `unit-01`.

Do not add a Celery worker to `docker/prod/services/` or point any other
worker at the production broker: no queue routing sends scrapes to the home
machine; it gets them only because it is the only worker.

## Alternatives

- Worker on the VPS with the rest of the stack: simpler, no Tailscale
  exposure, but (per the old note) blocked by the sources.
- A proxy or VPN exit in Turkey for the scrapers only: not tried.

## Consequences

- When the home machine or its Tailscale link is down, scraping stops. Duty
  windows run out within a day, after which the site shows no duty
  pharmacies. Beat keeps queueing tasks in Redis; the worker runs the backlog
  when it is back.
- `unit-01` must publish Redis and Postgres to the tailnet and nowhere else;
  not yet confirmed on the server (#242).
- The worker gets only `CELERY_BROKER_URL`, `DB_*` and `SENTRY_DSN`: no
  Google key. A new task that needs another setting must have it added to the
  worker compose.
- A scraper change takes effect when `workers` deploys. Both apps deploy on
  every push to `main` and django migrates on start, so for a short time the
  worker can run older code against a newer schema: migrations must stay
  compatible with the previous worker.
- Moving the worker to the VPS needs the geoblocking checked first.
