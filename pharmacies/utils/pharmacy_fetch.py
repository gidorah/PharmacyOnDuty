import os
from functools import lru_cache

import requests
from dotenv import load_dotenv

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

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        print(f"API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request failed: {str(e)}")

    return []


def fetch_nearest_pharmacies(
    lat: float, lng: float, keyword: str = "pharmacy", limit: int = 5
):
    """Returns cached pharmacy results with limit applied"""

    # First round lat and lng to exclude little variations
    lat, lng = round_lat_lng(lat, lng, precision=4)
    print(f"will fetch pharmacies near {lat}, {lng}")

    results = _fetch_pharmacy_data(lat, lng, keyword)
    return results[:limit]


def round_lat_lng(lat: float, lng: float, precision: int = 6):
    """Rounds lat and lng to given precision"""

    return round(lat, precision), round(lng, precision)
