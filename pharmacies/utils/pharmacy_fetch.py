import requests


def fetch_nearest_pharmacies(lat, lng, keyword="pharmacy", limit=5):
    import os

    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "rankby": "distance",  # Orders results by distance
        "keyword": keyword,  # Search keyword, e.g., pharmacy
        "key": api_key,
    }

    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if "results" in data:
            # Return only the nearest 'limit' pharmacies
            return data["results"][:limit]
        print("No results found.")
        return []
    print(f"Error: {response.status_code} - {response.text}")
    return []
