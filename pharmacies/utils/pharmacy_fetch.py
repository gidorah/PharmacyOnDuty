"""
Module for fetching pharmacy data from external APIs (Google Places).
"""

import os
from functools import lru_cache
from typing import Any

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError

# Load environment variables once at startup
load_dotenv()
API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")


@lru_cache(maxsize=1024)
def _fetch_pharmacy_data(lat: float, lng: float, keyword: str) -> list[dict[str, Any]]:
    """
    Perform the actual HTTP request to Google Places API.

    Cached to prevent redundant API calls for the same coordinates.
    """
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "rankby": "distance",
        "keyword": keyword,
        "key": API_KEY,
    }

    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        raise HTTPError(f"API Error: {response.status_code} - {response.text}")
    data = response.json()
    results = data.get("results", [])
    return results  # type: ignore


def fetch_nearest_pharmacies(
    lat: float, lng: float, keyword: str = "pharmacy", limit: int = 5
) -> list[dict[str, Any]]:
    """
    Retrieve nearest pharmacies from Google Places API.

    Wraps the cached `_fetch_pharmacy_data` function and applies a limit.
    """
    results = _fetch_pharmacy_data(lat, lng, keyword)
    return results[:limit]
