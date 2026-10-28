# Eczanerede

Eczanerede ("where is a pharmacy") is the public site at eczanerede.com that
shows the nearest pharmacy a visitor can go to right now, in the Turkish cities
it covers. This repository is named PharmacyOnDuty.

Use these words in code, issues, PRs and tests. Each entry says what the term
means here; _Avoid_ lists words that mean something else or blur the term.

## Pharmacies and time

**Pharmacy**:
One pharmacy as a source lists it: name, address, district, phone, a location
point, and its current or next duty window (`Pharmacy`).

**On duty** (nöbetçi):
Assigned by the city's chamber to stay open outside working hours. A pharmacy
is on duty at a time when that time falls inside its duty window.
_Avoid_: open, emergency pharmacy

**Duty window**:
`duty_start` to `duty_end` of one pharmacy, as its source publishes it,
usually an evening to the next morning, or a whole Sunday.
_Avoid_: shift (except when quoting a source)

**Working hours**:
The hours ordinary pharmacies in a city are open: weekdays and Saturday, start
and end, stored in UTC (`WorkingSchedule`). Sundays have none.

**City status**:
For one city at one time, either **open** (inside working hours) or **closed**
(outside them), from `WorkingSchedule.get_status`. It decides what a visitor
sees.
_Avoid_: pharmacy status (for this meaning)

**Open pharmacies**:
What a visitor gets when the city status is open: the nearest pharmacies from
Google Places, not from this database
([ADR 0006](docs/decisions/0006-serve-open-pharmacies-from-google-and-duty-pharmacies-from-the-database.md)).

**Duty pharmacies**:
What a visitor gets when the city status is closed: the nearest pharmacies on
duty at that time, from this database.

## Data sources

**Chamber** (Eczacı Odası):
The body that publishes a city's duty list; for Istanbul it is the provincial
health directorate. The source of truth for duty windows.
_Avoid_: provider, API

**Scraper**:
The code that reads one source's duty list and returns the standard dict
(`pharmacies/utils/<source>_scraper.py`), registered in `get_city_data`.

**Scrape**:
One run of `run_scraper` for one city: fetch, then one bulk write
([ADR 0005](docs/decisions/0005-identify-a-pharmacy-by-name-and-phone-and-never-delete-rows.md)).

**Scraper config**:
A city's scrape interval in hours and its last successful scrape
(`ScraperConfig.last_run`).

**Data health**:
The public `/health/data/` summary: per city, the last scrape and how many
pharmacies are on duty now and in the next 12 hours.

## Places and distance

**City**:
A city the site covers, by its ASCII lower-case name (`eskisehir`,
`istanbul`, `ankara`). A visitor's city comes from reverse geocoding their
location.

**District** (ilçe):
The part of a city a pharmacy is in, as its source names it.

**Distance**:
Straight-line distance, used to pick and sort candidates in the database.

**Travel distance**:
Driving distance and time from Google's Distance Matrix, shown to the visitor.

## Infrastructure

**Maps proxy**:
`google_maps_proxy`, which serves the Google Maps script with the key added on
the server
([ADR 0004](docs/decisions/0004-proxy-the-google-maps-script-behind-a-referer-allow-list.md)).

**Worker**:
The Celery worker that runs scrapes, on its own host
([ADR 0001](docs/decisions/0001-run-the-celery-worker-on-a-home-machine.md)).

**Testenv**:
The full stack per git worktree in `docker/testenv/`, used to prove a change.
_Avoid_: dev stack (that is `docker/dev/`)
