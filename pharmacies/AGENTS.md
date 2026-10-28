# PHARMACY DOMAIN KNOWLEDGE BASE

The only app: PostGIS models, city scrapers and duty-scheduling logic.

## Where to look

- **Add a city**: create `utils/<city>_scraper.py`, register it in `utils/utils.py:get_city_data`.
- **Nearest search**: `utils/utils.py:get_nearest_pharmacies_on_duty` (`Distance` annotation); travel time comes separately from Google Distance Matrix.
- **Ingest**: `utils/utils.py:add_scraped_data_to_db` (bulk UPSERT with a pre-fetched lookup map).
- **Rate limit**: `get_pharmacy_points` in `views.py` is rate-limited per client IP in `ratelimit.py`; the client-IP rule is [ADR 0003](../docs/decisions/0003-trust-one-proxy-hop-for-the-rate-limit-key.md).
- **Schedules**: `ScraperConfig` writes celery-beat rows, see [ADR 0002](../docs/decisions/0002-drive-scrape-schedules-from-the-database.md).

## Conventions

- **Scraper output** must be the standardized dict: `name`, `address`, `district`, `phone`, `coordinates` (`lat`/`lng`), `duty_start`, `duty_end`.
- **Turkish characters**: use `utils.py:normalize_string`.
- **GIS order**: `Point(longitude, latitude)`; validate scraped lat/lng before building a Point.

## Anti-patterns

- Looping `.save()` on ingest; use `bulk_create` / `bulk_update`.
- Registering scrapers anywhere but `get_city_data`.

## Testing

- Scrapers: mock `requests` (get or post). `tests/test_scraper_performance.py` guards ingest efficiency.
- Geo queries: test `Distance` with known coordinate pairs.
- `Pharmacy` has no unique constraint; `(name, phone)` is matched in Python only, and `ignore_conflicts=True` does not prevent duplicates ([ADR 0005](../docs/decisions/0005-identify-a-pharmacy-by-name-and-phone-and-never-delete-rows.md)).
