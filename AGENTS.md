# Agent Guidelines for PharmacyOnDuty

## Virtual Environment
- Project uses `uv` for dependency management
- Python 3.13 required (auto-detected via .python-version)
- No need to manually activate venv - `uv run` handles this automatically

## Build/Lint/Test Commands
- **Run tests**: `uv run python manage.py test`
- **Run single test**: `uv run python manage.py test pharmacies.tests.TestClassName.test_method_name`
- **Lint & format**: `uv run ruff check --fix . && uv run ruff format .`
- **Run migrations**: `uv run python manage.py migrate`
- **Create migrations**: `uv run python manage.py makemigrations`
- **Run dev server**: `uv run python manage.py runserver 0.0.0.0:8000`
- **Build Tailwind CSS**: `uv run python manage.py tailwind build`
- **Install dependencies**: `uv sync` (uses uv.lock)

## Code Style
- **Formatting & Linting**: Use Ruff (Black-compatible formatter + linter)
- **Imports**: Standard library → Django → Third-party → Local (see models.py, views.py, utils.py)
- **Type hints**: Use for function parameters and return types (e.g., `def func(city: str | None = None) -> PharmacyStatus`)
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Models**: Use verbose_name/verbose_name_plural in Meta, related_name for ForeignKeys/OneToOne
- **Django patterns**: Use timezone.now() for time, GeoDjango for spatial queries, bulk_create/bulk_update for efficiency
- **Error handling**: Raise ValueError with descriptive messages, use try/except for external API calls
- **Caching**: Use @lru_cache for expensive operations (geocoding, distance matrix), @cache_page for views
- **Pre-commit**: Tailwind CSS builds automatically on HTML changes (see .pre-commit-config.yaml)
