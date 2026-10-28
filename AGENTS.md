# AGENTS.md

Guidance for coding agents (Codex, Claude Code, etc.) working in this repository.

## Project

Pharmacy on-duty finder for Turkey (Eskişehir, Istanbul, Ankara). Django 6 with
GeoDjango/PostGIS, Celery/Redis, Tailwind. Python 3.13, `uv` for dependencies,
`just` as task runner, Docker Compose for every environment. Product overview:
[readme.md](readme.md).

## Where to read

- [CONTEXT.md](CONTEXT.md): glossary. Use its terms in code, tests and PRs.
- [docs/decisions/](docs/decisions/README.md): ADRs. Read the ones touching the
  area you change; the README says when a change needs a new one.
- [docs/explanation/production.md](docs/explanation/production.md): hosts,
  Coolify apps and the deploy path. Update it with any change to `docker/prod/`.
- [docker/testenv/README.md](docker/testenv/README.md): the per-worktree test stack.
- Area files, read before non-trivial edits there:
  [pharmacies/AGENTS.md](pharmacies/AGENTS.md),
  [docker/AGENTS.md](docker/AGENTS.md), [theme/AGENTS.md](theme/AGENTS.md).

## Commands

Everything runs in containers. Do not invoke `python`, `pytest`, `ruff`, `mypy`
or `pip` on the host; use `uv run` inside the stack. `uv` only: `uv sync`,
`uv run`, `uv add`; no `pip`, no manual venvs.

```bash
just dev-up / dev-down / dev-rebuild   # shared dev stack
just dev-django                        # shell in the django container
just dev-db                            # psql into the PostGIS db
just logs <service>                    # django, db, redis, worker, beat, flower
just manage "<command>"                # manage.py inside the container
just migrate / makemigrations / shell / seed
```

Flower is on `localhost:5555` in dev. Sentry starts when `SENTRY_DSN` is set.

## Proving a change: the testenv

Run from inside your worktree; it gives each worktree its own full stack, so
runs never collide with each other or the shared dev stack. `just testenv <args>`
is the same script.

```bash
docker/testenv/testenv.sh prepare <name>   # once: .env and images
docker/testenv/testenv.sh start            # up, validate, seed cities
docker/testenv/testenv.sh check            # validate, ruff, format, mypy, full pytest
docker/testenv/testenv.sh exec django uv run pytest pharmacies/tests/test_views.py -x
docker/testenv/testenv.sh reset            # tear down
```

A change counts as proven when `check` passes after `validate`. `just test`
runs Django's runner, not pytest; prefer the testenv.

## Gates CI runs

`.github/workflows/ci.yml` reports one aggregate check, `check`, that passes
only when its three jobs pass. Run these through `testenv.sh exec django ...`
(or in the dev stack).

- Lint: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`.
- Templates: djlint is not a project dependency; CI runs it with `uvx` at the
  workflow's `DJLINT_VERSION` (the pin in `.pre-commit-config.yaml`):
  `uvx djlint@<version> theme/templates --check --profile=django`, and the same
  with `--lint` and the workflow's `--ignore` list.
- Test: `uv run python manage.py makemigrations --check --dry-run`,
  `uv run python manage.py collectstatic --noinput`,
  `uv run pytest -p no:cacheprovider`.
- Build: the image from `docker/prod/Dockerfile` must build.

`testenv.sh check` covers ruff, mypy and pytest only. It does not run djlint,
the migrations check, collectstatic or the image build; run those yourself when
you touch templates, models, static files or `docker/prod/`.

## Conventions the code cannot show

- Ruff is the sole linter and formatter (`E4/E7/F/I/UP`, line length 88, double
  quotes). Strict mypy with the django plugin; fix types, do not weaken it.
  Never suppress a lint error to make it go away; if you cannot resolve it, ask.
- `timezone.now()`, never `datetime.now()`.
- Ingest uses bulk operations (`bulk_create(ignore_conflicts=True)`,
  `bulk_update`); never loop `.save()`.
  `pharmacies/tests/test_scraper_performance.py` enforces it.
- Scraper tests mock `requests` (scrapers use `get` and `post`); never hit the network.
- Scrapers are registered only in `pharmacies/utils/utils.py:get_city_data`.
- GeoDjango `Point(x, y)` is `(lng, lat)`. Validate scraped coordinates first.
- Scraping cadence lives in the database: `ScraperConfig.save()` writes
  `django-celery-beat` `PeriodicTask` rows ([ADR 0002](docs/decisions/0002-drive-scrape-schedules-from-the-database.md)).
- Do not hand-edit `theme/static/css/dist/styles.css`; use Tailwind classes, not raw CSS.
- Tests live in `tests/` (infra and performance) and `pharmacies/tests/` (domain).
