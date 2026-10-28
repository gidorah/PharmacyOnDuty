# PHARMACY DOMAIN KNOWLEDGE BASE

## OVERVIEW
Core domain handling PostGIS models, external data scrapers, and duty-scheduling logic.

## STRUCTURE
- `models.py`: `Pharmacy` (GIS Point), `City` (Schedule), `ScraperConfig` (Celery trigger).
- `utils/`: City scrapers (`ankaraeo`, `eskisehireo`, `istanbul_saglik`) + GIS helpers.
- `tasks.py`: Celery entrypoints for city-specific scraping.
- `views.py`: Geo-spatial API endpoints for nearest-pharmacy search. `get_pharmacy_points` is rate-limited per client IP (`ratelimit.py`, Redis `"ratelimit"` cache alias; `PHARMACY_POINTS_RATE_LIMIT`, default `30/m`; `RATELIMIT_TRUSTED_PROXY_COUNT`, default 0 = `REMOTE_ADDR`).
- `management/`: `seed_cities.py` for bootstrapping system.

## WHERE TO LOOK
- **Add City**: Create `utils/<city>_scraper.py` -> Register in `utils/utils.py:get_city_data`. How the existing scrapers read their sources and duty windows: [`docs/explanation/scraping.md`](../docs/explanation/scraping.md).
- **Tune Search**: `utils/utils.py:get_nearest_pharmacies_on_duty` (Annotation logic).
- **Fix Data**: `utils/utils.py:add_scraped_data_to_db` (UPSERT logic with pre-fetching map).

## CONVENTIONS
- **GIS Order**: `Point(longitude, latitude)` - standard for GeoDjango.
- **Scraper Output**: MUST return standardized dict: `name`, `address`, `district`, `phone`, `coordinates` (`lat`/`lng`), `duty_start`, `duty_end`.
- **String Normalization**: Use `utils.py:normalize_string` for Turkish char handling.
- **Distance**: Use `Distance` annotation for DB queries; use Google Distance Matrix for travel time.

## ANTI-PATTERNS
- **Sequential Ingest**: Never loop `.save()`; use `bulk_create` / `bulk_update` (see `add_scraped_data_to_db`).
- **Coordinate Swap**: Do not use `(lat, lng)` for `Point` creation; GeoDjango expects `(x, y)` which is `(lng, lat)`.
- **Untrusted Coords**: Always validate scraped lat/lng before Point creation.
- **O(N) Scraper Registry**: Avoid adding scrapers manually in multiple places; use `utils.py:get_city_data`.

## TESTING
- **Scrapers**: Mock `requests.get`. Use `test_scraper_performance.py` for ingest efficiency.
- **Geo-Queries**: Test `Distance` functions with known coordinate pairs.
- **Data Integrity**: `Pharmacy` has no unique constraint; `(name, phone)` is matched in Python only, and `ignore_conflicts=True` does not prevent duplicates (ADR 0005).
