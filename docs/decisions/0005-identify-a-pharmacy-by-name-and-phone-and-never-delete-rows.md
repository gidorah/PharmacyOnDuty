# Identify a pharmacy by name and phone, and never delete rows

## Status

Accepted. Back-filled 28 Oct 2026 from commits 6b6a0eb (15 Feb 2025) and
43a51f4 (29 Dec 2025).

## Context

A scrape returns every duty pharmacy of a city and runs at least hourly.
Saving rows one by one cost at least one query per pharmacy.

## Decision

- A pharmacy's identity is `(name, phone)` within its city. Only application
  code enforces it: `Pharmacy` has no unique constraint, so the
  `ignore_conflicts=True` on `bulk_create` deduplicates nothing.
- `add_scraped_data_to_db` (`pharmacies/utils/utils.py`) loads the city's rows
  once, creates rows for unseen keys and bulk-updates `duty_start` and
  `duty_end` on known ones. `run_scraper` runs it in one transaction with the
  `ScraperConfig.last_run` update.
- Rows are never deleted. Whether a pharmacy is on duty comes only from its
  duty window at query time, not from whether it appeared in the last scrape.

Changing the identity key, deleting rows missing from a scrape, or adding a
unique constraint with `update_conflicts=True` needs a new record.

## Alternatives

- A unique constraint plus `bulk_create(update_conflicts=True)`: enforced by
  the database, but needs a migration and a cleanup of existing duplicates.
- Per-row `update_or_create`: simple, one or more queries per pharmacy.
- Delete and replace the city's rows on each scrape: no stale rows, but loses
  rows when a source returns a partial list.

## Consequences

- Duplicate rows are possible: a source listing a pharmacy twice, two scrapes
  of a city overlapping, or `phone` being empty for two pharmacies of the same
  name.
- Only duty times update. A changed address, district or location in the
  source is ignored, and a new name or phone makes a new row. These are
  accepted limitations, not goals; fixing them is allowed if this record is
  updated by a new one.
- `pharmacies/tests/test_scraper_performance.py` fails if one ingest takes 10
  queries or more. It does not cover the transaction or `last_run`.
- Every scraper returns the standard dict (`name`, `address`, `district`,
  `phone`, `coordinates` with `lat` and `lng`, `duty_start`, `duty_end`);
  `Point` takes `(lng, lat)`.
