import os
import unittest
from unittest.mock import patch

from PharmacyOnDuty.database_config import get_database_settings


class TestDatabaseConfig(unittest.TestCase):
    def test_database_url_populates_database_settings(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": (
                    "postgresql://app_user:secret@managed-db.internal:6543/appdb"
                )
            },
            clear=True,
        ):
            self.assertEqual(
                get_database_settings(),
                {
                    "NAME": "appdb",
                    "USER": "app_user",
                    "PASSWORD": "secret",
                    "HOST": "managed-db.internal",
                    "PORT": "6543",
                },
            )

    def test_db_variables_override_database_url(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": (
                    "postgresql://app_user:secret@managed-db.internal:6543/appdb"
                ),
                "DB_HOST": "db",
                "DB_PORT": "5432",
            },
            clear=True,
        ):
            self.assertEqual(
                get_database_settings()["HOST"],
                "db",
            )
            self.assertEqual(
                get_database_settings()["PORT"],
                "5432",
            )

    def test_pg_aliases_are_supported(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PGDATABASE": "gis",
                "PGUSER": "postgres",
                "PGPASSWORD": "password",
                "PGHOST": "postgres.internal",
                "PGPORT": "6432",
            },
            clear=True,
        ):
            self.assertEqual(
                get_database_settings(),
                {
                    "NAME": "gis",
                    "USER": "postgres",
                    "PASSWORD": "password",
                    "HOST": "postgres.internal",
                    "PORT": "6432",
                },
            )

    def test_postgres_aliases_are_supported(self) -> None:
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DB": "gis",
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "password",
                "POSTGRES_HOST": "postgres.internal",
                "POSTGRES_PORT": "6432",
            },
            clear=True,
        ):
            self.assertEqual(
                get_database_settings(),
                {
                    "NAME": "gis",
                    "USER": "postgres",
                    "PASSWORD": "password",
                    "HOST": "postgres.internal",
                    "PORT": "6432",
                },
            )
