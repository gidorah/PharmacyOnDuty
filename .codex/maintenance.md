# Codex Maintenance Spec

## Project Identity

- GitHub repo: `gidorah/PharmacyOnDuty`
- Default branch: `main`
- Production URL: `https://eczanerede.com`
- Timezone: `Europe/Istanbul`
- Product: Public pharmacy on-duty finder for Turkey; current city coverage is Eskisehir, Istanbul, and Ankara.

## Required Tools

- GitHub CLI: `gh` must be authenticated with read/write access to issues, PRs, labels, checks, and contents for `gidorah/PharmacyOnDuty`.
- Sentry: required for Sentry observe and Sentry fix. Organization/project must be verified by bootstrap before those tasks are activated.
- Context7: required for Dependabot release-note and API research; official maintainer docs/GitHub releases are fallback sources.
- Runtime notes: use Docker Compose, `just`, and `uv` inside containers. Do not run host `python`, `pytest`, `pip`, or host virtualenv commands.
- Codex automation memory: use `${CODEX_HOME:-/home/onur/.codex}/automations/<automation-id>/memory.md` for ephemeral task state only.
- Required environment variables for scheduled runtime: `CODEX_HOME` optional; Sentry connector/API credentials must be available to Sentry tasks; API-mode Sentry tasks should receive `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, and `SENTRY_PROJECT`; no project secrets are stored in this spec.

## Validation Commands

- Setup: `just dev-up`
- Dependency sync: containers run `uv sync` on startup; for explicit repair use `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv sync`
- Lint check: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv run ruff check .`
- Lint fix: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv run ruff check --fix .`
- Format: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv run ruff format .`
- Typecheck: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv run mypy .`
- Full tests: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv run pytest -x`
- Targeted tests: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv run pytest <path-or-nodeid> -x`
- Dependency audit: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django sh -lc 'uv export --no-hashes --format requirements-txt | uvx pip-audit -r /dev/stdin'`
- Smoke HTTP: run only the HTTP flows listed under `Production Smoke Tests`.
- Smoke browser: run only the browser flows listed under `Production Smoke Tests`.

## Dependabot Policy

- Auto-merge patch: allowed when CI is green, release notes are clear, no relevant breaking behavior exists, and repo API/config usage is unaffected.
- Auto-merge minor: allowed for low-risk minor updates only. Dev dependencies may qualify when CI is green and release notes show no relevant config/API impact. Runtime dependencies qualify only when listed in `Low-risk minor packages`.
- Low-risk minor packages: `ruff`, `pytest`, `pytest-django`, `pytest-cov`, `mypy`, `django-stubs`, `django-stubs-ext`, `types-requests`, `types-redis`, `pre-commit`, `interrogate`, `pygments`, `faker`.
- Never auto-merge: `django`, `celery`, `django-celery-beat`, `django-celery-results`, `redis`, `django-redis`, `psycopg2-binary`, `sentry-sdk`, `requests`, `urllib3`, `gunicorn`, `whitenoise`, `django-tailwind`, `beautifulsoup4`, `python-dotenv`, major updates, red/pending/missing CI, ambiguous release notes.
- Lockfile repair command: `docker-compose -f docker/dev/docker-compose.yml --project-directory . exec django uv sync`
- Review cap per run: 10 Dependabot PRs.

## Sentry

- Organization: `TBD - bootstrap must verify through Sentry access`
- Project: `TBD - bootstrap must verify through Sentry access`
- Environment: `production`
- Issue label: `sentry`
- Skip labels: `wontfix`, `blocked`, `needs-design`, `needs-human`, `investigating`
- Observe cap: analyze at most 5 Sentry issues and file at most 3 new GitHub issues per run.
- Fix cap: fix exactly 1 eligible GitHub issue per run.
- Safe-fix boundaries: localized Django/Python fixes only; no schema migrations, broad refactors, scraper rewrites, deployment changes, external API contract changes, billing/API-key behavior changes, or uncertain product decisions.
- No-touch without `needs-human`: `pharmacies/migrations/**`, `docker/prod/**`, deployment scripts, Sentry initialization/configuration, Google Maps key/proxy policy, production database settings, broad Celery scheduling behavior, and scraper changes that require live external network validation.

## Security

