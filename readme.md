# Eczanerede (Pharmacy Locator)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Eczanerede helps people in Turkey find a pharmacy that is open right now, or the one on duty. It covers Eskişehir, Istanbul and Ankara.

**Live site:** [eczanerede.com](https://eczanerede.com)

## Screenshots

<img src="screenshots/Screenshot%20Map.png" width="300"> <img src="screenshots/Screenshot%20List.png" width="300">

## What it does

It is built for people who need medicine outside normal hours or in an area they do not know, mostly on a phone. The goals are to find the nearest available pharmacy fast, show the way there, and be correct about "open" versus "on duty".

- During a city's working hours, the visitor gets the nearest open pharmacies from Google Places.
- Outside working hours, the visitor gets the nearest pharmacies on duty from our own database. The data is scraped from each city's pharmacists' chamber (Istanbul: the provincial health directorate).
- A map shows directions (Google Maps) with driving distance and time (Google Distance Matrix).
- The layout is mobile-first and the list is swipeable.
- `/health/data/` is a public page showing how fresh the scraped data is.
- `/get_pharmacy_points` is rate limited per visitor (Redis-backed).

A location test suite (`tests/test_location_coverage.py`, fixtures in `tests/fixtures/`) checks more than 50 places, inside and outside the covered cities, against recorded Google responses.

Stack: Python 3.13, Django 6 with GeoDjango, PostgreSQL 15 with PostGIS, Celery and Redis (the beat schedule lives in the database), Tailwind (the `theme/` app), jQuery and Hammer.js on the front end (loaded in `theme/templates/pharmacies.html`; Hammer.js drives the swipeable list), uv, just and Docker Compose.

## Quick start

You need Docker with `docker-compose`, [just](https://github.com/casey/just) and git.

```bash
git clone https://github.com/gidorah/PharmacyOnDuty.git && cd PharmacyOnDuty
cp .env.example .env
```

Edit `.env`: set `REDIS_PASSWORD` and use the same password in `CELERY_BROKER_URL`, set `DJANGO_DEBUG=True` for local work, set the four HTTPS switches in the "Production HTTPS" block (`DJANGO_ENABLE_SECURE_PROXY_SSL_HEADER`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SESSION_COOKIE_SECURE` and `DJANGO_CSRF_COOKIE_SECURE`) to `False` for local work (left on, `http://localhost:8000/` redirects to https and the site cannot be opened), and optionally set `GOOGLE_MAPS_API_KEY` (without it the maps and the Google results do not work). `.env.example` lists every variable.

```bash
just dev-setup   # starts the dev stack and runs migrations
just seed        # creates the cities and their scraper schedules
```

Then open http://localhost:8000. Flower (the Celery monitor) is at http://localhost:5555.

The dev stack is defined in `docker/dev/docker-compose.yml` and runs django, db, redis, worker, beat and flower. Other recipes you will use: `just --list`, `just dev-down`, `just logs <service>`, `just shell`, `just dev-django`.

## Checks

The check that gives the real result, and the one pull requests use, runs in a per-worktree test environment:

```bash
docker/testenv/testenv.sh prepare <name>
docker/testenv/testenv.sh start
docker/testenv/testenv.sh check   # validate, ruff, format, mypy, full pytest
docker/testenv/testenv.sh reset
```

`just testenv <args>` runs the same script. Details are in `docker/testenv/README.md`.

`just test` is a quick run of Django's own test runner in the dev stack. It only covers part of the suite (the unittest-style tests; the full suite is pytest) and can fail on settings that only the testenv sets, such as no proxy SSL header and collected static files.

CI (`.github/workflows/ci.yml`) runs lint, tests and the production image build on every pull request and every push to `main`.

Inside the container, lint, format and types are `uv run ruff check .`, `uv run ruff format .` and `uv run mypy .`.

## Deploy

Coolify deploys every push to `main`. The web stack (`docker/prod/services/`) runs on a Hetzner VPS and the Celery worker (`docker/prod/workers/`) on a separate home machine. [`docs/explanation/production.md`](docs/explanation/production.md) explains the setup. The root `Procfile`, `Aptfile` and `nginx.conf` are leftovers from an older setup and are not used.

## Documentation

- [`AGENTS.md`](AGENTS.md): how to work in the repo, for people and coding agents.
- [`CONTEXT.md`](CONTEXT.md): the project glossary.
- [`docs/`](docs/): architecture decisions in `docs/decisions/` and explanations such as [`docs/explanation/production.md`](docs/explanation/production.md).
- [`docker/testenv/README.md`](docker/testenv/README.md): the test environment.

## Contributing

Open an issue or a pull request. Read `AGENTS.md` first, add tests with every change, and use ruff as the formatter.

## License and contact

MIT, see [`LICENSE`](LICENSE). Contact: Onur Akyüz, onur_akyuz@icloud.com.
