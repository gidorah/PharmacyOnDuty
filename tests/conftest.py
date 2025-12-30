import json
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture
def google_snapshots() -> dict[str, Any]:
    with open("tests/fixtures/google_api_snapshots.json") as f:
        data: dict[str, Any] = json.load(f)
        return data


@pytest.fixture
def mock_google_maps(google_snapshots: dict[str, Any]) -> Generator[Any]:
    def side_effect(
        url: str, params: dict[str, Any] | None = None, timeout: float | None = None
    ) -> Any:
        params = params or {}

        class MockResponse:
            def __init__(
                self, json_data: dict[str, Any], status_code: int = 200
            ) -> None:
                self.json_data = json_data
                self.status_code = status_code
                self.text = json.dumps(json_data)

            def json(self) -> dict[str, Any]:
                return self.json_data

            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    raise Exception(f"HTTP Error: {self.status_code}")

        if "geocode" in url:
            try:
                latlng_part = url.split("latlng=")[1].split("&")[0]
                key = f"geocode:{latlng_part}"
                if key in google_snapshots:
                    return MockResponse(google_snapshots[key])
            except IndexError:
                pass

        elif "distancematrix" in url:
            try:
                origins_part = url.split("origins=")[1].split("&")[0]

                key = f"distancematrix:{origins_part}"
                if key in google_snapshots:
                    return MockResponse(google_snapshots[key])
            except IndexError:
                pass

        print(f"WARNING: No snapshot found for URL: {url}")
        return MockResponse(
            {"status": "REQUEST_DENIED", "error_message": "No snapshot found"}, 200
        )

    with patch("requests.get", side_effect=side_effect) as mock_get:
        yield mock_get