- Issue label: `security`
- Severity labels: `sev-low`, `sev-med`, `sev-high`, `sev-critical`
- Skip labels: `wontfix`, `blocked`, `needs-design`, `needs-human`, `investigating`
- Observe cap: file at most 5 new security issues per run.
- Fix cap: fix exactly 1 eligible GitHub issue per run.
- Audit paths: `PharmacyOnDuty/settings.py`, `PharmacyOnDuty/database_config.py`, `PharmacyOnDuty/urls.py`, `pharmacies/views.py`, `pharmacies/tasks.py`, `pharmacies/utils/*.py`, `theme/templates/**/*.html`, `templates/**/*.txt`, `docker/prod/**/*.yml`, `docker/dev/**/*.yml`, `scripts/**/*.py`
- Exclusions: `.git/**`, `.venv/**`, `.ruff_cache/**`, `htmlcov/**`, `**/__pycache__/**`, `pharmacies/migrations/**`, `tests/**`, `pharmacies/tests/**`, `docs/**`, `readme.md`, fixture files, generated coverage files.
- Deterministic checks: dependency audit, tracked-file secrets scan, Django settings hardening, unsafe raw SQL, SSRF in outbound requests, XSS via `|safe`, unsafe deserialization, command injection, path traversal, permissive host/CORS/CSRF settings.
- Safe-fix boundaries: localized security patches only; no migrations, broad refactors, dependency strategy changes, production secret changes, DNS/Coolify/VPS changes, or behavior changes that need product judgment.

## Production Smoke Tests

### HTTP Flows

### homepage loads

- Mode: `http`
- URL: `https://eczanerede.com/`
- Method: `GET`
- Expected status: `200`
- Expected contains: `Eczanerede`
- Timeout seconds: `15`
- Failure issue title: `prod smoke: homepage failing`
- Recovery: close the issue after one successful run.

### robots txt loads

- Mode: `http`
- URL: `https://eczanerede.com/robots.txt`
- Method: `GET`
- Expected status: `200`
- Expected contains: `User-agent`
- Timeout seconds: `15`
- Failure issue title: `prod smoke: robots.txt failing`
- Recovery: close the issue after one successful run.

### sitemap loads

- Mode: `http`
- URL: `https://eczanerede.com/sitemap.xml`
- Method: `GET`
- Expected status: `200`
- Expected contains: `eczanerede.com`
- Timeout seconds: `15`
- Failure issue title: `prod smoke: sitemap failing`
- Recovery: close the issue after one successful run.

### static logo loads

- Mode: `http`
- URL: `https://eczanerede.com/static/icons/eczane-logo.png`
- Method: `GET`
- Expected status: `200`
- Expected content type: `image/png`
- Timeout seconds: `15`
- Failure issue title: `prod smoke: static assets failing`
- Recovery: close the issue after one successful run.

### google maps proxy blocks missing referer

- Mode: `http`
- URL: `https://eczanerede.com/google_maps_proxy?loading=async&callback=mapsCallback`
- Method: `GET`
- Expected status: `403`
- Expected contains: `Forbidden`
- Timeout seconds: `15`
- Failure issue title: `prod smoke: google maps proxy referer guard failing`
- Recovery: close the issue after one successful run.

### Browser Flows

### rendered homepage map shell

- Mode: `browser`
- URL: `https://eczanerede.com/`
- Browser: `Playwright Chromium`
- Expected status: `200`
- Expected title contains: `Eczanerede`
- Expected selectors: `#map`, `#pharmacy-list-container`, `#pharmacy-items`
- Console errors allowed: Google Maps authorization/configuration messages only when the page still renders the shell.
- Timeout seconds: `30`
- Failure issue title: `prod smoke: rendered homepage failing`
- Recovery: close the issue after one successful run.

### policy pages render

- Mode: `browser`
- URLs: `https://eczanerede.com/privacy-policy`, `https://eczanerede.com/terms-of-service`, `https://eczanerede.com/cookie-policy`
- Browser: `Playwright Chromium`
- Expected status: `200`
- Expected title contains: `Eczanerede`
- Timeout seconds: `30`
- Failure issue title: `prod smoke: policy pages failing`
- Recovery: close the issue after one successful run.

## Automation Failure Policy

- Failure issue title prefix: `maintenance:`
- Automation failure issue title format: `maintenance: <task name> failing`
- Escalation labels: `maintenance`, `automation`, `needs-human`
- Consecutive failure threshold: second consecutive automation failure creates or updates a GitHub issue; third consecutive failure adds `needs-human`.
- Reset rule: a successful automation run resets the automation failure streak.
- Product smoke failures create or update stable product failure issues immediately and are not delayed by the automation failure threshold.

## Project-Specific Overrides

- Commit and PR title style: emoji plus conventional commits, for example `🐛 fix: <summary> (closes #123)` and `🔒 fix(security): <summary> (closes #456)`.
- Branch naming: use domain/id branches such as `sentry/issue-123` and `security/issue-456`.
- GeoDjango coordinate order: `Point(lng, lat)`, never `Point(lat, lng)`.
- Time handling: use `timezone.now()`, never `datetime.now()`.
- Ingest performance: use bulk DB operations; never loop `.save()` for scraper ingestion.
- Scraper tests must mock `requests.get`; do not hit chamber websites from tests.
- Frontend changes should use Tailwind classes rather than hand-written raw CSS.
