"""Tests for production Google Maps configuration warnings."""

from unittest.mock import MagicMock, patch

from PharmacyOnDuty.settings import warn_production_maps_config


class TestWarnProductionMapsConfig:
    def test_skips_when_debug(self) -> None:
        logger = MagicMock()
        with patch("PharmacyOnDuty.settings.logger", logger):
            warn_production_maps_config(debug=True, api_key=None, map_id="DEMO_MAP_ID")
        logger.error.assert_not_called()
        logger.warning.assert_not_called()

    def test_errors_on_missing_api_key(self) -> None:
        logger = MagicMock()
        with patch("PharmacyOnDuty.settings.logger", logger):
            warn_production_maps_config(debug=False, api_key="", map_id="real-map-id")
        logger.error.assert_called_once()
        logger.warning.assert_not_called()

    def test_warns_on_demo_map_id(self) -> None:
        logger = MagicMock()
        with patch("PharmacyOnDuty.settings.logger", logger):
            warn_production_maps_config(
                debug=False, api_key="valid-key", map_id="DEMO_MAP_ID"
            )
        logger.warning.assert_called_once()
        logger.error.assert_not_called()
