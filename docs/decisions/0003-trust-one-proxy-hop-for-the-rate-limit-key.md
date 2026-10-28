# Trust one proxy hop for the rate-limit key, and fail open

## Status

Accepted. Back-filled 28 Oct 2026 from #125, PR #200 and its review.

## Context

`get_pharmacy_points` calls Google's paid APIs (Geocoding, Distance Matrix,
Places), so it is rate-limited per client IP before any call
(`pharmacies/ratelimit.py`, default `30/m`). Behind Coolify's Traefik every
request arrives from the proxy's address, so `REMOTE_ADDR` would put all
visitors under one counter. Trusting more `X-Forwarded-For` entries than
there are proxies lets a client choose its own key.

## Decision

- The key is the Nth entry from the right of `X-Forwarded-For`, where N is
  `RATELIMIT_TRUSTED_PROXY_COUNT`. With fewer than N entries it falls back to
  `REMOTE_ADDR`. The code default is 0 (`REMOTE_ADDR`); production sets 1 for
  Traefik in `docker/prod/services/docker-compose.yml`. Use 2 if Cloudflare
  proxying is ever put in front of Coolify.
- Counters live in Redis (the `ratelimit` cache alias: the broker's Redis
  unless `RATELIMIT_CACHE_URL` is set), shared by all gunicorn workers.
- If Redis is unavailable the request is allowed and the error logged.

Do not key on the leftmost `X-Forwarded-For` entry, do not use `REMOTE_ADDR`
alone in production, do not make the limiter fail closed, and do not move the
counters to the per-process default cache.

## Alternatives

- Fail closed: protects the Google bill during a Redis outage, but takes the
  main endpoint down with Redis.
- Per-process counters (the default LocMemCache): no Redis dependency, but
  each gunicorn worker counts separately.

## Consequences

- Adding or removing a proxy in front of the site changes the right value. A
  wrong value either merges all visitors under one key or lets them spoof it,
  silently.
- A Redis outage turns the limit off rather than taking the site down.
- The limiter shares the broker's Redis database.
