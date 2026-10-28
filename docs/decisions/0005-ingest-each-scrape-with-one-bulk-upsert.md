# Ingest each scrape with one bulk upsert, keyed by name and phone

## Status

Accepted. Back-filled 28 Oct 2026.

## Context

A scrape returns every duty pharmacy of a city, hundreds for Istanbul, and
runs at least hourly. Saving rows one by one costs at least one query per
pharmacy.

## Decision

`add_scraped_data_to_db` loads the city's pharmacies once into a map keyed by
`(name, phone)`, then calls `bulk_create(..., ignore_conflicts=True)` for new
ones and `bulk_update` of `duty_start` and `duty_end` for known ones. The
whole write runs in one transaction with the `ScraperConfig.last_run` update
(`pharmacies/tasks.py`). `pharmacies/tests/test_scraper_performance.py`
fails if one ingest takes 10 queries or more.

## Consequences

- Only duty times are updated for a known pharmacy. A changed address or
  location in the source is ignored until the row is removed.
- A pharmacy that changes its name or phone becomes a new row; the old row
  stays.
- Every scraper must return the standard dict (`name`, `address`, `district`,
  `phone`, `coordinates`, `duty_start`, `duty_end`), and `Point` takes
  `(lng, lat)`.
