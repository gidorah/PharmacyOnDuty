import requests

try:
    requests.get(
        "https://nonexistent.maps.googleapis.com/maps/api/js",
        params={"key": "SECRET_KEY_123"},
        timeout=0.01,
    )
except Exception as e:
    print("EXCEPTION:", str(e))
