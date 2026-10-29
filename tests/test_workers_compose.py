"""The worker compose must pass SENTRY_DSN explicitly (issue #249)."""

import unittest
from pathlib import Path
from typing import Any, cast

import yaml

WORKERS_COMPOSE = (
    Path(__file__).resolve().parent.parent
    / "docker"
    / "prod"
    / "workers"
    / "docker-compose.yml"
)


class WorkersComposeTests(unittest.TestCase):
    def test_worker_receives_sentry_dsn(self) -> None:
        compose = cast(dict[str, Any], yaml.safe_load(WORKERS_COMPOSE.read_text()))
        environment = cast(list[str], compose["services"]["worker"]["environment"])
        self.assertIn("SENTRY_DSN=${SENTRY_DSN:-}", environment)
