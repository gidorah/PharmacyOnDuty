import importlib
import os
from typing import Any
from unittest.mock import patch

from django.core.exceptions import DisallowedHost
from django.test import SimpleTestCase

# We need to import the module object, not just the name
import PharmacyOnDuty.settings as settings_module


class SentryConfigTest(SimpleTestCase):
    @patch("PharmacyOnDuty.settings.sentry_sdk.init")
    def test_sentry_ignores_system_exit(self, mock_init: Any) -> None:
        # Set environment variable to ensure Sentry initializes
        with patch.dict(
            os.environ, {"SENTRY_DSN": "https://public@sentry.example.com/1"}
        ):
            # Reload the settings module to re-run the initialization logic
            importlib.reload(settings_module)

        # Check if sentry_sdk.init was called
        self.assertTrue(mock_init.called, "sentry_sdk.init should have been called")

        # Verify arguments
        _, kwargs = mock_init.call_args

        # Check for ignore_errors
        self.assertIn(
            "ignore_errors", kwargs, "ignore_errors should be passed to sentry_sdk.init"
        )
        self.assertIn(
            SystemExit, kwargs["ignore_errors"], "SystemExit should be in ignore_errors"
        )

    @patch("PharmacyOnDuty.settings.sentry_sdk.init")
    def test_sentry_ignores_disallowed_host(self, mock_init: Any) -> None:
        # Set environment variable to ensure Sentry initializes
        with patch.dict(
            os.environ, {"SENTRY_DSN": "https://public@sentry.example.com/1"}
        ):
            # Reload the settings module to re-run the initialization logic
            importlib.reload(settings_module)

        # Check if sentry_sdk.init was called
        self.assertTrue(mock_init.called, "sentry_sdk.init should have been called")

        # Verify arguments
        _, kwargs = mock_init.call_args

        # Check for ignore_errors
        self.assertIn(
            "ignore_errors", kwargs, "ignore_errors should be passed to sentry_sdk.init"
        )
        self.assertIn(
            DisallowedHost,
            kwargs["ignore_errors"],
            "DisallowedHost should be in ignore_errors",
        )
