import os
import unittest
from unittest.mock import MagicMock, patch

from scripts import wait_for_services


class TestWaitForServices(unittest.TestCase):
    @patch("scripts.wait_for_services.psycopg2.connect")
    def test_wait_for_postgres_success(self, mock_connect: MagicMock) -> None:
        mock_connect.return_value.close.return_value = None
        self.assertTrue(wait_for_services.wait_for_postgres())
        mock_connect.assert_called()

    @patch("scripts.wait_for_services.time.sleep")
    @patch("scripts.wait_for_services.psycopg2.connect")
    def test_wait_for_postgres_failure_then_success(
        self, mock_connect: MagicMock, mock_sleep: MagicMock
    ) -> None:
        import psycopg2  # type: ignore

        # Fail twice then succeed
        mock_connect.side_effect = [
            psycopg2.OperationalError("Error"),
            psycopg2.OperationalError("Error"),
            MagicMock(),
        ]
        self.assertTrue(wait_for_services.wait_for_postgres())
        self.assertEqual(mock_connect.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("scripts.wait_for_services.psycopg2.connect")
    def test_wait_for_postgres_uses_database_url(self, mock_connect: MagicMock) -> None:
        mock_connect.return_value.close.return_value = None

        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": (
                    "postgresql://app_user:secret@managed-db.internal:6543/appdb"
                )
            },
            clear=True,
        ):
            self.assertTrue(wait_for_services.wait_for_postgres())

        mock_connect.assert_called_once_with(
            dbname="appdb",
            user="app_user",
            password="secret",
            host="managed-db.internal",
            port="6543",
        )

    @patch("scripts.wait_for_services.redis.from_url")
    def test_wait_for_redis_success(self, mock_redis: MagicMock) -> None:
        mock_redis.return_value.ping.return_value = True
        with patch.dict(os.environ, {"CELERY_BROKER_URL": "redis://localhost:6379/0"}):
            self.assertTrue(wait_for_services.wait_for_redis())
        mock_redis.assert_called()

    @patch("scripts.wait_for_services.time.sleep")
    @patch("scripts.wait_for_services.redis.from_url")
    def test_wait_for_redis_failure_then_success(
        self, mock_redis: MagicMock, mock_sleep: MagicMock
    ) -> None:
        import redis

        # Create the success mock first
        success_mock = MagicMock()
        success_mock.ping.return_value = True

        # Fail twice then succeed
        mock_redis.side_effect = [
            redis.exceptions.ConnectionError("Error"),
            redis.exceptions.ConnectionError("Error"),
            success_mock,
        ]

        with patch.dict(os.environ, {"CELERY_BROKER_URL": "redis://localhost:6379/0"}):
            self.assertTrue(wait_for_services.wait_for_redis())

        self.assertEqual(mock_redis.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
