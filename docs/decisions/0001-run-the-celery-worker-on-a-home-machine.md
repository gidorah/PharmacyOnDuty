# Run the Celery worker on a home machine, apart from the web stack

## Status

Accepted. Back-filled 28 Oct 2026.

## Context

The scrapers read the city pharmacy chambers' websites
(`pharmacies/utils/*_scraper.py`). The earlier stack notes
(`conductor/tech-stack.md`) record that these sites geoblock requests, and
that the workers ran on a home Raspberry Pi to get around it. The web stack
runs on a Hetzner VPS (`unit-01`).

## Decision

The Celery worker runs as its own Coolify app (`workers`,
`docker/prod/workers/docker-compose.yml`) on a home machine, today `monolith`.
It reaches Redis and Postgres on `unit-01` over Tailscale. Beat, Flower,
Redis and Postgres stay with django on `unit-01`.

## Consequences

- Scraping stops when the home machine or its Tailscale link is down, while the
  site keeps serving the last scraped duty times.
- `unit-01` must publish Redis and Postgres to the tailnet, and nowhere else
  (#242).
- A scraper change reaches production only when both Coolify apps have
  deployed.
- Moving the worker to the VPS would need the geoblocking checked again first.
