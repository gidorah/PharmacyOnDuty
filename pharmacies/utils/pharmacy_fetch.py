import os
from functools import lru_cache

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError

# Load environment variables once at startup
load_dotenv()
API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")


@lru_cache(maxsize=1024)
def _fetch_pharmacy_data(lat: float, lng: float, keyword: str):
    """Cached function that handles the actual API call"""

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
    return data.get("results", [])


def fetch_nearest_pharmacies(
    lat: float, lng: float, keyword: str = "pharmacy", limit: int = 5
):
    """Returns cached pharmacy results with limit applied"""

    results = _fetch_pharmacy_data(lat, lng, keyword)
    return results[:limit]
