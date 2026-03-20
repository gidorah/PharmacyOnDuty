import os
from typing import Final
from urllib.parse import unquote, urlparse

DEFAULT_DATABASE_SETTINGS: Final[dict[str, str]] = {
    "NAME": "postgres",
    "USER": "postgres",
    "PASSWORD": "password",
    "HOST": "db",
    "PORT": "5432",
}

DATABASE_ENV_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "NAME": ("DB_NAME", "PGDATABASE", "POSTGRES_DB"),
    "USER": ("DB_USER", "PGUSER", "POSTGRES_USER"),
    "PASSWORD": ("DB_PASSWORD", "PGPASSWORD", "POSTGRES_PASSWORD"),
    "HOST": ("DB_HOST", "PGHOST", "POSTGRES_HOST"),
    "PORT": ("DB_PORT", "PGPORT", "POSTGRES_PORT"),
}


def _get_first_env_value(*names: str) -> str | None:
    """Return the first non-empty value found among the given env vars."""

    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _get_database_url_settings() -> dict[str, str]:
    """Parse database settings from DATABASE_URL when it is present."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return {}

    parsed = urlparse(database_url)
    settings: dict[str, str] = {}
    database_name = parsed.path.lstrip("/")

    if database_name:
        settings["NAME"] = unquote(database_name)
    if parsed.username:
        settings["USER"] = unquote(parsed.username)
    if parsed.password:
        settings["PASSWORD"] = unquote(parsed.password)
    if parsed.hostname:
        settings["HOST"] = parsed.hostname
    if parsed.port:
        settings["PORT"] = str(parsed.port)

    return settings


def get_database_settings() -> dict[str, str]:
    """Resolve database settings from defaults, DATABASE_URL, and env aliases."""

    settings = DEFAULT_DATABASE_SETTINGS.copy()
    settings.update(_get_database_url_settings())

    for key, names in DATABASE_ENV_ALIASES.items():
        value = _get_first_env_value(*names)
        if value:
            settings[key] = value

    return settings


def get_database_connection_kwargs() -> dict[str, str]:
    """Return psycopg2-compatible keyword arguments for the active DB config."""

    settings = get_database_settings()
    return {
        "dbname": settings["NAME"],
        "user": settings["USER"],
        "password": settings["PASSWORD"],
        "host": settings["HOST"],
        "port": settings["PORT"],
    }
