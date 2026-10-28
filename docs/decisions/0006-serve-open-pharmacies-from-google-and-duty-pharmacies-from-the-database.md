# Serve open pharmacies from Google, duty pharmacies from the database

## Status

Accepted. Back-filled 28 Oct 2026 from `pharmacies/views.py` and
`pharmacies/utils/utils.py`. The reasons are inferred from the code.

## Context

During working hours any pharmacy is open, and the chambers publish only duty
lists. Outside working hours only duty pharmacies are open, and only the
chambers know which.

## Decision

`get_pharmacy_points` finds the visitor's city by reverse geocoding, then
asks its `WorkingSchedule` for the city status:

- **open**: the nearest pharmacies come live from Google Places
  (`pharmacy_fetch.py`), not from this database;
- **closed**: the nearest pharmacies on duty at that time come from the
  database (`get_nearest_pharmacies_on_duty`), filled by the scrapers.

Either way Google's Distance Matrix adds travel distance and the list is
sorted by it.

## Alternatives

- Always serve from the database: no Places calls, but the database holds
  only pharmacies that have been on duty, not every pharmacy.
- Always serve from Google Places: no scrapers, but Places does not know duty
  assignments.

## Consequences

- Every request calls paid Google APIs (Geocoding, and Places or Distance
  Matrix), which is why the endpoint is rate-limited (ADR 0003).
- The working-hour boundaries are the moments the source of truth switches,
  which is why scrapes also run then (ADR 0002).
- In `DEBUG`, the view uses a fixed time ten hours after process start
  (`TEST_TIME`) instead of now, so local results can differ from production.
